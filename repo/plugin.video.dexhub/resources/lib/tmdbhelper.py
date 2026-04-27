# -*- coding: utf-8 -*-
import re
import sqlite3
from functools import lru_cache

import xbmcvfs

# Bug fix: previously every image (poster/fanart/logo) was fetched at
# /t/p/original — full-resolution 2000+px files (often 500KB-2MB each)
# downloaded just to be displayed in a 320x480 poster slot. Use TMDb's
# CDN-served sized variants to drop bandwidth ~95% with no visible
# quality loss for Kodi display sizes.
_TMDB_IMAGE_BASE_POSTER = 'https://image.tmdb.org/t/p/w500'
_TMDB_IMAGE_BASE_BACKDROP = 'https://image.tmdb.org/t/p/w1280'
_TMDB_IMAGE_BASE_LOGO = 'https://image.tmdb.org/t/p/w500'
# Backwards-compatible alias for any external caller that imports the old name.
_TMDB_IMAGE_BASE = _TMDB_IMAGE_BASE_POSTER
_DB_PATHS = [
    'special://userdata/addon_data/plugin.video.themoviedb.helper/database_10/ItemDetails.db',
    'special://userdata/addon_data/plugin.video.themoviedb.helper/database_09/ItemDetails.db',
    'special://userdata/addon_data/plugin.video.themoviedb.helper/database_08/ItemDetails.db',
    'special://userdata/addon_data/plugin.video.themoviedb.helper/database_07/ItemDetails.db',
    'special://userdata/addon_data/plugin.video.themoviedb.helper/database_06/ItemDetails.db',
    'special://userdata/addon_data/plugin.video.themoviedb.helper/database_05/ItemDetails.db',
]
_CACHE = {}
_CACHE_ORDER = []
_CACHE_MAX = 1024


def _cache_put(key, value):
    if key in _CACHE:
        return
    _CACHE[key] = value
    _CACHE_ORDER.append(key)
    if len(_CACHE_ORDER) > _CACHE_MAX:
        old = _CACHE_ORDER.pop(0)
        _CACHE.pop(old, None)


@lru_cache(maxsize=1)
def _active_db_path():
    """Return the first existing TMDb Helper DB path. Cached for the session
    since these paths don't change at runtime."""
    for db in _DB_PATHS:
        try:
            path = xbmcvfs.translatePath(db)
            if xbmcvfs.exists(path):
                return path
        except Exception:
            continue
    return ''


def _normalize_media_type(media_type):
    if media_type in ['tvshow', 'episode', 'season', 'series', 'show', 'tv']:
        return 'tv'
    return 'movie'


def _to_image_url(icon, kind='poster'):
    """Build a sized TMDb URL. `kind` ∈ {'poster','backdrop','logo'}."""
    icon = str(icon or '').strip()
    if icon and '](' in icon:
        icon = icon.split('](')[-1].replace(')', '')
    if not icon:
        return ''
    if icon.startswith('http'):
        return icon
    if kind == 'backdrop':
        return _TMDB_IMAGE_BASE_BACKDROP + icon
    if kind == 'logo':
        return _TMDB_IMAGE_BASE_LOGO + icon
    return _TMDB_IMAGE_BASE_POSTER + icon


# Map TMDb Helper db `art.type` values to our size kind.
_ART_TYPE_KIND = {
    'posters': 'poster', 'thumb': 'poster',
    'fanarts': 'backdrop', 'landscape': 'backdrop',
    'logos': 'logo',
}


def _query_art_for_parent(conn, parent_id, art_type):
    cur = conn.cursor()
    cur.execute(
        "SELECT icon FROM art WHERE type=? AND parent_id=? ORDER BY CASE WHEN iso_language='en' THEN 0 ELSE 1 END, rating DESC LIMIT 1",
        (art_type, parent_id),
    )
    row = cur.fetchone()
    kind = _ART_TYPE_KIND.get(art_type, 'poster')
    return _to_image_url(row[0] if row and row[0] else '', kind=kind)


def _table_columns(conn, table):
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(%s)" % table)
        return [row[1] for row in cur.fetchall()]
    except Exception:
        return []


def _find_title_columns(cols):
    candidates = ['title', 'name', 'label', 'originaltitle', 'showname']
    return [c for c in candidates if c in cols]


def _find_tmdb_column(cols):
    for key in ('tmdb_id', 'tmdb'):
        if key in cols:
            return key
    return ''


def _find_media_type_column(cols):
    for key in ('media_type', 'type'):
        if key in cols:
            return key
    return ''


def _find_year_column(cols):
    for key in ('year', 'release_year'):
        if key in cols:
            return key
    return ''


