# -*- coding: utf-8 -*-
"""menu_model.py - ABUKARIM TOOLS (4.8.23)

What the AB Tools menu holds, shared by the two ways of showing it:

  * the settings window (settings_window.py, abk_settings.xml): categories
    on one side, the entries of the chosen one on the other, like a skin's
    own settings page - what a plain launch of the add-on opens;
  * the classic plugin listing (default.py main_menu / category_menu),
    kept for ?view=list, shortcuts and widgets.

Moved out of default.py so both read the same list, the same on/off state
and the same value text.
"""
import xbmc

# Grouped menu: each category is (cat_key, category_label_id, icon_key, [items])
# where each item is (mode, label_id).
CATEGORIES = [
    ('setup',  30014, 'cat_setup', [
        ('first_run',      30001),
        ('phone_setup',    30730),
        ('backup',         30002),
        ('skin_install',   30003),
        ('addon_portal',   30021),
        ('af3_shortcuts',  30630),
        ('trakt_hubs',     30660),
        ('streaming_rows', 30860),
        ('binary_install', 30004),
        ('bootstrap',      30590),
        ('hw_tuning',      30591),
        ('webserver',      30592),
    ]),
    ('patch',  30015, 'cat_patch', [
        ('patcher',        30005),
        ('origin_fix',     30007),
        ('remote_refresh', 30594),
        ('players_update', 30023),
    ]),
    ('maint',  30016, 'cat_maint', [
        ('abukarimwizard', 30008),
        ('total_clean',    30012),
        ('old_thumbs',     30013),
        ('build_cleanup',  30780),
        ('rebuild_addons33', 30018),
        ('settings_v4',    30900),
        ('speedtest',      30019),
        ('cpu_benchmark',  30620),
        ('log_share',      30593),
        ('menu_reconcile', 30595),
    ]),
    ('toggle', 30017, 'cat_toggle', [
        ('skin_switch',    30009),
        ('dplex_toggle',   30010),
        ('korean_toggle',  30011),
        ('icons_toggle',   30020),
        ('ab_glass',       32216),
        ('lucent_theme',   30800),
        ('af3_trailers',   30430),
        ('af3_waves',      30603),
        ('af3_lucent',     30850),
        ('af3_lucentplayer', 32080),
        ('lucent_from_af3', 32089),
        ('af3_plotright',  30890),
        ('af3_plotsize',   32113),
        ('af3_discmenu',   32102),
        ('af3_classicflags', 32127),
        ('seek_preview',   30024),
        ('font_scale',     30740),
    ]),
    ('profiles', 30598, 'cat_profiles', [
        ('profile_export',  30596),
        ('profile_restore', 30597),
    ]),
]

# Icon of every entry, relative to the add-on folder.
ICON_FILES = {
    'skin_install':   'resources/icons/skin_installer.png',
    'skin_switch':    'resources/icons/skin_switcher.png',
    'backup':         'resources/icons/backup.png',
    'abukarimwizard': 'resources/icons/abukarimwizard.png',
    'patcher':        'resources/icons/patcher.png',
    'binary_install': 'resources/icons/binary_install.png',
    'first_run':      'resources/icons/first_run.png',
    'dplex_toggle':   'resources/icons/dplex_toggle.png',
    'korean_toggle':  'resources/icons/korean_toggle.png',
    'icons_toggle':   'resources/icons/icons_toggle.png',
    'ab_glass':       'resources/icons/lucent_theme.png',
    'lucent_theme':   'resources/icons/lucent_theme.png',
    'af3_trailers':   'resources/icons/af3_trailers.png',
    'af3_waves':      'resources/icons/af3_waves.png',
    'af3_lucent':     'resources/icons/af3_lucent.png',
    'af3_lucentplayer': 'resources/icons/af3_lucentplayer.png',
    'lucent_from_af3': 'resources/icons/lucent_from_af3.png',
    'af3_plotright':  'resources/icons/af3_plotright.png',
    'af3_plotsize':   'resources/icons/af3_plotsize.png',
    'af3_discmenu':   'resources/icons/af3_discmenu.png',
    'af3_classicflags': 'resources/icons/af3_classicflags.png',
    'seek_preview':   'resources/icons/seek_preview.png',
    'font_scale':     'resources/icons/font_scale.png',
    'origin_fix':     'resources/icons/sources.png',
    'rebuild_addons33': 'resources/icons/rebuild_addons33.png',
    'settings_v4':    'resources/icons/clear_cache.png',
    'total_clean':    'resources/icons/total_clean.png',
    'old_thumbs':     'resources/icons/old_thumbs.png',
    'build_cleanup':  'resources/icons/build_cleanup.png',
    'speedtest':      'resources/icons/speedtest.png',
    'cpu_benchmark':  'resources/icons/cpu_benchmark.png',
    'addon_portal':   'resources/icons/addon_portal.png',
    'af3_shortcuts':  'resources/icons/af3_shortcuts.png',
    'trakt_hubs':     'resources/icons/trakt_hubs.png',
    'streaming_rows': 'resources/icons/streaming_rows.png',
    'phone_setup':    'resources/icons/phone_setup.png',
    'bootstrap':      'resources/icons/bootstrap.png',
    'hw_tuning':      'resources/icons/hw_tuning.png',
    'webserver':      'resources/icons/webserver.png',
    'log_share':      'resources/icons/log_share.png',
    'remote_refresh': 'resources/icons/remote_refresh.png',
    'players_update': 'resources/icons/players_update.png',
    'menu_reconcile': 'resources/icons/menu_reconcile.png',
    'profile_export': 'resources/icons/profile_export.png',
    'profile_restore': 'resources/icons/profile_restore.png',
    'cat_profiles':   'resources/icons/cat_profiles.png',
    'cat_setup':      'resources/icons/install_setup.png',
    'cat_patch':      'resources/icons/cat_patch.png',
    'cat_maint':      'resources/icons/maintenance.png',
    'cat_toggle':     'resources/icons/cat_toggle.png',
    'support':        'resources/icons/support.png',
}

