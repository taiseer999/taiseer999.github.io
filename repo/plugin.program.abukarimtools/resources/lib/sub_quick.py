# -*- coding: utf-8 -*-
"""
AF3 Subtitle Look button - the runtime half of the 'af3_substyle' toggle.

4.6.27: the panel now carries the rows of Dex Hub's "Subtitle look"
(skin.dexhub / Dex Hub 5.10.451, skinui/subwindow.py + substyle.py), on the
right of the screen so the subtitle line stays visible and every change
previews live. One list (abk_subquick.xml, id 100); Up / Down move, Left /
Right change the row, OK changes it forward or opens it:

  Show subtitles   on / off
  Delay            SubtitleDelayPlus / Minus (Kodi's own player action)
  Auto sync        Dex Hub's best-synced subtitle (DexSubtitles' own flow
                   when Dex Hub is missing); only shown when one is there
  Height           subtitles.marginvertical in percent (AB Tools 4.6.5 - a
                   known height, not SubtitleShift steps); OK = Kodi default
  Font, Size, Style, Colour (+ its Shade), Opacity, Border, Border colour,
  Background (+ box / shadow rows for the chosen background), Blur, Line
  spacing, Position, and Kodi's own subtitle dialog.

Everything except Show / Delay is one of Kodi's subtitle settings, read and
written over JSON-RPC: Kodi reloads the subtitle style on a change, so the
playing line is the preview.
"""

import json
import re

import xbmc
import xbmcaddon
import xbmcgui

ADDON_ID = 'plugin.program.abukarimtools'
XML = 'abk_subquick.xml'
LIST = 100

LEFT, RIGHT = 1, 2
CLOSE = (9, 10, 92, 110, 216, 247, 257, 275, 61448, 61467)

POS_KEY = 'subtitles.marginvertical'      # percent of the screen height, Kodi range 0..50
POS_MIN, POS_MAX = 1.0, 50.0
POS_STEP = 1.0
POS_DEFAULT = 4.95                       # Kodi's default
ALIGN_BOTTOM = 1

PRESET_PROP = 'abk.substyle.preset'
BASE_PROP = 'abk.substyle.base'
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


def _all():
    """{setting id: setting} of Kodi's subtitle category (values and options)."""
    answer = _rpc('Settings.GetSettings', {'level': 'expert',
                                           'filter': {'section': 'player', 'category': 'subtitles'}})
    out = {}
    for setting in ((answer.get('result') or {}).get('settings') or []):
        if isinstance(setting, dict) and setting.get('id'):
            out[setting['id']] = setting
    # Kodi leaves its colour buttons out of that list; each is read on its own
    for key, _ar, _en, kind, _extra in ROWS:
        if key not in out and kind == 'colour':
            value = _get(key)
            if value is not None:
                out[key] = {'id': key, 'value': value}
    return out


def _player_id():
    for p in (_rpc('Player.GetActivePlayers').get('result') or []):
        if p.get('type') == 'video':
            return p.get('playerid')
    return None


def _subs_on():
    pid = _player_id()
    if pid is None:
        return False
    r = _rpc('Player.GetProperties', {'playerid': pid, 'properties': ['subtitleenabled']})
    return bool((r.get('result') or {}).get('subtitleenabled'))


def _act(name):
    """A player action, waited for; its slider is closed again (the row shows the value)."""
    xbmc.executebuiltin('Action(%s)' % name, True)
    xbmc.executebuiltin('Dialog.Close(sliderdialog,true)')


# ------------------------------------------------- Dex Hub's subtitle look
# (Dex Hub 5.10.451 skinui/substyle.py: colours, shades, rows, ready looks)
TEXT = (('FFFFFFFF', 'أبيض', 'White'), ('FFD9D9D9', 'رمادي فاتح', 'Light grey'), ('FFFFD700', 'ذهبي', 'Gold'),
        ('FF00E5FF', 'سماوي', 'Cyan'), ('FFFF5C5C', 'مرجاني', 'Coral'), ('FF00FF88', 'أخضر', 'Green'),
        ('FFFFAD42', 'برتقالي', 'Orange'), ('FFFFF59D', 'أصفر فاتح', 'Soft yellow'),
        ('FFB3E5FC', 'أزرق فاتح', 'Pale blue'), ('FFE1BEE7', 'بنفسجي فاتح', 'Lavender'))
