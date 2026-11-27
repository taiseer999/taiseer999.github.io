# -*- coding: utf-8 -*-
"""Arabic RTL prayer BOARD with a live one-second countdown.

The window renders as a full mosque-style board. Text comes from window
properties; a background loop refreshes the countdown every second while the
big wall-clock uses Kodi's own live $INFO[System.Time].
"""
import threading
from datetime import datetime, timedelta

import xbmcgui

from resources.lib.core.prayer_engine import calculate, NAMES, as_datetime, name_of
from resources.lib.core import cities

ORDER = ('fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha')
ROW = ('fajr', 'dhuhr', 'asr', 'maghrib', 'isha')  # five cells on the board
_ACTION_CLOSE = (9, 10, 92, 247)  # back / escape / nav-back

_METHODS = ['UmmAlQura', 'MWL', 'Egypt', 'Karachi', 'ISNA']
_SCHOOLS = ['standard', 'hanafi']

_HIJRI_MONTHS = ['محرّم', 'صفر', 'ربيع الأول', 'ربيع الآخر', 'جمادى الأولى',
                 'جمادى الآخرة', 'رجب', 'شعبان', 'رمضان', 'شوّال',
                 'ذو القعدة', 'ذو الحجة']
_WEEKDAYS = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']

_VERSES = [
    'وَأَقِمِ الصَّلَاةَ لِذِكْرِي',
    'إِنَّ الصَّلَاةَ كَانَتْ عَلَى الْمُؤْمِنِينَ كِتَابًا مَّوْقُوتًا',
    'حَافِظُوا عَلَى الصَّلَوَاتِ وَالصَّلَاةِ الْوُسْطَى',
    'قَدْ أَفْلَحَ الْمُؤْمِنُونَ ۝ الَّذِينَ هُمْ فِي صَلَاتِهِمْ خَاشِعُونَ',
    'وَأْمُرْ أَهْلَكَ بِالصَّلَاةِ وَاصْطَبِرْ عَلَيْهَا',
    'الصلاة نور، وهي عمود الدين',
    'إنَّ أوَّلَ ما يُحاسَبُ به العبدُ يومَ القيامةِ الصَّلاةُ',
]


