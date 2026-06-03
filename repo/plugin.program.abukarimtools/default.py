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
    'abukarimwizard': ADDON_PATH + 'resources/icons/abukarimwizard.png',
}

MENU = [
    ('skin_install',   'Skin Selection'),
    ('skin_switch',    'Skin Switcher'),
    ('backup',         'Userdata Backup'),
    ('openwizard',     'OpenWizard'),
    ('abukarimwizard', 'ABUKARIM Wizard'),
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
        from resources.lib.wizard_runner import run_openwizard, run_abukarimwizard
        if wizard == 'openwizard':
            run_openwizard(HANDLE, ADDON_PATH, paramstring)
        elif wizard == 'abukarimwizard':
            run_abukarimwizard(HANDLE, ADDON_PATH, paramstring)
        return

    # --- Top-level menu ---
    if mode is None:
        main_menu()
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

    elif mode == 'abukarimwizard':
        from resources.lib.wizard_runner import run_abukarimwizard
        run_abukarimwizard(HANDLE, ADDON_PATH)


router()
