# -*- coding: utf-8 -*-
"""settings_engine.py - ABUKARIM TOOLS (4.8.26, 4.8.27)

A settings page like the skin's own settings, for any add-on: categories in
a column on one side, the entries of the chosen one on the other, a switch
or the current value on each entry, and a description of the focused entry
at the bottom (abk_settings.xml; mirrored for Arabic; Arctic Fuse 3 shows
its own copy in the theme colours).

Used by AB Tools (settings_window.py) and by AB Wizard. SELF-CONTAINED on
purpose - only xbmc / xbmcgui / xbmcaddon / xbmcvfs - because the wizard
loads it by file path: both add-ons have a package called "resources", so
a normal import from the wizard would find the wizard's own.

    from <path to this file> import open_page
    open_page(model)

The model (any object):
    title            "ABUKARIM TOOLS" - window title
    version          shown at the top
    key              short id: remembers the last category, one page open
    categories()     [{'key', 'label', 'icon', 'desc', 'run'?}]
                     with 'run' the category is an action (Support, ...)
    entries(key)     [{'id', 'label', 'icon', 'desc',
                       'switch'?: callable -> True/False/None,
                       'value'?:  str or callable -> str,
                       'slow'?:   True = read the callables in the
                                  background (folder sizes, ...),
                       'run':     callable(page) or a Kodi builtin string}]
                     Called again while the page refreshes, so it must be
                     cheap; when the ids change the list is rebuilt
                     (an entry that only shows when a switch is on).

Entries run as their own RunPlugin / RunScript / dialog. Nothing tells the
page when they finish, so for a while after a click it re-reads the states
(every second; slow ones every 5 s) and the entry list itself.
"""
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

XML = 'abk_settings.xml'
TOOLS_ID = 'plugin.program.abukarimtools'
IDS = {'ltr': (9000, 9001), 'rtl': (9100, 9101)}
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
REFRESH_AFTER_CLICK = 180
SLOW_EVERY = 5.0
WAIT = '…'
PYTHON_WINDOWS = 13000          # script windows get ids from here (other pages)
AWAY_CLOSE = 1.5                # s on a non-page window before the page closes
BEAT_STALE = 6.0                # s without a heartbeat = the page is gone


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AB Settings Page] %s' % msg, level)


def tools_path():
    """AB Tools folder: the window file lives there (any add-on's page)."""
    p = xbmcvfs.translatePath(xbmcaddon.Addon(TOOLS_ID).getAddonInfo('path'))
    return p if p.endswith(('/', '\\')) else p + os.sep


