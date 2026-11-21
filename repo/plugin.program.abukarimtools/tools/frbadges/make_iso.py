# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""ISO.png for every FR style's lucent_player/ set, redrawn from that style's
BLURAY.png: the label is wiped (columns blended from both sides of it, so the
pill, its gradient and its edges stay), then "ISO" is written at the same cap
height, place and colours. lucent / colorful get the AB Tools Lucent pill."""
import os, sys, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
RES, LUCENT_ISO = sys.argv[1], sys.argv[2]
FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
DARK = {'iconlight', 'light', 'textblack', 'whiteblack'}
SHADOW = {'textblack', 'textwhite'}
_cap = None
def cap_ratio():
    global _cap
    if _cap is None:
        bb = ImageFont.truetype(FONT, 1000).getbbox('H'); _cap = (bb[3] - bb[1]) / 1000.0
    return _cap

def text_mask(a, dark):
    lum = a[..., :3].astype(int).mean(2)
    m = ((lum < 80) if dark else (lum > 200)) & (a[..., 3] > 160)
    h = a.shape[0]; m[:int(h * .12)] = False; m[int(h * .88):] = False
    return m

def label_box(m, with_prev=False):
    h = m.shape[0]
    cols = np.where(m.any(0))[0]
    groups, cur = [], [cols[0]]
    for c in cols[1:]:
        if c - cur[-1] > h * .14: groups.append(cur); cur = [c]
        else: cur.append(c)
    groups.append(cur)
    g = max(groups[-2:], key=len) if len(groups) > 1 and len(groups[-1]) < h * .25 else groups[-1]
    x0, x1 = g[0], g[-1]
    rows = np.where(m[:, x0:x1 + 1].any(1))[0]
    if with_prev:
        k = groups.index(g)
        return (x0, rows.min(), x1, rows.max()), (groups[k - 1][-1] if k > 0 else -1)
    return x0, rows.min(), x1, rows.max()

def colours(a, m, box):
    x0, y0, x1, y1 = box; reg = a[:, x0:x1 + 1].astype(int); mm = m[:, x0:x1 + 1]
    q = max(1, (y1 - y0) // 4)
    top = reg[y0:y0 + q][mm[y0:y0 + q]][:, :3].mean(0); bot = reg[y1 - q:y1 + 1][mm[y1 - q:y1 + 1]][:, :3].mean(0)
    return np.array(top), np.array(bot)

def make(style):
    src = os.path.join(RES, style, 'lucent_player', 'BLURAY.png')
    im = Image.open(src).convert('RGBA'); a = np.array(im); h, w = a.shape[:2]
    dark = style in DARK
    m = text_mask(a, dark); box, prev = label_box(m, True); x0, y0, x1, y1 = box
    c_top, c_bot = colours(a, m, box)
    pad = max(6, int(h * .10))
    L = max(prev + 3 if prev >= 0 else 0, x0 - pad)
    R = min(w - 1, x1 + pad)
    out = a.copy().astype(float)
    if a[h // 2, L, 3] < 40 and a[h // 2, R, 3] < 40 or style in SHADOW:
        out[:, L:R + 1] = 0                     # no pill behind the label: clear it
    else:
        for x in range(L + 1, R):
            t = (x - L) / float(R - L)
            out[:, x] = (1 - t) * a[:, L] + t * a[:, R]
    out = Image.fromarray(out.round().astype(np.uint8), 'RGBA')
    size = int((y1 - y0 + 1) / cap_ratio()); font = ImageFont.truetype(FONT, size)
    bb = font.getbbox('ISO'); tw = bb[2] - bb[0]
    cx = (x0 + x1) / 2.0
    x = cx - tw / 2.0 - bb[0]; y = y0 - font.getbbox('H')[1]
    mask = Image.new('L', out.size); ImageDraw.Draw(mask).text((x, y), 'ISO', font=font, fill=255)
    if style in SHADOW:
        sh = Image.new('RGBA', out.size, (255, 255, 255, 0) if dark else (0, 0, 0, 0))
        sh.putalpha(mask.filter(ImageFilter.GaussianBlur(h * .02)).point(lambda v: int(v * .55)))
        out.alpha_composite(sh, (0, int(h * .012)))
    g = np.zeros((h, w, 3), np.uint8)
    for yy in range(h):
        t = min(1, max(0, (yy - y0) / max(1, y1 - y0)))
        g[yy] = (c_top + (c_bot - c_top) * t).astype(np.uint8)
    txt = Image.fromarray(g).convert('RGBA'); txt.putalpha(mask); out.alpha_composite(txt)
    return out

for style in sorted(os.listdir(RES)):
    dst = os.path.join(RES, style, 'lucent_player', 'ISO.png')
    if not os.path.isdir(os.path.dirname(dst)): continue
    if style in ('lucent', 'colorful'):
        shutil.copyfile(LUCENT_ISO, dst)
    else:
        make(style).save(dst, optimize=True)
    print(style, Image.open(dst).size)
