# -*- coding: utf-8 -*-
"""Settings of the AF3 auto-trailers, shared by the Toggles menu and the service.

Stored as one small JSON file in addon_data so the menu (a short-lived plugin
call) and the background engine (inside the service) never need Kodi's
settings machinery. The engine re-reads the file only when its mtime changes.
"""
import json
import os
import threading

import xbmcvfs

PROFILE = xbmcvfs.translatePath('special://profile/addon_data/plugin.program.abukarimtools/')
PATH = os.path.join(PROFILE, 'af3_trailers.json')
CACHE_DIR = os.path.join(PROFILE, 'trailers')

DELAYS = (1, 2, 3, 5, 8, 10)
QUALITIES = (720, 1080, 2160)
SOURCES = ('newpipe', 'imdb')   # 3.2.43~beta1 TEST: NewPipe (YouTube) or IMDb
DEFAULTS = {
    'enabled': False,   # off until the user turns it on from Toggles
    'sound': True,      # heard by default (Dex Hub does the same since 5.10.104)
    'delay': 3,         # seconds the cursor rests on a title before its trailer starts
    'quality': 720,     # highest MP4 height picked from IMDb
    'fullscreen': True, # 3.2.35: a trailer that starts opens full screen
    'source': 'newpipe', # 3.2.43~beta1 TEST: YouTube via NewPipe, IMDb as fallback
}

_cache = {'mtime': None, 'cfg': dict(DEFAULTS)}


def _clean(data):
    cfg = dict(DEFAULTS)
    if isinstance(data, dict):
        cfg['enabled'] = bool(data.get('enabled', cfg['enabled']))
        cfg['sound'] = bool(data.get('sound', cfg['sound']))
        # 3.2.37: stored as 'show' ('fullscreen' | 'background'). The 3.2.35/36
        # 'fullscreen' flag is ignored on purpose - 3.2.35 flipped it off when
        # the row was merely opened, so everyone starts on full screen again.
        cfg['fullscreen'] = data.get('show', 'fullscreen') != 'background'
        try:
            delay = int(data.get('delay', cfg['delay']))
            cfg['delay'] = delay if delay in DELAYS else DEFAULTS['delay']
        except Exception:
            pass
        source = data.get('source', cfg['source'])
        cfg['source'] = source if source in SOURCES else DEFAULTS['source']
        try:
            quality = int(data.get('quality', cfg['quality']))
            cfg['quality'] = quality if quality in QUALITIES else DEFAULTS['quality']
        except Exception:
            pass
    return cfg


def load():
    try:
        with open(PATH, 'r', encoding='utf-8') as handle:
            return _clean(json.load(handle))
    except Exception:
        return dict(DEFAULTS)


def load_cached():
    """The current settings, re-read only when the file changed."""
    try:
        mtime = os.path.getmtime(PATH)
    except OSError:
        mtime = None
    if mtime != _cache['mtime']:
        _cache['mtime'] = mtime
        _cache['cfg'] = load() if mtime is not None else dict(DEFAULTS)
    return _cache['cfg']


def save(cfg):
    cfg = dict(cfg)
    cfg['show'] = 'fullscreen' if cfg.pop('fullscreen', True) else 'background'
    cfg = _clean(cfg)
    os.makedirs(PROFILE, exist_ok=True)
    data = dict(cfg)
    data['show'] = 'fullscreen' if data.pop('fullscreen', True) else 'background'
    # a private temp name per writer: two writers never share one file
    tmp = '%s.%d.%d.tmp' % (PATH, os.getpid(), threading.get_ident())
    try:
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, PATH)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return cfg


def enabled():
    return load_cached().get('enabled', False)
