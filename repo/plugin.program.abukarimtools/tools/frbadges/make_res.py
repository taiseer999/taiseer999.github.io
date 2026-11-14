import os, sys, shutil
from PIL import Image
FR, CLS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
STYLES = {'glass':'Badges','blackwhite':'Badges-Black-White','whiteblack':'Badges-White-Black','minimal':'Badges-Minimal','light':'Badges-Light','lucent':'Badges-Text-White',
          'solid':'Badges-Solid','icondark':'Badges-Icon-Dark','split':'Badges-Split','frost':'Badges-Frost',
          'neonicon':'Badges-Neon-Icon','iconlight':'Badges-Icon-Light','textwhite':'Badges-Text-White','textblack':'Badges-Text-Black'}
H = 110
M = {}
def m(cands, *targets):
    for t in targets: M[t] = cands if isinstance(cands, list) else [cands]
# resolution
m(['1080p','res-1080p'],'resolution/1080','other/1080'); m(['4k','res-4k'],'resolution/2160','resolution/4k','other/4k','source/4k')
m(['8k','res-8k'],'resolution/8k'); m(['720p','res-720p'],'resolution/720'); m(['576p','res-576p'],'resolution/576')
m(['480p','res-480p'],'resolution/480','other/sdtv'); m(['360p','res-360p'],'resolution/288')
# hdr / other
m(['dolby-vision','hdr-dovi'],'other/dolbyvision'); m(['hdr','hdr-hdr'],'other/hdr'); m(['hdr10','hdr-hdr10'],'other/hdr10')
m(['hdr10plus','hdr-hdr10plus'],'other/hdr10plus'); m(['hlg','hdr-hlg'],'other/hlg'); m(['sdr','hdr-sdr'],'other/sdr')
m(['3d','vid-3d'],'other/3d','source/3dbd','source/bluray3d'); m(['source-uhd-bluray','src-uhdbluray'],'other/4k_bluray')
m(['source-webdl','src-webdl'],'other/4k_web-dl','other/web-dl'); m(['source-bluray','src-bluray'],'other/bluray','other/bluray_flat','source/bluray','source/bluray_flat')
m(['source-dvd','src-dvd'],'other/dvd','source/dvd'); m(['source-hdtv','src-hdtv'],'other/hdtv','source/hdtv','source/hdtv_old')
m(['hfr','vid-hfr'],'other/fps'); m(['dual-audio','flag-dual-audio'],'other/soun'); m(['multi-sub','flag-multi-sub'],'other/subt','other/subtd')
# audio
m('aac',*['audio/'+x for x in 'aac aac_latm aac_lc aac_ltp aac_ssr he_aac he_aac_v2 m4a'.split()])
m('dd','audio/ac3','audio/dolbydigital'); m('ddplus','audio/eac3'); m(['atmos-ddplus','atmos'],'audio/eac3_ddp_atmos')
m('atmos','audio/atmos'); m('truehd','audio/truehd','audio/dolbytruehd','audio/mlp'); m(['atmos-truehd','atmos'],'audio/truehd_atmos')
m('dts','audio/dts','audio/dca'); m('dtshd-ma','audio/dtshd_ma','audio/dtshdma','audio/dtsma'); m('dtshd-hra','audio/dtshd_hra')
m('dtsx','audio/dtsx','audio/dts_x','audio/dtshd_ma_x','audio/dtsx-imax','audio/dtshd_ma_x_imax')
m('flac','audio/flac'); m('alac','audio/alac'); m('opus','audio/opus'); m('vorbis','audio/vorbis','audio/ogg')
m('mp3','audio/mp3','audio/mp3float'); m('pcm',*['audio/'+x for x in 'pcm pcm_s16be pcm_s16le pcm_s24le pcm_u8 wav aif aifc aiff cdda'.split()])
m('wma',*['audio/'+x for x in 'wma wma2 wma3 wmapro wmav2'.split()])
# channels (Kodi reports a channel count)
m('1-0','channels/1'); m('2-0','channels/2'); m(['2-1','chan-21'],'channels/3'); m(['chan-40'],'channels/4'); m(['chan-41'],'channels/5')
m('5-1','channels/6'); m('6-1','channels/7'); m('7-1','channels/8'); m('7-1-2','channels/10'); m('5-1-4','channels/5.1.4'); m('7-1-4','channels/7.1.4')
# video codecs
m(['hevc','vcodec-hevc'],*['source/'+x for x in 'hevc h265 hev1 hvc1 x265'.split()])
m(['avc','vcodec-avc'],*['source/'+x for x in 'avc avc1 h264 x264 x264-2 avchd'.split()])
m(['av1','vcodec-av1'],'source/av1'); m(['vc1','vcodec-vc1'],'source/vc1','source/vc-1','source/wvc1')
m(['mpeg2','vcodec-mpeg2'],*['source/'+x for x in 'mpeg2 mpeg2video v_mpeg2 h262'.split()])
m(['mpeg4','vcodec-mpeg4'],*['source/'+x for x in ['mpeg4','mp4v','fmp4','mpg4','mpeg-4 visual','mp42','mp43']])
m(['divx','vcodec-divx'],*['source/'+x for x in ['divx','divx 4','div2','div3','div4','dx50']])
m(['xvid','vcodec-xvid'],'source/xvid','source/xvid2'); m(['wmv','vcodec-wmv'],'source/wmv2','source/wmv3','source/wmvhd')
m(['vp9','vcodec-vp9'],'source/webm'); m(['prores','vcodec-prores'],'source/quicktime')
# languages: colorful code -> FR lang code
L = {'alb':'sq','sqi':'sq','sq':'sq','ar':'ar','ara':'ar','arm':'hy','hye':'hy','hy':'hy','baq':'eu','bg':'bg','bul':'bg','bos':'bs','bs':'bs',
 'cat':'ca','chi':'zh','zho':'zh','zh':'zh','cro':'hr','hr':'hr','hrv':'hr','cs':'cs','cze':'cs','da':'da','dan':'da','de':'de','deu':'de','ger':'de',
 'dut':'nl','nl':'nl','nld':'nl','el':'el','ell':'el','gre':'el','en':'en','eng':'en','es':'es','spa':'es','est':'et','et':'et','fa':'fa','fas':'fa','per':'fa',
 'fi':'fi','fin':'fi','fil':'fil','fo':'fo','fr':'fr','fra':'fr','fre':'fr','he':'he','heb':'he','hi':'hi','hin':'hi','hu':'hu','hun':'hu','ice':'is','is':'is','isl':'is',
 'id':'id','ind':'id','it':'it','ita':'it','ja':'ja','jap':'ja','jpn':'ja','kaz':'kk','kk':'kk','ko':'ko','kor':'ko','lav':'lv','lv':'lv','lb':'lb','ltz':'lb',
 'lit':'lt','lt':'lt','mac':'mk','mk':'mk','mkd':'mk','mal':'ml','may':'ms','ms':'ms','msa':'ms','no':'no','nob':'no','nor':'no','pb':'pt-br','pt-br':'pt-br',
 'pl':'pl','pol':'pl','por':'pt','pt':'pt','ro':'ro','rom':'ro','ron':'ro','rum':'ro','ru':'ru','rus':'ru','scc':'sr','ser':'sr','sr':'sr','srp':'sr',
 'sk':'sk','slk':'sk','slo':'sk','sl':'sl','slv':'sl','sv':'sv','swe':'sv','tam':'ta','tel':'te','th':'th','tha':'th','thai':'th','tr':'tr','tur':'tr',
 'uk':'uk','ukr':'uk','ur':'ur','vi':'vi','vie':'vi'}
