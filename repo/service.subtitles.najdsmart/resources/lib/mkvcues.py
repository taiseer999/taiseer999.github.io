# -*- coding: utf-8 -*-
"""Timing of the subtitles built into an MKV file, read from its index.

An MKV keeps an index ("Cues") that mkvmerge fills with an entry for every subtitle
block: the time a line appears (and, in newer files, how long it stays). Reading the
file head, the track list and that index is usually 1-3 small range requests — the
video and audio are never touched, even for a 60 GB remux over the internet.

The result is a list of (start_ms, end_ms) that is exactly in sync with THIS video,
which makes it the best timing reference there is.

Pure Python, no Kodi imports (testable outside Kodi).
"""
import struct
import time
import urllib.parse
import urllib.request
import ssl

EBML, SEGMENT, SEEKHEAD, SEEK, SEEKID, SEEKPOS = 0x1A45DFA3, 0x18538067, 0x114D9B74, 0x4DBB, 0x53AB, 0x53AC
INFO, TIMESCALE, DURATION = 0x1549A966, 0x2AD7B1, 0x4489
TRACKS, TRACKENTRY, TRACKNUM, TRACKTYPE, CODEC, NAME = 0x1654AE6B, 0xAE, 0xD7, 0x83, 0x86, 0x536E
LANG, LANG_BCP47, FORCED = 0x22B59C, 0x22B59D, 0x55AA
CUES, CUEPOINT, CUETIME, CUETRACKPOS, CUETRACK, CUEDUR = 0x1C53BB6B, 0xBB, 0xB3, 0xB7, 0xF7, 0xB2
CLUSTER = 0x1F43B675
CUECLUSTER, CUEREL = 0xF1, 0xF0
SIMPLEBLOCK, BLOCKGROUP, BLOCK, BLOCKDUR = 0xA3, 0xA0, 0xA1, 0x9B
CODECPRIV = 0x63A2
ENCODINGS, ENCODING, COMPRESSION, COMPALGO, COMPSETTINGS = 0x6D80, 0x6240, 0x5034, 0x4254, 0x4255
SUBTITLE = 17
MB = 1024 * 1024


class MkvError(Exception):
    pass


# ---------------------------------------------------------------- readers
class _Budget(object):
    def __init__(self, max_bytes, max_requests, deadline):
        self.bytes, self.requests = 0, 0
        self.max_bytes, self.max_requests, self.deadline = max_bytes, max_requests, deadline

    def charge(self, n):
        self.requests += 1
        self.bytes += n
        if self.requests > self.max_requests or self.bytes > self.max_bytes:
            raise MkvError('budget')
        if time.time() > self.deadline:
            raise MkvError('timeout')


class FileReader(object):
    def __init__(self, path, budget):
        self.f = open(path, 'rb')
        self.budget = budget
        self.f.seek(0, 2)
        self.size = self.f.tell()

    def read(self, pos, n):
        self.budget.charge(n)
        self.f.seek(pos)
        return self.f.read(n)

    def close(self):
        self.f.close()


class HttpReader(object):
    """Range requests. Kodi URLs may carry headers after '|' (User-Agent=...&Referer=...)."""

    def __init__(self, path, budget, timeout=20):   # Piers edition: slow far seeks (usenet)
        url, _, hdrs = path.partition('|')
        self.url = url
        self.headers = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'}
        if hdrs:
            self.headers.update(dict(urllib.parse.parse_qsl(hdrs)))
        self.budget = budget
        self.timeout = timeout
        self.size = None
        self.ctx = ssl.create_default_context()

    def read(self, pos, n):
        if pos < 0:
            pos = 0
        self.budget.charge(n)
        h = dict(self.headers, Range='bytes=%d-%d' % (pos, pos + n - 1))
        req = urllib.request.Request(self.url, headers=h)
        left = max(2.0, min(self.timeout, self.budget.deadline - time.time()))
        with urllib.request.urlopen(req, timeout=left, context=self.ctx) as r:
            if r.status == 200 and pos > 0:
                raise MkvError('no_range')          # server ignores Range: never download the film
            cr = r.headers.get('Content-Range') or ''
            if '/' in cr and cr.rsplit('/', 1)[1].strip().isdigit():
                self.size = int(cr.rsplit('/', 1)[1])
            out = bytearray()
            while len(out) < n:
                chunk = r.read(min(256 * 1024, n - len(out)))
                if not chunk:
                    break
                out += chunk
            return bytes(out)

    def close(self):
        pass


