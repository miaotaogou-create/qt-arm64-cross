"""WSL 交叉编译环境的导出 / 导入（发给同事：exe + 环境包）。"""
from __future__ import annotations

import gzip
import os
import shutil
import subprocess
from pathlib import Path

from . import wsl, wsl_setup


def run_stream(args: list[str], on_line=None) -> int:
    """跑 Windows 命令并流式输出。"""
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
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        if on_line:
            on_line(line.rstrip("\n"))
    return proc.wait()


def slim_build_cache(distro: str = wsl.DEFAULT_DISTRO, on_line=None) -> int:
    """删除 /opt/qt5142-cross（仅 Qt 源码与编译缓存，不影响已安装前缀）。"""
    if on_line:
        on_line("[env] 删除 /opt/qt5142-cross …")
    return wsl.run_wsl(
        "rm -rf /opt/qt5142-cross && echo '[env] qt5142-cross 已删除' && df -h / | tail -1",
        distro=distro,
        user="root",
        on_line=on_line,
    )


def export_distro(
    dest: str | Path,
    *,
    distro: str = wsl.DEFAULT_DISTRO,
    slim: bool = False,
    compress: bool = True,
    on_line=None,
) -> int:
    """导出发行版为 .tar 或 .tar.gz。默认完整导出（含已装 Qt/FFmpeg/sysroot）。"""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not wsl.wsl_available():
        if on_line:
            on_line("[env] 未找到 wsl 命令")
        return 1
    if not wsl.distro_exists(distro):
        if on_line:
            on_line(f"[env] 发行版不存在: {distro}")
        return 1

    if slim:
        code = slim_build_cache(distro, on_line=on_line)
        if code != 0:
            return code

    name = dest.name.lower()
    if name.endswith(".tar.gz"):
        gz_path = dest
        tar_path = dest.with_name(dest.name[:-3])  # xxx.tar.gz → xxx.tar
    elif name.endswith(".tar"):
        tar_path = dest
        gz_path = Path(str(dest) + ".gz")
    else:
        tar_path = Path(str(dest) + ".tar")
        gz_path = Path(str(dest) + ".tar.gz")

    if on_line:
        on_line(f"[env] 导出 {distro} → {tar_path} （可能数 GB，请耐心等待）")
    code = run_stream(["wsl", "--export", distro, str(tar_path)], on_line=on_line)
    if code != 0:
        return code
    if not tar_path.is_file():
        if on_line:
            on_line("[env] 导出失败：未生成 tar")
        return 1

    mb = tar_path.stat().st_size / (1024 * 1024)
    if on_line:
        on_line(f"[env] tar 完成: {tar_path} ({mb:.1f} MB)")

    if compress:
        if on_line:
            on_line(f"[env] 压缩 → {gz_path}")
        with tar_path.open("rb") as fin, gzip.open(gz_path, "wb", compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout, length=1024 * 1024 * 8)
        tar_path.unlink(missing_ok=True)
        mb = gz_path.stat().st_size / (1024 * 1024)
        if on_line:
            on_line(f"[env] 环境包就绪: {gz_path} ({mb:.1f} MB)")
            on_line("[env] 发给同事: QtArm64Cross.exe + 本环境包；对方点「导入环境包」即可")
    else:
        if on_line:
            on_line(f"[env] 环境包就绪: {tar_path}")
    return 0


def import_distro(
    archive: str | Path,
    install_dir: str | Path,
    *,
    distro: str = wsl.DEFAULT_DISTRO,
    replace: bool = False,
    set_default: bool = True,
    auto_enable_wsl: bool = True,
    on_line=None,
) -> int:
    """从 .tar / .tar.gz 导入发行版。

    返回码：0 成功；2 需重启后再导入；其它失败。
    """
    archive = Path(archive)
    install_dir = Path(install_dir)
    if not archive.is_file():
        if on_line:
            on_line(f"[env] 找不到环境包: {archive}")
        return 1

    if auto_enable_wsl:
        st, msg = wsl_setup.ensure_wsl(on_line=on_line)
        if st == "needs_reboot":
            if on_line:
                on_line(f"[env] {msg}")
            return 2
        if st != "ready":
            if on_line:
                on_line(f"[env] {msg}")
            return 1
    elif not wsl_setup.wsl_usable():
        if on_line:
            on_line("[env] WSL 不可用。请点导入以自动启用，或手动执行: wsl --install --no-distribution")
        return 1

    if wsl.distro_exists(distro):
        if not replace:
            if on_line:
                on_line(f"[env] 发行版已存在: {distro}。勾选「覆盖已有」或先卸载。")
            return 1
        if on_line:
            on_line(f"[env] 注销已有发行版 {distro} …")
        code = run_stream(["wsl", "--unregister", distro], on_line=on_line)
        if code != 0:
            return code

    install_dir.mkdir(parents=True, exist_ok=True)
    tar_path = archive
    tmp_tar: Path | None = None
    name = archive.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        tmp_tar = install_dir / "_import_tmp.tar"
        if on_line:
            on_line(f"[env] 解压 {archive.name} …")
        with gzip.open(archive, "rb") as fin, tmp_tar.open("wb") as fout:
            shutil.copyfileobj(fin, fout, length=1024 * 1024 * 8)
        tar_path = tmp_tar

    if on_line:
        on_line(f"[env] 导入为 {distro} → {install_dir}")
    code = run_stream(
        ["wsl", "--import", distro, str(install_dir), str(tar_path), "--version", "2"],
        on_line=on_line,
    )
    if tmp_tar is not None:
        tmp_tar.unlink(missing_ok=True)
    if code != 0:
        return code

    if set_default:
        if on_line:
            on_line(f"[env] 设为默认发行版: {distro}")
        run_stream(["wsl", "--set-default", distro], on_line=on_line)

    if on_line:
        on_line("[env] 导入完成。请点「检测环境」确认工具链与 Qt。")
    return 0
