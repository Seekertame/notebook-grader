from pydantic import BaseModel, ConfigDict, Field, model_validator

_TESTS_REQUIRED_MSG = "Для задачи типа 'по набору тестов' необходим минимум один тест-кейс"


class AssignmentCreate(BaseModel):
    title: str
    course_name: str | None = None
    group_name: str | None = None


class AssignmentUpdate(BaseModel):
    title: str | None = None
    course_name: str | None = None
    group_name: str | None = None


class TaskCreate(BaseModel):
    task_code: str = Field(min_length=1, max_length=50)
    title: str
    max_score: int
    check_type: str
    expected_answer: str | None = None
    test_cases: list[dict] | None = None
    reference_code: str | None = None

    @model_validator(mode="after")
    def _validate_tests_have_cases(self):
        if self.check_type == "tests":
            if self.test_cases is None or len(self.test_cases) < 1:
                raise ValueError(_TESTS_REQUIRED_MSG)
        return self


class TaskUpdate(BaseModel):
    task_code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = None
    max_score: int | None = None
    check_type: str | None = None
    expected_answer: str | None = None
    test_cases: list[dict] | None = None
    reference_code: str | None = None

    @model_validator(mode="after")
    def _validate_tests_have_cases(self):
        provided = self.model_fields_set
        if "check_type" in provided and "test_cases" in provided and self.check_type == "tests":
            if self.test_cases is None or len(self.test_cases) < 1:
                raise ValueError(_TESTS_REQUIRED_MSG)
        return self


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_code: str
    title: str
    max_score: int
    check_type: str
    expected_answer: str | None = None
    test_cases: list[dict] | None = None
    reference_code: str | None = None


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
    grade: int


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