def open_source(path, budget):
    if path.startswith(('http://', 'https://')):
        return HttpReader(path, budget)
    if '://' in path:
        raise MkvError('unsupported_path')
    return FileReader(path, budget)


# ---------------------------------------------------------------- EBML
def _vint(buf, pos, strip):
    if pos >= len(buf):
        raise MkvError('eof')
    first = buf[pos]
    length = 1
    mask = 0x80
    while length <= 8 and not (first & mask):
        mask >>= 1
        length += 1
    if length > 8 or pos + length > len(buf):
        raise MkvError('bad_vint')
    val = (first & (mask - 1)) if strip else first
    for b in buf[pos + 1:pos + length]:
        val = (val << 8) | b
    unknown = strip and val == (1 << (7 * length)) - 1
    return val, length, unknown


def header(buf, pos):
    """→ (id, data_start, data_size or None if unknown)."""
    eid, l1, _ = _vint(buf, pos, False)
    size, l2, unknown = _vint(buf, pos + l1, True)
    return eid, pos + l1 + l2, (None if unknown else size)


def children(buf, start, end):
    pos = start
    while pos < end:
        try:
            eid, ds, size = header(buf, pos)
        except MkvError:
            return
        if size is None:
            yield eid, ds, None
            return
        yield eid, ds, size
        pos = ds + size


def _uint(buf, s, n):
    v = 0
    for b in buf[s:s + n]:
        v = (v << 8) | b
    return v


def _float(buf, s, n):
    if n == 4:
        return struct.unpack('>f', bytes(buf[s:s + 4]))[0]
    if n == 8:
        return struct.unpack('>d', bytes(buf[s:s + 8]))[0]
    return 0.0


def _str(buf, s, n):
    return bytes(buf[s:s + n]).split(b'\0')[0].decode('utf-8', 'replace')


# ---------------------------------------------------------------- parsers
def parse_seekhead(buf, s, e):
    out = {}
    for eid, ds, size in children(buf, s, e):
        if eid != SEEK or size is None:
            continue
        sid = pos = None
        for cid, cs, cn in children(buf, ds, ds + size):
            if cid == SEEKID:
                sid = _uint(buf, cs, cn)
            elif cid == SEEKPOS:
                pos = _uint(buf, cs, cn)
        if sid is not None and pos is not None:
            out.setdefault(sid, []).append(pos)
    return out


def parse_info(buf, s, e):
    scale, dur = 1000000, 0.0
    for eid, ds, size in children(buf, s, e):
        if eid == TIMESCALE:
            scale = _uint(buf, ds, size) or 1000000
        elif eid == DURATION:
            dur = _float(buf, ds, size)
    return scale, dur


def parse_tracks(buf, s, e):
    tracks = []
    for eid, ds, size in children(buf, s, e):
        if eid != TRACKENTRY or size is None:
            continue
        t = {'lang': 'eng', 'name': '', 'forced': False, 'codec': '', 'type': 0, 'num': 0}
        for cid, cs, cn in children(buf, ds, ds + size):
            if cid == TRACKNUM:
                t['num'] = _uint(buf, cs, cn)
            elif cid == TRACKTYPE:
                t['type'] = _uint(buf, cs, cn)
            elif cid == CODEC:
                t['codec'] = _str(buf, cs, cn)
            elif cid == LANG:
                t['lang'] = _str(buf, cs, cn) or 'eng'
            elif cid == LANG_BCP47:
                t['lang'] = _str(buf, cs, cn) or t['lang']
            elif cid == NAME:
                t['name'] = _str(buf, cs, cn)
            elif cid == FORCED:
                t['forced'] = bool(_uint(buf, cs, cn))
            elif cid == ENCODINGS:
                for _a, es, en in children(buf, cs, cs + cn):
                    for bid, bs, bn in children(buf, es, es + en):
                        if bid != COMPRESSION:
                            continue
                        algo, sett = 0, b''
                        for xid, xs, xn in children(buf, bs, bs + bn):
                            if xid == COMPALGO:
                                algo = _uint(buf, xs, xn)
                            elif xid == COMPSETTINGS:
                                sett = bytes(buf[xs:xs + xn])
                        t['comp'] = (algo, sett)
        tracks.append(t)
    return tracks


