"""环境检测与安装命令提示。"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import wsl


@dataclass
class CheckItem:
    key: str
    label: str
    ok: bool
    fix: str = ""


@dataclass
class EnvReport:
    distro_ok: bool
    items: list[CheckItem] = field(default_factory=list)
    facts: dict[str, str] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        # 含 qxcb：缺平台插件时客户机窗口起不来，不能算就绪
        need = {"cross_gpp", "rootfs", "qt_widgets", "qt_qmake", "qt_xcb"}
        got = {i.key for i in self.items if i.ok}
        return self.distro_ok and need <= got


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _cache_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return base / "QtArm64Cross" / "toolkit"


def _tools_stamp(src_tools: Path, extra: str = "") -> str:
    """用源 tools 内容时间戳（或 exe）决定是否刷新本地缓存。"""
    times: list[int] = []
    if src_tools.is_dir():
        for p in src_tools.rglob("*"):
            if p.is_file():
                try:
                    times.append(p.stat().st_mtime_ns)
                except OSError:
                    pass
    body = f"{extra}|{max(times) if times else 0}|{len(times)}"
    return body


def _copy_tools_lf(src: Path, dst: Path) -> None:
    """拷贝 tools，并把常见文本转为 LF，避免 WSL bash 踩 CRLF。"""
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True, exist_ok=True)
    text_suffix = {".sh", ".cmake", ".conf", ".py", ".txt", ".md", ".in", ".pri", ".prl"}
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        out = dst / rel
        if path.is_dir():
            out.mkdir(parents=True, exist_ok=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() in text_suffix or path.name in {"qmake.conf", "qplatformdefs.h"}:
            data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            out.write_bytes(data)
        else:
            shutil.copy2(path, out)


def toolkit_root() -> Path:
    """工具根目录（含 tools/）。

    绿色 exe / 开发态都镜像到 %LOCALAPPDATA%\\QtArm64Cross\\toolkit，
    统一 LF，且不 sed 改仓库或 _MEIPASS 里的脚本。
    """
    if getattr(sys, "frozen", False):
        mei = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        src_tools = mei / "tools"
        extra = ""
        try:
            exe = Path(sys.executable)
            st = exe.stat()
            extra = f"exe:{st.st_mtime_ns}:{st.st_size}"
        except OSError:
            extra = "exe:0"
    else:
        src_tools = _repo_root() / "tools"
        extra = "dev"

    if not src_tools.is_dir():
        return _repo_root() if not getattr(sys, "frozen", False) else Path(
            getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)
        )

    cache = _cache_root()
    dst_tools = cache / "tools"
    marker = cache / ".ready"
    stamp = _tools_stamp(src_tools, extra)
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8", errors="replace").strip() == stamp
        and (dst_tools / "cross_build.sh").is_file()
        and (dst_tools / "env_check.sh").is_file()
    ):
        return cache

    cache.mkdir(parents=True, exist_ok=True)
    _copy_tools_lf(src_tools, dst_tools)
    marker.write_text(stamp + "\n", encoding="utf-8")
    return cache


def detect(distro: str = wsl.DEFAULT_DISTRO, on_line=None) -> EnvReport:
    items: list[CheckItem] = []
    if on_line:
        on_line("[detect] 检查 WSL…")
    if not wsl.wsl_available():
        return EnvReport(
            False,
            [CheckItem("wsl", "WSL", False, "安装 Windows 功能「适用于 Linux 的 Windows 子系统」")],
        )
    if on_line:
        on_line(f"[detect] 检查发行版 {distro}…")
    if not wsl.distro_exists(distro):
        return EnvReport(
            False,
            [CheckItem("distro", f"发行版 {distro}", False, f"wsl --install -d {distro}")],
        )

    tk = wsl.win_to_wsl(toolkit_root())
    lines: list[str] = []

    def _cap(line: str) -> None:
        lines.append(line)
        if on_line:
            on_line(line)

    if on_line:
        on_line("[detect] 在 WSL 中执行 env_check.sh…")
    code = wsl.run_wsl(
        f"bash '{tk}/tools/env_check.sh'",
        distro=distro,
        on_line=_cap,
    )
    parsed: dict[str, str] = {}
    for line in lines:
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k.strip()] = v.strip()

    fixes = {
        "cross_gpp": f"wsl -d {distro} -u root bash {tk}/tools/setup_cross_focal.sh",
        "rootfs": f"wsl -d {distro} -u root bash {tk}/tools/setup_cross_focal.sh",
        "rootfs_glibc": f"wsl -d {distro} -u root bash {tk}/tools/ensure_focal_rootfs.sh",
        "qt_widgets": f"wsl -d {distro} -u root bash {tk}/tools/build_qt5142_arm64_cross.sh",
        "qt_qmake": f"wsl -d {distro} -u root bash {tk}/tools/build_qt5142_arm64_cross.sh",
        "qt_moc": f"wsl -d {distro} -u root bash {tk}/tools/build_qt5142_arm64_cross.sh",
        "qt_xcb": f"wsl -d {distro} -u root bash {tk}/tools/update_sysroot_xcb_deps.sh && "
        f"wsl -d {distro} -u root bash {tk}/tools/build_qt5142_arm64_cross.sh",
    }
    labels = {
        "cross_gpp": "交叉编译器 aarch64-linux-gnu-g++",
        "cross_readelf": "readelf",
        "pkg_config": "pkg-config",
        "cmake_bin": "cmake（仅 CMake 工程需要）",
        "ccache_bin": "ccache",
        "rootfs": f"sysroot {parsed.get('rootfs_codename', '/opt/arm64-rootfs')}",
        "rootfs_glibc": "sysroot 为 focal",
        "qt_widgets": "Qt 目标库 libQt5Widgets",
        "qt_qmake": "主机 qmake",
        "qt_moc": "主机 moc",
        "qt_xcb": "qxcb 插件",
    }
    for key, label in labels.items():
        val = parsed.get(key, "missing")
        items.append(CheckItem(key, label, val == "ok", fixes.get(key, "")))

    if code != 0 and not items:
        items.append(CheckItem("env_check", "env_check.sh", False, "检查 WSL 是否可执行 bash"))

    return EnvReport(True, items, facts=parsed)
