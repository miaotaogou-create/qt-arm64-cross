"""从 images/图标.png 生成 app.ico / app.png（裁黑边 + 透明底，供 exe 与窗口图标）。"""
from __future__ import annotations

import io
import struct
import sys
from collections import deque
from pathlib import Path

from PIL import Image


def _near_black(c: tuple[int, int, int, int], thr: int = 22) -> bool:
    r, g, b, a = c
    return a < 8 or (r <= thr and g <= thr and b <= thr)


def trim_and_punch_black(im: Image.Image, *, margin: float = 0.04) -> Image.Image:
    """裁掉大块黑边，并把与四角连通的黑底打成透明（圆角外不再留黑框）。"""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if not _near_black(px[x, y]):
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return im

    pad = int(max(maxx - minx + 1, maxy - miny + 1) * margin)
    left = max(0, minx - pad)
    top = max(0, miny - pad)
    right = min(w, maxx + 1 + pad)
    bottom = min(h, maxy + 1 + pad)
    crop = im.crop((left, top, right, bottom)).convert("RGBA")

    # 从边缘洪水填充：与画布边缘连通的近黑像素 → 透明
    cw, ch = crop.size
    pix = crop.load()
    visited = [[False] * cw for _ in range(ch)]
    q: deque[tuple[int, int]] = deque()
    for x in range(cw):
        q.append((x, 0))
        q.append((x, ch - 1))
    for y in range(ch):
        q.append((0, y))
        q.append((cw - 1, y))
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= cw or y >= ch or visited[y][x]:
            continue
        visited[y][x] = True
        if not _near_black(pix[x, y]):
            continue
        r, g, b, _a = pix[x, y]
        pix[x, y] = (r, g, b, 0)
        q.append((x + 1, y))
        q.append((x - 1, y))
        q.append((x, y + 1))
        q.append((x, y - 1))

    # 放到正方形画布（透明底），避免拉伸变形
    side = max(cw, ch)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(crop, ((side - cw) // 2, (side - ch) // 2), crop)
    return canvas


def write_ico(path: Path, im: Image.Image, sizes: list[int]) -> None:
    blobs: list[bytes] = []
    for s in sizes:
        buf = io.BytesIO()
        im.resize((s, s), Image.Resampling.LANCZOS).save(buf, format="PNG")
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
    path.write_bytes(out)


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
    base = trim_and_punch_black(Image.open(src))
    (base.resize((256, 256), Image.Resampling.LANCZOS)).save(img_dir / "app.png", "PNG")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    ico = img_dir / "app.ico"
    write_ico(ico, base, sizes)
    print(f"ICON_OK src={src.name} cropped={base.size} ico={ico.stat().st_size} sizes={sizes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