def _resolve_tmdb_from_imdb(conn, imdb_id, media_type):
    if not imdb_id:
        return ''
    mt = _normalize_media_type(media_type)
    queries = [
        ("SELECT tmdb_id FROM unique_ids WHERE imdb_id=? LIMIT 1", (imdb_id,)),
        ("SELECT tmdb FROM unique_ids WHERE imdb=? LIMIT 1", (imdb_id,)),
        ("SELECT tmdb_id FROM item_ids WHERE imdb_id=? LIMIT 1", (imdb_id,)),
        ("SELECT tmdb FROM item_ids WHERE imdb=? LIMIT 1", (imdb_id,)),
        ("SELECT tmdb_id FROM items WHERE imdb_id=? AND media_type=? LIMIT 1", (imdb_id, mt)),
        ("SELECT tmdb_id FROM items WHERE imdb_id=? LIMIT 1", (imdb_id,)),
    ]
    for sql, params in queries:
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            value = str(row[0]) if row and row[0] not in (None, '') else ''
            if value and value.isdigit():
                return value
        except Exception:
            continue
    return ''


def _resolve_tmdb_from_title(conn, title, media_type, year=''):
    title = str(title or '').strip()
    if not title:
        return ''
    mt = _normalize_media_type(media_type)
    norm = re.sub(r'\s+', ' ', title).strip().lower()
    for table in ('items', 'item_ids', 'unique_ids'):
        cols = _table_columns(conn, table)
        if not cols:
            continue
        title_cols = _find_title_columns(cols)
        tmdb_col = _find_tmdb_column(cols)
        if not title_cols or not tmdb_col:
            continue
        mt_col = _find_media_type_column(cols)
        year_col = _find_year_column(cols)
        for tc in title_cols:
            sql = "SELECT %s FROM %s WHERE lower(%s)=?" % (tmdb_col, table, tc)
            params = [norm]
            if mt_col:
                sql += " AND %s=?" % mt_col
                params.append(mt)
            if year_col and str(year or '').isdigit():
                sql += " AND %s=?" % year_col
                params.append(int(year))
            sql += " LIMIT 1"
            try:
                cur = conn.cursor()
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                value = str(row[0]) if row and row[0] not in (None, '') else ''
                if value and value.isdigit():
                    return value
            except Exception:
                continue
    return ''




def _find_column(cols, *names):
    for name in names:
        if name in cols:
            return name
    return ''


