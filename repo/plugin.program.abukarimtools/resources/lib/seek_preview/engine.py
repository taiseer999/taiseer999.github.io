# -*- coding: utf-8 -*-
"""
AB Tools "Seek Preview" (4.8.12) - while you skip forward or back, a small
picture of the spot you are jumping to shows above the seek bar.

Based on service.seekpreview 1.2.0 by easter478
(https://github.com/easter478/kodi-seek-preview), GPL-3.0-or-later - see
LICENSE.txt in this folder. frames.py is the original frame maker, unchanged.
What AB Tools changed:
  - runs as a thread of the AB Tools service (started at boot, idles while
    the toggle is off) instead of its own add-on;
  - settings live in addon_data/plugin.program.abukarimtools/seek_preview.json
    and are set from Toggles > Seek Preview;
  - Kodi's own skip settings are never touched;
  - frames made ahead of time: the whole file for local files; on a stream
    only 3 minutes each way by default (4.8.13; every frame is one more HTTP
    request on the file being played), 10 minutes with "Always";
  - 4.8.13: diagnostics in kodi.log (first frame and its time, failures with
    ffmpeg's error text, low memory) with every URL replaced by <url>;
  - the box is a Lucent-style glass card, fitted to the Lucent Player seek
    bar on Arctic Fuse 3 (skin bool abk.lucentplayer);
  - the playing URL (it can carry a debrid / Silo token) is never logged.

ffmpeg comes from the CoreELEC "FFmpeg Tools" add-on (tools.ffmpeg-tools) or
from the system PATH; without one there is no preview.
"""
import hashlib
import json
import os
import re
import shutil
import threading
import time

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import paths
from resources.lib.seek_preview import frames

PROFILE = xbmcvfs.translatePath('special://profile/addon_data/plugin.program.abukarimtools/')
CONFIG = os.path.join(PROFILE, 'seek_preview.json')
DISK = xbmcvfs.translatePath('special://temp/abk_seekpreview')
RAM = '/tmp/abk_seekpreview' if os.path.isdir('/tmp') and not frames.WIN else DISK
MEDIA = os.path.join(paths.ADDON_PATH, 'resources', 'seek_preview', 'media')
FFMPEG_TOOLS = [
    xbmcvfs.translatePath('special://home/addons/tools.ffmpeg-tools/bin/ffmpeg'),
    '/usr/lib/kodi/addons/tools.ffmpeg-tools/bin/ffmpeg',
    # macOS: Kodi.app does not get the shell PATH, so Homebrew / MacPorts
    # installs are not found by shutil.which.
    '/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/opt/local/bin/ffmpeg',
]

DEFAULTS = {'enabled': False, 'size': 1, 'ahead': 1, 'hidesubs': True, 'step': 10}
# 1280x720 units. Frame size, the card's padding and the time row under the frame.
SIZES = [(240, 135), (320, 180), (426, 240)]
NAMES = ['s', 'm', 'l']
PAD, TIME_H = 8, 30
FRAME_W = 426                   # frames are made once at the largest size
# Lucent Player on AF3 (Includes_ABK_LucentPlayer.xml, 1080p units): the bar runs
# 96..1824; the time labels above it start at 880 (seek bar) / 836 (OSD open).
LUCENT = {'x0': 64, 'x1': 1216, 'bottom': 878 * 2 // 3, 'bottom_osd': 834 * 2 // 3}
GENERIC = {'x0': 64, 'x1': 1216, 'bottom': 720 - 150, 'bottom_osd': 720 - 210}
GAP = 10
LOW_MEM = 250 << 20            # 4.8.13: was 450 MB (the original's default)
SPAN_NEARBY, SPAN_FULL = 180, 600

STOP = threading.Event()
_THREAD = [None]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SeekPreview] %s' % msg, level)


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: data[k] for k in DEFAULTS if k in data})
    except Exception:
        pass
    cfg['size'] = max(0, min(2, int(cfg['size'])))
    cfg['ahead'] = max(0, min(2, int(cfg['ahead'])))
    cfg['step'] = int(cfg['step']) if int(cfg['step']) in (5, 10, 15, 30) else 10
    return cfg


def save_config(cfg):
    os.makedirs(PROFILE, exist_ok=True)
    tmp = CONFIG + '.part'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}, f, indent=1)
    os.replace(tmp, CONFIG)


def find_ffmpeg():
    """(path, where) or ('', '')."""
    for p in FFMPEG_TOOLS + [shutil.which('ffmpeg') or '']:
        if p and os.path.isfile(p) and frames.runs(p):
            return p, 'tools.ffmpeg-tools' if 'ffmpeg-tools' in p else 'system'
    return '', ''


def _secs(s):
    try:
        n = 0
        for part in s.strip().split(':'):
            n = n * 60 + int(part)
        return n
    except Exception:
        return -1


# ffmpeg can't open smb:// or nfs://, Kodi can: a tiny HTTP server on 127.0.0.1
# serves the file through xbmcvfs with Range support (from the original add-on).
PROXY = {'port': 0, 'files': {}, 'srv': None}


