# -*- coding: utf-8 -*-
"""settings_page.py - AB Wizard 4.2

The wizard's menu as a settings page, like the skin's own settings and like
ABUKARIM TOOLS: categories in a column (Builds, Accounts, Cleaning, Auto
Clean, Add-ons, Logs, System, Backup & Restore, Settings, Support, Classic
list view), the entries of the chosen one beside it with their switch or
current value (sizes, frequency, account status...), and a description of
the focused entry at the bottom. Arabic Kodi gets the mirrored layout;
Arctic Fuse 3 shows it in its theme colours.

The page itself is ABUKARIM TOOLS' settings engine (4.8.26+:
resources/lib/settings_engine.py + abk_settings.xml), loaded BY FILE PATH:
both add-ons have a package called "resources", so a normal import would
find the wizard's own. Without it (older AB Tools) the classic list opens.

Every entry runs the same wizard mode as the classic list, as its own
RunPlugin; listings (Build Menu, Restore Backup, Network Information...)
open in Programs on top of the page and Back comes back to it. Accounts:
one entry per service with its status; a click lists that service's
Account Manager actions.

Settings are read with a fresh xbmcaddon.Addon() every time: the page
lives in one interpreter while the entries change them in others.
"""
import importlib.util
import os
from urllib.parse import quote_plus

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'plugin.program.ABUKARIMwizard'
ENGINE = 'special://home/addons/plugin.program.abukarimtools/resources/lib/settings_engine.py'
MODE_PAGE = 500
MODE_PAGE_ON = 501

_engine_mod = None


