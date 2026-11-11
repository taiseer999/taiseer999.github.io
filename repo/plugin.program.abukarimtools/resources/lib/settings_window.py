# -*- coding: utf-8 -*-
"""settings_window.py - ABUKARIM TOOLS (4.8.23)

The AB Tools menu as a settings page, like the skin's own settings: the
categories in a column on one side, the entries of the chosen one on the
other, a switch or the current value on each entry, and a description of
the focused entry at the bottom. Arabic Kodi gets the mirrored layout
(categories on the right, text aligned right).

Window file: abk_settings.xml. Kodi looks for it in the ACTIVE skin first,
so Arctic Fuse 3 gets its own copy in the skin's theme colours (installed
by the always-on patcher entry "AF3: AB Tools settings window"); every
other skin uses the copy in resources/skins/Default/1080i. Both are made
by tools/gen_settings_window.py from one template.

It is a full window (xbmcgui.WindowXML), not a dialog, so an entry that
opens a listing (ABUKARIM Wizard) goes on top of it and Back comes back
here. Every entry runs exactly as from the classic list - as its own
RunPlugin(...?mode=<mode>) - so nothing in the entries had to change.
Those run in another interpreter and say nothing when they finish, so for
a while after a click the switches and values are re-read every second.

Classic list: ?view=list, or the "Classic list view" entry at the end of
the categories (remembered in addon_data/menu_view.txt; the classic list
has "Settings view" to come back).
"""
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import menu_model
from resources.lib.i18n import T

ADDON_ID = 'plugin.program.abukarimtools'
XML = 'abk_settings.xml'

# list ids per direction (abk_settings.xml): (categories, entries)
IDS = {'ltr': (9000, 9001), 'rtl': (9100, 9101)}

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

REFRESH_AFTER_CLICK = 180       # s of state re-reads after an entry ran
HOME_CAT = 'abukarimtools.settings.cat'

S_CLASSIC = 32190               # "Classic list view"
S_CLASSIC_DESC = 32194
S_SUPPORT = 32192              # "Support ABUKARIM" (short)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Settings] %s' % msg, level)


def _addon():
    return xbmcaddon.Addon(ADDON_ID)


def _addon_path():
    p = xbmcvfs.translatePath(_addon().getAddonInfo('path'))
    return p if p.endswith(('/', '\\')) else p + os.sep


def _view_file():
    return os.path.join(xbmcvfs.translatePath(_addon().getAddonInfo('profile')), 'menu_view.txt')


def enabled():
    """False when the user picked the classic list."""
    try:
        with open(_view_file(), 'r') as f:
            return f.read().strip() != 'list'
    except Exception:
        return True


def set_enabled(on):
    try:
        path = _view_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write('window' if on else 'list')
    except Exception as e:
        _log('cannot save the menu view: %s' % e, xbmc.LOGWARNING)


