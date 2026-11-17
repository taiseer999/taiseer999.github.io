# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""4.9.9: the extra Lucent Player pills - bit depth, container, multi audio.

  python3 make_extra_lp.py FR-Badges-dir frbadges-resources-dir ab-tools-dir

FR styles take FR-Badges' own 8bit / 10bit / 12bit / mkv / ts / avi /
multi-audio badges through make_lp's fitting (tight / compact / place); the
Lucent look (and the classic colourful set, which has none of these) gets new
Lucent pills drawn on the MP4 pill."""
import os, sys, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FR, RES, AB = sys.argv[1], sys.argv[2], sys.argv[3]
LUCENT = os.path.join(AB, 'resources', 'lucent', 'media', 'lucent', 'flags')
LP_OFF = os.path.join(AB, 'resources', 'lucent_player', 'media', 'flags')

# make_lp's helpers without its main loop
src = open(os.path.join(HERE, 'make_lp.py'), encoding='utf-8').read()
src = src[:src.index('for style, folder in STY.items():')]
sys.argv = [sys.argv[0], FR, '', RES, LUCENT]
sys.path.insert(0, HERE)
ns = {'__file__': os.path.join(HERE, 'make_lp.py')}
exec(compile(src, 'make_lp', 'exec'), ns)
STY, tight, compact, place, MAXR = ns['STY'], ns['tight'], ns['compact'], ns['place'], ns['MAXR']

NEW = {'8-BIT': ['8bit'], '10-BIT': ['10bit', 'hdr-10bit'], '12-BIT': ['12bit', 'hdr-12bit'],
       'MKV': ['mkv', 'cont-mkv'], 'TS': ['ts', 'cont-ts'], 'AVI': ['avi', 'cont-avi'],
       'MULTI': ['multi-audio', 'flag-multi-audio']}
LABEL = {'MULTI': 'MULTI AUDIO'}
BOLD = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
SEMI = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'


def lucent_pill(name):
    base = Image.open(os.path.join(LUCENT, 'MP4.png')).convert('RGBA')
    a = np.array(base)
    a[:, 22:154] = a[:, 21:22]                       # wipe the label: repeat a clean column
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im)
    W, H = im.size
    if name == 'MULTI':
        f1 = ImageFont.truetype(BOLD, 26); f2 = ImageFont.truetype(SEMI, 12)
        for text, f, cy in (('MULTI', f1, 28), ('AUDIO', f2, 49)):
            bb = f.getbbox(text)
            d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], cy - (bb[1] + bb[3]) / 2), text, font=f, fill=(255, 255, 255, 255))
    else:
        size = 31
        while True:
            f = ImageFont.truetype(BOLD, size)
            bb = f.getbbox(name)
            if bb[2] - bb[0] <= 136 or size <= 18:
                break
            size -= 1
        d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], 33.5 - (bb[1] + bb[3]) / 2), name, font=f, fill=(255, 255, 255, 255))
    return im


made = {}
for n in NEW:
    made[n] = lucent_pill(n)
    for d in (LUCENT, LP_OFF, os.path.join(RES, 'lucent', 'lucent_player'), os.path.join(RES, 'colorful', 'lucent_player')):
        os.makedirs(d, exist_ok=True)
        made[n].save(os.path.join(d, n + '.png'), optimize=True)

for style, folder in STY.items():
    d = os.path.join(RES, style, 'lucent_player')
    for name, cands in NEW.items():
        p = next((q for q in (os.path.join(FR, folder, c + '.png') for c in cands) if os.path.isfile(q)), None)
        if p is None:
            made[name].save(os.path.join(d, name + '.png'), optimize=True)
            print('lucent pill for', style, name)
            continue
        im = tight(Image.open(p).convert('RGBA'))
        if im.width / im.height > MAXR:
            im = compact(style, p, LABEL.get(name, name))
        place(im).save(os.path.join(d, name + '.png'), optimize=True)
print('ok')