def engine():
    """AB Tools' settings engine, or None when AB Tools is older than 4.8.26."""
    global _engine_mod
    if _engine_mod is not None:
        return _engine_mod
    path = xbmcvfs.translatePath(ENGINE)
    if not os.path.isfile(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location('abk_settings_engine', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _engine_mod = mod
    except Exception as e:
        xbmc.log('[AB Wizard Page] engine: %s' % e, xbmc.LOGWARNING)
        return None
    return _engine_mod


def enabled():
    eng = engine()
    return bool(eng) and eng.page_enabled(ADDON_ID)


def set_enabled(on):
    eng = engine()
    if eng:
        eng.set_page_enabled(ADDON_ID, on)


def _addon():
    return xbmcaddon.Addon(ADDON_ID)


def S(sid):
    return _addon().getLocalizedString(sid)


def _setting(sid):
    return _addon().getSetting(sid)


def _url(mode, url=''):
    u = 'plugin://%s/?mode=%d' % (ADDON_ID, mode)
    return u + ('&url=%s' % quote_plus(url) if url else '')


def run(mode, url=''):
    return 'RunPlugin(%s)' % _url(mode, url)


def folder(mode, url=''):
    return 'ActivateWindow(Programs,"%s",return)' % _url(mode, url)


def _real(url):
    return url not in ('', None, 'http://', 'https://', 'http://CHANGEME', 'http://CHANGEME/')


class WizardModel(object):
    title = 'AB WIZARD'
    key = 'wizard'

    def __init__(self):
        a = _addon()
        self.version = a.getAddonInfo('version')
        p = xbmcvfs.translatePath(a.getAddonInfo('path'))
        self.icons = os.path.join(p, 'resources', 'media', 'icons')
        self.addon_icon = os.path.join(p, 'resources', 'icon.png')

    def icon(self, name):
        path = os.path.join(self.icons, name + '.png')
        if not os.path.isfile(path):
            return self.addon_icon
        from . import glass_look
        return glass_look.icon(path)

    @staticmethod
    def glass_on():
        """4.2.2: AB Tools' glass look (the page reads Window.Property(glass))."""
        from . import glass_look
        return glass_look.is_on()

    # ── categories ────────────────────────────────────────────────────────
    def categories(self):
        i = self.icon
        return [
            {'key': 'builds', 'label': S(30500), 'icon': i('builds'), 'desc': S(30510)},
            {'key': 'accounts', 'label': S(30501), 'icon': i('accounts'), 'desc': S(30401)},
            {'key': 'clean', 'label': S(30200), 'icon': i('broom'), 'desc': S(30512)},
            {'key': 'autoclean', 'label': S(30214), 'icon': i('clock'), 'desc': S(30513)},
            {'key': 'addons', 'label': S(30201), 'icon': i('addon_portal'), 'desc': S(30514)},
            {'key': 'logs', 'label': S(30202), 'icon': i('log_share'), 'desc': S(30515)},
            {'key': 'system', 'label': S(30502), 'icon': i('wrench'), 'desc': S(30516)},
            {'key': 'backup', 'label': S(30506), 'icon': i('backup'), 'desc': S(30517)},
            {'key': 'settings', 'label': S(30015), 'icon': i('hw_tuning'), 'desc': S(30016), 'run': run(9)},
            {'key': 'support', 'label': S(30505), 'icon': i('support'), 'desc': S(30519), 'run': run(300)},
            {'key': 'classic', 'label': S(30503), 'icon': i('cat_toggle'), 'desc': S(30520), 'run': _classic},
        ]

    def entries(self, key):
        fn = getattr(self, '_e_' + key, None)
        return fn() if fn else []

    @staticmethod
    def e(eid, label, icon, desc, run=None, **kw):
        d = {'id': eid, 'label': label, 'icon': icon, 'desc': desc, 'run': run}
        d.update(kw)
        return d

    # ── Builds ────────────────────────────────────────────────────────────
    def _e_builds(self):
        from . import addonvar as av
        from uservar import changelog_dir, videos_url, notify_url
        i, e = self.icon, self.e
        out = []
        installed = av.CURRENT_BUILD not in ('No Build Installed', 'No Build')

        def _vt(v):
            return tuple(int(''.join(c for c in x if c.isdigit()) or 0) for x in str(v or '0').split('.'))
        if installed and av.UPDATE_VERSION and _vt(av.UPDATE_VERSION) > _vt(av.BUILD_VERSION):
            out.append(e('update', S(30530), i('update_alert'), S(30550), run(32), value='v%s' % av.UPDATE_VERSION))
        out.append(e('installed', S(30531), i('builds'), S(30111),
                     value=('%s v%s' % (av.CURRENT_BUILD, av.BUILD_VERSION)) if installed else S(30532)))
        out.append(e('menu', S(30010), i('builds'), S(30001), folder(1),
                     value=(S(30537) % av.NUM_BUILDS) if av.NUM_BUILDS else ''))
        if installed and _real(av.GUI_URL):
            out.append(e('lite', S(30113), i('patcher'), S(30114), run(33, av.GUI_URL)))
        if installed and _real(av.OPTION2_URL):
            out.append(e('full', S(30118), i('patcher'), S(30551), run(35, av.OPTION2_URL)))
        if installed and _real(changelog_dir):
            out.append(e('changelog', S(30535), i('changelog'), S(30109), run(101)))
        out.append(e('notify', S(30013), i('bell'), S(30014), run(100)))
        if _real(videos_url):
            out.append(e('videos', S(30536), i('video'), S(30552), folder(30, videos_url)))
        out.append(e('kodi', S(30533), i('info'), S(30553), value='%s %s' % (av.code_name, av.kodi_ver)))
        out.append(e('os', S(30534), i('info'), S(30554), value='%s %s' % (av.os_name, av.sys_arch)))
        return out

    # ── Accounts (Account Manager) ────────────────────────────────────────
    def _e_accounts(self):
        from . import authorize as au
        e = self.e
        if au._am() is None:
            return [e('am_missing', S(30402), self.icon('accounts'), S(30403), run(41))]
        out = []
        for key, label, _ids, _acct, _sup in au.SERVICES:
            if not au._am_supports(key):
                continue
            out.append(e('svc_' + key, label, au._am_icon(key), self._svc_desc(key, label),
                         (lambda page, k=key: _account_actions(k)),
                         value=(lambda k=key: _account_state(k))))
        out.append(e('revoke_all', S(30420), self.icon('accounts'), S(30421), 'RunScript(%s, action=allRevoke)' % au.AM_ID))
        out.append(e('am_settings', S(30422), self.icon('advanced'), S(30423), run(40)))
        return out

    @staticmethod
    def _svc_desc(key, label):
        st = _account_state(key, raw=True)
        return S(30406).format(label, st) if st else S(30408).format(label)

    # ── Cleaning ──────────────────────────────────────────────────────────
    def _e_clean(self):
        from . import maint_tools as mt
        i, e = self.icon, self.e
        size = mt.convert_size

        def _sz(fn):
            return lambda: size(fn())
        out = [
            e('total', S(30207), i('broom'), S(30555), run(210), slow=True,
              value=_sz(lambda: mt.get_size(mt.packages) + mt.get_size(mt.THUMBNAILS) + mt.get_cache_size()
                        + (mt.get_size(mt.ARCHIVE_CACHE) if os.path.exists(mt.ARCHIVE_CACHE) else 0))),
            e('cache', S(30208), i('clear_cache'), S(30556), run(211), slow=True, value=_sz(mt.get_cache_size)),
        ]
        if xbmc.getCondVisibility('System.HasAddon(script.module.resolveurl)') or \
                xbmc.getCondVisibility('System.HasAddon(script.module.urlresolver)'):
            out.append(e('resolver', S(30209), i('clear_cache'), S(30557), run(212)))
        out.append(e('packages', S(30023), i('binary_install'), S(30005), run(6), slow=True,
                     value=_sz(lambda: mt.get_size(mt.packages))))
        out.append(e('thumbs', S(30024), i('icons_toggle'), S(30558), run(7), slow=True,
                     value=_sz(lambda: mt.get_size(mt.THUMBNAILS))))
        if os.path.exists(mt.ARCHIVE_CACHE):
            out.append(e('archive', S(30210), i('clear_cache'), S(30559), run(213), slow=True,
                         value=_sz(lambda: mt.get_size(mt.ARCHIVE_CACHE))))
        out += [
            e('old_thumbs', S(30211), i('icons_toggle'), S(30560), run(214)),
            e('crash', S(30212), i('log_share'), S(30561), run(215)),
            e('purge', S(30213), i('database'), S(30562), run(216)),
            e('fresh', S(30012), i('fresh'), S(30563), run(4)),
        ]
        return out

    # ── Auto clean ────────────────────────────────────────────────────────
    def _e_autoclean(self):
        i, e = self.icon, self.e
        out = [e('auto', S(30215), i('broom'), S(30564), run(217, 'autoclean'),
                 switch=lambda: _setting('autoclean') == 'true')]
        if _setting('autoclean') == 'true':
            out += [
                e('freq', S(30216), i('clock'), S(30565), run(218), value=_freq),
                e('auto_cache', S(30217), i('clear_cache'), S(30566), run(217, 'autoclean_cache'),
                  switch=lambda: _setting('autoclean_cache') != 'false'),
                e('auto_thumbs', S(30218), i('icons_toggle'), S(30567), run(217, 'autoclean_thumbs'),
                  switch=lambda: _setting('autoclean_thumbs') != 'false'),
            ]
        out.append(e('auto_pkg', S(30270), i('clock'), S(30568), run(219), value=_pkg_freq))
        return out

    # ── Add-ons ───────────────────────────────────────────────────────────
    def _e_addons(self):
        i, e = self.icon, self.e
        return [
            e('remove', S(30219), i('addon_remove'), S(30569), run(220)),
            e('remove_data', S(30277), i('folder'), S(30570), folder(221)),
            e('enable', S(30291), i('cat_toggle'), S(30571), folder(222)),
            e('repos', S(30220), i('refresh'), S(30572), run(225)),
            e('update', S(30221), i('update'), S(30573), run(226)),
            e('whitelist', S(30064), i('menu_reconcile'), S(30574), run(11)),
        ]

    # ── Logs ──────────────────────────────────────────────────────────────
    def _e_logs(self):
        from . import maint_tools as mt
        i, e = self.icon, self.e

        def _errors():
            n = mt.error_checking(count=True)
            return (S(30222) % n) if n else S(30223)
        return [
            e('debug', S(30304), i('log_share'), S(30575), run(230),
              switch=lambda: bool(mt._get_kodi_setting('debug.showloginfo'))),
            e('view', S(30224), i('log_share'), S(30576), run(26)),
            e('errors', S(30225), i('alert'), S(30577), run(231), slow=True, value=_errors),
            e('last_error', S(30226), i('alert'), S(30578), run(232)),
        ]

    # ── System ────────────────────────────────────────────────────────────
    def _e_system(self):
        from . import maint_tools as mt
        from . import addonvar as av
        i, e = self.icon, self.e

        def _updates():
            upd = mt._get_kodi_setting('general.addonupdates')
            names = [S(30227), S(30228), S(30229)]
            return names[upd] if isinstance(upd, int) and 0 <= upd < 3 else ''
        adv = 31 if '22' in av.kodi_ver else 29 if '21' in av.kodi_ver else 8 if '20' in av.kodi_ver else None
        out = [
            e('network', S(30311), i('webserver'), S(30579), folder(240)),
            e('speed', S(30230), i('speedtest'), S(30580), run(28)),
            e('unknown', S(30305), i('key'), S(30581), run(241),
              switch=lambda: bool(mt._get_kodi_setting('addons.unknownsources'))),
            e('addon_updates', S(30231), i('addons_auto'), S(30582), run(242), value=_updates),
        ]
        if adv:
            out.append(e('advanced', S(30547), i('advanced'), S(30583), run(adv)))
        out += [
            e('sources', S(30235), i('sources'), S(30584), run(250)),
            e('repos', S(30236), i('remote_refresh'), S(30585), run(251)),
            e('special', S(30237), i('advanced'), S(30586), run(252)),
            e('sysinfo', S(30319), i('info'), S(30587), folder(253)),
            e('reload_skin', S(30232), i('refresh'), S(30588), run(243)),
            e('reload_profile', S(30233), i('profile'), S(30589), run(244)),
            e('force_close', S(30234), i('power'), S(30590), run(245)),
        ]
        return out

    # ── Backup & restore ──────────────────────────────────────────────────
    def _e_backup(self):
        i, e = self.icon, self.e
        return [
            e('backup', S(30538), i('backup_up'), S(30591), run(13)),
            e('restore', S(30539), i('backup_down'), S(30592), folder(14)),
            e('folder', S(30540), i('folder'), S(30593), run(16)),
            e('folder_reset', S(30541), i('folder_reset'), S(30594), run(17)),
            e('cleanup', S(30238), i('clear_cache'), S(30239), run(254)),
            e('gui_backup', S(30542), i('profile_export'), S(30595), run(22)),
            e('gui_restore', S(30543), i('profile_restore'), S(30596), run(23)),
            e('skin_restore', S(30544), i('profile_restore'), S(30597), run(24)),
            e('gui_default', S(30545), i('fresh'), S(30598), run(20)),
            e('skin_default', S(30546), i('fresh'), S(30599), run(21)),
        ]


# ── values / actions ──────────────────────────────────────────────────────
def _freq():
    names = [S(30260), S(30261), S(30262), S(30263), S(30264)]
    try:
        return names[int(_setting('autocleanfreq') or 3)]
    except (ValueError, IndexError):
        return names[3]


def _pkg_freq():
    names = [S(30267), S(30260), S(30268), S(30269)]
    try:
        return names[int(_setting('autoclearpackages') or 1)]
    except (ValueError, IndexError):
        return names[1]


def _account_state(key, raw=False):
    from . import authorize as au
    am = au._am()
    st = au._status(am, key) if am is not None else ''
    if raw:
        return st
    return st or S(30407)


def _account_actions(key):
    """The Account Manager actions of one service (same as its classic
    sub-menu), in a list."""
    from . import authorize as au
    if au._am() is None:
        xbmc.executebuiltin(run(41))
        return
    _k, label, _ids, has_acct, supported = au._BY_KEY[key]
    rows = []
    if _account_state(key, raw=True):
        if has_acct:
            rows.append((S(30410), au._run('%sAcct' % key)))
        rows.append((S(30412), au._run('%sReSync' % key)))
        if key == 'trakt':
            rows.append((S(30418), au._run('traktEditSyncList')))
        if au._has(au.AM_VIEWER_ID):
            rows.append((S(30414), au._run('%sViewer' % key)))
        rows.append((S(30416), au._run('%sRevoke' % key)))
    else:
        rows.append((S(30424).format(label), au._run('%sAuth' % key)))
    rows.append((S(30426), au._run('ShowSupported_%s' % supported)))
    pick = xbmcgui.Dialog().select(label, [r[0] for r in rows])
    if pick >= 0:
        xbmc.executebuiltin(rows[pick][1])


def _classic(page):
    set_enabled(False)
    page.close()
    xbmc.executebuiltin('ActivateWindow(Programs,"plugin://%s/?view=list",return)' % ADDON_ID)


def wants_page(handle):
    """True when the user opened the wizard itself (Programs / Add-ons), not
    a widget or another container listing its root."""
    if handle < 0 or not enabled():
        return False
    return bool(xbmc.getCondVisibility(
        'Window.IsActive(programs) | Window.IsActive(addonbrowser) | Window.IsActive(addoninformation)'))


def open_page(start_cat=None):
    eng = engine()
    if not eng:
        xbmc.executebuiltin('ActivateWindow(Programs,"plugin://%s/?view=list",return)' % ADDON_ID)
        return
    eng.open_page(WizardModel(), start_cat)
