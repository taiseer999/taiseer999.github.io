# -*- coding: utf-8 -*-
"""Draw the AF3 "Lucent Look" player icons (AB Tools 4.6.14).

Dev tool (not used at runtime). Output: resources/af3_lucent/icons/*.png
(96 x 96, white on transparent; AF3 tints them with colordiffuse).

Our own drawings in the thin, rounded line style of the Lucent skin by
djdirty60 - the Lucent repository states no licence and calls its icons
original designs, so its PNG files are not copied.

Run:  python3 tools/gen_af3_lucent_icons.py
"""
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'resources', 'af3_lucent', 'icons')
S = 8                      # supersampling
N = 96
W = (255, 255, 255, 255)
STROKE = 7.5               # px at 96


def canvas():
    im = Image.new('RGBA', (N * S, N * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def p(*xy):
    return [v * S for v in xy]


def line(d, pts, w=STROKE):
    pts = [(x * S, y * S) for x, y in pts]
    d.line(pts, fill=W, width=int(w * S), joint='curve')
    r = w * S / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=W)


def rounded_poly(d, pts, r=5):
    """Filled polygon with softened corners (polygon + round joints)."""
    d.polygon([(x * S, y * S) for x, y in pts], fill=W)
    for i in range(len(pts)):
        line(d, [pts[i], pts[(i + 1) % len(pts)]], w=r)


def tri(d, x0, x1, cy, h):
    rounded_poly(d, [(x0, cy - h), (x1, cy), (x0, cy + h)])


def save(im, name):
    im.resize((N, N), Image.LANCZOS).save(os.path.join(OUT, name + '.png'))


def build():
    os.makedirs(OUT, exist_ok=True)
    made = []

    im, d = canvas(); tri(d, 33, 72, 48, 23); save(im, 'play'); made.append('play')

    im, d = canvas()
    d.rounded_rectangle(p(29, 24, 41, 72), radius=4 * S, fill=W)
    d.rounded_rectangle(p(55, 24, 67, 72), radius=4 * S, fill=W)
    save(im, 'pause'); made.append('pause')

    im, d = canvas(); tri(d, 18, 48, 48, 18); tri(d, 48, 78, 48, 18); save(im, 'forward'); made.append('forward')
    im, d = canvas(); tri(d, 48, 18, 48, 18); tri(d, 78, 48, 48, 18); save(im, 'rewind'); made.append('rewind')

    im, d = canvas(); tri(d, 70, 36, 48, 20); line(d, [(28, 28), (28, 68)]); save(im, 'prev'); made.append('prev')
    im, d = canvas(); tri(d, 26, 60, 48, 20); line(d, [(68, 28), (68, 68)]); save(im, 'next'); made.append('next')

    im, d = canvas(); d.rounded_rectangle(p(28, 28, 68, 68), radius=7 * S, fill=W); save(im, 'stop'); made.append('stop')

    im, d = canvas()
    d.ellipse(p(14, 14, 82, 82), outline=W, width=int(STROKE * S))
    line(d, [(48, 44), (48, 64)])
    d.ellipse(p(43.5, 28.5, 52.5, 37.5), fill=W)
    save(im, 'info'); made.append('info')

    im, d = canvas()                                   # waveform, like Lucent's audio
    for x, h in ((20, 10), (30, 22), (40, 32), (50, 18), (60, 28), (70, 14), (80, 6)):
        line(d, [(x - 2, 48 - h), (x - 2, 48 + h)], w=6.5)
    save(im, 'audio'); made.append('audio')

    im, d = canvas()                                   # subtitles: screen with two caption lines
    d.rounded_rectangle(p(12, 22, 84, 74), radius=10 * S, outline=W, width=int(STROKE * S))
    line(d, [(26, 50), (42, 50)], w=6); line(d, [(52, 50), (70, 50)], w=6)
    line(d, [(26, 61), (56, 61)], w=6); line(d, [(64, 61), (70, 61)], w=6)
    save(im, 'subtitles'); made.append('subtitles')

    im, d = canvas()                                   # video settings: three sliders
    for y, k in ((28, 60), (48, 36), (68, 54)):
        line(d, [(16, y), (80, y)], w=6)
        d.ellipse(p(k - 8, y - 8, k + 8, y + 8), fill=W)
    save(im, 'video'); made.append('video')

    im, d = canvas()
    for y in (28, 48, 68):
        line(d, [(18, y), (78, y)])
    save(im, 'list'); made.append('list')

    im, d = canvas()                                   # live / record
    d.ellipse(p(14, 14, 82, 82), outline=W, width=int(STROKE * S))
    d.ellipse(p(34, 34, 62, 62), fill=W)
    save(im, 'record'); made.append('record')

    return made


if __name__ == '__main__':
    for n in build():
        print(n)
