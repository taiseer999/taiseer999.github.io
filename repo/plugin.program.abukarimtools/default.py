# -*- coding: utf-8 -*-
import sys
import os
from urllib.parse import parse_qsl

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON      = xbmcaddon.Addon('plugin.program.abukarimtools')
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
    'abukarimwizard': ADDON_PATH + 'resources/icons/abukarimwizard.png',
    'patcher':        ADDON_PATH + 'resources/icons/patcher.png',
    'binary_install': ADDON_PATH + 'resources/icons/binary_install.png',
    'first_run':      ADDON_PATH + 'resources/icons/first_run.png',
    'dplex_toggle':   ADDON_PATH + 'resources/icons/dplex_toggle.png',
    'korean_toggle':  ADDON_PATH + 'resources/icons/korean_toggle.png',
    'icons_toggle':   ADDON_PATH + 'resources/icons/icons_toggle.png',
    'origin_fix':     ADDON_PATH + 'resources/icons/sources.png',
    'rebuild_addons33': ADDON_PATH + 'resources/icons/rebuild_addons33.png',
    'total_clean':    ADDON_PATH + 'resources/icons/clear_cache.png',
    'old_thumbs':     ADDON_PATH + 'resources/icons/clear_cache.png',
    'speedtest':      ADDON_PATH + 'resources/icons/speedtest.png',
    'addon_portal':   ADDON_PATH + 'resources/icons/addon_portal.png',
    # category folder icons
    'cat_setup':      ADDON_PATH + 'resources/icons/install_setup.png',
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
        ('addon_portal',   30021),
        ('binary_install', 30004),
    ]),
    ('patch',  30015, 'cat_patch', [
        ('patcher',        30005),
        ('origin_fix',     30007),
    ]),
    ('maint',  30016, 'cat_maint', [
        ('abukarimwizard', 30008),
        ('total_clean',    30012),
        ('old_thumbs',     30013),
        ('rebuild_addons33', 30018),
        ('speedtest',      30019),
    ]),
    ('toggle', 30017, 'cat_toggle', [
        ('skin_switch',    30009),
        ('dplex_toggle',   30010),
        ('korean_toggle',  30011),
        ('icons_toggle',   30020),
    ]),
]

# Modes that are leaf actions (run then return), not plugin folders.
ACTION_MODES = {'skin_switch', 'first_run', 'abukarimwizard',
                'total_clean', 'old_thumbs'}


def _add_folder(label, cat_key, icon_key):
    url = sys.argv[0] + '?cat=' + cat_key
    li  = xbmcgui.ListItem(label)
    li.setArt({'icon': ICONS[icon_key], 'thumb': ICONS[icon_key], 'fanart': FANART})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)


