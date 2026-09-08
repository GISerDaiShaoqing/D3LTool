# -*- coding: utf-8 -*-
"""Generate the optimized D3L icon (keeps the original splat+D3L concept).

Output: d3ltool/resources/D3L.ico (256/128/64/48/32/16) + preview PNGs.
Deterministic (seeded) so it can be regenerated.
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
RES = ROOT / "d3ltool" / "resources"
RES.mkdir(parents=True, exist_ok=True)

S = 2048                      # supersampled canvas
RED = (214, 55, 42, 255)
RED_DARK = (170, 38, 28, 255)
WHITE = (255, 255, 255, 255)


def gradient_bg():
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    top, bot = (13, 27, 42), (30, 58, 92)
    for y in range(S):
        t = y / S
        gd.line([(0, y), (S, y)],
                fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([36, 36, S - 36, S - 36], radius=int(S * 0.19), fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return Image.composite(grad, img, mask)


def splat(d, cx, cy, r, seed):
    rnd = random.Random(seed)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED)
    for _ in range(22):                                  # droplets hugging the blob
        ang = rnd.uniform(0, 2 * math.pi)
        dist = rnd.uniform(1.03, 1.45)
        rr = rnd.uniform(0.05, 0.20) * r
        x, y = cx + math.cos(ang) * r * dist, cy + math.sin(ang) * r * dist
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=RED)
    for _ in range(6):                                   # far small dots
        ang = rnd.uniform(0, 2 * math.pi)
        dist = rnd.uniform(1.5, 2.0)
        rr = rnd.uniform(0.03, 0.06) * r
        x, y = cx + math.cos(ang) * r * dist, cy + math.sin(ang) * r * dist
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=RED)
    # inner shadow rim for depth
    d.arc([cx - r, cy - r, cx + r, cy + r], 20, 200, fill=RED_DARK, width=int(r * 0.10))


def load_font(size):
    import sys

    candidates = []
    if sys.platform == "win32":
        candidates = [f"C:/Windows/Fonts/{n}.ttf"
                      for n in ("ariblk", "arialbd", "segoeuib")]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    img_full = render(with_satellite=True)
    img_clean = render(with_satellite=False)

    # large sizes keep the satellite; small sizes drop it for legibility
    big = [(256, 256), (128, 128), (64, 64)]
    small = [(48, 48), (32, 32), (16, 16)]
    frames = [img_full.resize(s, Image.LANCZOS) for s in big] + \
             [img_clean.resize(s, Image.LANCZOS) for s in small]

    base = frames[0]
    base.save(RES / "D3L.ico", format="ICO",
              sizes=big + small,
              append_images=frames[1:])

    # previews for review: 512 full, 32px shown at 6x (nearest, no smoothing)
    img_full.resize((512, 512), Image.LANCZOS).save(RES / "icon_512.png")
    img_full.resize((512, 512), Image.LANCZOS).save(ROOT / "icon_preview_512.png")
    frames[-2].resize((192, 192), Image.NEAREST).save(ROOT / "icon_preview_32px.png")
    frames[-1].resize((128, 128), Image.NEAREST).save(ROOT / "icon_preview_16px.png")

    # macOS icon (used by the PyInstaller BUNDLE on darwin)
    img_full.resize((512, 512), Image.LANCZOS).save(
        RES / "D3L.icns", format="ICNS",
        sizes=[(512, 512), (256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("icon written:", RES / "D3L.ico", "and", RES / "D3L.icns")


def render(with_satellite=True):
    img = gradient_bg()
    d = ImageDraw.Draw(img)

    # subtle top-left sheen
    sheen = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.ellipse([-S * 0.3, -S * 0.45, S * 0.75, S * 0.4], fill=(255, 255, 255, 16))
    img = Image.alpha_composite(img, sheen)
    d = ImageDraw.Draw(img)

    # three splat blobs (keeps the original layout: D - 3 - L)
    blobs = [
        (0.285 * S, 0.47 * S, 0.185 * S, 11),   # D
        (0.545 * S, 0.42 * S, 0.150 * S, 23),   # 3
        (0.790 * S, 0.49 * S, 0.170 * S, 37),   # L
    ]
    for cx, cy, r, seed in blobs:
        splat(d, cx, cy, r, seed)

    # letters
    f_big = load_font(int(0.185 * S * 1.55))
    f_mid = load_font(int(0.150 * S * 1.55))
    f_sm = load_font(int(0.170 * S * 1.55))
    for (cx, cy, r, _), f, ch in zip(blobs, (f_big, f_mid, f_sm), "D3L"):
        d.text((cx, cy - r * 0.02), ch, font=f, fill=WHITE, anchor="mm")

    # tiny satellite (replaces the NASA ball): body + solar wings, top right
    if with_satellite:
        bx, by = 0.700 * S, 0.205 * S
        body = 0.026 * S
        d.ellipse([bx - body, by - body, bx + body, by + body], fill=WHITE)
        wing_h, wing_l = 0.030 * S, 0.075 * S
        gap = 0.022 * S
        d.rectangle([bx - gap - wing_l, by - wing_h, bx - gap, by + wing_h], fill=WHITE)
        d.rectangle([bx + gap, by - wing_h, bx + gap + wing_l, by + wing_h], fill=WHITE)
    return img


if __name__ == "__main__":
    main()
