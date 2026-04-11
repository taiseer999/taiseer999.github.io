# -*- coding: utf-8 -*-
import os, sys, time, io, zipfile, gzip, re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import requests
from urllib.parse import parse_qs, quote_plus, unquote_plus, urlparse

import urllib3
urllib3.disable_warnings()

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "DexWorldSubs/1.0 (Kodi)"})

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
PARAMS = sys.argv[2] if len(sys.argv) > 2 else ''

# ✅ استخدم special://temp بدل profile (أفضل مع كودي)
BASE_TEMP = xbmcvfs.translatePath("special://temp/")
TEMP_DIR  = os.path.join(BASE_TEMP, "dexworld_subs")
if not xbmcvfs.exists(TEMP_DIR):
    xbmcvfs.mkdirs(TEMP_DIR)

# ✅ إصلاح الرابط
FLAG_URL = "https://flagcdn.com/w40/sa.png"

def notify(msg):
    xbmcgui.Dialog().notification('DexWorld Subs', msg, xbmcgui.NOTIFICATION_INFO, 2500)

def get_param(name, default=''):
    try:
        qs = PARAMS[1:] if PARAMS.startswith('?') else PARAMS
        params = parse_qs(qs)
        return unquote_plus(params.get(name, [default])[0] or default)
    except:
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
    if not name:
        return "Subtitle"
    s = str(name)
    for j in ["Arabic", "arabic", "English", "english"]:
        s = s.replace(j, "")
    s = re.sub(r"\s+", " ", s).strip(" -|[](){}<>_")
    return s.strip() if s.strip() else "Subtitle"

def build_req_url(server_url, api_key):
    imdb_id = xbmc.getInfoLabel('VideoPlayer.IMDBNumber') or xbmc.getInfoLabel('ListItem.IMDBNumber')
    if not imdb_id:
        return None

    season = xbmc.getInfoLabel('VideoPlayer.Season')
    episode = xbmc.getInfoLabel('VideoPlayer.Episode')

    if season and episode and str(season) != '-1' and str(episode) != '-1':
        return f"{server_url}/subtitles/stremio/{api_key}/subtitles/series/{imdb_id}:{season}:{episode}.json"
    else:
        return f"{server_url}/subtitles/stremio/{api_key}/subtitles/movie/{imdb_id}.json"

# ✅ أسرع + retry بسيط
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
    xbmc.log(f"[DexWorld] fetch_subs_json exception: {last_err} | url={req_url}", xbmc.LOGERROR)
    return []

def add_sub_item(sub):
    url = str(sub.get('url') or '')
    if not url:
        return

    name     = str(sub.get('display_name') or sub.get('name') or 'Subtitle')
    provider = str(sub.get('provider_name') or sub.get('provider') or 'DexWorld')
    is_ai    = bool(sub.get('is_ai', sub.get('ai', False)))
    ai_p     = str(sub.get('ai_provider') or '').strip()

    base_name = safe_clean_name(name)
    pcol = provider_color(provider)
    provider_colored = f"[COLOR {pcol}]({provider})[/COLOR]"
    ai_tag = f" [COLOR yellow][AI:{(ai_p.upper() if ai_p else 'AI')}][/COLOR]" if is_ai else ""

    li = xbmcgui.ListItem(label="Arabic", label2=f"{base_name} {provider_colored}{ai_tag}")
    li.setArt({"thumb": FLAG_URL, "icon": FLAG_URL})
    li.setProperty('language', 'ar')
    li.setProperty('sync', 'true')
    li.setProperty('hearing_imp', 'false')
    li.setProperty('forced', 'false')
    li.setProperty('IsPlayable', 'true')

    plugin_url = f"plugin://{ADDON_ID}/?action=download&url={quote_plus(url)}&name={quote_plus(base_name)}"
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url, li, False)

