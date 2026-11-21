# -*- coding: utf-8 -*-
"""Quick live checks for each API key and for the audio tool."""
import subprocess
import sys

from .common import http, HttpError


def _err(e):
    if isinstance(e, HttpError):
        if e.code in (401, 403):
            return 'المفتاح غير صحيح'
        if e.code == 429:
            return 'المفتاح صحيح لكنه بلغ الحد، حاول لاحقاً'
        return 'خطأ %s' % e.code
    return 'تعذر الاتصال بالإنترنت'


def check_subdl(key):
    try:
        d = http('https://api.subdl.com/api/v1/subtitles',
                 params={'api_key': key, 'film_name': 'Inception', 'type': 'movie',
                         'languages': 'AR', 'subs_per_page': 1}, timeout=20)
        if d.get('status') is False and 'key' in str(d.get('error', '')).lower():
            return False, 'المفتاح غير صحيح'
        return True, 'يعمل ✓'
    except Exception as e:
        return False, _err(e)


def check_subsource(key):
    try:
        http('https://api.subsource.net/api/v1/movies/search',
             params={'searchType': 'text', 'q': 'inception'},
             headers={'X-API-Key': key, 'Accept': 'application/json'}, timeout=20)
        return True, 'يعمل ✓'
    except Exception as e:
        return False, _err(e)


def check_opensubtitles(key, user='', pwd=''):
    try:
        http('https://api.opensubtitles.com/api/v1/subtitles',
             params=[('imdb_id', '1375666'), ('languages', 'ar')],
             headers={'Api-Key': key, 'Accept': 'application/json'}, timeout=20)
    except Exception as e:
        return False, _err(e)
    if user and pwd:
        try:
            http('https://api.opensubtitles.com/api/v1/login',
                 json_body={'username': user, 'password': pwd},
                 headers={'Api-Key': key, 'Accept': 'application/json'}, timeout=20)
        except Exception as e:
            return False, 'المفتاح صحيح لكن اسم المستخدم أو كلمة المرور خطأ' \
                if isinstance(e, HttpError) and e.code in (400, 401) else _err(e)
    return True, 'يعمل ✓'


def check_gemini(key, model):
    from . import gemini
    try:
        if gemini.all_used_up():
            return False, 'المفتاح يعمل لكن الحد المجاني نفد اليوم، ويعود غداً'
        gemini.generate({'contents': [{'role': 'user', 'parts': [{'text': 'قل: تم'}]}]}, timeout=40)
        return True, 'يعمل ✓ (%s)' % gemini.models()[0]
    except gemini.QuotaExhausted:
        return False, 'المفتاح يعمل لكن الحد المجاني نفد اليوم، ويعود غداً'
    except HttpError as e:
        return False, _err(e)
    except Exception as e:
        return False, _err(e)


def check_ffmpeg(path):
    if not path:
        return False, 'غير موجودة'
    try:
        kw = {'creationflags': 0x08000000} if sys.platform.startswith('win') else {}
        p = subprocess.run([path, '-hide_banner', '-version'], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=20, **kw)
        return (p.returncode == 0), ('جاهزة ✓' if p.returncode == 0 else 'لم تعمل')
    except Exception as e:
        return False, 'لم تعمل: %s' % str(e)[:60]


def check_audio(configured=''):
    from . import audiosync, winaudio
    from .common import TEMP_DIR
    eng = audiosync.find_engine(configured)
    if eng and eng != audiosync.MF:
        return True, 'جاهزة ✓ (ffmpeg)'
    if eng == audiosync.MF:
        try:
            if winaudio.self_test(TEMP_DIR):
                return True, 'جاهزة ✓ (محرك الصوت في ويندوز)'
            return False, 'عمل محرك ويندوز لكن النتيجة خطأ'
        except Exception as e:
            return False, 'لم يعمل محرك ويندوز: %s' % str(e)[:80]
    err = audiosync._engine_cache.get('last_error', '')
    return False, 'غير متوفرة على هذا الجهاز' + (' (%s)' % err[:60] if err else '')