def get_external_ids_from_db(tmdb_id='', media_type='movie', imdb_id='', tvdb_id='', title='', year=''):
    """Resolve IMDb/TMDb/TVDb ids from TMDb Helper's local database.

    This is intentionally read-only and API-free.  Stremio stream addons such
    as Torrentio/AIOStreams usually resolve best with IMDb `tt...` ids, while
    Kodi/TMDb Helper handoffs often start as `tmdb:123`.  Stremio itself sends
    the configured addon the canonical id that the Stremio catalogue has; Dex
    Hub must recreate that by enriching ids locally before calling /stream.
    """
    mt = _normalize_media_type(media_type)
    tmdb_id = str(tmdb_id or '').strip()
    imdb_id = str(imdb_id or '').strip()
    tvdb_id = str(tvdb_id or '').strip()
    cache_key = 'ids:%s:%s:%s:%s:%s:%s' % (mt, tmdb_id, imdb_id, tvdb_id, title or '', year or '')
    if cache_key in _CACHE:
        return dict(_CACHE[cache_key] or {})
    out = {'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': tvdb_id}
    path = _active_db_path()
    if not path:
        _cache_put(cache_key, dict(out))
        return out
    try:
        conn = sqlite3.connect(path)
        try:
            # Prefer direct id tables.  Table/column names vary across TMDb
            # Helper versions, so discover columns and query defensively.
            for table in ('unique_ids', 'item_ids', 'items'):
                cols = _table_columns(conn, table)
                if not cols:
                    continue
                tmdb_col = _find_column(cols, 'tmdb_id', 'tmdb')
                imdb_col = _find_column(cols, 'imdb_id', 'imdb')
                tvdb_col = _find_column(cols, 'tvdb_id', 'tvdb')
                mt_col = _find_media_type_column(cols)
                select_cols = []
                for col in (tmdb_col, imdb_col, tvdb_col):
                    if col and col not in select_cols:
                        select_cols.append(col)
                if not select_cols:
                    continue

                where = []
                params = []
                if out.get('tmdb_id') and tmdb_col:
                    where.append('%s=?' % tmdb_col)
                    params.append(out['tmdb_id'])
                if out.get('imdb_id') and imdb_col:
                    where.append('%s=?' % imdb_col)
                    params.append(out['imdb_id'])
                if out.get('tvdb_id') and tvdb_col:
                    where.append('%s=?' % tvdb_col)
                    params.append(out['tvdb_id'])
                if not where:
                    continue
                sql = 'SELECT %s FROM %s WHERE (%s)' % (', '.join(select_cols), table, ' OR '.join(where))
                if mt_col:
                    sql += ' AND %s=?' % mt_col
                    params.append(mt)
                sql += ' LIMIT 1'
                try:
                    cur = conn.cursor()
                    cur.execute(sql, tuple(params))
                    row = cur.fetchone()
                except Exception:
                    row = None
                if not row:
                    continue
                values = dict(zip(select_cols, row))
                if tmdb_col and not out.get('tmdb_id'):
                    val = str(values.get(tmdb_col) or '').strip()
                    if val and val.isdigit():
                        out['tmdb_id'] = val
                if imdb_col and not out.get('imdb_id'):
                    val = str(values.get(imdb_col) or '').strip()
                    if val:
                        out['imdb_id'] = val if val.startswith('tt') else ('tt%s' % val if val.isdigit() else val)
                if tvdb_col and not out.get('tvdb_id'):
                    val = str(values.get(tvdb_col) or '').strip()
                    if val and val.isdigit():
                        out['tvdb_id'] = val
                if out.get('tmdb_id') and out.get('imdb_id'):
                    break

            # Title fallback for older databases that don't have populated id
            # columns in unique_ids/item_ids.
            if (not out.get('imdb_id') or not out.get('tmdb_id')) and title:
                norm = re.sub(r'\s+', ' ', str(title or '')).strip().lower()
                for table in ('items', 'item_ids', 'unique_ids'):
                    cols = _table_columns(conn, table)
                    if not cols:
                        continue
                    title_cols = _find_title_columns(cols)
                    if not title_cols:
                        continue
                    tmdb_col = _find_column(cols, 'tmdb_id', 'tmdb')
                    imdb_col = _find_column(cols, 'imdb_id', 'imdb')
                    tvdb_col = _find_column(cols, 'tvdb_id', 'tvdb')
                    mt_col = _find_media_type_column(cols)
                    year_col = _find_year_column(cols)
                    select_cols = [c for c in (tmdb_col, imdb_col, tvdb_col) if c]
                    if not select_cols:
                        continue
                    for tc in title_cols:
                        sql = 'SELECT %s FROM %s WHERE lower(%s)=?' % (', '.join(select_cols), table, tc)
                        params = [norm]
                        if mt_col:
                            sql += ' AND %s=?' % mt_col
                            params.append(mt)
                        if year_col and str(year or '').isdigit():
                            sql += ' AND %s=?' % year_col
                            params.append(int(year))
                        sql += ' LIMIT 1'
                        try:
                            cur = conn.cursor()
                            cur.execute(sql, tuple(params))
                            row = cur.fetchone()
                        except Exception:
                            row = None
                        if not row:
                            continue
                        values = dict(zip(select_cols, row))
                        if tmdb_col and not out.get('tmdb_id'):
                            val = str(values.get(tmdb_col) or '').strip()
                            if val and val.isdigit():
                                out['tmdb_id'] = val
                        if imdb_col and not out.get('imdb_id'):
                            val = str(values.get(imdb_col) or '').strip()
                            if val:
                                out['imdb_id'] = val if val.startswith('tt') else ('tt%s' % val if val.isdigit() else val)
                        if tvdb_col and not out.get('tvdb_id'):
                            val = str(values.get(tvdb_col) or '').strip()
                            if val and val.isdigit():
                                out['tvdb_id'] = val
                        if out.get('tmdb_id') and out.get('imdb_id'):
                            break
                    if out.get('tmdb_id') and out.get('imdb_id'):
                        break
        finally:
            conn.close()
    except Exception:
        pass
    _cache_put(cache_key, dict(out))
    return out

