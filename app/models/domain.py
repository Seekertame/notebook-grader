from sqlalchemy import Column, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=True)

    assignments = relationship("Assignment", back_populates="teacher")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    title = Column(String(100), nullable=False)
    course_name = Column(String(100), nullable=True)
    group_name = Column(String(50), nullable=True)
    template_filename = Column(String, nullable=True)
    template_content = Column(JSON, nullable=True)

    teacher = relationship("Teacher", back_populates="assignments")
    tasks = relationship("Task", back_populates="assignment", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    task_code = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    max_score = Column(Integer, nullable=False)
    check_type = Column(Enum("answer", "tests", "reference_assert", name="check_type_enum"), nullable=False)
    expected_answer = Column(String, nullable=True)
    test_cases = Column(JSON, nullable=True)
    reference_code = Column(Text, nullable=True)

    assignment = relationship("Assignment", back_populates="tasks")
    task_results = relationship("TaskResult", back_populates="task", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_fio = Column(String(150), nullable=False)
    student_group = Column(String(50), nullable=False)
    status = Column(String, nullable=False)
    total_score = Column(Integer, nullable=False, default=0)

    assignment = relationship("Assignment", back_populates="submissions")
    task_results = relationship("TaskResult", back_populates="submission", cascade="all, delete-orphan")


class TaskResult(Base):
    __tablename__ = "task_results"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    status = Column(String, nullable=False)
    awarded_points = Column(Integer, nullable=False)
    explanation = Column(String, nullable=True)

    submission = relationship("Submission", back_populates="task_results")
    task = relationship("Task", back_populates="task_results")