def parse_cues(buf, s, e, wanted, where=None):
    """→ {track: [(time, duration_or_None)]} for the wanted track numbers.
    where (a dict) is filled with {track: [(time, dur, cluster_pos, relative_pos)]}."""
    out = {n: [] for n in wanted}
    if where is not None:
        for n in wanted:
            where[n] = []
    for eid, ds, size in children(buf, s, e):
        if eid != CUEPOINT or size is None:
            continue
        t = None
        poss = []
        for cid, cs, cn in children(buf, ds, ds + size):
            if cid == CUETIME:
                t = _uint(buf, cs, cn)
            elif cid == CUETRACKPOS:
                trk = dur = cl = rel = None
                for pid, ps, pn in children(buf, cs, cs + cn):
                    if pid == CUETRACK:
                        trk = _uint(buf, ps, pn)
                    elif pid == CUEDUR:
                        dur = _uint(buf, ps, pn)
                    elif pid == CUECLUSTER:
                        cl = _uint(buf, ps, pn)
                    elif pid == CUEREL:
                        rel = _uint(buf, ps, pn)
                poss.append((trk, dur, cl, rel))
        if t is None:
            continue
        for trk, dur, cl, rel in poss:
            if trk in out:
                out[trk].append((t, dur))
                if where is not None:
                    where[trk].append((t, dur, cl, rel))
    return out


def is_text(codec):
    return codec.startswith('S_TEXT') or codec in ('S_SSA', 'S_ASS')


def is_image(codec):
    return codec in ('S_HDMV/PGS', 'S_VOBSUB', 'S_DVBSUB', 'S_HDMV/TEXTST')


# ---------------------------------------------------------------- main
def _element(src, seg, rel, expect, cap):
    """Read one top-level element at segment-relative position rel."""
    at = seg + rel
    head = src.read(at, 16)
    eid, ds, size = header(head, 0)
    if eid != expect or size is None:
        raise MkvError('not_%x' % expect)
    if size > cap:
        raise MkvError('too_big')
    body = src.read(at + ds, size)
    return body


def read_index(path, max_bytes=24 * MB, max_requests=10, timeout=15.0, positions=False):
    """→ {'tracks': [...], 'scale': ns per tick, 'duration_ms', 'cues': {num: [(t, dur)]}, 'stats'}"""
    budget = _Budget(max_bytes, max_requests, time.time() + timeout)
    src = open_source(path, budget)
    try:
        head = src.read(0, 512 * 1024)
        eid, ds, size = header(head, 0)
        if eid != EBML:
            raise MkvError('not_mkv')
        pos = ds + size
        eid, seg, _ssize = header(head, pos)
        if eid != SEGMENT:
            raise MkvError('no_segment')
        found = {}
        info = tracks = None
        cues_buf = None
        p = seg
        while p < len(head):
            try:
                eid, cs, csize = header(head, p)
            except MkvError:
                break
            if eid == CLUSTER or csize is None:
                break
            if cs + csize > len(head):
                # element runs past what we read: fetch it later by its position
                if eid in (SEEKHEAD, INFO, TRACKS, CUES):
                    found.setdefault(eid, []).insert(0, p - seg)
                break
            if eid == SEEKHEAD:
                for k, v in parse_seekhead(head, cs, cs + csize).items():
                    found.setdefault(k, []).extend(v)
            elif eid == INFO:
                info = parse_info(head, cs, cs + csize)
            elif eid == TRACKS:
                tracks = parse_tracks(head, cs, cs + csize)
            elif eid == CUES:
                cues_buf = (head, cs, cs + csize)
            p = cs + csize
        # a second SeekHead (often at the end) may hold the Cues position
        if CUES not in found and SEEKHEAD in found:
            for rel in found[SEEKHEAD]:
                try:
                    body = _element(src, seg, rel, SEEKHEAD, 2 * MB)
                    for k, v in parse_seekhead(body, 0, len(body)).items():
                        found.setdefault(k, []).extend(v)
                except MkvError:
                    pass
        if info is None and INFO in found:
            body = _element(src, seg, found[INFO][0], INFO, 512 * 1024)
            info = parse_info(body, 0, len(body))
        if tracks is None and TRACKS in found:
            body = _element(src, seg, found[TRACKS][0], TRACKS, 4 * MB)
            tracks = parse_tracks(body, 0, len(body))
        if not tracks:
            raise MkvError('no_tracks')
        subs = [t for t in tracks if t['type'] == SUBTITLE]
        if not subs:
            return {'tracks': tracks, 'cues': {}, 'scale': (info or (1000000, 0))[0],
                    'duration_ms': 0, 'reason': 'no_subtitle_tracks'}
        if cues_buf is None:
            if CUES not in found:
                raise MkvError('no_cues_index')
            body = _element(src, seg, found[CUES][0], CUES, 16 * MB)
            cues_buf = (body, 0, len(body))
        scale, dur = info or (1000000, 0.0)
        where = {} if positions else None
        cues = parse_cues(cues_buf[0], cues_buf[1], cues_buf[2], [t['num'] for t in subs], where)
        return {'tracks': tracks, 'cues': cues, 'scale': scale, 'seg': seg, 'where': where,
                'duration_ms': int(dur * scale / 1e6),
                'stats': {'requests': budget.requests, 'bytes': budget.bytes}}
    finally:
        try:
            src.close()
        except Exception:
            pass


