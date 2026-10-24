# -*- coding: utf-8 -*-
"""
setup_overlay.py - "Setup in progress" backdrop for the Installation Wizard.

3.4.22: while the wizard runs, a blurred full-screen backdrop sits BEHIND
the setup dialogs and warns, in English and Arabic at the same time, not to
restart, unplug or exit until setup is complete. The current step is shown
under the warning; at the end it switches to "Setup complete - restarting".

How it stays out of the way:
  * shown with show() (modeless), never doModal(): the setup code keeps
    running and setup dialogs open on top of it (window zorder 0);
  * no focusable control and onAction ignores every key, so Back / Menu
    cannot close it or reach the home screen behind it;
  * the whole wizard waits on System.HasModalDialog. start() checks that the
    backdrop does NOT count as a modal dialog on this Kodi; if it does, the
    backdrop is removed for the rest of the run (setup works as before).

3.4.23 - SKIN RELOADS (kodi.log 2026-10-24 05:52:03, macOS): the 3.4.22
keeper THREAD re-created the backdrop 0.7 s after the Skin Installer's
ReloadSkin, while Kodi was still stopping/restarting add-on services - the
GUI thread never logged again (frozen). Rules now:
  * every window call (show / close / setProperty) happens on the setup
    thread only - there is no background thread any more;
  * pause() closes the backdrop BEFORE each step that reloads the skin
    (Skin Installer, language switch, Widgets Layout, My Lists, patches);
  * ensure() shows it again only after the screen has been calm (no busy
    dialog, no modal dialog, no skin build) for STABLE_S seconds; if it never
    calms down within ENSURE_MAX_S, the backdrop simply stays off.
The backdrop is a courtesy, never a reason for setup to stop.
"""

import time

import xbmc
import xbmcgui

from resources.lib import paths as _paths
from resources.lib.strings_map import STRINGS

XML = 'abk_setup_overlay.xml'
PROP_RUNNING = 'abk.setup.running'
STABLE_S = 3.0
ENSURE_MAX_S = 20.0


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SetupOverlay] %s' % msg, level)


def _pair(sid):
    en, ar = STRINGS.get(int(sid)) or ('', '')
    return en, (ar or en)


def _home_prop(value):
    try:
        w = xbmcgui.Window(10000)
        if value:
            w.setProperty(PROP_RUNNING, value)
        else:
            w.clearProperty(PROP_RUNNING)
    except Exception:
        pass


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


def _busy():
    """Why the screen is not calm yet ('' = calm)."""
    try:
        if xbmc.getCondVisibility('Window.IsActive(busydialog)') or \
                xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'):
            return 'busy dialog'
        if xbmc.getCondVisibility('System.HasModalDialog'):
            return 'modal dialog'
        if xbmcgui.getCurrentWindowId() == 9999:
            return 'no window (skin loading)'
    except Exception:
        return 'gui query failed'
    try:
        from resources.lib import skin_rebuild
        reason = skin_rebuild.busy()
        if reason:
            return 'skin build: %s' % reason
    except Exception:
        pass
    return ''


class _Overlay(object):
    def __init__(self):
        self.win = None
        self.props = {}
        self.active = False       # setup is running (start .. stop)
        self.disabled = False     # never show again in this run
        self.by_name = False
        self.win_id = 0

    # -- window handling (setup thread only) ------------------------------
    def _visible(self):
        """True / False, or None when this Kodi cannot tell."""
        try:
            if self.by_name:
                return xbmc.getCondVisibility('Window.IsVisible(%s)' % XML)
            if self.win_id:
                return xbmc.getCondVisibility('Window.IsVisible(%d)' % self.win_id)
        except Exception:
            pass
        return None

    def _learn_detection(self):
        try:
            self.by_name = bool(xbmc.getCondVisibility(
                'Window.IsVisible(%s)' % XML))
        except Exception:
            self.by_name = False
        self.win_id = 0
        if not self.by_name:
            try:
                did = xbmcgui.getCurrentWindowDialogId()
                if did >= 13000 and xbmc.getCondVisibility(
                        'Window.IsVisible(%d)' % did):
                    self.win_id = did
            except Exception:
                pass

    def _show(self):
        self._drop()
        try:
            self.win = _Window(XML, _paths.ADDON_PATH, 'Default', '1080i',
                               props=dict(self.props))
            self.win.show()
        except Exception as e:
            _log('show failed: %s' % e, xbmc.LOGWARNING)
            self.win = None
            return False
        xbmc.sleep(400)
        self._learn_detection()
        return True

    def _drop(self, close=True):
        w, self.win = self.win, None
        if w is None:
            return
        if close:
            try:
                w.close()
            except Exception:
                pass
        try:
            del w
        except Exception:
            pass

    def _set(self, key, value):
        self.props[key] = value
        if self.win is not None:
            try:
                self.win.setProperty(key, value)
            except Exception:
                pass

    def _wait_calm(self, max_s):
        mon = xbmc.Monitor()
        calm_since = None
        deadline = time.time() + max_s
        reason = ''
        while time.time() < deadline and not mon.abortRequested():
            reason = _busy()
            if reason:
                calm_since = None
            else:
                calm_since = calm_since or time.time()
                if time.time() - calm_since >= STABLE_S:
                    return True
            if mon.waitForAbort(0.25):
                return False
        _log('screen not calm after %ds (%s) - backdrop stays off for now'
             % (max_s, reason or '?'))
        return False

    # -- public -----------------------------------------------------------
    def start(self):
        if self.active or self.disabled:
            return
        t_en, t_ar = _pair(30770)
        b_en, b_ar = _pair(30771)
        self.props.update({'title_en': t_en, 'title_ar': t_ar,
                           'body_en': b_en, 'body_ar': b_ar,
                           'step': '', 'done': ''})
        self.active = True
        _home_prop('1')
        if not self._wait_calm(ENSURE_MAX_S):
            return                      # ensure() tries again later
        if not self._show():
            return
        xbmc.sleep(300)
        if xbmc.getCondVisibility('System.HasModalDialog'):
            # This Kodi counts the backdrop as modal - the wizard would wait on
            # it forever. Drop it; setup runs exactly as before.
            _log('backdrop counts as a modal dialog on this Kodi - disabled',
                 xbmc.LOGWARNING)
            self.disabled = True
            self._drop()
            return
        _log('backdrop shown (visibility check: %s)' % (
            'xml name' if self.by_name else
            ('id %d' % self.win_id) if self.win_id else 'unavailable'))

    def pause(self, why=''):
        """Close the backdrop before something that reloads the skin."""
        if self.win is not None:
            _log('backdrop hidden%s' % (' (%s)' % why if why else ''))
            self._drop()

    def ensure(self):
        """Show the backdrop again if it is not up - only once calm."""
        if not self.active or self.disabled:
            return
        if self.win is not None:
            vis = self._visible()
            if vis or vis is None:
                return                  # up (or cannot tell: leave it alone)
            # Torn down by a reload we did not pause for: forget the dead
            # window WITHOUT calling into it.
            self._drop(close=False)
        if not self._wait_calm(ENSURE_MAX_S):
            return
        if self._show():
            _log('backdrop shown again')

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
        self._drop()
        _home_prop('')
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


def pause(why=''):
    _guard(_OVERLAY.pause, why)


def ensure():
    _guard(_OVERLAY.ensure)


def step(sid):
    _guard(_OVERLAY.step, sid)


def finish(sid):
    _guard(_OVERLAY.finish, sid)


def stop():
    _guard(_OVERLAY.stop)


def shown():
    return _OVERLAY.win is not None and not _OVERLAY.disabled
