# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""DV2.png and IMAX.png for every style's lucent_player/ set (176x68 canvas).
DV2  = the style's DV badge with a "2" after its big label line (VISION / DV),
       the pill widened by a band blended from the background next to the text.
IMAX = the style's 3D badge with its label wiped and "IMAX" written, the pill
       widened to fit. Same cap height, place and text colours as the source."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
RES = sys.argv[1]
# colorful/lucent_player gets lucent's IMAX (the classic set has no text pill to relabel)
ONLY = sys.argv[2:]                     # optional style names
FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
DARK = {'iconlight', 'light', 'textblack', 'whiteblack'}
SHADOW = {'textblack', 'textwhite'}
CW, CH = 176, 68

BRIGHT = {'solid': 242}                 # styles whose pill itself is bright


def mask_of(a, dark, style=''):
    lum = a[..., :3].astype(int).mean(2)
    m = ((lum < 80) if dark else (lum > BRIGHT.get(style, 200))) & (a[..., 3] > 160)
    h = a.shape[0]; m[:int(h * .08)] = False; m[int(h * .92):] = False
    return m

def runs(idx, gap):
    out, cur = [], [idx[0]]
    for v in idx[1:]:
        if v - cur[-1] > gap: out.append(cur); cur = [v]
        else: cur.append(v)
    out.append(cur); return out

def text_cols(m, y0, y1, h):
    cols = np.where(m[y0:y1 + 1].any(0))[0]
    groups = runs(list(cols), h * .14)
    g = max(groups[-2:], key=len) if len(groups) > 1 and len(groups[-1]) < h * .25 else groups[-1]
    k = groups.index(g)
    return g[0], g[-1], (groups[k - 1][-1] if k > 0 else -1)

