# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""local_folders.py - ABUKARIM TOOLS (4.10.0)

"My folders" for AB Search All: folders on this device or on the network
(smb://, nfs://, any path Kodi's VFS reads) searched next to the add-ons,
without Fen Light / Red Light folder scrapers.

  * The list lives in addon_data/<AB Tools>/ab_search_folders.json:
    [{"name": "NAS", "path": "smb://nas/Movies/"}, ...]
  * Each folder is walked once into a file index (ab_search_folders_index.json,
    rebuilt after INDEX_TTL or on demand) - a search then reads the index,
    not the share, so a large NAS answers in a moment.
  * Matching is EasyNews' rule (ab_search._en_match): the title's words, then
    the year (movies, +-1) or SxxEyy / 1x02 (episodes), tried on the file name
    and on it with its folder (and the folder above) in front, so both
    "Movie (2017)/movie-2160p.mkv" and "Show/Season 1/S01E02.mkv" match.
  * A pick plays the file directly with the title, year and ids on the
    ListItem (Kodi keeps the resume point by path).
"""
import json
import os
import re
import threading
import time

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

ADDON_ID = 'plugin.program.abukarimtools'
_DIR = xbmcvfs.translatePath('special://profile/addon_data/%s/' % ADDON_ID)
CONFIG = os.path.join(_DIR, 'ab_search_folders.json')
INDEX = os.path.join(_DIR, 'ab_search_folders_index.json')
INDEX_TTL = 6 * 3600
MAX_DEPTH = 6
MAX_FILES = 80000
VIDEO = ('.mkv', '.mp4', '.m4v', '.avi', '.ts', '.m2ts', '.mts', '.mov', '.wmv', '.webm', '.mpg', '.mpeg',
         '.iso', '.vob', '.divx', '.flv', '.3gp', '.ogm', '.strm')
_SKIP_DIRS = re.compile(r'^(?:\.|@eadir$|#recycle$|\$recycle\.bin$|system volume information$|lost\+found$)', re.I)
_JUNK = re.compile(r'(?<![a-z])(sample|trailer|teaser|featurette|extras?|behind[ ._-]the[ ._-]scenes|'
                   r'deleted[ ._-]scenes|interviews?|shorts)(?![a-z])', re.I)
_lock = threading.Lock()


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Folders] %s' % msg, level)


# ───────────────────────── config ─────────────────────────

def _read(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def _slash(path):
    path = str(path or '').strip()
    if not path:
        return ''
    sep = '\\' if ('\\' in path and '://' not in path) else '/'
    return path if path.endswith(('/', '\\')) else path + sep


def folders():
    out = []
    for f in _read(CONFIG, []):
        if isinstance(f, dict) and f.get('path'):
            out.append({'name': str(f.get('name') or '').strip() or _base(f['path']), 'path': _slash(f['path'])})
    return out


def _save(items):
    _write(CONFIG, [{'name': f['name'], 'path': f['path']} for f in items])
    _log('saved: %s' % ', '.join('%s = %s' % (f['name'], f['path']) for f in items))


def configured():
    return bool(folders())


def _base(path):
    p = str(path or '').rstrip('/\\')
    return re.split(r'[/\\]', p)[-1] or p


def display_name():
    """The source's name in Search All: the folder's own name when there is
    one folder, else 'My folders'."""
    items = folders()
    return items[0]['name'] if len(items) == 1 else T(32303)


def summary():
    n = len(folders())
    return T(32305) % n if n else T(32304)


# ───────────────────────── index ─────────────────────────

def _walk(root):
    """[relative file path] of the videos under root (depth <= MAX_DEPTH)."""
    files, stack, t0 = [], [('', 0)], time.time()
    mon = xbmc.Monitor()
    while stack:
        rel, depth = stack.pop()
        if mon.abortRequested():
            break
        try:
            dirs, names = xbmcvfs.listdir(root + rel)
        except Exception as e:
            _log('listdir %s%s: %s' % (root, rel, e), xbmc.LOGWARNING)
            if not rel:
                raise
            continue
        for n in names:
            if n.lower().endswith(VIDEO) and not n.startswith('.'):
                files.append(rel + n)
        if len(files) >= MAX_FILES:
            _log('%s: stopped at %d files' % (root, len(files)), xbmc.LOGWARNING)
            break
        if depth < MAX_DEPTH:
            for d in dirs:
                if not _SKIP_DIRS.search(d):
                    stack.append((rel + d + '/', depth + 1))
    _log('%s: %d videos indexed in %.1fs' % (root, len(files), time.time() - t0))
    return files


def index(folder, force=False):
    """The file list of one folder, from the index unless it is old."""
    path = folder['path']
    with _lock:
        data = _read(INDEX, {})
        ent = data.get(path) if isinstance(data, dict) else None
        if ent and not force and time.time() - float(ent.get('t') or 0) < INDEX_TTL:
            return ent.get('files') or []
    files = _walk(path)
    with _lock:
        data = _read(INDEX, {})
        if not isinstance(data, dict):
            data = {}
        known = {f['path'] for f in folders()}
        data = {k: v for k, v in data.items() if k in known}
        data[path] = {'t': time.time(), 'files': files}
        _write(INDEX, data)
    return files


# ───────────────────────── search ─────────────────────────

def _size(full):
    try:
        st = xbmcvfs.Stat(full)
        return st.st_size() or 0
    except Exception:
        return 0


def _quality(name, size):
    m = re.search(r'(?<![a-z0-9])(2160p|4k|uhd|1080p|1080i|720p|576p|480p)(?![a-z0-9])', name.lower())
    if m:
        q = m.group(1)
        return '4K' if q in ('2160p', '4k', 'uhd') else ('1080P' if q.startswith('1080') else
                                                         ('720P' if q == '720p' else 'SD'))
    gb = size / 1073741824.0
    return '4K' if gb >= 30 else ('1080P' if gb >= 4 else ('720P' if gb >= 1.2 else 'SD'))


def search(media, words_fn, match_fn):
    """Rows in the Fen Light 'folders' shape for Search All."""
    ep = media['media_type'] == 'episode'
    title = (media.get('tvshowtitle') if ep else media.get('title')) or media.get('title') or ''
    words = words_fn(title)
    if not words:
        raise ValueError('no title')
    year = str(media.get('year') or '')[:4]
    season = int(media['season']) if ep else None
    episode = int(media['episode']) if ep else None
    out, seen = [], set()
    for folder in folders():
        try:
            files = index(folder)
        except Exception as e:
            _log('%s not reachable: %s' % (folder['path'], e), xbmc.LOGWARNING)
            continue
        hits = 0
        for rel in files:
            parts = rel.split('/')
            stem = re.sub(r'\.[^.]+$', '', parts[-1])
            dirs = parts[:-1]
            if _JUNK.search(stem) or any(_JUNK.fullmatch(d.strip()) for d in dirs):
                continue
            cands = [stem]
            if dirs:
                cands.append(dirs[-1] + ' ' + stem)
            if len(dirs) > 1:
                cands.append(dirs[-2] + ' ' + stem)
                cands.append(dirs[-2] + ' ' + dirs[-1] + ' ' + stem)
            hit = next((c for c in cands if match_fn(c, words, year, season, episode)), None)
            if hit is None:
                continue
            full = folder['path'] + rel
            if full in seen:
                continue
            seen.add(full)
            size = _size(full)
            gb = round(size / 1073741824.0, 2)
            name = parts[-1]
            ext = name.rsplit('.', 1)[-1].upper() if '.' in name else ''
            out.append({'name': name, 'display_name': re.sub(r'[._]+', ' ', hit).strip(),
                        'quality': _quality(' '.join(dirs[-1:] + [name]), size),
                        'size': gb, 'size_label': ('%.2f GB' % gb) if gb else '',
                        'scrape_provider': 'folders', 'source': folder['name'], 'debrid': '',
                        'extraInfo': ' | '.join(x for x in (ext, folder['name']) if x),
                        'abk_loc': {'path': full}})
            hits += 1
        _log('%s: %d match "%s"' % (folder['name'], hits, title))
    out.sort(key=lambda r: -r['size'])
    return out


def play(item, media, meta=None):
    """Play the picked file with the title / ids on its ListItem."""
    path = ((item or {}).get('abk_loc') or {}).get('path')
    if not path:
        return False
    meta = meta or {}
    ep = media.get('media_type') == 'episode'
    label = (media.get('tvshowtitle') if ep else media.get('title')) or item.get('display_name') or item.get('name')
    li = xbmcgui.ListItem(label, path=path, offscreen=True)
    try:
        tag = li.getVideoInfoTag()
        tag.setMediaType('episode' if ep else 'movie')
        tag.setTitle(meta.get('ep_name') or label if ep else label)
        if ep:
            tag.setTvShowTitle(media.get('tvshowtitle') or '')
            tag.setSeason(int(media['season']))
            tag.setEpisode(int(media['episode']))
        if str(media.get('year') or '')[:4].isdigit():
            tag.setYear(int(str(media['year'])[:4]))
        ids = {'tmdb': str(media.get('tmdb_id') or '')}
        if media.get('imdb'):
            ids['imdb'] = media['imdb']
        tag.setUniqueIDs({k: v for k, v in ids.items() if v}, 'tmdb')
        if meta.get('plot'):
            tag.setPlot(meta['plot'])
    except Exception as e:
        _log('info tag: %s' % e, xbmc.LOGDEBUG)
    art = {k: meta[k] for k in ('fanart', 'clearlogo', 'poster', 'thumb') if meta.get(k)}
    if art:
        li.setArt(art)
    _log('play: %s' % path)
    xbmc.Player().play(path, li)
    return True


# ───────────────────────── manager (Mods > Search All: my folders) ─────────────────────────

def _ask_path():
    choice = xbmcgui.Dialog().select(T(32306), [T(32307), T(32296)])
    if choice == 0:
        p = xbmcgui.Dialog().browse(0, T(32306), 'files')
        return p if p and p != 'false' else ''
    if choice == 1:
        p = xbmcgui.Dialog().input(T(32296), 'smb://')
        return p.strip() if p and p.strip() not in ('smb://', 'nfs://') else ''
    return ''


def _check(path):
    try:
        xbmcvfs.listdir(path)
        return True
    except Exception:
        return False


def _reindex(items):
    bg = xbmcgui.DialogProgressBG()
    bg.create('AB Search All', T(32300))
    total = 0
    try:
        for n, f in enumerate(items):
            bg.update(int(100 * n / max(1, len(items))), 'AB Search All', f['name'])
            try:
                total += len(index(f, force=True))
            except Exception as e:
                xbmcgui.Dialog().notification('AB Search All', T(32302) % f['name'],
                                              xbmcgui.NOTIFICATION_WARNING, 5000)
                _log('index %s: %s' % (f['path'], e), xbmc.LOGWARNING)
    finally:
        bg.close()
    xbmcgui.Dialog().notification('AB Search All', T(32301) % (total, len(items)),
                                  xbmcgui.NOTIFICATION_INFO, 4000)


def run():
    while True:
        items = folders()
        rows = [xbmcgui.ListItem('[B]+ %s[/B]' % T(32295))]
        for f in items:
            li = xbmcgui.ListItem(f['name'], f['path'])
            li.setArt({'icon': 'DefaultFolder.png'})
            rows.append(li)
        if items:
            rows.append(xbmcgui.ListItem(T(32300)))
        pick = xbmcgui.Dialog().select(T(32293), rows, useDetails=True)
        if pick < 0:
            return
        if pick == 0:
            path = _slash(_ask_path())
            if not path:
                continue
            if any(f['path'] == path for f in items):
                continue
            if not _check(path):
                xbmcgui.Dialog().ok('AB Search All', T(32302) % path)
                continue
            name = xbmcgui.Dialog().input(T(32297), _base(path)).strip() or _base(path)
            items.append({'name': name, 'path': path})
            _save(items)
            _reindex([items[-1]])
            continue
        if items and pick == len(items) + 1:
            _reindex(items)
            continue
        f = items[pick - 1]
        # 4.10.1: a full dialog titled with the folder (the context menu was easy to miss)
        acts = [T(32299), T(32308), T(32300), T(32298)]
        act = xbmcgui.Dialog().select('%s  -  %s' % (f['name'], f['path']), acts)
        if act == 0:
            name = (xbmcgui.Dialog().input(T(32297), f['name']) or '').strip()
            _log('rename %s -> %s' % (f['name'], name or '(cancelled)'))
            if name and name != f['name']:
                f['name'] = name
                _save(items)
                xbmcgui.Dialog().notification('AB Search All', name, xbmcgui.NOTIFICATION_INFO, 2500)
        elif act == 1:
            path = _slash(_ask_path())
            if not path or path == f['path'] or any(x['path'] == path for x in items):
                continue
            if not _check(path):
                xbmcgui.Dialog().ok('AB Search All', T(32302) % path)
                continue
            f['path'] = path
            _save(items)
            _reindex([f])
        elif act == 2:
            _reindex([f])
        elif act == 3 and xbmcgui.Dialog().yesno('AB Search All', '%s[CR]%s' % (f['name'], f['path']),
                                                 nolabel=T(32290), yeslabel=T(32298)):
            items.remove(f)
            _save(items)
