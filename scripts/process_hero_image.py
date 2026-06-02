#!/usr/bin/env python3
"""Remove checkerboard / light studio background from product hero PNG."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def remove_checkerboard(src: Path, dst: Path) -> None:
    img = Image.open(src).convert('RGBA')
    px = img.load()
    w, h = img.size

    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 10:
                continue
            # Light gray / white checkerboard and near-white backdrop
            mx = max(r, g, b)
            mn = min(r, g, b)
            spread = mx - mn
            if mx > 200 and spread < 35:
                px[x, y] = (r, g, b, 0)
                continue
            if 170 <= mx <= 210 and spread < 25:
                px[x, y] = (r, g, b, 0)
                continue
            # Soft edge feather for remaining light fringe
            if mx > 155 and spread < 20:
                alpha = max(0, 255 - int((mx - 155) * 4))
                px[x, y] = (r, g, b, min(a, alpha))

    # Trim empty margins
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, 'PNG', optimize=True)
    print(f'Wrote {dst} ({img.size[0]}x{img.size[1]})')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'assets/static/img/nmed-product-hero-source.jpg'
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else root / 'assets/static/img/nmed-product-hero.png'
    remove_checkerboard(src, dst)