def _intervals(entries, scale, image):
    ms = [(int(t * scale / 1e6), (int(d * scale / 1e6) if d else None)) for t, d in entries]
    ms.sort()
    out = []
    if image:
        # bitmap subtitles: one block shows the line, the next (empty) one clears it
        k = 0
        while k < len(ms):
            s = ms[k][0]
            if ms[k][1]:
                out.append((s, s + ms[k][1]))
                k += 1
            elif k + 1 < len(ms) and 300 <= ms[k + 1][0] - s <= 8000:
                out.append((s, ms[k + 1][0]))
                k += 2
            else:
                out.append((s, s + 2000))
                k += 1
    else:
        for k, (s, d) in enumerate(ms):
            nxt = ms[k + 1][0] if k + 1 < len(ms) else s + 3000
            e = s + d if d else min(s + 2500, max(s + 600, nxt - 80))
            out.append((s, e))
    # duplicates (the same line indexed twice) away
    dedup = []
    for s, e in out:
        if dedup and abs(s - dedup[-1][0]) < 40:
            continue
        dedup.append((s, e))
    return dedup


def pick_track(index, min_lines=40, min_span_ms=300000):
    """The best subtitle track to use as a timing reference: full (not forced) dialogue,
    text before bitmap, English first."""
    best = None
    for t in index.get('tracks', []):
        if t['type'] != SUBTITLE:
            continue
        entries = index['cues'].get(t['num']) or []
        text, image = is_text(t['codec']), is_image(t['codec'])
        if not (text or image):
            continue
        name = (t.get('name') or '').lower()
        if t.get('forced') or 'forced' in name or 'sign' in name or 'song' in name:
            continue
        iv = _intervals(entries, index['scale'], image)
        if len(iv) < min_lines or (iv[-1][0] - iv[0][0]) < min_span_ms:
            continue
        lang = (t.get('lang') or '').lower()
        score = (1 if text else 0, 1 if lang.startswith('en') else 0,
                 0 if ('sdh' in name or 'cc' in name.split()) else 1, len(iv))
        if best is None or score > best[0]:
            best = (score, t, iv)
    if not best:
        return None, []
    return best[1], best[2]


def timeline(path, **kw):
    """→ (track, [(start_ms, end_ms)], index) or raises MkvError."""
    index = read_index(path, **kw)
    track, iv = pick_track(index)
    return track, iv, index


# ---------------------------------------------------------------- the text itself
def text_tracks(index):
    """Text subtitle tracks that hold the whole dialogue (not forced / signs only)."""
    out = []
    for t in index.get('tracks', []):
        if t['type'] != SUBTITLE or not is_text(t['codec']):
            continue
        name = (t.get('name') or '').lower()
        n = len(index['cues'].get(t['num']) or [])
        if t.get('forced') or 'forced' in name or 'sign' in name or 'song' in name or n < 40:
            continue
        out.append(t)
    return out


def _payload_text(codec, data):
    import re
    try:
        txt = data.decode('utf-8')
    except UnicodeDecodeError:
        txt = data.decode('cp1252', 'replace')
    if codec in ('S_TEXT/ASS', 'S_TEXT/SSA', 'S_ASS', 'S_SSA'):
        # ReadOrder, Layer, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        parts = txt.split(',', 8)
        txt = parts[8] if len(parts) == 9 else parts[-1]
        txt = re.sub(r'\{[^}]*\}', '', txt).replace('\\N', '\n').replace('\\n', '\n').replace('\\h', ' ')
    elif codec == 'S_TEXT/WEBVTT':
        txt = re.sub(r'</?c[^>]*>', '', txt)
    return '\n'.join(l.strip() for l in txt.strip().splitlines() if l.strip())


