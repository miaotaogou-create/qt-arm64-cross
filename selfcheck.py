#!/usr/bin/env python3
"""最小自检：路径转换与构建设置拼装（不连 WSL）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from crosskit import detect
from crosskit.build import discover_build_files, merge_extra_pkgconfig
from crosskit.httpshare import DirectoryShare, best_lan_ipv4, ethernet_ipv4, lan_ipv4
from crosskit.netip import mask_to_prefix
from crosskit.wsl import parse_distro_names, win_to_wsl
from crosskit import envpack
from crosskit.app_version import VERSION


def main() -> None:
    w = win_to_wsl(r"C:\ZYL\workspace\projects\qt-arm64-cross")
    assert w == r"/mnt/c/ZYL/workspace/projects/qt-arm64-cross", w
    # tools 镜像到 LocalAppData，根下应有 cross_build.sh
    tk = detect.toolkit_root()
    assert (tk / "tools" / "cross_build.sh").is_file(), tk
    assert (tk / "tools" / "env_check.sh").is_file(), tk

    # 发行版名按行精确匹配，避免 Ubuntu-20.04 误中 Ubuntu-20.04-backup
    names = parse_distro_names("Ubuntu-20.04\r\nUbuntu-20.04-backup\n")
    assert names == {"Ubuntu-20.04", "Ubuntu-20.04-backup"}, names
    assert "Ubuntu-20.04" in names
    assert "Ubuntu" not in names
    assert parse_distro_names("Ubuntu-20.04\x00\n") == {"Ubuntu-20.04"}

    assert VERSION
    free = envpack.free_bytes(ROOT)
    assert free is None or free > 0
    need = envpack.estimate_import_need_bytes(ROOT / "README.md")
    assert need >= 2 * 1024**3

    from crosskit import jobs as jobsmod

    assert jobsmod.CANCELLED == 130
    jobsmod.begin()
    assert not jobsmod.is_cancelled()
    jobsmod.cancel()
    assert jobsmod.is_cancelled()
    jobsmod.begin()
    assert not jobsmod.is_cancelled()

    qfiles = discover_build_files(ROOT / "examples" / "hello_qmake")
    assert any(k == "qmake" and p.endswith(".pro") for k, p in qfiles), qfiles

    cfiles = discover_build_files(ROOT / "examples" / "hello_cmake")
    assert any(k == "cmake" for k, p in cfiles), cfiles

    assert merge_extra_pkgconfig(False, "") == ""
    assert "libavcodec" in merge_extra_pkgconfig(True, "")
    assert merge_extra_pkgconfig(True, "libfoo").endswith("libfoo")

    assert mask_to_prefix("255.255.255.0") == 24
    assert mask_to_prefix("24") == 24
    assert mask_to_prefix("/16") == 16
    try:
        mask_to_prefix("255.0.255.0")
        raise AssertionError("expected invalid mask")
    except ValueError:
        pass

    assert isinstance(lan_ipv4(), list)
    assert best_lan_ipv4()
    eth = ethernet_ipv4()
    assert isinstance(eth, list)
    if eth:
        assert best_lan_ipv4() in eth
    share = DirectoryShare()
    share.start(ROOT, 18765)
    try:
        assert share.running
        assert share.urls()
        assert share.primary_url().startswith("http://")
        assert share.primary_url().count("\n") == 0
        assert share.local_url() == "http://127.0.0.1:18765/"
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:18765/README.md", timeout=3) as r:
            assert b"Qt" in r.read(200)
    finally:
        share.stop()
    assert not share.running

    from PySide6.QtWidgets import QApplication
    from gui.env_panel import DISTRO_PRESETS, ToolchainSpecsCard
    from crosskit import netip as netipmod

    assert DISTRO_PRESETS[0]["name"] == "Ubuntu-20.04"
    assert DISTRO_PRESETS[0]["supported"] == "1"
    assert DISTRO_PRESETS[2]["name"] == "Kylin-ARM64-SDK"
    assert DISTRO_PRESETS[2]["supported"] == "0"
    assert all(p["name"] != "Kirin-ARM64-SDK" for p in DISTRO_PRESETS)

    helper = netipmod._HELPER_PS1.format(dir=r"C:\Temp\qtarm64-netip-helper", ppid=1234)
    assert r"C:\Temp\qtarm64-netip-helper" in helper
    assert "{dir}" not in helper
    assert "$ppid = 1234" in helper
    report = detect.EnvReport(
        True,
        [
            detect.CheckItem("qt_widgets", "Qt", True),
            detect.CheckItem("rootfs", "sysroot", True),
            detect.CheckItem("cross_readelf", "r", True),
            detect.CheckItem("pkg_config", "p", True),
            detect.CheckItem("ccache_bin", "c", True),
        ],
        facts={
            "gcc_ver": "9.4.0",
            "gcc_machine": "aarch64-linux-gnu",
            "qt_version": "5.14.2",
            "rootfs_path": "/opt/arm64-rootfs",
            "rootfs_codename": "focal",
        },
    )
    assert report.facts["gcc_ver"] == "9.4.0"

    qapp = QApplication.instance() or QApplication([])
    assert qapp is not None
    card = ToolchainSpecsCard()
    card.apply_report(report)
    assert "9.4.0" in card._vals["gcc"].text()
    assert "5.14.2" in card._vals["qt"].text()
    assert "/opt/arm64-rootfs" in card._vals["sysroot"].text()
    assert "aarch64-linux-gnu" in card._vals["arch"].text()

    print("selfcheck OK")


if __name__ == "__main__":
    main()
