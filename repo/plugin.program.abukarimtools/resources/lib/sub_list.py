# -*- coding: utf-8 -*-
"""
sub_list.py - ABUKARIM TOOLS (4.6.14)

One subtitle list for the Arctic Fuse 3 player, after the subtitle list of
the Lucent skin by djdirty60 (1.31.39 / 1.31.40) - built with Kodi's own
player API and AB Tools' glass select window, no Lucent add-on:

    Subtitles: On / Off            toggles the subtitle display
    <streams in your languages>    the subtitles inside the video, current one
                                   marked; your languages = Kodi's preferred
                                   subtitle language, the GUI language, English
    Other languages      N         the rest, in a second list
    Search online...               Kodi's subtitle search window (the subtitle
                                   services you have installed)
    Subtitle look...               the AB Tools height / size / font panel

While "AF3: Lucent Look" is on, the AF3 OSD subtitle button opens this list
(patcher, Includes VideoOSD.xml, button 6007); with the look off the button
keeps AF3's own behaviour (Kodi's subtitle settings).
"""
import json

import xbmc

from resources.lib.i18n import T

ADDON_PATH = 'special://home/addons/plugin.program.abukarimtools/'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SubList] %s' % msg, level)


def _rpc(method, params=None):
    try:
        out = json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
        return out.get('result')
    except Exception as e:
        _log('%s failed: %s' % (method, e), xbmc.LOGWARNING)
        return None


def _player_id():
    for p in _rpc('Player.GetActivePlayers') or []:
        if p.get('type') == 'video':
            return p.get('playerid')
    return None


def _code(name):
    """'Arabic' / 'ar' / 'ara' -> 'ara' (ISO 639-2), '' when unknown."""
    if not name or name in ('original', 'default', 'none', 'forced_only'):
        return ''
    try:
        return (xbmc.convertLanguage(name, xbmc.ISO_639_2) or '').lower()
    except Exception:
        return ''


def my_languages():
    """ISO 639-2 codes, in order: preferred subtitle language, GUI language, English."""
    out = []
    pref = (_rpc('Settings.GetSettingValue', {'setting': 'locale.subtitlelanguage'}) or {}).get('value')
    for name in (pref, xbmc.getLanguage(xbmc.ISO_639_1), 'English'):
        c = _code(name)
        if c and c not in out:
            out.append(c)
    return out


def _stream_label(s):
    lang = s.get('language') or ''
    name = s.get('name') or ''
    try:
        full = xbmc.convertLanguage(lang, xbmc.ENGLISH_NAME) if lang else ''
    except Exception:
        full = ''
    label = full or lang.upper() or T(30885)
    if name and name.lower() not in (label.lower(), lang.lower()):
        label = '%s  ·  %s' % (label, name)
    flags = [T(30886)] if s.get('isforced') else []
    flags += [T(30887)] if s.get('isimpaired') else []
    flags = [f for f in flags if f.lower() not in label.lower()]      # "Forced" already in the name
    return label + ('  (%s)' % ', '.join(flags) if flags else '')


def split_streams(streams, mine):
    """(in my languages - ordered by my language order, others)."""
    rank = {c: i for i, c in enumerate(mine)}
    first = [s for s in streams if (s.get('language') or '').lower() in rank]
    first.sort(key=lambda s: (rank[(s.get('language') or '').lower()], s.get('index', 0)))
    rest = [s for s in streams if s not in first]
    return first, rest


def _theme():
    from resources.lib import ab_search
    th = ab_search._theme()
    if th:
        th._addon_root = lambda: ab_search.ADDON_PATH.rstrip('/\\')      # AB Tools' own lucent_select.xml
    return th


def _select(heading, labels, marks, preselect=0):
    th = _theme()
    if th:
        return th.lucent_select(heading, labels, counts=marks, preselect=preselect)
    import xbmcgui
    rows = ['%s   %s' % (l, m) if m else l for l, m in zip(labels, marks)]
    return xbmcgui.Dialog().select(heading, rows, preselect=preselect)


def _pick_stream(pid, streams, current, enabled, heading):
    labels = [_stream_label(s) for s in streams]
    marks = ['✓' if (enabled and current and s.get('index') == current.get('index')) else '' for s in streams]
    pre = next((i for i, m in enumerate(marks) if m), 0)
    pick = _select(heading, labels, marks, pre)
    if pick is None or pick < 0:
        return False
    idx = streams[pick].get('index')
    _rpc('Player.SetSubtitle', {'playerid': pid, 'subtitle': idx, 'enable': True})
    _log('subtitle stream %s (%s)' % (idx, streams[pick].get('language')))
    return True


def open_list():
    pid = _player_id()
    if pid is None:
        _log('no video playing')
        return
    props = _rpc('Player.GetProperties', {'playerid': pid,
                                          'properties': ['subtitles', 'currentsubtitle', 'subtitleenabled']}) or {}
    streams = props.get('subtitles') or []
    current = props.get('currentsubtitle') or {}
    enabled = bool(props.get('subtitleenabled'))
    mine, rest = split_streams(streams, my_languages())

    rows, marks, acts = [], [], []
    rows.append(T(30881) if enabled else T(30882)); marks.append(''); acts.append(('toggle', None))
    for s in mine:
        rows.append(_stream_label(s))
        marks.append('✓' if enabled and current and s.get('index') == current.get('index') else '')
        acts.append(('stream', s))
    if rest:
        cur_in_rest = enabled and current and any(s.get('index') == current.get('index') for s in rest)
        rows.append(T(30883)); marks.append('✓' if cur_in_rest else str(len(rest))); acts.append(('rest', None))
    rows.append(T(30884)); marks.append(''); acts.append(('search', None))
    rows.append(T(30888)); marks.append(''); acts.append(('look', None))
    if not streams:
        marks[0] = T(30889)                      # no subtitles inside the video
    pre = next((i for i, m in enumerate(marks) if m == '✓'), 0)

    pick = _select(T(30880), rows, marks, pre)
    if pick is None or pick < 0:
        return
    kind, s = acts[pick]
    if kind == 'toggle':
        _rpc('Player.SetSubtitle', {'playerid': pid, 'subtitle': 'off' if enabled else 'on'})
        _log('subtitles %s' % ('off' if enabled else 'on'))
    elif kind == 'stream':
        _rpc('Player.SetSubtitle', {'playerid': pid, 'subtitle': s.get('index'), 'enable': True})
        _log('subtitle stream %s (%s)' % (s.get('index'), s.get('language')))
    elif kind == 'rest':
        _pick_stream(pid, rest, current, enabled, T(30883))
    elif kind == 'search':
        xbmc.executebuiltin('ActivateWindow(subtitlesearch)')
    elif kind == 'look':
        from resources.lib import sub_quick
        sub_quick.open_window()