OUTLINE = (('FF000000', 'أسود', 'Black'), ('FFFFFFFF', 'أبيض', 'White'), ('FF00E5FF', 'سماوي', 'Cyan'),
           ('FFFF5C5C', 'مرجاني', 'Coral'), ('FF212121', 'فحمي', 'Charcoal'), ('FF8E44AD', 'بنفسجي', 'Purple'))
DARK = (('FF000000', 'أسود', 'Black'), ('FF1C1C1E', 'رمادي داكن', 'Dark grey'), ('FF0B1A33', 'كحلي', 'Navy'),
        ('FF2B1B3F', 'بنفسجي داكن', 'Deep purple'), ('FFFFFFFF', 'أبيض', 'White'))

SHADE_STEPS = (-0.45, -0.30, -0.15, 0.0, 0.25, 0.45, 0.65)
SHADE_NAMES = (('أغمق كثيرًا', 'Much darker'), ('أغمق', 'Darker'), ('أغمق قليلًا', 'A little darker'),
               ('الأصلي', 'As it is'), ('أفتح قليلًا', 'A little lighter'), ('أفتح', 'Lighter'),
               ('أفتح كثيرًا', 'Much lighter'))

# id, Arabic, English, kind, extra
ROWS = (
    ('subtitles.fontname', 'الخط', 'Font', 'options', None),
    ('subtitles.fontsize', 'الحجم', 'Size', 'int', (12, 74, 2)),
    ('subtitles.style', 'النمط', 'Style', 'choice', ((0, 'عادي', 'Normal'), (1, 'عريض', 'Bold'),
                                                     (2, 'مائل', 'Italic'), (3, 'عريض مائل', 'Bold italic'))),
    ('subtitles.colorpick', 'اللون', 'Colour', 'colour', TEXT),
    ('subtitles.opacity', 'العتامة', 'Opacity', 'pct', (0, 100, 5)),
    ('subtitles.bordersize', 'الحدود', 'Border', 'pct', (0, 100, 4)),
    ('subtitles.bordercolorpick', 'لون الحدود', 'Border colour', 'colour', OUTLINE),
    ('subtitles.backgroundtype', 'الخلفية', 'Background', 'choice', ((0, 'بلا خلفية', 'None'), (1, 'ظل', 'Shadow'),
                                                                     (2, 'صندوق', 'Box'), (3, 'صندوق مربع', 'Square box'))),
    ('subtitles.bgcolorpick', 'لون الصندوق', 'Box colour', 'colour', DARK),
    ('subtitles.bgopacity', 'عتامة الصندوق', 'Box opacity', 'pct', (0, 100, 5)),
    ('subtitles.shadowcolor', 'لون الظل', 'Shadow colour', 'colour', DARK),
    ('subtitles.shadowopacity', 'عتامة الظل', 'Shadow opacity', 'pct', (0, 100, 5)),
    ('subtitles.shadowsize', 'حجم الظل', 'Shadow size', 'pct', (0, 100, 5)),
    ('subtitles.blur', 'النعومة', 'Blur', 'pct', (0, 100, 5)),
    ('subtitles.linespacing', 'تباعد الأسطر', 'Line spacing', 'pct', (0, 100, 4)),
    ('subtitles.align', 'الموضع', 'Position', 'choice', ((1, 'أسفل الشاشة', 'Bottom'),
                                                         (2, 'تحت الصورة', 'Below picture'),
                                                         (3, 'أعلى الشاشة', 'Top'),
                                                         (4, 'فوق الصورة', 'Above picture'),
                                                         (0, 'يدوي', 'Manual'))),
)
_BOX, _SHADOW = (2, 3), (1, 2)
_SHOWN_IF = {
    'subtitles.bgcolorpick': _BOX, 'subtitles.bgopacity': _BOX,
    'subtitles.shadowcolor': _SHADOW, 'subtitles.shadowopacity': _SHADOW, 'subtitles.shadowsize': _SHADOW,
}

