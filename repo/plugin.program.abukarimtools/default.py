# -*- coding: utf-8 -*-
"""
ABUKARIM – All-in-One Plugin
Entry point / router.
"""

import sys
import os
from urllib.parse import parse_qsl

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
    'skin_install':    ADDON_PATH + 'resources/icons/skin_installer.png',
    'skin_switch':     ADDON_PATH + 'resources/icons/skin_switcher.png',
    'backup':          ADDON_PATH + 'resources/icons/backup.png',
    'openwizard':      ADDON_PATH + 'resources/icons/openwizard.png',
    'abukarimwizard':  ADDON_PATH + 'resources/icons/abukarimwizard.png',
}

MENU = [
    ('skin_install',   'Skin Selection'),
    ('skin_switch',    'Skin Switcher'),
    ('backup',         'Userdata Backup'),
    ('openwizard',     'OpenWizard'),
    ('abukarimwizard', 'ABUKARIM Wizard'),
]

# Addon IDs of the two wizard plugins that must be installed alongside this one
OPENWIZARD_ID    = 'plugin.program.openwizard'
ABUKARIMWIZARD_ID = 'plugin.program.ABUKARIMwizard'


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


def _launch_addon(addon_id):
    """Close the current directory listing then launch another addon."""
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True,
                               updateListing=False, cacheToDisc=False)
    # Check the addon is actually installed first
    try:
        xbmcaddon.Addon(addon_id)
    except RuntimeError:
        xbmcgui.Dialog().notification(
            'ABUKARIM TOOLS',
            '{} is not installed'.format(addon_id),
            ICONS.get('backup', ''),
            4000
        )
        return
    xbmc.executebuiltin('RunAddon({})'.format(addon_id))


def router():
    params = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    mode   = params.get('mode')

    if mode is None:
        main_menu()
        return

    if mode == 'skin_install':
        xbmcplugin.setContent(HANDLE, 'files')
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True,
                                   updateListing=False, cacheToDisc=False)
        from resources.lib import skin_installer
        skin_installer.run()

    elif mode == 'skin_switch':
        xbmcplugin.setContent(HANDLE, 'files')
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True,
                                   updateListing=False, cacheToDisc=False)
        from resources.lib import skin_switcher
        skin_switcher.run()

    elif mode == 'backup':
        xbmcplugin.setContent(HANDLE, 'files')
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True,
                                   updateListing=False, cacheToDisc=False)
        from resources.lib import backup_manager
        backup_manager.BackupManager().run()

    elif mode == 'openwizard':
        _launch_addon(OPENWIZARD_ID)

    elif mode == 'abukarimwizard':
        _launch_addon(ABUKARIMWIZARD_ID)


router()