def _greg_to_hijri(y, m, d):
    """Tabular (arithmetic) Islamic calendar — accurate to about +/-1 day."""
    if m < 3:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524
    ld = jd - 1948440 + 10632
    n = (ld - 1) // 10631
    ld = ld - 10631 * n + 354
    j = ((10985 - ld) // 5316) * ((50 * ld) // 17719) + (ld // 5670) * ((43 * ld) // 15238)
    ld = ld - ((30 - j) // 15) * ((17719 * j) // 50) - (j // 16) * ((15238 * j) // 43) + 29
    hm = (24 * ld) // 709
    hd = ld - (709 * hm) // 24
    hy = 30 * n + j - 30
    return hy, hm, hd


def _s(addon, key, default=''):
    v = addon.getSetting(key)
    return v if v not in (None, '') else default


def day_times(addon, day):
    mi = int(_s(addon, 'calculation_method', '0') or 0)
    si = int(_s(addon, 'asr_school', '0') or 0)
    adj = {k: int(_s(addon, 'adjust_' + k, '0') or 0) for k in ORDER}
    la, lo, tz = cities.resolve(_s(addon, 'city', '0'), _s(addon, 'latitude', '24.7136'),
                                _s(addon, 'longitude', '46.6753'), _s(addon, 'utc_offset', '3'))
    return calculate(day, la, lo, tz,
                     _METHODS[max(0, min(mi, 4))], _SCHOOLS[max(0, min(si, 1))],
                     adj, float(_s(addon, 'isha_interval', '90')))


def next_prayer(addon, now=None):
    """Return (name_key, datetime, today_data) of the next upcoming prayer."""
    now = now or datetime.now()
    data = day_times(addon, now.date())
    for k in ROW:
        dt = as_datetime(now.date(), data.get(k))
        if dt and dt > now:
            return k, dt, data
    tomorrow = now.date() + timedelta(days=1)
    td = day_times(addon, tomorrow)
    for k in ROW:
        dt = as_datetime(tomorrow, td.get(k))
        if dt:
            return k, dt, data
    return None, None, data


_GREG_MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو',
                'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
TIMELINE = ('fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha')
TIMELINE_X = (1720, 1416, 1112, 808, 504, 200)   # node centres, right to left (dialog.xml)
BAR_RIGHT, BAR_W = 72 + 6 * 112 + 2 * 46, 6 * 112 + 2 * 46   # countdown bar (dialog.xml)
FILL_BAR, FILL_LINE = 2001, 2002


def _h12(dt):
    return dt.strftime('%I:%M'), ('ص' if dt.hour < 12 else 'م')


def _chars(text):
    return ['colon' if c == ':' else c for c in text]


def _period(data, day, now):
    """Which sky to show: the part of the day we are in."""
    t = {k: as_datetime(day, data.get(k)) for k in ORDER}
    if t['fajr'] and now < t['fajr']:
        return 'night'
    if t['sunrise'] and now < t['sunrise']:
        return 'dawn'
    if t['asr'] and now < t['asr']:
        return 'day'
    if t['maghrib'] and now < t['maghrib']:
        return 'afternoon'
    if t['isha'] and now < t['isha']:
        return 'sunset'
    return 'night'


class PrayerDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(PrayerDialog, self).__init__(*args, **kwargs)
        self.addon = kwargs.get('addon')
        self._stop = threading.Event()
        self._thread = None
        self._day = None
        self._week = False

    def onInit(self):
        self._fill_static()
        self._tick()
        self._thread = threading.Thread(target=self._loop)
        self._thread.daemon = True
        self._thread.start()

    def _fill_static(self):
        now = datetime.now()
        self._day = now.date()
        self._data = day_times(self.addon, now.date())
        data = self._data
        city = cities.name_of(_s(self.addon, 'city', '0'), _s(self.addon, 'city_name', 'الرياض'))
        try:
            hadj = int(_s(self.addon, 'hijri_adjust', '0') or 0)
        except ValueError:
            hadj = 0
        hdate = now.date() + timedelta(days=hadj)
        hy, hm, hd = _greg_to_hijri(hdate.year, hdate.month, hdate.day)
        self.setProperty('NajdPrayer.City', city)
        self.setProperty('NajdPrayer.HijriDate',
                         '%s  %d %s %d هـ' % (_WEEKDAYS[now.weekday()], hd,
                                              _HIJRI_MONTHS[(hm - 1) % 12], hy))
        self.setProperty('NajdPrayer.GregDate', '%d %s %d م' % (now.day, _GREG_MONTHS[now.month - 1], now.year))
        self.setProperty('NajdPrayer.Verse', _VERSES[now.timetuple().tm_yday % len(_VERSES)])
        for k in TIMELINE:
            dt = as_datetime(now.date(), data.get(k))
            self.setProperty('NajdPrayer.name_%s' % k, name_of(k, now))
            self.setProperty('NajdPrayer.time_%s' % k, '%s %s' % _h12(dt) if dt else '--:--')
        self._fill_week()

    def _fill_week(self):
        today = datetime.now().date()
        for r in range(7):
            d = today + timedelta(days=r)
            data = day_times(self.addon, d)
            label = 'اليوم' if r == 0 else ('غداً' if r == 1 else _WEEKDAYS[d.weekday()])
            self.setProperty('NajdPrayer.w%d_day' % r, '%s  %d/%d' % (label, d.day, d.month))
            self.setProperty('NajdPrayer.w%d_today' % r, 'true' if r == 0 else '')
            for k in TIMELINE:
                dt = as_datetime(d, data.get(k))
                v = '%s %s' % _h12(dt) if dt else '--:--'
                self.setProperty('NajdPrayer.w%d_%s' % (r, k), v)

    def _tick(self):
        now = datetime.now()
        if now.date() != self._day:
            self._fill_static()
        data = self._data
        key, dt, _d = next_prayer(self.addon, now)
        self.setProperty('NajdPrayer.Period', _period(data, now.date(), now))
        if not (key and dt):
            return
        friday_noon = key == 'dhuhr' and dt.weekday() == 4
        self.setProperty('NajdPrayer.NextKey', 'jumuah' if friday_noon else key)
        self.setProperty('NajdPrayer.HeroLabel',
                         'الصلاة القادمة' + ('  •  غداً' if dt.date() != now.date() else ''))
        hhmm, ampm = _h12(dt)
        for i, c in enumerate(_chars(hhmm)):
            self.setProperty('NajdPrayer.t%d' % i, c)
        self.setProperty('NajdPrayer.AmPm', ampm)

        total = max(0, int((dt - now).total_seconds()))
        h, rem = divmod(total, 3600)
        m, sec = divmod(rem, 60)
        for i, c in enumerate(_chars('%02d:%02d:%02d' % (h, m, sec))):
            self.setProperty('NajdPrayer.c%d' % i, c)
        self.setProperty('NajdPrayer.CountLabel', 'يُرفع أذان %s بعد' % name_of(key, dt))

        # previous prayer (for the bar under the countdown)
        prev = None
        for d in (now.date(), now.date() - timedelta(days=1)):
            dd = data if d == now.date() else day_times(self.addon, d)
            for k in reversed(ROW):
                t = as_datetime(d, dd.get(k))
                if t and t <= now:
                    prev = (k, t)
                    break
            if prev:
                break
        frac = 0.0
        if prev:
            span = (dt - prev[1]).total_seconds()
            frac = min(1.0, max(0.0, (now - prev[1]).total_seconds() / span)) if span > 0 else 0.0
            ago = int((now - prev[1]).total_seconds() // 60)
            self.setProperty('NajdPrayer.SinceLabel',
                             'منذ أذان %s  %d:%02d' % (name_of(prev[0], prev[1]), ago // 60, ago % 60))
        self._set_fill(FILL_BAR, BAR_RIGHT, int(BAR_W * frac))

        # timeline states and fill
        times = [as_datetime(now.date(), data.get(k)) for k in TIMELINE]
        nxt = 'sunrise' if (times[1] and times[0] and times[0] <= now < times[1]) else key
        for k, t in zip(TIMELINE, times):
            if k == nxt and (t is None or t > now):
                state = 'next'
            elif t and t <= now:
                state = 'past'
            else:
                state = 'future'
            self.setProperty('NajdPrayer.state_%s' % k, state)
        x = TIMELINE_X[0]
        for i in range(len(TIMELINE) - 1):
            a, b = times[i], times[i + 1]
            if not a or now < a:
                break
            if b and now < b:
                x = TIMELINE_X[i] - (TIMELINE_X[i] - TIMELINE_X[i + 1]) * (now - a).total_seconds() / (b - a).total_seconds()
                break
            x = TIMELINE_X[i + 1]
        self._set_fill(FILL_LINE, TIMELINE_X[0], int(TIMELINE_X[0] - x))
        if total == 0:
            self._fill_static()

    def _set_fill(self, cid, right, width):
        try:
            c = self.getControl(cid)
            c.setWidth(max(0, width))
            c.setPosition(right - max(0, width), c.getY())
        except Exception:
            pass

    def _loop(self):
        while not self._stop.wait(1.0):
            try:
                self._tick()
            except Exception:
                pass

    def onAction(self, action):
        if action.getId() in _ACTION_CLOSE:
            if self._week:
                self._toggle_week(False)
            else:
                self._close()

    def onClick(self, cid):
        if cid == 9001:
            self.addon.openSettings()
            self._fill_static()
            self._tick()
        elif cid == 9002:
            self._toggle_week(not self._week)
        elif cid == 9003:
            self._close()

    def _toggle_week(self, show):
        self._week = show
        self.setProperty('NajdPrayer.Week', 'true' if show else '')

    def _close(self):
        self._stop.set()
        self.close()


def open_dialog(addon, addon_path):
    dlg = PrayerDialog('dialog.xml', addon_path, 'Default', addon=addon)
    dlg.doModal()
    del dlg
