#!/usr/bin/env python3
"""最小自检：路径转换与构建设置拼装（不连 WSL）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from crosskit import detect
from crosskit.build import discover_build_files, merge_extra_pkgconfig
from crosskit.httpshare import DirectoryShare, best_lan_ipv4, lan_ipv4
from crosskit.wsl import win_to_wsl


def main() -> None:
    w = win_to_wsl(r"C:\ZYL\workspace\projects\qt-arm64-cross")
    assert w == "/mnt/c/ZYL/workspace/projects/qt-arm64-cross", w
    assert detect.toolkit_root() == ROOT, detect.toolkit_root()

    qfiles = discover_build_files(ROOT / "examples" / "hello_qmake")
    assert any(k == "qmake" and p.endswith(".pro") for k, p in qfiles), qfiles

    cfiles = discover_build_files(ROOT / "examples" / "hello_cmake")
    assert any(k == "cmake" for k, p in cfiles), cfiles

    assert merge_extra_pkgconfig(False, "") == ""
    assert "libavcodec" in merge_extra_pkgconfig(True, "")
    assert merge_extra_pkgconfig(True, "libfoo").endswith("libfoo")

    assert isinstance(lan_ipv4(), list)
    assert best_lan_ipv4()
    share = DirectoryShare()
    share.start(ROOT, 18765)
    try:
        assert share.running
        assert share.urls()
        assert share.primary_url().startswith("http://")
        assert share.primary_url().count("\n") == 0
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:18765/README.md", timeout=3) as r:
            assert b"Qt" in r.read(200)
    finally:
        share.stop()
    assert not share.running

    print("selfcheck OK")


if __name__ == "__main__":
    main()