def direction():
    try:
        lang = (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower()
    except Exception:
        lang = ''
    return 'rtl' if lang in ('ar', 'he', 'fa', 'ur') else 'ltr'


def _call(fn, default=None):
    if not callable(fn):
        return fn if fn is not None else default
    try:
        return fn()
    except Exception as e:
        _log('state: %s' % e, xbmc.LOGDEBUG)
        return default


def _switch_text(fn):
    st = _call(fn)
    return '' if st is None else ('on' if st else 'off')


class Page(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        # Kodi's WindowXML takes its file / path in __new__; the base
        # __init__ is not called with our keyword (usual add-on pattern).
        self.model = kwargs.get('model')
        self.start_cat = kwargs.get('start_cat')
        self.dir = direction()
        self.cat_id, self.item_id = IDS[self.dir]
        self.cats = []
        self.cat_pos = -1
        self.rows = []              # [(entry, ListItem)] of the shown category
        self.lock = threading.Lock()
        self.closing = False
        self.refresh_until = 0.0
        self.slow_due = 0.0
        self.worker = None
        self.wid = 0
        key = getattr(self.model, 'key', 'page')
        self.home_cat = 'abk.page.%s.cat' % key
        self.beat = 'abk.page.%s.open' % key

    # ── building ──────────────────────────────────────────────────────────
    def _cat_items(self):
        out = []
        for c in self.cats:
            li = xbmcgui.ListItem(c.get('label', ''))
            icon = c.get('icon', '')
            li.setArt({'icon': icon, 'thumb': icon})
            li.setProperty('desc', c.get('desc', '') or '')
            out.append(li)
        return out

    def _entry_item(self, e):
        li = xbmcgui.ListItem(e.get('label', ''))
        icon = e.get('icon', '')
        li.setArt({'icon': icon, 'thumb': icon})
        li.setProperty('desc', e.get('desc', '') or '')
        if e.get('slow'):
            li.setProperty('switch', '')
            li.setLabel2(WAIT if (e.get('value') is not None or e.get('switch') is not None) else '')
        else:
            self._apply_state(e, li)
        return li

    @staticmethod
    def _apply_state(e, li):
        sw = _switch_text(e.get('switch')) if e.get('switch') is not None else ''
        value = '' if sw else (_call(e.get('value'), '') or '')
        if li.getProperty('switch') != sw:
            li.setProperty('switch', sw)
        if li.getLabel2() != value:
            li.setLabel2(value)

    def _fill(self, entries, keep_pos=False):
        lst = self.getControl(self.item_id)
        pos = lst.getSelectedPosition() if keep_pos else 0
        rows = [(e, self._entry_item(e)) for e in entries]
        with self.lock:
            self.rows = rows
        lst.reset()
        lst.addItems([li for _e, li in rows])
        if keep_pos and rows:
            lst.selectItem(max(0, min(pos, len(rows) - 1)))
        if any(e.get('slow') for e, _li in rows):
            self.slow_due = 0.0                 # read the slow ones now

    def _entries(self, key):
        try:
            return list(self.model.entries(key) or [])
        except Exception as e:
            _log('entries of %s: %s' % (key, e), xbmc.LOGWARNING)
            return []

    def _show_category(self, pos):
        if pos < 0 or pos >= len(self.cats):
            return
        cat = self.cats[pos]
        self.cat_pos = pos
        self.setProperty('cat.title', cat.get('label', ''))
        if cat.get('run'):
            # an action "category" (Support, ...): nothing to list
            self._fill([])
            return
        self._fill(self._entries(cat['key']))
        xbmcgui.Window(10000).setProperty(self.home_cat, cat['key'])

    # ── Kodi callbacks ────────────────────────────────────────────────────
    def onInit(self):
        try:
            self.wid = xbmcgui.getCurrentWindowId()
        except Exception:
            self.wid = 0
        self.setProperty('dir', self.dir)
        self.setProperty('title', getattr(self.model, 'title', ''))
        self.setProperty('version', getattr(self.model, 'version', ''))
        try:
            self.cats = list(self.model.categories() or [])
        except Exception as e:
            _log('categories: %s' % e, xbmc.LOGWARNING)
            self.cats = []
        cl = self.getControl(self.cat_id)
        cl.reset()
        cl.addItems(self._cat_items())
        want = self.start_cat or xbmcgui.Window(10000).getProperty(self.home_cat)
        pos = next((i for i, c in enumerate(self.cats) if c.get('key') == want and not c.get('run')), 0)
        cl.selectItem(pos)
        self._show_category(pos)
        self.setFocusId(self.cat_id)
        if self.worker is None:
            self.worker = threading.Thread(target=self._watch, name='abk-settings-page')
            self.worker.daemon = True
            self.worker.start()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        self._follow_category()

    def onFocus(self, control_id):
        if control_id == self.item_id:
            self._follow_category()

    def onClick(self, control_id):
        if control_id == self.cat_id:
            pos = self.getControl(self.cat_id).getSelectedPosition()
            cat = self.cats[pos] if 0 <= pos < len(self.cats) else None
            if cat and cat.get('run'):
                self._run(cat['run'])
                return
            self._follow_category()
            if self.getControl(self.item_id).size():
                self.setFocusId(self.item_id)
            return
        if control_id == self.item_id:
            pos = self.getControl(self.item_id).getSelectedPosition()
            with self.lock:
                row = self.rows[pos] if 0 <= pos < len(self.rows) else None
            if row and row[0].get('run'):
                self._run(row[0]['run'])

    def close(self):
        self.closing = True
        super().close()

    # ── running ───────────────────────────────────────────────────────────
    def _run(self, run):
        # 4.8.27: a listing (ActivateWindow) replaces the page. Opened on top
        # of it, Kodi brings the Programs window the page was opened from back
        # to the top - Back then never reaches the page, which stayed open
        # hidden and blocked the add-on ("already open"; AB Wizard 4.2,
        # Build Menu, 2026-11-12). Close first; reopening the add-on
        # brings the page back.
        if isinstance(run, str) and run.lstrip().lower().startswith('activatewindow('):
            self.close()
            xbmc.executebuiltin(run)
            return
        try:
            if callable(run):
                run(self)
            elif run:
                xbmc.executebuiltin(run)
        except Exception as e:
            _log('run failed: %s' % e, xbmc.LOGWARNING)
        self.refresh_until = time.time() + REFRESH_AFTER_CLICK
        self.slow_due = 0.0

    def _follow_category(self):
        try:
            pos = self.getControl(self.cat_id).getSelectedPosition()
        except Exception:
            return
        if pos != self.cat_pos and 0 <= pos < len(self.cats):
            self._show_category(pos)

    def _refresh(self, slow):
        # entries that come and go (a sub-option of a switch)
        cat = self.cats[self.cat_pos] if 0 <= self.cat_pos < len(self.cats) else None
        if cat and not cat.get('run'):
            fresh = self._entries(cat['key'])
            with self.lock:
                old_ids = [e.get('id') for e, _li in self.rows]
            if [e.get('id') for e in fresh] != old_ids:
                self._fill(fresh, keep_pos=True)
                return
        with self.lock:
            rows = list(self.rows)
        for e, li in rows:
            if self.closing:
                return
            if e.get('slow') and not slow:
                continue
            self._apply_state(e, li)

    def _away(self):
        """True while Kodi shows a window that is not this page, not a dialog
        over it and not another settings page."""
        try:
            cur = xbmcgui.getCurrentWindowId()
        except Exception:
            return False
        return bool(self.wid) and cur != self.wid and cur < PYTHON_WINDOWS

    def _watch(self):
        monitor = xbmc.Monitor()
        home = xbmcgui.Window(10000)
        last = 0.0
        away = 0.0
        while not self.closing and not monitor.abortRequested():
            if monitor.waitForAbort(0.3) or self.closing:
                break
            home.setProperty(self.beat, '%.1f' % time.time())
            # 4.8.27: navigated elsewhere (an entry or a shortcut opened
            # another window) -> close instead of waiting hidden forever
            if self._away():
                away += 0.3
                if away >= AWAY_CLOSE:
                    _log('another window took over - closing the page')
                    self.close()
                    break
                continue
            away = 0.0
            try:
                if self.getFocusId() == self.cat_id:
                    self._follow_category()
                now = time.time()
                slow = now >= self.slow_due
                if slow:
                    with self.lock:
                        has_slow = any(e.get('slow') for e, _li in self.rows)
                    if has_slow:
                        self.slow_due = now + (SLOW_EVERY if now < self.refresh_until else 3600)
                        self._refresh(True)
                        continue
                    self.slow_due = now + SLOW_EVERY
                if now < self.refresh_until and now - last >= 1.0:
                    last = now
                    self._refresh(False)
            except Exception:
                pass


def view_file(addon_id):
    return os.path.join(xbmcvfs.translatePath('special://profile/addon_data/%s/' % addon_id), 'menu_view.txt')


def page_enabled(addon_id):
    """False when the user picked the classic list for this add-on."""
    try:
        with open(view_file(addon_id), 'r') as f:
            return f.read().strip() != 'list'
    except Exception:
        return True


def set_page_enabled(addon_id, on):
    try:
        path = view_file(addon_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write('window' if on else 'list')
    except Exception as e:
        _log('cannot save the menu view: %s' % e, xbmc.LOGWARNING)


def open_page(model, start_cat=None):
    # 4.8.27: the guard is a heartbeat the page refreshes while it is open; a
    # page that stopped (crash, hidden window) no longer blocks the add-on
    guard = 'abk.page.%s.open' % getattr(model, 'key', 'page')
    home = xbmcgui.Window(10000)
    try:
        beat = float(home.getProperty(guard) or 0)
    except ValueError:
        beat = 0.0
    if beat and time.time() - beat < BEAT_STALE:
        _log('already open')
        return
    home.setProperty(guard, '%.1f' % time.time())
    try:
        win = Page(XML, tools_path(), 'Default', '1080i', model=model, start_cat=start_cat)
        win.doModal()
        win.closing = True
        if win.worker is not None:
            win.worker.join(2)
        del win
    finally:
        home.clearProperty(guard)
