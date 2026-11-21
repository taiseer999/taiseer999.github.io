# -*- coding: utf-8 -*-
"""Kodi subtitle module entry point: search / manualsearch / download."""
import json
import os
import sys
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.common import (ADDON, ADDON_NAME, JOBS_DIR, log, notify, setting, clean_temp,
                                  prune_cache, set_status)
from resources.lib import media, providers, pipeline

HANDLE = int(sys.argv[1])
PARAMS = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip('?')))

LANG_NAMES = {'ar': 'Arabic', 'en': 'English'}
KODI_TO_CODE = {'arabic': 'ar', 'english': 'en'}
PROVIDER_LABEL = {'subdl': 'SubDL', 'opensubtitles': 'OpenSub', 'subsource': 'SubSource'}


def wanted_langs():
    langs = ['ar']
    if setting('also_english', 'false') == 'true':
        langs.append('en')
    return langs


def no_keys():
    return not any(m.available() for m in providers.PROVIDERS.values())


def search(manual=None):
    if no_keys():
        if xbmcgui.Dialog().yesno(ADDON_NAME, 'لا يوجد أي مصدر للترجمة: لا مفاتيح ولا إضافات ترجمة أخرى مثبتة في كودي.\nهل تريد تشغيل معالج الإعداد الآن؟'):
            xbmc.executebuiltin('RunScript(%s,wizard)' % ADDON.getAddonInfo('id'))
        return
    video = media.current()
    if manual:
        g = media.guess_from_name(manual + '.mkv')
        video.update({'title': manual, 'tvshow': '', 'imdb': '', 'tmdb': '',
                      'show_imdb': '', 'show_tmdb': '', 'hash': None, 'is_episode': False})
        if g['season']:
            video.update({'tvshow': g['title'], 'season': g['season'],
                          'episode': g['episode'], 'is_episode': True})
        elif g['year']:
            video.update({'title': g['title'], 'year': g['year']})
    last = pipeline.last_for(video)
    if last and not manual:
        aid = ADDON.getAddonInfo('id')
        for label, url in (
                ('إعادة ضبط توقيت الترجمة الحالية', 'plugin://%s/?action=resync' % aid),):
            li = xbmcgui.ListItem(label='Arabic', label2='[COLOR gold]%s[/COLOR]' % label)
            li.setArt({'icon': '5', 'thumb': 'ar'})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    if not manual and setting('embedded_ai', 'true') != 'false' and pipeline.embedded_text_possible(video):
        li = xbmcgui.ListItem(label='Arabic',
                              label2='[COLOR gold]ترجم الترجمة المدمجة في الفيديو بالذكاء الاصطناعي[/COLOR]')
        li.setArt({'icon': '5', 'thumb': 'ar'})
        li.setProperty('sync', 'true')
        xbmcplugin.addDirectoryItem(HANDLE, 'plugin://%s/?action=embedded_ai' % ADDON.getAddonInfo('id'),
                                    li, isFolder=False)
    video['interactive'] = True
    results = providers.search_all(video, wanted_langs())
    if not results:
        notify('تعذر الاتصال بمواقع الترجمة، تأكد من اتصالك بالإنترنت' if providers.all_failed()
               else 'لم يتم العثور على ترجمة عربية لهذا العمل')
    for it in results[:80]:
        tag = it.get('source') or PROVIDER_LABEL.get(it['provider'], it['provider'])
        label2 = '[%s] %s' % (tag, it['release'] or '—')
        if it.get('ai'):
            label2 += ' (آلية)'
        if it.get('fit') == 'pack':
            label2 += ' (موسم كامل)'
        li = xbmcgui.ListItem(label=LANG_NAMES.get(it['lang'], it['lang']), label2=label2)
        rating = 5 if it['hash_match'] else int(round(min(1.0, it.get('match', 0) + 0.2) * 5))
        li.setArt({'icon': str(rating), 'thumb': it['lang']})
        li.setProperty('sync', 'true' if it['hash_match'] else 'false')
        li.setProperty('hearing_imp', 'true' if it['hi'] else 'false')
        payload = {k: it.get(k) for k in ('provider', 'id', 'lang', 'release', 'hash_match', 'hi', 'source')}
        url = 'plugin://%s/?action=download&item=%s' % (
            ADDON.getAddonInfo('id'), urllib.parse.quote(json.dumps(payload)))
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    if not manual:
        li = xbmcgui.ListItem(label='Arabic', label2='[COLOR gold]شرح سريع: كيفية استخدام ترجمة نجد[/COLOR]')
        li.setArt({'icon': '0', 'thumb': 'ar'})
        xbmcplugin.addDirectoryItem(HANDLE, 'plugin://%s/?action=guide' % ADDON.getAddonInfo('id'),
                                    li, isFolder=False)


