# -*- coding: utf-8 -*-
import json
import os
import sqlite3
import time
import uuid

from .common import profile_path

DB_PATH = os.path.join(profile_path(), 'cache.db')

_MEM = {}
_MEM_ORDER = []
_MEM_MAX = 256


def _mem_put(kind, cache_key, payload):
    key = '%s:%s' % (kind or '', cache_key or '')
    if key not in _MEM:
        _MEM_ORDER.append(key)
    _MEM[key] = payload
    while len(_MEM_ORDER) > _MEM_MAX:
        old = _MEM_ORDER.pop(0)
        _MEM.pop(old, None)


def _mem_get(kind, cache_key):
    return _MEM.get('%s:%s' % (kind or '', cache_key or ''))


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache_items (
            cache_key TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_kind_created ON cache_items(kind, created_at DESC)")
    return conn


def put(kind, payload, ttl_hours=24):
    conn = _conn()
    now = int(time.time())
    key = uuid.uuid4().hex
    conn.execute(
        "INSERT OR REPLACE INTO cache_items(cache_key, kind, payload, created_at) VALUES(?,?,?,?)",
        (key, kind, json.dumps(payload, ensure_ascii=False), now),
    )
    cutoff = now - int(ttl_hours * 3600)
    conn.execute("DELETE FROM cache_items WHERE created_at < ?", (cutoff,))
    conn.commit()
    conn.close()
    _mem_put(kind, key, payload)
    return key


def get(kind, cache_key):
    cached = _mem_get(kind, cache_key)
    if cached is not None:
        return cached
    conn = _conn()
    row = conn.execute("SELECT payload FROM cache_items WHERE kind=? AND cache_key=?", (kind, cache_key)).fetchone()
    conn.close()
    if not row:
        return None
    try:
        payload = json.loads(row[0])
        _mem_put(kind, cache_key, payload)
        return payload
    except Exception:
        return None


def update(kind, cache_key, payload):
    if not cache_key:
        return None
    conn = _conn()
    now = int(time.time())
    conn.execute(
        "INSERT OR REPLACE INTO cache_items(cache_key, kind, payload, created_at) VALUES(?,?,?,?)",
        (cache_key, kind, json.dumps(payload, ensure_ascii=False), now),
    )
    conn.commit()
    conn.close()
    _mem_put(kind, cache_key, payload)
    return cache_key


def clear_all(kind=None):
    conn = _conn()
    try:
        if kind:
            conn.execute("DELETE FROM cache_items WHERE kind=?", (kind,))
        else:
            conn.execute("DELETE FROM cache_items")
        conn.commit()
    finally:
        conn.close()
    if kind:
        prefix = '%s:' % (kind or '')
        for key in list(_MEM.keys()):
            if key.startswith(prefix):
                _MEM.pop(key, None)
        _MEM_ORDER[:] = [k for k in _MEM_ORDER if not k.startswith(prefix)]
    else:
        _MEM.clear()
        _MEM_ORDER[:] = []
