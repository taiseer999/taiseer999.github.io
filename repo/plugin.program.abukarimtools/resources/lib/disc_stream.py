# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""
disc_stream.py - ABUKARIM TOOLS (4.8.79)

Whole Blu-ray discs (.iso images) from a stream link - Debrid, TorBox,
Usenet through AIOStreams - played as discs: menus, chapters, languages,
subtitles, without downloading the image first.

Two parts, both behind Toggles > "AF3: Disc Menu for ISO Streams"
(skin bool abk.discmenu):

1. The disc server (service.py, one per Kodi session, 127.0.0.1 only).
   open_image(link) reads the image's UDF file system over a few ranged
   reads (disc_udf.py), remembers the disc in addon_data, and Kodi opens
     bluray://<http://127.0.0.1:<port>/abkdisc/<key>/>/menu
   Kodi's Blu-ray reader (libbluray) then asks this server for index.bdmv,
   the playlists and clip files, and the streams as it plays them; each
   request becomes the same range of the image link. Nothing is cached on
   disk, nothing is fetched that Kodi does not read.

2. The rescue (Player callbacks in the service). A disc image behind a link
   with no .iso in it (debrid / AIOStreams resolver links) is handed by Kodi
   to FFmpeg, which cannot read a disc, and playback fails. When a stream
   that may be a disc fails to start, its first bytes are checked for the
   ISO 9660 / UDF volume marks; a disc is opened again as a disc:
     CoreELEC / LibreELEC  udf://<link>/BDMV/index.bdmv  (Kodi reads it itself;
                           Java menus with "JRE for BD-J menus", disc_menu.py)
     other systems         through the disc server above (Kodi on the Mac
                           hangs on a streamed udf:// image)

Java (BD-J) menus need Java in Kodi: only CoreELEC / LibreELEC have it
(tools.jre.zulu). Elsewhere a disc with Java titles opens on its main movie
(the longest playlist) - opening its menu would stop at the first Java title.
Kodi's own Settings > Player > Discs > "Blu-ray playback mode" = Play main
movie is followed everywhere.
"""
import hashlib
import html
import json
import os
import re
import struct
import threading
import time
import urllib.parse
import urllib.request

import xbmc
import xbmcgui
import xbmcvfs

HOST = '127.0.0.1'
PATH_MARK = 'abkdisc'                         # in every served path (skin visibility)
PORT_PROP = 'abk.disc.port'
SOURCE_PROP = 'abk.disc.source'               # image link of the disc playing now
BUSY_PROP = 'abk.disc.busy'                   # a disc is being opened (Search All waits)
SETTING = 'abk.discmenu'
KEEP_FOR = 24 * 3600
_KODI_SAFE = '-._!()'                         # what URIUtils::URLEncode leaves alone
_VIDEO_EXT = ('.mkv', '.mp4', '.m4v', '.avi', '.m2ts', '.mts', '.ts', '.mov', '.webm', '.wmv',
              '.mpg', '.mpeg', '.flv', '.m3u8', '.mpd', '.strm', '.mp3', '.flac', '.aac')
_DISC_MARKS = (b'CD001', b'BEA01', b'NSR02', b'NSR03', b'BOOT2', b'TEA01')
_PLAYLIST = re.compile(r'^\d{5}\.mpls$', re.I)
_MAIN_TITLE = 2                               # Kodi disc.playback: Play main movie

_lock = threading.Lock()
_server = [None]
_registry = {'mtime': -1, 'data': {}}


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Disc] %s' % msg, level)


def _home():
    return xbmcgui.Window(10000)


def enabled():
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING))


def kodi_encode(text):
    """Kodi's URIUtils::URLEncode (how a URL nested in bluray:// / udf:// is written)."""
    out = []
    for b in text.encode('utf-8'):
        c = chr(b)
        out.append(c if c.isascii() and (c.isalnum() or c in _KODI_SAFE) else '%%%02x' % b)
    return ''.join(out)


def on_coreelec():
    try:
        with open('/etc/os-release', encoding='utf-8') as f:
            text = f.read().lower()
        return 'coreelec' in text or 'libreelec' in text
    except Exception:
        return False


def _data_file():
    folder = xbmcvfs.translatePath('special://profile/addon_data/plugin.program.abukarimtools/')
    return os.path.join(folder, 'disc_streams.json')


# ───────────────────────── links ─────────────────────────

def split_link(link):
    """'url|Header=value&...' (Kodi's form) -> (url, headers)."""
    url, _sep, extra = str(link or '').partition('|')
    headers = {'User-Agent': 'Kodi'}
    for pair in extra.split('&') if extra else []:
        name, _eq, value = pair.partition('=')
        if name:
            headers[urllib.parse.unquote(name)] = urllib.parse.unquote(value)
    return url, headers


def _open_range(link, start, length, timeout=30):
    url, headers = split_link(link)
    headers['Range'] = 'bytes=%d-%d' % (start, start + length - 1)
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)


