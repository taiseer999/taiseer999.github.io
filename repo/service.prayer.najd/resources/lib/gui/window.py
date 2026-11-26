# -*- coding: utf-8 -*-
"""Arabic RTL prayer BOARD with a live one-second countdown.

The window renders as a full mosque-style board. Text comes from window
properties; a background loop refreshes the countdown every second while the
big wall-clock uses Kodi's own live $INFO[System.Time].
"""
import threading
from datetime import datetime, timedelta

import xbmcgui

from resources.lib.core.prayer_engine import calculate, NAMES, as_datetime
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


class PrayerDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(PrayerDialog, self).__init__(*args, **kwargs)
        self.addon = kwargs.get('addon')
        self._stop = threading.Event()
        self._thread = None

    def onInit(self):
        self._fill_static()
        self._thread = threading.Thread(target=self._loop)
        self._thread.daemon = True
        self._thread.start()

    def _fill_static(self):
        now = datetime.now()
        data = day_times(self.addon, now.date())
        city = cities.name_of(_s(self.addon, 'city', '0'), _s(self.addon, 'city_name', 'الرياض'))
        try:
            hadj = int(_s(self.addon, 'hijri_adjust', '0') or 0)
        except ValueError:
            hadj = 0
        hdate = now.date() + timedelta(days=hadj)
        hy, hm, hd = _greg_to_hijri(hdate.year, hdate.month, hdate.day)
        self.setProperty('NajdPrayer.City', city)
        self.setProperty('NajdPrayer.HijriDate',
                         '%s %d %s %d هـ' % (_WEEKDAYS[now.weekday()], hd,
                                             _HIJRI_MONTHS[(hm - 1) % 12], hy))
        self.setProperty('NajdPrayer.GregDate', now.strftime('%Y / %m / %d'))
        self.setProperty('NajdPrayer.Sunrise', data.get('sunrise') or '--:--')
        self.setProperty('NajdPrayer.Sunset', data.get('maghrib') or '--:--')
        self.setProperty('NajdPrayer.Verse', _VERSES[now.timetuple().tm_yday % len(_VERSES)])
        for k in ROW:
            self.setProperty('NajdPrayer.%s_time' % k, data.get(k) or '--:--')

    def _loop(self):
        while not self._stop.is_set():
            now = datetime.now()
            key, dt, _d = next_prayer(self.addon, now)
            if key and dt:
                total = max(0, int((dt - now).total_seconds()))
                h, rem = divmod(total, 3600)
                m, sec = divmod(rem, 60)
                self.setProperty('NajdPrayer.Countdown', '%02d:%02d:%02d' % (h, m, sec))
                self.setProperty('NajdPrayer.NextLabel', 'المتبقّي لصلاة %s' % NAMES[key])
                self.setProperty('NajdPrayer.NextTime', 'وقتها %s' % dt.strftime('%H:%M'))
                for k in ROW:
                    self.setProperty('NajdPrayer.active_%s' % k,
                                     'true' if k == key else '')
                if total == 0:
                    self._fill_static()
            if self._stop.wait(1.0):
                break

    def onAction(self, action):
        if action.getId() in _ACTION_CLOSE:
            self._close()

    def onClick(self, cid):
        if cid == 9001:
            self.addon.openSettings()
            self._fill_static()
        elif cid == 9002:
            self._show_week()
        elif cid == 9003:
            self._close()

    def _show_week(self):
        today = datetime.now().date()
        rows = []
        for i in range(7):
            d = today + timedelta(days=i)
            data = day_times(self.addon, d)
            line = '  '.join('%s %s' % (NAMES[k], data.get(k) or '--:--') for k in ROW)
            rows.append(d.strftime('%a %Y-%m-%d') + '\n' + line)
        xbmcgui.Dialog().textviewer('مواقيت الأسبوع القادم', '\n\n'.join(rows))

    def _close(self):
        self._stop.set()
        self.close()


def open_dialog(addon, addon_path):
    dlg = PrayerDialog('dialog.xml', addon_path, 'Default', addon=addon)
    dlg.doModal()
    del dlg
