# Lucent -> AF3 "Lucent Player" port generator (AB Tools 4.7.25)
import re, sys, os, json
from lxml import etree as ET
L = sys.argv[1]            # Lucent repo root
OUT = sys.argv[2]
X = lambda f: open(os.path.join(L, 'xml', f), encoding='utf-8').read()
parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False)

def frag_children(xmltext):
    root = ET.fromstring(xmltext.encode('utf-8'), parser)
    return root

# ---------- source fragments ----------
def window_controls(fname):
    root = frag_children(X(fname))
    return root, root.find('controls')

def is_pvr_only(el):
    v = el.find('visible')
    return v is not None and (v.text or '').strip().startswith('Pvr.IsPlayingTV') and not (v.text or '').strip().startswith('!Pvr')

def drop(el):
    p = el.getparent(); p.remove(el)

def clean_controls(ctrls):
    """remove live-TV / sport-only groups and the NuvioStatsPanel include"""
    for el in list(ctrls):
        if not isinstance(el.tag, str):
            continue
        if el.tag == 'control' and is_pvr_only(el):
            drop(el); continue
        if el.tag == 'control' and el.get('id') == '9700':     # sport scoreboard
            drop(el); continue
        if el.tag == 'control' and el.find('include') is not None and (el.find('include').text or '') == 'NuvioStatsPanel':
            drop(el); continue
        if el.tag == 'include' and (el.text or '') == 'NuvioStatsPanel':
            drop(el); continue
    # sport bars of the player menu (visible starts with Pvr.IsPlayingTV + ...)
    return ctrls

parts = {}
r, c = window_controls('VideoOSD.xml'); parts['VideoOSD'] = clean_controls(c)
r, c = window_controls('DialogSeekBar.xml'); parts['SeekBar'] = clean_controls(c)
r, c = window_controls('VideoFullScreen.xml')
buf = [e for e in c if isinstance(e.tag, str) and e.tag == 'control' and (e.findtext('visible') or '') == 'Player.Caching']
parts['FullScreen'] = buf
r, c = window_controls('DialogFullScreenInfo.xml'); parts['FullScreenInfo'] = clean_controls(c)
pinfo_root = frag_children(X('Lucent_PlayerInfo.xml'))

# report
for k, v in parts.items():
    print(k, len(list(v)), 'top-level elements')
allxml = ''.join(ET.tostring(e, encoding='unicode') for v in parts.values() for e in v) + ET.tostring(pinfo_root, encoding='unicode')
ids = sorted(set(int(i) for i in re.findall(r'\$LOCALIZE\[(3[12]\d{3})\]', allxml)))
print('skin strings used:', ids)
open(os.path.join(OUT, 'stage1.xml'), 'w', encoding='utf-8').write(allxml)

# ---------- shared definitions (includes / variables / expressions) ----------
DEF_SRC = X('Includes.xml') + X('Variables.xml') + X('Includes_Player.xml')
def get_def(tag, name):
    m = re.search(r'<%s name="%s"[^>]*>.*?</%s>' % (tag, re.escape(name), tag), DEF_SRC, re.S)
    if not m:
        raise SystemExit('missing %s %s' % (tag, name))
    txt = m.group(0)
    if tag == 'include':      # nested includes: balance
        i = DEF_SRC.index(m.group(0)[:40]); depth = 0
        for mm in re.finditer(r'<include\b[^>]*?(/?)>|</include>', DEF_SRC[i:]):
            if mm.group(0).startswith('</'): depth -= 1
            elif not mm.group(1): depth += 1
            if depth == 0:
                txt = DEF_SRC[i:i + mm.end()]; break
    return txt

INCS = ['GlassPanel', 'Spinner', 'TextAutoScroll']
VARS = ['NuvioFlagImg_acodec', 'NuvioFlagImg_atmos', 'NuvioFlagImg_ch', 'NuvioFlagImg_hdr', 'NuvioFlagImg_res',
        'NuvioFlagImg_vcodec', 'OSDButtonLabel', 'PlayerLogo', 'PlayerSubtitle', 'PlayerTitle']
EXPS = ['LucentDV2Named', 'NuvioPauseInfo', 'OSDShowPlay']
defs_txt = '\n'.join(get_def('include', n) for n in INCS) + '\n' + \
           '\n'.join(get_def('variable', n) for n in VARS) + '\n' + \
           '\n'.join(get_def('expression', n) for n in EXPS)

