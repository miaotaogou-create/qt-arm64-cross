"""环境检测与安装命令提示。"""
from __future__ import annotations

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

    @property
    def ready(self) -> bool:
        need = {"cross_gpp", "rootfs", "qt_widgets", "qt_qmake"}
        got = {i.key for i in self.items if i.ok}
        return self.distro_ok and need <= got


def toolkit_root() -> Path:
    return Path(__file__).resolve().parent.parent


def detect(distro: str = wsl.DEFAULT_DISTRO) -> EnvReport:
    items: list[CheckItem] = []
    if not wsl.wsl_available():
        return EnvReport(
            False,
            [CheckItem("wsl", "WSL", False, "安装 Windows 功能「适用于 Linux 的 Windows 子系统」")],
        )
    if not wsl.distro_exists(distro):
        return EnvReport(
            False,
            [CheckItem("distro", f"发行版 {distro}", False, f"wsl --install -d {distro}")],
        )

    tk = wsl.win_to_wsl(toolkit_root())
    lines: list[str] = []
    code = wsl.run_wsl(
        f"sed -i 's/\\r$//' '{tk}/tools/env_check.sh' && bash '{tk}/tools/env_check.sh'",
        distro=distro,
        on_line=lines.append,
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
        "rootfs": f"sysroot {parsed.get('rootfs_codename', '/opt/arm64-rootfs')}",
        "rootfs_glibc": "sysroot 为 focal",
        "qt_widgets": "Qt 目标库 libQt5Widgets",
        "qt_qmake": "主机 qmake",
        "qt_moc": "主机 moc",
        "qt_xcb": "qxcb 插件",
    }
    for key, label in labels.items():
        val = parsed.get(key, "missing")
        items.append(
            CheckItem(key, label, val == "ok", fixes.get(key, ""))
        )

    if code != 0 and not items:
        items.append(CheckItem("env_check", "env_check.sh", False, "检查 WSL 是否可执行 bash"))

    return EnvReport(True, items)
