# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
najd_subs.py - ABUKARIM TOOLS (4.12.1)

Najd Smart Subtitles (service.subtitles.najdsmart, by Ali, MIT licence -
THIRD-PARTY-NOTICES.txt) ships inside AB Tools as its Piers edition zip in
resources/najdsmart/. It is not on any repository, so AB Tools installs and
updates it itself:

  * boot (service.py, background thread, after first-run setup and never
    during playback): install the bundled zip when Najd is missing or older,
    enable it, and - the first time only - make it Kodi's subtitle service
    for movies and episodes (subtitles.movie / subtitles.tv) with Arabic in
    the subtitle languages. The previous services are kept so the menu can
    put them back. A later change the user makes in Kodi's own settings is
    never overridden.
  * on CoreELEC, FFmpeg tools (tools.ffmpeg-tools, CoreELEC's repository)
    once, so Najd can listen to the audio to time the lines.
  * Mods > Najd Smart Subtitles: default on / off, Najd's setup wizard, its
    settings, the connection test, reinstall from AB Tools, FFmpeg tools.

Dex Hub keeps its own subtitle flow (DexSubtitles, AutoSync, Translate
subtitle): the Piers edition of Najd waits for it on Dex Hub videos.
"""
import glob
import json
import os
import re
import threading

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

NAJD_ID = 'service.subtitles.najdsmart'
FFMPEG_ID = 'tools.ffmpeg-tools'
SERVICES = ('subtitles.movie', 'subtitles.tv')

_HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BUNDLE_DIR = os.path.join(_HERE, 'resources', 'najdsmart')
_ADDONS = xbmcvfs.translatePath('special://home/addons/')
_STATE = xbmcvfs.translatePath(
    'special://profile/addon_data/plugin.program.abukarimtools/najd_state.json')
_LOCK = threading.Lock()


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Najd] %s' % msg, level)


def _notify(msg, ms=4000, warn=False):
    try:
        xbmcgui.Dialog().notification(
            T(32348), msg,
            xbmcgui.NOTIFICATION_WARNING if warn else xbmcgui.NOTIFICATION_INFO, ms)
    except Exception:
        pass


def _rpc(method, params=None):
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    except Exception:
        return {}


# ------------------------------------------------------------------ state
def _load():
    try:
        with open(_STATE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save(d):
    try:
        os.makedirs(os.path.dirname(_STATE), exist_ok=True)
        tmp = _STATE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f)
        os.replace(tmp, _STATE)
    except Exception as e:
        _log('state not saved: %s' % e, xbmc.LOGWARNING)


# ------------------------------------------------------------------ versions
def _vtuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', v or '')[:6])


def bundle():
    """(zip path, version) of the Najd zip AB Tools carries, newest first."""
    best = (None, '')
    for p in glob.glob(os.path.join(_BUNDLE_DIR, NAJD_ID + '-*.zip')):
        v = os.path.basename(p)[len(NAJD_ID) + 1:-4]
        if _vtuple(v) > _vtuple(best[1]):
            best = (p, v)
    return best


def installed_version():
    try:
        with open(os.path.join(_ADDONS, NAJD_ID, 'addon.xml'), 'r', encoding='utf-8') as f:
            m = re.search(r'<addon\b[^>]*\bversion="([^"]+)"', f.read())
        return m.group(1) if m else ''
    except Exception:
        return ''


def enabled(addon_id=NAJD_ID):
    return bool(xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % addon_id))


def _is_coreelec():
    try:
        from resources.lib import addon_portal as ap
        return ap._is_coreelec()
    except Exception:
        return os.path.isdir('/etc/coreelec')


def _ffmpeg_present():
    return os.path.isfile(os.path.join(_ADDONS, FFMPEG_ID, 'bin', 'ffmpeg'))


# ------------------------------------------------------------------ default service
def _get(sid):
    return (_rpc('Settings.GetSettingValue', {'setting': sid}).get('result') or {}).get('value')


def _set(sid, value):
    r = _rpc('Settings.SetSettingValue', {'setting': sid, 'value': value})
    return 'error' not in r


def is_default():
    return all(_get(s) == NAJD_ID for s in SERVICES)


def set_default(on=True):
    """on: Najd for movies and episodes (the current services kept), Arabic
    added to the subtitle languages. off: the kept services back (none kept
    -> DexSubtitles when it is there, else Kodi's empty choice)."""
    st = _load()
    if on:
        prev = st.get('previous') or {}
        for s in SERVICES:
            cur = _get(s)
            if cur and cur != NAJD_ID:
                prev[s] = cur
        st['previous'] = prev
        ok = all(_set(s, NAJD_ID) for s in SERVICES)
        langs = _get('subtitles.languages')
        if isinstance(langs, list) and 'Arabic' not in langs:
            _set('subtitles.languages', ['Arabic'] + langs)
    else:
        prev = st.get('previous') or {}
        fallback = 'service.subtitles.dexworld' if enabled('service.subtitles.dexworld') else ''
        ok = all(_set(s, prev.get(s) or fallback) for s in SERVICES)
    st['default_set'] = True
    st['default_on'] = bool(on)
    _save(st)
    _log('default subtitle service -> %s (ok=%s)' % ('Najd' if on else 'previous', ok))
    return ok


def service_name(sid='subtitles.movie'):
    aid = _get(sid) or ''
    if not aid:
        return T(32364)
    try:
        return xbmcaddon.Addon(aid).getAddonInfo('name') or aid
    except Exception:
        return aid


# ------------------------------------------------------------------ install
def install_bundled(force=False):
    """Install / update Najd from the zip AB Tools carries. True when Najd is
    present and enabled afterwards. Silent; never raises."""
    zpath, zver = bundle()
    have = installed_version()
    if not zpath:
        _log('no bundled zip in %s' % _BUNDLE_DIR, xbmc.LOGWARNING)
        return bool(have) and enabled()
    if have and not force and _vtuple(have) >= _vtuple(zver):
        if not enabled():
            _enable()
        return enabled()
    if not _LOCK.acquire(False):
        return False
    try:
        import shutil
        import tempfile
        from resources.lib import skin_installer as si
        _log('installing %s %s (installed: %s)' % (NAJD_ID, zver, have or '-'))
        # _extract_zip_silent deletes the zip it is given (made for downloads):
        # hand it a temporary copy so the bundled one stays in AB Tools
        fd, tmp = tempfile.mkstemp(suffix='.zip', prefix='abk_najd_')
        os.close(fd)
        shutil.copyfile(zpath, tmp)
        try:
            extracted = si._extract_zip_silent(tmp)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        if not extracted:
            _log('extract failed', xbmc.LOGWARNING)
            return False
        try:
            from resources.lib import addon_portal as ap
            ap._wait_registered(NAJD_ID)
        except Exception:
            xbmc.executebuiltin('UpdateLocalAddons')
            xbmc.sleep(3000)
        _enable()
        ok = installed_version() == zver and enabled()
        _log('%s %s ready=%s' % (NAJD_ID, zver, ok))
        return ok
    except Exception as e:
        _log('install failed: %s' % e, xbmc.LOGWARNING)
        return False
    finally:
        _LOCK.release()


def _enable(addon_id=NAJD_ID):
    try:
        from resources.lib import addon_portal as ap
        return ap._enable(addon_id)
    except Exception:
        _rpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True})
        return enabled(addon_id)


