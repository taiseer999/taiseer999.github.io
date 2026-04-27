# -*- coding: utf-8 -*-
"""Per-provider metadata source.

Each registered provider (Plex, Emby, Plexio, Jellyfin, Cinemeta, Torrentio,
etc.) can have its own metadata override target. The mapping is stored as a
single JSON blob in `provider_meta_map` setting:

    {
      "plexio_abc123":  "cinemeta_xyz",    # provider_id → meta source id
      "plex_def456":    "tmdb_helper",
      "anime_provider": "kitsu_mno"
    }

Values can be:
  - A provider_id of another registered Stremio meta-capable addon
  - "tmdb_helper" — TMDb Helper local database only (no Dex Hub TMDb API key required)
  - "auto"   (or missing key) — heuristic default. Plex/Emby get auto-replaced
             from the first available meta addon, every other addon stays native.
  - "native" — explicitly keep the provider's own metadata, no override.
               When set, the override layer is a no-op for both individual and
               batch calls; the consumer is expected to also respect it when
               picking artwork (see _resolve_meta_art in plugin.py).

`list_available_meta_sources()` populates the picker UI. We auto-register
EVERY addon that declares `meta` as a resource — the previous narrow whitelist
("only addons whose name contains cinemeta/tmdb/...") missed addons like
AIOMetadata, Anime Catalogs, MAL, anidb, etc.
"""
import json

import xbmc
import xbmcaddon

from .dexhub import store as _store
from .dexhub.client import fetch_meta
from .art import extract_ids

ADDON = xbmcaddon.Addon()


def _load_map():
    try:
        raw = ADDON.getSetting('provider_meta_map') or '{}'
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_map(mapping):
    try:
        ADDON.setSetting('provider_meta_map', json.dumps(mapping or {}, ensure_ascii=False))
    except Exception:
        pass


def get_meta_source_for(provider_id):
    """Return the configured meta source id for a given provider, or 'auto'."""
    if not provider_id:
        return 'auto'
    return (_load_map().get(provider_id) or 'auto').strip() or 'auto'


def set_meta_source_for(provider_id, source_id):
    if not provider_id:
        return
    mapping = _load_map()
    if not source_id or source_id == 'auto':
        mapping.pop(provider_id, None)
    else:
        mapping[provider_id] = source_id
    _save_map(mapping)
    # Drop the on-disk + in-memory HTTP cache for /meta/ URLs so the very
    # next catalog/detail render actually reflects the new mapping. Without
    # this, the user would have to wait for the meta TTL to expire (often
    # 6h+) before the change took visible effect — what users perceived as
    # "the meta source picker doesn't work".
    try:
        from .dexhub.client import purge_meta_cache as _purge
        _purge()
    except Exception:
        pass


def clear_meta_map():
    _save_map({})
    try:
        from .dexhub.client import purge_meta_cache as _purge
        _purge()
    except Exception:
        pass


def _provider_supports_meta(provider):
    manifest = (provider or {}).get('manifest') or {}
    for resource in manifest.get('resources', []):
        if resource == 'meta':
            return True
        if isinstance(resource, dict) and resource.get('name') == 'meta':
            return True
    return False


# --- Stream-only detection (Plex/Emby/Plexio/Jellyfin/DexBridge) --------
# These providers have private-token poster URLs that Kodi can't reliably
# load, so 'auto' meta-source mode auto-replaces them with remote art.
_STREAM_ONLY_HINTS = ('plex', 'plexio', 'emby', 'jellyfin', 'dexbridge')

# Negative hints for meta-source picker — these addons CAN report meta but
# the user almost never wants them as the *primary* metadata source for
# OTHER addons. They still get listed if the user hasn't disabled them.
_META_PICKER_BLOCKLIST = ('torrentio', 'comet', 'mediafusion', 'watchhub',
                          'opensubtitles', 'orion', 'debrid', 'real-debrid',
                          'realdebrid', 'rd:', 'aiostreams')


