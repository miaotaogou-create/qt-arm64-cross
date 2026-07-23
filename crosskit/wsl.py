"""WSL 调用与路径转换。"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


DEFAULT_DISTRO = "Ubuntu-20.04"


def _hidden_kwargs() -> dict:
    """Windows 下隐藏黑框控制台（GUI 调 wsl/netsh 时）。"""
    if os.name != "nt":
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return {"creationflags": flags, "stdin": subprocess.DEVNULL}


def win_to_wsl(path: str | Path) -> str:
    """C:\\foo\\bar → /mnt/c/foo/bar"""
    p = Path(path).resolve()
    s = str(p).replace("\\", "/")
    if len(s) >= 2 and s[1] == ":":
        return f"/mnt/{s[0].lower()}{s[2:]}"
    return s


def wsl_available() -> bool:
    return shutil.which("wsl") is not None


def distro_exists(distro: str = DEFAULT_DISTRO) -> bool:
    if not wsl_available():
        return False
    r = subprocess.run(
        ["wsl", "-l", "-q"],
        capture_output=True,
        text=True,
        encoding="utf-16-le",
        errors="replace",
        **_hidden_kwargs(),
    )
    # wsl -l 在部分环境是 utf-16；再兜底 utf-8
    names = r.stdout.replace("\x00", "")
    if distro not in names:
        r2 = subprocess.run(["wsl", "-l", "-q"], capture_output=True, **_hidden_kwargs())
        names = r2.stdout.decode("utf-16-le", errors="replace").replace("\x00", "")
        if distro not in names:
            names = r2.stdout.decode("utf-8", errors="replace")
    return distro in names


def run_wsl(
    cmd: str,
    *,
    distro: str = DEFAULT_DISTRO,
    user: str | None = None,
    env: dict[str, str] | None = None,
    on_line=None,
) -> int:
    """在 WSL 中执行 bash -lc。on_line(line) 流式回调。返回退出码。"""
    args = ["wsl", "-d", distro]
    if user:
        args += ["-u", user]
    export = ""
    if env:
        parts = []
        for k, v in env.items():
            # 单引号包裹，内部单引号转义
            safe = str(v).replace("'", "'\"'\"'")
            parts.append(f"export {k}='{safe}'")
        export = " && ".join(parts) + " && "
    full = f"{export}{cmd}"
    args += ["bash", "-lc", full]

    # 子进程环境：避免 Python UTF-8 与控制台乱码
    proc_env = os.environ.copy()
    proc_env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=proc_env,
        bufsize=1,
        **_hidden_kwargs(),
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        if on_line:
            on_line(line.rstrip("\n"))
    return proc.wait()
