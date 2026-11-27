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
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.core.prayer_engine import NAMES, name_of

PROP = 'NajdPrayer.OsdCountdown'
# One property and one pill per look, so switching the look in the settings simply
# empties the old property and the controls attached for the old look disappear.
STYLES = {                                               # pill sizes
    0: (PROP, 460, 'osd_pill.png'),
    1: (PROP + 'Full', 900, 'osd_pill_wide.png'),
}
# The looks the viewer can pick (setting osd_style) and the pill each one uses.
COUNTDOWN, FULL, SHORT, TIME_ONLY, ALTERNATE = 0, 1, 2, 3, 4
LOOK_PILL = {COUNTDOWN: 0, FULL: 1, SHORT: 0, TIME_ONLY: 0, ALTERNATE: 1}
ALTERNATE_SECONDS = 6
BOX_H, TOP = 58, 46  # in 1920x1080 units


def _count(n, one, two, few, many):
    """Arabic counted noun after «بعد»: ساعة / ساعتين / 3 ساعات / 11 ساعة."""
    if n == 1:
        return one
    if n == 2:
        return two
    if 3 <= n <= 10:
        return '%d %s' % (n, few)
    return '%d %s' % (n, many)


def remaining_words(total):
    """Seconds -> «8 ساعات و40 دقيقة» (whole minutes, like the countdown shows)."""
    h, m = divmod(max(0, int(total)) // 60, 60)
    parts = []
    if h:
        parts.append(_count(h, 'ساعة', 'ساعتين', 'ساعات', 'ساعة'))
    if m:
        parts.append(_count(m, 'دقيقة', 'دقيقتين', 'دقائق', 'دقيقة'))
    return ' و'.join(parts)


def time_12h(dt):
    return '%s %s' % (dt.strftime('%I:%M'), 'ص' if dt.hour < 12 else 'م')


def look_text(look, key, dt, total):
    name = name_of(key, dt)
    if look == ALTERNATE:      # the full sentence, then the seconds countdown, in turn
        look = FULL if (int(time.time()) // ALTERNATE_SECONDS) % 2 == 0 else COUNTDOWN
    if look == FULL:
        return full_text(key, dt, total)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if look == SHORT:
        return '%s %s  •  بعد %02d:%02d' % (name, time_12h(dt), h, m)
    if look == TIME_ONLY:
        return 'صلاة %s %s' % (name, time_12h(dt))
    return 'باقي على %s  %02d:%02d:%02d' % (name, h, m, s)


def full_text(key, dt, total):
    words = remaining_words(total)
    when = ('يحين الأذان بعد %s' % words) if words else 'يحين الأذان بعد أقل من دقيقة'
    return 'وقت صلاة %s %s  •  %s' % (name_of(key, dt), time_12h(dt), when)
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
        self.media = os.path.join(addon_path, 'resources', 'skins', 'Default', 'media')
        self.style = 0
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
        if (skin_dir, self.style) != self._skin:
            path, res, sw, sh = _skin_info()
            sx, sy = sw / 1920.0, sh / 1080.0
            w, h = int(STYLES[self.style][1] * sx), int(BOX_H * sy)
            self._geom = (int((sw - w) / 2), int(TOP * sy), w, h)
            self._origins = {wid: _window_origin(path, res, f) for wid, f, _c in TARGETS}
            self._ids = {}
            self._verified, self._attaches, self._session = set(), {}, set()
            self._skin = (skin_dir, self.style)
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
        prop, _w, pill = STYLES[self.style]
        bg = xbmcgui.ControlImage(x, y, w, h, os.path.join(self.media, pill))
        lb = xbmcgui.ControlLabel(x, y, w, h, '$INFO[Window(Home).Property(%s)]' % prop, font='font13', textColor='FFFFFFFF',
                                  alignment=0x00000002 | 0x00000004)  # center x | center y
        win.addControls([bg, lb])
        vis = '!String.IsEmpty(Window(Home).Property(%s))' % prop
        if cond:
            vis += ' + ' + cond
        for c in (bg, lb):
            c.setVisibleCondition(vis)
        self._ids[wid] = lb.getId()

    def update(self, enabled, upcoming, style=0):
        """upcoming: (prayer_key, datetime) or None. Call ~4x per second."""
        home = xbmcgui.Window(10000)
        look = style if style in LOOK_PILL else COUNTDOWN
        style = LOOK_PILL[look]
        if style != self.style:
            home.clearProperty(STYLES[self.style][0])   # hides the old look's pill
            self.style, self._last = style, None
        prop = STYLES[style][0]
        if not enabled or not upcoming or not xbmc.Player().isPlayingVideo():
            if self._last is not None:
                home.clearProperty(prop)   # empty text hides any attached copy
                self._last = None
            return
        key, dt = upcoming
        text = look_text(look, key, dt, max(0, int((dt - datetime.now()).total_seconds())))
        if text != self._last:
            home.setProperty(prop, text)
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
            for prop, _w, _p in STYLES.values():
                xbmcgui.Window(10000).clearProperty(prop)
        except Exception:
            pass
        self._last = None


# ---------------------------------------------------------------------------
# Home screen: a small status item (logo + "العصر بعد 00:38:49") in the top bar,
# next to the skin's clock / temperature / network icons. Same safe technique:
# controls are added once to the Home window and only read a property.
# Positions are in 1920x1080 units, measured on the Abu Karim build's top bar
# (status chips row, just left of the CPU-temperature chip), scaled to the skin.
# ---------------------------------------------------------------------------
HOME_WINDOW = 10000
HOME_PROP = 'NajdPrayer.HomeBadge'
HOME_RIGHT, HOME_TOP, HOME_H = 1600, 16, 36     # right edge of the item, top, height
HOME_ICON, HOME_GAP, HOME_TEXT_W = 26, 8, 380


class HomeBadge(object):
    def __init__(self, addon_path):
        self.logo = os.path.join(addon_path, 'resources', 'skins', 'Default', 'media', 'logo.png')
        self._skin = None
        self._label_id = None
        self._geom = None
        self._verified = False
        self._attaches = 0
        self._session = False
        self._last = None

    def _layout(self):
        skin_dir = xbmc.getSkinDir()
        if skin_dir != self._skin:
            _p, _r, sw, sh = _skin_info()
            sx, sy = sw / 1920.0, sh / 1080.0
            icon = int(HOME_ICON * sy)
            right, top, hgt = int(HOME_RIGHT * sx), int(HOME_TOP * sy), int(HOME_H * sy)
            icon_x = right - icon
            text_w = int(HOME_TEXT_W * sx)
            text_x = icon_x - int(HOME_GAP * sx) - text_w
            self._geom = (icon_x, top + (hgt - icon) // 2, icon, text_x, top, text_w, hgt)
            self._skin, self._label_id = skin_dir, None
            self._verified, self._attaches, self._session = False, 0, False
        return self._geom

    def _present(self, win, text_x, text_w):
        if self._label_id is None:
            return False
        try:
            c = win.getControl(self._label_id)
            return isinstance(c, xbmcgui.ControlLabel) and c.getX() == text_x and c.getWidth() == text_w
        except Exception:
            return False

    def _ensure(self):
        icon_x, icon_y, icon, text_x, top, text_w, hgt = self._layout()
        win = xbmcgui.Window(HOME_WINDOW)
        if self._present(win, text_x, text_w):
            self._verified = True
            return
        if self._session or (not self._verified and self._attaches >= MAX_UNVERIFIED_ATTACHES):
            return
        self._session = True
        self._attaches += 1
        img = xbmcgui.ControlImage(icon_x, icon_y, icon, icon, self.logo)
        lb = xbmcgui.ControlLabel(text_x, top, text_w, hgt, '$INFO[Window(Home).Property(%s)]' % HOME_PROP,
                                  font='font13', textColor='FFFFFFFF',
                                  alignment=0x00000001 | 0x00000004)  # right | center y
        win.addControls([img, lb])
        vis = '!String.IsEmpty(Window(Home).Property(%s))' % HOME_PROP
        for c in (img, lb):
            c.setVisibleCondition(vis)
        self._label_id = lb.getId()

    def update(self, enabled, upcoming):
        home = xbmcgui.Window(HOME_WINDOW)
        if not enabled or not upcoming:
            if self._last is not None:
                home.clearProperty(HOME_PROP)
                self._last = None
            return
        key, dt = upcoming
        total = max(0, int((dt - datetime.now()).total_seconds()))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        text = '%s بعد %02d:%02d:%02d' % (name_of(key, dt), h, m, s)
        if text != self._last:
            home.setProperty(HOME_PROP, text)
            self._last = text
        if xbmc.getCondVisibility('Window.IsVisible(home)'):
            try:
                self._ensure()
            except Exception as exc:
                xbmc.log('[NajdPrayer] home badge attach failed: %s' % exc, xbmc.LOGERROR)
        else:
            self._session = False

    def detach(self):
        try:
            xbmcgui.Window(HOME_WINDOW).clearProperty(HOME_PROP)
        except Exception:
            pass
        self._last = None
