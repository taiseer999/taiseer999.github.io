# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""AB Tools "Seek Preview" (rewritten for AB Tools in 4.12.0).

While the viewer skips forward or back, a glass card above the seek bar shows
a picture of the spot being skipped to, with its time. Pictures come from
grabber.py (ffmpeg); this module watches the player, chooses what to make and
draws the card.

  - one thread of the AB Tools service, started at boot, idle while off;
  - settings: addon_data/plugin.program.abukarimtools/seek_preview.json,
    set from Toggles > Seek Preview, read again whenever the file changes;
  - "frames ahead": off / local files whole, streams 3 min each way /
    always, streams 10 min each way;
  - only the picture of the skip target (or one step beside it) is shown,
    else a waiting picture;
  - Kodi's own skip settings are never changed, and no address of the
    playing video is written to kodi.log.

ffmpeg comes from CoreELEC's "FFmpeg Tools" add-on (tools.ffmpeg-tools), a
Homebrew / MacPorts install, or the PATH.
"""
import hashlib
import json
import os
import re
import shutil
import socket
import threading
import time
from urllib.parse import unquote_plus

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import paths
from resources.lib.seek_preview import grabber

PROFILE = xbmcvfs.translatePath('special://profile/addon_data/plugin.program.abukarimtools/')
CONFIG = os.path.join(PROFILE, 'seek_preview.json')
DISK = xbmcvfs.translatePath('special://temp/abk_seekpreview')
RAM = '/tmp/abk_seekpreview' if (os.path.isdir('/tmp') and not grabber.IS_WINDOWS) else DISK
MEDIA = os.path.join(paths.ADDON_PATH, 'resources', 'seek_preview', 'media')
WAIT_IMG = os.path.join(MEDIA, 'wait.png')

CANDIDATES = (
    'special://home/addons/tools.ffmpeg-tools/bin/ffmpeg',
    '/usr/lib/kodi/addons/tools.ffmpeg-tools/bin/ffmpeg',
    '/opt/homebrew/bin/ffmpeg',          # Kodi.app on macOS has no shell PATH
    '/usr/local/bin/ffmpeg',
    '/opt/local/bin/ffmpeg',
)

DEFAULTS = {'enabled': False, 'size': 1, 'ahead': 1, 'hidesubs': True, 'step': 10}
STEPS = (5, 10, 15, 30)

# The card, in 1280x720 skin units: picture sizes (small / medium / large),
# the padding around the picture and the time row under it.
CARD_SIZES = ((240, 135), (320, 180), (426, 240))
CARD_NAMES = ('s', 'm', 'l')
CARD_PAD = 8
CARD_TIME_H = 30
CARD_GAP = 10
GRAB_WIDTH = 426                        # pictures are made once, at the largest size
# where the seek bar is: x range and the line the card sits above (OSD closed / open)
BAR_LUCENT = (64, 1216, 585, 556)       # AF3 with Lucent Player (bar 96..1824 at 1080p)
BAR_OTHER = (64, 1216, 570, 510)

FOCUS_HOLD = 30                         # s: prefetch stays around the last skip target
MIN_FREE = 250 << 20
SPAN_NEAR, SPAN_FAR = 180, 600

STOP = threading.Event()
_WORKER = {'thread': None}


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SeekPreview] %s' % msg, level)


# ---------------------------------------------------------------------- settings
def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG, 'r', encoding='utf-8') as fh:
            saved = json.load(fh)
        for k in DEFAULTS:
            if isinstance(saved, dict) and k in saved:
                cfg[k] = saved[k]
    except Exception:
        pass

    def clamp(v, lo, hi, fallback):
        try:
            return max(lo, min(hi, int(v)))
        except Exception:
            return fallback
    cfg['enabled'] = bool(cfg['enabled'])
    cfg['hidesubs'] = bool(cfg['hidesubs'])
    cfg['size'] = clamp(cfg['size'], 0, 2, DEFAULTS['size'])
    cfg['ahead'] = clamp(cfg['ahead'], 0, 2, DEFAULTS['ahead'])
    step = clamp(cfg['step'], 0, 999, DEFAULTS['step'])
    cfg['step'] = step if step in STEPS else DEFAULTS['step']
    return cfg


def save_config(cfg):
    os.makedirs(PROFILE, exist_ok=True)
    data = dict((k, cfg.get(k, DEFAULTS[k])) for k in DEFAULTS)
    part = CONFIG + '.part'
    with open(part, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1)
    os.replace(part, CONFIG)


def find_ffmpeg():
    """(path, 'tools.ffmpeg-tools' | 'system') of a working ffmpeg, or ('', '')."""
    seen = []
    for c in CANDIDATES + (shutil.which('ffmpeg') or '',):
        p = xbmcvfs.translatePath(c) if c.startswith('special://') else c
        if not p or p in seen:
            continue
        seen.append(p)
        if os.path.isfile(p) and grabber.ffmpeg_ok(p):
            return p, ('tools.ffmpeg-tools' if 'ffmpeg-tools' in p else 'system')
    return '', ''


# ---------------------------------------------------------------------- reading the video
class _LocalServer(object):
    """Serves Kodi-only paths (smb://, nfs://, ...) to ffmpeg over http://127.0.0.1,
    reading them through xbmcvfs, with byte ranges so ffmpeg can seek."""

    def __init__(self):
        self.port = 0
        self.paths = {}
        self._sock = None

    def address(self, kodi_path):
        if not self.port:
            self._open()
        key = hashlib.sha1(kodi_path.encode('utf-8', 'replace')).hexdigest()[:24]
        self.paths[key] = kodi_path
        return 'http://127.0.0.1:%d/%s' % (self.port, key)

    def _open(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 0))
        s.listen(8)
        s.settimeout(0.5)
        self._sock, self.port = s, s.getsockname()[1]
        th = threading.Thread(target=self._accept, name='abk-seekpreview-files')
        th.daemon = True
        th.start()

    def _accept(self):
        while not STOP.is_set():
            try:
                conn, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            th = threading.Thread(target=self._answer, args=(conn,), name='abk-seekpreview-file')
            th.daemon = True
            th.start()

    def _answer(self, conn):
        try:
            conn.settimeout(30)
            head = b''
            while b'\r\n\r\n' not in head and len(head) < 16384:
                got = conn.recv(4096)
                if not got:
                    return
                head += got
            lines = head.split(b'\r\n')
            parts = lines[0].decode('latin-1').split(' ')
            key = parts[1].strip('/') if len(parts) > 1 else ''
            rng = ''
            for ln in lines[1:]:
                name, _, val = ln.decode('latin-1').partition(':')
                if name.strip().lower() == 'range':
                    rng = val.strip()
            path = self.paths.get(key)
            if not path:
                conn.sendall(b'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
                return
            self._send(conn, path, rng)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @staticmethod
    def _send(conn, path, rng):
        fh = xbmcvfs.File(path)
        try:
            total = fh.size()
            m = re.match(r'bytes=(\d*)-(\d*)$', rng)
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    first = int(m.group(1))
                    last = int(m.group(2)) if m.group(2) else total - 1
                else:                               # "bytes=-N": the last N bytes
                    first, last = max(0, total - int(m.group(2))), total - 1
                last = min(last, total - 1)
                status = '206 Partial Content'
                extra = 'Content-Range: bytes %d-%d/%d\r\n' % (first, last, total)
            else:
                first, last, status, extra = 0, total - 1, '200 OK', ''
            length = max(0, last - first + 1)
            conn.sendall(('HTTP/1.1 %s\r\nAccept-Ranges: bytes\r\nContent-Length: %d\r\n%s'
                          'Connection: close\r\n\r\n' % (status, length, extra)).encode('latin-1'))
            fh.seek(first, 0)
            while length > 0 and not STOP.is_set():
                chunk = fh.readBytes(min(1 << 18, length))
                if not chunk:
                    break
                conn.sendall(bytes(chunk))
                length -= len(chunk)
        finally:
            fh.close()

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


FILES = _LocalServer()


def video_input(playing):
    """Kodi's playing path -> (ffmpeg input, ffmpeg -headers text, streamed?).
    The input is None when ffmpeg cannot read it (discs, live TV, DRM)."""
    url, _, options = playing.partition('|')
    if url.startswith(('http://', 'https://')):
        headers = []
        for pair in options.split('&'):
            if '=' in pair:
                name, value = pair.split('=', 1)
                headers.append('%s: %s\r\n' % (unquote_plus(name), unquote_plus(value)))
        return url, ''.join(headers), True
    if os.path.isfile(url):
        return url, '', False
    if re.match(r'(smb|nfs|ftp|sftp|dav|davs|upnp|special|zip|rar)://', url) and xbmcvfs.exists(url):
        return FILES.address(url), '', False
    return None, '', False


# ---------------------------------------------------------------------- the card
def _bar():
    if (xbmc.getSkinDir() == 'skin.arctic.fuse.3'
            and xbmc.getCondVisibility('Skin.HasSetting(abk.lucentplayer)')):
        return BAR_LUCENT
    return BAR_OTHER


def card_position(fraction, size, osd_open):
    """Top-left corner of the card, centred over ``fraction`` of the seek bar."""
    w, h = CARD_SIZES[size]
    card_w, card_h = w + 2 * CARD_PAD, h + 2 * CARD_PAD + CARD_TIME_H
    left, right, base_closed, base_open = _bar()
    fraction = min(1.0, max(0.0, fraction))
    x = int(left + fraction * (right - left) - card_w / 2.0)
    x = min(max(x, left), right - card_w)
    y = (base_open if osd_open else base_closed) - CARD_GAP - card_h
    return x, max(4, y)


class Card(object):
    """The glass card: background, picture, rounded-corner mask, time label."""

    def __init__(self):
        self.window = None
        self.size = None
        self.image = ''

    def show(self, image, label, fraction, size, osd_open):
        if self.window is not None and size != self.size:
            self.hide()
        w, h = CARD_SIZES[size]
        x, y = card_position(fraction, size, osd_open)
        if self.window is None:
            name = CARD_NAMES[size]
            win = xbmcgui.WindowDialog()
            self.back = xbmcgui.ControlImage(x, y, w + 2 * CARD_PAD, h + 2 * CARD_PAD + CARD_TIME_H,
                                             os.path.join(MEDIA, 'card_%s.png' % name))
            self.pic = xbmcgui.ControlImage(x + CARD_PAD, y + CARD_PAD, w, h, image, aspectRatio=0)
            self.mask = xbmcgui.ControlImage(x + CARD_PAD, y + CARD_PAD, w, h,
                                             os.path.join(MEDIA, 'corners_%s.png' % name))
            self.time = xbmcgui.ControlLabel(x + CARD_PAD, y + CARD_PAD + h + 2, w, CARD_TIME_H - 4,
                                             label, font='font13', textColor='FFFFFFFF',
                                             alignment=0x00000002 | 0x00000004)
            win.addControls([self.back, self.pic, self.mask, self.time])
            win.show()
            self.window, self.size, self.image = win, size, image
            return
        self.back.setPosition(x, y)
        self.pic.setPosition(x + CARD_PAD, y + CARD_PAD)
        self.mask.setPosition(x + CARD_PAD, y + CARD_PAD)
        self.time.setPosition(x + CARD_PAD, y + CARD_PAD + h + 2)
        if image != self.image:
            self.pic.setImage(image, False)
            self.image = image
        self.time.setLabel(label)

    def hide(self):
        if self.window is not None:
            try:
                self.window.close()
            except Exception:
                pass
        self.window, self.image = None, ''


# ---------------------------------------------------------------------- diagnostics
def _scrub(text):
    text = re.sub(r'(?:https?|smb|nfs)://\S+', '<url>', text)
    return re.sub(r'(bearer|token|apikey|api_key)([=: +]+)\S+', r'\1 ***', text, flags=re.I)


def _make_reporter():
    state = {'lowmem': False, 'fails': 0}

    def report(kind, text):
        if kind == 'lowmem':
            if state['lowmem']:
                return
            state['lowmem'] = True
        elif kind == 'fail':
            state['fails'] += 1
            if state['fails'] > 3:
                return                      # the total is in "video done"
        flat = ' | '.join(r.strip() for r in _scrub(text).splitlines() if r.strip())
        _log('%s: %s' % (kind, flat), xbmc.LOGWARNING if kind in ('fail', 'lowmem') else xbmc.LOGINFO)
    return report


def _seconds(label):
    try:
        total = 0
        for piece in label.strip().split(':'):
            total = total * 60 + int(piece)
        return total
    except Exception:
        return -1


# ---------------------------------------------------------------------- the watcher
class _Watcher(object):
    def __init__(self, monitor):
        self.monitor = monitor
        self.player = xbmc.Player()
        self.card = Card()
        self.cfg = load_config()
        self.cfg_stamp = self._stamp()
        self.ffmpeg = ''
        self.looked_for_ffmpeg = False
        self.grab = None
        self.playing = None
        self.last_shown = 0.0
        self.subs_hidden = False
        self.target, self.target_at = 0, 0.0
        self._check_ffmpeg()

    @staticmethod
    def _stamp():
        try:
            return os.path.getmtime(CONFIG)
        except OSError:
            return None

    def _check_ffmpeg(self):
        if self.cfg['enabled'] and not self.looked_for_ffmpeg:
            self.looked_for_ffmpeg = True
            self.ffmpeg, where = find_ffmpeg()
            if self.ffmpeg:
                _log('ffmpeg: %s (%s)' % (self.ffmpeg, where))
            else:
                _log('ffmpeg: none found (install FFmpeg Tools) - no previews', xbmc.LOGWARNING)

    def _end_video(self):
        if self.grab:
            self.grab.stop()
            _log('video done: %d pictures made, %d failed' % (self.grab.made, self.grab.failed))
        self.grab = None

    def _hide(self):
        self.card.hide()
        self.last_shown = 0.0
        if self.subs_hidden:
            self.subs_hidden = False
            try:
                self.player.showSubtitles(True)
            except Exception:
                pass

    def _new_video(self, playing):
        self._end_video()
        self._hide()
        self.playing = playing
        if not playing or playing.endswith('dummy.mp4'):
            return
        src, headers, streamed = video_input(playing)
        if not src:
            _log('no preview for this video (disc, live TV, DRM or unknown source)')
            return
        cfg = self.cfg
        key = hashlib.sha1(('%d|%d|%s' % (GRAB_WIDTH, cfg['step'], playing.partition('|')[0]))
                           .encode('utf-8', 'replace')).hexdigest()[:16]
        ahead = cfg['ahead'] > 0
        span = SPAN_FAR if cfg['ahead'] == 2 else SPAN_NEAR
        slots = ((3 if cfg['ahead'] == 2 else 2) if streamed else 1) if ahead else 0
        grabber.keep_recent(RAM, key)
        self.grab = grabber.Grabber(self.ffmpeg, src, headers, os.path.join(RAM, key), step=cfg['step'],
                                    width=GRAB_WIDTH, streamed=streamed, stop_event=STOP,
                                    min_free=MIN_FREE, settle=20.0, span=span, slots=slots,
                                    report=_make_reporter())
        self.grab.start()
        if not ahead:
            how = 'off'
        elif not streamed:
            how = 'whole file'
        else:
            how = '%d min each way' % (span // 60)
        _log('new video: %s, pictures ahead %s' % ('stream' if streamed else 'file', how))

    def _active(self):
        return (self.cfg['enabled'] and self.ffmpeg and self.player.isPlayingVideo()
                and not xbmc.getCondVisibility('Pvr.IsPlayingTV'))

    def tick(self):
        """One pass; returns how long to wait before the next."""
        now = time.time()
        stamp = self._stamp()
        if stamp != self.cfg_stamp:
            self.cfg_stamp, self.cfg = stamp, load_config()
            self._check_ffmpeg()
            if not self.cfg['enabled']:
                self._end_video()
                self._hide()
                self.playing = None
        if not self._active():
            if self.grab:
                self._end_video()
                self._hide()
                if RAM != DISK:
                    shutil.rmtree(RAM, ignore_errors=True)
            self.playing = None
            return 1.0 if self.cfg['enabled'] else 2.0
        try:
            playing = self.player.getPlayingFile()
        except Exception:
            playing = ''
        if playing != self.playing:
            self._new_video(playing)
        g = self.grab
        if not g:
            return 0.5
        try:
            g.duration = int(self.player.getTotalTime())
            g.centre = self.target if now - self.target_at < FOCUS_HOLD else int(self.player.getTime())
        except Exception:
            pass
        if xbmc.getCondVisibility('Player.Seeking'):
            label = xbmc.getInfoLabel('Player.SeekTime')
            t = _seconds(label)
            if t >= 0:
                self.target, self.target_at = t, now
                g.want(t)
                image = g.picture(t, reach=g.step * 2) or WAIT_IMG
                if (self.cfg['hidesubs'] and not self.subs_hidden
                        and xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled')):
                    try:
                        self.player.showSubtitles(False)
                        self.subs_hidden = True
                    except Exception:
                        pass
                fraction = (t / float(g.duration)) if g.duration else 0.5
                self.card.show(image, label, fraction, self.cfg['size'],
                               bool(xbmc.getCondVisibility('Window.IsActive(videoosd)')))
                self.last_shown = now
        elif self.last_shown and now - self.last_shown > 0.4:
            self._hide()
        return 0.1

    def close(self):
        STOP.set()
        g = self.grab
        self._end_video()
        if g:
            g.join(2)
        self._hide()
        FILES.close()


def _run(monitor):
    watcher = None
    try:
        watcher = _Watcher(monitor)
        while not monitor.abortRequested():
            if monitor.waitForAbort(watcher.tick()):
                break
    except Exception:
        import traceback
        _log('stopped after an error:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
    finally:
        if watcher:
            try:
                watcher.close()
            except Exception:
                pass


def start(monitor):
    """Called once by the AB Tools service. Idles while Seek Preview is off."""
    th = _WORKER['thread']
    if th is not None and th.is_alive():
        return
    th = threading.Thread(target=_run, args=(monitor,), name='abk-seekpreview')
    th.daemon = True
    _WORKER['thread'] = th
    th.start()
    _log('engine started (%s)' % ('on' if load_config()['enabled'] else 'off'))
