# -*- coding: utf-8 -*-
"""Shared helpers: settings, logging, paths, HTTP."""
import json
import os
import threading
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'service.subtitles.najdsmart'
ADDON = xbmcaddon.Addon(ADDON_ID)
ADDON_NAME = ADDON.getAddonInfo('name')
VERSION = ADDON.getAddonInfo('version')
USER_AGENT = 'NajdSmartSubs v%s' % VERSION

PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
TEMP_DIR = os.path.join(PROFILE, 'temp')
CACHE_DIR = os.path.join(PROFILE, 'cache')
JOBS_DIR = os.path.join(PROFILE, 'jobs')


def ensure_dirs():
    """Piers edition: a cache cleaner (AB Wizard Auto Clean) can delete these
    folders while the service runs - make them again before they are used."""
    for _d in (PROFILE, TEMP_DIR, CACHE_DIR, JOBS_DIR):
        if not os.path.isdir(_d):
            try:
                os.makedirs(_d, exist_ok=True)
            except OSError:
                pass


ensure_dirs()


def setting(key, default=''):
    try:
        val = xbmcaddon.Addon(ADDON_ID).getSetting(key)
    except Exception:
        return default
    return val if val != '' else default


def setting_bool(key, default=False):
    val = setting(key, '')
    if val == '':
        return default
    return val.lower() == 'true'


def setting_int(key, default=0):
    try:
        return int(float(setting(key, str(default))))
    except ValueError:
        return default


# ------------------------------------------------------------------ Piers / AB Tools
# Piers edition (AB Tools): the AI keys the user already gave Dex Hub are used
# when this add-on has none of its own; its own key always wins.
_DEXHUB_PID = {'claude': 'anthropic'}       # Najd id -> Dex Hub id where they differ


def shared_key(pid):
    try:
        path = xbmcvfs.translatePath(
            'special://profile/addon_data/plugin.video.dexhub/ai.json')
        if not os.path.isfile(path):
            return ''
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        svc = (data.get('services') or {}).get(_DEXHUB_PID.get(pid, pid)) or {}
        if not svc and data.get('provider') == _DEXHUB_PID.get(pid, pid):
            svc = {'key': data.get('key') or ''}      # Dex Hub's older single-service file
        return (svc.get('key') or '').strip()
    except Exception:
        return ''


def abtools_setup_busy():
    """True while AB Tools' first-run setup is running (its lock file)."""
    return os.path.exists(xbmcvfs.translatePath(
        'special://profile/addon_data/plugin.program.abukarimtools/first_run.lock'))


_URL_RE = None


def redact(text):
    """Hide query strings, header tokens and keys so kodi.log is safe to share."""
    import re
    global _URL_RE
    if _URL_RE is None:
        _URL_RE = re.compile(r'(https?://[^/\s|\'"]+)[^\s\'"]*')
    text = _URL_RE.sub(r'\1/…', str(text))
    text = re.sub(r'(AIza)[0-9A-Za-z_\-]{20,}', r'\1…', text)
    text = re.sub(r'(?i)((?:api[_-]?key|token|password|authorization)["\']?\s*[:=]\s*["\']?)[^\s"\',&]+', r'\1…', text)
    return text


HISTORY = os.path.join(PROFILE, 'history.log')
HISTORY_HOURS = 72
_HIST = {'n': 0, 'lock': threading.Lock()}


def _history_add(text, level):
    """Najd's own log of the last two days: kodi.log starts over at every restart, so
    one report can cover every film watched since yesterday, not just the last one."""
    try:
        tag = 'error' if level >= xbmc.LOGERROR else 'warning' if level >= xbmc.LOGWARNING else 'info'
        line = '%s %s: %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), tag, text.replace('\n', ' / '))
        with _HIST['lock']:
            with open(HISTORY, 'a', encoding='utf-8') as f:
                f.write(line)
            _HIST['n'] += 1
            if _HIST['n'] % 400 == 1:
                prune_history()
    except Exception:
        pass


