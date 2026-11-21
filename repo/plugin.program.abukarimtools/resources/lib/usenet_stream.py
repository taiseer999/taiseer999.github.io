# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""usenet_stream.py - ABUKARIM TOOLS (4.11.0)

Direct Usenet streaming for AB Search All: an NZB is played straight from
the user's own NNTP provider(s) - no debrid, no NzbDAV / AltMount, no
download first.

Where the NZBs come from
  * Newznab indexers set in Mods > "Search All: Usenet" (NZBGeek, NZBFinder,
    DrunkenSlug ..., or a Prowlarr / NZBHydra Newznab endpoint): searched by
    IMDb / TVDb id (title + SxxEyy as a fallback) next to the add-ons, rows
    under the "Usenet" source.
  * AIOStreams: Stremio "nzbUrl" streams (Newznab / NZBHydra / Prowlarr
    built-ins with no streaming service behind them). They are kept in the
    AIOStreams rows and, when picked, played here instead of handing them to
    plugin.video.aiostreams. Their own "servers" (nntps://user:pass@host:563/8)
    are used when the stream carries them, the providers below otherwise.

How it plays (the server half runs in service.py, one per Kodi session)
  1. Search All downloads the NZB into addon_data and asks the local server
     (127.0.0.1, port in Home property abk.nzb.port) to open it.
  2. The server reads the NZB, picks the video (the largest one, the SxxEyy
     one in a season pack), fetches its first article(s) over NNTP and maps
     the file: a plain .mkv/.mp4 post, or a STORED (uncompressed, -m0) RAR
     set - RAR4 and RAR5, the usual scene packing - mapped volume by volume
     so the video inside is read without unpacking. Compressed, encrypted
     or 7z releases are refused with a clear message (and Search All shows
     the results again).
  3. Kodi plays http://127.0.0.1:<port>/abknzb/<key>/<name>. Every ranged
     read becomes the yEnc articles that cover it, fetched over a pool of
     NNTP connections (failover to the next provider on 430 "no such
     article") with read-ahead and a small memory cache, so seeking works.

NNTP and yEnc are done here: Python 3.13+ dropped nntplib, and yEnc is
decoded with bytes.translate (C speed) - fast enough for 4K remuxes on
an S928X.
"""
import hashlib
import json
import os
import re
import socket
import ssl
import threading
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict
from urllib.parse import quote, unquote, urlencode, urlsplit, parse_qs

try:
    import xbmc
    import xbmcgui
    import xbmcvfs
    _IN_KODI = True
except ImportError:                       # 4.11.6: the NZB server as its own process (_serve_main)
    import sys as _sys
    import types as _types
    _IN_KODI = False
    xbmc = _types.SimpleNamespace(LOGDEBUG=0, LOGINFO=1, LOGWARNING=2, LOGERROR=3)

    def _child_log(msg, level=1):
        if level < 1:
            return
        try:
            _sys.stdout.write('LOG %d %s\n' % (level, msg))
            _sys.stdout.flush()
        except Exception:
            pass                          # Kodi gone - the parent check ends this process
    xbmc.log = _child_log
    xbmcgui = None
    xbmcvfs = _types.SimpleNamespace(translatePath=lambda p: p)

ADDON_ID = 'plugin.program.abukarimtools'
_DIR = (xbmcvfs.translatePath('special://profile/addon_data/%s/' % ADDON_ID) if _IN_KODI
        else os.environ.get('ABK_DATA', '.'))
CONFIG = os.path.join(_DIR, 'usenet.json')
NZB_DIR = os.path.join(_DIR, 'nzb')
HOST = '127.0.0.1'
PATH_MARK = 'abknzb'
PORT_PROP = 'abk.nzb.port'
BUSY_PROP = 'abk.disc.busy'           # Search All waits while this is set (ab_search._pick_busy)
NZB_KEEP = 3 * 24 * 3600
SESSION_IDLE = 4 * 3600
UA = 'AB-Tools-Usenet/4.11 (Kodi)'
VIDEO_EXT = ('.mkv', '.mp4', '.m4v', '.avi', '.ts', '.m2ts', '.mts', '.mov', '.wmv', '.webm', '.mpg', '.mpeg',
             '.iso', '.vob', '.divx', '.flv')
_CTYPE = {'.mkv': 'video/x-matroska', '.mp4': 'video/mp4', '.m4v': 'video/mp4', '.avi': 'video/x-msvideo',
          '.ts': 'video/mp2t', '.m2ts': 'video/mp2t', '.mts': 'video/mp2t', '.mov': 'video/quicktime',
          '.webm': 'video/webm', '.iso': 'application/octet-stream'}
_JUNK = re.compile(r'(?<![a-z])(sample|trailer|teaser|featurette|extras?|proof)(?![a-z])', re.I)
_RAR_NAME = re.compile(r'^(.*?)(?:\.part0*(\d+)\.rar|\.rar|\.r(\d{2,3})|\.(\d{3}))$', re.I)
_SUBJ_NAME = re.compile(r'"([^"]+)"')
_SUBJ_YENC = re.compile(r'([^\s"\[\]()]+\.[a-z0-9]{2,4})\s*(?:\(\d+/\d+\)|yEnc)', re.I)
_SUBJ_COUNT = re.compile(r'[\[(](\d+)\s*/\s*(\d+)[\])]')
_NS = '{http://www.newzbin.com/DTD/2003/nzb}'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Usenet] %s' % msg, level)


def _home():
    return xbmcgui.Window(10000)


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
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def config():
    data = _read(CONFIG, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault('providers', [])
    data.setdefault('indexers', [])
    data.setdefault('cache_mb', 128)
    return data


def save_config(data):
    _write(CONFIG, data)


def providers():
    out = []
    for p in config().get('providers') or []:
        if isinstance(p, dict) and p.get('host'):
            out.append(_norm_provider(p))
    return out


def _norm_provider(p):
    ssl_on = p.get('ssl', True) not in (False, 'false', 0, '0')
    try:
        port = int(p.get('port') or (563 if ssl_on else 119))
    except (TypeError, ValueError):
        port = 563 if ssl_on else 119
    try:
        conns = max(1, min(50, int(p.get('conns') or 8)))
    except (TypeError, ValueError):
        conns = 8
    return {'name': str(p.get('name') or p.get('host')), 'host': str(p['host']).strip(), 'port': port,
            'ssl': ssl_on, 'user': str(p.get('user') or ''), 'pass': str(p.get('pass') or ''), 'conns': conns,
            'insecure': bool(p.get('insecure'))}


def indexers():
    out = []
    for i in config().get('indexers') or []:
        if isinstance(i, dict) and i.get('url'):
            out.append({'name': str(i.get('name') or urlsplit(i['url']).hostname or 'Newznab'),
                        'url': str(i['url']).strip(), 'key': str(i.get('key') or '').strip()})
    return out


def configured():
    """Search All lists the Usenet source: a provider AND an indexer."""
    return bool(providers()) and bool(indexers())


def can_play():
    return bool(providers())


def parse_server_url(url):
    """Stremio 'servers' entry nntps://user:pass@host:563/8 -> provider dict."""
    try:
        u = urlsplit(str(url))
    except Exception:
        return None
    if u.scheme not in ('nntp', 'nntps', 'snews', 'news') or not u.hostname:
        return None
    sec = u.scheme in ('nntps', 'snews')
    conns = re.sub(r'\D', '', u.path or '') or 8
    return _norm_provider({'name': u.hostname, 'host': u.hostname, 'port': u.port or (563 if sec else 119),
                           'ssl': sec, 'user': unquote(u.username or ''), 'pass': unquote(u.password or ''),
                           'conns': conns})


# ───────────────────────── NNTP ─────────────────────────

class NNTPError(Exception):
    pass


class Missing(NNTPError):
    """430 / 423: the article is not on this server."""


class _Conn(object):
    def __init__(self, prov, timeout=20):
        self.prov = prov
        raw = socket.create_connection((prov['host'], prov['port']), timeout=timeout)
        if prov['ssl']:
            ctx = ssl.create_default_context()
            if prov.get('insecure'):
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            raw = ctx.wrap_socket(raw, server_hostname=prov['host'])
        self.sock = raw
        self.buf = bytearray()
        self.used = time.time()
        code, line = self._status()
        if code not in (200, 201):
            self.close()
            raise NNTPError('greeting %s' % line)
        if prov.get('user'):
            code, line = self._cmd('AUTHINFO USER %s' % prov['user'])
            if code == 381:
                code, line = self._cmd('AUTHINFO PASS %s' % prov['pass'])
            if code not in (281, 250):
                self.close()
                raise NNTPError('login refused: %s' % line)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

    def _fill(self):
        chunk = self.sock.recv(262144)
        if not chunk:
            raise NNTPError('connection closed')
        self.buf += chunk

    def _line(self):
        while True:
            i = self.buf.find(b'\r\n')
            if i >= 0:
                line = bytes(self.buf[:i])
                del self.buf[:i + 2]
                return line.decode('utf-8', 'replace')
            self._fill()

    def _status(self):
        line = self._line()
        try:
            return int(line[:3]), line
        except ValueError:
            raise NNTPError('bad answer %r' % line[:80])

    def _cmd(self, text):
        self.sock.sendall(text.encode('utf-8') + b'\r\n')
        return self._status()

    def _multiline(self):
        if self.buf.startswith(b'.\r\n'):
            del self.buf[:3]
            return b''
        pos = 0
        while True:
            i = self.buf.find(b'\r\n.\r\n', pos)
            if i >= 0:
                data = bytes(self.buf[:i + 2])
                del self.buf[:i + 5]
                break
            pos = max(0, len(self.buf) - 4)
            self._fill()
        if data.startswith(b'..'):
            data = data[1:]
        return data.replace(b'\r\n..', b'\r\n.')

    def body(self, msgid):
        code, line = self._cmd('BODY <%s>' % msgid.strip('<>'))
        if code == 222:
            self.used = time.time()
            return self._multiline()
        if code in (423, 430):
            raise Missing(msgid)
        raise NNTPError('BODY: %s' % line)

    def stat(self, msgid):
        code, line = self._cmd('STAT <%s>' % msgid.strip('<>'))
        if code == 223:
            return True
        if code in (423, 430):
            return False
        raise NNTPError('STAT: %s' % line)


class _ProvPool(object):
    def __init__(self, prov):
        self.prov = prov
        self.sem = threading.BoundedSemaphore(prov['conns'])
        self.idle = []
        self.lock = threading.Lock()
        self.dead_until = 0.0

    def _get(self):
        with self.lock:
            while self.idle:
                c = self.idle.pop()
                if time.time() - c.used < 50:
                    return c
                c.close()                                   # servers drop idle links after ~60 s
        return _Conn(self.prov)

    def _put(self, c):
        with self.lock:
            self.idle.append(c)

    def run(self, fn, timeout=60):
        if not self.sem.acquire(timeout=timeout):
            raise NNTPError('%s: no free connection' % self.prov['name'])
        try:
            for attempt in (0, 1):
                c = None
                try:
                    c = self._get()
                    out = fn(c)
                    self._put(c)
                    return out
                except Missing:
                    if c:
                        self._put(c)
                    raise
                except (OSError, NNTPError) as e:
                    if c:
                        c.close()
                    if attempt:
                        raise NNTPError('%s: %s' % (self.prov['name'], e))
        finally:
            self.sem.release()

    def close(self):
        with self.lock:
            for c in self.idle:
                c.close()
            self.idle = []


class Pool(object):
    """Providers in priority order; an article missing on one is asked of the next."""

    def __init__(self, provs):
        self.pools = [_ProvPool(p) for p in provs]
        self.size = sum(p['conns'] for p in provs) or 1

    def _each(self, fn):
        last = None
        missing = False
        for pp in self.pools:
            if pp.dead_until > time.time():
                continue
            try:
                return pp.run(fn)
            except Missing:
                missing = True
            except NNTPError as e:
                last = e
                if 'login' in str(e) or 'greeting' in str(e):
                    pp.dead_until = time.time() + 120
        if missing:
            raise Missing('article')
        raise last or NNTPError('no provider')

    def body(self, msgid):
        return self._each(lambda c: c.body(msgid))

    def stat(self, msgid):
        """True when any provider has the article."""
        for pp in self.pools:
            if pp.dead_until > time.time():
                continue
            try:
                if pp.run(lambda c: c.stat(msgid)):
                    return True
            except NNTPError:
                pass
        return False

    def close(self):
        for pp in self.pools:
            pp.close()


def test_provider(prov):
    """'' when the login works, else the reason."""
    try:
        c = _Conn(_norm_provider(prov), timeout=15)
        c.close()
        return ''
    except Exception as e:
        return str(e) or e.__class__.__name__


# ───────────────────────── yEnc ─────────────────────────

_YTABLE = bytes((i - 42) & 255 for i in range(256))
_YKEY = re.compile(rb'(\w+)=(\S+)')


def _yfields(line):
    out = {}
    name = None
    i = line.find(b' name=')
    if i >= 0:
        name = line[i + 6:].strip()
        line = line[:i]
    for k, v in _YKEY.findall(line):
        out[k.decode('ascii', 'replace')] = v.decode('ascii', 'replace')
    if name is not None:
        out['name'] = name.decode('utf-8', 'replace')
    return out


def ydecode(body):
    """(info, data) of one article body. info: name, size, begin, end (1-based, incl.)."""
    start = body.find(b'=ybegin ')
    if start < 0:
        raise NNTPError('not yEnc')
    eol = body.find(b'\n', start)
    head = _yfields(body[start + 8:eol].rstrip(b'\r'))
    pos = eol + 1
    if body.startswith(b'=ypart ', pos):
        eol2 = body.find(b'\n', pos)
        head.update(_yfields(body[pos + 7:eol2].rstrip(b'\r')))
        pos = eol2 + 1
    end = body.find(b'\n=yend', pos - 1)
    enc = body[pos:end if end >= 0 else len(body)].translate(None, b'\r\n')
    parts = enc.split(b'=')
    out = [parts[0].translate(_YTABLE)]
    for p in parts[1:]:
        if p:
            out.append(bytes(((p[0] - 106) & 255,)))
            if len(p) > 1:
                out.append(p[1:].translate(_YTABLE))
    data = b''.join(out)
    info = {'name': head.get('name', ''), 'size': int(head.get('size') or len(data))}
    info['begin'] = int(head.get('begin') or 1)
    info['end'] = int(head.get('end') or (info['begin'] + len(data) - 1))
    return info, data


# ───────────────────────── NZB ─────────────────────────

def _subject_name(subject):
    m = _SUBJ_NAME.search(subject)
    if m:
        return m.group(1).strip()
    m = _SUBJ_YENC.search(subject)
    return m.group(1) if m else ''


def parse_nzb(data):
    """{'files': [{'subject', 'name', 'segments': [msgid], 'bytes', 'order', 'count'}], 'password'}"""
    if isinstance(data, bytes):
        data = data.decode('utf-8', 'replace')
    data = re.sub(r'<!DOCTYPE[^>]*>', '', data, count=1)
    root = ET.fromstring(data)
    ns = _NS if root.tag.startswith(_NS) else ''
    password = ''
    for meta in root.iter(ns + 'meta'):
        if (meta.get('type') or '').lower() == 'password' and (meta.text or '').strip():
            password = meta.text.strip()
    files = []
    for n, f in enumerate(root.iter(ns + 'file')):
        subject = f.get('subject') or ''
        segs = []
        for s in f.iter(ns + 'segment'):
            try:
                num = int(s.get('number') or 0)
            except ValueError:
                num = 0
            try:
                size = int(s.get('bytes') or 0)
            except ValueError:
                size = 0
            if (s.text or '').strip():
                segs.append((num, s.text.strip(), size))
        if not segs:
            continue
        segs.sort()
        seen, ids, total = set(), [], 0
        for num, mid, size in segs:
            if num in seen:
                continue
            seen.add(num)
            ids.append(mid)
            total += size
        m = _SUBJ_COUNT.search(subject)
        files.append({'subject': subject, 'name': _subject_name(subject), 'segments': ids, 'bytes': total,
                      'order': int(m.group(1)) if m else n, 'count': int(m.group(2)) if m else 0})
    return {'files': files, 'password': password}


# ───────────────────────── segment cache ─────────────────────────

class Cache(object):
    def __init__(self, pool, limit_bytes):
        self.pool = pool
        self.limit = max(32 << 20, limit_bytes)
        self.data = OrderedDict()
        self.used = 0
        self.errs = {}
        self.busy = {}
        self.lock = threading.Lock()
        self.work = []
        self.cv = threading.Condition(self.lock)
        self.stop = False
        self.workers = []
        for i in range(pool.size):
            t = threading.Thread(target=self._worker, name='abk-nntp-%d' % i, daemon=True)
            t.start()
            self.workers.append(t)

    def _worker(self):
        while True:
            with self.cv:
                while not self.work and not self.stop:
                    self.cv.wait()
                if self.stop:
                    return
                key, msgid = self.work.pop(0)
            try:
                res = ydecode(self.pool.body(msgid))
            except Exception as e:
                res = e
            self._done(key, res)

    def _done(self, key, res):
        with self.cv:
            ev = self.busy.pop(key, None)
            if not isinstance(res, Exception):
                size = len(res[1])
                self.data[key] = res
                self.data.move_to_end(key)
                self.used += size
                while self.used > self.limit and len(self.data) > 1:
                    _k, old = self.data.popitem(last=False)
                    self.used -= len(old[1])
            else:
                self.errs[key] = res
            if ev:
                ev.set()

    def want(self, key, msgid, first=False):
        """Queue a fetch (no wait). first = jump the queue (the read the player waits on)."""
        with self.cv:
            if key in self.data or key in self.busy:
                if first and key in self.busy:
                    for i, (k, _m) in enumerate(self.work):
                        if k == key:
                            self.work.insert(0, self.work.pop(i))
                            break
                return
            self.errs.pop(key, None)
            self.busy[key] = threading.Event()
            if first:
                self.work.insert(0, (key, msgid))
            else:
                self.work.append((key, msgid))
            self.cv.notify()

    def get(self, key, msgid, timeout=90):
        self.want(key, msgid, first=True)
        with self.cv:
            if key in self.data:
                self.data.move_to_end(key)
                return self.data[key]
            ev = self.busy.get(key)
        if ev is not None:
            ev.wait(timeout)
        with self.cv:
            if key in self.data:
                return self.data[key]
            err = self.errs.pop(key, None)
        if isinstance(err, Exception):
            raise err
        raise NNTPError('timeout')

    def drop_queue(self, prefix):
        """Forget queued read-ahead of a closed stream."""
        with self.cv:
            keep = []
            for k, m in self.work:
                if k[0] == prefix:
                    ev = self.busy.pop(k, None)
                    if ev:
                        ev.set()
                else:
                    keep.append((k, m))
            self.work = keep

    def close(self):
        with self.cv:
            self.stop = True
            self.cv.notify_all()
        self.pool.close()


# ───────────────────────── files over articles ─────────────────────────

class YFile(object):
    """One posted file: decoded size + where each article sits in it."""

    def __init__(self, sid, n, segments, cache):
        self.key = (sid, n)
        self.segs = segments
        self.cache = cache
        self.known = {}
        self.size = 0
        self.part = 0
        self.hint = 0              # article size of a sibling volume until this one is read
        self.name = ''

    def seg(self, idx):
        info, data = self.cache.get(self.key + (idx,), self.segs[idx])
        self.known[idx] = (info['begin'] - 1, info['end'])
        return info, data

    def head(self):
        info, data = self.seg(0)
        self.size = info['size'] or len(data)
        self.part = max(1, info['end'] - info['begin'] + 1)
        self.name = info['name']
        return data

    def guess(self, offset):
        return max(0, min(len(self.segs) - 1, offset // (self.part or self.hint or 1)))

    def want(self, idx):
        if 0 <= idx < len(self.segs):
            self.cache.want(self.key + (idx,), self.segs[idx])

    def read(self, offset, length):
        """Up to length bytes at offset (at least one byte unless at the end)."""
        if not self.part:
            self.head()
        if offset >= self.size:
            return b''
        idx = self.guess(offset)
        for _ in range(12):
            try:
                info, data = self.seg(idx)
            except Missing:
                _log('article %d of %s missing on every server - zeros' % (idx, self.name), xbmc.LOGWARNING)
                start = idx * self.part
                end = min(self.size, start + self.part)
                if not (start <= offset < end):
                    return b'\0' * min(length, max(1, self.size - offset))
                return b'\0' * min(length, end - offset)
            b0, e0 = info['begin'] - 1, info['end']
            if b0 <= offset < e0:
                rel = offset - b0
                return data[rel:rel + length]
            step = (offset - b0) // self.part
            idx = max(0, min(len(self.segs) - 1, idx + (step if step else (1 if offset >= e0 else -1))))
        raise NNTPError('offset %d not found in %s' % (offset, self.name))


class Stream(object):
    """The video: one or more (YFile, start, length) chunks back to back."""

    def __init__(self, sid, name, chunks, cache, ahead):
        self.sid = sid
        self.name = name
        self.chunks = chunks
        self.cache = cache
        self.ahead = ahead
        self.used = time.time()
        self.lock = threading.Lock()
        self._index()

    def _index(self):
        hint = next((yf.part for yf, _s, _l in self.chunks if yf.part), 0)
        for yf, _s, _l in self.chunks:
            if not yf.part:
                yf.hint = hint
        self.starts, pos = [], 0
        for _f, _s, ln in self.chunks:
            self.starts.append(pos)
            pos += ln
        self.size = pos

    def _chunk(self, offset):
        lo, hi = 0, len(self.starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def _prefetch(self, offset):
        left = self.ahead
        ci = self._chunk(offset)
        off = offset
        while left > 0 and ci < len(self.chunks):
            yf, cs, ln = self.chunks[ci]
            inner = cs + (off - self.starts[ci])
            idx = yf.guess(inner)
            last = yf.guess(cs + ln - 1)
            while idx <= last and left > 0:
                yf.want(idx)
                idx += 1
                left -= 1
            ci += 1
            if ci < len(self.chunks):
                off = self.starts[ci]

    def read(self, offset, length):
        self.used = time.time()
        if offset >= self.size:
            return b''
        ci = self._chunk(offset)
        yf, cs, ln = self.chunks[ci]
        rel = offset - self.starts[ci]
        n = min(length, ln - rel)
        self._prefetch(offset)
        data = yf.read(cs + rel, n)
        return data


# ───────────────────────── RAR (stored) ─────────────────────────

class NotStreamable(Exception):
    pass


_RAR4 = b'Rar!\x1a\x07\x00'
_RAR5 = b'Rar!\x1a\x07\x01\x00'


def _vint(b, p):
    v = shift = 0
    while True:
        c = b[p]
        p += 1
        v |= (c & 0x7f) << shift
        if not c & 0x80:
            return v, p
        shift += 7


def rar_files(head):
    """[{'name', 'data': offset, 'pack', 'unp', 'store', 'enc', 'before', 'after'}] from a
    volume's first bytes (the headers are at the front of every volume)."""
    out = []
    if head.startswith(_RAR5):
        p = len(_RAR5)
        while p + 7 < len(head):
            p0 = p + 4
            hsize, q = _vint(head, p0)
            hend = q + hsize
            htype, q = _vint(head, q)
            hflags, q = _vint(head, q)
            extra = dsize = 0
            if hflags & 1:
                extra, q = _vint(head, q)
            if hflags & 2:
                dsize, q = _vint(head, q)
            if htype == 4:
                raise NotStreamable('encrypted')
            if htype == 5:                                # end of archive
                break
            if htype == 2:
                fflags, q = _vint(head, q)
                unp, q = _vint(head, q)
                _attr, q = _vint(head, q)
                if fflags & 2:
                    q += 4
                if fflags & 4:
                    q += 4
                comp, q = _vint(head, q)
                _os, q = _vint(head, q)
                nlen, q = _vint(head, q)
                name = head[q:q + nlen].decode('utf-8', 'replace')
                q += nlen
                enc = False
                ex, exend = hend - extra, hend
                while extra and ex < exend:
                    rsize, r = _vint(head, ex)
                    rtype, _r = _vint(head, r)
                    if rtype == 1:
                        enc = True
                    ex = r + rsize
                out.append({'name': name, 'data': hend, 'pack': dsize, 'unp': unp,
                            'store': ((comp >> 7) & 7) == 0, 'enc': enc,
                            'before': bool(hflags & 8), 'after': bool(hflags & 16), 'dir': bool(fflags & 1)})
            p = hend + dsize
            if p > len(head) and htype == 2:
                break
        return out
    if head.startswith(_RAR4):
        p = len(_RAR4)
        import struct
        while p + 7 <= len(head):
            _crc, htype, flags, hsize = struct.unpack_from('<HBHH', head, p)
            if hsize < 7:
                break
            add = 0
            if htype == 0x73 and flags & 0x0080:
                raise NotStreamable('encrypted')
            if htype == 0x74:
                pack, unp = struct.unpack_from('<II', head, p + 7)
                method = head[p + 25]
                nlen = struct.unpack_from('<H', head, p + 26)[0]
                q = p + 32
                if flags & 0x100:
                    hp, hu = struct.unpack_from('<II', head, q)
                    pack |= hp << 32
                    unp |= hu << 32
                    q += 8
                raw = head[q:q + nlen]
                name = raw.split(b'\0')[0].decode('utf-8' if flags & 0x200 else 'latin-1', 'replace')
                out.append({'name': name.replace('\\', '/'), 'data': p + hsize, 'pack': pack, 'unp': unp,
                            'store': method == 0x30, 'enc': bool(flags & 0x04),
                            'before': bool(flags & 0x01), 'after': bool(flags & 0x02),
                            'dir': (flags & 0xe0) == 0xe0})
                add = pack
            elif flags & 0x8000:
                add = struct.unpack_from('<I', head, p + 7)[0]
            if htype == 0x7b:
                break
            p += hsize + add
            if p > len(head) and htype == 0x74:
                break
        return out
    raise NotStreamable('not a RAR volume')


# ───────────────────────── opening an NZB ─────────────────────────

def _ep_rx(season, episode):
    if season is None or episode is None:
        return None
    return re.compile(r'(?<![a-z0-9])(?:s0*%d[ ._-]?e0*%d|0*%dx0*%d|season[ ._-]?0*%d[ ._-]?episode[ ._-]?0*%d)'
                      r'(?![0-9])' % (season, episode, season, episode, season, episode), re.I)


def _ext(name):
    return os.path.splitext(name.lower())[1]


def _rar_part(name):
    """(set name, volume number) of a RAR volume name, None otherwise
    (name.001 of a split .mkv / .7z is not RAR: see _split_part)."""
    if _split_part(name):
        return None
    m = _RAR_NAME.match(name)
    if not m:
        return None
    base, part, rnum, num = m.groups()
    low = name.lower()
    if part:
        return base.lower(), int(part)
    if low.endswith('.rar'):
        return base.lower(), 0
    if rnum:
        return base.lower(), int(rnum) + 1
    return base.lower(), int(num)


def _split_part(name):
    """(video name, part) of a plain split file movie.mkv.001, None otherwise."""
    m = re.match(r'^(.*)\.(\d{3})$', name)
    if m and _ext(m.group(1)) in VIDEO_EXT:
        return m.group(1), int(m.group(2))
    return None


class Server(object):
    """All open releases of the session (service.py thread)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.streams = {}
        self.caches = {}
        self.srv = None

    # ---- opening ----
    def _cache_for(self, provs):
        sig = json.dumps([(p['host'], p['port'], p['user']) for p in provs])
        with self.lock:
            c = self.caches.get(sig)
            if c is None:
                mb = int(config().get('cache_mb') or 128)
                c = Cache(Pool(provs), mb << 20)
                self.caches[sig] = c
            return c

    def open(self, nzb_path, season=None, episode=None, servers=None):
        key = hashlib.sha1(('%s|%s|%s' % (nzb_path, season, episode)).encode('utf-8')).hexdigest()[:12]
        with self.lock:
            st = self.streams.get(key)
        if st:
            st.used = time.time()
            return key, st
        with open(nzb_path, 'rb') as f:
            nzb = parse_nzb(f.read())
        provs = [p for p in (parse_server_url(s) for s in (servers or [])) if p] or providers()
        if not provs:
            raise NotStreamable('no provider')
        cache = self._cache_for(provs)
        files = [f for f in nzb['files'] if not f['name'].lower().endswith(('.par2', '.nfo', '.sfv', '.nzb', '.jpg',
                                                                              '.png', '.txt', '.srr', '.srs'))]
        if not files:
            raise NotStreamable('empty NZB')
        stream = self._build(key, files, cache, _ep_rx(season, episode), bool(nzb['password']))
        with self.lock:
            self.streams[key] = stream
        self._expire()
        return key, stream

    def _build(self, key, files, cache, ep, password):
        ahead = max(8, min(48, cache.pool.size * 3))
        mk = lambda n, f: YFile(key, n, f['segments'], cache)

        def pick(cands, namef):
            good = [c for c in cands if not _JUNK.search(namef(c))]
            cands = good or cands
            if ep:
                hit = [c for c in cands if ep.search(namef(c))]
                if hit:
                    cands = hit
            return cands

        if any(_ext(f['name']) == '.7z' or re.search(r'\.7z\.\d{3}$', f['name'], re.I) for f in files) \
                and not any(_ext(f['name']) in VIDEO_EXT or _rar_part(f['name']) for f in files):
            raise NotStreamable('compressed')
        splits = {}
        for f in files:
            sp = _split_part(f['name'])
            if sp:
                splits.setdefault(sp[0], []).append((sp[1], f))
        if splits:
            cand = pick(list(splits.items()), lambda kv: kv[0])
            name, parts = max(cand, key=lambda kv: sum(f['bytes'] for _n, f in kv[1]))
            parts.sort(key=lambda t: t[0])
            yfs = [YFile(key, files.index(f), f['segments'], cache) for _n, f in parts]
            for yf in yfs:
                yf.want(0)
            chunks = []
            for yf in yfs:
                yf.head()
                chunks.append((yf, 0, yf.size))
            _log('split post %s: %d parts' % (name, len(yfs)))
            return Stream(key, os.path.basename(name), chunks, cache, ahead)
        videos = [f for f in files if _ext(f['name']) in VIDEO_EXT]
        sets = {}
        for f in files:
            rp = _rar_part(f['name'])
            if rp:
                sets.setdefault(rp[0], []).append((rp[1], f))
        big = max(f['bytes'] for f in files)
        if videos and max(v['bytes'] for v in videos) >= big * 0.5:
            v = max(pick(videos, lambda f: f['name']), key=lambda f: f['bytes'])
            return self._plain(key, v, files.index(v), cache, ahead)
        if sets:
            cand = pick(list(sets.items()), lambda kv: kv[0])
            name, vols = max(cand, key=lambda kv: sum(f['bytes'] for _n, f in kv[1]))
            vols.sort(key=lambda t: t[0])
            return self._rar(key, [f for _n, f in vols], files, cache, ahead, ep, password)
        # obfuscated: ask the articles themselves (yEnc name + magic)
        _log('NZB names hidden - probing the first article of each large file')
        probe = sorted([f for f in files if f['bytes'] >= big * 0.02], key=lambda f: -f['bytes'])[:120]
        yfs = []
        for f in probe:
            yf = mk(files.index(f), f)
            yf.want(0)
            yfs.append((f, yf))
        found, rars = [], []
        for f, yf in yfs:
            try:
                head = yf.head()
            except Exception as e:
                _log('probe %s: %s' % (f['subject'][:60], e), xbmc.LOGDEBUG)
                continue
            nm = yf.name or f['name']
            if head.startswith(b'\x1aE\xdf\xa3') or head[4:8] == b'ftyp' or _ext(nm) in VIDEO_EXT:
                found.append((f, yf, nm))
            elif head.startswith(b'Rar!'):
                rars.append((f, yf, nm, head))
        if found and (not rars or max(yf.size for _f, yf, _n in found) >= 0.5 * sum(yf.size for _f, yf, _n, _h in rars)):
            f, yf, nm = max(pick(found, lambda t: t[2]), key=lambda t: t[1].size)
            if _ext(nm) not in VIDEO_EXT:
                nm += '.mkv' if yf.head().startswith(b'\x1aE\xdf\xa3') else '.mp4'
            return Stream(key, os.path.basename(nm), [(yf, 0, yf.size)], cache, ahead)
        if rars:
            def vol_key(t):
                rp = _rar_part(t[2])
                return (rp[0], rp[1]) if rp else ('', t[0]['order'])
            rars.sort(key=vol_key)
            groups = {}
            for t in rars:
                rp = _rar_part(t[2])
                groups.setdefault(rp[0] if rp else '', []).append(t)
            grp = max(groups.values(), key=lambda g: sum(t[1].size for t in g))
            return self._rar_volumes(key, [(t[1], t[3]) for t in grp], cache, ahead, ep, password, eager=True)
        raise NotStreamable('no video found')

    def _plain(self, key, f, n, cache, ahead):
        yf = YFile(key, n, f['segments'], cache)
        for i in range(1, min(len(f['segments']), ahead)):
            yf.want(i)
        yf.head()
        name = yf.name if _ext(yf.name) in VIDEO_EXT else f['name']
        _log('plain post %s: %.2f GB, %d articles' % (name, yf.size / 1073741824.0, len(f['segments'])))
        return Stream(key, os.path.basename(name), [(yf, 0, yf.size)], cache, ahead)

    def _rar(self, key, vols, files, cache, ahead, ep, password):
        yfs = [YFile(key, files.index(f), f['segments'], cache) for f in vols]
        need = [0, 1, len(yfs) - 1] if len(yfs) > 2 else list(range(len(yfs)))
        for i in need:
            yfs[i].want(0)
        heads = {}
        for i in need:
            heads[i] = yfs[i].head()
        return self._rar_volumes(key, [(yfs[i], heads.get(i)) for i in range(len(yfs))], cache, ahead, ep,
                                 password)

    def _rar_volumes(self, key, vols, cache, ahead, ep, password, eager=False):
        first = rar_files(vols[0][1])
        vids = [e for e in first if not e['dir'] and _ext(e['name']) in VIDEO_EXT] or \
               [e for e in first if not e['dir']]
        if not vids:
            raise NotStreamable('no video in the RAR set')
        good = [e for e in vids if not _JUNK.search(e['name'])] or vids
        if ep:
            good = [e for e in good if ep.search(e['name'])] or good
        target = max(good, key=lambda e: e['unp'])
        if target['enc'] or password:
            raise NotStreamable('encrypted')
        if not target['store']:
            raise NotStreamable('compressed')
        tname = target['name']

        def entry(entries):
            for e in entries:
                if e['name'] == tname:
                    return e
            return None

        def chunks_from(entries_by_vol):
            out = []
            for (yf, _h), ents in zip(vols, entries_by_vol):
                e = entry(ents or [])
                if e and e['pack']:
                    out.append((yf, e['data'], e['pack']))
            return out

        n = len(vols)
        ents = [None] * n
        ents[0] = first
        if not eager and n > 2:
            ents[1] = rar_files(vols[1][1])
            ents[-1] = rar_files(vols[-1][1])
            e1, el = entry(ents[1]), entry(ents[-1])
            if e1 and el and e1['before']:
                guess = target['pack'] + e1['pack'] * (n - 2) + el['pack']
                if guess == target['unp']:
                    for i in range(2, n - 1):
                        ents[i] = [dict(e1)]
                    chunks = chunks_from(ents)
                    _log('stored RAR %s: %d volumes, %.2f GB (middle volumes alike)'
                         % (tname, n, target['unp'] / 1073741824.0))
                    return Stream(key, os.path.basename(tname), chunks, cache, ahead)
            _log('RAR volumes differ - reading every volume header')
        for yf, h in vols:
            if h is None:
                yf.want(0)
        for i, (yf, h) in enumerate(vols):
            if ents[i] is None:
                ents[i] = rar_files(h if h is not None else yf.head())
        chunks = chunks_from(ents)
        total = sum(c[2] for c in chunks)
        if total != target['unp']:
            _log('RAR set short: %d of %d bytes - playing what is there' % (total, target['unp']), xbmc.LOGWARNING)
        _log('stored RAR %s: %d volumes, %.2f GB' % (tname, n, total / 1073741824.0))
        return Stream(key, os.path.basename(tname), chunks, cache, ahead)

    def _expire(self):
        now = time.time()
        with self.lock:
            for k in [k for k, s in self.streams.items() if now - s.used > SESSION_IDLE]:
                st = self.streams.pop(k)
                st.cache.drop_queue(k)

    def check(self, stream, samples=4):
        """True when a few articles across the file are on the server."""
        pool = stream.cache.pool
        picks = []
        for yf, _s, _l in (stream.chunks[:1] + stream.chunks[len(stream.chunks) // 2:][:1] + stream.chunks[-1:]):
            picks += [yf.segs[len(yf.segs) // 2], yf.segs[-1]]
        for mid in picks[:samples * 2]:
            if not pool.stat(mid):
                return False
        return True

    # ---- http ----
    def handler(self):
        from http.server import BaseHTTPRequestHandler
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def do_HEAD(self):
                self._serve(True)

            def do_GET(self):
                self._serve(False)

            def _json(self, code, obj):
                body = json.dumps(obj).encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _open(self, q):
                def one(k):
                    return (q.get(k) or [''])[0]
                try:
                    s, e = one('season'), one('episode')
                    servers = json.loads(one('servers') or '[]')
                    key, st = server.open(one('nzb'), int(s) if s.isdigit() else None,
                                          int(e) if e.isdigit() else None, servers)
                    if one('check') == '1' and not server.check(st):
                        with server.lock:
                            server.streams.pop(key, None)
                        return self._json(200, {'ok': False, 'error': 'incomplete'})
                    path = '/%s/%s/%s' % (PATH_MARK, key, quote(st.name, safe=''))
                    self._json(200, {'ok': True, 'key': key, 'name': st.name, 'size': st.size, 'path': path})
                except NotStreamable as ex:
                    self._json(200, {'ok': False, 'error': str(ex)})
                except Missing:
                    self._json(200, {'ok': False, 'error': 'incomplete'})
                except Exception as ex:
                    _log('open failed: %s' % ex, xbmc.LOGWARNING)
                    self._json(200, {'ok': False, 'error': 'failed', 'detail': str(ex)})

            def _serve(self, head):
                parts = urlsplit(self.path)
                seg = parts.path.strip('/').split('/')
                if seg[:2] == [PATH_MARK, 'open']:
                    return self._open(parse_qs(parts.query))
                if len(seg) < 2 or seg[0] != PATH_MARK:
                    self.send_error(404)
                    return
                with server.lock:
                    st = server.streams.get(seg[1])
                if st is None:
                    self.send_error(404)
                    return
                size = st.size
                start, end = 0, size - 1
                rng = self.headers.get('Range')
                partial = False
                if rng:
                    m = re.match(r'bytes=(\d*)-(\d*)', rng.strip())
                    if m:
                        if m.group(1):
                            start = int(m.group(1))
                            if m.group(2):
                                end = min(size - 1, int(m.group(2)))
                        elif m.group(2):
                            start = max(0, size - int(m.group(2)))
                        partial = True
                if start >= size:
                    self.send_response(416)
                    self.send_header('Content-Range', 'bytes */%d' % size)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                self.send_response(206 if partial else 200)
                self.send_header('Content-Type', _CTYPE.get(_ext(st.name), 'application/octet-stream'))
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Length', str(end - start + 1))
                if partial:
                    self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
                self.end_headers()
                if head:
                    return
                pos = start
                try:
                    while pos <= end:
                        data = st.read(pos, min(end - pos + 1, 4 << 20))
                        if not data:
                            self.close_connection = True
                            break
                        self.wfile.write(data)
                        pos += len(data)
                except (BrokenPipeError, ConnectionResetError, socket.timeout):
                    pass
                except Exception as e:
                    _log('read at %d: %s' % (pos, e), xbmc.LOGWARNING)
                    self.close_connection = True

        return Handler

    def start(self):
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer((HOST, 0), self.handler())
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, name='abk-nzb-server', daemon=True).start()
        self.srv = srv
        return srv.server_address[1]

    def stop(self):
        if self.srv:
            try:
                self.srv.shutdown()
                self.srv.server_close()
            except Exception:
                pass
        for c in self.caches.values():
            c.close()


_server = [None]


# ── 4.11.6: the server runs as its OWN Python process when the box has a
# python3 (CoreELEC / LibreELEC do; macOS with the Command Line Tools or
# Homebrew). Inside Kodi every add-on shares one Python lock (GIL), and Kodi's
# xbmcvfs Stat / File calls keep it while they wait on the network: an add-on
# that Stats the playing 127.0.0.1 URL froze the in-process server for 30 s
# and Kodi stopped the video (kodi.log 2026-11-19 22:28:42-22:29:12,
# "CCurlFile::Stat ... Timeout was reached" x3 after "stream stalled"). Out of
# process the server never waits for Kodi's Python. In-process stays as the
# fallback when no python3 is found.

def _python():
    import shutil
    import sys
    cands = []
    if sys.platform == 'darwin':
        cands += ['/opt/homebrew/bin/python3', '/usr/local/bin/python3',
                  '/Library/Developer/CommandLineTools/usr/bin/python3']   # not /usr/bin: its stub may ask to install Xcode
    else:
        cands += ['/usr/bin/python3', '/usr/local/bin/python3', shutil.which('python3') or '']
    import subprocess
    for c in cands:
        if not c or not os.path.isfile(c) or not os.access(c, os.X_OK):
            continue
        try:
            out = subprocess.run([c, '-I', '-c', 'import ssl, http.server, xml.etree.ElementTree; print(1)'],
                                 capture_output=True, timeout=20)
            if out.returncode == 0 and out.stdout.strip() == b'1':
                return c
        except Exception:
            continue
    return ''


class _External(object):
    """The NZB server process, seen from service.py."""

    def __init__(self, proc):
        self.proc = proc

    def stop(self):
        try:
            self.proc.terminate()
            self.proc.wait(5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


def _start_external():
    import subprocess
    py = _python()
    if not py:
        _log('no python3 on this system - NZB server inside Kodi', xbmc.LOGWARNING)
        return None
    env = dict(os.environ, ABK_DATA=_DIR, PYTHONUNBUFFERED='1')
    proc = subprocess.Popen([py, '-I', os.path.abspath(__file__), '--serve'], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, close_fds=True)
    first = {}

    def reader():
        for raw in proc.stdout:
            line = raw.decode('utf-8', 'replace').rstrip('\n')
            if line.startswith('PORT '):
                first['port'] = int(line[5:])
            elif line.startswith('LOG '):
                try:
                    lvl, msg = line[4:].split(' ', 1)
                    xbmc.log(msg, int(lvl))             # already '[AbukarimTools Usenet] ...'
                except ValueError:
                    xbmc.log('[AbukarimTools Usenet] %s' % line, xbmc.LOGINFO)
            elif line.strip():
                xbmc.log('[AbukarimTools Usenet] server: %s' % line, xbmc.LOGWARNING)
        code = proc.wait()
        if _server[0] is not None and getattr(_server[0], 'proc', None) is proc:
            _log('NZB server process ended (%s) - restarting it inside Kodi' % code, xbmc.LOGWARNING)
            _server[0] = None
            _home().clearProperty(PORT_PROP)
            _start_inside()

    threading.Thread(target=reader, name='abk-nzb-proc', daemon=True).start()
    for _ in range(100):
        if 'port' in first or proc.poll() is not None:
            break
        time.sleep(0.1)
    if 'port' not in first:
        _log('NZB server process did not start (%s)' % py, xbmc.LOGWARNING)
        try:
            proc.kill()
        except Exception:
            pass
        return None
    _server[0] = _External(proc)
    _log('NZB server on %s:%d (own process, %s, pid %d)' % (HOST, first['port'], py, proc.pid))
    return first['port']


def _start_inside():
    s = Server()
    number = s.start()
    _server[0] = s
    _home().setProperty(PORT_PROP, str(number))
    _log('NZB server on %s:%d (inside Kodi)' % (HOST, number))
    return number


def start(monitor=None):
    """service.py: the NZB server for the rest of the session."""
    if _server[0] is not None:
        return True
    _clean_nzbs()
    try:
        number = _start_external()
        if number:
            _home().setProperty(PORT_PROP, str(number))
            return True
    except Exception as e:
        _log('NZB server process failed: %s' % e, xbmc.LOGWARNING)
    try:
        _start_inside()
        return True
    except Exception as e:
        _log('NZB server not started: %s' % e, xbmc.LOGERROR)
        return False


def stop():
    s = _server[0]
    _server[0] = None
    _home().clearProperty(PORT_PROP)
    if s:
        s.stop()


def _clean_nzbs():
    try:
        now = time.time()
        for n in os.listdir(NZB_DIR):
            p = os.path.join(NZB_DIR, n)
            if now - os.path.getmtime(p) > NZB_KEEP:
                os.remove(p)
    except Exception:
        pass


# ───────────────────────── Newznab search (Search All) ─────────────────────────

_NZ_ATTR = '{http://www.newznab.com/DTD/2010/feeds/attributes/}attr'


def _api(url):
    u = url.rstrip('/')
    if not re.search(r'/api$', u):
        u += '/api'
    return u


def _fetch(url, timeout=30, binary=False):
    import gzip
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get('Content-Encoding') == 'gzip' or data[:2] == b'\x1f\x8b':
            data = gzip.decompress(data)
    return data if binary else data.decode('utf-8', 'replace')


def _items(xml_text):
    try:
        root = ET.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
    except ET.ParseError:
        raise ValueError('not Newznab XML')
    if root.tag == 'error':
        raise ValueError(root.get('description') or 'indexer error %s' % root.get('code'))
    out = []
    for it in root.iter('item'):
        attrs = {a.get('name'): a.get('value') for a in it.iter(_NZ_ATTR)}
        enc = it.find('enclosure')
        link = (enc.get('url') if enc is not None else '') or (it.findtext('link') or '')
        size = attrs.get('size') or (enc.get('length') if enc is not None else 0) or 0
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = 0
        out.append({'title': (it.findtext('title') or '').strip(), 'link': link.strip(), 'size': size,
                    'grabs': attrs.get('grabs') or '', 'password': attrs.get('password') == '1',
                    'date': it.findtext('pubDate') or ''})
    return out


def test_indexer(idx):
    try:
        _items(_fetch('%s?%s' % (_api(idx['url']), urlencode({'t': 'search', 'q': 'test', 'limit': 1,
                                                                'apikey': idx.get('key', '')})), 20))
        return ''
    except Exception as e:
        return str(e) or e.__class__.__name__


def _search_one(idx, media, words_fn, match_fn):
    ep = media['media_type'] == 'episode'
    imdb = re.sub(r'\D', '', str(media.get('imdb') or ''))
    base = {'apikey': idx['key'], 'limit': 100, 'extended': 1}
    tries = []
    if ep:
        se = {'season': int(media['season']), 'ep': int(media['episode'])}
        if media.get('tvdb'):
            tries.append(dict(base, t='tvsearch', tvdbid=media['tvdb'], **se))
        if imdb:
            tries.append(dict(base, t='tvsearch', imdbid=imdb, **se))
        tries.append(dict(base, t='tvsearch', q=media.get('tvshowtitle') or media.get('title') or '', **se))
    else:
        if imdb:
            tries.append(dict(base, t='movie', imdbid=imdb))
        q = ('%s %s' % (media.get('title') or '', str(media.get('year') or '')[:4])).strip()
        tries.append(dict(base, t='movie', q=q))
    title = (media.get('tvshowtitle') if ep else media.get('title')) or media.get('title') or ''
    words = words_fn(title)
    year = str(media.get('year') or '')[:4]
    season = int(media['season']) if ep else None
    episode = int(media['episode']) if ep else None
    last = None
    for params in tries:
        try:
            items = _items(_fetch('%s?%s' % (_api(idx['url']), urlencode(params))))
        except Exception as e:
            last = e
            continue
        by_text = 'q' in params
        items = [i for i in items if i['link'] and not i['password'] and not _JUNK.search(i['title'])
                 and (not by_text or match_fn(i['title'], words, year, season, episode))]
        if ep:                                  # an id search can still return other episodes
            rx = _ep_rx(season, episode)
            pack = re.compile(r'(?<![a-z0-9])s0*%d(?![0-9e])' % season, re.I)
            items = [i for i in items if rx.search(i['title']) or (pack.search(i['title']) and
                                                                   not re.search(r'(?<![a-z0-9])s\d+[ ._-]?e\d+',
                                                                                 i['title'], re.I))]
        if items:
            return items
    if last:
        raise last
    return []


def _quality(name, size):
    m = re.search(r'(?<![a-z0-9])(2160p|4k|uhd|1080p|1080i|720p|576p|480p)(?![a-z0-9])', name.lower())
    if m:
        q = m.group(1)
        return '4K' if q in ('2160p', '4k', 'uhd') else ('1080P' if q.startswith('1080') else
                                                         ('720P' if q == '720p' else 'SD'))
    gb = size / 1073741824.0
    return '4K' if gb >= 30 else ('1080P' if gb >= 4 else ('720P' if gb >= 1.2 else 'SD'))


def search(media, words_fn, match_fn):
    """Rows for Search All from every indexer (one thread each)."""
    idxs = indexers()
    if not idxs:
        raise ValueError('no indexer')
    found, errors, threads = {}, [], []

    def run(idx):
        try:
            found[idx['name']] = _search_one(idx, media, words_fn, match_fn)
            _log('%s: %d releases' % (idx['name'], len(found[idx['name']])))
        except Exception as e:
            errors.append('%s: %s' % (idx['name'], e))
            _log('%s: %s' % (idx['name'], e), xbmc.LOGWARNING)

    for idx in idxs:
        t = threading.Thread(target=run, args=(idx,), name='abk-nz-' + idx['name'][:10])
        t.start()
        threads.append(t)
    for t in threads:
        t.join(60)
    if errors and not found:
        raise ValueError('; '.join(errors))
    out, seen = [], set()
    for idx in idxs:
        for it in found.get(idx['name']) or []:
            k = (it['title'].lower(), it['size'] // (1 << 20))
            if k in seen:
                continue
            seen.add(k)
            gb = round(it['size'] / 1073741824.0, 2)
            pack = media['media_type'] == 'episode' and not _ep_rx(int(media['season']),
                                                                   int(media['episode'])).search(it['title'])
            row = {'name': it['title'], 'display_name': re.sub(r'[._]+', ' ', it['title']).strip(),
                   'quality': _quality(it['title'], it['size']), 'size': gb,
                   'size_label': ('%.2f GB' % gb) if gb else '', 'scrape_provider': 'external',
                   'source': idx['name'], 'debrid': 'Usenet',
                   'extraInfo': ' | '.join(x for x in (idx['name'], ('%s grabs' % it['grabs']) if it['grabs'] else '')
                                           if x),
                   'abk_nn': {'nzb': it['link']}}
            if pack:
                row['package'] = True
            out.append(row)
    out.sort(key=lambda r: -r['size'])
    return out


# ───────────────────────── playing (Search All, add-on side) ─────────────────────────

def _port():
    try:
        return int(_home().getProperty(PORT_PROP) or 0)
    except ValueError:
        return 0


def _save_nzb(link):
    os.makedirs(NZB_DIR, exist_ok=True)
    path = os.path.join(NZB_DIR, hashlib.sha1(link.encode('utf-8')).hexdigest()[:16] + '.nzb')
    if os.path.isfile(path) and os.path.getsize(path) > 200:
        os.utime(path, None)
        return path
    data = _fetch(link, timeout=45, binary=True)
    if b'<nzb' not in data[:4096] and b'<segment' not in data:
        raise ValueError('the indexer did not return an NZB')
    with open(path + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(path + '.tmp', path)
    return path


_ERRORS = {'compressed': 32330, 'encrypted': 32331, 'incomplete': 32332, 'no provider': 32333,
           'no video found': 32334, 'no video in the RAR set': 32334, 'not a RAR volume': 32334}


def _local_server():
    """4.11.4: the service is not running (Kodi skipped it at boot - seen on
    macOS): ask it to start, wait a little, else run a server in this script
    and keep the script alive while the release plays (_hold)."""
    number = _port()
    if number:
        return number, None
    home = _home()
    if not home.getProperty('abukarimtools.service.alive.kick'):
        home.setProperty('abukarimtools.service.alive.kick', '1')
        _log('service not running - starting it', xbmc.LOGWARNING)
        xbmc.executebuiltin('RunPlugin(plugin://%s/?run=service)' % ADDON_ID)
    mon = xbmc.Monitor()
    for _ in range(40):                     # the service starts the server within seconds
        if mon.waitForAbort(0.25):
            break
        number = _port()
        if number:
            return number, None
    own = Server()
    number = own.start()
    _log('no service - NZB server in this script on port %d' % number, xbmc.LOGWARNING)
    return number, own


def _hold(own):
    """Keep a script-owned server up while Kodi plays from it."""
    mon = xbmc.Monitor()
    player = xbmc.Player()
    try:
        for _ in range(240):                # up to 60 s for playback to start
            if player.isPlaying() or mon.waitForAbort(0.25):
                break
        while player.isPlaying() and not mon.waitForAbort(1):
            pass
    finally:
        own.stop()
        _log('script NZB server stopped')


def play_nzb(link, media, title='', servers=None, meta=None):
    """Open the NZB on the local server and play it. False = not played
    (Search All shows the results again)."""
    from resources.lib.i18n import T
    try:
        number, own = _local_server()
    except Exception as e:
        _log('NZB server not available: %s' % e, xbmc.LOGWARNING)
        xbmcgui.Dialog().notification('AB Search All', T(32335), xbmcgui.NOTIFICATION_WARNING, 5000)
        return False
    if not servers and not can_play():
        xbmcgui.Dialog().ok('AB Search All', T(32333))
        return False
    ep = media.get('media_type') == 'episode'
    result = {}
    dlg = xbmcgui.DialogProgress()
    dlg.create('AB Search All - Usenet', T(32336))
    home = _home()
    home.setProperty(BUSY_PROP, 'nzb')

    def work():
        import urllib.request
        try:
            result['stage'] = 1
            path = _save_nzb(link)
            result['stage'] = 2
            q = {'nzb': path, 'check': '1', 'servers': json.dumps(list(servers or []))}
            if ep:
                q.update({'season': int(media['season']), 'episode': int(media['episode'])})
            with urllib.request.urlopen('http://%s:%d/%s/open?%s' % (HOST, number, PATH_MARK, urlencode(q)),
                                        timeout=180) as r:
                result.update(json.loads(r.read().decode('utf-8')))
        except Exception as e:
            result.update({'ok': False, 'error': 'failed', 'detail': str(e)})

    t = threading.Thread(target=work, name='abk-nzb-open')
    t.start()
    mon = xbmc.Monitor()
    shown = 0
    while t.is_alive():
        stage = result.get('stage', 0)
        if stage != shown:
            shown = stage
            dlg.update(10 if stage == 1 else 45, T(32336) if stage == 1 else T(32337))
        if dlg.iscanceled() or mon.waitForAbort(0.2):
            result.setdefault('cancel', True)
            break
    try:
        dlg.close()
    except Exception:
        pass
    if result.get('cancel') and not result.get('ok'):
        home.clearProperty(BUSY_PROP)
        _log('cancelled while opening')
        if own:
            threading.Thread(target=own.stop, daemon=True).start()
        return False
    if not result.get('ok'):
        home.clearProperty(BUSY_PROP)
        if own:
            own.stop()
        err = result.get('error') or 'failed'
        _log('not playable: %s %s' % (err, result.get('detail') or ''), xbmc.LOGWARNING)
        msg = T(_ERRORS[err]) if err in _ERRORS else T(32338) % (result.get('detail') or err)
        xbmcgui.Dialog().notification('AB Search All', msg, xbmcgui.NOTIFICATION_WARNING, 6000)
        return False
    url = 'http://%s:%d%s' % (HOST, number, result['path'])
    _log('play: %s (%.2f GB)' % (result.get('name'), float(result.get('size') or 0) / 1073741824.0))
    from resources.lib import local_folders
    item = {'abk_loc': {'path': url}, 'display_name': title or result.get('name'), 'name': result.get('name')}
    try:
        ok = local_folders.play(item, media, meta)
    finally:
        home.clearProperty(BUSY_PROP)
    if own:
        if ok:
            _hold(own)
        else:
            own.stop()
    return ok


def play(item, media, meta=None):
    """A Search All 'Usenet' row."""
    nn = (item or {}).get('abk_nn') or {}
    if not nn.get('nzb'):
        return False
    return play_nzb(nn['nzb'], media, item.get('display_name') or '', nn.get('servers'), meta)


# ───────────────────────── manager (Mods > Search All: Usenet) ─────────────────────────

def summary():
    from resources.lib.i18n import T
    n, m = len(providers()), len(indexers())
    return T(32318) % (n, m) if (n or m) else T(32317)


def _input(label, default='', hidden=False):
    opt = xbmcgui.ALPHANUM_HIDE_INPUT if hidden else 0
    v = xbmcgui.Dialog().input(label, default, type=xbmcgui.INPUT_ALPHANUM, option=opt)
    return (v or '').strip()


def _easynews_login():
    try:
        from resources.lib import ab_search
        return ab_search._en_login()
    except Exception:
        return '', ''


def _edit_provider(p=None):
    from resources.lib.i18n import T
    p = dict(p or {})
    if not p:
        user, pwd = _easynews_login()
        choices = [T(32320)] + ([T(32321)] if user and pwd else [])
        c = xbmcgui.Dialog().select(T(32319), choices)
        if c < 0:
            return None
        if c == 1:
            p = {'name': 'Easynews', 'host': 'news.easynews.com', 'port': 563, 'ssl': True, 'user': user,
                 'pass': pwd, 'conns': 20}
    if not p.get('host'):
        host = _input(T(32322), 'news.')
        if not host or host == 'news.':
            return None
        p['host'] = host
        p['name'] = host
        p['ssl'] = xbmcgui.Dialog().yesno(T(32319), T(32323), nolabel=T(32347), yeslabel='SSL / TLS')
        p['port'] = int(_input(T(32324), '563' if p['ssl'] else '119') or (563 if p['ssl'] else 119))
        p['user'] = _input(T(32325))
        p['pass'] = _input(T(32326), hidden=True)
        p['conns'] = int(re.sub(r'\D', '', _input(T(32327), '10')) or 10)
    return p


def _edit_indexer():
    from resources.lib.i18n import T
    url = _input(T(32328), 'https://')
    if not url or url == 'https://':
        return None
    key = _input(T(32329))
    name = _input(T(32297), urlsplit(url).hostname or 'Newznab') or 'Newznab'
    return {'name': name, 'url': url, 'key': key}


def _test(kind, obj):
    from resources.lib.i18n import T
    busy = xbmcgui.DialogProgressBG()
    busy.create('AB Search All', T(32339))
    try:
        err = test_provider(obj) if kind == 'p' else test_indexer(obj)
    finally:
        busy.close()
    if err:
        xbmcgui.Dialog().ok('AB Search All', T(32340) % (obj.get('name'), err))
    else:
        xbmcgui.Dialog().notification('AB Search All', T(32341) % obj.get('name'), xbmcgui.NOTIFICATION_INFO, 3000)
    return not err


def run():
    from resources.lib.i18n import T
    while True:
        cfg = config()
        provs, idxs = cfg['providers'], cfg['indexers']
        rows = [xbmcgui.ListItem('[B]+ %s[/B]' % T(32319)), xbmcgui.ListItem('[B]+ %s[/B]' % T(32342))]
        for p in provs:
            pn = _norm_provider(p)
            rows.append(xbmcgui.ListItem('%s  [%s]' % (pn['name'], T(32343)),
                                         '%s:%d  %s  x%d' % (pn['host'], pn['port'], 'SSL' if pn['ssl'] else '',
                                                             pn['conns'])))
        for i in idxs:
            rows.append(xbmcgui.ListItem('%s  [Newznab]' % i.get('name'), i.get('url')))
        rows.append(xbmcgui.ListItem(T(32344) % int(cfg.get('cache_mb') or 128)))
        pick = xbmcgui.Dialog().select(T(32314), rows, useDetails=True)
        if pick < 0:
            return
        if pick == 0:
            p = _edit_provider()
            if p and _test('p', p):
                provs.append(p)
                save_config(cfg)
            elif p and xbmcgui.Dialog().yesno('AB Search All', T(32345)):
                provs.append(p)
                save_config(cfg)
            continue
        if pick == 1:
            i = _edit_indexer()
            if i and (_test('i', i) or xbmcgui.Dialog().yesno('AB Search All', T(32345))):
                idxs.append(i)
                save_config(cfg)
            continue
        if pick == len(rows) - 1:
            v = re.sub(r'\D', '', _input(T(32346), str(cfg.get('cache_mb') or 128)))
            if v:
                cfg['cache_mb'] = max(32, min(1024, int(v)))
                save_config(cfg)
            continue
        n = pick - 2
        if n < len(provs):
            p = provs[n]
            act = xbmcgui.Dialog().select(_norm_provider(p)['name'], [T(32339), T(32327), T(32299), T(32298)])
            if act == 0:
                _test('p', p)
            elif act == 1:
                v = re.sub(r'\D', '', _input(T(32327), str(_norm_provider(p)['conns'])))
                if v:
                    p['conns'] = int(v)
                    save_config(cfg)
            elif act == 2:
                v = _input(T(32297), p.get('name') or p.get('host'))
                if v:
                    p['name'] = v
                    save_config(cfg)
            elif act == 3:
                provs.remove(p)
                save_config(cfg)
        else:
            i = idxs[n - len(provs)]
            act = xbmcgui.Dialog().select(i.get('name') or 'Newznab', [T(32339), T(32299), T(32298)])
            if act == 0:
                _test('i', i)
            elif act == 1:
                v = _input(T(32297), i.get('name'))
                if v:
                    i['name'] = v
                    save_config(cfg)
            elif act == 2:
                idxs.remove(i)
                save_config(cfg)


# ───────────────────────── the server process (python3 usenet_stream.py --serve) ─────────────────────────

def _serve_main():
    """Runs outside Kodi: ABK_DATA = AB Tools' addon_data folder (usenet.json,
    nzb/). Ends when Kodi (the parent) ends."""
    import signal
    parent = os.getppid()
    s = Server()
    number = s.start()
    print('PORT %d' % number, flush=True)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    while not stop.wait(3):
        if os.getppid() != parent:
            break
    try:
        s.stop()
    except Exception:
        pass


if __name__ == '__main__' and not _IN_KODI:
    import sys as _s
    if '--serve' in _s.argv:
        _serve_main()