def _provider_haystack(provider):
    manifest = (provider or {}).get('manifest') or {}
    return ' '.join([
        str((provider or {}).get('name') or ''),
        str((provider or {}).get('id') or ''),
        str((provider or {}).get('base_url') or ''),
        str((provider or {}).get('manifest_url') or ''),
        str(manifest.get('name') or ''),
        str(manifest.get('id') or ''),
        str(manifest.get('description') or ''),
    ]).lower()


def _provider_is_plexio(provider):
    haystack = _provider_haystack(provider)
    return any(hint in haystack for hint in (
        'plexio', 'plexbridge', 'com.stremio.plexio', 'com.stremio.plexbridge',
        'plexio.dexworld.cc'
    ))


def _provider_looks_like_meta_source(provider):
    """Permissive check: any provider that DECLARES `meta` is eligible for the
    picker, except the well-known stream-only providers and known stream
    aggregators. This is the fix for: 'when adding any tool that supports
    metadata it should auto-appear in the metadata picker'.
    """
    if not _provider_supports_meta(provider):
        return False
    haystack = _provider_haystack(provider)
    if any(hint in haystack for hint in _STREAM_ONLY_HINTS):
        return False
    if any(hint in haystack for hint in _META_PICKER_BLOCKLIST):
        return False
    return True


def provider_is_stream_only(provider):
    """True if provider is best known for streams/catalogs, unreliable meta."""
    return any(h in _provider_haystack(provider) for h in _STREAM_ONLY_HINTS)


def list_available_meta_sources():
    """Return the list of choosable meta sources for the picker."""
    sources = [
        {'id': 'auto', 'name': 'تلقائي (ذكي)', 'kind': 'special'},
        {'id': 'native', 'name': 'ميتاداتا الإضافة نفسها', 'kind': 'special'},
        {'id': 'tmdb_helper', 'name': 'TMDb Helper (بدون API)', 'kind': 'builtin'},
    ]
    seen = set()
    for row in _store.list_providers() or []:
        if not _provider_looks_like_meta_source(row):
            continue
        pid = row.get('id') or ''
        if not pid or pid in seen:
            continue
        seen.add(pid)
        sources.append({
            'id': pid,
            'name': row.get('name') or pid,
            'kind': 'stremio',
        })
    return sources


def source_display_name(source_id):
    """Human label for a source id, used in menus."""
    if not source_id or source_id == 'auto':
        return 'Automatic'
    if source_id == 'native':
        return 'Addon metadata'
    if source_id == 'tmdb_helper':
        return 'TMDb Helper'
    prov = _store.get_provider(source_id)
    if prov:
        return prov.get('name') or source_id
    return source_id


def _candidate_ids(ids):
    imdb = ids.get('imdb_id') or ''
    tmdb = ids.get('tmdb_id') or ''
    tvdb = ids.get('tvdb_id') or ''
    candidates = []
    if imdb:
        candidates.append(imdb if imdb.startswith('tt') else 'tt%s' % imdb)
    if tmdb:
        candidates.append('tmdb:%s' % tmdb)
    if tvdb:
        candidates.append('tvdb:%s' % tvdb)
    return candidates


def _fetch_from_stremio(meta_provider_id, media_type, ids):
    provider = _store.get_provider(meta_provider_id) if meta_provider_id else None
    if not provider:
        return None
    stremio_mt = 'series' if media_type in ('series', 'anime', 'tv', 'show') else 'movie'
    for item_id in _candidate_ids(ids):
        try:
            data = fetch_meta(provider, stremio_mt, item_id)
            meta = data.get('meta') or {}
            if meta and (meta.get('poster') or meta.get('background') or meta.get('description')):
                return meta
        except Exception as exc:
            xbmc.log('[DexHub] meta fetch %s:%s failed: %s' % (
                provider.get('name'), item_id, exc), xbmc.LOGDEBUG)
            continue
    return None


