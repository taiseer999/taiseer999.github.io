# -*- coding: utf-8 -*-
"""
tmdbh_auth.py - Installation Wizard: link Trakt and MDbList in TMDb Helper (4.7.9).

Question (asked with the others, nothing happens yet): which accounts to
link - Trakt and/or MDbList, both ticked unless already linked.

Step 'tmdbh_auth' (after Patches, so TMDb Helper's sign-in already opens in
the AB Tools QR window): for each ticked account that is not linked yet,
TMDb Helper's own sign-in is started and the wizard waits until the token
arrives or the window is closed (Back = skip that account).

    Trakt    RunScript(plugin.video.themoviedb.helper,authenticate_trakt)
             every version; token in the 'trakt_token' setting
    MDbList  RunScript(plugin.video.themoviedb.helper,authenticate_mdblist)
             TMDb Helper 7.x (multiservice) - OAuth device code; token in
             'mdblist_token'. 6.x (6.20+) has no MDbList sign-in: the key
             lives in script.module.tmdbhelper.sync.mdblist ('apikey'), so
             a QR to the MDbList key page is shown, then that module's
             settings open; linked = the key is there afterwards (4.7.10).
"""

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.i18n import T

TMDBH = 'plugin.video.themoviedb.helper'
MDB_MODULE = 'script.module.tmdbhelper.sync.mdblist'
MDB_KEY_PAGE = 'https://mdblist.com/preferences/'
SERVICES = (('trakt', 'Trakt', 30978), ('mdblist', 'MDbList', 30979))
QR_WINDOW = 'trakt_auth_qr.xml'
WAIT_MAX = 900          # a device code lives 10 min (Trakt) / 5 min (MDbList)
NEVER_SHOWN = 40        # no sign-in window at all after this many seconds


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools TMDbHAuth] %s' % msg, level)


def _addon(aid=TMDBH):
    try:
        return xbmcaddon.Addon(aid)
    except Exception:
        return None


def mdblist_key():
    """MDbList API key: the 6.20 sync module first, then the old TMDb Helper setting."""
    for aid, sid in ((MDB_MODULE, 'apikey'), (TMDBH, 'mdblist_apikey')):
        a = _addon(aid)
        if a is not None:
            key = (a.getSetting(sid) or '').strip()
            if key:
                return key
    return ''


def mdblist_supported():
    """TMDb Helper with the MDbList device sign-in (the multiservice 7.x)."""
    a = _addon()
    if a is None:
        return False
    path = os.path.join(a.getAddonInfo('path'), 'resources', 'tmdbhelper', 'lib',
                        'api', 'mdblist', 'api.py')
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return 'device-authorization' in f.read()
    except OSError:
        return False


def token(service):
    """The stored access token ('' = not linked)."""
    a = _addon()
    if a is None:
        return ''
    if service == 'trakt':
        for raw in (xbmcgui.Window(10000).getProperty('TMDbHelper.TraktUserToken'),
                    a.getSetting('trakt_token')):
            try:
                tok = json.loads(raw) if raw else {}
            except ValueError:
                tok = {}
            if isinstance(tok, dict) and tok.get('access_token'):
                return tok['access_token']
        return ''
    if mdblist_supported():
        return (a.getSetting('mdblist_token') or '').strip()
    return mdblist_key()


def linked(service):
    return bool(token(service))


# ---------------------------------------------------------------------------
# question
# ---------------------------------------------------------------------------

def ask(prev=None):
    """Ticked services (list of ids). Back = none."""
    labels, pre = [], []
    for i, (sid, name, _lab) in enumerate(SERVICES):
        state = T(30982) if linked(sid) else ''
        labels.append('%s%s' % (T(30984) % name, ('  -  ' + state) if state else ''))
        if (sid in prev) if prev is not None else not linked(sid):
            pre.append(i)
    for _ in range(4):
        started = time.time()
        picked = xbmcgui.Dialog().multiselect(T(30977), labels, preselect=pre)
        if picked is not None or time.time() - started >= 1.0:
            break
        xbmc.sleep(1200)            # torn down before anyone could answer
    picked = picked or []
    out = [SERVICES[i][0] for i in picked]
    _log('link in TMDb Helper: %s' % (out or 'none'))
    return out


def summary(services):
    names = dict((s, n) for s, n, _l in SERVICES)
    return ', '.join(names[s] for s in services if s in names) or T(30931)