def _proxy():
    if PROXY['port']:
        return PROXY['port']
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            path = PROXY['files'].get(self.path.strip('/'))
            if not path:
                self.send_error(404)
                return
            f = xbmcvfs.File(path)
            try:
                size = f.size()
                m = re.match(r'bytes=(\d+)-(\d*)', self.headers.get('Range', ''))
                a = int(m.group(1)) if m else 0
                b = int(m.group(2)) if m and m.group(2) else size - 1
                self.send_response(206 if m else 200)
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Length', str(b - a + 1))
                if m:
                    self.send_header('Content-Range', 'bytes %d-%d/%d' % (a, b, size))
                self.end_headers()
                f.seek(a, 0)
                left = b - a + 1
                while left > 0 and not STOP.is_set():
                    d = f.readBytes(min(262144, left))
                    if not d:
                        break
                    self.wfile.write(d)
                    left -= len(d)
            except Exception:
                pass
            finally:
                f.close()

    srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, kwargs={'poll_interval': 0.2},
                     name='abk-seekpreview-proxy', daemon=True).start()
    PROXY['port'], PROXY['srv'] = srv.server_address[1], srv
    return PROXY['port']


def source(f):
    """Playing file -> (ffmpeg input, http headers, streamed?). (None, ..) when
    ffmpeg can't read it (discs, PVR, DRM add-ons)."""
    url, _, hdr = f.partition('|')
    if re.match(r'https?://', url):
        # Kodi's "|Name=Value&..." headers are URL-encoded (Authorization=Bearer+eyJ...).
        from urllib.parse import unquote_plus
        h = ''.join('%s: %s\r\n' % tuple(unquote_plus(p) for p in x.split('=', 1))
                    for x in hdr.split('&') if '=' in x)
        return url, h, True
    if os.path.isfile(url):
        return url, '', False
    if re.match(r'(smb|nfs|ftp|sftp|dav|davs|upnp|special|zip|rar)://', url) and xbmcvfs.exists(url):
        tok = hashlib.md5(url.encode('utf8', 'replace')).hexdigest()
        PROXY['files'][tok] = url
        return 'http://127.0.0.1:%d/%s' % (_proxy(), tok), '', False
    return None, '', False


def _fit():
    if xbmc.getSkinDir() == 'skin.arctic.fuse.3' and xbmc.getCondVisibility('Skin.HasSetting(abk.lucentplayer)'):
        return LUCENT
    return GENERIC


def spot(frac, size, osd):
    """Top-left corner of the card, centred over the seek position."""
    w, h = SIZES[size]
    cw, ch = w + 2 * PAD, h + 2 * PAD + TIME_H
    fit = _fit()
    bottom = fit['bottom_osd'] if osd else fit['bottom']
    x = int(fit['x0'] + max(0.0, min(1.0, frac)) * (fit['x1'] - fit['x0']) - cw / 2.0)
    x = max(fit['x0'], min(fit['x1'] - cw, x))
    y = bottom - GAP - ch
    return x, max(4, y)


class Overlay(object):
    """Glass card: background, frame, rounded corners over the frame, time."""

    def __init__(self):
        self.win = None
        self.shown = ''
        self.size = None

    def show(self, img, text, frac, size, osd):
        w, h = SIZES[size]
        x, y = spot(frac, size, osd)
        if self.win and self.size != size:
            self.hide()
        if not self.win:
            n = NAMES[size]
            self.win = xbmcgui.WindowDialog()
            self.bg = xbmcgui.ControlImage(x, y, w + 2 * PAD, h + 2 * PAD + TIME_H,
                                           os.path.join(MEDIA, 'card_%s.png' % n))
            self.img = xbmcgui.ControlImage(x + PAD, y + PAD, w, h, img, aspectRatio=0)
            self.corners = xbmcgui.ControlImage(x + PAD, y + PAD, w, h,
                                                os.path.join(MEDIA, 'corners_%s.png' % n))
            self.lab = xbmcgui.ControlLabel(x + PAD, y + PAD + h + 2, w, TIME_H - 4, text,
                                            font='font13', textColor='FFFFFFFF',
                                            alignment=0x2 | 0x4)
            self.win.addControls([self.bg, self.img, self.corners, self.lab])
            self.win.show()
            self.shown, self.size = img, size
            return
        self.bg.setPosition(x, y)
        self.img.setPosition(x + PAD, y + PAD)
        self.corners.setPosition(x + PAD, y + PAD)
        self.lab.setPosition(x + PAD, y + PAD + h + 2)
        if img != self.shown:
            self.img.setImage(img, False)
            self.shown = img
        self.lab.setLabel(text)

    def hide(self):
        if self.win:
            try:
                self.win.close()
            except Exception:
                pass
            self.win = None
            self.shown = ''


def _clean(text):
    text = re.sub(r'(https?|smb|nfs)://\S+', '<url>', text)
    return re.sub(r'(Bearer|token|apikey|api_key)[=: +]+\S+', r'\1 ***', text, flags=re.I)


