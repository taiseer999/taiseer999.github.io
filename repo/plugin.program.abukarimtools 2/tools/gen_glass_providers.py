"""B&W glass debrid service icons for Search All (4.8.58).

resources/lucent/media/lucent/providers/*.png  ->  .../providers_bw/*.png
Same rule as tools/gen_glass_icons.py (white, no background, coloured parts
frosted where the logo also has white parts), plus a thin cut where two
colours meet, so logos made only of colour areas (Premiumize: figure +
tick, TorBox: cube faces) keep their shapes in one colour.
"""
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'resources', 'lucent', 'media', 'lucent', 'providers')
DST = os.path.join(ROOT, 'resources', 'lucent', 'media', 'lucent', 'providers_bw')
SIZE = 192
GLASS = 0.45

import importlib.util
_spec = importlib.util.spec_from_file_location('gi', os.path.join(ROOT, 'tools', 'gen_glass_icons.py'))
gi = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gi)


def convert(path):
    big = 4 * SIZE
    gi.SIZE = big
    out = np.asarray(gi.convert(path)).copy()
    # colour edges: where neighbouring opaque pixels differ a lot in colour
    rgb = np.asarray(Image.open(path).convert('RGB').resize((big, big), Image.LANCZOS)).astype(np.float32)
    k = 6                     # upscaled source: compare pixels k apart
    dx = np.abs(rgb[:, k:] - rgb[:, :-k]).max(axis=2)
    dy = np.abs(rgb[k:, :] - rgb[:-k, :]).max(axis=2)
    edge = np.zeros((big, big), bool)
    edge[:, k // 2:big - k + k // 2] |= dx > 125
    edge[k // 2:big - k + k // 2, :] |= dy > 125
    a = out[..., 3]
    solid = a > 200
    cut = edge & solid
    # only inside the logo, never its outline
    inner = np.asarray(Image.fromarray((solid * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(9))) > 0
    m = Image.fromarray(((cut & inner) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    a[np.asarray(m) > 0] = 0
    out[..., 3] = a
    return Image.fromarray(out, 'RGBA').resize((SIZE, SIZE), Image.LANCZOS)


def main():
    os.makedirs(DST, exist_ok=True)
    for f in sorted(os.listdir(SRC)):
        if f.endswith('.png'):
            convert(os.path.join(SRC, f)).save(os.path.join(DST, f), optimize=True)
    print('providers_bw:', len(os.listdir(DST)))


if __name__ == '__main__':
    main()
