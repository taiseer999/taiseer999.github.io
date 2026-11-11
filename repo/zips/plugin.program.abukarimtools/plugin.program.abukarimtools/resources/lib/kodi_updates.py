# -*- coding: utf-8 -*-
"""
kodi_updates.py - keep Kodi from auto-installing add-on updates while AB Tools
installs add-ons (4.7.12).

Deadlock found with `sample Kodi` on macOS (2026-11-03 08:33, Kodi 23 alpha,
also seen on 22 RC at 07:50 - setup frozen in the restore step):

  JobWorker   CRepositoryUpdater::OnJobComplete
              -> CAddonMgr::CheckAndInstallAddonUpdates   (auto-update ON)
              -> CAddonInstallJob::DoWork -> CSkinInfo::OnPreInstall
              -> CApplicationMessenger::SendMsg (WAITS for the main thread)
              ... while holding the repository updater's lock
  Main thread CBuiltins::Execute("UpdateAddonRepos")
              -> CRepositoryUpdater::CheckForUpdates (WAITS for that lock)

Enabling the restored repositories started a repo check that found a newer
skin; our own UpdateAddonRepos then met it. With general.addonupdates set to
"notify" (1) Kodi never installs on its own, so OnPreInstall is never reached.

    hold()            -> previous value (None = could not read); sets 1 when it was 0
    release(previous) -> puts the previous value back
"""

import json

import xbmc
import xbmcgui

SETTING = 'general.addonupdates'
AUTO, NOTIFY, NEVER = 0, 1, 2
HELD_PROP = 'abk.updates.held'          # Home property: setup holds it for the whole run


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools KodiUpdates] %s' % msg, level)


def _rpc(method, params):
    try:
        out = json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    except Exception as e:
        _log('%s failed: %s' % (method, e), xbmc.LOGWARNING)
        return None
    if 'error' in out:
        _log('%s error: %s' % (method, out['error']), xbmc.LOGWARNING)
        return None
    return out.get('result')


def current():
    res = _rpc('Settings.GetSettingValue', {'setting': SETTING})
    try:
        return int((res or {}).get('value'))
    except (TypeError, ValueError):
        return None


def _set(value):
    return _rpc('Settings.SetSettingValue', {'setting': SETTING, 'value': int(value)}) is not None


def hold():
    """Auto-install off (notify instead). Returns the value to restore later."""
    prev = current()
    if prev == AUTO:
        if _set(NOTIFY):
            _log('add-on auto-updates -> notify while add-ons are installed')
        else:
            _log('could not switch add-on auto-updates off', xbmc.LOGWARNING)
    return prev


def release(prev):
    """Back to what it was - not while the setup holds it for the whole run."""
    if prev is None or prev == current():
        return
    if xbmcgui.Window(10000).getProperty(HELD_PROP):
        return
    if _set(prev):
        _log('add-on auto-updates restored (%s)' % prev)


RESTORE_PROP = 'abk.updates.restore'   # the restored backup's own value (backup_manager)


def setup_hold(st):
    """Setup: hold for the whole apply phase; remember the first value only."""
    prev = hold()
    if 'updates_prev' not in st and prev is not None:
        st['updates_prev'] = prev
    home = xbmcgui.Window(10000)
    home.setProperty(HELD_PROP, '1')
    restored = home.getProperty(RESTORE_PROP)
    if restored.isdigit():              # the backup's value wins at the end
        st['updates_prev'] = int(restored)


def setup_release(st):
    home = xbmcgui.Window(10000)
    home.clearProperty(HELD_PROP)
    restored = home.getProperty(RESTORE_PROP)
    home.clearProperty(RESTORE_PROP)
    if restored.isdigit():
        st['updates_prev'] = int(restored)
    prev = st.get('updates_prev')
    if prev is not None and prev != current() and _set(prev):
        _log('add-on auto-updates restored after setup (%s)' % prev)
