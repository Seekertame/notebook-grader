from __future__ import annotations

import pytest

from app.models.schemas import ExecutionStatus

docker = pytest.importorskip("docker")

from app.grader.executor import SANDBOX_IMAGE, run_code_in_sandbox  # noqa: E402


def _docker_ready() -> tuple[bool, str]:
    try:
        client = docker.from_env()
        client.ping()
    except Exception as exc:  # pragma: no cover - зависит от окружения
        return False, f"Docker daemon not reachable: {exc!r}"
    try:
        client.images.get(SANDBOX_IMAGE)
    except docker.errors.ImageNotFound:  # pragma: no cover
        return False, f"Sandbox image '{SANDBOX_IMAGE}' is not built"
    except Exception as exc:  # pragma: no cover
        return False, f"Cannot query sandbox image: {exc!r}"
    return True, ""


_ready, _reason = _docker_ready()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _ready, reason=_reason or "Docker not available"),
]


def test_sandbox_runs_simple_code():
    result = run_code_in_sandbox("print('hello')")

    assert result.status == ExecutionStatus.SUCCESS
    assert result.stdout.strip() == "hello"
    assert result.execution_time < 30


def test_sandbox_fork_bomb_does_not_hang():
    fork_bomb = (
        "import os\n"
        "while True:\n"
        "    try:\n"
        "        os.fork()\n"
        "    except OSError:\n"
        "        pass\n"
    )

    result = run_code_in_sandbox(fork_bomb)

    assert result.execution_time < 60, (
        f"Fork bomb did not terminate in time: {result.execution_time:.1f}s"
    )
    assert result.status in {ExecutionStatus.TIMEOUT, ExecutionStatus.ERROR}, (
        f"Expected fork bomb to fail, got status={result.status}, "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )


def test_sandbox_timeout_terminates_long_running_code():
    result = run_code_in_sandbox("while True:\n    pass\n")

    assert result.status == ExecutionStatus.TIMEOUT
    assert result.execution_time < 60


def test_sandbox_network_is_disabled():
    code = (
        "import socket\n"
        "socket.setdefaulttimeout(3)\n"
        "try:\n"
        "    socket.gethostbyname('example.com')\n"
        "    print('NETWORK_REACHABLE')\n"
        "except OSError:\n"
        "    print('NETWORK_BLOCKED')\n"
    )
    result = run_code_in_sandbox(code)

    assert "NETWORK_BLOCKED" in result.stdout, (
        f"Expected network to be blocked, stdout={result.stdout!r}"
    )
