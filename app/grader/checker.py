import logging
from collections.abc import Callable

from app.models.schemas import (
    CheckType,
    ExecutionResult,
    ExecutionStatus,
    TaskConfig,
    TaskGradingResult,
)

logger = logging.getLogger(__name__)

MAX_EXPLANATION_CHARS = 300


def wrap_code_with_stdin(code: str, input_data: str) -> str:
    return (
        "import sys, io\n"
        f"sys.stdin = io.StringIO({input_data!r})\n"
        f"{code}"
    )


def _values_match(actual: str, expected: str) -> bool:
    actual = actual.rstrip()
    expected = expected.rstrip()

    try:
        # вещественные числа сравниваются с точностью до 4 знаков после запятой
        return round(float(actual), 4) == round(float(expected), 4)
    except ValueError:
        return actual == expected


def _truncate_stderr(stderr: str) -> str:
    text = stderr.strip()
    if len(text) > MAX_EXPLANATION_CHARS:
        return "…" + text[-MAX_EXPLANATION_CHARS:]
    return text


def _execution_failed(result: ExecutionResult) -> TaskGradingResult | None:
    if result.status == ExecutionStatus.TIMEOUT:
        explanation = _truncate_stderr(result.stderr) or "Превышено время выполнения"
        logger.error("Task execution timed out. stderr:\n%s", result.stderr)
        return TaskGradingResult(
            task_code="",
            awarded_points=0,
            status="тайм-аут",
            explanation=explanation,
        )
    if result.status == ExecutionStatus.ERROR:
        explanation = _truncate_stderr(result.stderr)
        logger.error("Task execution error. stderr:\n%s", result.stderr)
        return TaskGradingResult(
            task_code="",
            awarded_points=0,
            status="ошибка выполнения",
            explanation=explanation,
        )
    return None


def _grade_by_answer(
    code: str,
    config: TaskConfig,
    executor_func: Callable[[str], ExecutionResult],
) -> TaskGradingResult:
    result = executor_func(code)

    failure = _execution_failed(result)
    if failure is not None:
        failure.task_code = config.task_code
        return failure

    if config.expected_answer is None:
        return TaskGradingResult(
            task_code=config.task_code,
            awarded_points=0,
            status="не настроен эталонный ответ",
            explanation=f"stdout: {result.stdout.rstrip()!r}",
        )

    if _values_match(result.stdout, config.expected_answer):
        return TaskGradingResult(
            task_code=config.task_code,
            awarded_points=config.max_score,
            status="успешно",
        )

    return TaskGradingResult(
        task_code=config.task_code,
        awarded_points=0,
        status="несоответствие ожидаемому результату",
        explanation=(
            f"Ожидалось: {config.expected_answer!r}, "
            f"получено: {result.stdout.rstrip()!r}"
        ),
    )


def _grade_by_tests(
    code: str,
    config: TaskConfig,
    executor_func: Callable[[str], ExecutionResult],
) -> TaskGradingResult:
    if not config.test_cases:
        return TaskGradingResult(
            task_code=config.task_code,
            awarded_points=0,
            status="не настроены тест-кейсы",
        )

    for i, test in enumerate(config.test_cases, start=1):
        wrapped = wrap_code_with_stdin(code, test.input_data)
        result = executor_func(wrapped)

        failure = _execution_failed(result)
        if failure is not None:
            failure.task_code = config.task_code
            failure.explanation = f"Тест {i}: {failure.explanation}"
            return failure

        if not _values_match(result.stdout, test.expected_output):
            return TaskGradingResult(
                task_code=config.task_code,
                awarded_points=0,
                status="несоответствие ожидаемому результату",
                explanation=(
                    f"Тест {i}: ожидалось {test.expected_output.rstrip()!r}, "
                    f"получено {result.stdout.rstrip()!r}"
                ),
            )

    return TaskGradingResult(
        task_code=config.task_code,
        awarded_points=config.max_score,
        status="успешно",
    )


def _grade_by_reference_assert(
    code: str,
    config: TaskConfig,
    executor_func: Callable[[str], ExecutionResult],
) -> TaskGradingResult:
    if not config.reference_code:
        return TaskGradingResult(
            task_code=config.task_code,
            awarded_points=0,
            status="не настроен проверочный код",
        )

    final_code = code + "\n\n" + config.reference_code
    result = executor_func(final_code)

    failure = _execution_failed(result)
    if failure is not None:
        failure.task_code = config.task_code
        return failure

    return TaskGradingResult(
        task_code=config.task_code,
        awarded_points=config.max_score,
        status="успешно",
    )


_SYSTEM_SETUP = "def display(*args, **kwargs): print(*args)\n\n"


def _prepend_setup(setup_code: str, code: str) -> str:
    parts = [_SYSTEM_SETUP]
    if setup_code:
        parts.append(setup_code)
    parts.append("# --- код студента ниже ---")
    parts.append(code)
    return "\n".join(parts)


def grade_task(
    code: str,
    config: TaskConfig,
    executor_func: Callable[[str], ExecutionResult],
    setup_code: str = "",
) -> TaskGradingResult:
    full_code = _prepend_setup(setup_code, code)
    if config.check_type == CheckType.ANSWER:
        return _grade_by_answer(full_code, config, executor_func)
    if config.check_type == CheckType.REFERENCE_ASSERT:
        return _grade_by_reference_assert(full_code, config, executor_func)
    return _grade_by_tests(full_code, config, executor_func)