def read_range(link, start, length, timeout=30):
    with _open_range(link, start, length, timeout) as r:
        if r.status != 206:
            raise IOError('the link does not answer ranges (HTTP %d)' % r.status)
        return r.read(length)


def maybe_disc(path):
    """Cheap test before any network: an http link that is not plainly a video file."""
    p = str(path or '')
    low = p.lower()
    if not low.startswith(('http://', 'https://')) or ('/%s/' % PATH_MARK) in low:
        return False                                  # not a stream, or our own disc server
    bare = urllib.parse.urlsplit(p.split('|', 1)[0]).path.lower()
    return not bare.endswith(_VIDEO_EXT)


def probe(link, waits=(45, 30)):
    """(final link, image size) when the link is a disc image, else None.
    Sector 16 holds the ISO 9660 / UDF volume recognition marks. Usenet links
    from AIOStreams answer only once the file is ready - one more wait then."""
    url, headers = split_link(link)
    extra = link.split('|', 1)[1] if '|' in str(link) else ''
    for timeout in waits:
        req = urllib.request.Request(url, headers=dict(headers, Range='bytes=32768-34815'))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                head = r.read(2048)
                final = r.geturl() or url
                named = r.headers.get('Content-Disposition') or ''
                total = str(r.headers.get('Content-Range') or '').rsplit('/', 1)[-1]
                status = r.status
            break
        except Exception as e:
            _log('probe: %s' % e, xbmc.LOGWARNING)
            if 'timed out' not in str(e).lower() or xbmc.Monitor().abortRequested():
                return None
    else:
        return None
    if status != 206:
        return None
    is_disc = any(m in head[:16] for m in _DISC_MARKS) or re.search(r'\.(?:iso|img)\b', named, re.I)
    if not is_disc:
        return None
    size = int(total) if total.isdigit() else 0
    return (final + ('|' + extra if extra else '')), size


# ───────────────────────── Blu-ray structures ─────────────────────────

def has_java(index):
    """index.bdmv: does First Play, Top Menu or any title run a BD-J object?
    (BD spec: Indexes() at the address in bytes 8-11 - length, FirstPlayback,
    TopMenu, number_of_Titles, titles; object type in the top 2 bits, 2 = BD-J.)
    Unreadable -> True (the main movie is the safe choice)."""
    try:
        if index[:4] != b'INDX':
            return True
        at = struct.unpack_from('>I', index, 8)[0] + 4
        kinds = [index[at] >> 6, index[at + 12] >> 6]
        titles = struct.unpack_from('>H', index, at + 24)[0]
        kinds += [index[at + 26 + 12 * n] >> 6 for n in range(titles)]
        return 2 in kinds
    except Exception:
        return True


def playlist_seconds(mpls):
    """A .mpls playlist's length: sum of OUT-IN of its play items (45 kHz)."""
    try:
        if mpls[:4] != b'MPLS':
            return 0.0
        at = struct.unpack_from('>I', mpls, 8)[0]
        count = struct.unpack_from('>H', mpls, at + 6)[0]
        at += 10
        ticks = 0
        for _ in range(count):
            size = struct.unpack_from('>H', mpls, at)[0]
            # PlayItem: name 5, codec 4, flags 2, STC id 1, IN 4, OUT 4
            t_in, t_out = struct.unpack_from('>II', mpls, at + 2 + 12)
            if t_out > t_in:
                ticks += t_out - t_in
            at += 2 + size
        return ticks / 45000.0
    except Exception:
        return 0.0


def main_playlist(names, fetch):
    """The longest of the disc's playlists (Kodi's own idea of the main movie)."""
    best, best_len = '', 0.0
    for name in sorted(n for n in names if _PLAYLIST.match(n))[:300]:
        try:
            length = playlist_seconds(fetch(name))
        except Exception:
            length = 0.0
        if length > best_len:
            best, best_len = name, length
    return best, best_len


