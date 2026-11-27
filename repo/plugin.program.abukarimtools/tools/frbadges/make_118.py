# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""resource.images.af3.frbadges 1.0.18 from FR-Badges HEAD (2026-11-27).

  python3 make_118.py FR-Badges-dir frbadges-resources-dir ab-tools-dir

- solid        rebuilt: FR-Badges' Solid is now flat single-colour pills
- glassvibrant new: Glass Vibrant (the glossy candy pills Solid had until now)
- pastel / glowbar / pixel  new single-line styles (single_line.py)
- DD+ / Atmos DD+ refreshed in the styles that use FR's new artwork
- IMAX.png back in every style's lucent_player/ (make_imax_fill.py), Neon
  Icon's DV2 redrawn
- aspect ratios 1.00 1.19 1.43 1.50 1.90 put back in every style (lost in
  the 1.0.15 rebuild; Kodi 22 names them - see make_aspect.py)

Folder layout per style is the existing glass/ layout (every file the skin
reads); files FR-Badges has no picture for stay the classic fallback copies
the other styles carry. The ISO / DV2 / IMAX / uniform-width / extra-pill
passes run with the existing scripts on a scratch copy of the new styles."""
import os, sys, shutil, subprocess, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FR, RES, AB = sys.argv[1], sys.argv[2], sys.argv[3]
LUCENT = os.path.join(AB, 'resources', 'lucent', 'media', 'lucent', 'flags')
H = 110
import single_line as SL
import relabel as RL

PILL = {'solid': 'Badges-Solid', 'glassvibrant': 'Badges-Glass-Vibrant'}
LINE = {'pastel': 'Badges-Pastel', 'glowbar': 'Badges-Glow-Bar', 'pixel': 'Badges-Pixel'}
NEW = dict(PILL, **LINE)
# FR-Badges HEAD (larger text, 0.22h side padding): Solid and Glass Vibrant share one layout,
# measured on their SDR / 2.0 / HDR badges
RL.GEO['solid'] = ('Badges-Solid', 0.215, 0.228, 0.52, 0.49, False, False)
RL.GEO['glassvibrant'] = ('Badges-Glass-Vibrant',) + RL.GEO['solid'][1:]
for k in ('pastel', 'glowbar', 'pixel'):
    RL.GEO.pop(k, None)

# make_res's mapping (classic file -> FR candidates) without its main loop
src = open(os.path.join(HERE, 'make_res.py'), encoding='utf-8').read()
src = src[src.index('H = 110'):src.index('def load(')]
ns = {}; exec(src, ns); M = ns['M']
M['other/language/fil'] = ['lang-fil', 'lang-tl']          # FR's Filipino flag is Tagalog's


def fr(folder, cands):
    for c in cands:
        p = os.path.join(FR, folder, c + '.png')
        if os.path.isfile(p):
            return p


def h110(im):
    w, h = im.size
    return im.resize((max(1, round(w * H / h)), H), Image.LANCZOS)


def conv(p):
    return h110(Image.open(p).convert('RGBA'))


def label_badge(style, base, text):
    """A badge reading `text`, drawn on `base` (an FR file name) of this style."""
    p = os.path.join(FR, NEW[style], base + '.png')
    if style in LINE:
        return SL.draw(style, p, text)
    return RL.relabel(style, p, text)


GLASS = os.path.join(RES, 'glass')
RELS = []
for root, _d, files in os.walk(GLASS):
    for f in files:
        rel = os.path.relpath(os.path.join(root, f), GLASS).replace(os.sep, '/')
        if f.endswith('.png') and not rel.startswith(('lucent_player/', 'aspectratio/')):
            RELS.append(rel[:-4])

CHAN = {'channels/4': '4.0', 'channels/5': '4.1'}
RATIOS = ('1.00', '1.19', '1.33', '1.37', '1.43', '1.50', '1.66', '1.78', '1.85', '1.90',
          '2.00', '2.02', '2.20', '2.35', '2.39', '2.40', '2.55', '2.76')

# ---------------------------------------------------------------- main sets
for style, folder in NEW.items():
    out = os.path.join(RES, style)
    shutil.rmtree(out, ignore_errors=True)
    made = fb = drawn = 0
    for rel in RELS:
        dst = os.path.join(out, rel + '.png'); os.makedirs(os.path.dirname(dst), exist_ok=True)
        p = fr(folder, M.get(rel, []))
        if p:
            conv(p).save(dst); made += 1
        elif rel in CHAN:
            h110(label_badge(style, '2-0', CHAN[rel])).save(dst); drawn += 1
        else:                                               # the classic fallback every style carries
            shutil.copyfile(os.path.join(GLASS, rel + '.png'), dst); fb += 1
    ar = os.path.join(out, 'aspectratio'); os.makedirs(ar, exist_ok=True)
    for f in ('fallback.png', '0.00.png'):
        shutil.copyfile(os.path.join(GLASS, 'aspectratio', f), os.path.join(ar, f))
    for r in RATIOS:
        h110(label_badge(style, 'sdr', r)).save(os.path.join(ar, r + '.png'))
    print(style, 'mapped', made, 'drawn', drawn, 'fallback', fb)

# ---------------------------------------------------------- lucent_player
lp_src = open(os.path.join(HERE, 'make_lp.py'), encoding='utf-8').read()
lp_src = lp_src[:lp_src.index('for style, folder in STY.items():')]
sys.argv = [sys.argv[0], FR, '', RES, LUCENT]
lp = {'__file__': os.path.join(HERE, 'make_lp.py')}
exec(compile(lp_src, 'make_lp', 'exec'), lp)
lp['PH'] = lp['CH']                 # 1.0.15+: pills fill the 176x68 box (fit, then uniform width)
SRC, LABEL, tight, compact, place, MAXR = lp['SRC'], lp['LABEL'], lp['tight'], lp['compact'], lp['place'], lp['MAXR']
SRC = dict(SRC)
SRC.update({'8-BIT': ['8bit'], '10-BIT': ['10bit', 'hdr-10bit'], '12-BIT': ['12bit', 'hdr-12bit'],
            'MKV': ['mkv'], 'TS': ['ts'], 'AVI': ['avi'], 'MULTI': ['multi-audio']})
LABEL = dict(LABEL, MULTI='MULTI AUDIO')

# single-line styles: (FR file, words kept) or (FR file to draw on, text)
KEEP = {'4K': ('4k', [0]), '8K': ('8k', [0]), '1080P': ('1080p', [0]), '720P': ('720p', [0]), 'SD': ('480p', [0]),
        'HEVC': ('hevc', [0]), 'AVC': ('avc', [0]), 'ATMOS': ('atmos', [1]), 'TRUEHD': ('truehd', [1]),
        'PCM': ('pcm', [0]), '7.1': ('7-1', [0]), '6.1': ('6-1', [0]), '5.1': ('5-1', [0]), '2.0': ('2-0', [0]),
        '1.0': ('1-0', [0]), 'PDTV': ('source-tvrip', [0]), 'DVDRIP': ('source-dvd', [0]), 'SCR': ('scr', [0]),
        'HC': ('hc-hdrip', [0]), 'TS': ('ts', [1]), 'MULTI': ('multi-audio', [0]),
        'DTS-HD': ('dtshd-hra', [0])}
DRAW = {'DV': ('dolby-vision', 'DV'), 'DV2': ('dolby-vision', 'DV 2'), 'DD+': ('ddplus', 'DD+'), 'DD': ('dd', 'DD'),
        'DTS-HDMA': ('dtshd-hra', 'DTS-HD MA'), 'DTS-HDHR': ('dtshd-hra', 'DTS-HD HR'),
        'ISO': ('source-bluray', 'ISO'), 'IMAX': ('3d', 'IMAX')}


def line_lp(style, name):
    folder = NEW[style]
    if name in DRAW:
        b, t = DRAW[name]
        return place(SL.draw(style, os.path.join(FR, folder, b + '.png'), t))
    if name in KEEP:
        b, idx = KEEP[name]
        im = SL.keep(style, os.path.join(FR, folder, b + '.png'), idx, len(SL.TEXT[b].split()))
        if im is None:                                       # did not split into its words: write them
            words = SL.TEXT[b].split()
            im = SL.draw(style, os.path.join(FR, folder, b + '.png'), ' '.join(words[i] for i in idx))
        return place(im)
    return place(tight(Image.open(fr(folder, SRC[name])).convert('RGBA')))


for style, folder in NEW.items():
    d = os.path.join(RES, style, 'lucent_player'); os.makedirs(d, exist_ok=True)
    for name, cands in SRC.items():
        p = fr(folder, cands)
        if style in LINE:
            line_lp(style, name).save(os.path.join(d, name + '.png'))
            continue
        if p is None:
            shutil.copyfile(os.path.join(LUCENT, name + '.png'), os.path.join(d, name + '.png'))
            continue
        # 1.0.15+ layout: the whole FR badge, scaled down to fit the box when wide
        place(tight(Image.open(p).convert('RGBA'))).save(os.path.join(d, name + '.png'))
    if style in LINE:
        for name in ('ISO', 'IMAX'):
            line_lp(style, name).save(os.path.join(d, name + '.png'))

# pill styles: ISO / DV2 / IMAX / uniform width with the existing scripts on a scratch copy
tmp = tempfile.mkdtemp()
for style in PILL:
    shutil.copytree(os.path.join(RES, style), os.path.join(tmp, style))
py = [sys.executable, '-I']
# uniform width first (the 1.0.15+ order), then ISO / DV2 / IMAX are written into the widened pills
uw = open(os.path.join(HERE, 'uniform_width.py'), encoding='utf-8').read().replace(
    "CENTRED = ('blackwhite', 'glass', 'light', 'solid', 'whiteblack')", "CENTRED = ('solid', 'glassvibrant', 'pastel')").replace(
    "ICON = ('frost', 'icondark', 'iconlight', 'minimal', 'split')", "ICON = ()")
shutil.copytree(os.path.join(RES, 'pastel'), os.path.join(tmp, 'pastel'))
uwp = os.path.join(tmp, '_uw.py'); open(uwp, 'w').write(uw)
subprocess.run(py + [uwp, tmp], check=True)
os.remove(uwp)
shutil.move(os.path.join(tmp, 'pastel'), os.path.join(tmp, '..', 'abk_pastel_tmp'))
subprocess.run(py + [os.path.join(HERE, 'make_iso.py'), tmp, os.path.join(LUCENT, 'ISO.png')], check=True)
dv = open(os.path.join(HERE, 'make_dv2_imax.py'), encoding='utf-8').read().replace(
    "BRIGHT = {'solid': 242}", "BRIGHT = {'solid': 242, 'glassvibrant': 242}")
dvp = os.path.join(tmp, '_dv2.py'); open(dvp, 'w').write(dv)
subprocess.run(py + [dvp, tmp] + list(PILL), check=True, cwd=HERE)
os.remove(dvp)
shutil.move(os.path.join(tmp, '..', 'abk_pastel_tmp'), os.path.join(tmp, 'pastel'))
for style in list(PILL) + ['pastel']:
    shutil.rmtree(os.path.join(RES, style)); shutil.copytree(os.path.join(tmp, style), os.path.join(RES, style))
shutil.rmtree(tmp)

# ------------------------------------------- DD+ / Atmos DD+ in the older styles
OLD = {'glass': 'Badges', 'blackwhite': 'Badges-Black-White', 'whiteblack': 'Badges-White-Black', 'light': 'Badges-Light',
       'lucent': 'Badges-Text-White'}
# (Text White / Black keep 1.0.17's: their other badges come from an older FR text set and
#  the new DD+ would stand larger than DD next to it)
from make_res_lp import lucent_pill
for style, folder in OLD.items():
    for rel, cands in (('audio/eac3', M['audio/eac3']), ('audio/eac3_ddp_atmos', M['audio/eac3_ddp_atmos'])):
        p = fr(folder, cands)
        im = Image.open(p).convert('RGBA')
        if style == 'lucent':
            im = lucent_pill(im)
        h110(im).save(os.path.join(RES, style, rel + '.png'))
    if style == 'lucent':
        continue                                            # its player pills are the Lucent pills
    p = fr(folder, SRC['DD+'])
    im = tight(Image.open(p).convert('RGBA'))
    dst = os.path.join(RES, style, 'lucent_player', 'DD+.png')
    place(im).save(dst)
    if style in ('blackwhite', 'glass', 'light', 'whiteblack'):
        g = {}; exec(open(os.path.join(HERE, 'uniform_width.py'), encoding='utf-8').read().split('for style in CENTRED')[0]
                     .replace('RES = sys.argv[1]', 'RES = None'), g)
        g['widen_badge'](dst, True)
# Neon Icon's DV2 read a giant "DV" since 1.0.15: redrawn as DOLBY / VISION 2 like the other styles
tmp = tempfile.mkdtemp()
shutil.copytree(os.path.join(RES, 'neonicon'), os.path.join(tmp, 'neonicon'))
dv = open(os.path.join(HERE, 'make_dv2_imax.py'), encoding='utf-8').read().replace(
    "'DV 2' if style == 'neonicon' else 'VISION 2'", "'VISION 2'")
dvp = os.path.join(tmp, '_dv2.py'); open(dvp, 'w').write(dv)
subprocess.run(py + [dvp, tmp, 'neonicon'], check=True)
shutil.copyfile(os.path.join(tmp, 'neonicon', 'lucent_player', 'DV2.png'), os.path.join(RES, 'neonicon', 'lucent_player', 'DV2.png'))
shutil.rmtree(tmp)
print('ok')
