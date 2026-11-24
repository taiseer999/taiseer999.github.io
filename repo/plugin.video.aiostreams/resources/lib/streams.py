# -*- coding: utf-8 -*-
"""Stream classification, labelling and playable-URL building."""
import os
import re
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import xbmc

from . import kodi

SERVICE_SHORT = {
    'realdebrid': 'RD', 'alldebrid': 'AD', 'premiumize': 'PM', 'debridlink': 'DL',
    'torbox': 'TB', 'easydebrid': 'ED', 'debrider': 'DB', 'putio': 'PIO', 'pikpak': 'PKP',
    'offcloud': 'OC', 'seedr': 'SDR', 'easynews': 'EN', 'nzbdav': 'ND', 'altmount': 'AM',
    'stremio_nntp': 'SN', 'stremthru_newz': 'STN', 'aiostreams': 'AIO', 'torrin': 'TRN',
}

# Strip emoji / pictographs that Kodi skin fonts can't render.
_EMOJI_RE = re.compile(
    '[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
    '\U00002B00-\U00002BFF\U0000FE0F\U0000200D\U000020E3\U00002300-\U000023FF]+')
_SPACES_RE = re.compile(r'[ \t]{2,}')
_EMPTY_BRACKETS_RE = re.compile(r'\[\s*\]|\(\s*\)')

INFO_TYPES = ('error', 'statistic')


def clean(text):
    if not text:
        return ''
    if kodi.setting_bool('strip_emoji'):
        text = _EMPTY_BRACKETS_RE.sub('', _EMOJI_RE.sub('', text))
    lines = [_SPACES_RE.sub(' ', ln).strip() for ln in text.splitlines()]
    return '\n'.join(ln for ln in lines if ln)


def stream_kind(stream):
    sd = stream.get('streamData') or {}
    if sd.get('type') in INFO_TYPES:
        return sd['type']
    if stream.get('url'):
        return 'url'
    if stream.get('infoHash'):
        return 'p2p'
    if stream.get('ytId'):
        return 'youtube'
    if stream.get('externalUrl'):
        # pre-streamData AIOStreams / passthrough errors look like this
        return 'external'
    return 'unsupported'  # nzbUrl / archive streams need Stremio's engine


def p2p_handler():
    # 0 hide, 1 Elementum, 2 Torrest
    return kodi.setting_int('p2p_handler', 0)


def is_playable(stream):
    kind = stream_kind(stream)
    if kind == 'url':
        return True
    if kind == 'p2p':
        return p2p_handler() > 0
    if kind == 'youtube':
        return xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)')
    return False


def filter_streams(streams):
    """Return (playable, notices) where notices are error/statistic entries."""
    playable, notices = [], []
    for st in streams:
        kind = stream_kind(st)
        if kind in INFO_TYPES or (kind == 'external' and not st.get('streamData')):
            notices.append(st)
        elif is_playable(st):
            playable.append(st)
    return playable, notices


def _human_size(num):
    try:
        num = float(num)
    except (TypeError, ValueError):
        return ''
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if num < 1024 or unit == 'TB':
            return ('%.0f %s' if unit in ('B', 'KB') else '%.2f %s') % (num, unit)
        num /= 1024.0


def compact_label(stream):
    """Kodi-native one-line label built from streamData (falls back to name)."""
    sd = stream.get('streamData') or {}
    pf = sd.get('parsedFile') or {}
    if not sd:
        return None
    tags = []
    if pf.get('resolution'):
        tags.append('[B]%s[/B]' % pf['resolution'])
    if pf.get('quality'):
        tags.append(pf['quality'])
    vis = [v for v in pf.get('visualTags', []) if v]
    if vis:
        tags.append(' '.join(vis))
    if pf.get('encode'):
        tags.append(pf['encode'])
    aud = (pf.get('audioTags') or [])[:2] + (pf.get('audioChannels') or [])[:1]
    if aud:
        tags.append(' '.join(aud))
    size = _human_size(sd.get('size') or (stream.get('behaviorHints') or {}).get('videoSize'))
    if size:
        tags.append(size)
    svc = sd.get('service') or {}
    if svc.get('id'):
        short = SERVICE_SHORT.get(svc['id'], svc['id'].upper())
        tags.append('[COLOR %s]%s%s[/COLOR]' % ('lime' if svc.get('cached') else 'orange',
                                               short, '+' if svc.get('cached') else ''))
    elif sd.get('type') == 'p2p':
        tags.append('[COLOR orange]P2P[/COLOR]')
    if sd.get('addon'):
        tags.append('[I]%s[/I]' % sd['addon'])
    return '  '.join(tags)