def kodi_disc_mode():
    """Kodi's Settings > Player > Discs > Blu-ray playback mode (disc.playback)."""
    try:
        q = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.GetSettingValue',
             'params': {'setting': 'disc.playback'}}
        return int(json.loads(xbmc.executeJSONRPC(json.dumps(q)))['result']['value'])
    except Exception:
        return None


# ───────────────────────── the registry (plugin call <-> service) ─────────────────────────

def _load():
    path = _data_file()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    with _lock:
        if mtime != _registry['mtime']:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                _registry['data'] = data if isinstance(data, dict) else {}
            except Exception:
                _registry['data'] = {}
            _registry['mtime'] = mtime
        return _registry['data']


def _remember(key, disc):
    now = time.time()
    data = {k: v for k, v in dict(_load()).items()
            if isinstance(v, dict) and now - float(v.get('at') or 0) < KEEP_FOR}
    data[key] = dict(disc, at=int(now))
    path = _data_file()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(data, f)
        os.replace(path + '.tmp', path)
    except Exception as e:
        _log('disc not remembered: %s' % e, xbmc.LOGWARNING)


def disc_for(key):
    return _load().get(key)


def key_of(path):
    """The disc key in a served path (bluray://http%3a%2f%2f127.0.0.1...abkdisc%2fKEY...)."""
    p = urllib.parse.unquote(urllib.parse.unquote(str(path or '')))
    m = re.search(r'/%s/([0-9a-f]{12})/' % PATH_MARK, p)
    return m.group(1) if m else ''


# ───────────────────────── opening a disc ─────────────────────────

def port():
    try:
        return int(_home().getProperty(PORT_PROP) or 0)
    except ValueError:
        return 0


def open_image(link, size=0):
    """Read the image's file system and remember it. Returns
    {'key', 'base' (bluray://.../, ends with '/'), 'java', 'main' (.mpls or '')}
    or None (no server, not a Blu-ray image, or the link gives no ranges)."""
    number = port()
    if not number:
        _log('the disc server is not running', xbmc.LOGWARNING)
        return None
    if not size:
        found = probe(link, waits=(30,))
        if not found:
            return None
        link, size = found
    if size <= 0:
        return None
    from resources.lib import disc_udf
    started = time.time()
    try:
        image = disc_udf.Image(lambda off, n: read_range(link, off, n), size).open()
        files = image.disc_files()
    except Exception as e:
        _log('image not read as a Blu-ray disc: %s' % e, xbmc.LOGWARNING)
        return None
    key = hashlib.sha1(link.split('|', 1)[0].encode('utf-8')).hexdigest()[:12]
    lower = {k.lower(): v for k, v in files.items()}

    def small(rel):
        entry = lower.get(rel.lower())
        return disc_udf.file_bytes(image, entry) if entry and not entry.get('dir') else b''

    try:
        java = has_java(small('BDMV/index.bdmv'))
    except Exception:
        java = True
    names = [k.rsplit('/', 1)[-1] for k in files if k.lower().startswith('bdmv/playlist/')]
    main, seconds = main_playlist(names, lambda n: small('BDMV/PLAYLIST/' + n))
    _remember(key, {'link': link, 'size': size, 'files': files, 'java': java, 'main': main})
    base = 'bluray://%s/' % kodi_encode('http://%s:%d/%s/%s/' % (HOST, number, PATH_MARK, key))
    _log('disc image: %d files in %.1fs (%d reads), %s menus, main %s (%.0f min)'
         % (len(files), time.time() - started, image.reads, 'Java' if java else 'HDMV',
            main or '?', seconds / 60.0))
    return {'key': key, 'base': base, 'java': java, 'main': main, 'link': link}


def remember_debrid(source, code, files, java, main):
    """disc_debrid: a disc folder from a debrid torrent; each file is a redirect
    to its debrid link (files[rel]['url'], else resolved when Kodi asks)."""
    key = hashlib.sha1(source.encode('utf-8')).hexdigest()[:12]
    _remember(key, {'kind': 'debrid', 'svc': code, 'link': source, 'files': files,
                    'java': java, 'main': main})
    return key


