"""lucent_player/ copies sized for the AF3 Lucent Player boxes (132x51 / 176x68,
ratio 2.59): every badge on a 176x68 canvas, same pill height; badges too wide
for the box are redrawn as a compact single-label pill in the same colours."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relabel import relabel, GEO
FR, CL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LUCENT = sys.argv[4]                # AB Tools resources/lucent/media/lucent/flags (all 52 Lucent pills)
import shutil
FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
CW, CH, PH = 176, 68, 60            # canvas, pill height inside it
MAXR = CW / PH                      # widest content that still fits at full height
STY = {'glass': 'Badges', 'blackwhite': 'Badges-Black-White', 'solid': 'Badges-Solid', 'icondark': 'Badges-Icon-Dark', 'split': 'Badges-Split', 'frost': 'Badges-Frost', 'neonicon': 'Badges-Neon-Icon', 'iconlight': 'Badges-Icon-Light', 'textwhite': 'Badges-Text-White', 'textblack': 'Badges-Text-Black', 'whiteblack': 'Badges-White-Black', 'minimal': 'Badges-Minimal', 'light': 'Badges-Light'}
SRC = {'4K': ['4k'], '8K': ['8k'], '1080P': ['1080p'], '720P': ['720p'], 'SD': ['480p'], 'DV': ['dolby-vision'], 'DV2': ['dolby-vision'],
       'HDR10': ['hdr10'], 'HDR10+': ['hdr10plus'], 'HLG': ['hlg'], 'HEVC': ['hevc'], 'AVC': ['avc'], 'AV1': ['av1'], 'VP9': ['vp9'],
       'ATMOS': ['atmos'], 'TRUEHD': ['truehd'], 'DTS-X': ['dtsx'], 'DTS-HDMA': ['dtshd-ma'], 'DTS-HDHR': ['dtshd-hra'], 'DTS': ['dts'],
       'DD+': ['ddplus'], 'DD': ['dd'], 'AAC': ['aac'], 'FLAC': ['flac'], 'OPUS': ['opus'], 'PCM': ['pcm'], 'MP3': ['mp3'],
       '7.1': ['7-1'], '6.1': ['6-1'], '5.1': ['5-1'], '2.0': ['2-0'], '1.0': ['1-0'],
       # 4.8.76: the rest of the Lucent stream badges (Search All + the add-ons' source windows)
       '3D': ['3d', 'vid-3d'], 'BLURAY': ['source-bluray', 'src-bluray'], 'REMUX': ['source-remux', 'src-remux'],
       'WEB': ['source-webdl', 'src-webdl'], 'HDTV': ['source-hdtv', 'src-hdtv'], 'PDTV': ['source-tvrip', 'src-tvrip'],
       'HD-RIP': ['hdrip'], 'DVDRIP': ['source-dvd', 'src-dvd'], 'CAM': ['cam', 'src-cam'], 'SCR': ['scr', 'src-scr'],
       'HC': ['hc-hdrip'], 'HDR': ['hdr'], 'SDR': ['sdr'], 'HYBRID': ['hybrid', 'edit-hybrid'], 'DIVX': ['divx'],
       'XVID': ['xvid'], 'MPEG': ['mpeg2'], 'MP4': ['mp4', 'cont-mp4'], 'WMV': ['wmv'], 'WMA': ['wma'],
       'DTS-HD': ['dtshd-ma']}
LABEL = {'DTS-HD': 'DTS-HD', 'DVDRIP': 'DVD', 'HD-RIP': 'HDRip', 'DTS-HDMA': 'DTS-HD MA', 'DTS-HDHR': 'DTS-HD HR', 'DTS-X': 'DTS:X', '1080P': '1080p', '720P': '720p', 'DV2': 'DV',
         'TRUEHD': 'TrueHD', 'ATMOS': 'ATMOS', 'HDR10+': 'HDR10+'}

def tight(im):
    bb = im.split()[3].point(lambda v: 255 if v > 8 else 0).getbbox()
    return im.crop(bb)

def text_color(a, dark_text):
    h, w = a.shape[:2]; reg = a[int(h*.3):int(h*.7), int(w*.15):int(w*.85)].reshape(-1, 4)
    reg = reg[reg[:, 3] > 200]; lum = reg[:, :3].astype(int).sum(1)
    pick = reg[lum.argmin()] if dark_text else reg[lum.argmax()]
    return tuple(int(x) for x in pick[:3])

def fit_font(text, maxw, size):
    while size > 20:
        f = ImageFont.truetype(FONT, size)
        if f.getlength(text) <= maxw: return f
        size -= 4
    return ImageFont.truetype(FONT, size)

def compact(style, src, label):
    """Redraw the badge as one label on its own pill (same caps + colours)."""
    if style in GEO:
        return relabel(style, src, label, MAXR * 0.98)
    im = Image.open(src).convert('RGBA'); w, h = im.size; a = np.array(im)
    target_w = int(h * MAXR * 0.98)
    if style == 'neon':
        col1, col2 = text_color(a, False), text_color(a[::-1], False)
        f = fit_font(label, target_w - 60, 150)
        out = Image.new('RGBA', (target_w, h)); m = Image.new('L', out.size)
        tw = f.getlength(label); bb = f.getbbox('H')
        ImageDraw.Draw(m).text(((target_w - tw) / 2, h / 2 - (bb[1] + bb[3]) / 2), label, font=f, fill=255)
        g = np.zeros((h, target_w, 3), np.uint8)
        for y in range(h): g[y] = (np.array(col1) + (np.array(col2) - np.array(col1)) * y / h).astype(np.uint8)
        t = Image.fromarray(g).convert('RGBA'); t.putalpha(m)
        glow = Image.new('RGBA', out.size, col2 + (0,)); glow.putalpha(m.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * .5)))
        out.alpha_composite(glow); out.alpha_composite(t); return out
    lc = {'minimal': int(h * .58)}.get(style, int(h * .227))
    rc = int(h * .24)
    dark = style in ('whiteblack', 'light')
    col = text_color(a, dark)
    tx0 = {'minimal': int(h * .615)}.get(style, int(h * .275))
    f = fit_font(label, target_w - tx0 - int(h * .26), 206 if style != 'minimal' else 140)
    tw = int(f.getlength(label))
    mid = max(10, tx0 + tw + int(h * .26) - lc - rc)
    out = Image.new('RGBA', (lc + mid + rc, h))
    out.paste(im.crop((0, 0, lc, h)), (0, 0))
    L = a[:, lc + 2].astype(float); R = a[:, w - rc - 2].astype(float)
    for i in range(mid):
        t = i / max(1, mid - 1)
        out.paste(Image.fromarray(((1 - t) * L + t * R).round().astype(np.uint8)[:, None, :], 'RGBA'), (lc + i, 0))
    out.paste(im.crop((w - rc, 0, w, h)), (lc + mid, 0))
    # vertically centre the caps on the pill body (shadow sits below: body ~ 0..0.83h)
    bb = f.getbbox('H'); cy = h * .485
    ImageDraw.Draw(out).text((tx0, cy - (bb[1] + bb[3]) / 2), label, font=f, fill=col + (255,))
    return out

def place(im):
    im = tight(im); s = PH / im.height
    im = im.resize((max(1, round(im.width * s)), PH), Image.LANCZOS)
    if im.width > CW:                       # still too wide (classic logos): fit the box
        s = CW / im.width; im = im.resize((CW, max(1, round(im.height * s))), Image.LANCZOS)
    c = Image.new('RGBA', (CW, CH)); c.alpha_composite(im, ((CW - im.width) // 2, (CH - im.height) // 2)); return c

for style, folder in STY.items():
    d = os.path.join(OUT, style, 'lucent_player'); os.makedirs(d, exist_ok=True)
    for name, cands in SRC.items():
        src = next((p for p in (os.path.join(FR, folder, c + '.png') for c in cands) if os.path.isfile(p)), None)
        if src is None:                          # not in this FR set: the Lucent pill
            shutil.copyfile(os.path.join(LUCENT, name + '.png'), os.path.join(d, name + '.png'))
            continue
        im = tight(Image.open(src).convert('RGBA'))
        if im.width / im.height > MAXR:
            im = compact(style, src, LABEL.get(name, name))
        place(im).save(os.path.join(d, name + '.png'), optimize=True)
# classic colourful: same box, logos keep their look
MAPC = {'DD+':'audio/eac3','DD':'audio/ac3','1.0':'channels/1','DTS-X':'audio/dtsx','HLG':'other/hlg','720P':'resolution/720','OPUS':'audio/opus',
'7.1':'channels/8','ATMOS':'audio/atmos','AAC':'audio/aac','DTS-HDMA':'audio/dtshd_ma','HDR10':'other/hdr10','1080P':'resolution/1080','8K':'resolution/8k',
'VP9':'source/webm','DTS-HDHR':'audio/dtshd_hra','MP3':'audio/mp3','HDR10+':'other/hdr10plus','AV1':'source/av1','6.1':'channels/7','DTS':'audio/dts',
'AVC':'source/avc','SD':'resolution/480','PCM':'audio/pcm','TRUEHD':'audio/truehd','HEVC':'source/hevc','FLAC':'audio/flac','DV':'other/dolbyvision',
'DV2':'other/dolbyvision','2.0':'channels/2','5.1':'channels/6','4K':'resolution/4k',
'3D':'other/3d','BLURAY':'other/bluray','REMUX':'other/bluray','WEB':'other/web-dl','HDTV':'other/hdtv','PDTV':'other/hdtv',
'DVDRIP':'other/dvd','HDR':'other/hdr','SDR':'other/sdr','DIVX':'source/divx','XVID':'source/xvid','MPEG':'source/mpeg2',
'MP4':'source/mp4v','WMV':'source/wmv3','WMA':'audio/wma','DTS-HD':'audio/dtshd_ma'}
d = os.path.join(OUT, 'colorful', 'lucent_player'); os.makedirs(d, exist_ok=True)
for n in SRC:
    if n in MAPC:
        place(Image.open(os.path.join(CL, MAPC[n] + '.png')).convert('RGBA')).save(os.path.join(d, n + '.png'), optimize=True)
    else:                                       # CAM / SCR / HC / HD-RIP / HYBRID: no classic badge
        shutil.copyfile(os.path.join(LUCENT, n + '.png'), os.path.join(d, n + '.png'))
# Lucent: the Lucent pills themselves
d = os.path.join(OUT, 'lucent', 'lucent_player'); os.makedirs(d, exist_ok=True)
for f in os.listdir(LUCENT):
    shutil.copyfile(os.path.join(LUCENT, f), os.path.join(d, f))
print('ok')
