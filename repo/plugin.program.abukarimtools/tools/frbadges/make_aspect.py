# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""The aspect-ratio badges Kodi 22 can name that the styles lack (1.00, 1.19,
1.43, 1.50, 1.90 - Kodi's built-in vocabulary, utils/AspectRatioVocabulary.cpp),
drawn from each style's own aspectratio/1.78.png with the number replaced
(same font size, place and colours; reuses make_dv2_imax.redraw)."""
import os, sys
RES = sys.argv[1]
NEW = ('1.00', '1.19', '1.43', '1.50', '1.90')
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, 'make_dv2_imax.py')).read().split('for style in sorted(os.listdir(RES)):')[0]
g = {'__name__': 'make_dv2_imax', 'sys': sys}
sys_argv = sys.argv; sys.argv = [sys.argv[0], RES]
exec(src, g)
sys.argv = sys_argv
from PIL import Image
g['BRIGHT']['solid'] = 225
g['NO_WIDEN'] = True                                # ratio badges keep their pill size                          # solid's ratio text is ~234 on a pill up to ~202
_fit = g['fit']


def fit_same(img):
    """Same layout as the source badge: no crop / re-centre (a narrower number
    such as 1.19 must not be scaled up)."""
    if img.width == 3 * g['CW'] and img.height == 3 * g['CH']:
        return img.resize((g['CW'], g['CH']), Image.LANCZOS)
    return _fit(img)


g['fit'] = fit_same
for style in sorted(os.listdir(RES)):
    folder = os.path.join(RES, style, 'aspectratio')
    base = os.path.join(folder, '1.78.png')
    if not os.path.exists(base):
        continue
    w, h = Image.open(base).size
    g['CW'], g['CH'] = w, h                          # keep the folder's own canvas size
    for label in NEW:
        dst = os.path.join(folder, label + '.png')
        if os.path.exists(dst):
            continue
        im = g['redraw'](style, os.path.join('..', 'aspectratio', '1.78.png'), label)
        im.save(dst, optimize=True)
    print(style)
