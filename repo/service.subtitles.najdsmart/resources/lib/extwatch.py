# -*- coding: utf-8 -*-
"""Piers edition: time ANY external subtitle that plays in Kodi.

Whatever puts a subtitle file on the player - the subtitle window with any
service, Dex Hub / DexSubtitles, another add-on, a file beside the video -
Najd times it the way it times its own: on the video's own subtitle timeline
(MKV index) at once, else on the sound in the background.

Kodi gives the playing subtitle's name and language, not its file. Kodi names
an external stream after its file name (the video's name taken off the front,
the language and forced / default flags taken out), so the file is found by
that name among the places subtitle files land: special://temp (the subtitle
window copies a stream's subtitle there), the add-ons' subtitle folders, the
custom subtitle folder and the folder of the video. A fresh file wins; when
two different files fit and none is fresh, nothing is guessed.
"""
import hashlib
import json
import os
import re
import threading
import time

import xbmc
import xbmcvfs

from .common import PROFILE, log, notify, set_status, setting_bool

SUB_EXTS = ('.srt', '.ass', '.ssa', '.vtt')
MAX_BYTES = 8 * 1024 * 1024
_SPLIT = re.compile(r'[\s.\-_\[\]()]+')
_FLAGS = {'external', 'forced', 'default', 'none', 'sdh', 'cc', 'hi'}
_SUB_DIRS = ('subs', 'subtitles', 'sub', 'subtitle')
_ADDON_DIRS = ('plugin.video.dexhub/subtitle_cache', 'service.subtitles.dexworld',
               'service.subtitles.a4ksubtitles', 'service.subtitles.opensubtitles-com',
               'service.subtitles.subdl-com')

QUIET_UNTIL = [0.0]      # Najd itself just set a subtitle: not an outside one


def najd_set():
    """Called whenever Najd puts a subtitle on the player."""
    QUIET_UNTIL[0] = time.time() + 8


def _rpc(method, params):
    try:
        r = json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
        return r.get('result')
    except Exception:
        return None


def _state():
    r = _rpc('Player.GetProperties', {'playerid': 1, 'properties':
                                      ['currentsubtitle', 'subtitles', 'subtitleenabled']}) or {}
    cur = r.get('currentsubtitle') or {}
    return {'enabled': bool(r.get('subtitleenabled')), 'count': len(r.get('subtitles') or []),
            'index': cur.get('index', -1), 'name': cur.get('name') or '',
            'lang': (cur.get('language') or '').lower(), 'external': cur.get('isexternal')}


def _tokens(text):
    return [t for t in _SPLIT.split((text or '').lower()) if t]


def _lang_words(lang):
    out = {lang} if lang else set()
    for fmt in (xbmc.ISO_639_1, xbmc.ISO_639_2, xbmc.ENGLISH_NAME):
        try:
            v = xbmc.convertLanguage(lang, fmt)
            if v:
                out.add(v.lower())
        except Exception:
            pass
    return out


_LANG_CACHE = {}


def _is_lang(tok):
    """A file-name token Kodi would take for a language (en, ara, arabic...)."""
    if tok in _LANG_CACHE:
        return _LANG_CACHE[tok]
    ok = False
    if tok.isalpha() and 2 <= len(tok) <= 12:
        try:
            ok = bool(xbmc.convertLanguage(tok, xbmc.ENGLISH_NAME))
        except Exception:
            ok = False
    _LANG_CACHE[tok] = ok
    return ok


def _list(folder, depth=1):
    """Subtitle files under folder (local or Kodi VFS): [(path, mtime, size)]."""
    out = []
    if os.path.isabs(folder) and not os.path.isdir(folder):
        return out
    try:
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if os.path.isdir(full):
                    if depth > 0 and not os.path.realpath(full).startswith(os.path.realpath(PROFILE)):
                        out.extend(_list(full, depth - 1))
                elif name.lower().endswith(SUB_EXTS):
                    st = os.stat(full)
                    if 0 < st.st_size <= MAX_BYTES:
                        out.append((full, st.st_mtime, st.st_size))
            return out
        dirs, files = xbmcvfs.listdir(folder)
        sep = '' if folder.endswith('/') else '/'
        for name in files:
            if name.lower().endswith(SUB_EXTS):
                full = folder + sep + name
                st = xbmcvfs.Stat(full)
                if 0 < st.st_size() <= MAX_BYTES:
                    out.append((full, st.st_mtime(), st.st_size()))
        if depth > 0:
            for d in dirs:
                if d.lower() in _SUB_DIRS:
                    out.extend(_list(folder + sep + d, 0))
    except Exception as e:
        log('external sync: cannot list %s (%s)' % (folder, e))
    return out


def _folders(video_path):
    tp = xbmcvfs.translatePath
    out = [tp('special://temp/')]
    for d in _ADDON_DIRS:
        out.append(tp('special://profile/addon_data/%s' % d))
    custom = (_rpc('Settings.GetSettingValue', {'setting': 'subtitles.custompath'}) or {}).get('value')
    if custom:
        out.append(tp(custom))
    p = (video_path or '').split('|', 1)[0]
    if p and not p.startswith(('http://', 'https://', 'plugin://', 'pvr://', 'bluray://')):
        out.append(p.rsplit('/', 1)[0] + '/' if '/' in p else os.path.dirname(p))
    return out


