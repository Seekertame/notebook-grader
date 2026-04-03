from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.grader.checker import grade_task
from app.grader.executor import run_code_in_sandbox
from app.grader.parser import parse_notebook_bytes
from app.models.api import BatchSubmissionResponse, SubmissionBriefResult
from app.models.domain import Submission, Task, TaskResult
from app.models.schemas import TaskConfig

router = APIRouter(tags=["submissions"])


def _grade_one(content: bytes, db_tasks: list[Task]) -> tuple[str, str, int, list]:
    """Parse and grade a single notebook. Returns (fio, group, total_score, grading_results)."""
    parsed = parse_notebook_bytes(content)
    code_map = {cell.task_code: cell.source for cell in parsed.tasks}

    total_score = 0
    grading_results = []

    for db_task in db_tasks:
        source = code_map.get(db_task.task_code)

        if source is None:
            grading_results.append(
                (db_task, 0, "структура ноутбука не соответствует заданию", None)
            )
            continue

        config = TaskConfig(
            task_code=db_task.task_code,
            max_score=db_task.max_score,
            check_type=db_task.check_type,
            expected_answer=db_task.expected_answer,
            test_cases=db_task.test_cases,
        )
        result = grade_task(source, config, run_code_in_sandbox)

        total_score += result.awarded_points
        grading_results.append(
            (db_task, result.awarded_points, result.status, result.explanation)
        )

    student = parsed.student
    fio = student.fio if student else ""
    group = student.group if student else ""

    return fio, group, total_score, grading_results


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=BatchSubmissionResponse,
)
async def create_submissions(
    assignment_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    db_tasks = db.query(Task).filter(Task.assignment_id == assignment_id).all()
    if not db_tasks:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found or has no tasks",
        )

    results: list[SubmissionBriefResult] = []
    success_count = 0

    for file in files:
        content = await file.read()

        try:
            fio, group, total_score, grading_results = _grade_one(content, db_tasks)
        except Exception as exc:
            results.append(
                SubmissionBriefResult(
                    student_fio=file.filename or "",
                    student_group="",
                    status="error",
                    total_score=0,
                    error=str(exc),
                )
            )
            continue

        submission = Submission(
            assignment_id=assignment_id,
            student_fio=fio,
            student_group=group,
            status="graded",
            total_score=total_score,
        )
        db.add(submission)
        db.flush()

        for db_task, points, status, explanation in grading_results:
            db.add(
                TaskResult(
                    submission_id=submission.id,
                    task_id=db_task.id,
                    status=status,
                    awarded_points=points,
                    explanation=explanation,
                )
            )

        success_count += 1
        results.append(
            SubmissionBriefResult(
                student_fio=fio,
                student_group=group,
                status="graded",
                total_score=total_score,
            )
        )

    db.commit()

    return BatchSubmissionResponse(
        total=len(files),
        success=success_count,
        failed=len(files) - success_count,
        results=results,
    )