# Settings-window description of each entry / category (strings 32140-32199).
CATEGORY_DESC = {
    'setup': 32140, 'patch': 32141, 'maint': 32142, 'toggle': 32143,
    'profiles': 32144, 'support': 32145,
}
DESC = {
    'first_run': 32146, 'phone_setup': 32147, 'backup': 32148,
    'skin_install': 32149, 'addon_portal': 32150, 'af3_shortcuts': 32151,
    'trakt_hubs': 32152, 'streaming_rows': 32153, 'binary_install': 32154,
    'bootstrap': 32155, 'hw_tuning': 32156, 'webserver': 32157,
    'patcher': 32158, 'origin_fix': 32159, 'remote_refresh': 32160,
    'players_update': 32161, 'abukarimwizard': 32162, 'total_clean': 32163,
    'old_thumbs': 32164, 'build_cleanup': 32165, 'rebuild_addons33': 32166,
    'settings_v4': 32167, 'speedtest': 32168, 'cpu_benchmark': 32169,
    'log_share': 32170, 'menu_reconcile': 32171, 'skin_switch': 32172,
    'dplex_toggle': 32173, 'korean_toggle': 32174, 'icons_toggle': 32175,
    'lucent_theme': 32176, 'af3_trailers': 32177, 'af3_waves': 32178,
    'af3_lucent': 32179, 'af3_lucentplayer': 32180, 'lucent_from_af3': 32181,
    'af3_plotright': 32182, 'af3_plotsize': 32183, 'af3_discmenu': 32184,
    'af3_classicflags': 32185, 'seek_preview': 32186, 'font_scale': 32187,
    'profile_export': 32188, 'profile_restore': 32189,
    'ab_glass': 32217,
}


def icon_rel(key):
    """Icon of an entry relative to the add-on folder; the glass copy while
    AB Tools' glass look is on (4.8.57)."""
    rel = ICON_FILES.get(key, '')
    try:
        from resources.lib import glass_look
        return glass_look.icon(rel)
    except Exception:
        return rel


def visible(mode):
    """False for an entry this box should not list."""
    if mode == 'settings_v4':
        # 4.6.31: only on a box whose Kodi rejects newer addon_data
        # settings.xml files (see settings_downgrade.py)
        try:
            from resources.lib import settings_downgrade
            return bool(settings_downgrade.applicable())
        except Exception:
            return False
    return True


def switch_state(mode):
    """True/False for entries that are an on/off switch, None otherwise."""
    try:
        if mode == 'ab_glass':
            from resources.lib import glass_look
            return glass_look.is_on()
        if mode == 'af3_waves':
            from resources.lib import af3_waves_toggle
            return bool(af3_waves_toggle.waves_on())
        if mode == 'af3_plotright':
            from resources.lib import af3_plotright_toggle
            return af3_plotright_toggle.plot_right_on()
        if mode == 'af3_discmenu':
            from resources.lib import af3_discmenu_toggle
            return af3_discmenu_toggle.disc_menu_on()
        if mode == 'af3_classicflags':
            from resources.lib import af3_classicflags_toggle
            return af3_classicflags_toggle.toggle_on() and af3_classicflags_toggle.res_ready()
        if mode == 'seek_preview':
            from resources.lib.seek_preview import engine as _sp
            return bool(_sp.load_config()['enabled'])
        if mode == 'af3_lucentplayer':
            from resources.lib import af3_lucentplayer_toggle
            return af3_lucentplayer_toggle.player_on()
        if mode == 'af3_trailers':
            from resources.lib.af3_trailers import config as _tcfg
            return bool(_tcfg.load()['enabled'])
        if mode in ('dplex_toggle', 'korean_toggle'):
            from resources.lib import tab_toggle
            st = tab_toggle._current_state('1104' if mode == 'dplex_toggle' else '1103')
            return None if st is None else bool(st)
    except Exception:
        return None
    return None


def mode_label2(mode):
    """Value text for multi-state entries (3.4.6: Font Size shows its mode)."""
    try:
        if mode == 'lucent_theme':
            from resources.lib import lucent_toggle
            return lucent_toggle.summary()
        if mode == 'af3_plotsize':
            from resources.lib import af3_plotsize
            return af3_plotsize.mode_label()
        if mode == 'font_scale':
            from resources.lib import font_scale
            return font_scale.mode_label()
        if mode == 'af3_lucent':
            from resources.lib import af3_lucent_toggle
            return af3_lucent_toggle.mode_label()
    except Exception as e:
        xbmc.log('[AbukarimTools Menu] value of %s: %s' % (mode, e), xbmc.LOGDEBUG)
    return None
