"""可取消的后台任务：跟踪子进程 + 协作取消标志。"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
from typing import Any

# 约定：取消退出码（与 bash 128+SIGINT 接近）
CANCELLED = 130

_lock = threading.Lock()
_procs: list[Any] = []
_flag = threading.Event()


def begin() -> None:
    """开始新任务前清掉取消标志。"""
    _flag.clear()


def is_cancelled() -> bool:
    return _flag.is_set()


def track(proc: Any) -> None:
    with _lock:
        _procs.append(proc)


def untrack(proc: Any) -> None:
    with _lock:
        if proc in _procs:
            _procs.remove(proc)


def cancel(*, distro: str | None = None) -> None:
    """请求取消：置标志、终止已跟踪子进程；可选结束整个 WSL 发行版会话。"""
    _flag.set()
    with _lock:
        procs = list(_procs)
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass
    if distro and shutil.which("wsl"):
        flags: dict = {}
        if os.name == "nt":
            flags["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            subprocess.run(
                ["wsl", "--terminate", distro],
                capture_output=True,
                timeout=15,
                **flags,
            )
        except Exception:
            pass
