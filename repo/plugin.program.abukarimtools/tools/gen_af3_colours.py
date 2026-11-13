# -*- coding: utf-8 -*-
"""Generate the textures of the AF3 Lucent Look "Colours" window (AB Tools 4.8.48).

Dev tool (not used at runtime). Output: resources/skins/Default/media/abk_col/
  card_<scheme>.png   preview card of every colour scheme (gradient, a mini
                      dialog in the scheme's highlight colour, label strip)
  card_focus.png      rounded outline drawn over the focused card
  badge.png           amber check badge of the selected card
  circle.png / ring.png / check.png   colour swatches
  panel.png / panel_edge.png / pill.png / pill_edge.png   window frame
  palette.png / close.png             icons

The schemes (colours, card corners) live in resources/lib/af3_lucent_schemes.py
(SCHEMES); this tool imports them so the cards always match.

Run from the addon root:  python3 tools/gen_af3_colours.py
"""
import importlib.util
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'resources', 'skins', 'Default', 'media', 'abk_col')
SS = 4                                   # supersampling

spec = importlib.util.spec_from_file_location(
    'cols', os.path.join(ROOT, 'resources', 'lib', 'af3_lucent_schemes.py'))
cols = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cols)


def rgb(h):
    h = h[-6:]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def rounded_mask(w, h, r):
    m = Image.new('L', (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), r * SS, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def save(img, name):
    img.save(os.path.join(OUT, name), optimize=True)


# Card: 684 x 440 (shown at 342 x 220), preview 348 + label strip 92.
CW, CH, PH, R = 684, 440, 348, 34


def card(scheme):
    tl, tr, bl, br = (rgb(c) for c in scheme['corners'])
    acc = rgb(scheme['focus'])
    img = Image.new('RGB', (CW, CH))
    px = img.load()
    for y in range(PH):
        ty = y / (PH - 1)
        left, right = lerp(tl, bl, ty), lerp(tr, br, ty)
        for x in range(CW):
            px[x, y] = lerp(left, right, x / (CW - 1))
    # label strip: the bottom colours, darkened
    for y in range(PH, CH):
        for x in range(CW):
            base = lerp(bl, br, x / (CW - 1))
            px[x, y] = tuple(int(c * 0.32) for c in base)
    d = ImageDraw.Draw(img, 'RGBA')
    s = CW / 572.0                                  # layout after the reference card
    def box(x, y, w, h):
        return (round(x * s), round(y * s * 1.0), round((x + w) * s), round((y + h) * s))
    d.rectangle(box(28, 31, 210, 31), fill=acc + (255,))
    d.rectangle(box(28, 89, 326, 161), fill=(0, 0, 0, 150))
    d.rectangle(box(56, 120, 233, 20), fill=(255, 255, 255, 120))
    d.rectangle(box(56, 162, 186, 20), fill=(255, 255, 255, 60))
    d.rectangle(box(56, 203, 94, 20), fill=acc + (255,))
    out = Image.new('RGBA', (CW, CH))
    out.paste(img, (0, 0), rounded_mask(CW, CH, R))
    save(out, 'card_%s.png' % scheme['id'])


def outline(w, h, r, width, name):
    m = Image.new('L', (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), r * SS,
                                        outline=255, width=width * SS)
    m = m.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    out.putalpha(m)
    save(out, name)


def filled(w, h, r, name):
    out = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    out.putalpha(rounded_mask(w, h, r))
    save(out, name)


def ellipse(size, name, ring=0):
    m = Image.new('L', (size * SS, size * SS), 0)
    dr = ImageDraw.Draw(m)
    if ring:
        dr.ellipse((0, 0, size * SS - 1, size * SS - 1), outline=255, width=ring * SS)
    else:
        dr.ellipse((0, 0, size * SS - 1, size * SS - 1), fill=255)
    out = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    out.putalpha(m.resize((size, size), Image.LANCZOS))
    save(out, name)


def check(size, name, colour=(255, 255, 255), bg=None):
    big = Image.new('RGBA', (size * SS, size * SS), (0, 0, 0, 0))
    dr = ImageDraw.Draw(big)
    if bg:
        dr.ellipse((0, 0, size * SS - 1, size * SS - 1), fill=bg + (255,))
    k = size * SS
    pts = [(0.30 * k, 0.52 * k), (0.44 * k, 0.65 * k), (0.71 * k, 0.37 * k)]
    dr.line(pts, fill=colour + (255,), width=int(0.085 * k), joint='curve')
    for p in (pts[0], pts[-1]):
        rr = 0.0425 * k
        dr.ellipse((p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr), fill=colour + (255,))
    save(big.resize((size, size), Image.LANCZOS), name)


def close_icon(size, name):
    big = Image.new('RGBA', (size * SS, size * SS), (0, 0, 0, 0))
    dr = ImageDraw.Draw(big)
    k = size * SS
    w = int(0.09 * k)
    dr.line([(0.22 * k, 0.22 * k), (0.78 * k, 0.78 * k)], fill=(255, 255, 255, 255), width=w)
    dr.line([(0.78 * k, 0.22 * k), (0.22 * k, 0.78 * k)], fill=(255, 255, 255, 255), width=w)
    save(big.resize((size, size), Image.LANCZOS), name)


def palette_icon(size, name):
    k = size * SS
    m = Image.new('L', (k, k), 0)
    dr = ImageDraw.Draw(m)
    dr.ellipse((0.08 * k, 0.10 * k, 0.92 * k, 0.90 * k), fill=255)
    # thumb notch + four paint holes
    dr.ellipse((0.50 * k, 0.56 * k, 0.74 * k, 0.80 * k), fill=0)
    for cx, cy in ((0.30, 0.42), (0.44, 0.27), (0.62, 0.27), (0.74, 0.42)):
        rr = 0.075 * k
        dr.ellipse((cx * k - rr, cy * k - rr, cx * k + rr, cy * k + rr), fill=0)
    out = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    out.putalpha(m.resize((size, size), Image.LANCZOS))
    save(out, name)


def build():
    os.makedirs(OUT, exist_ok=True)
    for sc in cols.SCHEMES:
        card(sc)
    outline(CW, CH, R, 6, 'card_focus.png')
    check(96, 'badge.png', colour=(20, 20, 24), bg=(0xF5, 0xA5, 0x24))
    ellipse(200, 'circle.png')
    ellipse(240, 'ring.png', ring=12)
    check(96, 'check.png')
    filled(96, 96, 40, 'panel.png')
    outline(96, 96, 40, 2, 'panel_edge.png')
    filled(140, 100, 50, 'pill.png')            # border="50,0,50,0"
    outline(140, 100, 50, 4, 'pill_edge.png')
    palette_icon(96, 'palette.png')
    close_icon(64, 'close.png')
    return sorted(os.listdir(OUT))


if __name__ == '__main__':
    for n in build():
        print(n)
