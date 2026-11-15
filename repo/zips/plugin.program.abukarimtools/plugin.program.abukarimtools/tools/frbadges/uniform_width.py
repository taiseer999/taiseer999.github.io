# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""Uniform chips: in the pill styles every lucent_player/ badge is widened to
the full 176 px canvas, so the Lucent Player rows have even gaps (a Kodi
image slot is fixed-width; a narrow badge such as 7.1 or 3D left wide empty
margins). Per badge: the label rows are rebuilt as a clean pill (each column
blended from the clean row above to the clean row below), the clean pill is
stretched in its middle, and the label (text + icon, lifted from the original
by its difference to the clean pill) is put back - centred, or kept at the
left in the icon styles."""
import os, sys
import numpy as np
from PIL import Image
RES = sys.argv[1]
CENTRED = ('blackwhite', 'glass', 'light', 'solid', 'whiteblack')
ICON = ('frost', 'icondark', 'iconlight', 'minimal', 'split')
CW = 176


def widen_badge(path, centred):
    a = np.array(Image.open(path).convert('RGBA')).astype(float)
    h, w = a.shape[:2]
    alpha = a[..., 3]
    cols = np.where((alpha > 20).any(0))[0]
    rows = np.where((alpha > 20).any(1))[0]
    if not len(cols):
        return False
    pl, pr, pt, pb = cols[0], cols[-1], rows[0], rows[-1]
    band = CW - (pr - pl + 1)
    if band < 6:
        return False
    ph = pb - pt + 1
    cap = int(ph * .42)
    # clean pill: rows inside the pill rebuilt from a thin band at its top and bottom
    ya, yb = pt + max(3, int(ph * .07)), pb - max(3, int(ph * .07))
    clean = a.copy()
    midrow = a[(pt + pb) // 2, :, 3]
    full = 0.9 * np.median(midrow[midrow > 20])     # a translucent pill (frost) is ~175, not 255
    inner = np.where((a[ya - 1, :, 3] >= full) & (a[yb + 1, :, 3] >= full))[0]   # inside the pill at both rows
    if len(inner) < 8:
        return False
    fl, fr = inner[0], inner[-1]                     # the thin round ends outside them stay as drawn
    top, bot = a[ya - 1, fl:fr + 1], a[yb + 1, fl:fr + 1]
    for y in range(ya, yb + 1):
        t = (y - ya + 1) / float(yb - ya + 2)
        clean[y, fl:fr + 1] = (1 - t) * top + t * bot
    clean[..., 3] = a[..., 3]
    # label = what differs from the clean pill
    diff = np.abs(a[..., :3] - clean[..., :3]).max(2)
    lab = np.clip((diff - 16) / 40.0, 0, 1)
    lab[:pt] = lab[pb + 1:] = 0
    lab[a[..., 3] < full] = 0
    lc = np.where((lab > .3).any(0))[0]
    if not len(lc):
        return False
    c0, c1 = max(pl, lc[0] - 2), min(pr, lc[-1] + 2)
    # stretch the clean pill: 2 columns in its flat middle
    mid = (fl + fr) // 2 if centred else (c1 + fr) // 2
    mid = int(min(max(mid, fl + 2), fr - 2))
    seg = Image.fromarray(clean[:, mid - 1:mid + 1].round().astype(np.uint8), 'RGBA')
    seg = np.array(seg.resize((2 + band, h), Image.BILINEAR)).astype(float)
    wide = np.concatenate([clean[:, :mid - 1], seg, clean[:, mid + 1:]], 1)
    shift = band // 2 if centred else 0
    nc0 = c0 - pl
    if not centred and c1 >= mid:            # label runs past the stretch point: keep it whole
        shift = 0
    out = wide[:, pl:pl + CW].copy()
    src = a[:, c0:c1 + 1]; al = lab[:, c0:c1 + 1][..., None]
    x = nc0 + shift
    out[:, x:x + src.shape[1], :3] = al * src[..., :3] + (1 - al) * out[:, x:x + src.shape[1], :3]
    out[:, x:x + src.shape[1], 3] = np.maximum(out[:, x:x + src.shape[1], 3], src[..., 3] * al[..., 0])
    Image.fromarray(out.round().clip(0, 255).astype(np.uint8), 'RGBA').save(path, optimize=True)
    return True


for style in CENTRED + ICON:
    lp = os.path.join(RES, style, 'lucent_player')
    n = sum(widen_badge(os.path.join(lp, f), style in CENTRED) for f in sorted(os.listdir(lp)) if f.endswith('.png'))
    print(style, n, 'widened')