def disc_info(key):
    """An opened disc again, by its key (the OSD buttons while it plays)."""
    disc = disc_for(key)
    number = port()
    if not disc or not number:
        return None
    base = 'bluray://%s/' % kodi_encode('http://%s:%d/%s/%s/' % (HOST, number, PATH_MARK, key))
    return {'key': key, 'base': base, 'java': disc.get('java', True), 'main': disc.get('main') or '',
            'link': disc.get('link') or ''}


def disc_path(disc, menu=None):
    """The bluray:// path to play for an opened disc: its menu, or its main movie
    when Kodi is set to Play main movie / the menus are Java without Java here."""
    if menu is None:
        menu = kodi_disc_mode() != _MAIN_TITLE and (on_coreelec() or not disc['java'])
    if menu or not disc.get('main'):
        return disc['base'] + 'menu', 'menu'
    return disc['base'] + 'BDMV/PLAYLIST/' + disc['main'], 'main movie'


def udf_path(link):
    """CoreELEC / LibreELEC: Kodi reads the streamed image itself."""
    return 'udf://%s/BDMV/index.bdmv' % kodi_encode(link.split('|', 1)[0])


# ───────────────────────── the server ─────────────────────────

def _handler():
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_HEAD(self):
            self._serve(True)

        def do_GET(self):
            self._serve(False)

        def _plain(self, code, body=b'', ctype='text/html; charset=utf-8', head=False):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if body and not head:
                self.wfile.write(body)

        def _serve(self, head):
            parts = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip('/').split('/', 2)
            if len(parts) < 2 or parts[0] != PATH_MARK:
                return self._plain(404, head=head)
            disc = disc_for(parts[1])
            if not disc:
                return self._plain(404, head=head)
            files = disc.get('files') or {}
            name = parts[2] if len(parts) > 2 else ''
            entry = files.get(name)
            if entry is None:                               # Kodi may change the case
                for k, v in files.items():
                    if k.lower() == name.lower():
                        name, entry = k, v
                        break
            if entry is not None and not entry.get('dir'):
                if disc.get('kind') == 'debrid':
                    return self._redirect(disc, entry, head)
                return self._file(disc, entry, head)
            prefix = name if not name or name.endswith('/') else name + '/'
            kids = set()
            for k in files:
                if k.startswith(prefix) and k != prefix:
                    rest = k[len(prefix):]
                    kids.add(rest.split('/', 1)[0] + ('/' if '/' in rest else ''))
            if not kids:
                return self._plain(404, head=head)
            page = ('<html><head><title>Index of /%s</title></head><body><pre>\n' % html.escape(prefix)
                    + ''.join('<a href="%s">%s</a>\n' % (urllib.parse.quote(k), html.escape(k))
                              for k in sorted(kids))
                    + '</pre></body></html>\n').encode('utf-8')
            return self._plain(200, page, head=head)

        def _redirect(self, disc, entry, head):
            url = entry.get('url') or ''
            if not url:
                try:
                    from resources.lib import disc_debrid
                    url = disc_debrid.resolve(disc.get('svc'), entry.get('ref'))
                except Exception as e:
                    _log('debrid link: %s' % e, xbmc.LOGWARNING)
                    return self._plain(502, head=head)
            self.send_response(302)
            self.send_header('Location', url)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def _file(self, disc, entry, head):
            size = int(entry.get('size') or 0)
            first, last, partial = 0, size - 1, False
            want = str(self.headers.get('Range') or '').strip()
            if want.startswith('bytes=') and ',' not in want:
                lo, _d, hi = want[6:].partition('-')
                try:
                    if lo.strip():
                        first = int(lo)
                        last = min(int(hi), size - 1) if hi.strip() else size - 1
                    elif hi.strip():
                        first, last = max(0, size - int(hi)), size - 1
                    partial = True
                except ValueError:
                    first, last, partial = 0, size - 1, False
            if size and first > last:
                self.send_response(416)
                self.send_header('Content-Range', 'bytes */%d' % size)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            self.send_response(206 if partial else 200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(max(0, last - first + 1)))
            if partial:
                self.send_header('Content-Range', 'bytes %d-%d/%d' % (first, last, size))
            self.end_headers()
            if head or size <= 0:
                return
            if entry.get('data') is not None:
                self.wfile.write(bytes.fromhex(entry['data'])[first:last + 1])
                return
            pos = 0                                           # file offset of this extent
            try:
                for offset, length in entry.get('x') or []:
                    lo, hi = max(first, pos), min(last, pos + length - 1)
                    if lo <= hi:
                        if offset < 0:
                            self.wfile.write(b'\0' * (hi - lo + 1))
                        else:
                            with _open_range(disc['link'], offset + lo - pos, hi - lo + 1, 60) as r:
                                while True:
                                    block = r.read(256 * 1024)
                                    if not block:
                                        break
                                    self.wfile.write(block)
                    pos += length
                    if pos > last:
                        break
            except (BrokenPipeError, ConnectionResetError):
                pass                                          # Kodi seeked / stopped
            except Exception as e:
                _log('read failed: %s' % e, xbmc.LOGWARNING)
                self.close_connection = True

    return Handler


