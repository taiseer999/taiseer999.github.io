# -*- coding: utf-8 -*-
"""
abk_dexhub_search.py - AB Tools "Search All" bridge for Dex Hub (4.7.13)

Copied into plugin.video.dexhub/resources/lib/ by AB Tools
(lucent_sources.SPECS['dexhub_search']) and called from one fenced hook in
plugin.py's dispatcher. Same protocol as the Fen Light device-select modes:

  ?action=app_list_sources&request_id=<id>&media_type=movie|episode&tmdb_id=..
          &imdb_id=..&title=..&season=..&episode=..
      Asks every Dex Hub stream add-on (its own provider list, timeouts and
      ranking), with no window, and saves the rows to
      addon_data/plugin.video.dexhub/device_select/<id>.json.
  ?action=app_play_source&request_id=<id>&selected_index=N
      Plays row N through Dex Hub's own play() (resolve, subtitles, resume,
      scrobbling), with the next rows of the same list as fallbacks.

The collection is the one Dex Hub's "pick from a list" TMDbHelper path uses
(_auto_play_first_movie / _auto_play_first_episode with pick_dialog), with
every provider waited for instead of the first ones to settle.
"""
import json
import os
import re

import xbmc
import xbmcplugin
import xbmcvfs

_ID = 'plugin.video.dexhub'
_DIR = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'), _ID, 'device_select')
_FALLBACKS = 4


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[DexHub ABK Search All] %s' % msg, level)


def _path(rid):
    safe = ''.join(c for c in str(rid or '') if c.isalnum() or c in '_-') or 'abs'
    return os.path.join(_DIR, '%s.json' % safe)


def _close_dir(api):
    try:
        if int(api.HANDLE) >= 0:
            xbmcplugin.endOfDirectory(api.HANDLE, succeeded=True, cacheToDisc=False)
    except Exception:
        pass


def _gb(e):
    try:
        return float(e.get('size_bytes') or 0) / 1073741824.0
    except (TypeError, ValueError):
        return 0.0


_RES = re.compile(r'(?<![a-z0-9])(2160p|4k|uhd|1080p|720p)(?![a-z0-9])', re.I)


def _quality(e, name):
    q = str(e.get('quality') or '').upper()
    if q in ('4K', '1080P', '720P'):
        return q
    if q in ('', '--'):                     # Dex Hub found no resolution tag: the file name may have one
        m = _RES.search(name)
        if m:
            r = m.group(1).upper()
            return '4K' if r in ('2160P', '4K', 'UHD') else r
    return 'SD'


def _bits(value):
    return [b.strip() for b in str(value or '').split('|') if b.strip() and b.strip() != '--']


def _row(e):
    """A Dex Hub entry as a Fen Light style result row (what ab_search.merge reads)."""
    name = str(e.get('filename') or e.get('name') or e.get('stream_title') or '').strip()
    gb = _gb(e)
    size_label = str(e.get('size_label') or '').strip()
    if size_label == '--':
        size_label = ('%.2f GB' % gb) if gb else ''
    info = []
    for part in _bits(e.get('extraInfo')) + _bits(e.get('extraInfo2')):
        if part not in info:
            info.append(part)
    row = {'name': name, 'display_name': name, 'quality': _quality(e, name), 'size': gb, 'size_label': size_label,
           'scrape_provider': 'external',
           'debrid': str(e.get('source_service') or e.get('service_name') or '').strip(),
           'source': str(e.get('source_addon') or e.get('provider_name_raw') or 'Dex Hub').strip(),
           'abk_site': str(e.get('source_site') or '').strip(),
           'extraInfo': ' | '.join(info), 'hash': str(e.get('info_hash') or '').strip().lower(),
           'stream_key': e.get('stream_key') or ''}
    if e.get('cached') is False:
        row['cache_provider'] = 'Uncached'
    return row


