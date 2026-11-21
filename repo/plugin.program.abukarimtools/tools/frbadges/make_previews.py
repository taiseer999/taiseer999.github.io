# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""Cards for the "AF3: OSD Flags Style" picker (4.12.12): 1072x604 (16:9,
shown at 536x302 in abk_grid.xml), rounded top corners, a soft cinematic
backdrop with a player progress bar, and three rows of that style's Lucent
Player pills at one even size and spacing.
Usage: make_previews.py FRBADGES_RESOURCES OUT"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
RES, OUT = sys.argv[1], sys.argv[2]
W, H, R = 1072, 604, 44
ROWS = [['4K', 'HDR10', 'DV', 'HDR10+'], ['ATMOS', 'TRUEHD', 'DTS-X', 'DD+'], ['HEVC', 'AV1', '7.1', 'REMUX']]
PH, GAP_X, GAP_Y, SIDE = 84, 22, 26, 56          # pill height, gaps, side margin
# base gradient (top-left, bottom-right) and glow blobs (x, y, radius, rgb)
LOOK = {'default': (((18, 14, 40), (10, 20, 44)),
                    ((0.12, 0.10, 0.55, (120, 40, 170)), (0.92, 0.95, 0.60, (20, 110, 160)), (0.55, 0.45, 0.35, (60, 40, 130)))),
        'lucent': (((28, 18, 30), (14, 26, 40)),
                   ((0.10, 0.15, 0.55, (190, 90, 50)), (0.90, 0.90, 0.55, (40, 120, 150)), (0.55, 0.50, 0.35, (90, 70, 120)))),
        'light': (((206, 212, 228), (226, 222, 236)),
                  ((0.10, 0.10, 0.55, (250, 225, 240)), (0.92, 0.95, 0.55, (200, 230, 245)), (0.5, 0.5, 0.3, (236, 236, 246))))}


def backdrop(kind):
    (a, b), blobs = LOOK[kind]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = np.clip(xx / W * 0.6 + yy / H * 0.4, 0, 1)[..., None]
    img = np.array(a, np.float32) * (1 - t) + np.array(b, np.float32) * t
    for bx, by, br, col in blobs:
        d = np.sqrt((xx - bx * W) ** 2 + (yy - by * H) ** 2) / (br * W)
        k = np.clip(1 - d, 0, 1)[..., None] ** 2 * 0.85
        img = img * (1 - k) + np.array(col, np.float32) * k
    if kind != 'light':                            # vignette
        v = np.sqrt(((xx / W) - .5) ** 2 + ((yy / H) - .5) ** 2) / .72
        img *= (1 - np.clip(v, 0, 1) ** 2.2 * 0.55)[..., None]
    rng = np.random.default_rng(7)                 # fine grain against banding
    img += rng.normal(0, 1.6, img.shape[:2])[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')


def player_bar(im, light):
    d = ImageDraw.Draw(im, 'RGBA'); y = H - 40; x0, x1 = SIDE, W - SIDE
    fg = (20, 22, 34) if light else (255, 255, 255)
    d.rounded_rectangle((x0, y - 4, x1, y + 4), 4, fill=fg + (60,))
    xp = x0 + int((x1 - x0) * 0.62)
    d.rounded_rectangle((x0, y - 4, xp, y + 4), 4, fill=fg + (220,))
    d.ellipse((xp - 11, y - 11, xp + 11, y + 11), fill=fg + (255,))


def pills(folder, names, h, alpha=255):
    out = []
    for n in names:
        b = Image.open(os.path.join(folder, n + '.png')).convert('RGBA')
        b = b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
        if alpha < 255:
            b.putalpha(b.getchannel('A').point(lambda v: v * alpha // 255))
        out.append(b)
    return out


def grid(im, rows, x0, x1, h=PH, top=None):
    """rows: list of pill lists; one shared scale so every pill is the same size"""
    widest = max(sum(b.width for b in r) + GAP_X * (len(r) - 1) for r in rows)
    s = min(1.0, (x1 - x0) / widest)
    rows = [[b.resize((max(1, round(b.width * s)), max(1, round(b.height * s))), Image.LANCZOS) if s < 1 else b
             for b in r] for r in rows]
    gx = GAP_X * s; rh = round(h * s); gy = GAP_Y * s
    tot = len(rows) * rh + (len(rows) - 1) * gy
    y = top if top is not None else (H - 64 - tot) / 2
    for r in rows:
        w = sum(b.width for b in r) + gx * (len(r) - 1)
        x = x0 + ((x1 - x0) - w) / 2
        for b in r:
            im.alpha_composite(b, (round(x), round(y + (rh - b.height) / 2))); x += b.width + gx
        y += rh + gy


def round_top(im):
    m = Image.new('L', (W * 2, H * 2))
    ImageDraw.Draw(m).rounded_rectangle((0, 0, W * 2 - 1, H * 2 + R * 4), R * 2, fill=255)
    out = Image.new('RGBA', (W, H)); out.paste(im, (0, 0), m.resize((W, H), Image.LANCZOS)); return out


def card(style):
    light = style == 'textblack'
    kind = 'light' if light else ('lucent' if style == 'lucent' else 'default')
    im = backdrop(kind)
    lp = lambda s: os.path.join(RES, s, 'lucent_player')
    if style == 'auto':                            # classic on one half, Lucent on the other
        half = backdrop('lucent')
        im.paste(half.crop((W // 2, 0, W, H)), (W // 2, 0))
        sh = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(sh)
        d.line((W // 2, 28, W // 2, H - 76), fill=(255, 255, 255, 150), width=3)
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(1)))
        grid(im, [pills(lp('colorful'), r[:2], PH) for r in ROWS], 24, W // 2 - 24)
        grid(im, [pills(lp('lucent'), r[2:], PH) for r in ROWS], W // 2 + 24, W - 24)
    elif style == 'off':
        grid(im, [pills(lp('colorful'), r, PH, alpha=45) for r in ROWS], SIDE, W - SIDE)
        lay = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(lay); c = (W // 2, (H - 64) // 2); r = 78
        d.ellipse((c[0] - r - 26, c[1] - r - 26, c[0] + r + 26, c[1] + r + 26), fill=(10, 10, 20, 150))
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=(255, 255, 255, 235), width=14)
        k = int(r * 0.7)
        d.line((c[0] - k, c[1] + k, c[0] + k, c[1] - k), fill=(255, 255, 255, 235), width=14)
        im.alpha_composite(lay)
    else:
        grid(im, [pills(lp(style), r, PH) for r in ROWS], SIDE, W - SIDE)
    player_bar(im, light)
    return round_top(im)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for st in ('auto', 'colorful', 'lucent', 'glass', 'solid', 'frost', 'whiteblack', 'blackwhite', 'minimal', 'light',
               'icondark', 'iconlight', 'split', 'neonicon', 'textwhite', 'textblack', 'off'):
        card(st).quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG).save(
            os.path.join(OUT, st + '.png'), optimize=True)
    print('ok')
