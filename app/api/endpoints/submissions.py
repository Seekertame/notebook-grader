from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.grader.checker import grade_task
from app.grader.executor import run_code_in_sandbox
from app.grader.parser import parse_notebook_bytes
from app.models.api import SubmissionResponse
from app.models.domain import Submission, Task, TaskResult
from app.models.schemas import TaskConfig

router = APIRouter(tags=["submissions"])


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionResponse,
)
async def create_submission(
    assignment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    parsed = parse_notebook_bytes(content)

    db_tasks = db.query(Task).filter(Task.assignment_id == assignment_id).all()
    if not db_tasks:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found or has no tasks",
        )

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
    submission = Submission(
        assignment_id=assignment_id,
        student_fio=student.fio if student else "",
        student_group=student.group if student else "",
        status="graded",
        total_score=total_score,
    )
    db.add(submission)
    db.flush()

    for db_task, points, status, explanation in grading_results:
        task_result = TaskResult(
            submission_id=submission.id,
            task_id=db_task.id,
            status=status,
            awarded_points=points,
            explanation=explanation,
        )
        db.add(task_result)

    db.commit()
    db.refresh(submission)
    return submission
