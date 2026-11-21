# -*- coding: utf-8 -*-
"""Collect info about the playing video (title, ids, season/episode, hash)."""
import json
import os
import re
import struct
import urllib.parse

import xbmc
import xbmcvfs

from .common import log


def _rpc(method, params):
    q = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    try:
        return json.loads(xbmc.executeJSONRPC(q)).get('result', {})
    except Exception:
        return {}


def os_hash(path):
    """OpenSubtitles hash (size + 64k head + 64k tail checksum)."""
    try:
        f = xbmcvfs.File(path)
        size = f.size()
        if not size or size < 65536 * 2:
            f.close()
            return None, size
        h = size
        head = f.readBytes(65536)
        f.seek(max(0, size - 65536), 0)
        tail = f.readBytes(65536)
        f.close()
        for chunk in (bytes(head), bytes(tail)):
            for (v,) in struct.iter_unpack('<q', chunk[:len(chunk) // 8 * 8]):
                h = (h + v) & 0xFFFFFFFFFFFFFFFF
        return '%016x' % h, size
    except Exception as e:
        log('hash failed: %s' % e)
        return None, 0


_SE_RE = re.compile(r'[Ss](\d{1,2})[ ._-]?[Ee](\d{1,3})|(\d{1,2})x(\d{2,3})')
_YEAR_RE = re.compile(r'[\.\s\(\[_-]((?:19|20)\d{2})[\.\s\)\]_-]')


_RELEASE_RE = re.compile(r'(?i)\bS\d{1,2}\s*E\d{1,3}\b|\b(480|576|720|1080|2160)p\b|\bx26[45]\b|\bh\.?26[45]\b'
                         r'|\bblu-?ray\b|\bweb-?(dl|rip)\b|\bhdtv\b')


def guess_from_name(name):
    base = os.path.splitext(os.path.basename(urllib.parse.unquote(name)))[0]
    info = {'season': '', 'episode': '', 'year': '', 'title': ''}
    m = _SE_RE.search(base)
    if m:
        info['season'] = str(int(m.group(1) or m.group(3)))
        info['episode'] = str(int(m.group(2) or m.group(4)))
        info['title'] = re.sub(r'[._]', ' ', base[:m.start()]).strip(' -')
    y = _YEAR_RE.search(' ' + base + ' ')
    if y:
        info['year'] = y.group(1)
        if not info['title']:
            info['title'] = re.sub(r'[._]', ' ', (' ' + base)[:y.start()]).strip(' -([')
    if not info['title']:
        info['title'] = re.sub(r'[._]', ' ', re.split(
            r'[\.\s](?:480p|720p|1080p|2160p|4k|web|bluray|hdtv|x264|x265|hevc)', base, flags=re.I)[0]).strip()
    return info


_FAMILY = [
    ('bluray', ('bluray', 'blu', 'bdrip', 'brrip', 'bdremux', 'remux', 'bd25', 'bd50', 'uhdbd')),
    ('web', ('web', 'webdl', 'webrip', 'amzn', 'nf', 'dsnp', 'hmax', 'atvp', 'hulu', 'itunes', 'pcok', 'max')),
    ('hdtv', ('hdtv', 'pdtv', 'tvrip')),
    ('dvd', ('dvd', 'dvdrip', 'dvd5', 'dvd9')),
]


def release_family(name):
    """bluray / web / hdtv / dvd — releases of the same family share timing far more often."""
    toks = release_tokens(name)
    joined = re.sub(r'[^a-z0-9]', '', (name or '').lower())
    for fam, words in _FAMILY:
        if toks & set(words) or any(w in joined for w in ('webdl', 'webrip', 'bluray', 'bdremux') if w in words):
            return fam
    return ''


def release_tokens(name):
    base = os.path.splitext(os.path.basename(urllib.parse.unquote(name or '')))[0].lower()
    return set(t for t in re.split(r'[^a-z0-9]+', base) if t)


def _home(prop):
    try:
        import xbmcgui
        return (xbmcgui.Window(10000).getProperty(prop) or '').strip()
    except Exception:
        return ''


def is_dexhub_item(player=None):
    """True when Dex Hub started the playing video (it has its own subtitle flow)."""
    try:
        return (player or xbmc.Player()).getPlayingItem().getProperty('dexhub_item') == '1'
    except Exception:
        return False


def _ids_from_addons(v, player):
    """Piers edition: streams from add-ons often carry no ids on the info tag.
    Dex Hub publishes them as dexhub.sub.* Home properties, and Fen Light /
    Umbrella / POV / Seren as the JSON in script.trakt.ids - fill the gaps
    from those so the searches can go by id instead of by title."""
    found = {}
    if is_dexhub_item(player):
        found = {'imdb': _home('dexhub.sub.imdb_id'), 'tmdb': _home('dexhub.sub.tmdb_id')}
        if _home('dexhub.sub.mediatype') == 'episode' and not v['episode']:
            v['season'] = _home('dexhub.sub.season')
            v['episode'] = _home('dexhub.sub.episode')
            if not v['tvshow']:
                v['tvshow'] = _home('dexhub.sub.title') or v['title']
        elif not v['title'] and not v['tvshow']:
            v['title'] = _home('dexhub.sub.title')
    else:
        raw = _home('script.trakt.ids')
        if raw:
            try:
                d = json.loads(raw)
                found = {'imdb': str(d.get('imdb') or ''), 'tmdb': str(d.get('tmdb') or '')}
            except ValueError:
                pass
    imdb = found.get('imdb') or ''
    if imdb and not imdb.startswith('tt') and imdb.isdigit():
        imdb = 'tt%07d' % int(imdb)
    if v['tvshow'] or v['episode']:
        # for an episode these are the SHOW's ids
        if imdb.startswith('tt') and not v['show_imdb']:
            v['show_imdb'] = imdb
        if found.get('tmdb') and not v['show_tmdb']:
            v['show_tmdb'] = found['tmdb']
    else:
        if imdb.startswith('tt') and not v['imdb']:
            v['imdb'] = imdb
        if found.get('tmdb') and not v['tmdb']:
            v['tmdb'] = found['tmdb']


def current():
    """Return a dict describing the playing (or selected) video."""
    player = xbmc.Player()
    path = ''
    tag = None
    duration = 0.0
    try:
        if player.isPlayingVideo():
            path = player.getPlayingFile()
            tag = player.getVideoInfoTag()
            duration = player.getTotalTime()
    except Exception:
        pass

    def il(x):
        return xbmc.getInfoLabel(x)

    v = {
        'path': path,
        'title': il('VideoPlayer.OriginalTitle') or il('VideoPlayer.Title'),
        'tvshow': il('VideoPlayer.TVshowtitle'),
        'year': il('VideoPlayer.Year'),
        'season': il('VideoPlayer.Season'),
        'episode': il('VideoPlayer.Episode'),
        'imdb': '', 'tmdb': '', 'show_imdb': '', 'show_tmdb': '',
        'fps': 0.0, 'hash': None, 'size': 0, 'filename': '', 'duration': duration,
    }
    if tag is not None:
        try:
            v['imdb'] = tag.getUniqueID('imdb') or ''
            v['tmdb'] = tag.getUniqueID('tmdb') or ''
            if not v['imdb']:
                n = tag.getIMDBNumber() or ''
                if n.startswith('tt'):
                    v['imdb'] = n
        except Exception:
            pass
    _ids_from_addons(v, player)
    # Show ids for episodes
    show_dbid = il('VideoPlayer.TvShowDBID')
    if v['tvshow'] and show_dbid and show_dbid.isdigit():
        r = _rpc('VideoLibrary.GetTVShowDetails',
                 {'tvshowid': int(show_dbid), 'properties': ['uniqueid', 'imdbnumber']})
        uid = r.get('tvshowdetails', {}).get('uniqueid', {})
        v['show_imdb'] = uid.get('imdb', '')
        v['show_tmdb'] = uid.get('tmdb', '')
        if not v['show_imdb']:
            n = r.get('tvshowdetails', {}).get('imdbnumber', '')
            if n.startswith('tt'):
                v['show_imdb'] = n
    if v['tvshow'] and v['imdb'] and not v['show_imdb']:
        # many addons set the show's imdb on episodes
        pass
    try:
        v['fps'] = float(il('Player.Process(videofps)') or 0)
    except ValueError:
        v['fps'] = 0.0

    # filename (strip addon/stream junk)
    fname = path
    if path.startswith(('http://', 'https://')):
        fname = urllib.parse.urlparse(path).path
    v['filename'] = os.path.basename(urllib.parse.unquote(fname.split('|')[0]))

    # a player that knows nothing about the video shows its release name as the title
    # ('Prisoner 951 S01E02 1080p BluRay x264-PRiSONER'): keep only the name
    for k in ('title', 'tvshow'):
        if v[k] and _RELEASE_RE.search(v[k]):
            clean = guess_from_name(v[k] + '.mkv')['title']
            if clean:
                v[k] = clean
    # fill gaps from the file name
    g = guess_from_name(v['filename'])
    if not v['title'] and not v['tvshow']:
        if g['season']:
            v['tvshow'] = g['title']
        else:
            v['title'] = g['title']
    if not v['season'] and g['season']:
        v['season'], v['episode'] = g['season'], g['episode']
        if not v['tvshow']:
            v['tvshow'] = v['title'] or g['title']
    if not v['year']:
        v['year'] = g['year']
    if v['season'] in ('-1', '0') and not v['episode']:
        v['season'] = ''

    # hash only for local / smb / nfs files
    if path and not path.startswith(('http', 'plugin://', 'pvr://', 'rtmp', 'stack://')):
        v['hash'], v['size'] = os_hash(path)
    v['is_episode'] = bool(v['tvshow'] and v['episode'])
    log('video: %s' % {k: v[k] for k in v if k != 'path'})
    return v


def is_arabic_code(code):
    """'ar', 'ara', 'arabic', 'ar-SA', 'عربي' — but not 'arm'/'armenian'."""
    c = (code or '').strip().lower()
    return c in ('ar', 'ara', 'arabic') or c.startswith(('ar-', 'ar_', 'arabic', 'عرب'))


def subtitle_streams_have_arabic():
    try:
        langs = xbmc.Player().getAvailableSubtitleStreams() or []
        return any(is_arabic_code(l) for l in langs)
    except Exception:
        return False


def _is_ar(lang, name=''):
    lang = (lang or '').lower()
    name = (name or '').lower()
    return lang in ('ar', 'ara', 'arabic') or lang.startswith('ar-') or \
        'arabic' in name or 'عرب' in name


def enable_arabic_stream():
    """Piers edition: the video carries an Arabic subtitle but Kodi showed
    another one (or none) - switch to the Arabic one and turn subtitles on.
    Prefers a full (not forced) and not hearing-impaired track. Returns
    'already' when Arabic is on screen, 'switched' after switching, '' when
    there is no Arabic track or the switch failed."""
    def rpc(method, params):
        try:
            return json.loads(xbmc.executeJSONRPC(json.dumps(
                {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}))).get('result')
        except Exception:
            return None
    pid = None
    for p in rpc('Player.GetActivePlayers', {}) or []:
        if p.get('type') == 'video':
            pid = p.get('playerid')
    if pid is None:
        return ''
    props = rpc('Player.GetProperties', {'playerid': pid, 'properties':
                                         ['subtitles', 'currentsubtitle', 'subtitleenabled']}) or {}
    subs = [s for s in props.get('subtitles') or [] if _is_ar(s.get('language'), s.get('name'))]
    if not subs:
        return ''
    cur = props.get('currentsubtitle') or {}
    if props.get('subtitleenabled') and _is_ar(cur.get('language'), cur.get('name')) \
            and not cur.get('isforced'):
        return 'already'
    subs.sort(key=lambda s: (bool(s.get('isforced')), bool(s.get('isimpaired')), s.get('index', 0)))
    best = subs[0]
    ok = rpc('Player.SetSubtitle', {'playerid': pid, 'subtitle': best.get('index', 0), 'enable': True})
    log('arabic stream: switched to #%s (%s, forced=%s) -> %s'
        % (best.get('index'), best.get('name') or best.get('language'), best.get('isforced'), ok))
    return 'switched' if ok == 'OK' else ''
