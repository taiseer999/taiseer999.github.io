# -*- coding: utf-8 -*-
"""
phone_setup.py - "Setup from your phone" (الإعداد من الجوال), 3.3.7.

Idea from the Dex Hub developer: the TV shows a QR code, the phone opens a
page served by THIS box over the local network, and everything is done from
the phone - no FTP, no file shuffling:

    backup   download a full backup to the phone / restore one from it
    add-ons  tick and install from the Add-on Portal catalog
    layout   Widgets Layout (light / moderate / full)
    lists    My Lists: Original or the Trakt lists for the hubs
    anime    Otaku lists on the home page
    patches  the patch toggles, applied at once

It reuses the same code as the TV screens (addon_portal, af3_shortcuts,
trakt_hubs, backup_manager, patcher) - only the questions move to the phone.
Progress dialogs of those tools still appear on the TV.

Safety: the server exists only while the QR screen is open (BACK on the TV
or "Finish" on the phone stops it, and 30 minutes without a request stops
it too). Every request must carry the random token from the QR link.
One job runs at a time.
"""

import hmac
import json
import os
import secrets
import socket
import threading
import time
import traceback
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'plugin.program.abukarimtools'
PORTS = range(8091, 8100)
IDLE_LIMIT = 30 * 60
MAX_UPLOAD = 2 * 1024 * 1024 * 1024          # 2 GB
PROFILE = xbmcvfs.translatePath('special://profile/addon_data/%s/' % ADDON_ID)
WORK_DIR = os.path.join(PROFILE, 'phone')
ADDON_PATH = xbmcvfs.translatePath('special://home/addons/%s/' % ADDON_ID)
PAGE = os.path.join(ADDON_PATH, 'resources', 'phone', 'index.html')


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Phone] %s' % msg, level)


def T(sid):
    from resources.lib.i18n import T as _t
    return _t(sid)


def _version():
    try:
        return xbmcaddon.Addon(ADDON_ID).getAddonInfo('version')
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# session state
# ---------------------------------------------------------------------------

class _Session(object):

    def __init__(self):
        self.token = secrets.token_urlsafe(12)
        self.last_seen = time.time()
        self.finish = False
        self.stopped = False              # 3.3.8: no new job once stopping
        self.done = set()                 # sections finished from the phone
        self.lock = threading.Lock()
        self.job = {'id': 0, 'name': '', 'running': False, 'pct': 0,
                    'msg': '', 'ok': None, 'result': None}

    def touch(self):
        self.last_seen = time.time()

    def start(self, name, fn):
        """Run fn(progress) in a worker thread. False when one is running."""
        with self.lock:
            if self.job['running'] or self.finish or self.stopped:
                return False
            self.job = {'id': self.job['id'] + 1, 'name': name, 'running': True,
                        'pct': 0, 'msg': '', 'ok': None, 'result': None}
            jid = self.job['id']

        def progress(pct, msg=''):
            with self.lock:
                if self.job['id'] == jid:
                    self.job['pct'] = max(0, min(100, int(pct)))
                    if msg:
                        self.job['msg'] = msg

        def run():
            ok, result = False, None
            try:
                ok, result = fn(progress)
            except Exception as e:
                _log('job %s crashed:\n%s' % (name, traceback.format_exc()),
                     xbmc.LOGERROR)
                result = {'error': str(e)}
            with self.lock:
                if self.job['id'] == jid:
                    self.job.update({'running': False, 'pct': 100,
                                     'ok': bool(ok), 'result': result})
            if ok:
                self.done.add(name)
            _log('job %s finished: ok=%s' % (name, ok))

        t = threading.Thread(target=run, name='abk-phone-%s' % name)
        t.daemon = True
        t.start()
        return True


S = None                                  # the live session


# ---------------------------------------------------------------------------
# data for the page
# ---------------------------------------------------------------------------

