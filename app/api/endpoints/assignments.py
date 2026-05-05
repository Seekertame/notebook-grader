import nbformat
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_teacher
from app.grader.reporter import generate_csv_report
from app.models.api import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TemplateUploadResponse,
)
from app.models.domain import Assignment, Submission, Task, TaskResult, Teacher
from app.models.schemas import StudentInfo, StudentWorkResult, TaskGradingResult

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("", response_model=AssignmentResponse)
def create_assignment(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = Assignment(
        title=data.title,
        course_name=data.course_name,
        group_name=data.group_name,
        teacher_id=current_teacher.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("", response_model=list[AssignmentResponse])
def list_assignments(
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    return (
        db.query(Assignment)
        .filter(Assignment.teacher_id == current_teacher.id)
        .options(joinedload(Assignment.tasks))
        .all()
    )


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = (
        db.query(Assignment)
        .options(joinedload(Assignment.tasks))
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.put("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()


@router.post("/{assignment_id}/template", response_model=TemplateUploadResponse)
def upload_template(
    assignment_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if not file.filename or not file.filename.lower().endswith(".ipynb"):
        raise HTTPException(status_code=400, detail="Ожидается файл *.ipynb")

    if file.size is not None and file.size > 52428800:
        raise HTTPException(
            status_code=400,
            detail="Файл превышает максимальный размер 50 МБ",
        )

    try:
        nb = nbformat.read(file.file, as_version=4)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Невозможно прочитать файл как Jupyter Notebook",
        )

    assignment.template_filename = file.filename
    assignment.template_content = nb

    existing_codes = {
        t.task_code
        for t in db.query(Task.task_code)
        .filter(Task.assignment_id == assignment_id)
        .all()
    }

    task_codes: list[str] = []
    for cell in nb.get("cells", []):
        tags = cell.get("metadata", {}).get("tags", [])
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("task:"):
                code = tag[len("task:"):]
                if code and code not in existing_codes and code not in task_codes:
                    task_codes.append(code)

    for code in task_codes:
        db.add(
            Task(
                assignment_id=assignment_id,
                task_code=code,
                title=f"Задача {code}",
                max_score=10,
                check_type="answer",
                expected_answer=None,
            )
        )

    db.commit()

    return TemplateUploadResponse(
        filename=file.filename,
        tasks_created=len(task_codes),
    )


@router.post("/{assignment_id}/tasks", response_model=TaskResponse)
def create_task(
    assignment_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    duplicate = (
        db.query(Task.id)
        .filter(
            Task.assignment_id == assignment_id,
            Task.task_code == data.task_code,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Задача с кодом '{data.task_code}' уже существует в этом задании",
        )

    task = Task(
        assignment_id=assignment_id,
        task_code=data.task_code,
        title=data.title,
        max_score=data.max_score,
        check_type=data.check_type,
        expected_answer=data.expected_answer,
        test_cases=data.test_cases,
        reference_code=data.reference_code,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/{assignment_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    assignment_id: int,
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    task = (
        db.query(Task)
        .join(Assignment)
        .filter(
            Task.id == task_id,
            Task.assignment_id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    payload = data.model_dump(exclude_unset=True)
    new_code = payload.get("task_code")
    if new_code is not None and new_code != task.task_code:
        duplicate = (
            db.query(Task.id)
            .filter(
                Task.assignment_id == assignment_id,
                Task.task_code == new_code,
                Task.id != task_id,
            )
            .first()
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Задача с кодом '{new_code}' уже существует в этом задании",
            )

    for field, value in payload.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{assignment_id}/tasks/{task_id}", status_code=204)
def delete_task(
    assignment_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    task = (
        db.query(Task)
        .join(Assignment)
        .filter(
            Task.id == task_id,
            Task.assignment_id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.flush()

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .options(joinedload(Submission.task_results))
        .all()
    )
    for sub in submissions:
        sub.total_score = sum(tr.awarded_points for tr in sub.task_results)

    db.commit()


@router.get("/{assignment_id}/report")
def get_report(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .options(joinedload(Submission.task_results))
        .all()
    )
    if not submissions:
        raise HTTPException(
            status_code=404,
            detail="No submissions found for this assignment",
        )

    work_results = []
    for sub in submissions:
        student = StudentInfo(
            fio=sub.student_fio,
            group=sub.student_group,
        )
        task_results = [
            TaskGradingResult(
                task_code=tr.task.task_code,
                awarded_points=tr.awarded_points,
                status=tr.status,
                explanation=tr.explanation,
            )
            for tr in sub.task_results
        ]
        work_results.append(
            StudentWorkResult(
                student=student,
                task_results=task_results,
                total_score=sub.total_score,
            )
        )

    csv_content = generate_csv_report(work_results)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="report_{assignment_id}.csv"'
        },
    )
