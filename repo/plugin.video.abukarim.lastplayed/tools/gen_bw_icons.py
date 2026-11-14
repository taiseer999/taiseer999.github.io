"""Black & white glass menu icons of Last Played (1.0.16), same look as
AB Tools / AB Wizard glass icons and Search All's service logos.

resources/media/<menu icon>.orig.png  ->  resources/media/<menu icon>.png
- background = colour of the icon's border, removed
- every other pixel becomes white; its alpha follows how far it is from
  the background (so dim greys stay dim, e.g. a toggle's off track)
- in icons that also carry solid white parts, the coloured parts become
  frosted glass (45 %) so the white parts (toggle knob, heart, page)
  still read on top of them
"""
import os, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, 'resources', 'media')
NAMES = ('all', 'movies', 'episodes', 'inprogress', 'clear', 'support')
SIZE = 256
GLASS = 0.45


def convert(path):
    im = Image.open(path).convert('RGB').resize((SIZE, SIZE), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    d = np.abs(a - bg).max(axis=2)
    alpha = np.clip((d - 0.07) / 0.33, 0, 1)
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    white = (sat < 0.18) & (mx > 0.78)
    coloured = (sat > 0.35) & (alpha > 0.5)
    if white.sum() > 0.01 * coloured.sum() and white.sum() > SIZE * SIZE * 0.002:
        # two-tone: coloured parts frosted, white parts solid
        k = np.clip((sat - 0.18) / 0.3, 0, 1)
        alpha = alpha * (1 - k * (1 - GLASS))
    out = np.zeros((SIZE, SIZE, 4), np.uint8)
    out[..., :3] = 255
    out[..., 3] = (alpha * 255).round().astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def main():
    """Put the colour originals in resources/media as <name>.orig.png first
    (they are not shipped); the shipped <name>.png are already converted."""
    for n in NAMES:
        dst = os.path.join(MEDIA, n + '.png')
        orig = os.path.join(MEDIA, n + '.orig.png')
        if not os.path.isfile(orig):
            print('skip %s: no %s.orig.png' % (n, n))
            continue
        convert(orig).save(dst, optimize=True)
    print('b&w menu icons:', len(NAMES))


if __name__ == '__main__':
    main()