def _fetch_from_tmdb_helper(ids, meta, media_type):
    """Pull artwork from TMDb Helper only.

    This source intentionally reads TMDb Helper's local database and never calls
    Dex Hub's `tmdb_direct` API fallback. When the user chooses TMDb Helper as
    the metadata source, the result must be 100% from the helper add-on cache
    and should not require a TMDb API key in Dex Hub.

    Fall-through: if TMDb Helper has never cached this item (common on fresh
    installs or for less popular content), try the tmdb_direct API so the user
    doesn't see a blank poster. This is still "TMDB" artwork — just fetched
    live from the API instead of from the helper's cache.
    """
    is_tv = media_type in ('series', 'anime', 'show', 'tv')
    mt_norm = 'tv' if is_tv else 'movie'
    tmdb_id = str(ids.get('tmdb_id') or '').strip()
    imdb_id = str(ids.get('imdb_id') or '').strip()
    title = str(meta.get('name') or meta.get('title') or '').strip()
    year = str(meta.get('releaseInfo') or meta.get('year') or '').strip()

    try:
        from . import tmdbhelper as _tmdbh
        db_bundle = _tmdbh.get_art_bundle_from_db(
            tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            media_type=mt_norm,
            title=title,
            year=year,
        ) or {}
    except Exception:
        db_bundle = {}

    poster = db_bundle.get('poster') or ''
    fanart = db_bundle.get('fanart') or db_bundle.get('landscape') or ''
    clearlogo = db_bundle.get('clearlogo') or ''
    if any([poster, fanart, clearlogo]):
        return {
            'poster': poster,
            'background': fanart,
            'fanart': fanart,
            'landscape': db_bundle.get('landscape') or fanart,
            'logo': clearlogo,
            'clearlogo': clearlogo,
        }

    # TMDb Helper DB had no cached art for this item. Fall back to tmdb_direct
    # API (requires the user's TMDb API key setting) so the user sees real
    # artwork instead of a blue default square.
    try:
        from . import tmdb_direct as _td
        direct = _td.art_for(
            tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            media_type=mt_norm,
            title=title,
            year=year,
        ) or {}
    except Exception:
        direct = {}
    d_poster = direct.get('poster') or ''
    d_fanart = direct.get('fanart') or direct.get('landscape') or ''
    d_clearlogo = direct.get('clearlogo') or ''
    if not any([d_poster, d_fanart, d_clearlogo]):
        return None

    return {
        'poster': d_poster,
        'background': d_fanart,
        'fanart': d_fanart,
        'landscape': direct.get('landscape') or d_fanart,
        'logo': d_clearlogo,
        'clearlogo': d_clearlogo,
    }


def _meta_is_good_enough(meta):
    if not isinstance(meta, dict):
        return False
    if not (meta.get('poster') or meta.get('logo') or meta.get('clearlogo')):
        return False
    if meta.get('background') or meta.get('fanart') or meta.get('landscape'):
        return True
    desc = meta.get('description') or meta.get('overview') or ''
    return len(str(desc)) >= 80


_ART_OVERRIDE_KEYS = (
    'poster', 'posterUrl', 'posterURL', 'thumbnail', 'thumb', 'thumbUrl', 'thumbURL',
    'image', 'imageUrl', 'imageURL', 'background', 'fanart', 'landscape', 'banner',
    'backdrop', 'logo', 'clearlogo', 'clearart', 'plex_original_poster',
    'parentThumb', 'grandparentThumb'
)


def _drop_art_fields(meta):
    """Remove artwork from a base meta object before applying an explicit source.

    Without this, choosing a metadata source can still leak artwork from the
    previous/provider meta through nested `images` or `behaviorHints` fields.
    """
    out = dict(meta or {})
    for key in _ART_OVERRIDE_KEYS:
        out.pop(key, None)
    images = out.get('images')
    if isinstance(images, dict):
        new_images = dict(images)
        for key in list(new_images.keys()):
            if str(key).lower() in (
                'poster', 'thumb', 'thumbnail', 'cover', 'image', 'posterurl', 'poster_url',
                'background', 'fanart', 'backdrop', 'landscape', 'banner', 'art',
                'clearlogo', 'clearart', 'logo'
            ):
                new_images.pop(key, None)
        if new_images:
            out['images'] = new_images
        else:
            out.pop('images', None)
    behavior = out.get('behaviorHints')
    if isinstance(behavior, dict):
        new_behavior = dict(behavior)
        for key in _ART_OVERRIDE_KEYS:
            new_behavior.pop(key, None)
        if new_behavior:
            out['behaviorHints'] = new_behavior
        else:
            out.pop('behaviorHints', None)
    return out