def start_server():
    if _server[0] is not None:
        return True
    try:
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer((HOST, 0), _handler())
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, name='abk-disc-server', daemon=True).start()
        _server[0] = srv
        _home().setProperty(PORT_PROP, str(srv.server_address[1]))
        _log('disc server on %s:%d' % (HOST, srv.server_address[1]))
        return True
    except Exception as e:
        _log('disc server not started: %s' % e, xbmc.LOGERROR)
        return False


def stop_server():
    srv = _server[0]
    _server[0] = None
    _home().clearProperty(PORT_PROP)
    if srv is not None:
        try:
            srv.shutdown()
            srv.server_close()
        except Exception:
            pass


# ───────────────────────── the rescue ─────────────────────────

_RESCUE_WINDOW = 25.0          # s from start to failure that counts as "would not open"


class _Rescue(xbmc.Player):

    def __init__(self):
        super().__init__()
        self.path = ''
        self.started = 0.0
        self.av = False
        self.item = None
        self.busy = False

    def _remember_item(self, path):
        try:
            from resources.lib import disc_menu
            self.item = disc_menu._listitem(path, chosen=False)
        except Exception:
            self.item = None

    def onPlayBackStarted(self):
        try:
            path = self.getPlayingFile() or ''
        except Exception:
            path = ''
        if not path:
            path = _last_opened_from_log()
        self.path, self.started, self.av = path, time.time(), False
        if path and key_of(path) == '' and not path.lower().startswith(('udf://', 'bluray://')):
            if _home().getProperty(SOURCE_PROP) and path.split('|', 1)[0] != \
                    _home().getProperty(SOURCE_PROP).split('|', 1)[0]:
                _home().clearProperty(SOURCE_PROP)           # another file: no disc now
        if self.path and enabled() and maybe_disc(self.path):
            self._remember_item(self.path)
        _clear_old_source_badge(path)

    def onAVStarted(self):
        self.av = True
        try:
            path = self.getPlayingFile()
        except Exception:
            path = ''
        try:
            from resources.lib import disc_debrid
            disc_debrid.bind_playing(path)
        except Exception as e:
            _log('disc pick: %s' % e, xbmc.LOGWARNING)
        _source_badge_fallback(path)
        try:
            from resources.lib import stream_badges      # 4.9.9: bit depth / container / multi audio
            stream_badges.started(path)
        except Exception as e:
            _log('stream badges: %s' % e, xbmc.LOGWARNING)
        try:
            _explain_disc_button(path)
        except Exception:
            pass

    def onPlayBackError(self):
        self._failed('error')

    def onPlayBackStopped(self):
        self.path, self.item = '', None            # the user stopped it: never reopen
        _clear_stream_badges()

    def onPlayBackEnded(self):
        _clear_stream_badges()
        self._failed('ended')

    def _failed(self, how):
        path, self.path = self.path, ''
        if self.av or not path or self.busy:
            return
        if time.time() - self.started > _RESCUE_WINDOW or not enabled() or not maybe_disc(path):
            return
        item, self.item = self.item, None
        self.busy = True
        threading.Thread(target=self._reopen, args=(path, item, how),
                         name='abk-disc-rescue', daemon=True).start()

    def _reopen(self, link, item, how):
        home = _home()
        home.setProperty(BUSY_PROP, '1')
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            found = probe(link)
            if not found:
                _log('%s link (%s) is not a disc image - left alone' % (how, link.split('|', 1)[0][:80]))
                return
            final, size = found
            if on_coreelec():
                try:
                    from resources.lib import disc_menu
                    xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)')
                    disc_menu._ensure_jre()
                except Exception as e:
                    _log('Java check: %s' % e, xbmc.LOGWARNING)
                path, what = udf_path(final), 'udf'
            else:
                disc = open_image(final, size)
                if not disc:
                    return
                path, what = disc_path(disc)
            home.setProperty(SOURCE_PROP, final)
            _log('a Blu-ray image would not play (%s) - opening it as a disc (%s)' % (how, what))
            from resources.lib.i18n import T
            xbmcgui.Dialog().notification('ABUKARIM TOOLS', T(32269), xbmcgui.NOTIFICATION_INFO, 3000)
            li = item if item is not None else xbmcgui.ListItem(path=path, offscreen=True)
            li.setPath(path)
            if what != 'udf':
                li.setProperty('playlist_chosen', 'true')
            xbmc.Player().play(path, li)
        except Exception as e:
            _log('rescue failed: %s' % e, xbmc.LOGWARNING)
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)')
            home.clearProperty(BUSY_PROP)
            self.busy = False


