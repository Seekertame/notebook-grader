from enum import Enum

from pydantic import BaseModel


class StudentInfo(BaseModel):
    fio: str
    group: str


class TaskCell(BaseModel):
    task_code: str
    source: str


class ParsedNotebook(BaseModel):
    student: StudentInfo | None
    tasks: list[TaskCell]
    setup_code: str = ""


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    status: ExecutionStatus
    execution_time: float


class CheckType(str, Enum):
    ANSWER = "answer"
    TESTS = "tests"
    REFERENCE_ASSERT = "reference_assert"


class TestCase(BaseModel):
    input_data: str
    expected_output: str


class TaskConfig(BaseModel):
    task_code: str
    max_score: int
    check_type: CheckType
    expected_answer: str | None = None
    test_cases: list[TestCase] | None = None
    reference_code: str | None = None


class TaskGradingResult(BaseModel):
    task_code: str
    awarded_points: int
    status: str
    explanation: str | None = None


class StudentWorkResult(BaseModel):
    student: StudentInfo
    task_results: list[TaskGradingResult]
    total_score: int
