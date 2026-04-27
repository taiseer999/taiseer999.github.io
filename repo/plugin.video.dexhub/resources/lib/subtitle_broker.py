# -*- coding: utf-8 -*-
import os
import re
import time

import xbmc
import xbmcaddon

from . import store
from .client import fetch_subtitles, supports_resource

ADDON = xbmcaddon.Addon()


def _timeout_seconds():
    try:
        return max(1, int(ADDON.getSetting('subtitle_timeout') or '4'))
    except Exception:
        return 4


def enabled():
    try:
        return (ADDON.getSetting('enable_stremio_subtitle_broker') or 'true').lower() == 'true'
    except Exception:
        return True


def _normalize_lang(value):
    if isinstance(value, (list, tuple, set)):
        for item in value:
            key = _normalize_lang(item)
            if key and key != 'und':
                return key
        return 'und'
    if isinstance(value, dict):
        for k in ('lang', 'language', 'languageCode', 'iso639', 'code', 'name'):
            if value.get(k):
                key = _normalize_lang(value.get(k))
                if key and key != 'und':
                    return key
        return 'und'
    raw = str(value or 'und').strip().lower().replace('_', '-').replace(' ', '-')
    if not raw:
        return 'und'
    aliases = {
        'ara': 'ar', 'arabic': 'ar', 'عربي': 'ar', 'عربية': 'ar', 'العربية': 'ar',
        'eng': 'en', 'english': 'en',
        'fre': 'fr', 'fra': 'fr', 'french': 'fr',
        'spa': 'es', 'spanish': 'es',
        'ger': 'de', 'deu': 'de', 'german': 'de',
        'por': 'pt', 'pob': 'pt-br', 'pb': 'pt-br', 'brazilian': 'pt-br',
        'tur': 'tr', 'turkish': 'tr',
        'rus': 'ru', 'russian': 'ru',
        'jpn': 'ja', 'japanese': 'ja',
        'kor': 'ko', 'korean': 'ko',
        'chi': 'zh', 'zho': 'zh', 'chinese': 'zh',
        'hin': 'hi', 'hindi': 'hi',
        'fas': 'fa', 'per': 'fa', 'persian': 'fa', 'farsi': 'fa',
    }
    return aliases.get(raw, aliases.get(raw.split('-')[0], raw))


def _coerce_subtitle(row):
    if not row:
        return None
    if isinstance(row, str):
        return {'id': row, 'url': row, 'lang': 'und'}
    if not isinstance(row, dict):
        return None
    url = row.get('url') or row.get('externalUrl') or row.get('key')
    if not url:
        return None
    out = dict(row)
    out['url'] = url
    out['lang'] = _normalize_lang(row.get('lang') or row.get('language') or row.get('languageCode') or row.get('iso639') or 'und')
    source_name = row.get('sourceName') or row.get('providerName') or row.get('provider') or row.get('addonName') or row.get('addon') or row.get('sourceAddon') or row.get('source')
    if source_name:
        out['sourceName'] = source_name
    source_type = row.get('sourceType') or row.get('origin')
    if source_type:
        out['sourceType'] = str(source_type)
    display_name = row.get('displayName') or row.get('label') or row.get('title') or row.get('name') or row.get('release') or row.get('filename') or row.get('fileName')
    if display_name:
        out['displayName'] = str(display_name)
    return out


def _dedupe(rows):
    out = []
    seen = set()
    for row in rows:
        norm = _coerce_subtitle(row)
        if not norm:
            continue
        key = (norm.get('url') or '', norm.get('lang') or 'und')
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out


def _candidate_ids(ctx):
    """Build an aggressive list of ID variants Stremio subtitle addons accept.

    Many subtitle addons (including the official Subscene/OpenSubtitles bridges)
    need `tt…` IMDb IDs. When we only have `tmdb:…`, try to cross-resolve via
    the TMDb Helper SQLite cache so we can also fire requests in the IMDb form.
    """
    candidates = []
    for key in ('video_id', 'canonical_id'):
        val = str(ctx.get(key) or '').strip()
        if val:
            candidates.append(val)
    imdb = str(ctx.get('imdb_id') or '').strip()
    tmdb = str(ctx.get('tmdb_id') or '').strip()
    tvdb = str(ctx.get('tvdb_id') or '').strip()

    # Cross-resolve TMDb → IMDb via TMDb Helper DB (best effort, cached).
    if not imdb and tmdb:
        try:
            from . import tmdbhelper as _tmdb_art_db
            media_type = 'tv' if (ctx.get('media_type') in ('series', 'show', 'tv', 'anime')) else 'movie'
            # Reuse the DB helper to peek for any cached imdb mapping.
            bundle = _tmdb_art_db.get_art_bundle_from_db(
                tmdb_id=tmdb, media_type=media_type,
                title=ctx.get('title') or '', year=ctx.get('year') or '',
            ) or {}
            # Some TMDBH schema versions store imdb alongside posters; ignore if
            # not present — we'll still try with tmdb-prefixed variants.
            _ = bundle  # placeholder; if the helper ever exposes id mappings, wire here.
        except Exception:
            pass

    if imdb:
        imdb_norm = imdb if imdb.startswith('tt') else 'tt%s' % imdb
        candidates.extend([imdb, imdb_norm, 'imdb:%s' % imdb_norm])
    if tmdb:
        candidates.extend(['tmdb:%s' % tmdb, tmdb])
    if tvdb:
        candidates.extend(['tvdb:%s' % tvdb, tvdb])

    season = ctx.get('season')
    episode = ctx.get('episode')
    if season not in (None, '') and episode not in (None, ''):
        try:
            s = int(season)
            e = int(episode)
        except Exception:
            s = e = None
        if s is not None and e is not None:
            episode_variants = []
            for item in list(candidates):
                if not item:
                    continue
                episode_variants.append('%s:%s:%s' % (item, s, e))
            candidates = episode_variants + candidates

    out = []
    seen = set()
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _provider_order(ctx):
    rows = list(store.list_providers())
    preferred = str(ctx.get('provider_id') or '').strip()
    if not preferred:
        return rows
    front = [row for row in rows if row.get('id') == preferred]
    back = [row for row in rows if row.get('id') != preferred]
    return front + back


