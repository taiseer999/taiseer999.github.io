# -*- coding: utf-8 -*-
"""
ABUKARIM – All-in-One Plugin
Entry point / router.
"""

import sys
from urllib.parse import parse_qsl

import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
HANDLE     = int(sys.argv[1]) if len(sys.argv) > 1 else -1
ADDON_PATH = xbmcvfs.translatePath('special://home/addons/%s/' % ADDON_ID)

FANART = ADDON_PATH + 'fanart.jpg'
ICONS  = {
    'skin_install': ADDON_PATH + 'resources/icons/skin_installer.png',
    'skin_switch':  ADDON_PATH + 'resources/icons/skin_switcher.png',
    'backup':       ADDON_PATH + 'resources/icons/backup.png',
}

MENU = [
    ('skin_install', 'Skin Selection'),
    ('skin_switch',  'Skin Switcher'),
    ('backup',       'Userdata Backup'),
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


def router():
    params = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    mode   = params.get('mode')

    if mode is None:
        main_menu()
        return

    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

    if mode == 'skin_install':
        from resources.lib import skin_installer
        skin_installer.run()
    elif mode == 'skin_switch':
        from resources.lib import skin_switcher
        skin_switcher.run()
    elif mode == 'backup':
        from resources.lib import backup_manager
        backup_manager.BackupManager().run()


router()
