# -*- coding: utf-8 -*-
"""Use the OTHER subtitle add-ons already installed in Kodi (a4kSubtitles, OpenSubtitles,
SubDL, Arabic build add-ons ...) as extra sources — no API keys needed on our side.

Kodi subtitle add-ons are plugins: Kodi's own subtitle dialog lists them with
plugin://<id>/?action=search&languages=... and downloads with the item's URL.
We do exactly the same through JSON-RPC Files.GetDirectory, then run our own
fixing / sync / AI on whatever file they give back."""
import json
import urllib.parse

import xbmc
import xbmcvfs

from ..common import ADDON_ID, log, setting

LANG_NAMES = {'ar': 'Arabic', 'en': 'English'}
SKIP = {ADDON_ID}


def _rpc(method, params):
    q = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    try:
        return json.loads(xbmc.executeJSONRPC(q))
    except Exception as e:
        log('rpc %s failed: %s' % (method, e))
        return {}


def installed():
    r = _rpc('Addons.GetAddons', {'type': 'xbmc.subtitle.module', 'enabled': True,
                                  'properties': ['name']})
    out = []
    for a in r.get('result', {}).get('addons', []) or []:
        # only real subtitle services; video add-ons that also register a subtitle
        # module (e.g. hubs) can start their own playback logic when called
        if a.get('addonid') not in SKIP and a.get('addonid', '').startswith('service.subtitles.'):
            out.append((a['addonid'], a.get('name') or a['addonid']))
    return out


def available():
    return setting('use_kodi_addons', 'true') == 'true' and bool(installed())


def _lang_of(f):
    thumb = (f.get('thumbnail') or '').lower()
    label = (f.get('label') or '').lower()
    for code, name in LANG_NAMES.items():
        if thumb in (code, name.lower()) or thumb.startswith(code + '.') or \
                label == name.lower() or label.startswith(name.lower()):
            return code
    if 'arab' in label or 'عرب' in label:
        return 'ar'
    return ''


def _search_one(addon_id, addon_name, langs, video):
    names = ','.join(LANG_NAMES[l] for l in langs if l in LANG_NAMES)
    params = {'action': 'search', 'languages': names, 'preferredlanguage': LANG_NAMES[langs[0]]}
    url = 'plugin://%s/?%s' % (addon_id, urllib.parse.urlencode(params))
    r = _rpc('Files.GetDirectory', {'directory': url, 'media': 'files',
                                    'properties': ['title', 'thumbnail', 'file']})
    out = []
    for f in r.get('result', {}).get('files', []) or []:
        lang = _lang_of(f)
        if lang not in langs:
            continue
        rel = f.get('title') or f.get('label') or ''
        out.append({
            'provider': 'kodi',
            'source': addon_name,
            'id': f.get('file'),
            'lang': lang,
            'release': rel if rel.lower() not in ('arabic', 'english') else '',
            'hi': False,
            'hash_match': False,
            'episode': '',
        })
    return out


def search(video, langs):
    import threading
    if not video.get('interactive'):
        return []          # never call other add-ons from the background (playback start)
    results = []
    lock = threading.Lock()

    def one(aid, name):
        try:
            items = _search_one(aid, name, langs, video)
            log('kodi add-on %s: %d results' % (name, len(items)))
            with lock:
                results.extend(items)
        except Exception as e:
            log('kodi add-on %s failed: %s' % (name, e))
    threads = []
    for aid, name in installed():
        t = threading.Thread(target=one, args=(aid, name), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(20)        # a slow/hung add-on must never block us
    with lock:
        return list(results)


def download(item):
    r = _rpc('Files.GetDirectory', {'directory': item['id'], 'media': 'files'})
    files = r.get('result', {}).get('files', []) or []
    for f in files:
        path = f.get('file') or f.get('label') or ''
        if not path:
            continue
        try:
            fh = xbmcvfs.File(path)
            data = bytes(fh.readBytes())
            fh.close()
            if data:
                return data
        except Exception as e:
            log('read %s failed: %s' % (path, e))
    raise Exception('لم تُرجع الإضافة %s ملف ترجمة' % item.get('source', ''))
