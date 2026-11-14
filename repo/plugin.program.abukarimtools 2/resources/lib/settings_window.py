# -*- coding: utf-8 -*-
"""settings_window.py - ABUKARIM TOOLS (4.8.23, engine split in 4.8.26)

The AB Tools menu as a settings page (settings_engine.py draws and runs it;
this file only says what is on it): the categories of menu_model.CATEGORIES,
each entry with its switch or value and its description, then Support and
"Classic list view".

Every entry runs exactly as from the classic list - RunPlugin(...?mode=X) -
except ABUKARIM Wizard, which opens its own settings page when the wizard
has one (4.2+), else its maintenance listing on top of this page.

Classic list: ?view=list, or "Classic list view" at the end of the
categories (remembered in addon_data/menu_view.txt; the classic list has
"Settings view" to come back).
"""
import os

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib import menu_model
from resources.lib import settings_engine as engine
from resources.lib.i18n import T

ADDON_ID = 'plugin.program.abukarimtools'

S_SUPPORT = 32192               # "Support ABUKARIM" (short)
S_CLASSIC = 32190               # "Classic list view"
S_CLASSIC_DESC = 32194


def enabled():
    return engine.page_enabled(ADDON_ID)


def set_enabled(on):
    engine.set_page_enabled(ADDON_ID, on)


def _plugin(mode):
    return 'RunPlugin(plugin://%s/?mode=%s)' % (ADDON_ID, mode)


def _wizard_has_page():
    """AB Wizard 4.2+ opens as a settings page of its own (mode 500)."""
    try:
        v = xbmcaddon.Addon('plugin.program.ABUKARIMwizard').getAddonInfo('version')
        nums = tuple(int(''.join(c for c in x if c.isdigit()) or 0) for x in v.split('.'))
        return nums >= (4, 2)
    except Exception:
        return False


def _run_wizard(page):
    try:
        from resources.lib import wizard_runner
        if wizard_runner.wizard_installed() and _wizard_has_page():
            xbmc.executebuiltin('RunPlugin(%s?mode=500&cat=clean)' % wizard_runner.WIZARD_URL)
            return
        if wizard_runner.wizard_installed():
            url = wizard_runner.wizard_url(wizard_runner.MODE_MAINTENANCE)
            page.close()                # 4.8.27: a listing replaces the page
            xbmc.executebuiltin('ActivateWindow(Programs,"%s",return)' % url)
            return
    except Exception as e:
        xbmc.log('[AbukarimTools Settings] wizard link failed: %s' % e, xbmc.LOGWARNING)
    xbmc.executebuiltin(_plugin('abukarimwizard'))


def _classic(page):
    set_enabled(False)
    page.close()
    xbmc.executebuiltin('ActivateWindow(Programs,"plugin://%s/?view=list",return)' % ADDON_ID)


class ToolsModel(object):
    title = 'ABUKARIM TOOLS'
    key = 'tools'

    def __init__(self):
        addon = xbmcaddon.Addon(ADDON_ID)
        self.version = addon.getAddonInfo('version')
        p = xbmcvfs.translatePath(addon.getAddonInfo('path'))
        self.path = p if p.endswith(('/', '\\')) else p + os.sep

    def _icon(self, key):
        rel = menu_model.icon_rel(key)
        return self.path + rel if rel else ''

    @staticmethod
    def glass_on():
        from resources.lib import glass_look
        return glass_look.is_on()

    def categories(self):
        out = [{'key': key, 'label': T(label_id), 'icon': self._icon(icon_key),
                'desc': T(menu_model.CATEGORY_DESC[key]) if key in menu_model.CATEGORY_DESC else ''}
               for key, label_id, icon_key, _items in menu_model.CATEGORIES]
        out.append({'key': 'support', 'label': T(S_SUPPORT), 'icon': self._icon('support'),
                    'desc': T(menu_model.CATEGORY_DESC['support']), 'run': _plugin('support')})
        out.append({'key': 'classic', 'label': T(S_CLASSIC), 'icon': self._icon('cat_toggle'),
                    'desc': T(S_CLASSIC_DESC), 'run': _classic})
        return out

    def entries(self, key):
        for cat_key, _label, _icon, items in menu_model.CATEGORIES:
            if cat_key != key:
                continue
            out = []
            for mode, label_id in items:
                if not menu_model.visible(mode):
                    continue
                e = {'id': mode, 'label': T(label_id), 'icon': self._icon(mode),
                     'desc': T(menu_model.DESC[mode]) if mode in menu_model.DESC else '',
                     'run': _run_wizard if mode == 'abukarimwizard' else
                            _toggle_glass if mode == 'ab_glass' else _plugin(mode)}
                if menu_model.switch_state(mode) is not None:
                    e['switch'] = (lambda m=mode: menu_model.switch_state(m))
                else:
                    e['value'] = (lambda m=mode: menu_model.mode_label2(m) or '')
                out.append(e)
            return out
        return []


def _toggle_glass(page):
    """4.8.57: flip AB Tools' glass look and redraw the page in place."""
    from resources.lib import glass_look
    glass_look.toggle()
    page.restyle()


def open_window(start_cat=None):
    engine.open_page(ToolsModel(), start_cat)
