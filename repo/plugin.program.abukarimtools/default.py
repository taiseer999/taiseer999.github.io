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
    'total_clean':    ADDON_PATH + 'resources/icons/clear_cache.png',
    'old_thumbs':     ADDON_PATH + 'resources/icons/clear_cache.png',
    # category folder icons
    'cat_setup':      ADDON_PATH + 'resources/icons/first_run.png',
    'cat_patch':      ADDON_PATH + 'resources/icons/patcher.png',
    'cat_maint':      ADDON_PATH + 'resources/icons/clear_cache.png',
    'cat_toggle':     ADDON_PATH + 'resources/icons/skin_switcher.png',
}

# Grouped menu: each category is (cat_key, category_label_id, icon_key, [items])
# where each item is (mode, label_id). Folder vs. action is decided per-mode
# below (only 'skin_switch' is a non-folder top-level action historically;
# inside a category, every entry is a leaf action).
CATEGORIES = [
    ('setup',  30014, 'cat_setup', [
        ('first_run',      30001),
        ('backup',         30002),
        ('skin_install',   30003),
        ('binary_install', 30004),
    ]),
    ('patch',  30015, 'cat_patch', [
        ('patcher',        30005),
        ('autopatch',      30006),
        ('origin_fix',     30007),
    ]),
    ('maint',  30016, 'cat_maint', [
        ('openwizard',     30008),
        ('total_clean',    30012),
        ('old_thumbs',     30013),
    ]),
    ('toggle', 30017, 'cat_toggle', [
        ('skin_switch',    30009),
        ('dplex_toggle',   30010),
        ('korean_toggle',  30011),
    ]),
]

# Modes that are leaf actions (run then return), not plugin folders.
ACTION_MODES = {'skin_switch'}


def _add_folder(label, cat_key, icon_key):
    url = sys.argv[0] + '?cat=' + cat_key
    li  = xbmcgui.ListItem(label)
    li.setArt({'icon': ICONS[icon_key], 'thumb': ICONS[icon_key], 'fanart': FANART})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)


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


def _ensure_patches():
    """Self-heal: re-apply the automatic patch set when the menu is opened, in
    case the background watchdog service never ran this session (e.g. Kodi did
    not launch the freshly-registered xbmc.service after an in-place update, or
    the kill switch/service was disabled). Runs in a daemon thread so opening
    the menu is never blocked; every patch is idempotent, so a redundant sweep
    writes nothing. Honours the same autopatch.off kill switch as the watchdog.
    """
    try:
        from resources.lib import patch_watchdog
        if not patch_watchdog.is_enabled():
            return
        import threading
        from resources.lib import patcher

        def _sweep():
            try:
                ids = [a for a in patcher.target_addon_ids() if patch_watchdog._addon_path(a)]
                if ids:
                    patcher.apply_set(addon_ids=ids)
            except Exception:
                pass

        threading.Thread(target=_sweep, name='AbukarimMenuPatchSweep',
                         daemon=True).start()
    except Exception:
        pass


def main_menu():
    from resources.lib.i18n import T
    _ensure_fallback_font()
    _ensure_patches()
    for cat_key, label_id, icon_key, _items in CATEGORIES:
        _add_folder(T(label_id), cat_key, icon_key)
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE)


def category_menu(cat_key):
    from resources.lib.i18n import T
    for c_key, _label_id, _icon, items in CATEGORIES:
        if c_key != cat_key:
            continue
        for mode, label_id in items:
            _add_item(T(label_id), mode, is_folder=(mode not in ACTION_MODES))
        break
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
    cat     = params.get('cat')      # set when a category folder is opened
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

    # --- Category folder ---
    if cat is not None and mode is None:
        category_menu(cat)
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