def _direction():
    try:
        lang = (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower()
    except Exception:
        lang = ''
    return 'rtl' if lang in ('ar', 'he', 'fa', 'ur') else 'ltr'


def _state(mode):
    """(switch 'on'/'off'/'', value text) of one entry."""
    sw = menu_model.switch_state(mode)
    value = '' if sw is not None else (menu_model.mode_label2(mode) or '')
    return ('' if sw is None else ('on' if sw else 'off')), value


class SettingsWindow(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        # Kodi's WindowXML takes its file / path args in __new__; the base
        # __init__ is not called with our extra keyword (usual add-on pattern).
        self.start_cat = kwargs.get('start_cat')
        self.direction = _direction()
        self.cat_id, self.item_id = IDS[self.direction]
        self.path = _addon_path()
        self.cats = [c for c in menu_model.CATEGORIES]
        self.cat_pos = -1
        self.items = []             # (mode, ListItem) of the shown category
        self.lock = threading.Lock()
        self.closing = False
        self.refresh_until = 0.0
        self.worker = None

    # ── building ──────────────────────────────────────────────────────────
    def _icon(self, key):
        rel = menu_model.ICON_FILES.get(key)
        return self.path + rel if rel else ''

    def _cat_items(self):
        out = []
        for key, label_id, icon_key, _items in self.cats:
            li = xbmcgui.ListItem(T(label_id))
            li.setArt({'icon': self._icon(icon_key), 'thumb': self._icon(icon_key)})
            li.setProperty('key', key)
            li.setProperty('kind', 'cat')
            li.setProperty('desc', T(menu_model.CATEGORY_DESC.get(key, 0)) if key in menu_model.CATEGORY_DESC else '')
            out.append(li)
        li = xbmcgui.ListItem(T(S_SUPPORT))
        li.setArt({'icon': self._icon('support'), 'thumb': self._icon('support')})
        li.setProperty('key', 'support')
        li.setProperty('kind', 'support')
        li.setProperty('desc', T(menu_model.CATEGORY_DESC['support']))
        out.append(li)
        li = xbmcgui.ListItem(T(S_CLASSIC))
        li.setArt({'icon': self._icon('cat_toggle'), 'thumb': self._icon('cat_toggle')})
        li.setProperty('key', 'classic')
        li.setProperty('kind', 'classic')
        li.setProperty('desc', T(S_CLASSIC_DESC))
        out.append(li)
        return out

    def _entry(self, mode, label_id):
        li = xbmcgui.ListItem(T(label_id))
        li.setArt({'icon': self._icon(mode), 'thumb': self._icon(mode)})
        li.setProperty('mode', mode)
        li.setProperty('desc', T(menu_model.DESC[mode]) if mode in menu_model.DESC else '')
        sw, value = _state(mode)
        li.setProperty('switch', sw)
        li.setLabel2(value)
        return li

    def _show_category(self, pos):
        if pos < 0 or pos >= len(self.cats):
            return
        key, label_id, _icon, entries = self.cats[pos]
        items = [(m, self._entry(m, lid)) for m, lid in entries if menu_model.visible(m)]
        with self.lock:
            self.items = items
            self.cat_pos = pos
        lst = self.getControl(self.item_id)
        lst.reset()
        lst.addItems([li for _m, li in items])
        self.setProperty('cat.title', T(label_id))
        xbmcgui.Window(10000).setProperty(HOME_CAT, key)

    # ── Kodi callbacks ────────────────────────────────────────────────────
    def onInit(self):
        self.setProperty('dir', self.direction)
        self.setProperty('title', 'ABUKARIM TOOLS')
        try:
            self.setProperty('version', _addon().getAddonInfo('version'))
        except Exception:
            pass
        cats = self.getControl(self.cat_id)
        cats.reset()
        cats.addItems(self._cat_items())
        want = self.start_cat or xbmcgui.Window(10000).getProperty(HOME_CAT)
        pos = next((i for i, c in enumerate(self.cats) if c[0] == want), 0)
        cats.selectItem(pos)
        self._show_category(pos)
        self.setFocusId(self.cat_id)
        if self.worker is None:
            self.worker = threading.Thread(target=self._watch, name='abk-settings')
            self.worker.daemon = True
            self.worker.start()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        self._follow_category()

    def onFocus(self, control_id):
        if control_id == self.item_id:
            self._follow_category()

    def onClick(self, control_id):
        if control_id == self.cat_id:
            li = self.getControl(self.cat_id).getSelectedItem()
            kind = li.getProperty('kind') if li else ''
            if kind == 'support':
                self._run('support')
            elif kind == 'classic':
                set_enabled(False)
                self.close()
                xbmc.executebuiltin('ActivateWindow(Programs,"plugin://%s/?view=list",return)' % ADDON_ID)
            else:
                self._follow_category()
                if self.getControl(self.item_id).size():
                    self.setFocusId(self.item_id)
            return
        if control_id == self.item_id:
            li = self.getControl(self.item_id).getSelectedItem()
            mode = li.getProperty('mode') if li else ''
            if mode:
                self._run(mode)

    def close(self):
        self.closing = True
        super().close()

    # ── running entries ───────────────────────────────────────────────────
    def _run(self, mode):
        _log('run %s' % mode)
        if mode == 'abukarimwizard':
            try:
                from resources.lib import wizard_runner
                if wizard_runner.wizard_installed():
                    url = wizard_runner.wizard_url(wizard_runner.MODE_MAINTENANCE)
                    xbmc.executebuiltin('ActivateWindow(Programs,"%s",return)' % url)
                    return
            except Exception as e:
                _log('wizard link failed: %s' % e, xbmc.LOGWARNING)
        xbmc.executebuiltin('RunPlugin(plugin://%s/?mode=%s)' % (ADDON_ID, mode))
        self.refresh_until = time.time() + REFRESH_AFTER_CLICK

    def _follow_category(self):
        try:
            pos = self.getControl(self.cat_id).getSelectedPosition()
        except Exception:
            return
        if pos != self.cat_pos and 0 <= pos < len(self.cats):
            self._show_category(pos)

    def _refresh_states(self):
        with self.lock:
            items = list(self.items)
        for mode, li in items:
            if self.closing:
                return
            sw, value = _state(mode)
            if li.getProperty('switch') != sw:
                li.setProperty('switch', sw)
            if li.getLabel2() != value:
                li.setLabel2(value)

    def _watch(self):
        """Follow the category under the cursor (mouse / touch) and re-read
        the states for a while after an entry ran."""
        monitor = xbmc.Monitor()
        last = 0.0
        while not self.closing and not monitor.abortRequested():
            if monitor.waitForAbort(0.3):
                break
            if self.closing:
                break
            try:
                if self.getFocusId() == self.cat_id:
                    self._follow_category()
                now = time.time()
                if now < self.refresh_until and now - last >= 1.0:
                    last = now
                    self._refresh_states()
            except Exception:
                pass


def open_window(start_cat=None):
    if xbmcgui.Window(10000).getProperty('abukarimtools.settings.open'):
        _log('already open')
        return
    xbmcgui.Window(10000).setProperty('abukarimtools.settings.open', '1')
    try:
        win = SettingsWindow(XML, _addon_path(), 'Default', '1080i', start_cat=start_cat)
        win.doModal()
        win.closing = True
        if win.worker is not None:
            win.worker.join(2)
        del win
    finally:
        xbmcgui.Window(10000).clearProperty('abukarimtools.settings.open')
