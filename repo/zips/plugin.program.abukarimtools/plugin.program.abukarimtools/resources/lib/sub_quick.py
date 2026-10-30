# -*- coding: utf-8 -*-
"""
AF3 Subtitle Look button (4.6.5) - the runtime half of the 'af3_substyle' toggle.

The patcher adds one button to the Arctic Fuse 3 player OSD, just before the
Video settings button. It runs RunPlugin(...?mode=subtitle_style), which opens
this small panel at the top right (so the subtitle line stays visible at the
bottom and every change previews live):

  * Height     Left/Right  -> subtitles.marginvertical, the distance of the line
                              from the bottom of the screen in percent
                              (POS_MIN..POS_MAX: never under the screen edge,
                              at most half the screen). Position is set to
                              Bottom (1), where Kodi places the line at
                              screen height - margin.
               OK          -> Kodi's default margin (4.95 %).
  * Font size  Left/Right  -> subtitles.fontsize
  * Font       OK (or Left/Right) -> next / previous of subtitles.fontname,
                              wrapping around (a loop).

All are Kodi's own settings over JSON-RPC: Kodi reloads the subtitle style on
a settings change, so the playing line moves / changes at once. (The
SubtitleShiftUp/Down actions used before accelerate with key repeat and depend
on the frame time, so they could never land on a known height.)
"""

import json
import os
import re

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'plugin.program.abukarimtools'
XML = 'abk_subquick.xml'

POS_ROW, SIZE_ROW, FONT_ROW = 101, 102, 103
POS_BAR, SIZE_BAR = 201, 202
POS_NIB, SIZE_NIB = 211, 212

ACTION_LEFT, ACTION_RIGHT = 1, 2
ACTION_CLOSE = (9, 10, 92, 110)          # parent dir, previous menu, back, nav back
POS_KEY = 'subtitles.marginvertical'      # percent of the screen height, Kodi range 0..50
POS_MIN, POS_MAX = 1.0, 50.0             # 1 %: just above the edge; 50 %: half the screen
POS_STEP = 1.0
POS_DEFAULT = 4.95                       # Kodi's default
SIZE_STEP = 2

# bar geometry inside a row (abk_subquick.xml): bar left 28, right 28, row 592
BAR_X, BAR_W, NIB_W, NIB_Y = 28, 536, 26, 71

ALIGN_BOTTOM = 1                         # Bottom: line at screen height - marginvertical

_BUSY = 'abk.subquick.open'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SubLook] %s' % msg, level)


def _arabic():
    try:
        return xbmc.getLanguage(xbmc.ISO_639_1).lower().startswith('ar')
    except Exception:
        return False


def _t(ar, en):
    return ar if _arabic() else en


# ---------------------------------------------------------------- settings
def _rpc(method, params=None):
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        payload['params'] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
    except Exception:
        return {}


def _get(key):
    return (_rpc('Settings.GetSettingValue', {'setting': key}).get('result') or {}).get('value')


def _set(key, value):
    answer = _rpc('Settings.SetSettingValue', {'setting': key, 'value': value})
    ok = bool(answer.get('result'))
    if not ok:
        _log('%s=%r refused (%s)' % (key, value, answer.get('error')), xbmc.LOGWARNING)
    return ok


def _subtitle_settings():
    answer = _rpc('Settings.GetSettings', {'level': 'expert',
                                           'filter': {'section': 'player', 'category': 'subtitles'}})
    out = {}
    for setting in ((answer.get('result') or {}).get('settings') or []):
        if isinstance(setting, dict) and setting.get('id'):
            out[setting['id']] = setting
    return out


def _font_name(value, label):
    """'DexHub InterArabicBold' -> 'Inter Arabic Bold', 'arial.ttf' -> 'arial'."""
    text = str(label or value or '').strip()
    if text.lower().startswith('dexhub '):
        text = text[7:]
    text = re.sub(r'\.(ttf|otf|ttc)$', '', text, flags=re.I)
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    return text.replace('_', ' ').strip() or str(value)


def _bottom():
    if _get('subtitles.align') != ALIGN_BOTTOM:
        _set('subtitles.align', ALIGN_BOTTOM)


