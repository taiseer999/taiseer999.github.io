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
    'dplex_toggle':   ADDON_PATH + 'resources/icons/dplex_toggle.png',
    'korean_toggle':  ADDON_PATH + 'resources/icons/korean_toggle.png',
    'origin_fix':     ADDON_PATH + 'resources/icons/patcher.png',
    'autopatch':      ADDON_PATH + 'resources/icons/patcher.png',
    'select_patches': ADDON_PATH + 'resources/icons/patcher.png',
    'total_clean':    ADDON_PATH + 'resources/icons/clear_cache.png',
    'old_thumbs':     ADDON_PATH + 'resources/icons/clear_cache.png',
}

MENU = [
    ('first_run',      30001),
    ('backup',         30002),
    ('skin_install',   30003),
    ('binary_install', 30004),
    ('patcher',        30005),
    ('select_patches', 30326),
    ('autopatch',      30006),
    ('origin_fix',     30007),
    ('openwizard',     30008),
    ('total_clean',    30012),
    ('old_thumbs',     30013),
    ('skin_switch',    30009),
    ('dplex_toggle',   30010),
    ('korean_toggle',  30011),
]


def _add_item(label, mode, is_folder=True):
    url = sys.argv[0] + '?mode=' + mode
    li  = xbmcgui.ListItem(label)
    li.setArt({'icon': ICONS[mode], 'thumb': ICONS[mode], 'fanart': FANART})
    if not is_folder:
        li.setProperty('IsPlayable', 'false')
    xbmcplugin.addDirectoryItem(HANDLE, url, li, is_folder)


def _ensure_fallback_font():
    """Self-heal: install the Arabic-capable global fallback font when the menu
    is opened, so Arabic is readable even if the boot service didn't run (e.g.
    service disabled, or on the very first open before a restart). Best-effort;
    a change only takes effect on the next Kodi start."""
    try:
        from resources.lib import font_fallback
        font_fallback.install()
    except Exception:
        pass


def main_menu():
    from resources.lib.i18n import T
    _ensure_fallback_font()
    for mode, label_id in MENU:
        _add_item(T(label_id), mode, is_folder=(mode != 'skin_switch'))
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
        from resources.lib.i18n import T
        if xbmcgui.Dialog().yesno(
                'ABUKARIM TOOLS',
                T(30050),
                yeslabel=T(30051), nolabel=T(30052)):
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
        # Non-folder action: don't open/close a plugin listing (that leaves an
        # empty container with a back arrow). Just run; the switcher returns to
        # the main menu itself via _return_to_abukarim().
        from resources.lib import skin_switcher
        skin_switcher.run()

    elif mode == 'backup':
        _end_directory()
        from resources.lib import backup_manager
        backup_manager.BackupManager().run()

    elif mode == 'openwizard':
        from resources.lib.wizard_runner import run_openwizard
        run_openwizard(HANDLE, ADDON_PATH)

    elif mode == 'total_clean':
        _end_directory()
        from resources.lib.wizard_runner import run_openwizard_total_clean
        run_openwizard_total_clean(ADDON_PATH)

    elif mode == 'old_thumbs':
        _end_directory()
        from resources.lib.wizard_runner import run_openwizard_old_thumbs
        run_openwizard_old_thumbs(ADDON_PATH)

    elif mode == 'patcher':
        _end_directory()
        from resources.lib import patcher
        patcher.run()

    elif mode == 'select_patches':
        from resources.lib import patcher
        patcher.run_selectable()

    elif mode == 'autopatch':
        _end_directory()
        from resources.lib import patch_watchdog
        patch_watchdog.run()

    elif mode == 'binary_install':
        _end_directory()
        from resources.lib import binary_installer
        binary_installer.run()

    elif mode == 'dplex_toggle':
        _end_directory()
        from resources.lib import dplex_toggle
        dplex_toggle.run()

    elif mode == 'korean_toggle':
        _end_directory()
        from resources.lib import korean_toggle
        korean_toggle.run()

    elif mode == 'origin_fix':
        _end_directory()
        from resources.lib import origin_fix
        origin_fix.run()


router()
