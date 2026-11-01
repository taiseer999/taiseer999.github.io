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


def labels(stream):
    """(label, label2, plot) for list items / select dialog."""
    name = clean(stream.get('name') or '')
    desc = clean(stream.get('description') or stream.get('title') or '')
    sd = stream.get('streamData') or {}
    filename = sd.get('filename') or (stream.get('behaviorHints') or {}).get('filename') or ''
    if kodi.setting_int('label_style', 0) == 1:
        compact = compact_label(stream)
        if compact:
            return compact, filename or desc.replace('\n', ' | '), '\n'.join(x for x in (name, desc) if x)
    return name.replace('\n', ' '), desc.replace('\n', ' | '), '\n'.join(x for x in (name, desc) if x)


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
