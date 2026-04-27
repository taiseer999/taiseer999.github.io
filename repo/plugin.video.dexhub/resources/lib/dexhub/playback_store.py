# -*- coding: utf-8 -*-
import os
import sqlite3
import time

from .common import profile_path

DB_PATH = os.path.join(profile_path(), 'playback.db')
_DB_READY = False


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
    except Exception:
        pass
    return conn


def _ensure_db():
    global _DB_READY
    if _DB_READY:
        return
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS playback (
            media_type TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            video_id TEXT NOT NULL,
            title TEXT,
            provider_name TEXT,
            poster TEXT,
            background TEXT,
            clearlogo TEXT,
            season INTEGER,
            episode INTEGER,
            position REAL,
            duration REAL,
            percent REAL,
            stream_url TEXT,
            event_type TEXT,
            updated_at INTEGER,
            PRIMARY KEY (media_type, canonical_id, video_id)
        )
        """
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_playback_updated ON playback(updated_at DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_playback_percent ON playback(percent)')
    conn.commit()
    conn.close()
    _DB_READY = True


def upsert_entry(media_type, canonical_id, video_id, title, provider_name, poster, background, clearlogo, season, episode, position, duration, percent, stream_url, event_type, ext_updated_at=None):
    """Insert or update a continue-watching row.

    `ext_updated_at` allows the caller to pass an authoritative timestamp
    (e.g. Trakt's `paused_at`) instead of "now". This keeps Continue Watching
    ordering STABLE across imports — the previous behavior used time.time()
    on every Trakt sync, so the home row reshuffled every few minutes.

    For local playback events, leave it None and we fall back to time.time().
    For local rows we only bump updated_at when the row is genuinely "new
    activity" (position has actually advanced, or this is a freshly inserted
    row); pure UI re-saves no longer reshuffle the row.
    """
    ts = int(ext_updated_at) if ext_updated_at else int(time.time())
    _ensure_db()
    conn = _connect()
    # We avoid clobbering updated_at on no-op updates: when the new position
    # is within ~30s of the stored one, keep the existing updated_at so the
    # home row doesn't bounce around when service.py re-saves the same point.
    existing = conn.execute(
        "SELECT position, updated_at FROM playback WHERE media_type=? AND canonical_id=? AND video_id=?",
        (media_type or '', canonical_id or '', video_id or ''),
    ).fetchone()
    if existing and ext_updated_at is None:
        try:
            old_pos = float(existing[0] or 0.0)
            if abs(float(position or 0.0) - old_pos) < 30.0:
                ts = int(existing[1] or ts)
        except Exception:
            pass
    conn.execute(
        """
        INSERT INTO playback (
            media_type, canonical_id, video_id, title, provider_name, poster, background, clearlogo,
            season, episode, position, duration, percent, stream_url, event_type, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(media_type, canonical_id, video_id)
        DO UPDATE SET
            title=excluded.title,
            provider_name=excluded.provider_name,
            poster=excluded.poster,
            background=excluded.background,
            clearlogo=excluded.clearlogo,
            season=excluded.season,
            episode=excluded.episode,
            position=excluded.position,
            duration=excluded.duration,
            percent=excluded.percent,
            stream_url=excluded.stream_url,
            event_type=excluded.event_type,
            updated_at=excluded.updated_at
        """,
        (
            media_type, canonical_id, video_id, title, provider_name, poster, background, clearlogo,
            season, episode, position, duration, percent, stream_url, event_type, ts
        ),
    )
    conn.commit()
    conn.close()


def update_art(media_type, canonical_id, video_id, poster='', background='', clearlogo=''):
    """Update artwork only without touching updated_at so Continue Watching
    ordering stays stable until the user actually watches something new."""
    _ensure_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE playback
        SET
            poster=CASE WHEN ? != '' THEN ? ELSE poster END,
            background=CASE WHEN ? != '' THEN ? ELSE background END,
            clearlogo=CASE WHEN ? != '' THEN ? ELSE clearlogo END
        WHERE media_type=? AND canonical_id=? AND video_id=?
        """,
        (
            poster or '', poster or '',
            background or '', background or '',
            clearlogo or '', clearlogo or '',
            media_type or '', canonical_id or '', video_id or '',
        ),
    )
    conn.commit()
    conn.close()


def list_continue_items(limit=50):
    _ensure_db()
    conn = _connect()
    rows = conn.execute(
        """
        SELECT media_type, canonical_id, video_id, title, provider_name, poster, background, clearlogo,
               season, episode, position, duration, percent, updated_at
        FROM playback
        WHERE percent < 95.0
        ORDER BY updated_at DESC, title COLLATE NOCASE ASC, canonical_id ASC, video_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    out = []
    for row in rows:
        out.append({
            'media_type': row[0], 'canonical_id': row[1], 'video_id': row[2], 'title': row[3],
            'provider_name': row[4], 'poster': row[5], 'background': row[6], 'clearlogo': row[7],
            'season': row[8], 'episode': row[9], 'position': row[10], 'duration': row[11],
            'percent': row[12], 'updated_at': row[13],
        })
    return out


def list_recent_items(limit=200, media_types=None, include_watched=True):
    """Return recent playback rows without forcing the Continue Watching filter.

    Used by Next Up and diagnostics where fully watched episodes must remain
    visible as the base for finding the *next* episode.
    """
    _ensure_db()
    conn = _connect()
    where = []
    params = []
    if media_types:
        mts = [str(x or '').strip().lower() for x in media_types if str(x or '').strip()]
        if mts:
            where.append('media_type IN (%s)' % ','.join(['?'] * len(mts)))
            params.extend(mts)
    if not include_watched:
        where.append('percent < 95.0')
    sql = """
        SELECT media_type, canonical_id, video_id, title, provider_name, poster, background, clearlogo,
               season, episode, position, duration, percent, updated_at, event_type, stream_url
        FROM playback
    """
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += " ORDER BY updated_at DESC, title COLLATE NOCASE ASC, canonical_id ASC, video_id ASC LIMIT ?"
    params.append(int(limit or 200))
    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    out = []
    for row in rows:
        out.append({
            'media_type': row[0], 'canonical_id': row[1], 'video_id': row[2], 'title': row[3],
            'provider_name': row[4], 'poster': row[5], 'background': row[6], 'clearlogo': row[7],
            'season': row[8], 'episode': row[9], 'position': row[10], 'duration': row[11],
            'percent': row[12], 'updated_at': row[13], 'event_type': row[14], 'stream_url': row[15],
        })
    return out


def delete_entry(media_type, canonical_id, video_id):
    _ensure_db()
    conn = _connect()
    conn.execute(
        "DELETE FROM playback WHERE media_type=? AND canonical_id=? AND video_id=?",
        (media_type or '', canonical_id or '', video_id or ''),
    )
    conn.commit()
    conn.close()


def mark_watched(media_type, canonical_id, video_id):
    """Set percent=100 so the row is filtered out of continue_watching without deleting it."""
    import time as _t
    _ensure_db()
    conn = _connect()
    conn.execute(
        "UPDATE playback SET percent=100.0, updated_at=? WHERE media_type=? AND canonical_id=? AND video_id=?",
        (int(_t.time()), media_type or '', canonical_id or '', video_id or ''),
    )
    conn.commit()
    conn.close()
