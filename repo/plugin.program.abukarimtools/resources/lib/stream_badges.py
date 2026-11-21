# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""4.9.9: facts for the OSD badge row the skin cannot read by itself, set as
Home window properties when a video starts (disc_stream's player calls in):

  abk.lp.bits   8 / 10 / 12      video bit depth - same reading as the
                                 Statistics screen (lucent_playerinfo.bit_depth);
                                 empty when Kodi reports none
  abk.lp.cont   MKV / MP4 / TS / AVI   the container, from the file name
  abk.lp.multi  1                more than one audio language in the file

Kodi has no infolabel for the number of audio tracks, so that one comes from
JSON-RPC Player.GetProperties."""
import json
import re
import threading
import time
import urllib.parse

import xbmc
import xbmcgui

PROPS = ('abk.lp.bits', 'abk.lp.cont', 'abk.lp.multi')
_CONT = (('.mkv', 'MKV'), ('.mk3d', 'MKV'), ('.webm', 'MKV'), ('.mp4', 'MP4'), ('.m4v', 'MP4'),
         ('.mov', 'MP4'), ('.m2ts', 'TS'), ('.mts', 'TS'), ('.ts', 'TS'), ('.avi', 'AVI'))
_gen = [0]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Badges] %s' % msg, level)


def _home():
    return xbmcgui.Window(10000)


def clear():
    _gen[0] += 1
    h = _home()
    for p in PROPS:
        h.clearProperty(p)


def container(path):
    low = str(path or '').split('|', 1)[0].lower()
    if low.startswith('bluray://'):
        return 'TS'
    bare = urllib.parse.unquote(urllib.parse.urlsplit(low).path if '://' in low else low)
    for ext, name in _CONT:
        if bare.endswith(ext):
            return name
    m = re.search(r'\.(mkv|mp4|m2ts|avi)\b', low)          # resolver links: ...file.mkv?token=
    return {'mkv': 'MKV', 'mp4': 'MP4', 'm2ts': 'TS', 'avi': 'AVI'}.get(m.group(1)) if m else ''


def _audio_languages():
    q = {"jsonrpc": "2.0", "id": 1, "method": "Player.GetProperties",
         "params": {"playerid": 1, "properties": ["audiostreams"]}}
    try:
        res = json.loads(xbmc.executeJSONRPC(json.dumps(q)))
        streams = (res.get('result') or {}).get('audiostreams') or []
    except Exception:
        return None
    langs = set()
    for s in streams:
        lang = str(s.get('language') or '').strip().lower()
        langs.add(lang if lang and lang not in ('und', 'unk', 'unknown') else 'und#%s' % s.get('index'))
    return langs if streams else None


def _bits(path=''):
    try:
        from resources.lib import lucent_playerinfo as lp
        hdr = (xbmc.getInfoLabel('VideoPlayer.HdrType') or '').lower()
        # 4.12.5: the file name's FEL / MEL as a last fallback for the layer
        name = urllib.parse.unquote(str(path or '').split('|', 1)[0].rsplit('/', 1)[-1])
        layer = '%s %s' % (xbmc.getInfoLabel('Player.Process(amlogic.dv.el)'),
                           lp.dolby_vision_from_name(name).get('layer') or '')
        return lp.bit_depth(hdr, xbmc.getInfoLabel('Player.Process(video.source.hdr.type)'), layer)
    except Exception as e:
        _log('bit depth: %s' % e, xbmc.LOGWARNING)
        return 0


def started(path):
    """onAVStarted: fill the properties; Player.Process values arrive a moment
    after the first frame, so bit depth is read again for a few seconds."""
    clear()
    gen = _gen[0]
    h = _home()
    cont = container(path)
    if cont:
        h.setProperty('abk.lp.cont', cont)

    def work():
        mon = xbmc.Monitor()
        langs = None
        bits = 0
        for _ in range(8):
            if gen != _gen[0] or mon.abortRequested() or not xbmc.Player().isPlayingVideo():
                return
            if langs is None:
                langs = _audio_languages()
                if langs is not None and len(langs) > 1:
                    h.setProperty('abk.lp.multi', '1')
            b = _bits(path)
            if b and b > bits:
                bits = b
                h.setProperty('abk.lp.bits', str(b))
            # 4.12.5: Dolby Vision's layer facts arrive after the first frame -
            # keep reading (8 s) until the 12-bit of an FEL / MEL shows
            dv_wait = (xbmc.getInfoLabel('VideoPlayer.HdrType') or '').lower() == 'dolbyvision' \
                and bits < 12
            if langs is not None and bits and not dv_wait \
                    and xbmc.getInfoLabel('Player.Process(video.bitdepth)'):
                break
            if mon.waitForAbort(1.0):
                return
        _log('%s: %s-bit, container %s, audio languages %s'
             % (str(path or '').split('|', 1)[0].rsplit('/', 1)[-1][:60], bits or '?', cont or '?',
                len(langs) if langs is not None else '?'))

    threading.Thread(target=work, name='abk-badges', daemon=True).start()