def _info():
    from resources.lib import addon_portal, af3_shortcuts, trakt_hubs, patcher
    portal = []
    for aid, name, repo, _icon in addon_portal._catalog():
        portal.append({'id': aid, 'name': name, 'repo': addon_portal.REPO_NAMES.get(repo, repo),
                       'installed': addon_portal._is_local(aid),
                       'note': addon_portal._note(aid)})
    disabled = patcher._load_disabled()
    toggles = [{'id': tid, 'label': label, 'on': tid not in disabled}
               for tid, label in patcher._toggle_groups()]
    anime_cur = set(trakt_hubs.anime_picks())
    anime = [{'route': r, 'label': trakt_hubs.AR(lab), 'on': r in anime_cur}
             for r, lab, _ic, _st in trakt_hubs.ANIME_ENTRIES]
    return {
        'version': _version(),
        'kodi': xbmc.getInfoLabel('System.BuildVersion').split(' ')[0],
        'skin': xbmc.getSkinDir(),
        'device': xbmc.getInfoLabel('System.FriendlyName') or '',
        'portal': portal,
        'layout': af3_shortcuts.current_mode() or '',
        'lists_mode': trakt_hubs.current_mode() or 'original',
        'trakt_linked': bool(trakt_hubs._token()),
        'anime': anime,
        'otaku': trakt_hubs._otaku_installed(),
        'toggles': toggles,
        'done': sorted(S.done) if S else [],
    }


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------

def _job_backup(progress):
    from resources.lib import backup_manager
    os.makedirs(WORK_DIR, exist_ok=True)
    for f in os.listdir(WORK_DIR):                    # one backup at a time
        if f.startswith('abk_backup_'):
            try:
                os.remove(os.path.join(WORK_DIR, f))
            except OSError:
                pass
    name = 'abk_backup_%s.zip' % time.strftime('%Y%m%d_%H%M%S')
    path = os.path.join(WORK_DIR, name)
    n = backup_manager.write_backup(
        path, lambda i, tot, arc: progress(i * 100 / max(tot, 1), arc))
    if not n:
        return False, {'error': 'empty'}
    return True, {'download': '/dl/%s' % name, 'files': n,
                  'size': os.path.getsize(path)}


def _job_restore(path):
    def job(progress):
        from resources.lib import backup_manager
        try:
            total, cancelled, after = backup_manager.restore_backup(
                path, lambda i, tot, arc: progress(i * 95 / max(tot, 1), arc))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        if not cancelled:
            xbmcgui.Dialog().notification('ABUKARIM TOOLS', T(30738),
                                          xbmcgui.NOTIFICATION_INFO, 8000)
        return (not cancelled), {'files': total, 'settings': after.get('settings', 0),
                                 'skin': after.get('skin', ''),
                                 'installed': after.get('installed', 0),
                                 'failed': after.get('failed', []), 'restart': True}
    return job


def _job_addons(ids):
    def job(progress):
        from resources.lib import addon_portal
        cat = {a[0]: a for a in addon_portal._catalog()}
        entries = [(i, cat[i][1], cat[i][2]) for i in ids if i in cat]
        if not entries:
            return False, {'error': 'none'}
        progress(5, '...')
        res = addon_portal._install_selection(entries)
        try:
            addon_portal._patch_now()
        except Exception:
            pass
        out = [{'name': n, 'ok': bool(ok), 'note': note} for n, ok, note in res]
        return all(r['ok'] for r in out), {'results': out}
    return job


def _job_layout(mode):
    def job(progress):
        from resources.lib import af3_shortcuts
        progress(5)
        return bool(af3_shortcuts.apply(mode)), {'mode': mode}
    return job


def _job_lists_fetch(progress):
    from resources.lib import trakt_hubs
    progress(5)
    res = trakt_hubs.phone_fetch()
    return bool(res.get('ok')), res


def _job_lists_apply(mode, keys, wmode):
    def job(progress):
        from resources.lib import trakt_hubs
        progress(10)
        if mode == 'original':
            return trakt_hubs.phone_original(), {'mode': 'original'}
        return trakt_hubs.phone_apply(keys or {}, wmode), {'mode': 'custom'}
    return job


def _job_anime(routes):
    def job(progress):
        from resources.lib import trakt_hubs, addon_portal
        if routes and not trakt_hubs._otaku_installed():
            progress(5, 'Otaku')
            addon_portal._install_selection(
                [(trakt_hubs.OTAKU, 'Otaku', trakt_hubs.OTAKU_REPO)])
            if not trakt_hubs._otaku_installed():
                return False, {'error': 'otaku'}
        progress(80)
        return trakt_hubs.phone_anime(routes), {'routes': routes}
    return job


