"""打包/开发环境下的静态资源路径。"""
from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def app_icon_path() -> Path | None:
    """应用程序图标：优先 app.ico，其次 app.png / 源图。"""
    root = project_root()
    for name in ("images/app.ico", "images/app.png", "images/图标.png"):
        p = root / name
        if p.is_file():
            return p
    # 开发态兜底：images 下任意非 app 的 png
    img = root / "images"
    if img.is_dir():
        for p in sorted(img.glob("*.png")):
            if p.name.lower() != "app.png":
                return p
    return None