def _decompress(track, data):
    comp = track.get('comp')
    if not comp:
        return data
    algo, sett = comp
    if algo == 0:
        import zlib
        return zlib.decompress(data)
    if algo == 3:
        return sett + data
    raise MkvError('compression_%d' % algo)


def _parse_block(buf, track):
    """→ (payload bytes, duration ticks or None) from a SimpleBlock/BlockGroup buffer."""
    eid, ds, size = header(buf, 0)
    if size is None or ds + size > len(buf):
        raise MkvError('short_block')
    dur = None
    if eid == BLOCKGROUP:
        blk = None
        for cid, cs, cn in children(buf, ds, ds + size):
            if cid == BLOCK:
                blk = (cs, cn)
            elif cid == BLOCKDUR:
                dur = _uint(buf, cs, cn)
        if not blk:
            raise MkvError('no_block')
        bs, bn = blk
    elif eid == SIMPLEBLOCK:
        bs, bn = ds, size
    else:
        raise MkvError('not_block')
    num, l, _ = _vint(buf, bs, True)
    if num != track['num']:
        raise MkvError('wrong_track')
    flags = buf[bs + l + 2]
    if flags & 0x06:
        raise MkvError('laced')
    return _decompress(track, bytes(buf[bs + l + 3:bs + bn])), dur


class KeepAliveReader(object):
    """Range reads over ONE kept-open connection (a new TLS handshake for every
    small read is what makes debrid/CDN servers time out). Follows redirects."""

    def __init__(self, path, timeout=20):
        import http.client
        self._hc = http.client
        url, _, hdrs = path.partition('|')
        self.headers = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Connection': 'keep-alive'}
        if hdrs:
            self.headers.update(dict(urllib.parse.parse_qsl(hdrs)))
        self.timeout = timeout
        self.ctx = ssl.create_default_context()
        self.conn = None
        self._set(url)

    def _set(self, url):
        u = urllib.parse.urlsplit(url)
        self.scheme, self.host = u.scheme, u.netloc
        self.target = (u.path or '/') + ('?' + u.query if u.query else '')
        self.close()

    def _connect(self):
        if self.scheme == 'https':
            self.conn = self._hc.HTTPSConnection(self.host, timeout=self.timeout, context=self.ctx)
        else:
            self.conn = self._hc.HTTPConnection(self.host, timeout=self.timeout)

    def read(self, pos, n):
        for hop in range(6):
            if self.conn is None:
                self._connect()
            h = dict(self.headers, Range='bytes=%d-%d' % (pos, pos + n - 1))
            try:
                self.conn.request('GET', self.target, headers=h)
                r = self.conn.getresponse()
                status = r.status
                if status in (301, 302, 303, 307, 308):
                    r.read(65536)
                    data = b''
                elif status == 200:
                    # the server ignored Range: never pull the whole film — take what we
                    # asked for (only useful at the very start) and drop the connection
                    data = r.read(n) if pos == 0 else b''
                    self.close()
                elif status == 206:
                    try:
                        cl = int(r.getheader('Content-Length') or 0)
                    except ValueError:
                        cl = 0
                    if cl > n + 65536:
                        data = r.read(n)
                        self.close()
                    else:
                        data = r.read()
                else:
                    data = b''
                    self.close()
            except Exception:
                self.close()
                raise
            if status in (301, 302, 303, 307, 308):
                loc = r.getheader('Location')
                if not loc:
                    raise MkvError('redirect_without_location')
                self._set(urllib.parse.urljoin('%s://%s%s' % (self.scheme, self.host, self.target), loc))
                continue
            if status == 200 and pos > 0:
                raise MkvError('no_range')
            if status not in (200, 206):
                raise MkvError('http_%d' % status)
            if self.conn is not None and (r.getheader('Connection') or '').lower() == 'close':
                self.close()
            return data[:n]
        raise MkvError('too_many_redirects')

    def read_many(self, spans, max_bytes=4 * MB):
        """Several byte ranges in ONE request (multipart/byteranges).
        → [(start, bytes)] segments, or None if the server will not do it."""
        rng = ','.join('%d-%d' % (a, a + n - 1) for a, n in spans)
        for hop in range(6):
            if self.conn is None:
                self._connect()
            h = dict(self.headers, Range='bytes=' + rng)
            try:
                self.conn.request('GET', self.target, headers=h)
                r = self.conn.getresponse()
            except Exception:
                self.close()
                raise
            if r.status in (301, 302, 303, 307, 308):
                r.read()
                loc = r.getheader('Location')
                self._set(urllib.parse.urljoin('%s://%s%s' % (self.scheme, self.host, self.target), loc))
                continue
            clen = int(r.getheader('Content-Length') or 0)
            if r.status != 206 or not clen or clen > max_bytes:
                self.close()               # never download the film itself
                return None
            data = r.read()
            if (r.getheader('Connection') or '').lower() == 'close':
                self.close()
            ctype = r.getheader('Content-Type') or ''
            if 'multipart/byteranges' not in ctype:
                cr = r.getheader('Content-Range') or ''
                try:
                    a = int(cr.split()[1].split('-')[0])
                except (IndexError, ValueError):
                    return None
                return [(a, data)]
            b = ctype.split('boundary=', 1)[-1].strip().strip('"').encode()
            segs = []
            for part in data.split(b'--' + b):
                hdr, sep, body = part.partition(b'\r\n\r\n')
                if not sep:
                    continue
                m = None
                for line in hdr.split(b'\r\n'):
                    if line.lower().startswith(b'content-range:'):
                        m = line.split(b':', 1)[1].strip()
                if not m:
                    continue
                try:
                    a, z = m.split()[1].split(b'/')[0].split(b'-')
                    a, z = int(a), int(z)
                except (IndexError, ValueError):
                    continue
                segs.append((a, body[:z - a + 1]))
            return segs or None
        raise MkvError('too_many_redirects')

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None