def _clear_stream_badges():
    try:
        from resources.lib import stream_badges
        stream_badges.clear()
    except Exception:
        pass


def _clear_old_source_badge(path):
    """4.8.85: abk.lp.src (Search All pick's release type) belongs to the file
    that pick starts - drop it when something else plays (a disc reopened from
    that pick keeps it)."""
    home = _home()
    if not home.getProperty('abk.lp.src'):
        return
    low = str(path or '').lower()
    if low.startswith(('bluray://', 'udf://')) or ('/%s/' % PATH_MARK) in low:
        return
    try:
        age = time.time() - float(home.getProperty('abk.lp.src.ts') or 0)
    except ValueError:
        age = 1e9
    if age > 180:
        home.clearProperty('abk.lp.src')
        home.clearProperty('abk.lp.src.ts')
        home.clearProperty('abk.lp.imax')


def _source_badge_fallback(path):
    """4.8.87: no Search All pick to name the release type - the file type
    does: a Blu-ray stream (.m2ts, bluray://) is BLURAY, a disc image ISO."""
    home = _home()
    if home.getProperty('abk.lp.src'):
        return
    low = str(path or '').lower().split('|', 1)[0]
    bare = urllib.parse.urlsplit(low).path if low.startswith('http') else low
    src = ''
    if low.startswith('udf://') or bare.endswith('.iso'):
        src = 'ISO'
    elif low.startswith('bluray://') or bare.endswith(('.m2ts', '.mts')):
        src = 'BLURAY'
    if src:
        home.setProperty('abk.lp.src', src)
        home.setProperty('abk.lp.src.ts', str(int(time.time())))


def _explain_disc_button(path):
    """4.8.85: one log line saying why the AF3 Disc Menu button is (not) shown
    for an http .m2ts / .iso (the skin evaluates the same conditions)."""
    low = str(path or '').lower().split('|', 1)[0]
    if not low.startswith('http') or not (low.endswith('.m2ts') or '.iso' in low or PATH_MARK in low):
        return
    cond = xbmc.getCondVisibility
    parts = {'toggle on': cond('Skin.HasSetting(abk.discmenu)'),
             'disc pick': bool(_home().getProperty('abk.disc.pick')),
             'iso path': '.iso' in low,
             'skin buttons v5': _skin_has_buttons()}
    _log('Disc Menu button for %s: %s' % (low.rsplit('/', 1)[-1][:60],
                                         ', '.join('%s=%s' % kv for kv in parts.items())))


def _skin_has_buttons():
    try:
        p = xbmcvfs.translatePath('special://skin/1080i/VideoOSD.xml')
        with open(p, 'r', encoding='utf-8') as f:
            return '<!-- ABUKARIM: AF3 disc menu buttons v5 -->' in f.read()
    except Exception:
        return None


def _last_opened_from_log():
    """The file Kodi's VideoPlayer opened last, from the end of kodi.log - for a
    link that failed before Python could ask the player for it."""
    try:
        path = xbmcvfs.translatePath('special://logpath/kodi.log')
        with open(path, 'rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 65536))
            tail = f.read().decode('utf-8', 'replace')
        found = re.findall(r'VideoPlayer::OpenFile: (\S+)', tail)
        return found[-1] if found else ''
    except Exception:
        return ''


_players = []


def start(monitor=None):
    """service.py: the disc server and the rescue, for the rest of the session."""
    start_server()
    if not _players:
        _players.append(_Rescue())
    _log('disc streams ready (rescue %s)' % ('on' if enabled() else 'off until the toggle is on'))
