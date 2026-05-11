# -*- coding: utf-8 -*-

"""
Fast in-memory + disk cache for DPlex addon.
Reduces HTTP requests to Plex server dramatically.
"""

import hashlib
import json
import os
import time

try:
    import xbmcvfs
    import xbmc
    KODI = True
except ImportError:
    KODI = False

# TTL values (seconds)
TTL_SECTIONS      = 300    # قوائم المكتبة  -> 5 دقائق
TTL_EPISODES      = 180    # قائمة حلقات    -> 3 دقائق
TTL_ONDECK        = 30     # On Deck         -> 30 ثانية
TTL_MEDIA_INFO    = 3600   # codec/size      -> 1 ساعة
TTL_IMAGES        = 86400  # صور             -> 24 ساعة
TTL_SEARCH        = 60     # نتائج البحث    -> 1 دقيقة

def _get_cache_dir():
    if KODI:
        path = xbmcvfs.translatePath('special://temp/composite_cache/')
        if not xbmcvfs.exists(path):
            xbmcvfs.mkdirs(path)
        return path
    path = os.path.join(os.path.expanduser('~'), '.composite_cache')
    os.makedirs(path, exist_ok=True)
    return path

def _make_key(url, params=None):
    raw = url + (json.dumps(params, sort_keys=True) if params else '')
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

# In-memory layer (L1)
_MEM_CACHE = {}   
_MAX_MEM   = 200  

def _mem_get(key):
    entry = _MEM_CACHE.get(key)
    if entry and entry[0] > time.time():
        return entry[1]
    if entry:
        del _MEM_CACHE[key]
    return None

def _mem_set(key, data, ttl):
    if len(_MEM_CACHE) >= _MAX_MEM:
        now = time.time()
        expired = [k for k, v in list(_MEM_CACHE.items()) if v[0] <= now]
        for k in expired:
            del _MEM_CACHE[k]
    if len(_MEM_CACHE) >= _MAX_MEM:
        oldest = min(_MEM_CACHE, key=lambda k: _MEM_CACHE[k][0])
        del _MEM_CACHE[oldest]
    _MEM_CACHE[key] = (time.time() + ttl, data)

# Disk layer (L2)
def _disk_get(key):
    path = os.path.join(_get_cache_dir(), key + '.json')
    try:
        if KODI:
            if not xbmcvfs.exists(path):
                return None
            f = xbmcvfs.File(path)
            raw = f.read()
            f.close()
        else:
            if not os.path.exists(path):
                return None
            with open(path, 'r', encoding='utf-8') as f:
                raw = f.read()

        entry = json.loads(raw)
        if entry.get('expire', 0) > time.time():
            return entry.get('data')
    except Exception:
        pass
    return None

def _disk_set(key, data, ttl):
    path = os.path.join(_get_cache_dir(), key + '.json')
    try:
        raw = json.dumps({'expire': time.time() + ttl, 'data': data})
        if KODI:
            f = xbmcvfs.File(path, 'w')
            f.write(raw)
            f.close()
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(raw)
    except Exception:
        pass

# Public API
def get(url, params=None):
    key = _make_key(url, params)
    data = _mem_get(key)
    if data is not None:
        return data

    data = _disk_get(key)
    if data is not None:
        _mem_set(key, data, 60) 
        return data
    return None

def set(url, data, ttl, params=None):
    key = _make_key(url, params)
    _mem_set(key, data, ttl)
    if ttl >= TTL_EPISODES:
        _disk_set(key, data, ttl)

def invalidate(url, params=None):
    key = _make_key(url, params)
    _MEM_CACHE.pop(key, None)
    path = os.path.join(_get_cache_dir(), key + '.json')
    try:
        if KODI:
            xbmcvfs.delete(path)
        else:
            os.remove(path)
    except Exception:
        pass

def invalidate_all():
    _MEM_CACHE.clear()
    cache_dir = _get_cache_dir()
    try:
        if KODI:
            dirs, files = xbmcvfs.listdir(cache_dir)
            for fname in files:
                if fname.endswith('.json'):
                    xbmcvfs.delete(os.path.join(cache_dir, fname))
        else:
            for fname in os.listdir(cache_dir):
                if fname.endswith('.json'):
                    os.remove(os.path.join(cache_dir, fname))
    except Exception:
        pass

# Media Info cache 
_MEDIA_INFO_CACHE = {} 

def get_media_info(rating_key):
    entry = _MEDIA_INFO_CACHE.get(rating_key)
    if entry and entry[0] > time.time():
        return entry[1]
    return None

def set_media_info(rating_key, info_string):
    _MEDIA_INFO_CACHE[rating_key] = (time.time() + TTL_MEDIA_INFO, info_string)