# ---------- Lucent control defaults, written onto each control ----------
DEFAULTS = {
    'label':    [('font', 'font12'), ('textcolor', 'text'), ('shadowcolor', 'transparent'), ('aligny', 'center'), ('height', '40')],
    'fadelabel':[('font', 'font12'), ('textcolor', 'text'), ('height', '40')],
    'textbox':  [('font', 'font_body'), ('textcolor', 'text3')],
    'button':   [('height', '64'), ('font', 'font_label_bold'), ('textcolor', 'text'), ('focusedcolor', 'on_focus'),
                 ('disabledcolor', 'text5'), ('selectedcolor', 'text'), ('textoffsetx', '30'), ('aligny', 'center'),
                 ('pulseonselect', 'false')],
    'progress': [('height', '6')],
}
BTN_TEX = [('texturefocus', 'focus', 'pill64.png'), ('texturenofocus', 'glass_strong', 'pill64.png')]

def apply_defaults(root):
    for el in root.iter('control'):
        t = el.get('type')
        for tag, val in DEFAULTS.get(t, []):
            if el.find(tag) is None:
                n = ET.SubElement(el, tag); n.text = val
        if t == 'button':
            for tag, col, tex in BTN_TEX:
                if el.find(tag) is None:
                    n = ET.SubElement(el, tag, border='32', colordiffuse=col); n.text = tex
        if t == 'progress':
            if el.find('texturebg') is None:
                n = ET.SubElement(el, 'texturebg', border='3', colordiffuse='glass_strong'); n.text = 'pill6.png'
            if el.find('midtexture') is None:
                n = ET.SubElement(el, 'midtexture', border='3', colordiffuse='text'); n.text = 'pill6.png'
            for tag in ('lefttexture', 'righttexture', 'overlaytexture'):
                if el.find(tag) is None:
                    ET.SubElement(el, tag)

def ser(elems):
    return '\n'.join(ET.tostring(e, encoding='unicode') for e in elems)

for k in parts:
    for e in parts[k]:
        if isinstance(e.tag, str): apply_defaults(e)
apply_defaults(pinfo_root)
defs_root = ET.fromstring(('<r>' + defs_txt + '</r>').encode('utf-8'), parser)
apply_defaults(defs_root)
defs_txt = ''.join(ET.tostring(e, encoding='unicode') for e in defs_root)

# ---------- stage 3: text-level renames ----------
COLORS = dict(re.findall(r'<color name="([^"]+)">([0-9A-Fa-f]{8})</color>', open(os.path.join(L, 'colors', 'defaults.xml'), encoding='utf-8').read()))
FONTFILE = {'Inter-Regular.ttf': 'Inter-Regular.ttf', 'Inter-Medium.ttf': 'Inter-Regular.ttf',
            'Inter-SemiBold.ttf': 'Inter-Bold.ttf', 'Inter-Bold.ttf': 'Inter-Bold.ttf', 'Inter-ExtraBold.ttf': 'Inter-Bold.ttf'}
LFONTS = {}
for m in re.finditer(r'<font>\s*<name>([^<]+)</name>(.*?)</font>', X('Font.xml'), re.S):
    LFONTS.setdefault(m.group(1), m.group(2))
ID_OFF = 7000
OSD_IDS = {87, 100, 101, 102, 103, 105, 106, 111, 112, 113, 114, 115, 116, 117, 118, 119, 190, 1031,
           7500, 7501, 7502, 7503, 7504, 7505, 7506, 7507, 7508, 7509, 7510, 7600, 7601, 7602, 7603, 7604, 7605, 7606}
used_fonts, used_tex, used_str = set(), set(), set()

