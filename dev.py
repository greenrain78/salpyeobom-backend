"""백엔드(FastAPI) + 프론트엔드(Next.js) 를 한 명령으로 띄운다.

사용:
  uv run python dev.py           # 권장 — 백엔드 venv 자동 활성
  python dev.py                  # uv 없이도 동작 (PATH 의 uv 가 사용됨)

Ctrl+C 한 번에 두 프로세스를 모두 정리한다.
한쪽이 먼저 죽으면 다른 쪽도 함께 내린다.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"

BACKEND_CMD = ["uv", "run", "uvicorn", "app.main:app", "--reload"]
FRONTEND_CMD = ["npm", "run", "dev"]

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

ANSI = {
    "BE": "\033[36m",   # cyan
    "FE": "\033[32m",   # green
    "DEV": "\033[35m",  # magenta
    "RESET": "\033[0m",
}


def _enable_windows_ansi() -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return True
    except Exception:
        return False


USE_COLOR = (_enable_windows_ansi() if IS_WINDOWS else sys.stdout.isatty())


def tag(label: str, message: str) -> str:
    if USE_COLOR:
        return f"{ANSI.get(label, '')}[{label}]{ANSI['RESET']} {message}"
    return f"[{label}] {message}"


def stream_output(label: str, proc: subprocess.Popen[bytes]) -> None:
    assert proc.stdout is not None
    for raw in iter(proc.stdout.readline, b""):
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            print(tag(label, line), flush=True)
    proc.stdout.close()


def spawn(label: str, cmd: list[str], cwd: Path) -> subprocess.Popen[bytes]:
    print(tag(label, f"starting: {' '.join(cmd)}  (cwd={cwd.name or cwd})"), flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("FORCE_COLOR", "1")

    common: dict = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "env": env,
    }

    if IS_WINDOWS:
        # cmd.exe 경유로 띄워야 npm.cmd / uv.exe 등 PATH 검색이 정상 동작.
        # CREATE_NEW_PROCESS_GROUP 으로 자체 그룹을 부여해, 부모(이 스크립트)의
        # Ctrl+C 가 자식까지 전파되지 않게 한다. 종료 시에는 우리가 명시적으로
        # CTRL_BREAK_EVENT 를 보낸다.
        return subprocess.Popen(  # noqa: S603
            " ".join(cmd),
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # type: ignore[attr-defined]
            **common,
        )

    # POSIX: 자체 세션으로 분리해 부모의 SIGINT 가 자동으로 자식에 가지 않게 한다.
    return subprocess.Popen(  # noqa: S603
        cmd,
        start_new_session=True,
        **common,
    )


def terminate(label: str, proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    print(tag(label, "stopping..."), flush=True)
    try:
        if IS_WINDOWS:
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    except (ProcessLookupError, OSError):
        pass
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        print(tag(label, "force kill"), flush=True)
        try:
            if IS_WINDOWS:
                proc.kill()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


def main() -> int:
    if not FRONTEND.exists():
        print(f"[FATAL] frontend/ not found at {FRONTEND}", file=sys.stderr)
        return 1
    if not (FRONTEND / "node_modules").exists():
        print(
            tag(
                "DEV",
                "frontend/node_modules 가 없습니다. 먼저 `cd frontend && npm install` 을 실행하세요.",
            ),
            file=sys.stderr,
        )
        return 1

    print(tag("DEV", f"Backend  → {BACKEND_URL}"))
    print(tag("DEV", f"Frontend → {FRONTEND_URL}"))
    print(tag("DEV", "Ctrl+C 한 번으로 두 프로세스를 모두 정리합니다."))

    be = spawn("BE", BACKEND_CMD, ROOT)
    fe = spawn("FE", FRONTEND_CMD, FRONTEND)

    threading.Thread(target=stream_output, args=("BE", be), daemon=True).start()
    threading.Thread(target=stream_output, args=("FE", fe), daemon=True).start()

    exit_code = 0
    try:
        while True:
            if be.poll() is not None:
                print(tag("BE", f"exited (code={be.returncode}) — stopping FE"), flush=True)
                exit_code = be.returncode or 0
                break
            if fe.poll() is not None:
                print(tag("FE", f"exited (code={fe.returncode}) — stopping BE"), flush=True)
                exit_code = fe.returncode or 0
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(tag("DEV", "Ctrl+C 받음 — 두 프로세스를 정리합니다"), flush=True)

    terminate("BE", be)
    terminate("FE", fe)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
