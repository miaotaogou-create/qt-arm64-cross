#!/usr/bin/env python3
"""启动 Qt ARM64 交叉编译 GUI（支持 PyInstaller 单文件绿色版）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_frozen() -> None:
    """onefile 解压后：定位 Tcl/Tk，并把仓库根加入 sys.path。"""
    if not getattr(sys, "frozen", False):
        root = Path(__file__).resolve().parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        return

    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    # PyInstaller 对 Python 3.14 的 tcl 钩子常漏文件；显式指定库目录
    for rel in ("_tcl_data", "tcl8.6", Path("tcl") / "tcl8.6"):
        p = base / rel
        if (p / "init.tcl").is_file():
            os.environ["TCL_LIBRARY"] = str(p)
            break
    for rel in ("_tk_data", "tk8.6", Path("tcl") / "tk8.6"):
        p = base / rel
        if (p / "tk.tcl").is_file():
            os.environ["TK_LIBRARY"] = str(p)
            break


_prepare_frozen()

from gui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
