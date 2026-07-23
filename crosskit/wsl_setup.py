"""检测并启用 WSL2（导入环境包前的傻瓜式准备）。"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from . import wsl


def _hidden() -> dict:
    return wsl._hidden_kwargs()


def wsl_usable() -> bool:
    """WSL 已可用（允许尚无任何发行版）。"""
    if not shutil.which("wsl"):
        return False
    try:
        r = subprocess.run(
            ["wsl", "-l", "-v"],
            capture_output=True,
            timeout=90,
            **_hidden(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    text = _decode(r.stdout) + "\n" + _decode(r.stderr)
    low = text.lower()
    blockers = (
        "not installed",
        "not enabled",
        "must be enabled",
        "没有安装",
        "未启用",
        "无法解析",
        "error code: 0x80070002",
        "error code: 0x8007007e",
    )
    if any(b in low for b in blockers):
        return False
    # 无发行版时也会打出提示，仍视为可用（可直接 --import）
    return True


def ensure_wsl(*, on_line=None) -> tuple[str, str]:
    """确保本机可跑 wsl --import。

    返回 (状态, 说明)：
      ready / needs_reboot / cancelled / failed
    """
    if wsl_usable():
        _try_set_default_version(on_line)
        return "ready", "WSL 已就绪"

    if on_line:
        on_line("[wsl] 未检测到可用的 WSL，将请求管理员权限自动启用…")

    script = _enable_script()
    code = _run_elevated_ps1(script, on_line=on_line)
    if code == 1223:  # ERROR_CANCELLED
        return "cancelled", "已取消管理员授权，无法启用 WSL"
    if code not in (0, None) and code != 3010:
        # 3010 = ERROR_SUCCESS_REBOOT_REQUIRED（部分环境）
        if on_line:
            on_line(f"[wsl] 启用命令退出码={code}，继续检测…")

    # 功能刚打开时可能稍延迟
    for i in range(6):
        if wsl_usable():
            _try_set_default_version(on_line)
            return "ready", "WSL 已启用"
        time.sleep(1.5)
        if on_line and i == 2:
            on_line("[wsl] 等待 WSL 生效…")

    if on_line:
        on_line("[wsl] 功能已尝试启用，但当前仍不可用，通常需要重启 Windows 一次。")
    return "needs_reboot", "请重启电脑，然后重新打开本工具继续导入"


def _try_set_default_version(on_line=None) -> None:
    try:
        r = subprocess.run(
            ["wsl", "--set-default-version", "2"],
            capture_output=True,
            timeout=60,
            **_hidden(),
        )
        if on_line and r.returncode == 0:
            on_line("[wsl] 默认版本已设为 WSL2")
    except (OSError, subprocess.TimeoutExpired):
        pass


def _enable_script() -> str:
    # 不安装 Ubuntu：我们用自己的环境包 import
    return r"""
$ErrorActionPreference = 'Continue'
$log = Join-Path $env:TEMP 'qt-arm64-cross-wsl-enable.log'
function L([string]$m) { Add-Content -Path $log -Value $m -Encoding UTF8; Write-Output $m }

L '[wsl] 开始启用 WSL / 虚拟机平台…'

# 新系统优先：不附带发行版
try {
  $out = & wsl.exe --install --no-distribution 2>&1 | Out-String
  L $out
} catch {
  L ("[wsl] wsl --install 异常: " + $_)
}

# 兜底：DISM 可选功能（无需重启参数，由调用方判断）
try {
  $f1 = Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All -NoRestart
  L ("[wsl] Microsoft-Windows-Subsystem-Linux State=" + $f1.State + " RestartNeeded=" + $f1.RestartNeeded)
} catch { L ("[wsl] 启用 WSL 功能失败: " + $_) }
try {
  $f2 = Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
  L ("[wsl] VirtualMachinePlatform State=" + $f2.State + " RestartNeeded=" + $f2.RestartNeeded)
} catch { L ("[wsl] 启用虚拟机平台失败: " + $_) }

try {
  & wsl.exe --set-default-version 2 2>&1 | ForEach-Object { L $_ }
} catch {}

L '[wsl] 启用步骤结束'
exit 0
"""


def _run_elevated_ps1(script: str, on_line=None) -> int:
    """弹出 UAC，以管理员跑一段 PowerShell。取消授权约返回 1223。"""
    fd, path = tempfile.mkstemp(prefix="qtarm64-wsl-", suffix=".ps1")
    os.close(fd)
    ps1 = Path(path)
    try:
        ps1.write_text(script, encoding="utf-8-sig")
        # 外层不提升；内层 Start-Process -Verb RunAs
        wrapper = (
            f"$p = Start-Process -FilePath 'powershell.exe' "
            f"-ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','{ps1}') "
            f"-Verb RunAs -Wait -PassThru; "
            f"if ($null -eq $p) {{ exit 1223 }}; exit $p.ExitCode"
        )
        if on_line:
            on_line("[wsl] 请在弹出的 UAC 窗口点「是」…")
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", wrapper],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            **_hidden(),
        )
        if on_line:
            for line in (r.stdout or "").splitlines():
                if line.strip():
                    on_line(line.rstrip())
            log = Path(os.environ.get("TEMP", ".")) / "qt-arm64-cross-wsl-enable.log"
            if log.is_file():
                try:
                    for line in log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]:
                        on_line(line)
                except OSError:
                    pass
        return int(r.returncode)
    except subprocess.TimeoutExpired:
        if on_line:
            on_line("[wsl] 启用超时")
        return 1
    except OSError as e:
        if on_line:
            on_line(f"[wsl] 无法启动提升进程: {e}")
        return 1
    finally:
        ps1.unlink(missing_ok=True)


def _decode(data: bytes | None) -> str:
    if not data:
        return ""
    for enc in ("utf-16-le", "utf-8"):
        try:
            return data.decode(enc).replace("\x00", "")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
