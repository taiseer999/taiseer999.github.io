# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""1.0.18: the single-line FR-Badges styles (Pastel, Glow Bar, Pixel).

Their badges are one line of text ("7.1 SURROUND", "DOLBY VISION"), so a
compact Lucent Player label cannot come from the two-line geometry relabel.py
measures. Two ways, both keep the badge's own pill / bar / colours:

  keep(style, src, words)  the badge with only some of its words, spliced by
                           whole columns (flat Pastel pill, transparent Glow
                           Bar background and its bar, Pixel blocks), so the
                           kept words are the original artwork
  draw(style, src, text)   new text on the badge's own background: Inter
                           Black for Pastel / Glow Bar (same cap height,
                           place and colour), a 5-row pixel font with the
                           black outline and drop shadow for Pixel
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FOLDER = {'pastel': 'Badges-Pastel', 'glowbar': 'Badges-Glow-Bar', 'pixel': 'Badges-Pixel'}

# FR-Badges' text for the badges the Lucent Player / ratio / ISO badges use
TEXT = {'1080p': '1080p FHD', '720p': '720p HD', '480p': '480p SD', 'dolby-vision': 'DOLBY VISION', 'hdr10plus': 'HDR10+',
        'hevc': 'HEVC H.265', 'avc': 'AVC H.264', 'atmos': 'DOLBY ATMOS', 'truehd': 'DOLBY TRUEHD',
        'dtshd-ma': 'DTS-HD MASTER AUDIO', 'dtshd-hra': 'DTS-HD HRA', 'ddplus': 'DOLBY DIGITAL+', 'dd': 'DOLBY DIGITAL',
        'pcm': 'PCM LPCM', '7-1': '7.1 SURROUND', '6-1': '6.1 SURROUND', '5-1': '5.1 SURROUND', '2-0': '2.0 STEREO',
        '1-0': '1.0 MONO', 'source-tvrip': 'TVRIP SATRIP', 'source-dvd': 'DVD DVDRIP', 'scr': 'SCR SCREENER',
        'hc-hdrip': 'HC HDRIP', 'ts': 'M2TS TS', 'multi-audio': 'MULTI AUDIO', '4k': '4K UHD', '8k': '8K UHD'}

# 5-row pixel font (Pixel style): '#' = one unit
PIX = {
 'A': ['.#.', '#.#', '###', '#.#', '#.#'], 'B': ['##.', '#.#', '##.', '#.#', '##.'], 'C': ['.##', '#..', '#..', '#..', '.##'],
 'D': ['##.', '#.#', '#.#', '#.#', '##.'], 'E': ['###', '#..', '##.', '#..', '###'], 'F': ['###', '#..', '##.', '#..', '#..'],
 'G': ['.##', '#..', '#.#', '#.#', '.##'], 'H': ['#.#', '#.#', '###', '#.#', '#.#'], 'I': ['###', '.#.', '.#.', '.#.', '###'],
 'K': ['#.#', '#.#', '##.', '#.#', '#.#'], 'L': ['#..', '#..', '#..', '#..', '###'], 'M': ['#...#', '##.##', '#.#.#', '#...#', '#...#'],
 'N': ['#..#', '##.#', '#.##', '#..#', '#..#'], 'O': ['.#.', '#.#', '#.#', '#.#', '.#.'], 'P': ['##.', '#.#', '##.', '#..', '#..'],
 'Q': ['.#.', '#.#', '#.#', '#.#', '.##'], 'R': ['##.', '#.#', '##.', '#.#', '#.#'], 'S': ['.##', '#..', '.#.', '..#', '##.'],
 'T': ['###', '.#.', '.#.', '.#.', '.#.'], 'U': ['#.#', '#.#', '#.#', '#.#', '###'], 'V': ['#.#', '#.#', '#.#', '#.#', '.#.'],
 'W': ['#...#', '#...#', '#.#.#', '##.##', '#...#'], 'X': ['#.#', '#.#', '.#.', '#.#', '#.#'], 'Y': ['#.#', '#.#', '.#.', '.#.', '.#.'],
 'Z': ['###', '..#', '.#.', '#..', '###'],
 '0': ['###', '#.#', '#.#', '#.#', '###'], '1': ['.#', '##', '.#', '.#', '.#'], '2': ['##.', '..#', '.#.', '#..', '###'],
 '3': ['##.', '..#', '.#.', '..#', '##.'], '4': ['#.#', '#.#', '###', '..#', '..#'], '5': ['###', '#..', '##.', '..#', '##.'],
 '6': ['.##', '#..', '###', '#.#', '###'], '7': ['###', '..#', '.#.', '.#.', '.#.'], '8': ['###', '#.#', '###', '#.#', '###'],
 '9': ['###', '#.#', '###', '..#', '##.'], '.': ['.', '.', '.', '.', '#'], ':': ['.', '#', '.', '#', '.'],
 '-': ['..', '..', '##', '..', '..'], '+': ['...', '.#.', '###', '.#.', '...'], ' ': ['.', '.', '.', '.', '.']}