def read_text(path, track, index, workers=4, timeout=180.0, progress=None, abort=None, t_range=None):
    """Read every line of a text subtitle track: [(start_ms, end_ms, text)].
    Only the subtitle blocks are fetched: one small range read per line, a few
    kept-open connections in parallel, each line retried if the server hiccups."""
    import concurrent.futures
    import threading
    entries = (index.get('where') or {}).get(track['num']) or []
    if not entries:
        raise MkvError('no_positions')
    if any(e[2] is None or e[3] is None for e in entries):
        raise MkvError('no_relative_positions')
    scale, seg = index['scale'], index['seg']
    if t_range:
        a_ms, b_ms = t_range
        entries = [e for e in entries if a_ms <= e[0] * scale / 1e6 < b_ms]
        if not entries:
            return []
    remote = path.startswith(('http://', 'https://'))
    deadline = time.time() + timeout
    lock = threading.Lock()
    local = threading.local()
    readers = []
    stop = [False]

    def reader():
        r = getattr(local, 'r', None)
        if r is None:
            if remote:
                r = KeepAliveReader(path)
            else:
                r = FileReader(path, _Budget(1 << 40, 1 << 30, deadline + 3600))
            local.r = r
            with lock:
                readers.append(r)
        return r

    tvint = bytes([0x80 | track['num']]) if track['num'] < 127 else None

    def find_block(buf, base):
        """The block sits right after the cluster header (4-byte ID + 1..8-byte size)."""
        for h in range(5, 13):
            k = base + h
            if k + 4 > len(buf) or buf[k] not in (SIMPLEBLOCK, BLOCKGROUP):
                continue
            try:
                eid, ds, size = header(buf, k)
            except MkvError:
                continue
            if size is None:
                continue
            inner = ds if eid == SIMPLEBLOCK else None
            if eid == BLOCKGROUP:
                try:
                    for cid, cs, cn in children(buf, ds, min(len(buf), ds + size)):
                        if cid == BLOCK:
                            inner = cs
                            break
                except MkvError:
                    continue
            if inner is not None and inner < len(buf) and (tvint is None or buf[inner:inner + 1] == tvint):
                return k, ds + size
        return None

    def one(e):
        t, dur, cl, rel = e
        at = seg + cl + rel          # block position minus the (unknown) cluster-header size
        last = None
        for attempt in range(4):
            if stop[0] or (abort and abort()):
                raise MkvError('aborted')
            if time.time() > deadline:
                raise MkvError('timeout')
            try:
                r = reader()
                buf = r.read(at, 4096)
                hit = find_block(buf, 0)
                if hit is None:
                    raise MkvError('block_not_found')
                k, end = hit
                if end > len(buf):
                    buf = r.read(at, end)
                data, bdur = _parse_block(buf[k:], track)
                s = int(t * scale / 1e6)
                d = dur or bdur
                return s, (s + int(d * scale / 1e6)) if d else None, _payload_text(track['codec'], data)
            except MkvError as er:
                if str(er) in ('aborted', 'no_range', 'block_not_found'):
                    raise
                last = er
            except Exception as er:
                last = er
            time.sleep(0.4 * (attempt + 1))
        raise last

    def decode(e, buf):
        t, dur, cl, rel = e
        hit = find_block(buf, 0)
        if hit is None:
            return None
        k, end = hit
        if end > len(buf):
            return 'more', end
        data, bdur = _parse_block(buf[k:], track)
        s = int(t * scale / 1e6)
        d = dur or bdur
        return s, (s + int(d * scale / 1e6)) if d else None, _payload_text(track['codec'], data)

    if remote:
        return _remote_lines(path, entries, seg, decode, one, reader, readers, progress, abort,
                             deadline, stop)

    out, errors = [], []
    done = [0]
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futs = []
    try:
        futs = [ex.submit(one, e) for e in entries]
        for f in concurrent.futures.as_completed(futs):
            try:
                out.append(f.result())
            except MkvError as er:
                if str(er) in ('aborted', 'no_range'):
                    raise
                errors.append(er)
            except Exception as er:
                errors.append(er)
            done[0] += 1
            if len(errors) > len(entries) * 0.2:
                break
            if progress and done[0] % 20 == 0:
                progress(done[0], len(futs))
    finally:
        stop[0] = True
        for f in futs:
            f.cancel()
        ex.shutdown(wait=False)
        for r in readers:
            try:
                r.close()
            except Exception:
                pass
    if len(errors) > len(entries) * 0.2:
        raise MkvError('read_failed: %s' % errors[0])
    return _finish(out)