def rename(txt, offset_ids=True):
    # include / variable / expression names
    for n in INCS:
        txt = re.sub(r'(<include name="|<include content="|<include>)%s(["<])' % n, r'\g<1>ABK_LP_%s\2' % n, txt)
    for n in VARS:
        txt = txt.replace('$VAR[%s]' % n, '$VAR[ABK_LP_%s]' % n).replace('<variable name="%s"' % n, '<variable name="ABK_LP_%s"' % n)
    for n in EXPS:
        txt = txt.replace('$EXP[%s]' % n, '$EXP[ABK_LP_%s]' % n).replace('<expression name="%s"' % n, '<expression name="ABK_LP_%s"' % n)
    # fonts
    def f(m):
        used_fonts.add(m.group(1)); return '<font>abk_lp_%s</font>' % m.group(1)
    txt = re.sub(r'<font>([A-Za-z0-9_]+)</font>', f, txt)
    # colours (attribute and element forms)
    def col(name):
        return COLORS.get(name, name)
    txt = re.sub(r'(colordiffuse=")([a-z][a-z0-9_]*)(")', lambda m: m.group(1) + col(m.group(2)) + m.group(3), txt)
    txt = re.sub(r'<(textcolor|focusedcolor|shadowcolor|disabledcolor|selectedcolor|colordiffuse|invalidcolor)>([a-z][a-z0-9_]*)</',
                 lambda m: '<%s>%s</' % (m.group(1), col(m.group(2))), txt)
    # textures: relative skin media paths -> abk_lp/
    def tex(m):
        p = m.group(2)
        if p.startswith(('special://', '$', 'resource://', 'http', '/', 'abk_lp/')) or not re.search(r'\.(png|jpg|gif)$', p, re.I):
            return m.group(0)
        used_tex.add(p); return m.group(1) + 'abk_lp/' + p + m.group(3)
    txt = re.sub(r'(<(?:texture|texturefocus|texturenofocus|texturebg|midtexture|lefttexture|righttexture|overlaytexture|texturesliderbar|texturesliderbardisabled|textureslidernib|textureslidernibfocus|alttexturefocus|alttexturenofocus)\b[^>]*>)([^<]+)(</)', tex, txt)
    txt = re.sub(r'(<value[^>]*>)([A-Za-z0-9_/+.\-]+\.png)(</value>)', tex, txt)
    # skin strings -> AB Tools strings
    def s(m):
        used_str.add(int(m.group(1))); return '$ADDON[plugin.program.abukarimtools %d]' % (32000 + int(m.group(1)) - 31000 if False else STRMAP.get(int(m.group(1)), 0))
    txt = re.sub(r'\$LOCALIZE\[(3[12]\d{3})\]', s, txt)
    # scripts and Lucent-only settings
    txt = txt.replace('RunScript(special://skin/scripts/playerinfo.py,open)', 'RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/lucent_playerinfo.py,open)')
    txt = txt.replace('RunScript(special://skin/scripts/sleep.py)', 'RunScript(special://home/addons/plugin.program.abukarimtools/resources/lib/lucent_sleep.py)')
    txt = txt.replace('RunScript(special://skin/scripts/subs_live.py)', 'RunPlugin(plugin://plugin.program.abukarimtools/?mode=subtitle_list)')
    txt = txt.replace('!Skin.HasSetting(nuvio.osdstats)', 'true').replace('Skin.HasSetting(nuvio.osdstats)', 'false')
    txt = txt.replace('!Skin.HasSetting(lucent.subs.native.off)', 'true').replace('Skin.HasSetting(lucent.subs.native.off)', 'false')
    txt = txt.replace('!Skin.HasSetting(nuvio.pauseinfo.hideflags)', 'true')
    txt = txt.replace('Skin.String(nuvio.', 'Skin.String(abk.lp.')
    if offset_ids:
        ids = '|'.join(str(i) for i in sorted(OSD_IDS, reverse=True))
        txt = re.sub(r'\bid="(%s)"' % ids, lambda m: 'id="%d"' % (int(m.group(1)) + ID_OFF), txt)
        txt = re.sub(r'<(onup|ondown|onleft|onright|defaultcontrol)( [^>]*)?>(%s)</' % ids,
                     lambda m: '<%s%s>%d</' % (m.group(1), m.group(2) or '', int(m.group(3)) + ID_OFF), txt)
        txt = re.sub(r'(SetFocus|Control\.HasFocus|Control\.IsVisible|Control\.IsEnabled)\((%s)\)' % ids,
                     lambda m: '%s(%d)' % (m.group(1), int(m.group(2)) + ID_OFF), txt)
    return txt

# ---------- strings ----------
LPO = open(os.path.join(L, 'language', 'resource.language.en_gb', 'strings.po'), encoding='utf-8').read()
LEN = dict((int(k), v) for k, v in re.findall(r'msgctxt "#(\d+)"\nmsgid "((?:[^"\\]|\\.)*)"', LPO))
pre = ser([e for v in parts.values() for e in v]) + ET.tostring(pinfo_root, encoding='unicode') + defs_txt
need = sorted(set(int(i) for i in re.findall(r'\$LOCALIZE\[(3[12]\d{3})\]', pre)))
STRMAP = {sid: 32000 + n for n, sid in enumerate(need)}
json.dump({str(STRMAP[s]): [s, LEN.get(s, '??')] for s in need}, open(os.path.join(OUT, 'strings.json'), 'w'), ensure_ascii=False, indent=0)
print('strings mapped:', len(STRMAP), 'missing en:', [s for s in need if s not in LEN])