def download():
    clean_temp()
    prune_cache()
    item = json.loads(urllib.parse.unquote(PARAMS['item']))
    video = media.current()
    set_status('جارٍ تجهيز الترجمة...')
    dlg = xbmcgui.DialogProgress()
    dlg.create(ADDON_NAME, 'جارٍ التحضير...')
    try:
        path, summary = pipeline.process(item, video,
                                         progress=lambda p, m: dlg.update(p, m))
    except Exception as e:
        dlg.close()
        log('download failed: %s' % e, xbmc.LOGERROR)
        msg = str(e)
        if msg == 'quota':
            msg = 'انتهى حد التنزيل اليومي في OpenSubtitles، جرّب مصدراً آخر'
        set_status('فشل تنزيل الترجمة', 'err')
        xbmcgui.Dialog().ok(ADDON_NAME, 'فشل تنزيل الترجمة:\n%s' % msg)
        return
    dlg.close()
    busy = bool(os.listdir(JOBS_DIR))
    set_status('الترجمة تعمل، وجارٍ ضبطها مع الصوت...' if busy else 'الترجمة تعمل ✓',
               'busy' if busy else 'ok')
    if summary:
        notify(' | '.join(summary), seconds=7)
    li = xbmcgui.ListItem(label=path)
    xbmcplugin.addDirectoryItem(HANDLE, path, li, isFolder=False)


def embedded_ai():
    clean_temp()
    video = media.current()
    set_status('جارٍ استخراج الترجمة المدمجة وترجمتها...')
    dlg = xbmcgui.DialogProgress()
    dlg.create(ADDON_NAME, 'جارٍ التحضير...')
    try:
        def pos():
            try:
                return xbmc.Player().getTime() * 1000
            except Exception:
                return 0
        path, summary = pipeline.embedded_translate(video, progress=lambda p, m: dlg.update(p, m),
                                                    abort=dlg.iscanceled, position=pos)
    except Exception as e:
        dlg.close()
        log('embedded_ai failed: %s' % e, xbmc.LOGERROR)
        set_status('فشل استخراج الترجمة المدمجة', 'err')
        if 'aborted' not in str(e):
            xbmcgui.Dialog().ok(ADDON_NAME, str(e))
        return
    dlg.close()
    set_status('الترجمة تعمل ✓', 'ok')
    notify(' | '.join(summary), seconds=7)
    li = xbmcgui.ListItem(label=path)
    xbmcplugin.addDirectoryItem(HANDLE, path, li, isFolder=False)


def resync():
    video = media.current()
    last = pipeline.last_for(video)
    if not last:
        return
    steps = []
    from resources.lib import llm
    if setting('sync_method', 'smart') in ('smart', 'auto') and llm.any_available() and \
            pipeline.has_reference(video):
        steps = ['semantic']
    elif pipeline.audio_possible(video):
        steps = ['audio']
    else:
        xbmcgui.Dialog().ok(ADDON_NAME, 'لم يتم العثور على ترجمة إنجليزية مرجعية لهذا الفيديو، والاستماع غير متاح له.\n'
                            'جرّب ترجمة أخرى من القائمة، أو اضبط التوقيت يدوياً من «تأخير الترجمة».')
        return
    pipeline.queue_job(last['path'], video, last.get('item') or {}, steps, resync=True)
    set_status('جارٍ ضبط الترجمة...')
    notify('جارٍ ضبط التوقيت... وستُستبدل الترجمة تلقائياً عند الانتهاء')
    li = xbmcgui.ListItem(label=last['path'])
    xbmcplugin.addDirectoryItem(HANDLE, last['path'], li, isFolder=False)


def do_nudge():
    video = media.current()
    try:
        ms = int(PARAMS.get('ms', '0'))
    except ValueError:
        return
    r = pipeline.nudge(video, ms)
    if not r:
        return
    path, total = r
    set_status('التوقيت %+.2f ث — تم حفظه لهذا الفيديو ✓' % (total / 1000.0), 'ok')
    li = xbmcgui.ListItem(label=path)
    xbmcplugin.addDirectoryItem(HANDLE, path, li, isFolder=False)


action = PARAMS.get('action', '')
try:
    if action == 'search':
        search()
    elif action == 'manualsearch':
        search(manual=urllib.parse.unquote(PARAMS.get('searchstring', '')))
    elif action == 'download':
        download()
    elif action == 'guide':
        xbmc.executebuiltin('RunScript(%s,guide)' % ADDON.getAddonInfo('id'))
    elif action == 'embedded_ai':
        embedded_ai()
    elif action == 'resync':
        resync()
    elif action == 'nudge':
        do_nudge()
finally:
    xbmcplugin.endOfDirectory(HANDLE)