def _preferred_languages():
    raw = (ADDON.getSetting('preferred_subtitle_langs') or 'ar,en').strip()
    if not raw:
        return ['ar', 'en']
    return [x.strip().lower() for x in raw.split(',') if x.strip()]


def _lang_priority(lang, prefs):
    """Return sort priority — lower is better. Preferred langs rank by position."""
    lang = (lang or 'und').strip().lower().replace('_', '-')
    # Normalize common codes.
    alias = {'ara': 'ar', 'arabic': 'ar', 'eng': 'en', 'english': 'en'}
    lang_short = alias.get(lang, lang.split('-')[0])
    for i, pref in enumerate(prefs):
        if lang_short == pref:
            return i
    return 999 + len(lang_short)  # unpreferred — stable last


def _sort_by_lang_preference(rows):
    prefs = _preferred_languages()
    return sorted(rows, key=lambda r: (
        _lang_priority(r.get('lang'), prefs),
        # Stream-embedded subtitles first (most likely to match the file),
        # then addon results grouped by source name for readability.
        0 if r.get('sourceType') == 'stream' else 1,
        str(r.get('sourceName') or r.get('providerName') or 'zzz').lower(),
    ))


# Per-process subtitle result cache. Key = (canonical_id, season, episode).
# TTL is short — subtitle availability changes day-to-day — but within a
# single playback or back-and-forth session, hits are common.
_RESULT_CACHE = {}
_RESULT_CACHE_ORDER = []
_RESULT_CACHE_MAX = 64
_RESULT_TTL = 600  # 10 minutes


def _result_cache_get(key):
    entry = _RESULT_CACHE.get(key)
    if not entry:
        return None
    expires, value = entry
    if expires < time.monotonic():
        _RESULT_CACHE.pop(key, None)
        return None
    return value


def _result_cache_put(key, value):
    if key in _RESULT_CACHE:
        _RESULT_CACHE[key] = (time.monotonic() + _RESULT_TTL, value)
        return
    _RESULT_CACHE[key] = (time.monotonic() + _RESULT_TTL, value)
    _RESULT_CACHE_ORDER.append(key)
    if len(_RESULT_CACHE_ORDER) > _RESULT_CACHE_MAX:
        old = _RESULT_CACHE_ORDER.pop(0)
        _RESULT_CACHE.pop(old, None)


def search_subtitles(ctx, initial_subtitles=None, max_results=12):
    rows = _dedupe(initial_subtitles or [])
    if not enabled():
        return _sort_by_lang_preference(rows)[:max_results]
    media_type = str(ctx.get('media_type') or 'movie').strip().lower() or 'movie'

    # Check result cache first — within a single Kodi session, hitting the
    # same item twice (e.g. closing and re-opening sources) shouldn't refire
    # all addons.
    cache_key = (
        str(ctx.get('canonical_id') or ''),
        str(ctx.get('season') or ''),
        str(ctx.get('episode') or ''),
    )
    if cache_key[0]:
        cached = _result_cache_get(cache_key)
        if cached is not None:
            merged = _dedupe(rows + cached)
            return _sort_by_lang_preference(merged)[:max_results]

    candidates = _candidate_ids(ctx)
    if not candidates:
        return _sort_by_lang_preference(rows)[:max_results]
    # Cap at 3 candidates per provider — beyond that we're spamming the
    # addon with permutations that almost never differ.
    candidates = candidates[:3]

    deadline = time.monotonic() + float(_timeout_seconds())
    fetched_for_cache = []
    for provider in _provider_order(ctx):
        if time.monotonic() >= deadline:
            break
        for item_id in candidates:
            if time.monotonic() >= deadline:
                break
            try:
                if not supports_resource(provider, 'subtitles', media_type=media_type, item_id=item_id):
                    continue
                data = fetch_subtitles(provider, media_type, item_id, timeout_seconds=max(1, deadline - time.monotonic()))
                subs = []
                if isinstance(data, dict):
                    subs = data.get('subtitles') or data.get('subs') or []
                elif isinstance(data, list):
                    subs = data
                if subs:
                    annotated = []
                    for sub in subs:
                        if isinstance(sub, dict):
                            row = dict(sub)
                        else:
                            row = {'url': sub, 'id': sub, 'lang': 'und'}
                        row.setdefault('sourceType', 'addon')
                        row.setdefault('sourceName', provider.get('name') or provider.get('id') or 'Subtitle addon')
                        annotated.append(row)
                    rows.extend(annotated)
                    fetched_for_cache.extend(annotated)
                    break
            except Exception as exc:
                xbmc.log('[DexHub] subtitle broker error for %s %s: %s' % (provider.get('name'), item_id, exc), xbmc.LOGDEBUG)
                continue
        if len(rows) >= max_results:
            break

    # Cache only the addon-fetched results (not initial); next call will
    # merge them with whatever new initial_subtitles arrive.
    if cache_key[0] and fetched_for_cache:
        _result_cache_put(cache_key, fetched_for_cache)

    return _sort_by_lang_preference(_dedupe(rows))[:max_results]