# 1.4.2: characters Kodi's skin fonts have no glyph for, beyond emoji: the
# "fancy" letters some AIOStreams formatters use (mathematical alphanumerics,
# small capitals, super- / subscripts) and anything outside the BMP. They
# came out as boxes in the player's info.
_NO_GLYPH_RE = re.compile('[\U00010000-\U0010FFFF\u1D00-\u1DBF\u2070-\u209F\uA700-\uA71F]')


def plain(text):
    """Text for the player: emoji and glyph-less letters out, whatever the
    strip-emoji setting says (that one is about the lists)."""
    if not text:
        return ''
    import unicodedata
    text = _EMOJI_RE.sub('', text)
    # fancy letters back to plain ones (bold-sans M -> M, superscript b -> b)
    text = unicodedata.normalize('NFKC', text)
    text = _EMPTY_BRACKETS_RE.sub('', _NO_GLYPH_RE.sub('', text))
    lines = [_SPACES_RE.sub(' ', ln).strip(' \t·|-') for ln in text.splitlines()]
    return '\n'.join(ln for ln in lines if ln)


def labels(stream):
    """(label, label2, plot) for list items / select dialog."""
    name = clean(stream.get('name') or '')
    desc = clean(stream.get('description') or stream.get('title') or '')
    sd = stream.get('streamData') or {}
    filename = sd.get('filename') or (stream.get('behaviorHints') or {}).get('filename') or ''
    plot = '\n'.join(x for x in (name, desc) if x)
    style = kodi.setting_int('label_style', 0)
    if style == 2:
        info = classify(stream)
        return dv_label(info), filename or desc.replace('\n', ' | '), plot
    if style == 1:
        compact = compact_label(stream)
        if compact:
            return compact, filename or desc.replace('\n', ' | '), plot
    return name.replace('\n', ' '), desc.replace('\n', ' | '), plot


# --------------------------------------------------------------------------
# Dolby Vision FEL / MEL classification (merged from FEL Cinema)
# --------------------------------------------------------------------------

# Release groups known for Profile 7 FEL UHD remuxes
TOP_FEL_GROUPS = {'wildcat', 'bluranium', 'cinephiles', 'framestor', 'epsilon',
                  'btm', '3l', 'bizkit', 'pmp', 'zq'}

COLOR_FEL = 'FFFFA500'   # orange
COLOR_MEL = 'FFFF69B4'   # pink
COLOR_71 = 'FF4DA6FF'    # blue
COLOR_51 = 'FFFF5555'    # red
COLOR_STD = 'FFEDEDED'

_FEL_RE = re.compile(r'\b(FEL|P7|PROFILE[ .]?7|DUAL[ .]?LAYER)\b')
_MEL_RE = re.compile(r'\b(MEL|P8|P8\.1|PROFILE[ .]?8|HYBRID)\b')
_DV_RE = re.compile(r'\b(DV|DOVI|DOLBY[ .]?VISION)\b')
_CH71_RE = re.compile(r'(?<![0-9])7[.\s]1(?![0-9])|\b[78]CH\b')
_CH51_RE = re.compile(r'(?<![0-9])5[.\s]1(?![0-9])|\b6CH\b')
_CH20_RE = re.compile(r'(?<![0-9])2[.\s]0(?![0-9])|\b2CH\b')


def _size_of(stream):
    sd = stream.get('streamData') or {}
    try:
        return int(sd.get('size') or (stream.get('behaviorHints') or {}).get('videoSize') or 0)
    except (TypeError, ValueError):
        return 0


