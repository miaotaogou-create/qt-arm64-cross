"""记住最近工程与界面设置。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _path() -> Path:
    base = Path.home() / ".qt-arm64-cross"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


DEFAULTS: dict[str, Any] = {
    "distro": "Ubuntu-20.04",
    "recent_projects": [],
    "project": "",
    "build_file": "",
    "build_system": "auto",
    "app_name": "",
    "out_bin": "",
    "jobs": 0,
    "do_bundle": True,
    "use_ffmpeg": False,
    "plugins": "platforms/libqxcb.so platforms/libqoffscreen.so",
    "extra_pkgconfig": "",
    "extra_copy": "",
    "share_dir": "",
    "share_port": 8080,
}


def load() -> dict[str, Any]:
    p = _path()
    if not p.is_file():
        return dict(DEFAULTS)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update({k: v for k, v in data.items() if k in DEFAULTS})
    return out


def save(data: dict[str, Any]) -> None:
    cur = load()
    cur.update({k: v for k, v in data.items() if k in DEFAULTS})
    proj = (cur.get("project") or "").strip()
    if proj:
        recent = [p for p in cur.get("recent_projects", []) if p != proj]
        recent.insert(0, proj)
        cur["recent_projects"] = recent[:12]
    _path().write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
