"""4.8.78 / frbadges 1.0.7: same height for every badge in AF3's own rows
(footer codec row, OSD extras). AF3 draws each badge in a fixed box, so the
wide ones (AVC|H.264, 2.0|STEREO, DTS-HD MA ...) shrank. Every classic-layout
badge of every FR style is put on one canvas (Lucent pill proportions,
176x68 -> 285x110) at the same pill height; badges too wide for it are
redrawn as one-label pills in their own colours (make_lp.compact / relabel).
Usage: make_fit.py FR CLASSIC LUCENT_FLAGS OUT"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
FR_, CL_, LUC_, OUT_ = sys.argv[1:5]

def _part(fname, stop, argv):
    src = open(os.path.join(HERE, fname)).read(); src = src[:src.index(stop)]
    old = sys.argv; sys.argv = argv
    ns = {'__file__': os.path.join(HERE, fname)}; exec(compile(src, fname, 'exec'), ns)
    sys.argv = old; return ns

R = _part('make_res.py', 'def lucent_pill', ['x', FR_, CL_, '/tmp/unused'])
P = _part('make_lp.py', 'def place', ['x', FR_, CL_, '/tmp/unused', LUC_])
from make_res_lp import lucent_pill
M, load, STYLES = R['M'], R['load'], R['STYLES']
tight, compact, MAXR = P['tight'], P['compact'], P['MAXR']
CW, CH, PH = 285, 110, 97

LABEL = {'1080p': '1080p', '720p': '720p', '576p': '576p', '480p': '480p', '360p': '360p', '4k': '4K', '8k': '8K',
         'avc': 'AVC', 'hevc': 'HEVC', 'mpeg2': 'MPEG-2', 'mpeg4': 'MPEG-4', 'vc1': 'VC-1', 'av1': 'AV1', 'vp9': 'VP9',
         'divx': 'DIVX', 'xvid': 'XVID', 'wmv': 'WMV', 'prores': 'PRORES',
         'dd': 'DD', 'ddplus': 'DD+', 'atmos': 'ATMOS', 'atmos-ddplus': 'ATMOS', 'atmos-truehd': 'ATMOS', 'truehd': 'TrueHD',
         'dts': 'DTS', 'dtshd-ma': 'DTS-HD MA', 'dtshd-hra': 'DTS-HD HR', 'dtsx': 'DTS:X',
         '1-0': '1.0', '2-0': '2.0', '2-1': '2.1', 'chan-21': '2.1', 'chan-40': '4.0', 'chan-41': '4.1', '5-1': '5.1',
         '6-1': '6.1', '7-1': '7.1', '7-1-2': '7.1.2', '5-1-4': '5.1.4', '7-1-4': '7.1.4',
         'dolby-vision': 'DV', 'hdr10plus': 'HDR10+', 'hdr10': 'HDR10', 'hdr': 'HDR', 'sdr': 'SDR', 'hlg': 'HLG',
         'hfr': 'HFR', 'dual-audio': 'DUAL', 'multi-sub': 'SUBS', '3d': '3D', 'source-uhd-bluray': 'UHD BD',
         'source-bluray': 'BLU-RAY', 'source-webdl': 'WEB-DL', 'source-dvd': 'DVD', 'source-hdtv': 'HDTV'}

def label_for(src):
    n = os.path.basename(src)[:-4]
    for p in ('res-', 'vcodec-', 'acodec-', 'hdr-', 'src-', 'vid-', 'flag-'):
        if n.startswith(p) and n[len(p):] in LABEL:
            n = n[len(p):]
    if n.startswith('lang-'):
        return n[5:].upper()
    return LABEL.get(n, n.upper().replace('-', ' '))

def lucent_compact(label):
    f = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf', 200)
    w = int(f.getlength(label)) + 20; im = Image.new('RGBA', (w, 309))
    bb = f.getbbox('H'); ImageDraw.Draw(im).text((10, 155 - (bb[1] + bb[3]) / 2), label, font=f, fill=(255, 255, 255, 255))
    t = im.crop(im.split()[3].getbbox()); s = 150 / t.height
    t = t.resize((int(t.width * s), 150), Image.LANCZOS)
    c = Image.new('RGBA', (t.width, 241)); c.alpha_composite(t, (0, 45))
    c.putpixel((0, 0), (255, 255, 255, 30)); c.putpixel((0, 240), (255, 255, 255, 30))
    return lucent_pill(c)

def place(im):
    im = tight(im); s = PH / im.height
    im = im.resize((max(1, round(im.width * s)), PH), Image.LANCZOS)
    if im.width > CW:
        s = CW / im.width; im = im.resize((CW, max(1, round(im.height * s))), Image.LANCZOS)
    c = Image.new('RGBA', (CW, CH)); c.alpha_composite(im, ((CW - im.width) // 2, (CH - im.height) // 2)); return c

FOLDERS = ('audio', 'channels', 'source', 'resolution', 'other', 'aspectratio')
# AF3 draws on top of these (frame rate; a 33x24 country flag), so they keep the
# classic pictures (restore_templates) and are not refitted
TEMPLATES = ('other/fps', 'other/soun', 'other/subt', 'other/subtd')
n_comp = n_all = 0
for style in STYLES:
    for top in FOLDERS:
        base = os.path.join(OUT_, style, top)
        for d, _s, fs in os.walk(base):
            for f in fs:
                if not f.endswith('.png'):
                    continue
                p = os.path.join(d, f); key = os.path.relpath(p, os.path.join(OUT_, style))[:-4]
                if key in TEMPLATES or key.startswith('other/language/'):
                    continue
                im = Image.open(p).convert('RGBA'); t = tight(im)
                lang_minimal = style in ('minimal', 'whiteblack') and key.startswith('other/language/')
                if t.width / t.height > MAXR and key in M and not lang_minimal:
                    src = load(style, M[key])
                    if src:
                        lab = label_for(src)
                        im = lucent_compact(lab) if style == 'lucent' else compact(style, src, lab)
                        n_comp += 1
                place(im).save(p); n_all += 1
print('placed', n_all, 'compact', n_comp)
