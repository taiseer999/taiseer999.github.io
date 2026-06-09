# -*- coding: utf-8 -*-
import os, sys, io, zipfile, gzip, re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import requests
from urllib.parse import parse_qs, quote_plus, unquote_plus

import urllib3
urllib3.disable_warnings()

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "DexSubtitles/1.0 (Kodi)"})

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
PARAMS = sys.argv[2] if len(sys.argv) > 2 else ''

BASE_TEMP = xbmcvfs.translatePath("special://temp/")
TEMP_DIR  = os.path.join(BASE_TEMP, "dexworld_subs")
if not xbmcvfs.exists(TEMP_DIR):
    xbmcvfs.mkdirs(TEMP_DIR)

LANG_INFO = {
    'ar': ('ar', 'Arabic'),
    'ara': ('ar', 'Arabic'),
    'en': ('en', 'English'),
    'eng': ('en', 'English'),
    'fr': ('fr', 'French'),
    'fre': ('fr', 'French'),
    'fra': ('fr', 'French'),
    'es': ('es', 'Spanish'),
    'spa': ('es', 'Spanish'),
}

TEXTISH_EXTS = ('.srt', '.ass', '.ssa', '.vtt', '.sub', '.txt')


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ('1', 'true', 'yes', 'on', 'ai')


def is_ai_sub(sub):
    return _to_bool(sub.get('is_ai', sub.get('ai', False))) or str(sub.get('kind', '')).strip().lower() == 'ai'


def notify(msg):
    xbmcgui.Dialog().notification('DexSubtitles', msg, xbmcgui.NOTIFICATION_INFO, 2500)


def get_param(name, default=''):
    try:
        qs = PARAMS[1:] if PARAMS.startswith('?') else PARAMS
        params = parse_qs(qs)
        return unquote_plus(params.get(name, [default])[0] or default)
    except Exception:
        return default


def provider_color(provider):
    p = (provider or "").lower()
    if "opensubtitles" in p: return "lime"
    if "subdl" in p: return "deepskyblue"
    if "wyzie" in p: return "gold"
    if "subsource" in p: return "magenta"
    if "pro" in p: return "violet"
    return "orange"