# ---------------------------------------------------------------------------
# step
# ---------------------------------------------------------------------------

def _signin_visible():
    return xbmc.getCondVisibility(
        'System.HasModalDialog | Window.IsVisible(%s) | Window.IsActive(progressdialog)'
        % QR_WINDOW)


def wait_link(service, old='', monitor=None):
    """After TMDb Helper's sign-in was started: the new token, or '' when the
    window was closed / never opened / the code expired. The QR window is a
    modeless dialog (show(), not doModal), so System.HasModalDialog alone
    cannot see it - it is also looked for by its XML name."""
    mon = monitor or xbmc.Monitor()
    started = time.time()
    seen, gone = False, 0
    while time.time() - started < WAIT_MAX:
        if mon.waitForAbort(1):
            return ''
        tok = token(service)
        if tok and tok != old:
            xbmc.sleep(1500)        # let TMDb Helper close its window
            return tok
        if _signin_visible():
            seen, gone = True, 0
        elif seen:
            gone += 1
            if gone >= 3:           # closed for 3 s: Back or expired
                break
        elif time.time() - started > NEVER_SHOWN:
            _log('%s: the sign-in window never opened' % service, xbmc.LOGWARNING)
            break
    tok = token(service)
    return tok if tok and tok != old else ''


def _link_mdblist_key(monitor=None):
    """TMDb Helper 6.x: the MDbList API key in the sync module's settings."""
    if _addon(MDB_MODULE) is None:
        return False, 'sync module %s not installed' % MDB_MODULE
    try:
        from resources.lib import qr_view
        qr_view.show('MDbList', T(30985) % MDB_KEY_PAGE.replace('https://', ''), MDB_KEY_PAGE,
                     hint=T(30986))
    except Exception as e:
        _log('key page QR not shown: %s' % e, xbmc.LOGWARNING)
    xbmc.executebuiltin('Addon.OpenSettings(%s)' % MDB_MODULE)
    mon = monitor or xbmc.Monitor()
    opened = False
    for _ in range(40):                     # wait for the settings window
        if xbmc.getCondVisibility('Window.IsActive(addonsettings)'):
            opened = True
            break
        if mon.waitForAbort(0.25):
            return False, 'aborted'
    started = time.time()
    while opened and xbmc.getCondVisibility('Window.IsActive(addonsettings)'):
        if mon.waitForAbort(0.5) or time.time() - started > WAIT_MAX:
            break
    ok = bool(mdblist_key())
    return ok, ('API key saved' if ok else 'no API key entered')


def link(service, monitor=None):
    """Start TMDb Helper's sign-in and wait. Returns (ok, note)."""
    name = dict((s, n) for s, n, _l in SERVICES)[service]
    old = token(service)
    if service == 'mdblist' and not mdblist_supported():
        ok, note = _link_mdblist_key(monitor)
        _log('%s: %s' % (name, note))
        return ok, note
    if service == 'mdblist':
        a = _addon()
        if a is not None and a.getSetting('service_mdblist').lower() == 'false':
            a.setSetting('service_mdblist', 'true')     # the Accounts switch
    xbmcgui.Dialog().notification(name, T(30983) % name, xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.executebuiltin('RunScript(%s,authenticate_%s)' % (TMDBH, service))
    tok = wait_link(service, old, monitor)
    _log('%s: %s' % (name, 'linked' if tok else 'not linked'))
    return bool(tok), ('linked' if tok else 'not linked')


def apply(services, ctx=None, monitor=None):
    """Returns (status, detail)."""
    if services is None:
        return 'skipped', 'not asked'
    if not services:
        return 'skipped', 'none chosen'
    if _addon() is None:
        return 'skipped', 'TMDb Helper not installed'
    notes, linked_n = [], 0
    for sid, name, _lab in SERVICES:
        if sid not in services:
            continue
        if linked(sid):
            notes.append('%s: already linked' % name)
            linked_n += 1
            continue
        if ctx is not None and monitor is not None:
            ctx._wait_no_modal(monitor)
        try:
            ok, note = link(sid, monitor)
        except Exception as e:
            ok, note = False, 'error: %s' % e
            _log('%s failed: %s' % (name, e), xbmc.LOGWARNING)
        linked_n += 1 if ok else 0
        notes.append('%s: %s' % (name, note))
    # a skipped sign-in is the user's choice, not a failure of the setup
    return ('ok' if linked_n else 'skipped'), '; '.join(notes)