def _mark_source(meta, source_id='', provider_id='', strict_art=False, virtual_key=''):
    """Stamp meta so downstream artwork code can respect the user's picker.

    Kodi listing/detail/playback flows may re-score or re-cache metadata after
    the catalog page. These private fields let plugin.py know that the artwork
    already came from a selected source and must not be enriched/fallen back to
    another source later.
    """
    out = dict(meta or {})
    if source_id:
        out['_dexhub_meta_source_id'] = str(source_id or '')
    if provider_id:
        out['_dexhub_meta_provider_id'] = str(provider_id or '')
    if virtual_key:
        out['_dexhub_meta_virtual_key'] = str(virtual_key or '')
    if strict_art:
        out['_dexhub_art_strict'] = '1'
    return out


def _merge_meta(base_meta, replacement, strict_art=False, source_id='', provider_id='', virtual_key=''):
    if not replacement:
        merged = _drop_art_fields(base_meta) if strict_art else dict(base_meta or {})
        return _mark_source(merged, source_id=source_id, provider_id=provider_id, strict_art=strict_art, virtual_key=virtual_key)
    merged = _drop_art_fields(base_meta) if strict_art else dict(base_meta or {})
    for key in ('poster', 'posterUrl', 'posterURL', 'thumbnail', 'background', 'banner', 'logo', 'clearlogo', 'clearart', 'description',
                'genres', 'releaseInfo', 'imdbRating', 'cast', 'director', 'year',
                'fanart', 'landscape', 'backdrop', 'thumb', 'images', 'behaviorHints', 'name', 'title',
                'videos', 'trailers', 'links', 'runtime', 'released', 'country', 'certification'):
        val = replacement.get(key)
        if val not in (None, '', [], {}):
            # Clearlogo / logo: never overwrite a good existing value with
            # something empty — the user sees the clearlogo change every time
            # they switch meta sources, which feels broken. Only update it
            # if the replacement actually has a richer value.
            if key in ('clearlogo', 'logo') and merged.get(key) and not val:
                continue
            merged[key] = val
    return _mark_source(merged, source_id=source_id, provider_id=provider_id, strict_art=strict_art, virtual_key=virtual_key)


def is_native_for(provider_id):
    """Public helper: True iff the user explicitly asked for native meta."""
    return get_meta_source_for(provider_id) == 'native'


def override_virtual_meta(target_key, media_type, meta):
    """Apply a metadata override for non-provider targets (Continue Watching,
    Trakt collection entries) where there is no concrete Stremio provider row
    to attach the mapping to."""
    if not target_key:
        return meta
    meta = dict(meta or {})
    ids = extract_ids(meta)
    if not any(ids.values()):
        return meta

    source_id = get_meta_source_for(target_key)
    if source_id == 'native':
        return meta

    replacement = None
    if source_id in ('', 'auto'):
        replacement = _fetch_from_tmdb_helper(ids, meta, media_type)
        if not replacement:
            for src in list_available_meta_sources():
                if src.get('kind') == 'stremio':
                    replacement = _fetch_from_stremio(src.get('id') or '', media_type, ids)
                    if replacement:
                        break
    elif source_id == 'tmdb_helper':
        replacement = _fetch_from_tmdb_helper(ids, meta, media_type)
    else:
        # Explicit source means explicit source: do not silently fall back to
        # TMDb Helper/API when the selected meta add-on has no artwork.
        replacement = _fetch_from_stremio(source_id, media_type, ids)

    explicit = source_id not in ('', 'auto')
    return _merge_meta(meta, replacement, strict_art=explicit, source_id=source_id, virtual_key=target_key)


