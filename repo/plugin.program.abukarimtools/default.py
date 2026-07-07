# -*- coding: utf-8 -*-
import sys
import os
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
HANDLE     = int(sys.argv[1]) if len(sys.argv) > 1 else -1
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
if not ADDON_PATH.endswith('/') and not ADDON_PATH.endswith('\\'):
    ADDON_PATH += '/'

FANART = ADDON_PATH + 'fanart.jpg'
ICONS  = {
    'skin_install':   ADDON_PATH + 'resources/icons/skin_installer.png',
    'skin_switch':    ADDON_PATH + 'resources/icons/skin_switcher.png',
    'backup':         ADDON_PATH + 'resources/icons/backup.png',
    'openwizard':     ADDON_PATH + 'resources/icons/openwizard.png',
    'patcher':        ADDON_PATH + 'resources/icons/patcher.png',
    'binary_install': ADDON_PATH + 'resources/icons/binary_install.png',
    'first_run':      ADDON_PATH + 'resources/icons/first_run.png',
    'am6b_fix':       ADDON_PATH + 'resources/icons/am6b_fix.png',
}

MENU = [
    ('first_run',      'Run First-Time Setup'),
    ('backup',         'Backup/Restore'),
    ('skin_install',   'Skin Selection'),
    ('binary_install', 'New Build Tools'),
    ('patcher',        'Apply Patches'),
    ('am6b_fix',       'AM6B CoreELEC Fix (AF3 GBM Flicker)'),
    ('openwizard',     'OpenWizard'),
    ('skin_switch',    'Skin Switcher'),
]


def _add_item(label, mode):
    url = sys.argv[0] + '?mode=' + mode
    li  = xbmcgui.ListItem(label)
    li.setArt({'icon': ICONS[mode], 'thumb': ICONS[mode], 'fanart': FANART})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, True)


def main_menu():
    for mode, label in MENU:
        _add_item(label, mode)
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE)


def _end_directory():
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True,
                               updateListing=False, cacheToDisc=False)


def router():
    raw     = sys.argv[2][1:] if len(sys.argv) > 2 else ''
    params  = dict(parse_qsl(raw))
    mode    = params.get('mode')
    wizard  = params.get('wizard')   # set when a wizard sub-page is clicked

    # --- Wizard sub-navigation (re-entry from a wizard menu item click) ---
    if wizard:
        # Strip 'wizard' key; pass everything else back as the paramstring
        sub_params = {k: v for k, v in params.items() if k != 'wizard'}
        paramstring = urlencode(sub_params)
        from resources.lib.wizard_runner import run_openwizard
        if wizard == 'openwizard':
            run_openwizard(HANDLE, ADDON_PATH, paramstring)
        return

    # --- Top-level menu ---
    if mode is None:
        main_menu()
        return

    if mode == 'first_run':
        _end_directory()
        # Run the same first-run sequence the service runs on first boot,
        # on demand. Confirm first so it isn't triggered by accident.
        if xbmcgui.Dialog().yesno(
                'ABUKARIM TOOLS',
                'Run first-time setup now?\n\n'
                'This installs binaries, offers a backup restore, '
                'then opens the Skin Installer.',
                yeslabel='Run setup', nolabel='Cancel'):
            import_root = ADDON_PATH.rstrip('/\\')
            if import_root not in sys.path:
                sys.path.insert(0, import_root)
            import service
            service.run_now(remove_flag=True, force=True)
        return

    if mode == 'skin_install':
        _end_directory()
        from resources.lib import skin_installer
        skin_installer.run()

    elif mode == 'skin_switch':
        _end_directory()
        from resources.lib import skin_switcher
        skin_switcher.run()

    elif mode == 'backup':
        _end_directory()
        from resources.lib import backup_manager
        backup_manager.BackupManager().run()

    elif mode == 'openwizard':
        from resources.lib.wizard_runner import run_openwizard
        run_openwizard(HANDLE, ADDON_PATH)

    elif mode == 'patcher':
        _end_directory()
        from resources.lib import patcher
        patcher.run()

    elif mode == 'am6b_fix':
        _end_directory()
        from resources.lib import af3_gbm_fix
        af3_gbm_fix.run()

    elif mode == 'binary_install':
        _end_directory()
        from resources.lib import binary_installer
        binary_installer.run()


router()
