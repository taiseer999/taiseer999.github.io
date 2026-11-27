# -*- coding: utf-8 -*-
"""Offline solar prayer-time calculations. Times are local wall-clock values."""
import math
from datetime import datetime, date, timedelta

METHODS = {
    # Fajr angle; Isha is either an angle or minutes after Maghrib.
    'UmmAlQura': {'fajr': 18.5, 'isha_minutes': 90},
    'MWL': {'fajr': 18.0, 'isha': 17.0},
    'Egypt': {'fajr': 19.5, 'isha': 17.5},
    'Karachi': {'fajr': 18.0, 'isha': 18.0},
    'ISNA': {'fajr': 15.0, 'isha': 15.0},
}
NAMES = {'fajr':'الفجر','sunrise':'الشروق','dhuhr':'الظهر','asr':'العصر','maghrib':'المغرب','isha':'العشاء'}


def name_of(key, when=None):
    """Prayer name for display: on Friday the Dhuhr prayer is «الجمعة».
    when: the prayer's date or datetime (default: today)."""
    if key == 'dhuhr':
        import datetime as _dt
        day = when or _dt.date.today()
        if day.weekday() == 4:
            return 'الجمعة'
    return NAMES.get(key, key)

def _julian_day(y, m, d):
    if m <= 2: y -= 1; m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + b - 1524.5

def _sun(jd):
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t*(36000.76983 + t*0.0003032)) % 360
    m = 357.52911 + t*(35999.05029 - 0.0001537*t)
    e = 0.016708634 - t*(0.000042037 + 0.0000001267*t)
    mr = math.radians(m)
    c = (1.914602-t*(0.004817+0.000014*t))*math.sin(mr) + (0.019993-0.000101*t)*math.sin(2*mr) + 0.000289*math.sin(3*mr)
    true_long = l0 + c
    omega = 125.04 - 1934.136*t
    lam = true_long - 0.00569 - 0.00478*math.sin(math.radians(omega))
    eps0 = 23 + (26 + (21.448-t*(46.815+t*(0.00059-t*0.001813)))/60)/60
    eps = eps0 + 0.00256*math.cos(math.radians(omega))
    decl = math.degrees(math.asin(math.sin(math.radians(eps))*math.sin(math.radians(lam))))
    y = math.tan(math.radians(eps)/2)**2
    l0r = math.radians(l0)
    eq = 4*math.degrees(y*math.sin(2*l0r)-2*e*math.sin(mr)+4*e*y*math.sin(mr)*math.cos(2*l0r)-0.5*y*y*math.sin(4*l0r)-1.25*e*e*math.sin(2*mr))
    return decl, eq

def _hour_angle(lat, decl, altitude):
    # cos(H) = (sin(h)-sin(lat)sin(dec))/(cos(lat)cos(dec))
    la, de, al = map(math.radians, (lat, decl, altitude))
    den = math.cos(la)*math.cos(de)
    if abs(den) < 1e-12: return None
    c = (math.sin(al)-math.sin(la)*math.sin(de))/den
    if c < -1 or c > 1: return None
    return math.degrees(math.acos(c))

def _fmt(hours):
    if hours is None: return None
    minutes = int(round(hours*60)) % (24*60)
    return '%02d:%02d' % (minutes//60, minutes%60)

def _time_for_angle(noon, lat, decl, angle, morning):
    h = _hour_angle(lat, decl, -angle)
    if h is None: return None
    return noon + (-h/15.0 if morning else h/15.0)

def calculate(day, latitude, longitude, utc_offset, method='UmmAlQura', asr_school='standard', adjustments=None, isha_interval=90):
    """Calculate prayer times for a date and fixed UTC offset in hours."""
    if isinstance(day, datetime): day = day.date()
    if not isinstance(day, date): raise TypeError('day must be datetime.date')
    latitude=float(latitude); longitude=float(longitude); utc_offset=float(utc_offset)
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180: raise ValueError('Invalid coordinates')
    if not -14 <= utc_offset <= 14: raise ValueError('Invalid UTC offset')
    cfg=METHODS.get(method, METHODS['UmmAlQura'])
    jd=_julian_day(day.year,day.month,day.day)
    decl, eq=_sun(jd + 0.5 - longitude/360.0)
    # Solar noon in local clock hours.
    noon=12 + utc_offset - longitude/15.0 - eq/60.0
    sunrise_h=_time_for_angle(noon,latitude,decl,0.833,True)
    sunset_h=_time_for_angle(noon,latitude,decl,0.833,False)
    fajr_h=_time_for_angle(noon,latitude,decl,cfg['fajr'],True)
    if 'isha_minutes' in cfg:
        interval=float(isha_interval if method == 'UmmAlQura' else cfg['isha_minutes'])
        if not 30 <= interval <= 180: raise ValueError('Isha interval must be between 30 and 180 minutes')
        isha_h=(sunset_h + interval/60.0) if sunset_h is not None else None
    else:
        isha_h=_time_for_angle(noon,latitude,decl,cfg['isha'],False)
    # High latitude fallback: proportional night, preserving a finite result.
    night=(sunrise_h+24-sunset_h) if sunrise_h is not None and sunset_h is not None else None
    if night is not None:
        if fajr_h is None: fajr_h=(sunrise_h-night/2.0)
        if isha_h is None: isha_h=(sunset_h+night/2.0)
    # Asr shadow factor: standard=1, Hanafi=2.
    factor=2 if asr_school.lower() in ('hanafi','2') else 1
    angle=math.degrees(math.atan(1.0/(factor+math.tan(math.radians(abs(latitude-decl))))))
    asr_angle=_hour_angle(latitude,decl,angle)
    asr_h=noon+asr_angle/15.0 if asr_angle is not None else None
    vals={'fajr':fajr_h,'sunrise':sunrise_h,'dhuhr':noon+1.0/60.0,'asr':asr_h,'maghrib':sunset_h,'isha':isha_h}
    adj=adjustments or {}
    out={}
    for key,val in vals.items():
        if val is None: out[key]=None; continue
        val += float(adj.get(key,0))/60.0
        out[key]=_fmt(val)
    return out

def as_datetime(day, hhmm):
    if not hhmm: return None
    h,m=map(int,hhmm.split(':'))
    return datetime(day.year,day.month,day.day,h,m)
