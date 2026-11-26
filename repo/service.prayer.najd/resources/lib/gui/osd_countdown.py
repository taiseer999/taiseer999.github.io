# -*- coding: utf-8 -*-
"""Small next-prayer countdown shown together with the player bar.

How it works (tested in Kodi):
- The countdown text lives in a Home-window property, refreshed every second.
- A pill image + label that reads that property are added *inside* the skin's
  player-bar dialogs (VideoOSD, or the seek bar when it shows on its own).
  Being part of those dialogs, they appear and disappear with the bar, are drawn
  above the bar's own top fade, and never take focus — the remote keeps working.
- setLabel() is never called on these controls: an id added to a skin window can
  collide with skin controls, so the label only reads the property via $INFO.
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.core.prayer_engine import NAMES

PROP = 'NajdPrayer.OsdCountdown'
LABEL = '$INFO[Window(Home).Property(%s)]' % PROP
BOX_W, BOX_H, TOP = 460, 58, 46  # in 1920x1080 units
# (window id, skin xml file, extra visibility condition)
# 12901 = player bar (VideoOSD): drawn inside it, above its top fade.
# 12005 = full-screen video window: covers the seek bar / pause / info cases when
#         the player bar itself is closed. (The seek-bar dialog 10115 does not
#         accept added controls, so it is not used.)
TARGETS = (
    (12901, 'VideoOSD.xml', ''),
    (12005, 'VideoFullScreen.xml',
     '!Window.IsVisible(videoosd) + [Window.IsVisible(seekbar) | Player.Seeking | Player.ShowInfo]'),
)
MAX_UNVERIFIED_ATTACHES = 3  # safety: never pile up controls in a skin we cannot verify


def _skin_info():
    """Return (skin_dir_path, res_folder, width, height) of the active skin."""
    try:
        skin = xbmcaddon.Addon(xbmc.getSkinDir())
        path = skin.getAddonInfo('path')
        xml = open(os.path.join(path, 'addon.xml'), encoding='utf-8').read()
        tags = re.findall(r'<res\b[^>]*>', xml)
        pick = next((t for t in tags if 'default="true"' in t), tags[0] if tags else '')
        w = int(re.search(r'width="(\d+)"', pick).group(1))
        h = int(re.search(r'height="(\d+)"', pick).group(1))
        m = re.search(r'folder="([^"]+)"', pick)
        return path, (m.group(1) if m else ''), w, h
    except Exception:
        return '', '', 1920, 1080


def _window_origin(skin_path, res_folder, filename):
    """Window-level offset of a skin window (controls we add are relative to it)."""
    try:
        folder = os.path.join(skin_path, res_folder)
        name = next(f for f in os.listdir(folder) if f.lower() == filename.lower())
        root = ET.parse(os.path.join(folder, name)).getroot()
        x = y = 0.0
        coords = root.find('coordinates')
        for node in ([coords] if coords is not None else []) + [root]:
            for tag, axis in (('left', 'x'), ('posx', 'x'), ('top', 'y'), ('posy', 'y')):
                el = node.find(tag)
                if el is not None and (el.text or '').strip().lstrip('-').replace('.', '', 1).isdigit():
                    if axis == 'x':
                        x = float(el.text)
                    else:
                        y = float(el.text)
        return x, y
    except Exception:
        return 0.0, 0.0


class OsdCountdown(object):
    def __init__(self, addon_path):
        self.pill = os.path.join(addon_path, 'resources', 'skins', 'Default', 'media', 'osd_pill.png')
        self._skin = None
        self._geom = None          # (x, y, w, h) in skin units
        self._origins = {}
        self._ids = {}             # window id -> our label's control id
        self._verified = set()     # windows where we could confirm our controls exist
        self._attaches = {}        # window id -> number of attach attempts
        self._session = set()      # windows already handled during this visibility period
        self._last = None

    def _layout(self):
        skin_dir = xbmc.getSkinDir()
        if skin_dir != self._skin:
            path, res, sw, sh = _skin_info()
            sx, sy = sw / 1920.0, sh / 1080.0
            w, h = int(BOX_W * sx), int(BOX_H * sy)
            self._geom = (int((sw - w) / 2), int(TOP * sy), w, h)
            self._origins = {wid: _window_origin(path, res, f) for wid, f, _c in TARGETS}
            self._ids = {}
            self._verified, self._attaches, self._session = set(), {}, set()
            self._skin = skin_dir
        return self._geom

    def _present(self, win, wid, x, w):
        cid = self._ids.get(wid)
        if cid is None:
            return False
        try:
            c = win.getControl(cid)
            return isinstance(c, xbmcgui.ControlLabel) and c.getX() == x and c.getWidth() == w
        except Exception:
            return False

    def _ensure(self, wid, cond):
        x, y, w, h = self._layout()
        ox, oy = self._origins.get(wid, (0.0, 0.0))
        x, y = int(x - ox), int(y - oy)
        win = xbmcgui.Window(wid)
        if self._present(win, wid, x, w):
            self._verified.add(wid)
            return
        # Attach at most once per visibility period, and stop for good in a skin
        # where our controls can never be confirmed (prevents piling them up).
        if wid in self._session:
            return
        if wid not in self._verified and self._attaches.get(wid, 0) >= MAX_UNVERIFIED_ATTACHES:
            return
        self._session.add(wid)
        self._attaches[wid] = self._attaches.get(wid, 0) + 1
        bg = xbmcgui.ControlImage(x, y, w, h, self.pill)
        lb = xbmcgui.ControlLabel(x, y, w, h, LABEL, font='font13', textColor='FFFFFFFF',
                                  alignment=0x00000002 | 0x00000004)  # center x | center y
        win.addControls([bg, lb])
        vis = '!String.IsEmpty(Window(Home).Property(%s))' % PROP
        if cond:
            vis += ' + ' + cond
        for c in (bg, lb):
            c.setVisibleCondition(vis)
        self._ids[wid] = lb.getId()

    def update(self, enabled, upcoming):
        """upcoming: (prayer_key, datetime) or None. Call ~4x per second."""
        home = xbmcgui.Window(10000)
        if not enabled or not upcoming or not xbmc.Player().isPlayingVideo():
            if self._last is not None:
                home.clearProperty(PROP)   # empty text hides any attached copy
                self._last = None
            return
        key, dt = upcoming
        total = max(0, int((dt - datetime.now()).total_seconds()))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        text = 'باقي على %s  %02d:%02d:%02d' % (NAMES[key], h, m, s)
        if text != self._last:
            home.setProperty(PROP, text)
            self._last = text
        for wid, _f, cond in TARGETS:
            if xbmc.getCondVisibility('Window.IsVisible(%d)' % wid):
                try:
                    self._ensure(wid, cond)
                except Exception as exc:
                    xbmc.log('[NajdPrayer] osd countdown attach %d failed: %s' % (wid, exc), xbmc.LOGERROR)
            else:
                self._session.discard(wid)

    def detach(self):
        try:
            xbmcgui.Window(10000).clearProperty(PROP)
        except Exception:
            pass
        self._last = None
