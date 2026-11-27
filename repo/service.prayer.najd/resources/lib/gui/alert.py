# -*- coding: utf-8 -*-
"""Popup adhan alert window, shown non-blocking from the background service.

Uses WindowXMLDialog.show() (not doModal) so it can be raised directly from the
scheduler's main thread without blocking the service loop. onInit is not called
for a show() window and Window.Property is not read from a non-current window,
so labels are set on controls by id right after the window is up. A daemon timer
closes it after `seconds`; any key / the OK button dismiss it immediately.
References are kept in a module-level list so the window is not garbage collected
while on screen.
"""
import os
import threading

import xbmc
import xbmcgui

_ACTION_CLOSE = (7, 9, 10, 92, 247, 100, 101)  # select / back / escape / nav / clicks
_LIVE = []  # keep references alive while shown


class _AlertWindow(xbmcgui.WindowXMLDialog):
    # WindowXMLDialog consumes only positional args in __new__; extra keywords
    # must be stripped here or construction fails.
    def __new__(cls, *args, **kwargs):
        return super(_AlertWindow, cls).__new__(cls, *args)

    def __init__(self, *args, **kwargs):
        super(_AlertWindow, self).__init__(*args)

    def onAction(self, action):
        if action.getId() in _ACTION_CLOSE:
            dismiss(self)

    def onClick(self, cid):
        dismiss(self)


def _apply_labels(win, lines):
    for _ in range(15):
        missing = False
        for cid, text in lines.items():
            try:
                win.getControl(cid).setLabel(text)
            except Exception:
                missing = True
        if not missing:
            return
        xbmc.sleep(100)


def dismiss(win):
    try:
        win.close()
    except Exception:
        pass
    try:
        _LIVE.remove(win)
    except ValueError:
        pass


def show_alert(addon_path, lead, prayer, time_str, city, seconds=20, image_key=None):
    subtitle = time_str if not city else ('%s  •  %s' % (time_str, city))
    lines = {101: lead, 102: prayer, 103: subtitle}
    try:
        win = _AlertWindow('alert.xml', addon_path, 'Default')
    except Exception as exc:
        xbmc.log('[NajdPrayer] alert construct failed: %s' % exc, xbmc.LOGERROR)
        return
    _LIVE.append(win)
    win.show()
    _apply_labels(win, lines)
    if image_key:
        img = os.path.join(addon_path, 'resources', 'skins', 'Default', 'media', 'modern', 'nm_%s.png' % image_key)
        if os.path.exists(img):
            try:
                win.getControl(104).setImage(img)
                win.getControl(102).setLabel('')     # the drawn name replaces the plain text
            except Exception:
                pass
    timer = threading.Timer(max(3, seconds), dismiss, args=(win,))
    timer.daemon = True
    timer.start()
