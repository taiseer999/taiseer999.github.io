import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FR, OUT = sys.argv[1], sys.argv[2]
F = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
H = 110
CFG = {  # folder, left cap end, strip col, right cap start, text color, font size, caps-top y, text start x
 'glass':      ('Badges',            70, 75, 480, (248,249,251), 206, 75, 85),
 'whiteblack': ('Badges-White-Black',70, 75, 480, (10,10,10),    206, 75, 85),
 'blackwhite': ('Badges-Black-White',70, 75, 480, (248,248,248), 206, 75, 85),
 'light':      ('Badges-Light',      70, 75, 480, (15,27,46),    206, 75, 85),
 'minimal':    ('Badges-Minimal',   180,182, 450, (255,255,255), 128,105,190),
}
def caps_off(font):  # offset from draw y to top of caps
    return font.getbbox('H')[1]
def pill(style, text):
    folder, lc, sc, rc, col, size, ytop, tx = CFG[style]
    base = Image.open(f'{FR}/{folder}/sdr.png').convert('RGBA')
    w, h = base.size
    font = ImageFont.truetype(F, size)
    tw = font.getlength(text)
    mid = int(tx + tw - lc + (rc - (tx + font.getlength('SDR')) ) * 0 + 30)
    mid = max(mid, 10)
    out = Image.new('RGBA', (lc + mid + (w - rc), h))
    out.paste(base.crop((0, 0, lc, h)), (0, 0))
    a = np.array(base).astype(float); L = a[:, sc]; R = a[:, rc - 2]
    for i, x in enumerate(range(lc, lc + mid)):
        t = i / max(1, mid - 1)
        out.paste(Image.fromarray(((1 - t) * L + t * R).round().astype(np.uint8)[:, None, :], 'RGBA'), (x, 0))
    out.paste(base.crop((rc, 0, w, h)), (lc + mid, 0))
    d = ImageDraw.Draw(out)
    d.text((tx, ytop - caps_off(font)), text, font=font, fill=col + (255,))
    return out
def neon(text):
    font = ImageFont.truetype(F, 150)
    tw = int(font.getlength(text)); h = int(227 * 309 / 227)
    w = tw + 80
    mask = Image.new('L', (w, h)); ImageDraw.Draw(mask).text((40, (h - 110) // 2 - caps_off(font)), text, font=font, fill=255)
    grad = np.zeros((h, w, 3), np.uint8); top, bot = np.array([235, 250, 255]), np.array([80, 200, 255])
    for y in range(h): grad[y] = (top + (bot - top) * y / h).astype(np.uint8)
    txt = Image.fromarray(grad).convert('RGBA'); txt.putalpha(mask)
    glow = Image.new('RGBA', (w, h), (60, 180, 255, 0)); glow.putalpha(mask.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .7)))
    out = Image.new('RGBA', (w, h)); out.alpha_composite(glow); out.alpha_composite(txt)
    return out
def lucent(text):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from make_res_lp import lucent_pill
    font = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf', 200)
    w = int(font.getlength(text)) + 20; im = Image.new('RGBA', (w, 309))
    ImageDraw.Draw(im).text((10, 155 - 72 - caps_off(font)), text, font=font, fill=(255, 255, 255, 255))
    # pad to the 241 px ink height of the two-line badges so the pill comes out the same height
    bb = im.split()[3].getbbox(); t = im.crop(bb); sc = 150 / t.height
    t = t.resize((int(t.width * sc), 150), Image.LANCZOS)
    c = Image.new('RGBA', (t.width, 241)); c.alpha_composite(t, (0, 45))
    c.putpixel((0, 0), (255, 255, 255, 30)); c.putpixel((0, 240), (255, 255, 255, 30))
    return lucent_pill(c)
for style in ('glass', 'whiteblack', 'blackwhite', 'light', 'minimal', 'lucent'):
    d = os.path.join(OUT, style, 'aspectratio')
    for f in sorted(os.listdir(d)):
        t = f[:-4]
        if t in ('fallback', '0.00'): continue
        im = neon(t) if style == 'neon' else lucent(t) if style == 'lucent' else pill(style, t)
        w, h = im.size; im.resize((round(w * H / h), H), Image.LANCZOS).save(os.path.join(d, f), optimize=True)
print('ok')