def override_meta(provider, media_type, meta):
    """Apply per-provider metadata override.

    'native' is treated as a STRICT no-op — the provider's own meta is
    returned untouched, even if it looks sparse. This is what 'احترام
    اختيار المستخدم' means for users that explicitly prefer Plexio/DexBridge
    meta because their setup already has rich local artwork.
    """
    if not provider:
        return meta
    source_id = get_meta_source_for(provider.get('id'))
    if source_id == 'native' or (source_id == 'auto' and _provider_is_plexio(provider)):
        # Plexio already behaves like a Stremio metadata provider and carries
        # tokenized Plex artwork in its catalog/meta payload. In auto/native
        # mode, never replace it with TMDb/Cinemeta. Explicit selections below
        # still override 100%.
        return _mark_source(meta, source_id='native', provider_id=(provider.get('id') or ''), strict_art=False)

    ids = extract_ids(meta)
    if not any(ids.values()):
        return meta

    # 'auto' → replace only for Plex/Emby (unreliable meta), leave others native.
    if source_id == 'auto':
        if not provider_is_stream_only(provider):
            return meta
        replacement = None
        for src in list_available_meta_sources():
            if src['kind'] == 'stremio':
                replacement = _fetch_from_stremio(src['id'], media_type, ids)
                if replacement:
                    break
        if not replacement:
            replacement = _fetch_from_tmdb_helper(ids, meta, media_type)
    elif source_id == 'tmdb_helper':
        replacement = _fetch_from_tmdb_helper(ids, meta, media_type)
    else:
        # Explicit source means explicit source: do not silently fall back to
        # TMDb Helper/API when the selected meta add-on has no artwork.
        replacement = _fetch_from_stremio(source_id, media_type, ids)

    explicit = source_id not in ('', 'auto')
    if not replacement and explicit:
        # The user's explicitly-selected source had no art for this item.
        # As a last resort, try tmdb_direct API so the user sees SOME poster
        # instead of a blue default square. This only fires for explicit
        # picks (not auto), so it doesn't re-enrich native/auto artwork.
        replacement = _fetch_from_tmdb_helper(ids, meta, media_type)
    if not replacement:
        # Explicit source means strict source: if the selected source has no
        # artwork/meta for this item, do not leak the provider's old poster.
        return _merge_meta(meta, None, strict_art=explicit, source_id=source_id, provider_id=provider.get('id') or '')
    return _merge_meta(meta, replacement, strict_art=explicit, source_id=source_id, provider_id=provider.get('id') or '')


def override_metas_batch(provider, media_type, metas):
    if not provider or not metas:
        return metas
    source_id = get_meta_source_for(provider.get('id'))
    # Short-circuit: native = strict no-op. Plexio is also native in auto
    # because its configured Stremio manifest is already the authoritative
    # metadata/art source (same as Stremio).
    if source_id == 'native' or (source_id == 'auto' and _provider_is_plexio(provider)):
        return [_mark_source(m, source_id='native', provider_id=(provider.get('id') or ''), strict_art=False) for m in (metas or [])]
    if source_id == 'auto' and not provider_is_stream_only(provider):
        return metas

    from .dexhub.client import run_parallel

    # When the user picks an EXPLICIT source (tmdb_helper or a specific
    # Stremio meta addon), every item must go through override_meta —
    # short-circuiting on _meta_is_good_enough makes the picker silently
    # do nothing for items whose original meta already had a poster +
    # description (the typical Plex/Plexio case). The "good_enough" skip
    # is only an optimisation valid for `auto` mode, where the goal is to
    # avoid redundant lookups; with an explicit pick the user is asking
    # us to replace the meta regardless.
    skip_good_enough = (source_id == 'auto')

    def _one(m):
        try:
            if skip_good_enough and _meta_is_good_enough(m):
                return m
            return override_meta(provider, media_type, m)
        except Exception:
            return m

    results = run_parallel(_one, metas)
    return [r if not isinstance(r, Exception) else original
            for original, r in results]