def _collect(api, params):
    vtype = 'series' if params.get('media_type') in ('episode', 'tv', 'tvshow', 'series') else 'movie'
    tmdb_id = str(params.get('tmdb_id') or '').strip()
    imdb_id = str(params.get('imdb_id') or '').strip()
    tvdb_id = str(params.get('tvdb_id') or '').strip()
    title = str(params.get('title') or '').strip()
    season, episode = params.get('season'), params.get('episode')
    canonical_id = api._resolve_best_id('episode' if vtype == 'series' else 'movie', tmdb_id=tmdb_id,
                                        imdb_id=imdb_id, tvdb_id=tvdb_id, title=title)
    if not canonical_id:
        raise ValueError('no id for %s' % params)
    seed_ids = {'tmdb_id': tmdb_id, 'imdb_id': imdb_id if imdb_id.startswith('tt') else '', 'tvdb_id': tvdb_id}
    video_id = None
    if vtype == 'series':
        from .search.episode_route import helper_episode_id
        video_id = helper_episode_id(imdb_id, season, episode)
        if not video_id:
            video_id, _t = api._find_episode_video_id(canonical_id, season, episode)
    providers = api._provider_order_for_id_with_context(vtype, canonical_id)
    try:
        meta, cached = api._fast_meta_for_sources(vtype, canonical_id, providers, title=title, seed_ids=seed_ids)
    except Exception:
        meta, cached = None, False
    if not cached:
        meta = api._best_meta_for_item(vtype, canonical_id, providers)
    meta = meta or {}
    fb = api._item_fallback_art(providers[0] if providers else {}, vtype)
    art = api._resolve_meta_art(providers[0] if providers else {}, vtype, meta, fallback_art=fb)
    art = api._prefer_item_art(art, meta, vtype, fallback_art=fb)
    bg = api._content_background(art, fb)
    ids = api._merge_seed_ids(api.extract_ids(meta), seed_ids)
    ids = api._enrich_stream_ids(ids, vtype, meta=meta, canonical_id=canonical_id,
                                 title=title or meta.get('name') or meta.get('title') or '')
    stream_meta = api._meta_with_seed_ids(meta, ids)
    if vtype == 'series':
        targets = list(api._stream_provider_targets(vtype, canonical_id, meta=stream_meta, season=season, episode=episode))
    else:
        targets = list(api._stream_provider_targets(vtype, canonical_id, meta=stream_meta))
    targets = api._prioritize_provider_targets(targets)
    targets, fallback = api._split_targets_by_source_mode(targets)
    entries = []

    def _fetch(t):
        return api._fetch_stream_payload(t, vtype)

    def _append(target, data):
        p, rid = target
        if vtype == 'series':
            api._append_stream_entries_from_data(entries, data, p, rid, vtype, canonical_id, meta, art, bg, ids,
                                                 title=title, video_id=video_id, season=season, episode=episode)
        else:
            api._append_stream_entries_from_data(entries, data, p, rid, vtype, canonical_id, meta, art, bg, ids,
                                                 title=title)

    for batch in (targets, fallback):
        if entries or not batch:
            continue
        for target, data in api.run_parallel(_fetch, batch):
            if isinstance(data, Exception) or not data:
                continue
            try:
                _append(target, data)
            except Exception as e:
                _log('rows of %s skipped: %s' % (target[0].get('name') if isinstance(target[0], dict) else '?', e),
                     xbmc.LOGWARNING)
    if entries:
        kw = {'media_type': vtype, 'canonical_id': canonical_id}
        if video_id:
            kw['video_id'] = video_id
        entries = api._finalize_stream_entries(entries, **kw)
    return [_row(e) for e in entries if e.get('stream_key')]


def _list(api, params):
    rid = params.get('request_id') or ''
    rows = []
    try:
        rows = _collect(api, params)
        _log('%d sources for %s' % (len(rows), rid))
    except Exception as e:
        _log('list failed: %s' % e, xbmc.LOGWARNING)
    try:
        os.makedirs(_DIR, exist_ok=True)
        # old request files (one per search) go after a day
        import time
        for name in os.listdir(_DIR):
            full = os.path.join(_DIR, name)
            if name.startswith('abs') and time.time() - os.path.getmtime(full) > 86400:
                os.remove(full)
        tmp = _path(rid) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(rows, f)
        os.replace(tmp, _path(rid))
    except Exception as e:
        _log('result file not written: %s' % e, xbmc.LOGWARNING)
    _close_dir(api)


def _play(api, params):
    try:
        with open(_path(params.get('request_id')), 'r', encoding='utf-8') as f:
            rows = json.load(f)
        idx = int(params.get('selected_index') or 0)
        key = rows[idx]['stream_key']
    except Exception as e:
        _log('play: no such row (%s)' % e, xbmc.LOGWARNING)
        return _close_dir(api)
    fallbacks = [r.get('stream_key') for r in rows[idx + 1:idx + 1 + _FALLBACKS]
                 if r.get('stream_key') and r.get('cache_provider') != 'Uncached']
    _log('play row %d (%d fallbacks)' % (idx, len(fallbacks)))
    return api.play(key, fallback_keys=fallbacks)


def app_mode(api, action, params):
    if action == 'app_list_sources':
        return _list(api, params)
    return _play(api, params)
