"""
Mandatory ABUKARIM TOOLS backup before a build install.

build_install() calls require_tools_backup() right after the user confirms
the install. The install only goes ahead once ABUKARIM TOOLS has written a
new backup zip. If ABUKARIM TOOLS is missing, the backup is cancelled or
fails, the install is aborted (the user can retry the backup first).

How the backup is run: ABUKARIM TOOLS' own backup_manager.BackupManager
._do_backup(dialog, set(SKIN_ADDONS)) - the same call its Backup/Restore menu
makes, so the user gets the normal ABUKARIM TOOLS backup (folder picker,
progress, menus/widgets included).

Both add-ons ship a top-level package called `resources`, and the wizard's is
already imported. To load the TOOLS module without clashing, the wizard's
`resources*` entries are lifted out of sys.modules for the duration of the
call and put back afterwards (also on error).
"""
import os
import sys
import json
import time
import traceback

import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

from .addonvar import addon_name, local_string

TOOLS_ID = 'plugin.program.abukarimtools'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[ABUKARIMwizard ToolsBackup] %s' % msg, level)


def _s(sid, fallback):
    try:
        return local_string(sid) or fallback
    except Exception:
        return fallback


# --------------------------------------------------------------------------
#  ABUKARIM TOOLS presence
# --------------------------------------------------------------------------
def _tools_state():
    """Return 'enabled', 'disabled' or 'missing' (JSON-RPC keeps the real state;
    System.HasAddon is true for disabled add-ons)."""
    try:
        req = {'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.GetAddonDetails',
               'params': {'addonid': TOOLS_ID, 'properties': ['enabled']}}
        res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
        if 'error' in res:
            return 'missing'
        return 'enabled' if res['result']['addon'].get('enabled') else 'disabled'
    except Exception:
        try:
            xbmcaddon.Addon(TOOLS_ID)
            return 'enabled'
        except Exception:
            return 'missing'


def _ensure_tools_enabled():
    state = _tools_state()
    if state == 'disabled':
        _log('ABUKARIM TOOLS is disabled - enabling it.')
        req = {'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled',
               'params': {'addonid': TOOLS_ID, 'enabled': True}}
        xbmc.executeJSONRPC(json.dumps(req))
        for _ in range(20):
            xbmc.sleep(250)
            if _tools_state() == 'enabled':
                break
        state = _tools_state()
    return state == 'enabled'


def _tools_path():
    return xbmcvfs.translatePath(xbmcaddon.Addon(TOOLS_ID).getAddonInfo('path'))


# --------------------------------------------------------------------------
#  Dialog proxy: remembers which folder the user picked for the backup
# --------------------------------------------------------------------------
class _DialogSpy(object):
    def __init__(self):
        self._d = xbmcgui.Dialog()
        self.folders = []

    def browse(self, *args, **kwargs):
        res = self._d.browse(*args, **kwargs)
        btype = args[0] if args else kwargs.get('type')
        if btype in (0, 3) and res:
            self.folders.append(res)
        return res

    def __getattr__(self, name):
        return getattr(self._d, name)


def _new_zip_in(folder, since):
    """True if `folder` holds a .zip modified at/after `since`."""
    try:
        if not folder.endswith(('/', '\\')):
            folder += '/'
        _dirs, files = xbmcvfs.listdir(folder)
        for f in files:
            if not f.lower().endswith('.zip'):
                continue
            path = folder + f
            try:
                mtime = xbmcvfs.Stat(path).st_mtime()
            except Exception:
                local = xbmcvfs.translatePath(path)
                mtime = os.path.getmtime(local) if os.path.exists(local) else 0
            if mtime >= since - 2:
                _log('New backup found: %s' % path)
                return True
    except Exception:
        _log('Could not list %s:\n%s' % (folder, traceback.format_exc()),
             xbmc.LOGWARNING)
    return False


# --------------------------------------------------------------------------
#  Run the TOOLS backup
# --------------------------------------------------------------------------
def _run_tools_backup():
    """Run ABUKARIM TOOLS' backup once. Returns True if a new zip was written."""
    tools_path = _tools_path()
    saved_mods = {k: v for k, v in sys.modules.items()
                  if k == 'resources' or k.startswith('resources.')}
    saved_path = list(sys.path)
    spy = _DialogSpy()
    started = time.time()
    try:
        for k in saved_mods:
            del sys.modules[k]
        sys.path.insert(0, tools_path)
        from resources.lib import backup_manager  # TOOLS' module
        bm = backup_manager.BackupManager()
        include_skin = set(getattr(backup_manager, 'SKIN_ADDONS', []) or [])
        _log('Running ABUKARIM TOOLS backup from %s' % tools_path)
        result = bm._do_backup(spy, include_skin)
    except Exception:
        _log('ABUKARIM TOOLS backup failed:\n%s' % traceback.format_exc(),
             xbmc.LOGERROR)
        return False
    finally:
        for k in [k for k in sys.modules
                  if k == 'resources' or k.startswith('resources.')]:
            del sys.modules[k]
        sys.modules.update(saved_mods)
        sys.path[:] = saved_path

    if result is False:
        return False
    if not spy.folders:
        # No folder picker seen: a TOOLS version that saves to a fixed place
        # counts only if it reports success itself.
        _log('No destination picked (result=%r).' % (result,))
        return result is True
    return any(_new_zip_in(f, started) for f in spy.folders)


def require_tools_backup():
    """Mandatory step before a build install. Returns True to continue."""
    if not _ensure_tools_enabled():
        _log('ABUKARIM TOOLS not installed - build install blocked.',
             xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(addon_name, _s(
            30380,
            'ABUKARIM TOOLS is required to back up your setup before a build '
            'is installed.[CR]Install ABUKARIM TOOLS first, then try again.'))
        return False

    xbmcgui.Dialog().ok(addon_name, _s(
        30381,
        'Before the build is installed, ABUKARIM TOOLS will back up your '
        'setup.[CR]Choose where to save the backup.'))

    while True:
        if _run_tools_backup():
            _log('Backup done - continuing with build install.')
            return True
        if not xbmcgui.Dialog().yesno(
                addon_name,
                _s(30382, 'The backup was not completed. The build cannot be '
                          'installed without a backup.'),
                nolabel=_s(30383, 'Cancel install'),
                yeslabel=_s(30384, 'Retry backup')):
            _log('User cancelled - build install aborted.')
            return False
