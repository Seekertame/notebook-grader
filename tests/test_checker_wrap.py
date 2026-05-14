"""Тесты крайних случаев для wrap_code_with_stdin.

Функция собирает исходный код Python, который подаёт input_data в stdin.
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout

import pytest

from app.grader.checker import wrap_code_with_stdin


def _run(wrapped: str) -> str:
    """Компилирует и исполняет обёрнутый код, возвращает захваченный stdout."""
    compiled = compile(wrapped, "<wrapped>", "exec")
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compiled, {"__name__": "__main__"})
    return buf.getvalue()


ECHO = "print(sys.stdin.read(), end='')"


@pytest.mark.parametrize(
    "input_data",
    [
        "",
        "hello",
        "1\n2\n3\n",
        "привет, мир\n",
        '"double"',
        "'single'",
        '"""triple double"""',
        "'''triple single'''",
        "back\\slash",
        "tab\there\nnewline",
        "mix: \"\\n\"\\\\'''\"\"\"",
        "\x00null\x01ctrl",
        "🚀 emoji + 中文",
    ],
)
def test_wrap_roundtrip(input_data: str):
    wrapped = wrap_code_with_stdin(ECHO, input_data)
    compile(wrapped, "<wrapped>", "exec")
    assert _run(wrapped) == input_data


def test_wrap_does_not_execute_input_as_code():
    malicious = '""")\nimport os\nos.environ["PWNED"] = "1"\n#'
    wrapped = wrap_code_with_stdin(ECHO, malicious)

    sys.modules["os"].environ.pop("PWNED", None)

    out = _run(wrapped)

    assert out == malicious
    assert sys.modules["os"].environ.get("PWNED") is None


def test_wrap_preserves_student_code_verbatim():
    student = "x = 1 + 2\nprint(x)"
    wrapped = wrap_code_with_stdin(student, "irrelevant")
    assert student in wrapped
    assert _run(wrapped) == "3\n"
