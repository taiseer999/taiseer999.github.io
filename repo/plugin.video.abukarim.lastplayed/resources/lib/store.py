# -*- coding: utf-8 -*-
"""History storage shared by the service and the plugin.

history.json in the add-on profile: a list of entries, newest first.
Writes are atomic (temp file + os.replace) and serialised with a lock file, so
the plugin and the service never corrupt it between them.
"""

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON_ID = 'plugin.video.abukarim.lastplayed'
OLD_ADDON_ID = 'plugin.video.last_played'


def _profile():
    path = xbmcvfs.translatePath('special://profile/addon_data/%s/' % ADDON_ID)
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    return path


def history_file():
    return os.path.join(_profile(), 'history.json')


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def debug(msg):
    try:
        if xbmcaddon.Addon(ADDON_ID).getSettingBool('debug'):
            log(msg)
    except Exception:
        pass


class _Lock(object):
    """Cross-process lock: O_EXCL lock file, stale after 10 s."""

    def __init__(self):
        self.path = os.path.join(_profile(), '.lock')
        self.fd = None

    def __enter__(self):
        deadline = time.time() + 5
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > 10:
                        os.remove(self.path)
                        continue
                except OSError:
                    continue
                if time.time() > deadline:
                    return self          # give up waiting, write anyway
                time.sleep(0.05)

    def __exit__(self, *a):
        if self.fd is not None:
            try:
                os.close(self.fd)
                os.remove(self.path)
            except OSError:
                pass


def load():
    try:
        with open(history_file(), 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save(items):
    fn = history_file()
    tmp = fn + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False)
    os.replace(tmp, fn)


def same(a, b):
    """Same title? (stream links change every play, so compare metadata)."""
    if a.get('dbid') and a.get('dbid') == b.get('dbid') and a.get('type') == b.get('type'):
        return True
    if a.get('type') != b.get('type'):
        return False
    ia, ib = a.get('ids') or {}, b.get('ids') or {}
    if a.get('type') == 'episode':
        if (ia.get('tmdb') and ia.get('tmdb') == ib.get('tmdb')
                or a.get('show') and a.get('show') == b.get('show')):
            return (str(a.get('season')) == str(b.get('season'))
                    and str(a.get('episode')) == str(b.get('episode')))
        return False
    for k in ('imdb', 'tmdb'):
        if ia.get(k) and ia.get(k) == ib.get(k):
            return True
    if a.get('title') and a.get('title') == b.get('title'):
        return str(a.get('year') or '') == str(b.get('year') or '')
    return bool(a.get('path')) and a.get('path') == b.get('path')


def upsert(entry, limit=100):
    """Put entry at the top, replacing an older copy of the same title."""
    with _Lock():
        items = load()
        for old in list(items):
            if same(old, entry):
                items.remove(old)
                for k, v in old.items():          # keep art/ids we had before
                    if k not in entry or entry[k] in ('', None, {}, []):
                        entry[k] = v
                art = dict(old.get('art') or {})
                art.update({k: v for k, v in (entry.get('art') or {}).items() if v})
                entry['art'] = art
        items.insert(0, entry)
        del items[max(1, int(limit)):]
        save(items)
    return entry


def get(key):
    for it in load():
        if it.get('key') == key:
            return it
    return None


# Set by the plugin right before it starts a replay, read once by the service:
# {"key": entry key, "mode": "saved"|"sources"|"library", "t": epoch}
REPLAY_PROP = 'abk.lastplayed.replay'


def update(key, **fields):
    with _Lock():
        items = load()
        for it in items:
            if it.get('key') == key:
                it.update(fields)
                save(items)
                return True
    return False


def remove(key):
    with _Lock():
        items = [i for i in load() if i.get('key') != key]
        save(items)


def clear():
    with _Lock():
        save([])


def migrate_old():
    """One-time import of plugin.video.last_played's lastPlayed.json."""
    marker = os.path.join(_profile(), '.migrated')
    if os.path.exists(marker):
        return 0
    open(marker, 'w').close()
    old = xbmcvfs.translatePath('special://profile/addon_data/%s/lastPlayed.json' % OLD_ADDON_ID)
    try:
        with open(old, 'r', encoding='utf-8') as f:
            rows = json.load(f)
    except (OSError, ValueError):
        return 0
    if not isinstance(rows, list):
        return 0
    out = []
    for r in rows:
        if not isinstance(r, dict) or not r.get('title'):
            continue
        t = r.get('type') or 'video'
        when = 0
        try:
            when = int(time.mktime(time.strptime('%s %s' % (r.get('date'), r.get('time')),
                                                  '%Y-%m-%d %H:%M:%S')))
        except Exception:
            pass
        try:
            dbid = int(r.get('id') or 0)
        except (TypeError, ValueError):
            dbid = 0
        ids = {}
        for k in ('tmdb', 'imdb'):
            if r.get(k):
                ids[k] = r[k]
        out.append({
            'key': 'm%d_%d' % (when, len(out)), 'type': t, 'title': r.get('title'),
            'year': r.get('year') or '', 'show': r.get('show') or '',
            'season': r.get('season') if r.get('season') not in ('', None) else -1,
            'episode': r.get('episode') if r.get('episode') not in ('', None) else -1,
            'dbid': dbid, 'ids': ids, 'plot': '',
            'art': {'poster': r.get('thumbnail') or '', 'fanart': r.get('fanart') or ''},
            'path': r.get('video') or r.get('file') or '', 'stream': '',
            'source_id': '', 'source': r.get('source') or '',
            'played_at': when, 'position': 0, 'total': 0,
        })
    if out:
        with _Lock():
            cur = load()
            for e in out:
                if not any(same(e, c) for c in cur):
                    cur.append(e)
            cur.sort(key=lambda i: i.get('played_at') or 0, reverse=True)
            save(cur[:200])
        log('imported %d entries from %s' % (len(out), OLD_ADDON_ID))
    return len(out)