def add_ai_button(req_url):
    li = xbmcgui.ListItem(label="Arabic", label2="[B][COLOR yellow]🤖 عرض ترجمات AI فقط[/COLOR][/B]")
    li.setArt({"thumb": FLAG_URL, "icon": FLAG_URL})
    li.setProperty('language', 'ar')
    li.setProperty('IsPlayable', 'true')

    # ✅ اطلب AI فقط من السيرفر
    ai_req = req_url + ("&" if "?" in req_url else "?") + "ai=1&bypass=1"
    btn_url = f"plugin://{ADDON_ID}/?action=search_ai&req={quote_plus(ai_req)}"
    xbmcplugin.addDirectoryItem(HANDLE, btn_url, li, False)

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

    notify('جاري البحث...')
    subs = fetch_subs_json(req_url, timeout=20, retries=1)
    if not subs:
        notify('لا توجد نتائج (تحقق من السيرفر/الاتصال)')
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    native = [s for s in subs if not bool(s.get('is_ai', s.get('ai', False)))]
    ai     = [s for s in subs if     bool(s.get('is_ai', s.get('ai', False)))]

    xbmcplugin.setContent(HANDLE, 'files')

    # ✅ عرض العربي أولاً بسرعة
    for s in native[:40]:
        add_sub_item(s)

     # ✅ زر AI يظهر دائمًا (يطلب ai=1 من السيرفر)
    add_ai_button(req_url)
    # إذا مافيه عربي أصلاً: نضغط AI مباشرة
    if not native and ai:
        notify('لا يوجد عربي — عرض AI...')
        for s in ai[:25]:
            add_sub_item(s)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def search_subtitles_ai_only():
    req_url = get_param('req', '')
    if not req_url:
        notify('طلب AI غير صحيح')
        return

    notify('جاري جلب ترجمات AI...')
    subs = fetch_subs_json(req_url, timeout=20, retries=1)
    if not subs:
        notify('لا توجد نتائج AI (Timeout/سيرفر)')
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    ai = [s for s in subs if bool(s.get('is_ai', s.get('ai', False)))]
    xbmcplugin.setContent(HANDLE, 'files')

    if not ai:
        notify('لا توجد ترجمات AI متاحة')
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    for s in ai[:25]:
        add_sub_item(s)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def _guess_ext(url, content_type):
    u = url.lower()
    if u.endswith(".ass"): return ".ass"
    if u.endswith(".vtt"): return ".vtt"
    if u.endswith(".srt"): return ".srt"
    if content_type:
        ct = content_type.lower()
        if "text/vtt" in ct: return ".vtt"
        if "application/x-subrip" in ct or "text/plain" in ct: return ".srt"
    return ".srt"

def download_subtitle():
    url = get_param('url', '')
    base_name = get_param('name', 'Subtitle')
    if not url:
        notify('رابط التحميل فارغ')
        return []

    try:
        notify('تحميل...')
        r = SESSION.get(url, timeout=240, verify=False, allow_redirects=True, stream=False)
        if r.status_code != 200:
            xbmc.log(f"[DexWorld] Download HTTP {r.status_code} URL={url}", xbmc.LOGERROR)
            notify(f'فشل التحميل: {r.status_code}')
            return []

        content = r.content or b""
        if not content:
            xbmc.log(f"[DexWorld] Download empty content URL={url}", xbmc.LOGERROR)
            notify('فشل: ملف فارغ')
            return []

        ext = _guess_ext(url, r.headers.get("Content-Type"))
        safe = re.sub(r'[\\/:*?"<>|]+', "_", base_name).strip() or "Subtitle"
        out_path = os.path.join(TEMP_DIR, f"{safe}{ext}")

        # ✅ فك ضغط zip/gzip
        if content.startswith(b'PK'):
            z = zipfile.ZipFile(io.BytesIO(content))
            picked = None
            for fn in z.namelist():
                if fn.lower().endswith(('.srt', '.ass', '.vtt')):
                    picked = fn; break
            if not picked:
                notify('ZIP بدون ترجمة')
                return []
            file_bytes = z.read(picked)
            ext = os.path.splitext(picked)[1].lower() or ext
            out_path = os.path.join(TEMP_DIR, f"{safe}{ext}")
            content = file_bytes

        elif content.startswith(b'\x1f\x8b'):
            content = gzip.decompress(content)

        # ✅ كتابة عبر xbmcvfs (أضمن على CoreELEC/Android)
        f = xbmcvfs.File(out_path, 'wb')
        f.write(content)
        f.close()

        return [out_path]

    except Exception as e:
        xbmc.log(f"[DexWorld] Download Exception: {e} URL={url}", xbmc.LOGERROR)
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