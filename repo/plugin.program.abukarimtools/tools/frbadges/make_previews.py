# SPDX-License-Identifier: GPL-3.0-or-later
"""Cards for the "AF3: OSD Flags Style" picker (4.9.1): 560x270, rounded top
corners, a small player mock-up (title + plot lines) with a row of that
style's Lucent Player badges. Usage: make_previews.py FRBADGES_RESOURCES OUT"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
RES, OUT = sys.argv[1], sys.argv[2]
W, H, R = 560, 270, 22
ROWS = [['4K', 'HDR10', 'DV', 'HDR10+'], ['ATMOS', 'TRUEHD', 'DTS-X', 'DD+'], ['HEVC', 'AV1', '7.1', 'REMUX']]
ROW_Y = (30, 105, 180)
BG = {'default': ((84, 24, 120), (24, 36, 92), (34, 30, 52)),   # bottom-left, centre, top-right
      'textblack': ((214, 210, 226), (198, 214, 232), (230, 226, 236)),
      'lucent': ((150, 70, 40), (60, 70, 120), (40, 90, 110))}


def backdrop(kind):
    a, b, c = (np.array(x, float) for x in BG.get(kind, BG['default']))
    yy, xx = np.mgrid[0:H, 0:W]
    t = np.clip((xx / W) * 0.65 + (1 - yy / H) * 0.35, 0, 1)[..., None]
    img = np.where(t < .5, a + (b - a) * (t / .5), b + (c - b) * ((t - .5) / .5))
    im = Image.fromarray(img.astype(np.uint8)).convert('RGBA')
    return im.filter(ImageFilter.GaussianBlur(6))


def mock(im, light):
    lay = Image.new('RGBA', im.size); d = ImageDraw.Draw(lay)
    fg = (20, 22, 30) if light else (255, 255, 255)
    d.rounded_rectangle((26, 22, W - 220, 150), 10, fill=(255, 255, 255, 90) if light else (10, 8, 20, 140))
    d.rectangle((40, 38, 220, 56), fill=fg + (235,))
    d.rectangle((40, 74, 330, 86), fill=fg + (110,))
    d.rectangle((40, 98, 280, 110), fill=fg + (80,))
    im.alpha_composite(lay)


def row(im, folder, names, y, h=48, alpha=255, x0=0, x1=W):
    bad = [Image.open(os.path.join(folder, n + '.png')).convert('RGBA') for n in names]
    bad = [b.resize((round(b.width * h / b.height), h), Image.LANCZOS) for b in bad]
    gap = 8; tot = sum(b.width for b in bad) + gap * (len(bad) - 1)
    span = x1 - x0
    if tot > span - 40:
        s = (span - 40 - gap * (len(bad) - 1)) / sum(b.width for b in bad)
        bad = [b.resize((round(b.width * s), round(h * s)), Image.LANCZOS) for b in bad]
        tot = sum(b.width for b in bad) + gap * (len(bad) - 1)
    x = x0 + (span - tot) // 2
    for b in bad:
        if alpha < 255:
            b.putalpha(b.split()[3].point(lambda v: v * alpha // 255))
        im.alpha_composite(b, (x, y + (h - b.height) // 2)); x += b.width + gap


def round_top(im):
    m = Image.new('L', (W * 4, H * 4)); ImageDraw.Draw(m).rounded_rectangle((0, 0, W * 4 - 1, H * 4 + R * 8), R * 4, fill=255)
    out = Image.new('RGBA', (W, H)); out.paste(im, (0, 0), m.resize((W, H), Image.LANCZOS)); return out


def card(style):
    kind = style if style in BG else 'default'
    im = backdrop(kind)
    lp = lambda s: os.path.join(RES, s, 'lucent_player')
    if style == 'auto':                       # classic on the left half, Lucent on the right
        half = backdrop('lucent')
        im.paste(half.crop((W // 2, 0, W, H)), (W // 2, 0))
        ImageDraw.Draw(im).line((W // 2, 12, W // 2, H - 12), fill=(255, 255, 255, 120), width=2)
        for names, y in zip(ROWS, ROW_Y):
            row(im, lp('colorful'), names[:2], y, h=56, x0=0, x1=W // 2)
            row(im, lp('lucent'), names[2:], y, h=56, x0=W // 2, x1=W)
    elif style == 'off':
        for names, y in zip(ROWS, ROW_Y):
            row(im, lp('colorful'), names, y, h=56, alpha=40)
        d = ImageDraw.Draw(im); c = (W // 2, H // 2)
        d.ellipse((c[0] - 44, c[1] - 44, c[0] + 44, c[1] + 44), outline=(255, 255, 255, 230), width=8)
        d.line((c[0] - 30, c[1] + 30, c[0] + 30, c[1] - 30), fill=(255, 255, 255, 230), width=8)
    else:
        for names, y in zip(ROWS, ROW_Y):
            row(im, lp(style), names, y, h=56)
    return round_top(im)


os.makedirs(OUT, exist_ok=True)
for st in ('auto', 'colorful', 'lucent', 'glass', 'solid', 'frost', 'whiteblack', 'blackwhite', 'minimal', 'light',
           'icondark', 'iconlight', 'split', 'neonicon', 'textwhite', 'textblack', 'off'):
    card(st).save(os.path.join(OUT, st + '.png'), optimize=True)
print('ok')
