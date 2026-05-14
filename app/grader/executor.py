import logging
import time

import docker
from docker.errors import APIError

from app.models.schemas import ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "notebook-grader-sandbox"
TIMEOUT_SECONDS = 30
MEMORY_LIMIT = "1g"
PIDS_LIMIT = 64
NOFILE_LIMIT = 256


def run_code_in_sandbox(code: str) -> ExecutionResult:
    client = docker.from_env()

    container = None
    start = time.monotonic()

    try:
        container = client.containers.run(
            image=SANDBOX_IMAGE,
            command=["python", "-c", code],
            user="student",
            network_disabled=True,
            mem_limit=MEMORY_LIMIT,
            nano_cpus=1_000_000_000,
            pids_limit=PIDS_LIMIT,
            read_only=True,
            tmpfs={"/tmp": "size=64m,mode=1777"},
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
            ulimits=[
                docker.types.Ulimit(name="nofile", soft=NOFILE_LIMIT, hard=NOFILE_LIMIT)
            ],
            detach=True,
            stderr=True,
        )

        try:
            result = container.wait(timeout=TIMEOUT_SECONDS)
            elapsed = time.monotonic() - start

            stdout = container.logs(stdout=True, stderr=False).decode()
            stderr = container.logs(stdout=False, stderr=True).decode()

            exit_code = result.get("StatusCode", -1)
            status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.ERROR

            if status == ExecutionStatus.ERROR:
                logger.error("Sandbox process failed (exit code %d):\n%s", exit_code, stderr)

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                status=status,
                execution_time=elapsed,
            )

        except (ConnectionError, TimeoutError, APIError):
            # истёк лимит TIMEOUT_SECONDS - принудительно останавливаем контейнер
            elapsed = time.monotonic() - start
            container.stop(timeout=0)

            stdout = container.logs(stdout=True, stderr=False).decode()
            stderr = container.logs(stdout=False, stderr=True).decode()

            logger.error("Sandbox timeout (%.1fs):\n%s", elapsed, stderr)

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                status=ExecutionStatus.TIMEOUT,
                execution_time=elapsed,
            )

    finally:
        if container is not None:
            container.remove(force=True)
