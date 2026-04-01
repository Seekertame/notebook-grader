from fastapi import APIRouter, Depends, HTTPException
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
        .filter(Assignment.id == assignment_id)
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

    has_submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .first()
        is not None
    )
    if has_submissions:
        raise HTTPException(
            status_code=409,
            detail="Нельзя удалить задание, для которого уже загружены работы студентов",
        )

    db.query(Task).filter(Task.assignment_id == assignment_id).delete()
    db.delete(assignment)
    db.commit()


@router.post("/{assignment_id}/tasks", response_model=TaskResponse)
def create_task(
    assignment_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    task = Task(
        assignment_id=assignment_id,
        task_code=data.task_code,
        title=data.title,
        max_score=data.max_score,
        check_type=data.check_type,
        expected_answer=data.expected_answer,
        test_cases=data.test_cases,
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
        .filter(Task.id == task_id, Task.assignment_id == assignment_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in data.model_dump(exclude_unset=True).items():
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
        .filter(Task.id == task_id, Task.assignment_id == assignment_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    has_results = (
        db.query(TaskResult)
        .filter(TaskResult.task_id == task_id)
        .first()
        is not None
    )
    if has_results:
        raise HTTPException(
            status_code=409,
            detail="Нельзя удалить задачу, для которой уже есть результаты проверки",
        )

    db.delete(task)
    db.commit()


@router.get("/{assignment_id}/report")
def get_report(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
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
