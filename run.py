#!/usr/bin/env python3
"""启动 Qt ARM64 交叉编译 GUI（支持 PyInstaller 单文件绿色版）。"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _prepare_frozen() -> None:
    """onefile：准备 sys.path，并把 Tcl/Tk 拷到 LocalAppData（WINDOWS\\TEMP 下 Tcl 拒读 init.tcl）。"""
    if not getattr(sys, "frozen", False):
        root = Path(__file__).resolve().parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        return

    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    src_tcl = next(
        (base / rel for rel in ("_tcl_data", "tcl8.6") if (base / rel / "init.tcl").is_file()),
        None,
    )
    src_tk = next(
        (base / rel for rel in ("_tk_data", "tk8.6") if (base / rel / "tk.tcl").is_file()),
        None,
    )
    if src_tcl is None or src_tk is None:
        raise FileNotFoundError(f"打包包内缺少 Tcl/Tk 数据: {base}")

    cache = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    cache = cache / "QtArm64Cross" / "tcltk-8.6.15"
    dst_tcl = cache / "tcl8.6"
    dst_tk = cache / "tk8.6"
    marker = cache / ".ready"

    need_copy = True
    if marker.is_file() and (dst_tcl / "init.tcl").is_file() and (dst_tk / "tk.tcl").is_file():
        need_copy = False
    if need_copy:
        if cache.exists():
            shutil.rmtree(cache, ignore_errors=True)
        cache.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_tcl, dst_tcl)
        shutil.copytree(src_tk, dst_tk)
        marker.write_text("ok\n", encoding="utf-8")

    # 覆盖 PyInstaller rthook 指向 TEMP 的设置
    os.environ["TCL_LIBRARY"] = str(dst_tcl)
    os.environ["TK_LIBRARY"] = str(dst_tk)


def _smoke() -> int:
    """打包自检：真正创建 Tk，成功则写旁路标记文件。"""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    ver = str(root.tk.call("info", "patchlevel"))
    root.destroy()
    mark = Path(sys.executable).with_suffix(".smoke_ok") if getattr(sys, "frozen", False) else Path("smoke_ok.txt")
    mark.write_text(
        f"TK_OK {ver}\nMEIPASS={getattr(sys, '_MEIPASS', '')}\n"
        f"TCL_LIBRARY={os.environ.get('TCL_LIBRARY', '')}\n",
        encoding="utf-8",
    )
    print(f"SMOKE_OK {ver}")
    return 0


_prepare_frozen()

if __name__ == "__main__":
    if "--smoke" in sys.argv:
        raise SystemExit(_smoke())
    from gui.app import main

    main()
