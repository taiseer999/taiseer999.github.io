"""
tools_setup_prompt.py - 3.9.47: after a build install + restart, offer to run
the ABUKARIM TOOLS Installation Wizard.

Called once from the first boot after a build install (Startup.run_startup,
firstrun branch). Waits for Kodi to settle on Home, makes sure AB Tools is
enabled, then asks. "Yes" launches AB Tools' setup directly
(mode=first_run_exec, the same entry its own "Installation Wizard" menu item
uses after its confirm), so the user is not asked twice. "Later" does
nothing - the Installation Wizard stays in AB Tools > Setup.
"""
import json
import os

import xbmc
import xbmcgui
import xbmcvfs

from .addonvar import addon_name, local_string

TOOLS_ID = 'plugin.program.abukarimtools'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[%s SetupPrompt] %s' % (addon_name, msg), level)


def _s(sid, fallback):
    try:
        return local_string(sid) or fallback
    except Exception:
        return fallback


def _tools_present():
    return os.path.isfile(xbmcvfs.translatePath(
        'special://home/addons/%s/addon.xml' % TOOLS_ID))


def _tools_enabled():
    return xbmc.getCondVisibility('System.HasAddon(%s)' % TOOLS_ID)


def _enable_tools():
    req = {'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled',
           'params': {'addonid': TOOLS_ID, 'enabled': True}}
    try:
        xbmc.executeJSONRPC(json.dumps(req))
    except Exception as e:
        _log('enable AB Tools failed: %s' % e, xbmc.LOGWARNING)


def _wait(cond, seconds, monitor):
    """Poll cond() every second; False on timeout or Kodi abort."""
    for _ in range(int(seconds)):
        if cond():
            return True
        if monitor.waitForAbort(1):
            return False
    return cond()


def _settled():
    return (xbmc.getCondVisibility('Window.IsVisible(home)')
            and not xbmc.getCondVisibility('System.HasActiveModalDialog')
            and not xbmc.getCondVisibility('Window.IsActive(busydialog)')
            and not xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'))


def run():
    """Never raises."""
    try:
        monitor = xbmc.Monitor()
        if not _tools_present():
            _log('AB Tools not installed - no setup prompt')
            return False
        if not _tools_enabled():
            _enable_tools()
            if not _wait(_tools_enabled, 20, monitor):
                _log('AB Tools could not be enabled - no setup prompt',
                     xbmc.LOGWARNING)
                return False
        # Let the skin, add-on services and their start-up toasts finish.
        if not _wait(_settled, 120, monitor):
            _log('Home never settled - no setup prompt', xbmc.LOGWARNING)
            return False
        if monitor.waitForAbort(3) or not _wait(_settled, 30, monitor):
            return False
        go = xbmcgui.Dialog().yesno(
            addon_name,
            _s(30998, 'The build is installed.[CR][CR]Run the ABUKARIM TOOLS '
                      'Installation Wizard now to finish setting up this box '
                      '(skin, restore, add-ons, lists and patches)?'),
            yeslabel=_s(30999, 'Run now'), nolabel=_s(31000, 'Later'))
        if not go:
            _log('user chose Later')
            return False
        _log('launching AB Tools Installation Wizard')
        xbmc.executebuiltin('RunPlugin(plugin://%s/?mode=first_run_exec)' % TOOLS_ID)
        return True
    except Exception as e:
        _log('setup prompt failed: %s' % e, xbmc.LOGERROR)
        return False
