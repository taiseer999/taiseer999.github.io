"""Palette-compress every PNG in place (libimagequant, visually lossless)."""
import os, sys
import imagequant
from PIL import Image
n = 0
for root in sys.argv[1:]:
    for d, _s, fs in os.walk(root):
        for f in fs:
            if not f.endswith('.png'):
                continue
            p = os.path.join(d, f)
            try:
                im = Image.open(p).convert('RGBA')
                q = imagequant.quantize_pil_image(im, dithering_level=1.0, max_colors=256, min_quality=70, max_quality=95)
                tmp = p + '.tmp'; q.save(tmp, format='PNG', optimize=True)
                if os.path.getsize(tmp) < os.path.getsize(p):
                    os.replace(tmp, p); n += 1
                else:
                    os.remove(tmp)
            except Exception as e:
                print('skip', p, e)
print('quantized', n)