def _job_patches(disabled):
    def job(progress):
        from resources.lib import patcher, patch_watchdog
        known = {t for t, _l in patcher._toggle_groups()}
        patcher._save_disabled({d for d in disabled if d in known})
        progress(20)
        ids = [a for a in patcher.target_addon_ids() if patch_watchdog._addon_path(a)]
        ok_n, fail_n, written, _r = patcher.apply_set(addon_ids=ids)
        patcher.reload_skin_if_pending()
        return fail_n == 0, {'ok': ok_n, 'failed': fail_n, 'written': written}
    return job


def _reboot():
    try:
        from resources.lib import addons33_rebuild
        coreelec = addons33_rebuild._is_coreelec()
    except Exception:
        coreelec = False
    xbmc.sleep(1500)
    xbmc.executebuiltin('Reboot' if coreelec else 'RestartApp')


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    server_version = 'ABUKARIM-TOOLS'
    protocol_version = 'HTTP/1.1'
    # 3.3.9: one request per connection and a socket timeout. kodi.log
    # 2026-10-14 10:00:46: the phone browser kept idle keep-alive sockets
    # open, so handler threads outlived the QR screen ("waiting on thread",
    # "left several classes in memory") and its later reset was printed as
    # a ConnectionResetError traceback.
    timeout = 20

    def log_message(self, fmt, *args):
        pass

    # -- helpers --
    def _token_ok(self, q):
        tok = (q.get('t') or [''])[0] or self.headers.get('X-Token', '')
        return bool(S) and hmac.compare_digest(tok.encode(), S.token.encode())

    def _send(self, code, body, ctype='application/json; charset=utf-8', extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.close_connection = True
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0 or n > 1024 * 1024:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode('utf-8') or '{}')
        except Exception:
            return {}

    def _parse(self):
        u = urllib.parse.urlsplit(self.path)
        return u.path, urllib.parse.parse_qs(u.query)

    # -- GET --
    def do_GET(self):
        path, q = self._parse()
        if path == '/favicon.ico':
            return self._send(204, b'', 'image/x-icon')
        if not self._token_ok(q):
            return self._send(403, {'error': 'token'})
        S.touch()
        if path in ('/', '/index.html'):
            try:
                with open(PAGE, 'rb') as f:
                    return self._send(200, f.read(), 'text/html; charset=utf-8')
            except Exception as e:
                return self._send(500, {'error': str(e)})
        if path == '/api/info':
            return self._send(200, _info())
        if path == '/api/job':
            with S.lock:
                return self._send(200, dict(S.job))
        if path.startswith('/dl/'):
            name = os.path.basename(urllib.parse.unquote(path[4:]))
            fp = os.path.join(WORK_DIR, name)
            if not name.startswith('abk_backup_') or not os.path.isfile(fp):
                return self._send(404, {'error': 'missing'})
            size = os.path.getsize(fp)
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Length', str(size))
            self.send_header('Content-Disposition', 'attachment; filename="%s"' % name)
            self.send_header('Connection', 'close')
            self.close_connection = True
            self.end_headers()
            with open(fp, 'rb') as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    S.touch()
            return
        return self._send(404, {'error': 'path'})

    # -- POST --
    def do_POST(self):
        path, q = self._parse()
        if not self._token_ok(q):
            return self._send(403, {'error': 'token'})
        S.touch()
        if path == '/api/restore':
            return self._upload_restore()
        body = self._json_body()
        job = None
        name = path.rsplit('/', 1)[-1]
        if path == '/api/backup':
            job = _job_backup
        elif path == '/api/addons':
            job = _job_addons([str(i) for i in body.get('ids') or []])
        elif path == '/api/layout' and body.get('mode') in ('light', 'moderate', 'full'):
            job = _job_layout(body['mode'])
        elif path == '/api/lists/fetch':
            job, name = _job_lists_fetch, 'lists_fetch'
        elif path == '/api/lists/apply':
            job, name = _job_lists_apply(body.get('mode'), body.get('keys'),
                                         body.get('wmode') or 'add'), 'lists'
        elif path == '/api/lists/link':
            xbmc.executebuiltin('RunScript(plugin.video.themoviedb.helper,authenticate_trakt)')
            return self._send(200, {'ok': True})
        elif path == '/api/anime':
            job = _job_anime([str(r) for r in body.get('routes') or []])
        elif path == '/api/patches':
            job = _job_patches([str(d) for d in body.get('disabled') or []])
        elif path == '/api/reboot':
            S.finish = True
            threading.Thread(target=_reboot, daemon=True).start()
            return self._send(200, {'ok': True})
        elif path == '/api/finish':
            S.finish = True
            return self._send(200, {'ok': True})
        if job is None:
            return self._send(404, {'error': 'path'})
        if not S.start(name, job):
            return self._send(409, {'error': 'busy'})
        return self._send(202, {'ok': True, 'job': name})

    def _upload_restore(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0 or n > MAX_UPLOAD:
            return self._send(413, {'error': 'size'})
        os.makedirs(WORK_DIR, exist_ok=True)
        fp = os.path.join(WORK_DIR, 'upload_restore.zip')
        left = n
        with open(fp, 'wb') as f:
            while left > 0:
                chunk = self.rfile.read(min(256 * 1024, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
                S.touch()
        if left > 0 or not zipfile.is_zipfile(fp):
            try:
                os.remove(fp)
            except OSError:
                pass
            return self._send(400, {'error': 'zip'})
        if not S.start('restore', _job_restore(fp)):
            return self._send(409, {'error': 'busy'})
        return self._send(202, {'ok': True, 'job': 'restore'})


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """A phone closing / resetting its connection is normal - one quiet
        line instead of socketserver's traceback on stderr (kodi.log)."""
        import sys
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionError, TimeoutError, socket.timeout, BrokenPipeError)):
            _log('connection from %s closed: %s' % (client_address[0], type(exc).__name__),
                 xbmc.LOGDEBUG)
            return
        _log('request from %s failed:\n%s' % (client_address[0], traceback.format_exc()),
             xbmc.LOGWARNING)


def _bind():
    for port in PORTS:
        try:
            srv = _Server(('', port), _Handler)
            srv.daemon_threads = True
            return srv, port
        except OSError:
            continue
    return None, 0


# ---------------------------------------------------------------------------
# TV side
# ---------------------------------------------------------------------------

class _QRWindow(xbmcgui.WindowXMLDialog):
    """abk_qr.xml, non-modal: stays up while the phone works; BACK stops."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._props = kwargs.get('props') or {}
        self.closed = False

    def onInit(self):
        for k, v in self._props.items():
            self.setProperty(k, v)

    def onClick(self, control_id):
        pass

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU,
                              xbmcgui.ACTION_STOP):
            self.closed = True
            self.close()


def run(first_run=False):
    """Show the QR, serve the phone until Finish / BACK / idle. Returns the
    set of sections done from the phone ('backup', 'restore', 'addons',
    'layout', 'lists', 'anime', 'patches')."""
    global S
    from resources.lib import webserver_secure, qr_view
    S = _Session()
    srv, port = _bind()
    if not srv:
        _log('no free port in %s-%s' % (PORTS[0], PORTS[-1]), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(T(30730), T(30733))
        return set()
    ip = webserver_secure._local_ip()
    url = 'http://%s:%d/?t=%s' % (ip, port, S.token)
    th = threading.Thread(target=srv.serve_forever, name='abk-phone-http')
    th.daemon = True
    th.start()
    _log('serving on port %d (first_run=%s)' % (port, first_run))
    try:
        qr = qr_view.make_qr(url)
    except Exception as e:
        _log('QR failed: %s' % e, xbmc.LOGWARNING)
        qr = ''
    win = _QRWindow('abk_qr.xml', ADDON_PATH, 'Default', '1080i', props={
        'title': T(30730),
        'text': T(30731) % ('http://%s:%d' % (ip, port)),
        'qr': qr, 'hint': T(30732)})
    win.show()
    mon = xbmc.Monitor()
    try:
        while not mon.abortRequested():
            if win.closed or S.finish:
                S.stopped = True
                break
            with S.lock:
                busy = S.job['running']
            if not busy and time.time() - S.last_seen > IDLE_LIMIT:
                _log('idle for %d min - stopping' % (IDLE_LIMIT // 60))
                S.stopped = True
                break
            if mon.waitForAbort(1):
                break
        # a job still running (install, restore) is allowed to finish
        while not mon.abortRequested():
            with S.lock:
                if not S.job['running']:
                    break
            if mon.waitForAbort(1):
                break
    finally:
        try:
            win.close()
        except Exception:
            pass
        del win
        srv.shutdown()
        srv.server_close()
        done = set(S.done)
        _log('stopped; done from the phone: %s' % (', '.join(sorted(done)) or 'nothing'))
    return done