# ------------------------------------------------------------------ window
class SubLookWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.margin = POS_DEFAULT
        self.size_min, self.size_max = 12, 74
        self.fonts = []

    # setup
    def onInit(self):
        settings = _subtitle_settings()
        size = settings.get('subtitles.fontsize') or {}
        try:
            self.size_min = int(size.get('minimum', self.size_min))
            self.size_max = int(size.get('maximum', self.size_max))
        except (TypeError, ValueError):
            pass
        font = settings.get('subtitles.fontname') or {}
        self.fonts = [(o['value'], _font_name(o['value'], o.get('label')))
                      for o in (font.get('options') or [])
                      if isinstance(o, dict) and o.get('value') not in (None, '')]
        self.setProperty('sq.title', _t('مظهر الترجمة', 'Subtitle look'))
        self.setProperty('sq.hint', _t('يمين ويسار للتعديل، ورجوع للإغلاق',
                                       'Left / Right to adjust, Back to close'))
        self.setProperty('sq.pos.hint', _t('اضغط لإعادة الارتفاع الافتراضي', 'Press OK for the default height'))
        self.setProperty('sq.pos.label', _t('ارتفاع الترجمة', 'Subtitle height'))
        self.setProperty('sq.size.label', _t('حجم الخط', 'Font size'))
        self.setProperty('sq.font.label', _t('الخط', 'Font'))
        self.setProperty('sq.font.hint', _t('اضغط للانتقال إلى الخط التالي', 'Press OK for the next font'))
        self.setProperty('sq.nosubs', _t('الترجمة متوقفة الآن، فلن تظهر المعاينة',
                                         'Subtitles are off, so there is nothing to preview'))
        try:
            self.margin = float(_get(POS_KEY))
        except (TypeError, ValueError):
            self.margin = POS_DEFAULT
        self.show_position()
        self.show_size(_get('subtitles.fontsize'))
        self.show_font(_get('subtitles.fontname'))
        self.setFocusId(POS_ROW)

    # drawing
    def _bars(self, bar, nib, percent):
        percent = max(0.0, min(100.0, float(percent)))
        try:
            self.getControl(bar).setPercent(percent)
        except Exception:
            pass
        try:
            x = BAR_X + int(round(BAR_W * percent / 100.0)) - NIB_W // 2
            self.getControl(nib).setPosition(x, NIB_Y)
        except Exception:
            pass

    def show_position(self):
        value = max(POS_MIN, min(POS_MAX, self.margin))
        self.setProperty('sq.pos.value', ('%.1f' % value).rstrip('0').rstrip('.') + '%')
        self._bars(POS_BAR, POS_NIB, (value - POS_MIN) * 100.0 / (POS_MAX - POS_MIN))

    def show_size(self, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = self.size_min
        self.setProperty('sq.size.value', str(value))
        span = max(1, self.size_max - self.size_min)
        self._bars(SIZE_BAR, SIZE_NIB, (value - self.size_min) * 100.0 / span)

    def show_font(self, value):
        label = next((name for v, name in self.fonts if v == value), None)
        self.setProperty('sq.font.value', label or _font_name(value, None))

    # changes
    def set_margin(self, value):
        value = round(max(POS_MIN, min(POS_MAX, float(value))), 2)
        _bottom()
        if _set(POS_KEY, float(value)):
            self.margin = value
        self.show_position()

    def move(self, direction):
        try:
            current = float(_get(POS_KEY))
        except (TypeError, ValueError):
            current = self.margin
        # snap to the 1 % grid, then step (Kodi's default 4.95 -> 5 / 4)
        base = round(current) if abs(current - round(current)) > 0.01 else current
        if direction > 0:
            target = base + POS_STEP if base <= current + 0.01 else base
        else:
            target = base - POS_STEP if base >= current - 0.01 else base
        self.set_margin(target)

    def resize(self, direction):
        try:
            current = int(_get('subtitles.fontsize'))
        except (TypeError, ValueError):
            current = self.size_min
        value = max(self.size_min, min(self.size_max, current + direction * SIZE_STEP))
        if value != current:
            _set('subtitles.fontsize', value)
        self.show_size(value)

    def next_font(self, direction=1):
        if not self.fonts:
            return
        values = [v for v, _name in self.fonts]
        current = _get('subtitles.fontname')
        index = values.index(current) if current in values else -1
        value = values[(index + direction) % len(values)]
        _set('subtitles.fontname', value)
        self.show_font(value)

    # input
    def onAction(self, action):
        aid = action.getId()
        if aid in ACTION_CLOSE:
            self.close()
            return
        if aid not in (ACTION_LEFT, ACTION_RIGHT):
            return
        direction = 1 if aid == ACTION_RIGHT else -1
        focus = self.getFocusId()
        if focus == POS_ROW:
            self.move(direction)
        elif focus == SIZE_ROW:
            self.resize(direction)
        elif focus == FONT_ROW:
            self.next_font(direction)

    def onClick(self, control_id):
        if control_id == FONT_ROW:
            self.next_font(1)
        elif control_id == POS_ROW:
            self.set_margin(POS_DEFAULT)


def open_window():
    home = xbmcgui.Window(10000)
    if home.getProperty(_BUSY) == '1':
        return
    if not xbmc.getCondVisibility('Player.HasVideo'):
        return
    home.setProperty(_BUSY, '1')
    try:
        # the OSD bar and its popups go, so the subtitle line is the preview
        for name in ('videoosd', '1146', '1147'):
            xbmc.executebuiltin('Dialog.Close(%s,true)' % name)
        path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
        window = SubLookWindow(XML, path, 'Default', '1080i')
        window.doModal()
        del window
    except Exception as exc:
        _log('panel failed: %s' % exc, xbmc.LOGWARNING)
    finally:
        home.clearProperty(_BUSY)
