"""
Code Sandbox Tool — execute Python code inside an isolated Docker container.

Security model:
  - No network access (--network=none)
  - Memory capped at 256MB
  - CPU capped at 0.5 cores
  - Read-only filesystem (code injected via volume mount)
  - Container killed at the timeout and always deleted
  - Hard 30-second timeout
"""
import sys
import asyncio
import tempfile
import os
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    SANDBOX_IMAGE,
    SANDBOX_TIMEOUT,
    SANDBOX_MEMORY_LIMIT,
    SANDBOX_CPU_QUOTA,
)

try:
    import docker
    import requests  # installed with the docker SDK
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


async def run_code_sandbox(code: str, language: str = "python") -> dict:
    """
    Execute code in an isolated Docker container.

    Args:
        code:     Python source code string to execute
        language: Currently only "python" is supported

    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "timed_out": bool
        }
    """
    if not DOCKER_AVAILABLE:
        return _failure("docker Python SDK not installed. Run: pip install docker")

    if language.lower() != "python":
        return _failure(f"Language '{language}' not yet supported. Only 'python' is available.")

    # Write code to a temp directory (will be volume-mounted read-only)
    tmp_dir = tempfile.mkdtemp(prefix="sfbox_")
    code_file = os.path.join(tmp_dir, "solution.py")

    try:
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        # _run_container enforces SANDBOX_TIMEOUT itself and kills the container;
        # this outer timeout is only a backstop in case the Docker daemon hangs.
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _run_container, tmp_dir),
                timeout=SANDBOX_TIMEOUT + 30,
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Docker daemon did not respond in time",
                "exit_code": -1,
                "timed_out": True,
            }
        return result

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_container(tmp_dir: str) -> dict:
    """
    Synchronous Docker run — called in thread executor.
    Runs detached so a runaway program can be killed at SANDBOX_TIMEOUT; the
    container is always removed, whatever happens.
    """
    container = None
    try:
        client = docker.from_env()

        # Determine the bind path for the volume
        # On Windows, Docker Desktop requires forward-slash paths
        bind_path = _to_docker_path(tmp_dir)

        container = client.containers.run(
            image=SANDBOX_IMAGE,
            command="python3 /sandbox/solution.py",
            volumes={bind_path: {"bind": "/sandbox", "mode": "ro"}},
            network_mode="none",         # ← ZERO network access
            mem_limit=SANDBOX_MEMORY_LIMIT,
            nano_cpus=SANDBOX_CPU_QUOTA,
            read_only=True,
            tmpfs={"/tmp": "size=64m"},
            detach=True,
        )

        try:
            status = container.wait(timeout=SANDBOX_TIMEOUT)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            container.kill()
            return {
                "success": False,
                "stdout": _logs(container, stdout=True),
                "stderr": f"Execution timed out after {SANDBOX_TIMEOUT} seconds",
                "exit_code": -1,
                "timed_out": True,
            }

        exit_code = status.get("StatusCode", -1)
        stderr = _logs(container, stdout=False)
        container.reload()
        if container.attrs.get("State", {}).get("OOMKilled"):
            stderr = (stderr + f"\nKilled: exceeded the {SANDBOX_MEMORY_LIMIT} memory limit").strip()

        return {
            "success": exit_code == 0,
            "stdout": _logs(container, stdout=True),
            "stderr": stderr,
            "exit_code": exit_code,
            "timed_out": False,
        }

    except docker.errors.ImageNotFound:
        return _failure(
            f"Sandbox image '{SANDBOX_IMAGE}' not found. "
            "Run: docker build -t sovereignforge-sandbox:latest ./sandbox/"
        )

    except Exception as exc:
        return _failure(str(exc))

    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass


def _logs(container, stdout: bool) -> str:
    return container.logs(stdout=stdout, stderr=not stdout).decode("utf-8", errors="replace")


def _failure(message: str) -> dict:
    return {
        "success": False,
        "stdout": "",
        "stderr": message,
        "exit_code": -1,
        "timed_out": False,
    }


def _to_docker_path(win_path: str) -> str:
    """
    Convert Windows path to Docker-compatible path.
    e.g.  C:\\Users\\foo\\tmp  →  C:/Users/foo/tmp
    """
    return win_path.replace("\\", "/")
