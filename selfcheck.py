#!/usr/bin/env python3
"""最小自检：路径转换与构建设置拼装（不连 WSL）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from crosskit import detect
from crosskit.build import discover_build_files, merge_extra_pkgconfig
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

    print("selfcheck OK")


if __name__ == "__main__":
    main()