def classify(stream):
    """Tag a stream as FEL / MEL / 7.1 / 5.1 using AIOStreams' parsedFile and
    the filename. Works without streamData too (falls back to name/description).
    Returns a dict; tier 0 is best (FEL) and 4 is plain."""
    sd = stream.get('streamData') or {}
    pf = sd.get('parsedFile') or {}
    filename = sd.get('filename') or (stream.get('behaviorHints') or {}).get('filename') or ''
    vis = [str(v) for v in pf.get('visualTags') or [] if v]
    aud = [str(v) for v in pf.get('audioTags') or [] if v]
    chs = [str(v) for v in pf.get('audioChannels') or [] if v]
    res = str(pf.get('resolution') or '')
    qual = str(pf.get('quality') or '')
    grp = str(pf.get('releaseGroup') or '')
    hay = ' '.join([filename, qual, ' '.join(vis), ' '.join(aud), ' '.join(chs)])
    if not sd:  # no streamData: fall back to the formatter text
        hay += ' ' + (stream.get('name') or '') + ' ' + (stream.get('description') or stream.get('title') or '')
    hay = _EMOJI_RE.sub(' ', hay).upper()

    has_dv = any(v.upper() in ('DV', 'HDR+DV', 'DV+HDR') for v in vis) or bool(_DV_RE.search(hay))
    remux = 'REMUX' in hay
    is_4k = res.lower() in ('2160p', '4k') or '2160P' in hay or bool(re.search(r'\b4K\b', hay))
    is_mel = bool(_MEL_RE.search(hay))
    is_fel = bool(_FEL_RE.search(hay))

    ch_str = ' '.join(chs)
    if '7.1' in ch_str or _CH71_RE.search(hay):
        ch = '7.1'
    elif '5.1' in ch_str or _CH51_RE.search(hay):
        ch = '5.1'
    elif '2.0' in ch_str or _CH20_RE.search(hay):
        ch = '2.0'
    else:
        ch = ''

    # A 4K DV remux that isn't marked MEL is almost always a P7 FEL disc rip.
    if is_fel or (has_dv and remux and is_4k and not is_mel):
        kind, color, tier = 'FEL', COLOR_FEL, 0
    elif is_mel and has_dv:
        kind, color, tier = 'MEL', COLOR_MEL, 1
    elif ch == '7.1':
        kind, color, tier = '', COLOR_71, 2
    elif ch == '5.1':
        kind, color, tier = '', COLOR_51, 3
    else:
        kind, color, tier = '', COLOR_STD, 4
    badge = ' · '.join(x for x in (kind, ch) if x) or 'STD'

    svc = sd.get('service') or {}
    svc_id = svc.get('id') or ''
    debrid = SERVICE_SHORT.get(svc_id, svc_id.upper()) if svc_id else ('P2P' if sd.get('type') == 'p2p' else '')
    if debrid and svc.get('cached'):
        debrid += '+'

    return {
        'filename': filename or clean(stream.get('description') or stream.get('title') or '').split('\n')[0],
        'resolution': '4K' if is_4k else (res or ''),
        'is_4k': is_4k,
        'quality': qual,
        'group': grp,
        'visual': ' '.join(vis),
        'audio': ' '.join(aud),
        'channels': ch,
        'dv_type': kind,
        'badge': badge,
        'color': color,
        'tier': tier,
        'remux': remux,
        'top_group': grp.lower() in TOP_FEL_GROUPS,
        'size': _size_of(stream),
        'size_label': _human_size(_size_of(stream)) or '',
        'debrid': debrid,
        'cached': bool(svc.get('cached')),
        'addon': sd.get('addon') or '',
    }


def dv_label(info):
    """One-line label coloured by FEL/MEL/7.1/5.1 tier."""
    parts = ['[B]%s[/B]' % info['badge']]
    for key in ('resolution', 'quality', 'group', 'visual', 'audio', 'size_label'):
        if info.get(key):
            parts.append(info[key])
    out = '[COLOR %s]%s[/COLOR]' % (info['color'], '  |  '.join(parts))
    if info['debrid']:
        out += '  [COLOR %s]%s[/COLOR]' % ('lime' if info['cached'] else 'orange', info['debrid'])
    if info['addon']:
        out += '  [I]%s[/I]' % info['addon']
    return out


