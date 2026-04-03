from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    title: str
    course_name: str | None = None
    group_name: str | None = None


class AssignmentUpdate(BaseModel):
    title: str | None = None
    course_name: str | None = None
    group_name: str | None = None


class TaskCreate(BaseModel):
    task_code: str
    title: str
    max_score: int
    check_type: str
    expected_answer: str | None = None
    test_cases: list[dict] | None = None


class TaskUpdate(BaseModel):
    task_code: str | None = None
    title: str | None = None
    max_score: int | None = None
    check_type: str | None = None
    expected_answer: str | None = None
    test_cases: list[dict] | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_code: str
    title: str
    max_score: int
    check_type: str
    expected_answer: str | None = None
    test_cases: list[dict] | None = None


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    course_name: str | None = None
    group_name: str | None = None
    tasks: list[TaskResponse] = []


class TemplateUploadResponse(BaseModel):
    filename: str | None
    tasks_created: int


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_fio: str
    student_group: str
    status: str
    total_score: int


class SubmissionBriefResult(BaseModel):
    student_fio: str
    student_group: str
    status: str
    total_score: int
    error: str | None = None


class BatchSubmissionResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: list[SubmissionBriefResult]