def _load(src):
    return np.array(Image.open(src).convert('RGBA'))


def _fg(style, a):
    """Text pixels (bool) and the text rows."""
    h, w = a.shape[:2]
    rgb = a[..., :3].astype(int); al = a[..., 3]
    lum = rgb.mean(2); sat = rgb.max(2) - rgb.min(2)
    if style == 'glowbar':
        bar = np.where(((sat > 60) & (al > 150)).sum(1) > w * .2)[0]
        m = (lum > 185) & (sat < 60) & (al > 200)
        if len(bar):
            m[bar.min() - 4:] = False
    elif style == 'pixel':
        m = ((lum > 215) | (lum < 60)) & (al > 200)
        e = int(h * .16); m[:, :e] = False; m[:, w - e:] = False
        m[:int(h * .2)] = False; m[int(h * .9):] = False
    else:                                               # pastel: away from the flat fill
        fill = _fill(a)
        m = (np.abs(rgb - fill).max(2) > 60) & (al > 250)
        m[:int(h * .15)] = False; m[int(h * .85):] = False
        e = int(h * .12); m[:, :e] = False; m[:, w - e:] = False
    rows = np.where(m.any(1))[0]
    return m, (rows.min(), rows.max())


def _fill(a):
    h = a.shape[0]
    reg = a[int(h * .1):int(h * .22)].reshape(-1, 4)
    reg = reg[reg[:, 3] > 250][:, :3]
    return np.median(reg, 0).astype(int)


def _cap(style, m, y0, y1, x0, x1):
    """Cap height: rows of the first upper-case letter / digit."""
    return y0, y1


def words(style, src):
    """[(x0, x1)] of each word (columns), the text rows."""
    a = _load(src); m, (y0, y1) = _fg(style, a); h = a.shape[0]
    xs = np.where(m[y0:y1 + 1].any(0))[0]
    gap = (y1 - y0) * (.26 if style != 'pixel' else .55)
    out = [[xs[0], xs[0]]]
    for x in xs[1:]:
        if x - out[-1][1] > gap:
            out.append([x, x])
        else:
            out[-1][1] = x
    return a, m, (y0, y1), [tuple(o) for o in out]


def keep(style, src, idx, expect=None):
    """The badge with only the words at `idx` (whole columns spliced).
    None when the badge does not split into `expect` words."""
    a, m, (y0, y1), ws = words(style, src)
    if expect and len(ws) != expect:
        return None
    sp = [ws[i + 1][0] - ws[i][1] for i in range(len(ws) - 1)]
    space = int(np.median(sp)) if sp else int((y1 - y0) * .35)
    L, R = ws[0][0], ws[-1][1] + 1
    parts = [a[:, :L]]
    for k, i in enumerate(idx):
        if k:
            parts.append(_bg_cols(style, a, m, y0, y1, ws, space))
        parts.append(a[:, ws[i][0]:ws[i][1] + 1])
    parts.append(a[:, R:])
    return Image.fromarray(np.concatenate(parts, 1), 'RGBA')


