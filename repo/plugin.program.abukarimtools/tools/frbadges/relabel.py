"""Redraw an FR badge with another label, keeping its icon, pill and colours
(used for the aspect-ratio badges and the compact Lucent Player badges of the
styles added in 4.8.75). Geometry measured on each style's SDR badge."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
# style: (folder, text start / h, right pad / h, caps height / h, caps centre / h, dark text, text shadow)
GEO = {
    'solid':     ('Badges-Solid',      0.275, 0.294, 0.476, 0.50, False, False),
    'icondark':  ('Badges-Icon-Dark',  1.055, 0.298, 0.301, 0.49, False, False),
    'split':     ('Badges-Split',      1.094, 0.288, 0.301, 0.49, False, False),
    'frost':     ('Badges-Frost',      0.880, 0.298, 0.301, 0.49, False, False),
    'neonicon':  ('Badges-Neon-Icon',  1.196, 0.239, 0.505, 0.47, False, False),
    'iconlight': ('Badges-Icon-Light', 1.055, 0.298, 0.301, 0.49, True,  False),
    'textwhite': ('Badges-Text-White', 0.175, 0.188, 0.476, 0.50, False, True),
    'textblack': ('Badges-Text-Black', 0.152, 0.168, 0.476, 0.50, True,  True),
}
_CAP = None


def _cap_ratio():
    global _CAP
    if _CAP is None:
        f = ImageFont.truetype(FONT, 1000); bb = f.getbbox('H'); _CAP = (bb[3] - bb[1]) / 1000.0
    return _CAP


def _colours(a, x0, x1, dark):
    h = a.shape[0]
    reg = a[:, x0:x1].astype(int); lum = reg[..., :3].mean(2)
    m = ((lum < 90) if dark else (lum > 190)) & (reg[..., 3] > 200)
    m[:int(h * .15)] = False; m[int(h * .85):] = False
    rows = np.where(m.any(1))[0]
    if not len(rows):
        c = (20, 20, 25) if dark else (245, 245, 245)
        return c, c
    r0, r1 = rows.min(), rows.max(); q = max(1, (r1 - r0) // 4)
    top = reg[r0:r0 + q][m[r0:r0 + q]][:, :3].mean(0); bot = reg[r1 - q:r1 + 1][m[r1 - q:r1 + 1]][:, :3].mean(0)
    return tuple(int(v) for v in top), tuple(int(v) for v in bot)


def relabel(style, src, label, max_ratio=None):
    folder, xt, rp, capf, cyf, dark, shadow = GEO[style]
    im = Image.open(src).convert('RGBA'); w, h = im.size; a = np.array(im)
    xL = max(1, int(xt * h) - 10); xR = min(w - 1, int(w - rp * h) + 10)
    c_top, c_bot = _colours(a, xL, xR, dark)
    size = int(capf * h / _cap_ratio())
    font = ImageFont.truetype(FONT, size)
    if max_ratio:
        room = max_ratio * h - xL - (w - xR) - 20
        while font.getlength(label) > room and size > 20:
            size -= 4; font = ImageFont.truetype(FONT, size)
    tw = int(font.getlength(label))
    mid = max(20, tw + 20)
    out = Image.new('RGBA', (xL + mid + (w - xR), h))
    out.paste(im.crop((0, 0, xL, h)), (0, 0))
    L = a[:, xL - 1].astype(float); R = a[:, xR].astype(float)
    for i in range(mid):
        t = i / max(1, mid - 1)
        out.paste(Image.fromarray(((1 - t) * L + t * R).round().astype(np.uint8)[:, None, :], 'RGBA'), (xL + i, 0))
    out.paste(im.crop((xR, 0, w, h)), (xL + mid, 0))
    bb = font.getbbox('H'); x = xL + 10; y = cyf * h - (bb[1] + bb[3]) / 2
    mask = Image.new('L', out.size); ImageDraw.Draw(mask).text((x, y), label, font=font, fill=255)
    if shadow:
        sh = Image.new('RGBA', out.size, (255, 255, 255, 0) if dark else (0, 0, 0, 0))
        sh.putalpha(mask.filter(ImageFilter.GaussianBlur(h * .02)).point(lambda v: int(v * .55)))
        out.alpha_composite(sh, (0, int(h * .012)))
    g = np.zeros((h, out.width, 3), np.uint8)
    ys = np.where(np.array(mask).any(1))[0]; y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, h)
    for yy in range(h):
        t = min(1, max(0, (yy - y0) / max(1, y1 - y0)))
        g[yy] = (np.array(c_top) + (np.array(c_bot) - np.array(c_top)) * t).astype(np.uint8)
    txt = Image.fromarray(g).convert('RGBA'); txt.putalpha(mask)
    out.alpha_composite(txt)
    return out
