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
# 3.2.48: how a trailer is shown. 'artwork' = Dex Hub's way (inside AF3's
# artwork frame, faded in once it plays, parked between titles) - the default;
# 'background' = behind the whole page (AF3's background video);
# 'fullscreen' = grows to Kodi's full-screen video window.
SHOWS = ('artwork', 'background', 'fullscreen')
# A file written before 3.2.48 moves to 'artwork' once: 3.2.37 had put
# everyone on full screen without asking, so that value was never a choice.
SHOW_V = 2
DEFAULTS = {
    'enabled': False,   # off until the user turns it on from Toggles
    'sound': True,      # heard by default (Dex Hub does the same since 5.10.104)
    'delay': 3,         # seconds the cursor rests on a title before its trailer starts
    'quality': 720,     # highest MP4 height picked from IMDb
    'show': 'artwork',  # 3.2.48 (see SHOWS)
    'fullscreen': False, # derived from 'show' (kept for older callers)
    'source': 'newpipe', # 3.2.43~beta1 TEST: YouTube via NewPipe, IMDb as fallback
}

_cache = {'mtime': None, 'cfg': dict(DEFAULTS)}


def _clean(data):
    cfg = dict(DEFAULTS)
    if isinstance(data, dict):
        cfg['enabled'] = bool(data.get('enabled', cfg['enabled']))
        cfg['sound'] = bool(data.get('sound', cfg['sound']))
        # 3.2.37: stored as 'show'. The 3.2.35/36 'fullscreen' flag is
        # ignored on purpose. 3.2.48: a file older than SHOW_V moves to
        # 'artwork' once (see SHOW_V).
        show = data.get('show', DEFAULTS['show'])
        if data.get('show_v') != SHOW_V:
            show = DEFAULTS['show']
        cfg['show'] = show if show in SHOWS else DEFAULTS['show']
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
    cfg['fullscreen'] = cfg['show'] == 'fullscreen'
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
    """Write ``cfg`` (its 'show' decides; 'fullscreen' is derived)."""
    data = dict(cfg)
    data['show_v'] = SHOW_V
    cfg = _clean(data)
    os.makedirs(PROFILE, exist_ok=True)
    data = {k: v for k, v in cfg.items() if k != 'fullscreen'}
    data['show_v'] = SHOW_V
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
