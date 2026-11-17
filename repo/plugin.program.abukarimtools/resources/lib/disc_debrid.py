# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""
disc_debrid.py - ABUKARIM TOOLS (4.8.81)

Whole Blu-ray discs that come as a folder (BDMV/...) in a torrent, from a
debrid account. The source add-on (Red Light, Fen Light...) plays only the
largest file of such a release - BDMV/STREAM/00278.m2ts, the main movie
without its menus (kodi.log 2026-11-15: John Wick 3 / 4 from AllDebrid).

With Toggles > "AF3: Disc Menu for ISO Streams" on, the AF3 "Disc Menu"
button shows while that .m2ts plays. Pressing it:
  1. takes the torrent hash of the release picked in Search All
     (ab_search -> remember_pick, Home abk.disc.pick),
  2. lists the torrent's files from the debrid account linked in Account
     Manager (script.module.acctmgr: alldebrid.token / torbox.token /
     premiumize.token),
  3. has disc_stream serve the disc folder on 127.0.0.1: every file is a
     redirect to its debrid link, asked for the first time Kodi reads that
     file (index.bdmv, MovieObject.bdmv and the playlists are asked at once),
  4. reopens the film as bluray://<folder>/menu.
Real-Debrid lists a torrent's files only as a new download, so it is not
offered here.
"""
import json
import re
import threading
import time
import urllib.parse
import urllib.request

import xbmc
import xbmcgui

PICK_PROP = 'abk.disc.pick'
PICK_MAX_AGE = 12 * 3600
AM_ID = 'script.module.acctmgr'
AGENT = 'abtools'
AD_API = 'https://api.alldebrid.com'
TB_API = 'https://api.torbox.app/v1/api'
PM_API = 'https://www.premiumize.me/api'
SERVICES = {'AD': 'AllDebrid', 'TB': 'TorBox', 'PM': 'Premiumize'}
_TOKEN_KEY = {'AD': 'alldebrid.token', 'TB': 'torbox.token', 'PM': 'premiumize.token'}
_PART = re.compile(r'/(?:BDMV/STREAM/)?\d{5}\.m2ts$', re.I)
_PRE = re.compile(r'^BDMV/(?:index\.bdmv|MovieObject\.bdmv|PLAYLIST/[^/]+\.mpls)$', re.I)
_LINK_KEEP = 3 * 3600


class DebridError(Exception):
    """text for the log; sid / arg: the string shown to the user (strings_map)."""

    def __init__(self, text, sid=32272, arg=None):
        Exception.__init__(self, text)
        self.sid = sid
        self.arg = text if arg is None else arg


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Disc] %s' % msg, level)


# ───────────────────────── the Search All pick ─────────────────────────

def remember_pick(item, code):
    """ab_search, at every pick: the release's torrent hash and debrid service
    (cleared for a pick that has neither)."""
    home = xbmcgui.Window(10000)
    hsh = str((item or {}).get('hash') or '').strip().lower()
    if code in SERVICES and re.match(r'^[0-9a-f]{40}$', hsh):
        home.setProperty(PICK_PROP, json.dumps({'hash': hsh, 'svc': code, 'ts': int(time.time()),
                                                'name': str(item.get('name') or '')[:200]}))
        _log('pick kept for the Disc Menu button: %s %s' % (code, hsh[:8]))
    else:
        home.clearProperty(PICK_PROP)
        _log('pick not usable for the Disc Menu button (service %r, hash %s)'
             % (code or '', 'ok' if re.match(r'^[0-9a-f]{40}$', hsh) else (repr(hsh[:12]) if hsh else 'none')))


def current_pick():
    """The pick the Disc Menu button works on: a Search All pick (torrent hash)
    or, 4.8.87, the playing disc stream itself (service, file name - the
    torrent is then found in the account by that file, see bind_playing)."""
    try:
        pick = json.loads(xbmcgui.Window(10000).getProperty(PICK_PROP) or '{}')
    except ValueError:
        return {}
    if not (pick.get('hash') or pick.get('file')) or time.time() - float(pick.get('ts') or 0) > PICK_MAX_AGE:
        return {}
    return pick


def service_of(url):
    """Debrid service of a download link, by its host."""
    host = urllib.parse.urlsplit(str(url or '').split('|', 1)[0]).netloc.lower()
    if host.endswith(('debrid.it', 'alldebrid.com', 'alldebrid.fr')):
        return 'AD'
    if 'torbox' in host or host.endswith('tb-cdn.st'):
        return 'TB'
    if 'premiumize' in host or host.endswith('energycdn.com'):
        return 'PM'
    return ''


def _base(url):
    return urllib.parse.unquote(urllib.parse.urlsplit(str(url).split('|', 1)[0]).path).rsplit('/', 1)[-1]


def bind_playing(path):
    """Service, when a stream starts (4.8.87). A disc stream (.../00278.m2ts)
    from a debrid host gets a pick for the Disc Menu button whatever started it
    (Search All, or the add-on's own source window): a Search All pick made in
    the last 3 minutes is tied to this file (it has the torrent hash); otherwise
    the pick is the file itself (service + name), and the button finds the
    torrent in the account by name and size. Anything else drops the pick."""
    home = xbmcgui.Window(10000)
    if not is_disc_part(path):
        low = str(path or '').lower()
        if not (low.startswith(('bluray://', 'udf://')) or '/abkdisc/' in low):
            home.clearProperty(PICK_PROP)
        return
    name, code = _base(path), service_of(path)
    pick = current_pick()
    if pick.get('hash') and not pick.get('file') and time.time() - float(pick.get('ts') or 0) < 180:
        pick['file'] = name
    elif not (pick.get('file') == name and pick.get('svc') == (code or pick.get('svc'))):
        if code not in SERVICES:
            home.clearProperty(PICK_PROP)
            _log('disc stream %s: not from AllDebrid / TorBox / Premiumize - no Disc Menu' % name)
            return
        pick = {'svc': code, 'file': name, 'ts': int(time.time())}
    pick['link'] = str(path).split('|', 1)[0]
    home.setProperty(PICK_PROP, json.dumps(pick))
    _log('disc stream %s (%s): Disc Menu %s' % (name, pick['svc'], 'by torrent hash' if pick.get('hash')
                                                 else 'finds the torrent by this file'))


def is_disc_part(path):
    """An http .m2ts that is one stream of a disc (00278.m2ts)."""
    p = str(path or '')
    if not p.lower().startswith(('http://', 'https://')):
        return False
    return bool(_PART.search(urllib.parse.urlsplit(p.split('|', 1)[0]).path))


def source_id(pick):
    return 'debrid:%s:%s' % (pick['svc'], pick.get('hash') or 'file:' + str(pick.get('link') or pick.get('file')))


# ───────────────────────── accounts ─────────────────────────

def token(code):
    try:
        import xbmcaddon
        return (xbmcaddon.Addon(AM_ID).getSetting(_TOKEN_KEY[code]) or '').strip()
    except Exception:
        return ''


def _call(url, tok, data=None, timeout=30):
    body = urllib.parse.urlencode(data, doseq=True).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={'Authorization': 'Bearer %s' % tok,
                                                          'User-Agent': 'AB Tools'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def _magnet(hsh):
    return 'magnet:?xt=urn:btih:%s' % hsh


# AllDebrid (api.alldebrid.com v4): upload the magnet (instant when cached),
# its files as a tree (n = name, s = size, l = link, e = entries of a folder),
# each link unlocked when it is read.
class SlotsFull(DebridError):
    """4.9.7: AllDebrid MAGNET_TOO_MANY_ACTIVE - the account already has its
    maximum of unfinished transfers, so the disc's magnet cannot be added."""


def _ad_err(step, res):
    err = (res or {}).get('error') or {}
    text = 'AllDebrid %s: %s %s' % (step, err.get('code', ''), err.get('message', ''))
    if err.get('code') == 'MAGNET_TOO_MANY_ACTIVE':
        m = re.search(r'\((\d+)\)', str(err.get('message') or ''))
        return SlotsFull(text, 32287, m.group(1) if m else '30')
    return DebridError(text)


def _ad_wait_ready(mid, tok, wait=12.0):
    """True once the magnet reaches statusCode 4 (ready) within `wait` s;
    False when it is still queued / downloading or failed."""
    if mid is None:
        return False
    end = time.time() + wait
    mon = xbmc.Monitor()
    while True:
        try:
            res = _call('%s/v4.1/magnet/status?%s' % (AD_API, urllib.parse.urlencode({'agent': AGENT, 'id': mid})), tok)
            m = (res.get('data') or {}).get('magnets') or {}
            m = m[0] if isinstance(m, list) and m else m
            code = int((m or {}).get('statusCode') or 0)
            if code == 4:
                _log('AllDebrid: magnet %s ready after the upload' % mid)
                return True
            if code > 4:
                _log('AllDebrid: magnet %s failed (%s)' % (mid, (m or {}).get('status')), xbmc.LOGWARNING)
                return False
        except Exception as e:
            _log('AllDebrid magnet/status %s: %s' % (mid, e), xbmc.LOGWARNING)
        if time.time() >= end or mon.waitForAbort(1.0):
            _log('AllDebrid: magnet %s not ready after %.0fs - not cached' % (mid, wait), xbmc.LOGWARNING)
            return False


def ad_stalled():
    """4.9.7: the account's unfinished AllDebrid transfers (statusCode 0-3:
    queued / downloading / compressing / uploading), oldest first:
    [{'id', 'name', 'status', 'date'}]."""
    tok = token('AD')
    if not tok:
        return []
    res = _call('%s/v4.1/magnet/status?%s' % (AD_API, urllib.parse.urlencode({'agent': AGENT, 'status': 'active'})), tok)
    if res.get('status') != 'success':
        _log('AllDebrid magnet/status (active): %s' % (res.get('error') or {}), xbmc.LOGWARNING)
        return []
    mags = (res.get('data') or {}).get('magnets') or []
    if isinstance(mags, dict):
        mags = list(mags.values()) if 'id' not in mags else [mags]
    out = [{'id': m.get('id'), 'name': str(m.get('filename') or m.get('hash') or ''),
            'status': str(m.get('status') or ''), 'date': int(m.get('uploadDate') or 0)}
           for m in mags if m.get('id') is not None and int(m.get('statusCode') or 0) < 4]
    out.sort(key=lambda m: m['date'])
    return out


def ad_delete(ids):
    """4.9.7: remove these transfers from the AllDebrid account; how many went."""
    tok = token('AD')
    if not tok or not ids:
        return 0
    gone = 0
    for i in range(0, len(ids), 20):
        part = ids[i:i + 20]
        try:
            res = _call('%s/v4/magnet/delete' % AD_API, tok,
                        data={'agent': AGENT, 'ids[]': [str(x) for x in part]})
            if res.get('status') == 'success':
                gone += len(part)
                continue
            _log('AllDebrid magnet/delete (ids[]): %s' % (res.get('error') or {}), xbmc.LOGWARNING)
        except Exception as e:
            _log('AllDebrid magnet/delete (ids[]): %s' % e, xbmc.LOGWARNING)
        for x in part:                      # older API: one id per call
            try:
                res = _call('%s/v4/magnet/delete?%s' % (AD_API, urllib.parse.urlencode({'agent': AGENT, 'id': x})), tok)
                if res.get('status') == 'success':
                    gone += 1
            except Exception as e:
                _log('AllDebrid magnet/delete %s: %s' % (x, e), xbmc.LOGWARNING)
    _log('AllDebrid: %d unfinished transfer(s) removed' % gone)
    return gone


def _ad_find(hsh, tok):
    """The magnet already in the account (the source add-on added it to play the
    film), ready (statusCode 4): its id, else None."""
    res = _call('%s/v4.1/magnet/status?%s' % (AD_API, urllib.parse.urlencode({'agent': AGENT})), tok)
    if res.get('status') != 'success':
        _log('AllDebrid magnet/status: %s' % (res.get('error') or {}), xbmc.LOGWARNING)
        return None
    mags = (res.get('data') or {}).get('magnets') or []
    if isinstance(mags, dict):
        mags = list(mags.values()) if 'id' not in mags else [mags]
    for m in mags:
        if str(m.get('hash') or '').lower() == hsh and int(m.get('statusCode') or 0) == 4:
            return m.get('id')
    return None


def _ad_files(hsh, tok):
    mid = None
    try:
        mid = _ad_find(hsh, tok)
    except Exception as e:
        _log('AllDebrid magnet/status: %s' % e, xbmc.LOGWARNING)
    if mid is None:
        q = urllib.parse.urlencode({'agent': AGENT, 'magnets[]': _magnet(hsh)})
        up = _call('%s/v4/magnet/upload?%s' % (AD_API, q), tok)
        if up.get('status') != 'success':
            raise _ad_err('upload', up)
        mag = ((up.get('data') or {}).get('magnets') or [{}])[0]
        if mag.get('error'):
            raise _ad_err('upload', mag)
        mid = mag.get('id')
        if not mag.get('ready', True):
            # 4.9.8: AllDebrid often answers ready=false even for a cached
            # torrent and finishes it a moment later - wait for statusCode 4
            # before calling it uncached; an uncached one is removed again so
            # it does not take one of the account's 30 active slots.
            if not _ad_wait_ready(mid, tok):
                ad_delete([mid])
                raise DebridError('AllDebrid: the torrent is not cached', 32292, '')
        _log('AllDebrid: magnet uploaded (id %s)' % mid)
    else:
        _log('AllDebrid: magnet already in the account (id %s)' % mid)
    tree = []
    try:
        res = _call('%s/v4/magnet/files?%s' % (AD_API, urllib.parse.urlencode({'agent': AGENT, 'id[]': mid})), tok)
        if res.get('status') != 'success':
            raise _ad_err('files', res)
        first = (((res.get('data') or {}).get('magnets') or [{}])[0])
        if first.get('error'):
            raise _ad_err('files', first)
        tree = first.get('files') or []
    except Exception as e:
        _log('AllDebrid magnet/files: %s' % e, xbmc.LOGWARNING)
    if not tree:
        res = _call('%s/v4.1/magnet/status?%s' % (AD_API, urllib.parse.urlencode({'agent': AGENT, 'id': mid})), tok)
        if res.get('status') != 'success':
            raise _ad_err('status', res)
        mags = (res.get('data') or {}).get('magnets') or {}
        mags = mags[0] if isinstance(mags, list) and mags else mags
        tree = mags.get('files') or []
    out = []

    def walk(nodes, prefix):
        for n in nodes or []:
            name = str(n.get('n') or '')
            if 'e' in n:
                walk(n.get('e'), prefix + name + '/')
            elif n.get('l'):
                out.append({'path': prefix + name, 'size': int(n.get('s') or 0), 'ref': n['l']})

    walk(tree, '')
    return out


def _ad_resolve(ref, tok):
    q = urllib.parse.urlencode({'agent': AGENT, 'link': ref})
    res = _call('%s/v4/link/unlock?%s' % (AD_API, q), tok)
    link = (res.get('data') or {}).get('link')
    if res.get('status') != 'success' or not link:
        raise DebridError('AllDebrid unlock: %s' % (res.get('error') or {}).get('message', 'no link'))
    return link


# TorBox (api.torbox.app v1): the torrent in the account (added when it is
# not there yet), its files with ids, a download link per file.
def _tb_files(hsh, tok):
    def find():
        res = _call('%s/torrents/mylist?bypass_cache=true' % TB_API, tok)
        for t in res.get('data') or []:
            if str(t.get('hash') or '').lower() == hsh:
                return t
        return None

    tor = find()
    if tor is None:
        res = _call('%s/torrents/createtorrent' % TB_API, tok, data={'magnet': _magnet(hsh)})
        if not res.get('success', True) and not res.get('data'):
            raise DebridError('TorBox: %s' % (res.get('detail') or 'add failed'))
        for _ in range(10):
            tor = find()
            if tor and tor.get('files'):
                break
            time.sleep(1)
    if not tor or not tor.get('files'):
        raise DebridError('TorBox: the torrent has no files yet')
    tid = tor.get('id')
    return [{'path': str(f.get('name') or ''), 'size': int(f.get('size') or 0),
             'ref': '%s:%s' % (tid, f.get('id'))} for f in tor['files']]


def _tb_resolve(ref, tok):
    tid, fid = ref.split(':', 1)
    q = urllib.parse.urlencode({'token': tok, 'torrent_id': tid, 'file_id': fid, 'redirect': 'false'})
    res = _call('%s/torrents/requestdl?%s' % (TB_API, q), tok)
    link = res.get('data')
    if not link:
        raise DebridError('TorBox requestdl: %s' % (res.get('detail') or 'no link'))
    return link


# Premiumize: directdl gives every file of a cached torrent with its link.
def _pm_files(hsh, tok):
    res = _call('%s/transfer/directdl' % PM_API, tok, data={'src': _magnet(hsh)})
    if res.get('status') != 'success':
        raise DebridError('Premiumize: %s' % (res.get('message') or 'not cached'))
    return [{'path': str(c.get('path') or ''), 'size': int(c.get('size') or 0), 'ref': c.get('link'),
             'link': c.get('link')} for c in res.get('content') or [] if c.get('link')]


def _size_of(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Kodi', 'Range': 'bytes=0-0'})
        with urllib.request.urlopen(req, timeout=20) as r:
            total = str(r.headers.get('Content-Range') or '').rsplit('/', 1)[-1]
            return int(total) if total.isdigit() else int(r.headers.get('Content-Length') or 0)
    except Exception as e:
        _log('size of the playing file: %s' % e, xbmc.LOGWARNING)
        return 0


def _ad_hash_by_file(name, size, tok):
    res = _call('%s/v4.1/magnet/status?%s' % (AD_API, urllib.parse.urlencode({'agent': AGENT})), tok)
    mags = (res.get('data') or {}).get('magnets') or []
    if isinstance(mags, dict):
        mags = list(mags.values()) if 'id' not in mags else [mags]
    ready = [m for m in mags if int(m.get('statusCode') or 0) == 4]
    ready.sort(key=lambda m: -int(m.get('completionDate') or m.get('uploadDate') or 0))
    ready = ready[:40]
    if not ready:
        return ''
    q = [('agent', AGENT)] + [('id[]', m.get('id')) for m in ready]
    res = _call('%s/v4/magnet/files?%s' % (AD_API, urllib.parse.urlencode(q)), tok)
    by_id = {str(m.get('id')): m.get('files') or [] for m in (res.get('data') or {}).get('magnets') or []}

    def has(nodes, depth=0):
        found_name = found_index = False
        for n in nodes or []:
            if 'e' in n:
                a, b = has(n.get('e'), depth + 1)
                found_name, found_index = found_name or a, found_index or b
            else:
                nm = str(n.get('n') or '')
                if nm == name and (not size or int(n.get('s') or 0) == size):
                    found_name = True
                if nm.lower() == 'index.bdmv':
                    found_index = True
        return found_name, found_index

    for m in ready:
        a, b = has(by_id.get(str(m.get('id'))))
        if a and b:
            return str(m.get('hash') or '').lower()
    return ''


def _tb_hash_by_file(name, size, tok):
    res = _call('%s/torrents/mylist?bypass_cache=true' % TB_API, tok)
    for t in res.get('data') or []:
        files = t.get('files') or []
        names = [str(f.get('name') or '') for f in files]
        hit = any(n.rsplit('/', 1)[-1] == name and (not size or int(f.get('size') or 0) == size)
                  for n, f in zip(names, files))
        if hit and any(n.lower().endswith('bdmv/index.bdmv') for n in names):
            return str(t.get('hash') or '').lower()
    return ''


_BY_FILE = {'AD': _ad_hash_by_file, 'TB': _tb_hash_by_file}
_FILES = {'AD': _ad_files, 'TB': _tb_files, 'PM': _pm_files}
_RESOLVE = {'AD': _ad_resolve, 'TB': _tb_resolve, 'PM': lambda ref, tok: ref}

_links = {}
_links_lock = threading.Lock()


def resolve(code, ref):
    """The playable link of one file (kept 3 h, per Kodi session)."""
    with _links_lock:
        hit = _links.get((code, ref))
        if hit and time.time() - hit[1] < _LINK_KEEP:
            return hit[0]
    tok = token(code)
    if not tok:
        raise DebridError('no %s account in Account Manager' % SERVICES.get(code, code), 32273,
                          SERVICES.get(code, code))
    link = _RESOLVE[code](ref, tok)
    with _links_lock:
        _links[(code, ref)] = (link, time.time())
    return link


# ───────────────────────── the disc ─────────────────────────

def _disc_root(files, playing):
    """The folder holding BDMV/ of the disc the playing .m2ts belongs to."""
    base = urllib.parse.unquote(urllib.parse.urlsplit(str(playing).split('|', 1)[0]).path).rsplit('/', 1)[-1]
    roots = {}
    for f in files:
        low = f['path'].replace('\\', '/').lower()
        at = low.find('bdmv/index.bdmv')
        if at >= 0 and (at == 0 or low[at - 1] == '/'):
            roots[f['path'][:at]] = 0
    if not roots:
        return None
    for root in roots:
        for f in files:
            p = f['path']
            if p.startswith(root) and p[len(root):].lower() == ('bdmv/stream/%s' % base).lower():
                roots[root] += 1 + f['size']
    return max(roots, key=lambda r: roots[r])


def open_disc(pick, playing):
    """disc_stream's {'key', 'base', 'java', 'main', 'link'} for the disc of
    the picked torrent, or raises DebridError with what went wrong."""
    from resources.lib import disc_stream
    code = pick.get('svc')
    if code not in _FILES:
        raise DebridError('unsupported service', 32275, '')
    tok = token(code)
    if not tok:
        raise DebridError('no %s account in Account Manager' % SERVICES[code], 32273, SERVICES[code])
    number = disc_stream.port()
    if not number:
        raise DebridError('the disc server is not running')
    started = time.time()
    hsh = pick.get('hash') or ''
    if not hsh:
        if code not in _BY_FILE:
            raise DebridError('%s: pick the release in Search All for its disc menu' % SERVICES[code], 32276, '')
        size = _size_of(pick.get('link') or playing)
        hsh = _BY_FILE[code](pick.get('file') or _base(playing), size, tok)
        if not hsh:
            raise DebridError('%s: no torrent with %s and a BDMV folder in the account'
                              % (SERVICES[code], pick.get('file')), 32274, '')
        _log('%s: torrent found by %s (%d bytes): %s' % (SERVICES[code], pick.get('file'), size, hsh[:8]))
    files = _FILES[code](hsh, tok)
    root = _disc_root(files, playing)
    if root is None:
        raise DebridError('not a whole disc (no BDMV/index.bdmv in the torrent)', 32274, '')
    tree = {}
    for f in files:
        p = f['path'].replace('\\', '/')
        if not p.startswith(root):
            continue
        rel = p[len(root):]
        if not rel.lower().startswith(('bdmv/', 'certificate/')):
            continue
        parts = rel.split('/')
        for i in range(1, len(parts)):
            tree.setdefault('/'.join(parts[:i]) + '/', {'dir': True})
        entry = {'size': f['size'], 'ref': f['ref']}
        if f.get('link'):
            entry['url'] = f['link']
        tree[rel] = entry

    # the small files Kodi reads first, resolved together
    pre = [k for k, v in tree.items() if not v.get('dir') and _PRE.match(k)]
    lock = threading.Lock()

    def work():
        while True:
            with lock:
                if not pre:
                    return
                rel = pre.pop()
            try:
                tree[rel]['url'] = resolve(code, tree[rel]['ref'])
            except Exception as e:
                _log('%s: %s' % (rel, e), xbmc.LOGWARNING)

    threads = [threading.Thread(target=work, daemon=True) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(90)

    def small(rel):
        entry = next((v for k, v in tree.items() if k.lower() == rel.lower()), None)
        if not entry or not entry.get('url'):
            return b''
        with urllib.request.urlopen(urllib.request.Request(
                entry['url'], headers={'User-Agent': 'Kodi', 'Range': 'bytes=0-1048575'}), timeout=30) as r:
            return r.read(1 << 20)

    try:
        java = disc_stream.has_java(small('BDMV/index.bdmv'))
    except Exception:
        java = True
    names = [k.rsplit('/', 1)[-1] for k in tree if k.lower().startswith('bdmv/playlist/') and not tree[k].get('dir')]
    main, seconds = disc_stream.main_playlist(names, lambda n: small('BDMV/PLAYLIST/' + n))
    sid = source_id(dict(pick, hash=hsh))
    key = disc_stream.remember_debrid(sid, code, tree, java, main)
    _log('%s disc: %d files in %.1fs, %s menus, main %s (%.0f min)'
         % (SERVICES[code], len(tree), time.time() - started, 'Java' if java else 'HDMV',
            main or '?', seconds / 60.0))
    return disc_stream.disc_info(key)