PRESETS = (
    ('dexhub', ('Dex Hub', 'Dex Hub'),
     {'subtitles.fontsize': 46, 'subtitles.style': 0, 'subtitles.colorpick': 'FFFFFFFF',
      'subtitles.opacity': 100, 'subtitles.bordersize': 24, 'subtitles.bordercolorpick': 'FF000000',
      'subtitles.backgroundtype': 1, 'subtitles.shadowcolor': 'FF000000', 'subtitles.shadowopacity': 60,
      'subtitles.shadowsize': 10, 'subtitles.blur': 0, 'subtitles.linespacing': 12},
     ('DexHub InterArabicBold', 'DexHub Jazeerahbold')),
    ('cinema', ('سينما', 'Cinema'),
     {'subtitles.fontsize': 44, 'subtitles.style': 0, 'subtitles.colorpick': 'FFFFF59D',
      'subtitles.opacity': 100, 'subtitles.bordersize': 20, 'subtitles.bordercolorpick': 'FF000000',
      'subtitles.backgroundtype': 1, 'subtitles.shadowcolor': 'FF000000', 'subtitles.shadowopacity': 70,
      'subtitles.shadowsize': 12, 'subtitles.blur': 0, 'subtitles.linespacing': 12},
     ('DexHub Jazeerahbold', 'DexHub InterArabicBold')),
    ('box', ('صندوق', 'Box'),
     {'subtitles.fontsize': 42, 'subtitles.style': 0, 'subtitles.colorpick': 'FFFFFFFF',
      'subtitles.opacity': 100, 'subtitles.bordersize': 0, 'subtitles.backgroundtype': 2,
      'subtitles.bgcolorpick': 'FF000000', 'subtitles.bgopacity': 60, 'subtitles.blur': 0,
      'subtitles.linespacing': 16},
     ('DexHub InterArabicRegular', 'DexHub InterArabicBold')),
    ('large', ('كبير', 'Large'),
     {'subtitles.fontsize': 56, 'subtitles.style': 1, 'subtitles.colorpick': 'FFFFFFFF',
      'subtitles.opacity': 100, 'subtitles.bordersize': 28, 'subtitles.bordercolorpick': 'FF000000',
      'subtitles.backgroundtype': 1, 'subtitles.shadowcolor': 'FF000000', 'subtitles.shadowopacity': 60,
      'subtitles.shadowsize': 12, 'subtitles.blur': 0, 'subtitles.linespacing': 12},
     ('DexHub InterArabicBold', 'DexHub Jazeerahbold')),
)

FONT_NAMES = {
    'interarabicbold': ('إنتر عربي عريض', 'Inter Arabic Bold'), 'interarabicregular': ('إنتر عربي', 'Inter Arabic'),
    'jazeerahbold': ('الجزيرة عريض', 'Al Jazeera Bold'), 'jazeerah': ('الجزيرة', 'Al Jazeera'),
    'mohandbold': ('مهند عريض', 'Mohand Bold'), 'mohandregular': ('مهند', 'Mohand'),
    'hacenpromoterbold': ('حسن عريض', 'Hacen Promoter Bold'), 'hacenpromoter': ('حسن', 'Hacen Promoter'),
    'iphone': ('آيفون عريض', 'iPhone Arabic Bold'), 'iphoneregular': ('آيفون', 'iPhone Arabic'),
    'monadibold': ('منادي عريض', 'Monadi Bold'), 'tonosbold': ('تونس عريض', 'Tonos Bold'),
}


def _rgb(argb):
    value = str(argb or 'FFFFFFFF').upper()[-6:]
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (255, 255, 255)


def shades(base):
    out = []
    r, g, b = _rgb(base)
    for step in SHADE_STEPS:
        target = 255 if step > 0 else 0
        mix = abs(step)
        out.append('FF%02X%02X%02X' % tuple(int(round(c + (target - c) * mix)) for c in (r, g, b)))
    return out


def base_of(value):
    """The ready colour a text colour is a shade of (itself, the one kept, or the nearest)."""
    value = str(value or 'FFFFFFFF').upper()
    ready = [c for c, _a, _e in TEXT]
    if value in ready:
        return value
    kept = xbmcgui.Window(10000).getProperty(BASE_PROP).upper()
    if kept in ready and value in shades(kept):
        return kept
    r, g, b = _rgb(value)
    return min(ready, key=lambda c: sum((x - y) ** 2 for x, y in zip(_rgb(c), (r, g, b))))


