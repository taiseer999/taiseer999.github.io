# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""1.0.18: IMAX.png back in every style's lucent_player/ (the 1.0.15 rebuild
dropped it; AF3's Lucent Player shows $VAR[ABK_LP_FlagDir]/IMAX.png since
4.8.88). FR styles: make_iso's wipe-and-write on the style's 3D pill; lucent /
colorful: the AB Tools Lucent IMAX pill.  python3 make_imax_fill.py RES LUCENT_FLAGS [skip-style ...]"""
import os, sys, shutil
RES, LUCENT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
# make_iso's wipe-and-write, on the style's own (widened) 3D pill, shrunk to fit
iso = open(os.path.join(here, 'make_iso.py'), encoding='utf-8').read().split('for style in sorted(os.listdir(RES)):')[0]
BASE = os.environ.get('ABK_BASE', '3D.png'); WORDX = os.environ.get('ABK_WORD', 'IMAX'); OUTN = WORDX + '.png'
iso = iso.replace("'BLURAY.png'", 'BASE').replace("font.getbbox('ISO')", "font.getbbox(WORD)").replace(
    "'ISO', font=font", "WORD, font=font").replace(
    "    bb = font.getbbox(WORD); tw = bb[2] - bb[0]\n",
    "    bb = font.getbbox(WORD); tw = bb[2] - bb[0]\n"
    "    while tw > (w - x0 - 10 if style in ICON else w * .78) and size > 12:\n"
    "        size -= 2; font = ImageFont.truetype(FONT, size); bb = font.getbbox(WORD); tw = bb[2] - bb[0]\n"
    "        y0 = y0 + 1\n").replace(
    "    x = cx - tw / 2.0 - bb[0]",
    "    x = (x0 - bb[0]) if style in ICON else (cx - tw / 2.0 - bb[0])")   # icon styles: start at the label, clear of the icon
argv = sys.argv; sys.argv = [argv[0], RES, '']
g = {'__name__': 'make_iso', 'WORD': WORDX, 'BASE': BASE,
     'ICON': {'frost', 'icondark', 'iconlight', 'minimal', 'split', 'neonicon'}}; exec(iso, g); sys.argv = argv
SKIP = set(a for a in sys.argv[3:] if not a.startswith('+'))
ONLY = set(a[1:] for a in sys.argv[3:] if a.startswith('+'))                         # styles whose IMAX is already drawn (single-line styles)
for style in sorted(os.listdir(RES)):
    lp = os.path.join(RES, style, 'lucent_player'); dst = os.path.join(lp, OUTN)
    if not os.path.isdir(lp) or style in SKIP or (ONLY and style not in ONLY):
        continue
    if style in ('lucent', 'colorful'):
        shutil.copyfile(os.path.join(LUCENT, OUTN), dst)
    else:
        g['make'](style).save(dst, optimize=True)
    print(style)