def safe_clean_name(name):
    """Clean a subtitle display name without losing the actual content.

    Strips emojis (Kodi shows them broken/empty), replaces [ ] with ( ),
    and removes trailing language words only.
    """
    if not name:
        return "Subtitle"
    s = str(name).strip()

    # 1. Strip emojis (Kodi cant render most Unicode symbols cleanly)
    s = re.sub("[🌀-🧿☀-⛿✀-➿🩰-🫿😀-🙏]", "", s)

    # 2. Strip trailing language words only
    s = re.sub(
        r"\s*[-—–|·•]\s*(arabic|english|french|spanish)\s*$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()

    # 3. Protect against Kodi BBcode interpretation
    s = s.replace("[", "(").replace("]", ")")

    # 4. Cleanup whitespace
    s = re.sub(r"\s+", " ", s).strip(" -|_·•")
    return s if s else "Subtitle"


def _read_dexhub_ids():
    """Read content IDs from DexHub's bridge properties on Window(10000).

    DexHub writes these right before calling player.play() / setResolvedUrl()
    so they are available even before VideoPlayer.* infolabels are populated.
    Returns a dict with imdb_id, tmdb_id, tvdb_id, season, episode, mediatype.
    """
    try:
        home = xbmcgui.Window(10000)
        return {
            'imdb_id':   home.getProperty('dexhub.sub.imdb_id') or '',
            'tmdb_id':   home.getProperty('dexhub.sub.tmdb_id') or '',
            'tvdb_id':   home.getProperty('dexhub.sub.tvdb_id') or '',
            'season':    home.getProperty('dexhub.sub.season') or '',
            'episode':   home.getProperty('dexhub.sub.episode') or '',
            'mediatype': home.getProperty('dexhub.sub.mediatype') or '',
        }
    except Exception:
        return {}


def build_req_url(server_url, api_key):
    # ── 1. Try VideoPlayer infolabels (populated once player starts) ─────
    vp_imdb   = xbmc.getInfoLabel('VideoPlayer.IMDBNumber') or ''
    vp_season  = xbmc.getInfoLabel('VideoPlayer.Season') or ''
    vp_episode = xbmc.getInfoLabel('VideoPlayer.Episode') or ''

    # ── 2. Fallback to DexHub bridge properties ──────────────────────────
    dex = _read_dexhub_ids()
    imdb_id  = vp_imdb or dex.get('imdb_id') or ''
    tmdb_id  = dex.get('tmdb_id') or ''
    tvdb_id  = dex.get('tvdb_id') or ''
    season   = vp_season or dex.get('season') or ''
    episode  = vp_episode or dex.get('episode') or ''
    mediatype = dex.get('mediatype') or ('episode' if (season and episode) else 'movie')

    is_episode = (
        season and episode
        and str(season) not in ('', '-1', '0')
        and str(episode) not in ('', '-1', '0')
    )

    # ── 3. Prefer imdb_id; fall back to tmdb_id for the Stremio path ─────
    if imdb_id and imdb_id.startswith('tt'):
        content_id = imdb_id
    elif tmdb_id:
        # Stremio Cinemeta uses tt-IDs. Many subtitle addons support
        # tmdb:NNN format as well; use it and let the server resolve.
        content_id = 'tmdb:%s' % tmdb_id
    elif tvdb_id:
        content_id = 'tvdb:%s' % tvdb_id
    else:
        xbmc.log('[DexSubtitles] build_req_url: no usable ID found', xbmc.LOGWARNING)
        return None

    xbmc.log(
        '[DexSubtitles] build_req_url id=%s season=%s episode=%s' % (content_id, season, episode),
        xbmc.LOGDEBUG,
    )

    if is_episode:
        return '%s/subtitles/stremio/%s/subtitles/series/%s:%s:%s.json' % (
            server_url, api_key, content_id, season, episode)
    return '%s/subtitles/stremio/%s/subtitles/movie/%s.json' % (
        server_url, api_key, content_id)


def fetch_subs_json(req_url, timeout=20, retries=1):
    last_err = None
    for _ in range(retries + 1):
        try:
            resp = SESSION.get(req_url, timeout=timeout, verify=False)
            if not resp.ok:
                return []
            data = resp.json() or {}
            return data.get('subtitles', []) or []
        except Exception as e:
            last_err = e
    xbmc.log(f"[DexSubtitles] fetch_subs_json exception: {last_err} | url={req_url}", xbmc.LOGERROR)
    return []


def _search_with_progress(req_url, title, attempts, ai_only=False):
    dlg = None
    try:
        dlg = xbmcgui.DialogProgressBG()
        dlg.create('DexSubtitles', title)
    except Exception:
        dlg = None

    last = []
    seen = set()
    total = len(attempts)

    for idx, (timeout_val, retries_val) in enumerate(attempts, 1):
        pct = int((idx / float(total)) * 100)
        try:
            if dlg:
                dlg.update(pct, 'جاري البحث...', f'Timeout={timeout_val}s / Retry={retries_val}')
        except Exception:
            pass

        subs = fetch_subs_json(req_url, timeout=timeout_val, retries=retries_val)
        if ai_only:
            subs = [s for s in subs if is_ai_sub(s)]

        merged = []
        for s in subs:
            key = (
                str(s.get('provider_name') or s.get('provider') or '').strip().lower(),
                str(s.get('display_name') or s.get('name') or '').strip().lower(),
                str(s.get('lang') or s.get('lang_code') or s.get('flag') or '').strip().lower(),
                '1' if is_ai_sub(s) else '0',
                str(s.get('status') or '').strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(s)

        if merged:
            last = merged
            break

        xbmc.sleep(350)

    try:
        if dlg:
            dlg.close()
    except Exception:
        pass
    return last


def resolve_lang(sub):
    candidates = [sub.get('flag'), sub.get('lang_code'), sub.get('lang')]
    for raw in candidates:
        val = str(raw or '').strip().lower()
        if not val:
            continue
        if val in LANG_INFO:
            return LANG_INFO[val]
        if 'arab' in val:
            return LANG_INFO['ar']
        if 'english' in val:
            return LANG_INFO['en']
        if 'french' in val or 'fran' in val:
            return LANG_INFO['fr']
        if 'spanish' in val or 'espan' in val:
            return LANG_INFO['es']
    return LANG_INFO['ar']


def _subtitle_sort_key(sub):
    provider = str(sub.get('provider_name') or sub.get('provider') or '').lower()
    name = str(sub.get('display_name') or sub.get('name') or '').lower()
    is_ai = is_ai_sub(sub)
    status = str(sub.get('status') or ('pending' if is_ai else 'ready')).lower()

    group = 9
    if 'uploaded' in provider:
        group = 0
    elif not is_ai:
        group = 1
    elif is_ai and status == 'ready':
        group = 2
    elif is_ai:
        group = 3

    score = 0
    if 'opensubtitles' in provider:
        score = 40
    elif 'subdl' in provider:
        score = 30
    elif 'wyzie' in provider:
        score = 20
    elif 'subsource' in provider:
        score = 10

    return (group, -score, name)


def build_plugin_url(url, base_name, is_ai=False, status='ready', lang='ar', provider='DexSubtitles'):
    qs = [
        'action=download',
        f'url={quote_plus(url)}',
        f'name={quote_plus(base_name)}',
        f'is_ai={quote_plus("1" if is_ai else "0")}',
        f'status={quote_plus(status or "ready")}',
        f'lang={quote_plus(lang or "ar")}',
        f'provider={quote_plus(provider or "DexSubtitles")}',
    ]
    return f"plugin://{ADDON_ID}/?{'&'.join(qs)}"


def add_sub_item(sub):
    url = str(sub.get('url') or '')
    if not url:
        return

    name     = str(sub.get('display_name') or sub.get('name') or 'Subtitle')
    provider = str(sub.get('provider_name') or sub.get('provider') or 'DexSubtitles')
    is_ai    = is_ai_sub(sub)
    ai_p     = str(sub.get('ai_provider') or '').strip()
    status   = str(sub.get('status') or ('pending' if is_ai else 'ready')).strip().lower()
    if status not in ('ready', 'pending', 'failed'):
        status = 'pending' if is_ai else 'ready'
    lang2, lang_label = resolve_lang(sub)

    # كل النصوص اللي ستدخل في label2 لازم تمر عبر safe_clean_name
    # هذا يحوّل [ ] الغير متوازنة إلى ( ) فيمنع Kodi من تفسيرها كـ BBcode
    # فاسد ويقطع العرض. النصوص الـ BBcode الحقيقية (مثل [COLOR yellow])
    # تُكتب بشكل صريح من قبلنا فهي متوازنة دائماً.
    base_name = safe_clean_name(name)
    safe_provider = safe_clean_name(provider)
    safe_ai_p = safe_clean_name(ai_p) if ai_p else ''

    pcol = provider_color(safe_provider)
    provider_colored = f"[COLOR {pcol}]({safe_provider})[/COLOR]"
    ai_name = safe_ai_p.upper() if safe_ai_p else 'AI'
    ai_tag = f" [COLOR yellow][AI:{ai_name}][/COLOR]" if is_ai else ""
    status_tag = " [COLOR orange][جاري التوليد][/COLOR]" if (is_ai and status != 'ready') else ""

    li = xbmcgui.ListItem(label=lang_label, label2=f"{base_name} {provider_colored}{ai_tag}{status_tag}")
    li.setProperty('language', lang2)
    li.setProperty('sync', 'true')
    li.setProperty('hearing_imp', 'false')
    li.setProperty('forced', 'false')
    li.setProperty('IsPlayable', 'true')
    try:
        li.setArt({'thumb': lang2, 'icon': lang2})
    except Exception:
        pass

    plugin_url = build_plugin_url(url, base_name, is_ai=is_ai, status=status, lang=lang2, provider=provider)
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url, li, False)


def add_ai_button(req_url):
    # نستخدم BBcode متوازن لتلوين الزر (Kodi يفسّره في القوائم)
    # كل الأقواس مغلقة بشكل صحيح فلن تسبب اقتطاع
    li = xbmcgui.ListItem(label="AI", label2="[B][COLOR yellow]🤖 طلب ترجمة AI[/COLOR][/B]")
    li.setProperty('language', 'ar')
    li.setProperty('IsPlayable', 'true')
    try:
        li.setArt({'thumb': 'ar', 'icon': 'ar'})
    except Exception:
        pass

    ai_req = req_url + ("&" if "?" in req_url else "?") + "ai=1"
    btn_url = f"plugin://{ADDON_ID}/?action=search_ai&req={quote_plus(ai_req)}"
    xbmcplugin.addDirectoryItem(HANDLE, btn_url, li, False)


def _get_timeout_setting(setting_id, default_val):
    try:
        raw = (ADDON.getSetting(setting_id) or '').strip()
        val = int(raw or str(default_val))
        return max(5, min(120, val))
    except Exception:
        return default_val


def search_subtitles_native():
    api_key = (ADDON.getSetting('api_key') or '').strip()
    server_url = (ADDON.getSetting('server_url') or '').strip().rstrip('/')

    if not api_key or not server_url:
        notify('اضبط server_url و api_key')
        return

    req_url = build_req_url(server_url, api_key)
    if not req_url:
        notify('لم يتم التعرف على الفيديو')
        return

    search_timeout = _get_timeout_setting('search_timeout', 18)
    attempts = [
        (max(10, search_timeout - 8), 0),
        (max(12, search_timeout - 4), 1),
        (search_timeout, 1),
        (search_timeout + 2, 2),
    ]
    subs = _search_with_progress(req_url, 'جاري البحث عن الترجمات...', attempts, ai_only=False)

    if not subs:
        notify('لا توجد نتائج (تحقق من السيرفر/الاتصال)')
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    native = sorted([s for s in subs if not is_ai_sub(s)], key=_subtitle_sort_key)
    ai     = sorted([s for s in subs if     is_ai_sub(s)], key=_subtitle_sort_key)

    xbmcplugin.setContent(HANDLE, 'files')

    for s in native[:60]:
        add_sub_item(s)

    for s in ai[:30]:
        add_sub_item(s)

    add_ai_button(req_url)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def search_subtitles_ai_only():
    req_url = get_param('req', '')
    if not req_url:
        notify('طلب AI غير صحيح')
        return

    ai_search_timeout = _get_timeout_setting('ai_search_timeout', 25)
    attempts = [
        (max(15, ai_search_timeout - 10), 1),
        (max(18, ai_search_timeout - 5), 1),
        (ai_search_timeout, 2),
    ]
    ai = _search_with_progress(req_url, 'جاري جلب ترجمات AI...', attempts, ai_only=True)

    if not ai:
        notify('لا توجد نتائج AI (Timeout/سيرفر)')
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    ai = sorted(ai, key=_subtitle_sort_key)

    xbmcplugin.setContent(HANDLE, 'files')

    for s in ai[:40]:
        add_sub_item(s)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def _guess_ext(url, content_type):
    u = (url or '').lower()
    if u.endswith('.ass'): return '.ass'
    if u.endswith('.ssa'): return '.ssa'
    if u.endswith('.vtt'): return '.vtt'
    if u.endswith('.srt'): return '.srt'
    if content_type:
        ct = content_type.lower()
        if 'text/vtt' in ct: return '.vtt'
        if 'application/x-subrip' in ct or 'text/plain' in ct: return '.srt'
    return '.srt'


def _safe_filename(name):
    return re.sub(r'[\/:*?"<>|]+', '_', name).strip() or 'Subtitle'


def _write_bytes(path, content):
    f = xbmcvfs.File(path, 'wb')
    f.write(content)
    f.close()


def _make_status_srt(lines):
    text = '\n'.join([str(x) for x in lines if x is not None])
    return f"1\n00:00:00,000 --> 00:01:00,000\n{text}\n".encode('utf-8')


def _write_status_subtitle(base_name, suffix, lines):
    safe = _safe_filename(base_name)
    out_path = os.path.join(TEMP_DIR, f"{safe}_{suffix}.srt")
    _write_bytes(out_path, _make_status_srt(lines))
    return [out_path]


def _looks_like_html(content):
    head = content[:512].lstrip().lower()
    return head.startswith(b'<!doctype html') or head.startswith(b'<html')


def _looks_like_subtitle_text(content):
    try:
        sample = content[:1500].decode('utf-8', errors='ignore')
    except Exception:
        return False
    return ('-->' in sample) or ('[🤖 DexSubtitles AI]' in sample) or ('يتم توليد الترجمة' in sample)


def _ai_pending_files(base_name, provider='DexSubtitles'):
    return _write_status_subtitle(base_name, 'ai_pending', [
        '[🤖 DexSubtitles AI]',
        '⏳ يتم توليد الترجمة الذكية الآن...',
        '',
        'أعد البحث بعد قليل ثم اختر هذه الترجمة مرة أخرى.',
        f'المصدر: {provider}',
    ])


def _ai_failed_files(base_name, provider='DexSubtitles'):
    return _write_status_subtitle(base_name, 'ai_failed', [
        '[🤖 DexSubtitles AI]',
        '⚠️ تعذر إكمال الترجمة الذكية حالياً.',
        '',
        'اشحن الرصيد أو عدّل المفتاح ثم أعد البحث؛ سيُعاد طلب الترجمة من جديد.',
        f'المصدر: {provider}',
    ])


def download_subtitle():
    url = get_param('url', '')
    base_name = get_param('name', 'Subtitle')
    is_ai = _to_bool(get_param('is_ai', '0')) or ('[AI:' in base_name) or ('🤖' in base_name)
    status = (get_param('status', 'ready') or 'ready').lower()
    if status not in ('ready', 'pending', 'failed'):
        status = 'pending' if is_ai else 'ready'
    provider = get_param('provider', 'DexSubtitles')

    if not url:
        notify('رابط التحميل فارغ')
        return _ai_pending_files(base_name, provider) if is_ai else []

    try:
        notify('تحميل...')
        r = SESSION.get(url, timeout=240, verify=False, allow_redirects=True, stream=False)
        if r.status_code != 200:
            xbmc.log(f"[DexSubtitles] Download HTTP {r.status_code} URL={url}", xbmc.LOGERROR)
            if is_ai:
                notify('الترجمة الذكية لم تجهز بعد...')
                return _ai_pending_files(base_name, provider) if status != 'ready' else _ai_failed_files(base_name, provider)
            notify(f'فشل التحميل: {r.status_code}')
            return []

        content = r.content or b''
        if not content:
            xbmc.log(f"[DexSubtitles] Download empty content URL={url}", xbmc.LOGERROR)
            if is_ai:
                notify('الترجمة الذكية لم تجهز بعد...')
                return _ai_pending_files(base_name, provider) if status != 'ready' else _ai_failed_files(base_name, provider)
            notify('فشل: ملف فارغ')
            return []

        ext = _guess_ext(url, r.headers.get('Content-Type'))
        safe = _safe_filename(base_name)
        out_path = os.path.join(TEMP_DIR, f"{safe}{ext}")

        if content.startswith(b'PK'):
            z = zipfile.ZipFile(io.BytesIO(content))
            picked = None
            for fn in z.namelist():
                if fn.lower().endswith(TEXTISH_EXTS):
                    picked = fn
                    break
            if not picked:
                return _ai_failed_files(base_name, provider) if is_ai else []
            content = z.read(picked)
            ext = os.path.splitext(picked)[1].lower() or ext
            out_path = os.path.join(TEMP_DIR, f"{safe}{ext}")
        elif content[:2] == bytes([0x1f, 0x8b]):
            content = gzip.decompress(content)

        if is_ai and (_looks_like_html(content) or not _looks_like_subtitle_text(content)):
            notify('الترجمة الذكية لم تجهز بعد...')
            return _ai_pending_files(base_name, provider) if status != 'ready' else _ai_failed_files(base_name, provider)

        _write_bytes(out_path, content)
        return [out_path]

    except Exception as e:
        xbmc.log(f"[DexSubtitles] Download Exception: {e} URL={url}", xbmc.LOGERROR)
        if is_ai:
            notify('الترجمة الذكية لم تجهز بعد...')
            return _ai_pending_files(base_name, provider) if status != 'ready' else _ai_failed_files(base_name, provider)
        notify('فشل تحميل')
        return []


def main():
    if HANDLE < 0:
        return

    action = get_param('action', 'search')

    if action == 'download':
        files = download_subtitle()
        for p in files:
            li = xbmcgui.ListItem(label=p)
            xbmcplugin.addDirectoryItem(HANDLE, p, li, False)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
    elif action == 'search_ai':
        search_subtitles_ai_only()
    else:
        search_subtitles_native()


if __name__ == "__main__":
    main()