def sort_fel_first(playable):
    """Stable re-sort: 4K first, then FEL > MEL > 7.1 > 5.1, remux, top FEL
    group, larger file. Returns a new list."""
    keyed = []
    for i, stream in enumerate(playable):
        c = classify(stream)
        keyed.append(((0 if c['is_4k'] else 1, c['tier'], 0 if c['remux'] else 1,
                       0 if c['top_group'] else 1, -c['size'], i), stream))
    keyed.sort(key=lambda x: x[0])
    return [s for _, s in keyed]


def _headers_suffix(stream):
    hints = stream.get('behaviorHints') or {}
    req = ((hints.get('proxyHeaders') or {}).get('request')) or {}
    if not req:
        return ''
    return '|' + urlencode(req, quote_via=quote)


def magnet(stream):
    mag = 'magnet:?xt=urn:btih:%s' % stream['infoHash']
    sd = stream.get('streamData') or {}
    name = sd.get('filename') or (stream.get('behaviorHints') or {}).get('filename')
    if name:
        mag += '&dn=' + quote(name)
    for src in stream.get('sources') or []:
        if src.startswith('tracker:'):
            mag += '&tr=' + quote(src[len('tracker:'):], safe='')
    return mag


def play_path(stream):
    kind = stream_kind(stream)
    if kind == 'url':
        return stream['url'] + _headers_suffix(stream)
    if kind == 'p2p':
        mag = magnet(stream)
        idx = stream.get('fileIdx')
        if p2p_handler() == 1:
            url = 'plugin://plugin.video.elementum/play?uri=' + quote(mag, safe='')
            if idx is not None:
                url += '&index=%s' % idx
            return url
        return 'plugin://plugin.video.torrest/play_magnet?magnet=' + quote(mag, safe='')
    if kind == 'youtube':
        return 'plugin://plugin.video.youtube/play/?video_id=' + stream['ytId']
    return None


# --------------------------------------------------------------------------
# Subtitles
# --------------------------------------------------------------------------

SUB_DIR = os.path.join(kodi.PROFILE, 'subs')


def _wanted_langs():
    raw = kodi.setting('sub_langs') or ''
    return [x.strip().lower() for x in raw.split(',') if x.strip()]


def collect_subtitles(stream, client, type_, video_id):
    """Return a list of local subtitle files for ListItem.setSubtitles."""
    if not kodi.setting_bool('subtitles'):
        return []
    subs = list(stream.get('subtitles') or [])
    hints = stream.get('behaviorHints') or {}
    sd = stream.get('streamData') or {}
    try:
        subs += client.subtitles(type_, video_id,
                                 filename=hints.get('filename') or sd.get('filename'),
                                 size=hints.get('videoSize') or sd.get('size'),
                                 video_hash=hints.get('videoHash'))
    except Exception as e:  # never block playback on subtitles
        kodi.log('subtitle lookup failed: %s' % e)
    wanted = _wanted_langs()
    if wanted:
        subs = [x for x in subs if str(x.get('lang', '')).lower()[:3] in wanted
                or str(x.get('lang', '')).lower() in wanted]
    limit = max(1, kodi.setting_int('sub_limit', 8))
    out, seen = [], set()
    # clear previous run's files
    if os.path.isdir(SUB_DIR):
        for f in os.listdir(SUB_DIR):
            try:
                os.remove(os.path.join(SUB_DIR, f))
            except OSError:
                pass
    kodi.ensure_dir(SUB_DIR)
    for i, sub in enumerate(subs):
        url = sub.get('url')
        if not url or url in seen or len(out) >= limit:
            continue
        seen.add(url)
        lang = re.sub(r'[^A-Za-z0-9_-]', '', str(sub.get('lang') or 'und'))[:12] or 'und'
        ext = 'vtt' if '.vtt' in url.lower() else 'srt'
        path = os.path.join(SUB_DIR, 'AIOStreams.%02d.%s.%s' % (i, lang, ext))
        try:
            req = Request(url, headers={'User-Agent': 'AIOStreams-Kodi'})
            with urlopen(req, timeout=15) as r:
                data = r.read()
            with open(path, 'wb') as f:
                f.write(data)
            out.append(path)
        except Exception as e:
            kodi.debug('subtitle download failed %s: %s' % (url, e))
    return out