for k,v in L.items(): M['other/language/'+k] = ['lang-'+v]

def load(style, cands):
    for c in cands:
        p = os.path.join(FR, STYLES[style], c + '.png')
        if os.path.isfile(p): return p
def lucent_pill(im):
    # Lucent glass: white text on a see-through white pill (AF3 Lucent: 38FFFFFF)
    from PIL import ImageDraw
    a = im.split()[3]; bb = a.point(lambda v: 255 if v > 20 else 0).getbbox() or (0, 0) + im.size
    im = im.crop(bb); w, h = im.size
    px, py = int(h * .32), int(h * .26)
    W, Hh = w + 2 * px, h + 2 * py
    S = 4; big = Image.new('RGBA', (W * S, Hh * S)); d = ImageDraw.Draw(big)
    r = int(Hh * .30) * S
    d.rounded_rectangle((0, 0, W * S - 1, Hh * S - 1), radius=r, fill=(255, 255, 255, 56), outline=(255, 255, 255, 96), width=3 * S)
    out = big.resize((W, Hh), Image.LANCZOS); out.alpha_composite(im, (px, py))
    return out
def conv(src, dst, style):
    im = Image.open(src).convert('RGBA')
    if style == 'lucent': im = lucent_pill(im)
    if style in ('neon', 'neonicon'):  # pad to the 309-tall canvas the other styles use, so it sits at the same size
        w, h = im.size; nh = int(h * 309 / (227 if style == 'neon' else 184)); c = Image.new('RGBA', (w, nh), (0,0,0,0)); c.paste(im, (0, (nh-h)//2)); im = c
    w, h = im.size; im = im.resize((max(1, round(w*H/h)), H), Image.LANCZOS)
    im.save(dst, optimize=True)
SKIP = ('mpaa/', 'ratings/', 'language/')
stats = {}
for style in STYLES:
    mapped = fb = 0; missing = []
    for root, _d, files in os.walk(CLS):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), CLS).replace(os.sep, '/')
            if rel.startswith(SKIP) or not rel.endswith('.png'): continue
            key = rel[:-4]; dst = os.path.join(OUT, style, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            src = load(style, M.get(key, []))
            if src: conv(src, dst, style); mapped += 1
            else: shutil.copyfile(os.path.join(CLS, rel), dst); fb += 1
    # files the skin references that colorful never had
    for key in ('other/sdtv',):
        dst = os.path.join(OUT, style, key + '.png')
        if not os.path.exists(dst):
            src = load(style, M[key]);  src and conv(src, dst, style)
    stats[style] = (mapped, fb)
print(stats)
