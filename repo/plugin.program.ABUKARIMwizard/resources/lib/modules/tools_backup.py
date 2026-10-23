"""
Optional ABUKARIM TOOLS backup before a build install (3.9.44; was mandatory
in 3.9.42-3.9.43).

build_install() calls offer_tools_backup() right after the user confirms the
install:

    Back up your setup with ABUKARIM TOOLS first?
        [Back up]   [Skip backup]   [Cancel install]

Back up      -> ABUKARIM TOOLS backup; if it is not completed:
                [Retry backup] [Install without backup] [Cancel install]
Skip backup  -> install goes ahead without a backup
Back / Cancel install -> nothing is changed on the box
ABUKARIM TOOLS missing -> a notification, install goes ahead.

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


def _ask(message, yeslabel, nolabel):
    """yes = 1, no = 0, Cancel install (custom button) / Back = -1."""
    res = xbmcgui.Dialog().yesnocustom(
        addon_name, message,
        customlabel=_s(30383, 'Cancel install'),
        nolabel=nolabel, yeslabel=yeslabel,
        defaultbutton=xbmcgui.DLG_YESNO_YES_BTN)
    if res == 1:
        return 1
    if res == 0:
        return 0
    return -1          # 2 = Cancel install, -1 = Back / dismissed


def offer_tools_backup():
    """Optional step before a build install. Returns True to continue the
    install, False to cancel it (nothing changed yet)."""
    if not _ensure_tools_enabled():
        _log('ABUKARIM TOOLS not installed - installing without a backup.',
             xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(addon_name, _s(
            30380, 'ABUKARIM TOOLS is not installed - continuing without a '
                   'backup.'), xbmcgui.NOTIFICATION_WARNING, 5000)
        return True

    choice = _ask(_s(30381, 'Back up your setup with ABUKARIM TOOLS before '
                            'the build is installed? (Recommended)'),
                  _s(30385, 'Back up'), _s(30386, 'Skip backup'))
    if choice < 0:
        _log('User cancelled - build install aborted.')
        return False
    if choice == 0:
        _log('User skipped the backup - continuing with build install.')
        return True

    while True:
        if _run_tools_backup():
            _log('Backup done - continuing with build install.')
            return True
        choice = _ask(_s(30382, 'The backup was not completed.[CR]Retry the '
                                'backup, install without a backup, or cancel '
                                'the install?'),
                      _s(30384, 'Retry backup'),
                      _s(30387, 'Install without backup'))
        if choice < 0:
            _log('User cancelled - build install aborted.')
            return False
        if choice == 0:
            _log('Backup not completed - user chose to install without it.')
            return True


# Old name (3.9.42-3.9.43), kept so nothing that still imports it breaks.
require_tools_backup = offer_tools_backup