def shade_index(value):
    value = str(value or '').upper()
    found = shades(base_of(value))
    return found.index(value) if value in found else -1


def _font_label(value, label):
    key = str(value or '').lower().replace(' ', '')
    if key.startswith('dexhub'):
        names = FONT_NAMES.get(key[len('dexhub'):])
        if names:
            return _t(*names)
        return str(value)[len('DexHub '):]
    text = str(label or value or '').strip()
    text = re.sub(r'\.(ttf|otf|ttc)$', '', text, flags=re.I)
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    return text.replace('_', ' ').strip() or str(value)


def _font_options(setting):
    out = []
    for option in (setting or {}).get('options') or []:
        if isinstance(option, dict) and option.get('value') not in (None, ''):
            out.append((option['value'], _font_label(option['value'], option.get('label') or option['value'])))
    return out


def _value_text(row, setting, value):
    key, ar, en, kind, extra = row
    if kind == 'options':
        for option_value, label in _font_options(setting):
            if option_value == value:
                return label
        return _font_label(value, None)
    if kind == 'int':
        return '%s' % value
    if kind == 'pct':
        return '%s %%' % value
    if kind == 'choice':
        for option_value, a, e in extra:
            if option_value == value:
                return _t(a, e)
        return str(value)
    if kind == 'colour':
        for option_value, a, e in extra:
            if str(option_value).upper() == str(value or '').upper():
                return _t(a, e)
        return '#%s' % str(value or '')[-6:]
    return str(value)


def _sync_target():
    """What Auto sync runs: Dex Hub's flow, else DexSubtitles' own, else nothing."""
    if xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.dexhub)'):
        return 'RunPlugin(plugin://plugin.video.dexhub/?action=subtitle_sync)'
    if xbmc.getCondVisibility('System.AddonIsEnabled(service.subtitles.dexworld)'):
        import os
        import xbmcvfs
        try:
            path = xbmcvfs.translatePath(xbmcaddon.Addon('service.subtitles.dexworld').getAddonInfo('path'))
        except Exception:
            path = ''
        if path and os.path.isfile(os.path.join(path, 'osd.py')):
            return 'RunScript(service.subtitles.dexworld,best)'      # DexSubtitles 5.7.6+
        if path and os.path.isfile(os.path.join(path, 'abk_osd_sync.py')):
            return 'RunScript(%s)' % os.path.join(path, 'abk_osd_sync.py')
    return ''