def find_file(st, video_path, since):
    """The file of the playing external subtitle, or ''."""
    vname = os.path.splitext((video_path or '').split('|', 1)[0].rsplit('/', 1)[-1])[0].lower()
    vname = vname.split('?', 1)[0]
    want = [t for t in _tokens(st['name']) if t not in _FLAGS]
    langs = _lang_words(st['lang'])
    want = [t for t in want if t not in langs]
    profile = os.path.realpath(PROFILE)
    found = []
    seen = set()
    for folder in _folders(video_path):
        for path, mtime, size in _list(folder):
            if path in seen or (os.path.isabs(path) and os.path.realpath(path).startswith(profile)):
                continue
            seen.add(path)
            stem = os.path.splitext(os.path.basename(path))[0].lower()
            if vname and stem.startswith(vname):
                stem = stem[len(vname):]
            toks = [t for t in _tokens(stem) if t not in _FLAGS]
            flangs = set(t for t in toks if t in langs or _is_lang(t))
            if flangs and st['lang'] not in ('', 'und') and not (flangs & langs):
                continue          # another language's file
            rest = [t for t in toks if t not in flangs]
            if want and not all(w in rest for w in want):
                continue
            if not want and rest and mtime < since:
                continue          # a nameless stream is a file named only video + language
            found.append((mtime, path, size))
    if not found:
        return ''
    found.sort(reverse=True)
    fresh = [f for f in found if f[0] >= since]
    if fresh:
        return fresh[0][1]
    if len(set(f[2] for f in found)) == 1:
        return found[0][1]
    log('external sync: %d files fit "%s" - not guessing' % (len(found), st['name']))
    return ''


def _digest(path):
    try:
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                return hashlib.sha1(f.read()).hexdigest()
        with xbmcvfs.File(path) as f:
            return hashlib.sha1(f.readBytes()).hexdigest()
    except Exception:
        return ''


def _local_copy(path):
    if os.path.isfile(path):
        return path
    from .common import TEMP_DIR
    dst = os.path.join(TEMP_DIR, 'ext_src' + os.path.splitext(path)[1].lower())
    return dst if xbmcvfs.copy(path, dst) else ''


def watch(player, video_path, started):
    """Runs while video_path plays; times each outside subtitle once."""
    from . import media, pipeline
    done = set()
    last = None
    stable = 0
    base = None          # streams the video started with; outside files are added after them
    mon = xbmc.Monitor()
    while not mon.abortRequested():
        if mon.waitForAbort(2):
            return
        try:
            if not player.isPlayingVideo() or player.getPlayingFile() != video_path:
                return
        except Exception:
            return
        if not setting_bool('ext_sync', True) or not setting_bool('auto_sync', True):
            continue
        st = _state()
        if base is None:
            base = st['count']
        key = (st['index'], st['name'], st['count'])
        if key != last:
            last, stable = key, 0
            continue
        stable += 1
        if stable not in (1, 3) or time.time() < QUIET_UNTIL[0] or not st['enabled'] or st['index'] < 0:
            continue
        added = st['count'] > base and st['index'] == st['count'] - 1
        if st['external'] is False or (st['external'] is None and not added
                                       and 'external' not in st['name'].lower()):
            continue
        path = find_file(st, video_path, started - 5)
        if not path:
            log('external sync: file of "%s" (%s) not found' % (st['name'], st['lang']))
            continue
        digest = _digest(path)
        if not digest or digest in done:
            continue
        done.add(digest)
        stable = 9          # handled: no second try on this subtitle
        log('external sync: %s' % path)
        try:
            src = _local_copy(path)
            if not src:
                continue
            set_status('جارٍ ضبط توقيت الترجمة...')
            r = pipeline.sync_external(src, media.current())
        except Exception as e:
            log('external sync failed: %s' % e, xbmc.LOGERROR)
            set_status('')
            continue
        if not r:
            set_status('')
            continue
        new_path, mode, lines = r
        if mode == 'now' and player.isPlayingVideo() and player.getPlayingFile() == video_path:
            najd_set()
            player.setSubtitles(new_path)
            player.showSubtitles(True)
            set_status('الترجمة مضبوطة ✓', 'ok')
            if lines:
                notify(' | '.join(lines), seconds=6)
        elif mode == 'same':
            set_status('الترجمة مضبوطة ✓', 'ok')
        else:
            set_status(lines[0] if lines else '')
            if lines:
                notify(' | '.join(lines), seconds=5)


_CURRENT = [None, None]


def start(player, video_path):
    if _CURRENT[0] == video_path and _CURRENT[1] is not None and _CURRENT[1].is_alive():
        return _CURRENT[1]
    t = threading.Thread(target=watch, args=(player, video_path, time.time()),
                         name='najd-extwatch', daemon=True)
    t.start()
    _CURRENT[0], _CURRENT[1] = video_path, t
    return t