def _reporter():
    seen = set()

    def report(kind, text):
        if kind == 'lowmem':
            if 'lowmem' in seen:
                return
            seen.add('lowmem')
        if kind == 'fail':
            n = sum(1 for x in seen if x.startswith('fail')) + 1
            seen.add('fail%d' % n)
            if n > 3:
                return              # the count is in "video done"
        _log('%s: %s' % (kind, ' | '.join(l.strip() for l in _clean(text).splitlines() if l.strip())),
             xbmc.LOGWARNING if kind in ('fail', 'lowmem') else xbmc.LOGINFO)
    return report


def _loop(monitor):
    player, box = xbmc.Player(), Overlay()
    ff, where = '', ''
    ff_checked = False
    cfg, cfg_mtime = load_config(), None
    gen, cur, last, root, subs = None, None, 0, None, False

    def drop():
        nonlocal gen, cur
        if gen:
            gen.halt()
        gen, cur = None, None

    def clear():
        nonlocal subs, last
        box.hide()
        last = 0
        if subs:
            subs = False
            try:
                player.showSubtitles(True)
            except Exception:
                pass

    while not monitor.abortRequested():
        now = time.time()
        try:
            m = os.path.getmtime(CONFIG)
        except OSError:
            m = None
        if m != cfg_mtime:
            cfg_mtime, cfg = m, load_config()
            if cfg['enabled'] and not ff_checked:
                ff, where = find_ffmpeg()
                ff_checked = True
                _log('ffmpeg: %s' % ('%s (%s)' % (ff, where) if ff else
                                      'none found (install FFmpeg Tools) - no previews'),
                     xbmc.LOGINFO if ff else xbmc.LOGWARNING)
            if not cfg['enabled']:
                drop()
                clear()
        if not (cfg['enabled'] and ff and player.isPlayingVideo()
                and not xbmc.getCondVisibility('Pvr.IsPlayingTV')):
            if gen:
                drop()
                clear()
                if root == RAM and RAM != DISK:
                    shutil.rmtree(RAM, True)
            monitor.waitForAbort(2 if not cfg['enabled'] else 1)
            continue
        root = RAM
        try:
            f = player.getPlayingFile()
        except Exception:
            f = ''
        if f != cur:
            if gen:
                gen.halt()
                _log('video done: %d frames made, %d failed' % (gen.made, gen.failed))
            gen, cur = None, f
            clear()
            url, hdr, remote = source(f) if f and not f.endswith('dummy.mp4') else (None, '', False)
            if url:
                key = hashlib.md5(('%d:%d:%s' % (FRAME_W, cfg['step'], f.partition('|')[0]))
                                  .encode('utf8', 'replace')).hexdigest()[:16]
                ahead = cfg['ahead'] > 0
                gen = frames.Frames(ff, url, hdr, os.path.join(root, key), cfg['step'], FRAME_W,
                                    remote, STOP, low_mem=LOW_MEM, wait=20 if ahead else 1e12)
                gen.span_remote = SPAN_FULL if cfg['ahead'] == 2 else SPAN_NEARBY
                gen.report = _reporter()
                frames.tidy(root, key)
                gen.start()
                _log('new video: %s, frames ahead %s' % (
                    'stream' if remote else 'file',
                    'off' if not ahead else ('whole file' if not remote else
                                             '%d min each way' % (gen.span_remote // 60))))
            elif f and not f.endswith('dummy.mp4'):
                _log('no preview for this video (disc, live TV, DRM or unknown source)')
        if not gen:
            monitor.waitForAbort(0.5)
            continue
        try:
            gen.dur = int(player.getTotalTime())
            gen.around = int(player.getTime())
        except Exception:
            pass
        if xbmc.getCondVisibility('Player.Seeking'):
            label = xbmc.getInfoLabel('Player.SeekTime')
            t = _secs(label)
            if t >= 0:
                gen.ask(t)
                img = gen.nearest(t)
                if img:
                    if (cfg['hidesubs'] and not subs
                            and xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled')):
                        try:
                            player.showSubtitles(False)
                            subs = True
                        except Exception:
                            pass
                    box.show(img, label, t / float(gen.dur) if gen.dur else 0.5, cfg['size'],
                             bool(xbmc.getCondVisibility('Window.IsActive(videoosd)')))
                last = now
        elif last and now - last > 0.4:
            clear()
        monitor.waitForAbort(0.1)

    STOP.set()
    if gen:
        gen.halt()
        gen.join(2)
    clear()
    if PROXY['srv']:
        try:
            PROXY['srv'].shutdown()
            PROXY['srv'].server_close()
        except Exception:
            pass


def _run(monitor):
    try:
        _loop(monitor)
    except Exception:
        import traceback
        _log('stopped after an error:\n%s' % traceback.format_exc(), xbmc.LOGERROR)


def start(monitor):
    """Called once by the AB Tools service. Idles while Seek Preview is off."""
    if _THREAD[0] and _THREAD[0].is_alive():
        return
    t = threading.Thread(target=_run, args=(monitor,), name='abk-seekpreview', daemon=True)
    _THREAD[0] = t
    t.start()
    _log('engine started (%s)' % ('on' if load_config()['enabled'] else 'off'))
