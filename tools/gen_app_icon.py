"""从 images/图标.png 生成 app.ico / app.png（多尺寸，供 exe 与窗口图标）。"""
from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    img_dir = root / "images"
    if not img_dir.is_dir():
        print("images/ missing", file=sys.stderr)
        return 1
    cands = [p for p in img_dir.glob("*.png") if p.name.lower() != "app.png"]
    if not cands:
        print("no source png in images/", file=sys.stderr)
        return 1
    src = next((p for p in cands if "图标" in p.name), cands[0])
    base = Image.open(src).convert("RGBA")
    (base.resize((256, 256), Image.Resampling.LANCZOS)).save(img_dir / "app.png", "PNG")

    # 手写多尺寸 ICO：资源管理器列表/磁贴都要小尺寸，单 256 常显示成默认图标
    sizes = [16, 24, 32, 48, 64, 128, 256]
    blobs: list[bytes] = []
    for s in sizes:
        buf = io.BytesIO()
        base.resize((s, s), Image.Resampling.LANCZOS).save(buf, format="PNG")
        blobs.append(buf.getvalue())
    out = bytearray()
    out += struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    for s, blob in zip(sizes, blobs):
        w = 0 if s >= 256 else s
        h = w
        out += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    for blob in blobs:
        out += blob
    ico = img_dir / "app.ico"
    ico.write_bytes(out)
    print(f"ICON_OK src={src.name} ico={ico.stat().st_size} sizes={sizes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