def install_ffmpeg():
    """tools.ffmpeg-tools from CoreELEC's repository (Kodi's own installer)."""
    if _ffmpeg_present():
        return True
    try:
        from resources.lib import addon_portal as ap
        ok = ap._kodi_install(FFMPEG_ID)
    except Exception as e:
        _log('ffmpeg-tools install failed: %s' % e, xbmc.LOGWARNING)
        ok = False
    if ok:
        _enable(FFMPEG_ID)
    _log('ffmpeg-tools present=%s' % _ffmpeg_present())
    return _ffmpeg_present()


def ensure():
    """Boot chore: Najd installed and up to date; the default service the
    first time; FFmpeg tools on CoreELEC once."""
    ok = install_bundled()
    st = _load()
    if ok and not st.get('default_set'):
        set_default(True)
        st = _load()
    if ok and _is_coreelec() and not _ffmpeg_present() and not st.get('ffmpeg_tried'):
        st['ffmpeg_tried'] = True
        _save(st)
        install_ffmpeg()
    return ok


def start_boot_ensure(monitor, delay=45):
    """Background thread: waits out first-run setup and playback."""
    zpath, zver = bundle()
    if not zpath:
        return
    if _load().get('default_set') and _vtuple(installed_version()) >= _vtuple(zver) \
            and enabled() and (not _is_coreelec() or _ffmpeg_present() or _load().get('ffmpeg_tried')):
        return

    def _run():
        if monitor.waitForAbort(delay):
            return
        try:
            from resources.lib import patcher
            lock = patcher._FIRST_RUN_LOCK_FILE
        except Exception:
            lock = ''
        for _ in range(120):                          # up to ~1 h
            busy = (lock and os.path.exists(lock)) or xbmc.getCondVisibility('Player.HasMedia')
            if not busy:
                break
            if monitor.waitForAbort(30):
                return
        try:
            ensure()
        except Exception as e:
            _log('boot ensure failed: %s' % e, xbmc.LOGWARNING)

    t = threading.Thread(target=_run, name='abk-najd-ensure')
    t.daemon = True
    t.start()