def get_art_bundle_from_db(tmdb_id='', media_type='movie', imdb_id='', title='', year=''):
    media_type = _normalize_media_type(media_type)
    cache_key = 'bundle:%s:%s:%s:%s:%s' % (media_type, tmdb_id or '', imdb_id or '', title or '', year or '')
    if cache_key in _CACHE:
        return dict(_CACHE[cache_key])

    bundle = {'poster': '', 'fanart': '', 'landscape': '', 'clearlogo': ''}
    path = _active_db_path()
    if path:
        try:
            conn = sqlite3.connect(path)
            try:
                resolved_tmdb = tmdb_id or _resolve_tmdb_from_imdb(conn, imdb_id, media_type) or _resolve_tmdb_from_title(conn, title, media_type, year)
                parent_ids = []
                if resolved_tmdb:
                    parent_ids.append('%s.%s' % (media_type, resolved_tmdb))
                if imdb_id:
                    parent_ids.extend([
                        '%s.%s' % (media_type, imdb_id),
                        '%s.imdb:%s' % (media_type, imdb_id),
                        imdb_id,
                    ])
                for parent_id in parent_ids:
                    if not bundle['poster']:
                        bundle['poster'] = _query_art_for_parent(conn, parent_id, 'posters') or _query_art_for_parent(conn, parent_id, 'thumb')
                    if not bundle['fanart']:
                        bundle['fanart'] = _query_art_for_parent(conn, parent_id, 'fanarts')
                    if not bundle['landscape']:
                        bundle['landscape'] = _query_art_for_parent(conn, parent_id, 'landscape')
                    if not bundle['clearlogo']:
                        bundle['clearlogo'] = _query_art_for_parent(conn, parent_id, 'logos')
                    if bundle['poster'] and bundle['fanart'] and bundle['clearlogo']:
                        break
            finally:
                conn.close()
        except Exception:
            pass
    if not bundle['landscape']:
        bundle['landscape'] = bundle['fanart']
    _cache_put(cache_key, dict(bundle))
    return bundle


def get_clearlogo_from_db(tmdb_id='', media_type='movie', imdb_id=''):
    return (get_art_bundle_from_db(tmdb_id=tmdb_id, media_type=media_type, imdb_id=imdb_id) or {}).get('clearlogo', '')


def _query_title_for_parent(conn, media_type, tmdb_id='', imdb_id='', title='', year=''):
    resolved_tmdb = str(tmdb_id or '').strip() or _resolve_tmdb_from_imdb(conn, imdb_id, media_type) or _resolve_tmdb_from_title(conn, title, media_type, year)
    candidates = []
    if resolved_tmdb:
        candidates.append((resolved_tmdb, _normalize_media_type(media_type)))
    cols = _table_columns(conn, 'items')
    if not cols:
        return ''
    title_cols = [c for c in ('originaltitle', 'originalname', 'title', 'name', 'label', 'showname') if c in cols]
    if not title_cols:
        return ''
    tmdb_col = _find_tmdb_column(cols)
    mt_col = _find_media_type_column(cols)
    if tmdb_col and candidates:
        for tmdb_val, mt in candidates:
            for tc in title_cols:
                sql = "SELECT %s FROM items WHERE %s=?" % (tc, tmdb_col)
                params = [tmdb_val]
                if mt_col:
                    sql += " AND %s=?" % mt_col
                    params.append(mt)
                sql += " LIMIT 1"
                try:
                    cur = conn.cursor()
                    cur.execute(sql, tuple(params))
                    row = cur.fetchone()
                    value = str(row[0]).strip() if row and row[0] not in (None, '') else ''
                    if value:
                        return value
                except Exception:
                    continue
    # Last resort: title-based lookup, prefer originaltitle/originalname when present.
    norm = re.sub(r'\s+', ' ', str(title or '')).strip().lower()
    if norm:
        for tc_match in [c for c in ('title', 'name', 'label', 'showname') if c in cols]:
            for tc_out in title_cols:
                sql = "SELECT %s FROM items WHERE lower(%s)=?" % (tc_out, tc_match)
                params = [norm]
                if mt_col:
                    sql += " AND %s=?" % mt_col
                    params.append(_normalize_media_type(media_type))
                sql += " LIMIT 1"
                try:
                    cur = conn.cursor()
                    cur.execute(sql, tuple(params))
                    row = cur.fetchone()
                    value = str(row[0]).strip() if row and row[0] not in (None, '') else ''
                    if value:
                        return value
                except Exception:
                    continue
    return ''


def get_title_from_db(tmdb_id='', media_type='movie', imdb_id='', title='', year=''):
    cache_key = 'title:%s:%s:%s:%s:%s' % (_normalize_media_type(media_type), tmdb_id or '', imdb_id or '', title or '', year or '')
    if cache_key in _CACHE:
        return _CACHE[cache_key] or ''
    value = ''
    path = _active_db_path()
    if path:
        try:
            conn = sqlite3.connect(path)
            try:
                value = _query_title_for_parent(conn, media_type, tmdb_id=tmdb_id, imdb_id=imdb_id, title=title, year=year)
            finally:
                conn.close()
        except Exception:
            value = ''
    _cache_put(cache_key, value or '')
    return value or ''