def _bg_cols(style, a, m, y0, y1, ws, n):
    """`n` columns of plain background from this badge (no text)."""
    if style == 'pixel':
        # a text-free, block-aligned run (the badge's own left padding)
        x0 = int(a.shape[0] * .16); x1 = ws[0][0] - 8
        chunk = a[:, x0:max(x0 + 1, x1)]
        reps = int(np.ceil(n / max(1, chunk.shape[1])))
        return np.concatenate([chunk] * reps, 1)[:, :n]
    if style == 'glowbar':
        # between words: the bar continues under the gap
        x = ws[0][1] + 1 + max(1, (ws[1][0] - ws[0][1]) // 2) if len(ws) > 1 else ws[0][0] - 4
        col = a[:, x:x + 1].copy()
        col[:y1 + 20, :, 3] = 0
        return np.repeat(col, n, 1)
    col = a[:, ws[0][0] - 6:ws[0][0] - 5]               # pastel: the flat fill
    return np.repeat(col, n, 1)


def _colour(style, a, m, y0, y1):
    reg = a[y0:y1 + 1][m[y0:y1 + 1]][:, :3].astype(int)
    if style == 'pixel' or style == 'glowbar':
        reg = reg[reg.mean(1) > 150]
    return tuple(int(v) for v in np.median(reg, 0))


def _pixel_text(text, unit, ink, dark):
    """Pixel-font label: white glyphs, black outline, drop shadow."""
    cols = []
    for k, ch in enumerate(text.upper()):
        g = PIX.get(ch, PIX[' '])
        if k:
            cols.append(np.zeros((5, 1), bool))      # one unit between letters
        cols.append(np.array([[c == '#' for c in row] for row in g]))
    g = np.concatenate(cols, 1)
    o = max(2, unit // 3)                                # outline / shadow width
    ux = int(round(unit * 1.4))                          # FR's pixel glyphs are wide, thick-stemmed
    H, W = 5 * unit + 3 * o, g.shape[1] * ux + 3 * o
    mask = np.kron(g, np.ones((unit, ux), bool))
    big = np.zeros((H, W), bool); big[o:o + mask.shape[0], o:o + mask.shape[1]] = mask
    edge = big.copy()
    for dy in range(-o, o + 1):
        for dx in range(-o, o + 1):
            edge |= np.roll(np.roll(big, dy, 0), dx, 1)
    sh = np.roll(np.roll(edge, o, 0), o, 1) | edge
    out = np.zeros((H, W, 4), np.uint8)
    out[sh] = dark + (255,)
    out[big] = ink + (255,)
    return Image.fromarray(out, 'RGBA'), o


def draw(style, src, text):
    """`text` written on the badge's own background in place of its words."""
    a, m, (y0, y1), ws = words(style, src)
    h = a.shape[0]
    L, R = ws[0][0], ws[-1][1] + 1
    ink = _colour(style, a, m, y0, y1)
    if style == 'pixel':
        unit = max(4, int(round((y1 - y0 + 1) / 5.6)))
        dark = tuple(int(v) for v in np.median(a[y0:y1 + 1][(a[y0:y1 + 1, :, :3].astype(int).mean(2) < 60) & (a[y0:y1 + 1, :, 3] > 200)][:, :3], 0))
        lab, o = _pixel_text(text, unit, ink, dark)
        mid = _bg_cols(style, a, m, y0, y1, ws, lab.width)
        out = Image.fromarray(np.concatenate([a[:, :L - o], mid, a[:, R + o:]], 1), 'RGBA')
        out.alpha_composite(lab, (L - o, y0 - o))
        return out
    cap = y1 - y0 + 1
    f = ImageFont.truetype(FONT, 1000); bb = f.getbbox('H'); size = int(cap / ((bb[3] - bb[1]) / 1000.0))
    font = ImageFont.truetype(FONT, size)
    tw = int(font.getlength(text))
    mid = _bg_cols(style, a, m, y0, y1, ws, tw + 2)
    if style == 'glowbar':                               # the bar follows the text width
        mid = _glow_mid(a, L, R, tw + 2)
    out = Image.fromarray(np.concatenate([a[:, :L], mid, a[:, R:]], 1), 'RGBA')
    mask = Image.new('L', out.size)
    ImageDraw.Draw(mask).text((L - font.getbbox(text)[0] + 1, y0 - font.getbbox('H')[1]), text, font=font, fill=255)
    if style == 'glowbar':
        sh = Image.new('RGBA', out.size, (0, 0, 0, 0))
        sh.putalpha(mask.filter(ImageFilter.GaussianBlur(h * .03)).point(lambda v: int(v * .6)))
        out.alpha_composite(sh, (0, int(h * .015)))
    txt = Image.new('RGBA', out.size, ink + (0,)); txt.putalpha(mask)
    out.alpha_composite(txt)
    return out


def _glow_mid(a, L, R, n):
    """Glow Bar: `n` columns for the new text: the old text cleared, the bar
    (and its glow) resampled from the old text span."""
    seg = a[:, L:R].copy()
    h = a.shape[0]
    rgb = seg[..., :3].astype(int); sat = rgb.max(2) - rgb.min(2)
    bar = np.where(((sat > 60) & (seg[..., 3] > 150)).sum(1) > seg.shape[1] * .2)[0]
    top = (bar.min() - int(h * .06)) if len(bar) else int(h * .7)
    seg[:top] = 0
    return np.array(Image.fromarray(seg, 'RGBA').resize((n, h), Image.BILINEAR))