def colours(a, m, x0, x1, y0, y1):
    reg = a[:, x0:x1 + 1].astype(int); mm = m[:, x0:x1 + 1]; q = max(1, (y1 - y0) // 4)
    sel = lambda r0, r1: reg[r0:r1][mm[r0:r1]][:, :3]
    t, b = sel(y0, y0 + q), sel(y1 - q, y1 + 1)
    t = t.mean(0) if len(t) else np.array([240, 240, 240]); b = b.mean(0) if len(b) else t
    return t, b

def font_for(cap):
    f = ImageFont.truetype(FONT, 1000); bb = f.getbbox('H'); r = (bb[3] - bb[1]) / 1000.0
    return ImageFont.truetype(FONT, max(8, int(round(cap / r))))

def widen(a, at, band, wipe=None):
    """Insert `band` columns at x=at, blended from the column at `at` (pill bg).
    wipe=(L, R): clear / refill [L, R] first (an old label)."""
    h, w = a.shape[:2]; a = a.astype(float)
    transparent = a[h // 2, min(w - 1, at), 3] < 40
    if wipe:
        L, R = wipe
        if transparent:
            a[:, L:R + 1] = 0
        else:
            for x in range(L + 1, R):
                t = (x - L) / float(R - L); a[:, x] = (1 - t) * a[:, L] + t * a[:, R]
    at = min(at, w - 1)
    if transparent:
        col = np.zeros_like(a[:, at:at + 1])
        out = np.concatenate([a[:, :at], np.repeat(col, band, 1), a[:, at:]], 1)
    else:
        # stretch the flat run of the pill [at, end) by `band` columns, so its
        # horizontal gloss / gradient stays continuous
        end = max(at + 2, inside(a.round().astype(np.uint8), w - 1, h))
        seg = Image.fromarray(a[:, at:end].round().astype(np.uint8), 'RGBA')
        seg = np.array(seg.resize((end - at + band, h), Image.BILINEAR)).astype(float)
        out = np.concatenate([a[:, :at], seg, a[:, end:]], 1)
    return out.round().astype(np.uint8)

def write(img, text, x, y_top, cap, ct, cb, shadow, dark):
    font = font_for(cap); h = img.height
    by = font.getbbox('H')[1]
    mask = Image.new('L', img.size); ImageDraw.Draw(mask).text((x - font.getbbox(text)[0], y_top - by), text, font=font, fill=255)
    if shadow:
        sh = Image.new('RGBA', img.size, (255, 255, 255, 0) if dark else (0, 0, 0, 0))
        sh.putalpha(mask.filter(ImageFilter.GaussianBlur(h * .02)).point(lambda v: int(v * .55)))
        img.alpha_composite(sh, (0, int(h * .012)))
    g = np.zeros((h, img.width, 3), np.uint8)
    for yy in range(h):
        t = min(1, max(0, (yy - y_top) / max(1, cap)))
        g[yy] = (ct + (cb - ct) * t).astype(np.uint8)
    txt = Image.fromarray(g).convert('RGBA'); txt.putalpha(mask); img.alpha_composite(txt)
    return img

def fit(img):
    bb = img.split()[3].point(lambda v: 255 if v > 8 else 0).getbbox()
    img = img.crop(bb); s = min(CW / img.width, CH / img.height, 1.0)
    img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
    out = Image.new('RGBA', (CW, CH)); out.alpha_composite(img, ((CW - img.width) // 2, (CH - img.height) // 2))
    return out

def upscale(im, k=3):
    return im.resize((im.width * k, im.height * k), Image.LANCZOS)

def label_rows(m, h):
    """Columns of the label (rightmost text group, icon left out), then its
    tallest row run (the big line)."""
    x0, x1, prev = text_cols(m, 0, m.shape[0] - 1, h)
    rows = runs(list(np.where(m[:, x0:x1 + 1].any(1))[0]), 2)
    big = max(rows, key=len)
    y0, y1 = big[0], big[-1]
    cols = np.where(m[y0:y1 + 1, x0:x1 + 1].any(0))[0]
    return x0 + cols[0], y0, x0 + cols[-1], y1, prev


def inside(a, x, h):
    """Clamp a column into the flat part of the pill (away from its round end)."""
    row = a[h // 2, :, 3]
    solid = np.where(row > 200)[0]
    if not len(solid):
        return x
    return int(min(x, solid[-1] - h * .38))


def clean_col(a, x1, y0, y1, h):
    """First column right of the text that matches plain pill background
    (no anti-aliased edge of the last letter), else x1 + 3."""
    w = a.shape[1]
    ref_x = inside(a, w - 1, h)
    if ref_x <= x1:
        return min(w - 1, x1 + 3)
    ref = a[y0:y1 + 1, ref_x].astype(int)
    for x in range(x1 + 1, ref_x):
        if np.abs(a[y0:y1 + 1, x].astype(int) - ref).max() < 10:
            return x + 1
    return min(w - 1, x1 + 3)


def redraw(style, src, word):
    """Wipe the badge's big text line, widen the pill to fit `word`, write
    `word` where the old line started (same cap height and colours).
    The wiped rows are rebuilt per column by blending the clean row just
    above the line with the clean row just below it (a small line above,
    such as DOLBY, stays); the pill is widened by stretching the middle of
    that clean area, away from its rounded ends."""
    im = upscale(Image.open(os.path.join(RES, style, 'lucent_player', src)).convert('RGBA'))
    a = np.array(im); h, w = a.shape[:2]; dark = style in DARK
    m = mask_of(a, dark, style)
    x0, y0, x1, y1, prev = label_rows(m, h)
    ct, cb = colours(a, m, x0, x1, y0, y1)
    cap = y1 - y0 + 1; font = font_for(cap)
    mid_y = (y0 + y1) // 2
    transparent = a[mid_y, min(w - 1, x1 + 3), 3] < 40 and a[mid_y, max(0, x0 - 3), 3] < 40
    margin = int(cap * .16) + 3
    L = max(prev + int(h * .04) if prev >= 0 else 0, x0 - margin)
    R = min(w - 1, x1 + margin)
    above = np.where(m[:y0, x0:x1 + 1].any(1))[0]
    ya = (above[-1] + y0) // 2 + 1 if len(above) else max(0, y0 - margin)
    yb = min(h - 1, y1 + margin)
    f = a.astype(float)
    if transparent:
        f[ya:, L:R + 1] = 0
    else:
        top, bot = a[ya - 1, L:R + 1].astype(float), a[min(h - 1, yb + 1), L:R + 1].astype(float)
        for y in range(ya, yb + 1):
            t = (y - ya + 1) / float(yb - ya + 2)
            f[y, L:R + 1] = (1 - t) * top + t * bot
    need = int(font.getlength(word)) + int(cap * .1)
    band = max(0, need - (x1 - x0 + 1))
    if style == 'lucent':                            # roomy pill: same size, text centred
        band, x0 = 0, int((w - int(font.getlength(word))) / 2)
    at = (x0 + x1) // 2
    if len(above) or ya > int(h * .3):               # a small line above (DOLBY): widen past its end
        at = max(at, x1 - 2 * margin)
    if transparent or band == 0:
        g = f[:, at:at + 1] if not transparent else np.zeros_like(f[:, at:at + 1])
        out = np.concatenate([f[:, :at], np.repeat(g, band, 1), f[:, at:]], 1)
    else:
        a0, a1 = at - 12, at + 12
        seg = Image.fromarray(f[:, a0:a1].round().astype(np.uint8), 'RGBA')
        seg = np.array(seg.resize((a1 - a0 + band, h), Image.BILINEAR)).astype(float)
        out = np.concatenate([f[:, :a0], seg, f[:, a1:]], 1)
    out = Image.fromarray(out.round().astype(np.uint8), 'RGBA')
    out = write(out, word, x0, y0, cap, ct, cb, style in SHADOW, dark)
    return fit(out)


def make_dv2(style):
    return redraw(style, 'DV.png', 'DV 2' if style == 'neonicon' else 'VISION 2')


def make_imax(style):
    return redraw(style, '3D.png', 'IMAX')


for style in sorted(os.listdir(RES)):
    lp = os.path.join(RES, style, 'lucent_player')
    if not os.path.isdir(lp) or (ONLY and style not in ONLY) or style == 'colorful':
        continue
    if style != 'lucent':                            # the Lucent pill already reads VISION 2
        make_dv2(style).save(os.path.join(lp, 'DV2.png'), optimize=True)
    make_imax(style).save(os.path.join(lp, 'IMAX.png'), optimize=True)
    print(style)
if os.path.exists(os.path.join(RES, 'lucent', 'lucent_player', 'IMAX.png')) and os.path.isdir(os.path.join(RES, 'colorful', 'lucent_player')):
    import shutil
    shutil.copyfile(os.path.join(RES, 'lucent', 'lucent_player', 'IMAX.png'), os.path.join(RES, 'colorful', 'lucent_player', 'IMAX.png'))