def prune_history():
    """Keep only the last HISTORY_HOURS hours (and at most ~4 MB)."""
    try:
        if not os.path.exists(HISTORY):
            return
        cut = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - HISTORY_HOURS * 3600))
        with open(HISTORY, encoding='utf-8', errors='replace') as f:
            lines, keep = [], False
            for l in f:
                if l[:2] == '20':
                    keep = l[:19] >= cut
                if keep:
                    lines.append(l)
        lines = lines[-20000:]
        tmp = HISTORY + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        os.replace(tmp, HISTORY)
    except Exception:
        pass


def history_note(text):
    """A line of Najd's own health record (start, power-off, pulse...) — history only,
    never kodi.log, so the pulses every few minutes do not fill Kodi's log."""
    try:
        with _HIST['lock']:
            with open(HISTORY, 'a', encoding='utf-8') as f:
                f.write('%s ★ %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), text))
    except Exception:
        pass


def history_block(title, lines):
    try:
        with _HIST['lock']:
            with open(HISTORY, 'a', encoding='utf-8') as f:
                f.write('%s ★ ---- %s ----\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), title))
                for l in lines:
                    f.write('    | %s\n' % redact(l.rstrip('\n')))
                f.write('%s ★ ---- end: %s ----\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), title))
    except Exception:
        pass


def history_lines(before=''):
    """The kept lines (older than `before`, 'YYYY-MM-DD HH:MM:SS', when given)."""
    try:
        prune_history()
        with open(HISTORY, encoding='utf-8', errors='replace') as f:
            out, older = [], True
            for l in f:
                if l[:2] == '20':
                    older = not before or l[:19] < before
                if older:
                    out.append(l.rstrip('\n'))
            return out
    except Exception:
        return []


def log(msg, level=xbmc.LOGINFO):
    text = redact(msg)
    xbmc.log('[%s] %s' % (ADDON_ID, text), level)
    _history_add(text, level)


def notify(msg, seconds=4, icon=None):
    if setting_bool('notifications', True):
        xbmcgui.Dialog().notification(ADDON_NAME, msg,
                                      icon or ADDON.getAddonInfo('icon'),
                                      seconds * 1000, False)
        try:
            xbmcgui.Window(10000).setProperty('NajdSubs.NotifyTime', str(time.time()))
        except Exception:
            pass


class HttpError(Exception):
    def __init__(self, code, body=''):
        Exception.__init__(self, 'HTTP %s: %s' % (code, body[:200]))
        self.code = code
        self.body = body


def http(url, params=None, headers=None, data=None, json_body=None,
         method=None, timeout=30, raw=False, retries=1):
    """Small urllib wrapper. Returns parsed JSON (or bytes if raw)."""
    if params:
        query = urllib.parse.urlencode([(k, v) for k, v in params
                                        if v not in (None, '')]
                                       if isinstance(params, list) else
                                       [(k, v) for k, v in params.items()
                                        if v not in (None, '')])
        url = url + ('&' if '?' in url else '?') + query
    hdrs = {'User-Agent': USER_AGENT, 'Accept': '*/*'}
    if headers:
        hdrs.update(headers)
    body = data
    if json_body is not None:
        body = json.dumps(json_body).encode('utf-8')
        hdrs['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=hdrs,
                                 method=method or ('POST' if body else 'GET'))
    ctx = ssl.create_default_context()
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                content = resp.read()
            if raw:
                return content
            return json.loads(content.decode('utf-8', 'replace')) if content else {}
        except urllib.error.HTTPError as e:
            err_body = ''
            try:
                err_body = e.read().decode('utf-8', 'replace')
            except Exception:
                pass
            last = HttpError(e.code, err_body)
            if e.code in (429, 502, 503, 504) and attempt < retries:
                time.sleep((10 if e.code == 429 else 2) * (attempt + 1))
                continue
            raise last
        except (urllib.error.URLError, OSError) as e:
            last = e
            if attempt < retries:
                time.sleep(1.5)
                continue
            raise
    raise last


def cache_get(name, max_age):
    path = os.path.join(CACHE_DIR, name)
    try:
        if time.time() - os.path.getmtime(path) < max_age:
            with open(path, 'rb') as f:
                return f.read()
    except OSError:
        pass
    return None


def write_atomic(path, content):
    """Write to a temporary file, then swap it in: a reader never sees a half-written file."""
    ensure_dirs()
    tmp = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp, 'wb') as f:
        f.write(content if isinstance(content, bytes) else content.encode('utf-8'))
    os.replace(tmp, path)
    return path


def cache_put(name, content):
    return write_atomic(os.path.join(CACHE_DIR, name), content)


def cache_del(name):
    try:
        os.remove(os.path.join(CACHE_DIR, name))
    except OSError:
        pass


def cache_json(name, max_age):
    """Cached JSON, or None; a damaged file is deleted instead of breaking the caller."""
    c = cache_get(name, max_age)
    if not c:
        return None
    try:
        return json.loads(c.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        cache_del(name)
        return None


def clean_temp(keep_hours=12):
    """Remove old working files. Recent ones stay, so the subtitle that is playing (and the
    versions made for it) are never pulled away and can be checked in a problem report."""
    now = time.time()
    ensure_dirs()
    for root, dirs, files in os.walk(TEMP_DIR, topdown=False):     # one folder per video too
        for name in files:
            try:
                p = os.path.join(root, name)
                if name.startswith('archive') or now - os.path.getmtime(p) > keep_hours * 3600:
                    os.remove(p)
            except OSError:
                pass
        if root != TEMP_DIR:
            try:
                os.rmdir(root)          # only when empty
            except OSError:
                pass


# long-lived cache files: AI translations and reference info are kept far longer
LONG_LIVED = {'whisper_': 365 * 86400, 'embtr_': 365 * 86400, 'tr_': 365 * 86400, 'refmeta_': 120 * 86400, 'ref_': 30 * 86400,
              'emb_': 60 * 86400}


def prune_cache(max_age=14 * 86400):
    now = time.time()
    for name in os.listdir(CACHE_DIR):
        p = os.path.join(CACHE_DIR, name)
        age = next((a for pre, a in LONG_LIVED.items() if name.startswith(pre)), max_age)
        try:
            if name.endswith('.tmp') and now - os.path.getmtime(p) > 3600:
                os.remove(p)
            elif now - os.path.getmtime(p) > age:
                os.remove(p)
        except OSError:
            pass


# ---------------------------------------------------------------- on-screen status
STATUS_PROP = 'NajdSubs.Status'
STATE_PROP = 'NajdSubs.State'      # busy | ok | err | ''


def set_status(text, state='busy'):
    """Shared status (any process) — shown as a skin notification and usable by skins:
    $INFO[Window(Home).Property(NajdSubs.Status)]"""
    try:
        w = xbmcgui.Window(10000)
        w.setProperty(STATUS_PROP, text or '')
        w.setProperty(STATE_PROP, state if text else '')
        w.setProperty('NajdSubs.Time', str(time.time()))
    except Exception:
        pass


def get_status():
    w = xbmcgui.Window(10000)
    return w.getProperty(STATUS_PROP), w.getProperty(STATE_PROP)


def history_events():
    """Only Najd's health record (★ lines and their blocks), all three days."""
    try:
        prune_history()
        out = []
        with open(HISTORY, encoding='utf-8', errors='replace') as f:
            for l in f:
                star = l[:2] == '20' and l[19:22] == ' ★ '
                if star or (l.startswith('    | ')):
                    out.append(l.rstrip('\n'))
        return out
    except Exception:
        return []