def _finish(out):
    out.sort()
    lines = []
    for k, (s, e, txt) in enumerate(out):
        if not txt:
            continue
        if lines and abs(s - lines[-1][0]) < 40 and txt == lines[-1][2]:
            continue
        if e is None:
            nxt = out[k + 1][0] if k + 1 < len(out) else s + 3000
            e = min(s + 4000, max(s + 800, nxt - 80))
        lines.append((s, e, txt))
    return lines


def _remote_lines(path, entries, seg, decode, one, reader, readers, progress, abort, deadline, stop,
                  batch=40):
    """Over the internet: ONE connection (servers often allow only one or two per link,
    and the player already uses one). Ask for many lines per request; if the server
    can't do that, read them one after another on the same connection."""
    out, errors = [], []
    multi = True
    order = sorted(entries, key=lambda e: e[2] + e[3])
    k = 0
    try:
        while k < len(order):
            if abort and abort():
                raise MkvError('aborted')
            if time.time() > deadline:
                raise MkvError('timeout')
            chunk = order[k:k + batch]
            k += len(chunk)
            pending = list(chunk)
            if multi:
                segs = None
                for attempt in range(3):
                    try:
                        segs = reader().read_many([(seg + e[2] + e[3], 4096) for e in chunk])
                        break
                    except Exception as er:
                        reader().close()
                        time.sleep(0.6 * (attempt + 1))
                        segs = er
                if isinstance(segs, Exception):
                    segs = None
                if segs is None:
                    multi = False          # this server: one range per request from now on
                else:
                    pending = []
                    for e in chunk:
                        at = seg + e[2] + e[3]
                        buf = None
                        for a, data in segs:
                            if a <= at < a + len(data):
                                buf = data[at - a:]
                                break
                        try:
                            r = decode(e, buf) if buf else None
                        except Exception:
                            r = None          # one odd block: read it on its own below
                        if r is None or r[0] == 'more':
                            pending.append(e)
                        else:
                            out.append(r)
            for e in pending:
                try:
                    out.append(one(e))
                except MkvError as er:
                    if str(er) in ('aborted', 'no_range', 'timeout'):
                        raise
                    errors.append(er)
                except Exception as er:
                    errors.append(er)
                if len(errors) > len(entries) * 0.2:
                    raise MkvError('read_failed: %s' % errors[0])
            if progress:
                progress(min(k, len(order)), len(order))
    finally:
        stop[0] = True
        for r in readers:
            try:
                r.close()
            except Exception:
                pass
    if len(errors) > len(entries) * 0.2:
        raise MkvError('read_failed: %s' % errors[0])
    return _finish(out)