# ------------------------------------------------------------------ window
class SubLookWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []
        self.list = None

    # rows
    def _rows(self):
        rows = []
        on = _subs_on()
        rows.append({'id': 'show', 'label': _t('إظهار الترجمة', 'Show subtitles'),
                     'value': _t('مفعّلة', 'On') if on else _t('متوقفة', 'Off'), 'adjust': True})
        rows.append({'id': 'delay', 'label': _t('التأخير', 'Delay'),
                     'value': xbmc.getInfoLabel('Player.SubtitleDelay') or '0.000 s', 'adjust': True})
        if _sync_target():
            rows.append({'id': 'sync', 'label': _t('مزامنة تلقائية', 'Auto sync'), 'value': '', 'opens': True})
        # 4.6.28: the ready looks row (Look) is taken out
        try:
            margin = float(_get(POS_KEY))
        except (TypeError, ValueError):
            margin = POS_DEFAULT
        margin = max(POS_MIN, min(POS_MAX, margin))
        rows.append({'id': 'height', 'label': _t('ارتفاع الترجمة', 'Height'),
                     'value': ('%.1f' % margin).rstrip('0').rstrip('.') + '%', 'adjust': True,
                     'pct': max(1, min(99, int(round((margin - POS_MIN) * 100.0 / (POS_MAX - POS_MIN)))))})
        settings = _all()
        background = (settings.get('subtitles.backgroundtype') or {}).get('value')
        for row in ROWS:
            key, ar, en, kind, extra = row
            setting = settings.get(key)
            if not setting:
                continue
            if key in _SHOWN_IF and background not in _SHOWN_IF[key]:
                continue
            value = setting.get('value')
            entry = {'id': key, 'label': _t(ar, en), 'value': _value_text(row, setting, value), 'adjust': True}
            if kind == 'colour':
                entry['swatches'] = [c for c, _a, _e in extra]
                upper = [c.upper() for c in entry['swatches']]
                shown = str(value or '').upper()
                if key == 'subtitles.colorpick':
                    shown = base_of(shown)          # a shade rings its colour
                    entry['value'] = dict((c.upper(), _t(a, e)) for c, a, e in extra).get(shown, entry['value'])
                entry['sel'] = upper.index(shown) if shown in upper else -1
            if kind in ('pct', 'int'):
                low, high, _step = extra
                if key == 'subtitles.fontsize':
                    low = int(setting.get('minimum', low))
                    high = int(setting.get('maximum', high))
                try:
                    entry['pct'] = max(1, min(99, int(round((float(value) - low) * 100.0 / max(1, high - low)))))
                except Exception:
                    entry['pct'] = 1
            rows.append(entry)
            if key == 'subtitles.colorpick':
                at = shade_index(value)
                rows.append({'id': 'shade', 'label': _t('درجة اللون', 'Shade'), 'adjust': True,
                             'value': _t(*SHADE_NAMES[at]) if at >= 0 else '',
                             'swatches': shades(base_of(value)), 'sel': at})
        rows.append({'id': 'kodi', 'label': _t('إعدادات Kodi للترجمة', 'Kodi subtitle settings'),
                     'value': '', 'opens': True})
        return rows

    @staticmethod
    def _swatches(li, row):
        colours = row.get('swatches') or []
        for i in range(10):
            li.setProperty('c%d' % i, colours[i] if i < len(colours) else '')
        li.setProperty('sel', str(row.get('sel', -1)) if colours else '')
        li.setProperty('n', str(len(colours)) if colours else '')

    def _item(self, row):
        li = xbmcgui.ListItem(label=row.get('label') or '', label2=row.get('value') or '', offscreen=True)
        li.setProperties({'id': str(row.get('id') or ''), 'adjust': '1' if row.get('adjust') else '',
                          'opens': '1' if row.get('opens') else '', 'pct': str(row.get('pct') or '')})
        self._swatches(li, row)
        if row.get('pct'):
            try:
                li.getVideoInfoTag().setResumePoint(float(row['pct']), 100.0)
            except Exception:
                pass
        return li

    def build(self, keep=''):
        self.rows = self._rows()
        position = 0
        if keep:
            position = next((i for i, r in enumerate(self.rows) if r['id'] == keep), 0)
        self.list.reset()
        self.list.addItems([self._item(r) for r in self.rows])
        self.list.selectItem(position)
        self.setFocusId(LIST)

    def refresh(self, index):
        """The values again; the whole list when a change shows or hides rows."""
        rows = self._rows()
        if [r['id'] for r in rows] != [r['id'] for r in self.rows]:
            keep = self.rows[index]['id'] if 0 <= index < len(self.rows) else ''
            self.build(keep=keep)
            return
        self.rows = rows
        for i, row in enumerate(rows):
            li = self.list.getListItem(i)
            li.setLabel2(row.get('value') or '')
            self._swatches(li, row)
            li.setProperty('pct', str(row.get('pct') or ''))
            if row.get('pct'):
                try:
                    li.getVideoInfoTag().setResumePoint(float(row['pct']), 100.0)
                except Exception:
                    pass

    # setup
    def onInit(self):
        self.list = self.getControl(LIST)
        self.setProperty('sq.title', _t('مظهر الترجمة', 'Subtitle look'))
        self.build()

    # changes
    def _height(self, step):
        try:
            current = float(_get(POS_KEY))
        except (TypeError, ValueError):
            current = POS_DEFAULT
        if step == 0:
            target = POS_DEFAULT
        else:
            # snap to the 1 % grid, then step (Kodi's default 4.95 -> 5 / 4)
            base = round(current) if abs(current - round(current)) > 0.01 else current
            if step > 0:
                target = base + POS_STEP if base <= current + 0.01 else base
            else:
                target = base - POS_STEP if base >= current - 0.01 else base
        target = round(max(POS_MIN, min(POS_MAX, float(target))), 2)
        if _get('subtitles.align') != ALIGN_BOTTOM:
            _set('subtitles.align', ALIGN_BOTTOM)
        _set(POS_KEY, float(target))

    def _shade(self, step):
        value = str(_get('subtitles.colorpick') or 'FFFFFFFF').upper()
        base = base_of(value)
        found = shades(base)
        at = found.index(value) if value in found else 3
        to = max(0, min(len(found) - 1, at + (1 if step > 0 else -1)))
        xbmcgui.Window(10000).setProperty(BASE_PROP, base)
        if to != at or value not in found:
            _set('subtitles.colorpick', found[to])

    def _preset(self, step):
        home = xbmcgui.Window(10000)
        names = [n for n, _l, _v, _f in PRESETS]
        current = home.getProperty(PRESET_PROP)
        at = names.index(current) if current in names else -1
        name, _label, values, fonts = PRESETS[(at + step) % len(PRESETS)]
        available = [v for v, _l in _font_options(_all().get('subtitles.fontname'))]
        for wanted in fonts:
            found = next((f for f in available
                          if f.lower().replace(' ', '') == wanted.lower().replace(' ', '')), None)
            if found:
                _set('subtitles.fontname', found)
                break
        for key, value in values.items():
            _set(key, value)
        home.setProperty(PRESET_PROP, name)

    def _step(self, key, step):
        row = next((r for r in ROWS if r[0] == key), None)
        if row is None:
            return
        _key, _ar, _en, kind, extra = row
        direction = 1 if step > 0 else -1
        if kind == 'options':
            values = [v for v, _l in _font_options(_all().get(key))]
            if not values:
                return
            current = _get(key)
            index = values.index(current) if current in values else -1
            value = values[(index + direction) % len(values)]
        elif kind in ('int', 'pct'):
            low, high, size = extra
            if key == 'subtitles.fontsize':
                setting = _all().get(key) or {}
                low = int(setting.get('minimum', low))
                high = int(setting.get('maximum', high))
            try:
                current = int(_get(key))
            except Exception:
                current = low
            value = max(low, min(high, current + direction * size))
            if value == current:
                return
        elif kind == 'choice':
            values = [v for v, _a, _e in extra]
            current = _get(key)
            index = values.index(current) if current in values else -1
            value = values[(index + direction) % len(values)]
        else:
            values = [v for v, _a, _e in extra]
            upper = [v.upper() for v in values]
            current = str(_get(key) or '').upper()
            if key == 'subtitles.colorpick' and current not in upper:
                current = base_of(current)          # a shade moves on from its colour
            index = upper.index(current) if current in upper else -1
            value = values[(index + direction) % len(values)]
            if key == 'subtitles.colorpick':
                xbmcgui.Window(10000).setProperty(BASE_PROP, value)
        _set(key, value)

    def change(self, step):
        index = self.list.getSelectedPosition()
        if not 0 <= index < len(self.rows):
            return
        row = self.rows[index]
        if not row.get('adjust'):
            return
        key = row['id']
        if key == 'show':
            xbmc.Player().showSubtitles(not _subs_on())
        elif key == 'delay':
            _act('SubtitleDelayPlus' if step > 0 else 'SubtitleDelayMinus')
        elif key == 'height':
            self._height(step)
        elif key == 'shade':
            self._shade(step)
        elif key == 'preset':
            self._preset(step)
            xbmc.sleep(80)
            self.build(keep='preset')
            return
        else:
            self._step(key, step)
        xbmc.sleep(80)          # Kodi's own changes (show, delay) land first
        self.refresh(index)

    # input
    def onAction(self, action):
        aid = action.getId()
        if aid in CLOSE:
            self.close()
            return
        if self.getFocusId() != LIST:
            if aid in (LEFT, RIGHT, 3, 4):
                self.setFocusId(LIST)
            return
        if aid in (LEFT, RIGHT):
            self.change(-1 if aid == LEFT else 1)

    def onClick(self, control_id):
        if control_id != LIST:
            return
        index = self.list.getSelectedPosition()
        row = self.rows[index] if 0 <= index < len(self.rows) else {}
        rid = row.get('id')
        if rid == 'sync':
            target = _sync_target()
            self.close()
            if target:
                xbmc.executebuiltin(target)
        elif rid == 'kodi':
            self.close()
            xbmc.executebuiltin('ActivateWindow(osdsubtitlesettings)')
        elif rid == 'height':
            self._height(0)                     # OK: Kodi's default height
            self.refresh(index)
        elif row.get('adjust'):
            self.change(1)


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
