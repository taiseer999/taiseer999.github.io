# -*- coding: utf-8 -*-
"""
setup_overlay.py - "Setup in progress" backdrop for the Installation Wizard.

3.4.22: while the wizard runs, a blurred full-screen backdrop sits BEHIND
every setup dialog and warns, in English and Arabic at the same time, not to
restart, unplug or exit until setup is complete. The current step is shown
under the warning; at the end it switches to "Setup complete - restarting".

How it stays out of the way:
  * shown with show() (modeless), never doModal(): the setup code keeps
    running and every setup dialog opens on top of it (window zorder 0);
  * no focusable control and onAction ignores every key, so Back / Menu
    cannot close it or reach the home screen behind it;
  * the whole wizard waits on System.HasModalDialog. start() checks that the
    backdrop does NOT count as a modal dialog on this Kodi; if it does, the
    backdrop is removed for the rest of the run (setup works as before).

Skin reloads (Skin Installer, language switch, Widgets Layout rebuild) tear
every add-on window down. A keeper thread sees the backdrop is gone and shows
it again; if that keeps failing it gives up quietly - the backdrop is a
courtesy, never a reason for setup to stop.
"""

import threading
import time

import xbmc
import xbmcgui

from resources.lib import paths as _paths
from resources.lib.strings_map import STRINGS

XML = 'abk_setup_overlay.xml'
HOME = xbmcgui.Window(10000)
PROP_RUNNING = 'abk.setup.running'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SetupOverlay] %s' % msg, level)


def _pair(sid):
    en, ar = STRINGS.get(int(sid)) or ('', '')
    return en, (ar or en)


class _Window(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.props = kwargs.get('props') or {}

    def onInit(self):
        for k, v in self.props.items():
            try:
                self.setProperty(k, v)
            except Exception:
                pass

    def onAction(self, action):
        return                  # every key ignored: setup decides when it closes

    def onClick(self, control_id):
        return


class _Overlay(object):
    def __init__(self):
        self.lock = threading.RLock()
        self.win = None
        self.props = {}
        self.active = False
        self.disabled = False
        self.thread = None
        self.reshows = []
        self.by_name = False
        self.win_id = 0

    # -- window handling --------------------------------------------------
    def _visible(self):
        """None = cannot tell on this Kodi (the keeper then leaves it alone)."""
        try:
            if self.by_name:
                return xbmc.getCondVisibility('Window.IsVisible(%s)' % XML)
            if self.win_id:
                return xbmc.getCondVisibility('Window.IsVisible(%d)' % self.win_id)
        except Exception:
            pass
        return None

    def _learn_detection(self):
        """Right after the first show: which visibility test works here."""
        try:
            self.by_name = bool(xbmc.getCondVisibility(
                'Window.IsVisible(%s)' % XML))
        except Exception:
            self.by_name = False
        if not self.by_name:
            try:
                did = xbmcgui.getCurrentWindowDialogId()
                if did >= 13000 and xbmc.getCondVisibility(
                        'Window.IsVisible(%d)' % did):
                    self.win_id = did
            except Exception:
                pass
        _log('visibility check: %s' % (
            'by xml name' if self.by_name else
            ('by id %d' % self.win_id) if self.win_id else
            'unavailable - backdrop not re-shown after a skin reload'))

    def _show(self):
        with self.lock:
            self._close_win()
            try:
                self.win = _Window(XML, _paths.ADDON_PATH, 'Default', '1080i',
                                   props=dict(self.props))
                self.win.show()
            except Exception as e:
                _log('show failed: %s' % e, xbmc.LOGWARNING)
                self.win = None
                return False
            return True

    def _close_win(self):
        w, self.win = self.win, None
        if w is not None:
            try:
                w.close()
            except Exception:
                pass
            try:
                del w
            except Exception:
                pass

    def _set(self, key, value):
        with self.lock:
            self.props[key] = value
            if self.win is not None:
                try:
                    self.win.setProperty(key, value)
                except Exception:
                    pass

    # -- keeper -----------------------------------------------------------
    def _keeper(self):
        mon = xbmc.Monitor()
        missing = 0
        while self.active and not mon.abortRequested():
            if mon.waitForAbort(1):
                break
            if not self.active or self.disabled:
                break
            vis = self._visible()
            if vis is None:
                continue
            if vis:
                missing = 0
                continue
            missing += 1
            if missing < 2:             # a reload passes through "gone" briefly
                continue
            if xbmc.getCondVisibility('Window.IsActive(busydialog)') or \
                    xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'):
                continue                # mid skin reload: try again next second
            now = time.time()
            self.reshows = [t for t in self.reshows if now - t < 60] + [now]
            if len(self.reshows) > 12:
                _log('backdrop keeps disappearing - giving up for this run',
                     xbmc.LOGWARNING)
                self.disabled = True
                with self.lock:
                    self._close_win()
                break
            _log('backdrop gone (skin reload?) - showing it again')
            if self._show() and not self.by_name:
                xbmc.sleep(500)
                self.win_id = 0
                self._learn_detection()
            missing = 0
        with self.lock:
            if not self.active:
                self._close_win()

    # -- public -----------------------------------------------------------
    def start(self):
        if self.active or self.disabled:
            return
        try:
            HOME.setProperty(PROP_RUNNING, "1")
        except Exception:
            pass
        t_en, t_ar = _pair(30770)
        b_en, b_ar = _pair(30771)
        self.props.update({'title_en': t_en, 'title_ar': t_ar,
                           'body_en': b_en, 'body_ar': b_ar,
                           'step': '', 'done': ''})
        modal_before = xbmc.getCondVisibility('System.HasModalDialog')
        if not self._show():
            self.disabled = True
            return
        xbmc.sleep(600)
        if not modal_before and xbmc.getCondVisibility('System.HasModalDialog'):
            # This Kodi counts the backdrop as modal - the wizard would wait on
            # it forever. Drop it; setup runs exactly as before.
            _log('backdrop counts as a modal dialog on this Kodi - disabled',
                 xbmc.LOGWARNING)
            self.disabled = True
            with self.lock:
                self._close_win()
            return
        self._learn_detection()
        self.active = True
        self.thread = threading.Thread(target=self._keeper,
                                       name='abk-setup-overlay')
        self.thread.daemon = True
        self.thread.start()
        _log('backdrop shown')

    def step(self, sid):
        """Show step `sid` (a strings_map id) as 'English  •  Arabic'."""
        en, ar = _pair(sid)
        self._set('step', '%s  •  %s' % (en, ar) if en != ar else en)

    def finish(self, sid):
        """Final state: no spinner, the given message (EN / AR) as title."""
        en, ar = _pair(sid)
        b_en, b_ar = _pair(30772)
        self._set('done', '1')
        self._set('step', '')
        self._set('title_en', en)
        self._set('title_ar', ar)
        self._set('body_en', b_en)
        self._set('body_ar', b_ar)

    def stop(self):
        self.active = False
        with self.lock:
            self._close_win()
        try:
            HOME.clearProperty(PROP_RUNNING)
        except Exception:
            pass
        _log('backdrop removed')


_OVERLAY = _Overlay()


def _guard(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        _log('%s failed (ignored): %s' % (getattr(fn, '__name__', fn), e),
             xbmc.LOGWARNING)


def start():
    _guard(_OVERLAY.start)


def step(sid):
    _guard(_OVERLAY.step, sid)


def finish(sid):
    _guard(_OVERLAY.finish, sid)


def stop():
    _guard(_OVERLAY.stop)


def shown():
    return _OVERLAY.active and not _OVERLAY.disabled