# ------------------------------------------------------------------ menu
def summary():
    if not installed_version():
        return T(32352)
    if enabled() and is_default():
        return T(32350)
    return T(32351)


def run():
    """Mods > Najd Smart Subtitles."""
    dlg = xbmcgui.Dialog()
    while True:
        have = installed_version()
        zpath, zver = bundle()
        rows = []
        if have and enabled():
            if is_default():
                rows.append(('off', T(32355)))
            else:
                rows.append(('on', T(32354)))
            rows.append(('wizard', T(32356)))
            rows.append(('settings', T(32357)))
            rows.append(('test', T(32358)))
        if zpath:
            rows.append(('install', '%s (%s)' % (T(32359), zver)))
        if _is_coreelec() and not _ffmpeg_present():
            rows.append(('ffmpeg', T(32365)))
        head = '%s  -  %s' % (T(32348), T(32353) % service_name())
        idx = dlg.select(head, [r[1] for r in rows])
        if idx < 0:
            return
        act = rows[idx][0]
        if act in ('on', 'off'):
            set_default(act == 'on')
            _notify(T(32362) if act == 'on' else T(32363))
        elif act == 'wizard':
            xbmc.executebuiltin('RunScript(%s,wizard)' % NAJD_ID)
            return
        elif act == 'settings':
            xbmc.executebuiltin('Addon.OpenSettings(%s)' % NAJD_ID)
            return
        elif act == 'test':
            xbmc.executebuiltin('RunScript(%s,test)' % NAJD_ID)
            return
        elif act == 'install':
            pd = xbmcgui.DialogProgress()
            pd.create(T(32348), T(32359))
            ok = install_bundled(force=True)
            pd.close()
            if ok:
                if not _load().get('default_set'):
                    set_default(True)
                _notify(T(32360) % installed_version())
            else:
                _notify(T(32361), warn=True)
        elif act == 'ffmpeg':
            pd = xbmcgui.DialogProgress()
            pd.create(T(32348), T(32365))
            ok = install_ffmpeg()
            pd.close()
            _notify(T(32366) if ok else T(32367), warn=not ok)
