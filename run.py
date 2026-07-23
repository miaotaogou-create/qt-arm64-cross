#!/usr/bin/env python3
"""启动 Qt ARM64 交叉编译 GUI。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.app import main

if __name__ == "__main__":
    main()