def _add_item(label, mode, is_folder=True):
    url = sys.argv[0] + '?mode=' + mode
    if mode == 'abukarimwizard':
        # Installed: link straight into the wizard's Maintenance menu, so it
        # opens with its own add-on context and Back returns here. Missing:
        # keep our own mode, which offers to install it.
        from resources.lib import wizard_runner
        if wizard_runner.wizard_installed():
            url = wizard_runner.wizard_url(wizard_runner.MODE_MAINTENANCE)
            is_folder = True
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
    case the background watchdog service never ran this session.

    3.1.0.11: no longer a daemon thread inside this plugin invocation. The
    plugin exits in milliseconds and Kodi finalized the interpreter while the
    thread was mid-sweep, which on Kodi 22 / Python 3.14 stopped the menu from
    opening. The sweep now runs as its own RunPlugin invocation (mode
    'menu_sweep'), synchronously on that invocation's main thread, so the menu
    never waits on it and nothing is left running when either script ends.
    Every patch is idempotent, so a redundant sweep writes nothing.
    """
    try:
        xbmc.executebuiltin('RunPlugin(plugin://%s/?mode=menu_sweep)' % ADDON_ID)
    except Exception:
        pass


def _menu_sweep():
    """Body of the 'menu_sweep' invocation. Main thread, no directory."""
    try:
        from resources.lib import patch_watchdog, patcher
        if patch_watchdog.first_run_active():
            return                      # never sweep under first-run dialogs
        ids = [a for a in patcher.target_addon_ids() if patch_watchdog._addon_path(a)]
        if ids:
            patcher.apply_set(addon_ids=ids)
            patcher.reload_skin_if_pending()
    except Exception as e:
        xbmc.log('[AbukarimTools MenuSweep] failed: %s' % e, xbmc.LOGWARNING)


def _continue_addons33_rebuild():
    """If an Addons33 rebuild is mid-flight (phase 2: DB deleted, Kodi has
    rebuilt a fresh one), finish it when the menu is opened even if the boot
    service never ran. No-op otherwise.

    3.1.7: no longer runs inline. Phase 2 waits ~25 s, enables add-ons and
    reboots; doing that inside this directory listing blocked the menu (the
    box looked frozen on "Programs"). It now runs as its own RunPlugin
    invocation (mode=addons33_continue), like the menu sweep."""
    try:
        from resources.lib import addons33_rebuild
        if addons33_rebuild._read_step() == '2':
            xbmc.executebuiltin(
                'RunPlugin(plugin://%s/?mode=addons33_continue)' % ADDON_ID)
    except Exception:
        pass


def _mlog(msg):
    """Menu-open trace (DEBUG level; was WARNING in the 3.1.0.13/14 diagnostics)."""
    try:
        xbmc.log('[AbukarimTools Menu] %s' % msg, xbmc.LOGDEBUG)
    except Exception:
        pass


def main_menu():
    _mlog('open: start (argv=%r)' % (sys.argv,))
    from resources.lib.i18n import T
    _mlog('i18n imported')
    _continue_addons33_rebuild()
    _mlog('addons33 continue checked')
    _ensure_fallback_font()
    _mlog('fallback font checked')
    for cat_key, label_id, icon_key, _items in CATEGORIES:
        label = T(label_id)
        _mlog('item %s: label ok' % cat_key)
        _add_folder(label, cat_key, icon_key)
        _mlog('item %s: added' % cat_key)
    xbmcplugin.setContent(HANDLE, 'files')
    _mlog('setContent done - calling endOfDirectory')
    xbmcplugin.endOfDirectory(HANDLE)
    _mlog('endOfDirectory returned')
    # The self-heal sweep is queued only AFTER the listing is handed back, so
    # nothing it does can overlap with building the menu.
    _ensure_patches()
    _mlog('sweep queued - done')


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

    # --- Category folder ---
    if cat is not None and mode is None:
        category_menu(cat)
        return

    # --- Top-level menu ---
    if mode is None:
        main_menu()
        return

    if mode == 'menu_sweep':
        _menu_sweep()
        return

    if mode == 'addons33_continue':
        try:
            from resources.lib import addons33_rebuild
            addons33_rebuild.continue_if_pending(xbmc.Monitor())
        except Exception as e:
            xbmc.log('[AbukarimTools Addons33] continue failed: %s' % e,
                     xbmc.LOGWARNING)
        return

    if mode == 'first_run':
        # Non-folder action (3.1.0.20): no plugin listing is opened, and the
        # sequence runs as its own RunPlugin invocation (mode=first_run_exec), detached from this
        # plugin call and from the Programs container (whose refreshes during
        # add-on rescans were tearing setup dialogs down).
        from resources.lib.i18n import T
        if xbmcgui.Dialog().yesno(
                'ABUKARIM TOOLS',
                T(30050),
                yeslabel=T(30051), nolabel=T(30052)):
            # RunPlugin (not RunScript-by-path, which has no add-on context:
            # 3.1.0.20 crashed with "No valid addon id could be obtained").
            # handle=-1 invocation, detached from any directory listing.
            xbmc.executebuiltin(
                'RunPlugin(plugin://%s/?mode=first_run_exec)' % ADDON_ID)
        return

    if mode == 'first_run_exec':
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

    elif mode == 'addon_portal':
        _end_directory()
        from resources.lib import addon_portal
        addon_portal.run()

    elif mode == 'skin_switch':
        # Non-folder action: don't open/close a plugin listing (that leaves an
        # empty container with a back arrow). Just run; the switcher closes
        # to the new skin's Home itself via _close_to_home().
        from resources.lib import skin_switcher
        skin_switcher.run()

    elif mode == 'backup':
        _end_directory()
        from resources.lib import backup_manager
        backup_manager.BackupManager().run()

    elif mode == 'abukarimwizard':
        # Non-folder action: only reached when the wizard link could not be
        # used (wizard missing) or from an old favourite/shortcut.
        from resources.lib import wizard_runner
        wizard_runner.open_wizard()

    elif mode == 'total_clean':
        from resources.lib import wizard_runner
        wizard_runner.run_total_clean()

    elif mode == 'old_thumbs':
        from resources.lib import wizard_runner
        wizard_runner.run_old_thumbs()

    elif mode == 'openwizard':
        # Legacy URL (<= 3.1.2 favourites / skin shortcuts), which were
        # opened as a folder: close that listing, then hand off.
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        from resources.lib import wizard_runner
        wizard_runner.open_wizard()

    elif mode == 'patcher':
        _end_directory()
        from resources.lib import patcher
        patcher.run()

    elif mode == 'rebuild_addons33':
        _end_directory()
        from resources.lib import addons33_rebuild
        addons33_rebuild.run()

    elif mode == 'speedtest':
        _end_directory()
        # Ookla speedtest-cli vendored at resources/lib/modules/speedtest.py.
        # Run it as a standalone script (RunScript adds its own directory to
        # sys.path so the sibling backtothefuture import resolves) — it draws
        # its own DialogProgress and shows the result image on completion.
        script = ADDON_PATH + 'resources/lib/modules/speedtest.py'
        xbmc.executebuiltin('RunScript(%s)' % script)

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

    elif mode == 'icons_toggle':
        _end_directory()
        from resources.lib import icons_toggle
        icons_toggle.run()

    elif mode == 'origin_fix':
        _end_directory()
        from resources.lib import origin_fix
        origin_fix.run()


router()