# ---------- stage 4: outputs ----------
ON = 'Skin.HasSetting(abk.lucentplayer)'
def group(name, inner, visible):
    return ('    <include name="%s">\n        <control type="group">\n            <visible>%s</visible>\n%s\n        </control>\n    </include>\n'
            % (name, visible, inner))
osd = rename(ser(parts['VideoOSD']))
seek = rename(ser(parts['SeekBar']))
fsb = rename(ser(parts['FullScreen']))
fsi = rename(ser(parts['FullScreenInfo']))
defs = rename(defs_txt)
head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!-- AB Tools "AF3: Lucent Player" - the player of the Lucent skin by djdirty60\n'
        '     (github.com/djdirty60/Lucent, GPL-2.0-or-later), ported to Arctic Fuse 3:\n'
        '     OSD, seek bar / pause screen, buffering, info screen. Shown while the skin bool\n'
        '     abk.lucentplayer is set; live TV keeps the AF3 player. Generated - do not hand-edit. -->\n<includes>\n')
body = (defs + '\n'
        + group('ABK_LP_VideoOSD', osd, ON + ' + !Pvr.IsPlayingTV')
        + group('ABK_LP_SeekBar', seek, ON + ' + !Pvr.IsPlayingTV + ![Window.IsActive(videoosd) | Window.IsActive(fullscreeninfo)]')
        + group('ABK_LP_FullScreen', fsb, ON + ' + !Pvr.IsPlayingTV')
        + group('ABK_LP_FullScreenInfo', fsi, ON + ' + !Pvr.IsPlayingTV'))
open(os.path.join(OUT, 'Includes_ABK_LucentPlayer.xml'), 'w', encoding='utf-8').write(head + body + '</includes>\n')
pi = rename(ET.tostring(pinfo_root, encoding='unicode'), offset_ids=False)
pi = pi.replace('<window type="dialog">', '<window type="dialog">\n    <!-- AB Tools "AF3: Lucent Player" Statistics window (Lucent_PlayerInfo.xml by djdirty60, GPL-2.0-or-later) -->', 1)
open(os.path.join(OUT, 'ABK_LucentPlayerInfo.xml'), 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n' + pi + '\n')
# fonts
fl = []
for n in sorted(used_fonts):
    b = LFONTS[n]
    fn = re.search(r'<filename>([^<]+)</filename>', b).group(1); sz = re.search(r'<size>([^<]+)</size>', b).group(1)
    ls = re.search(r'<linespacing>([^<]+)</linespacing>', b)
    fl.append('<font><name>abk_lp_%s</name><filename>%s</filename><size>%s</size>%s</font>'
              % (n, FONTFILE[fn], sz, '<linespacing>%s</linespacing>' % ls.group(1) if ls else ''))
open(os.path.join(OUT, 'fonts.txt'), 'w').write('\n'.join(fl))
used_tex.update({'pill64.png', 'pill6.png'})
open(os.path.join(OUT, 'media.txt'), 'w').write('\n'.join(sorted(used_tex)))
print('fonts', len(fl), 'textures', len(used_tex), 'strings', len(used_str))
left = re.findall(r'\b(?:font1[0-9]\w*|font_\w+)\b', re.sub(r'abk_lp_\w+', '', head + body + pi))
print('unrenamed font-like names:', sorted(set(left))[:10])
print('leftover LOCALIZE 31xxx:', re.findall(r'\$LOCALIZE\[3[12]\d{3}\]', body + pi)[:5])
print('leftover named colours:', sorted(set(re.findall(r'(?:colordiffuse="|<(?:textcolor|colordiffuse|focusedcolor|shadowcolor|disabledcolor|selectedcolor)>)([a-z][a-z_0-9]*)', body + pi))))
print('leftover scripts:', sorted(set(re.findall(r'special://skin/scripts/\w+\.py', body + pi))))
print('leftover lucent/nuvio skin settings:', sorted(set(re.findall(r'Skin\.\w+\((?:lucent|nuvio)[^)]*\)', body + pi))))
