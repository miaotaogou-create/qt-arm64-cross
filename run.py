#!/usr/bin/env python3
"""启动 Qt ARM64 交叉编译 GUI（PySide6；支持 PyInstaller 单文件绿色版）。"""
from __future__ import annotations

import sys
from pathlib import Path


def _prepare_frozen() -> None:
    if not getattr(sys, "frozen", False):
        root = Path(__file__).resolve().parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        return
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))


def _smoke() -> int:
    """打包自检：创建 QApplication，成功则写旁路标记文件。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    ver = "PySide6"
    try:
        import PySide6

        ver = f"PySide6 {PySide6.__version__}"
    except Exception:
        pass
    app.quit()
    mark = Path(sys.executable).with_suffix(".smoke_ok") if getattr(sys, "frozen", False) else Path("smoke_ok.txt")
    mark.write_text(
        f"QT_OK {ver}\nMEIPASS={getattr(sys, '_MEIPASS', '')}\n",
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
