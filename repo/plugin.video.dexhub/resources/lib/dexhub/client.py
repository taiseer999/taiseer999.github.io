# -*- coding: utf-8 -*-
import gzip
import hashlib
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import Request, urlopen

from .common import addon, profile_path

HTTP_CACHE_DIR = os.path.join(profile_path(), 'http_cache')


def _get_setting(key, default):
    try:
        raw = addon().getSetting(key) or ''
        return raw if raw != '' else default
    except Exception:
        return default


def _get_int_setting(key, default):
    try:
        return max(0, int(float(_get_setting(key, str(default)))))
    except Exception:
        return default


def timeout_seconds():
    return max(5, _get_int_setting('timeout', 20))


def catalog_ttl():
    return _get_int_setting('catalog_cache_ttl', 120)


def meta_ttl():
    return _get_int_setting('meta_cache_ttl', 3600)


def stream_ttl():
    # Very short in-memory cache for source discovery only. Avoids re-hitting
    # the same addon when the user backs out and re-opens the source window.
    return min(15, max(4, _get_int_setting('catalog_cache_ttl', 120)))


def fast_timeout(kind='generic'):
    base = timeout_seconds()
    if kind == 'stream':
        return max(4, min(base, 8))
    if kind == 'meta':
        return max(4, min(base, 8))
    if kind == 'search':
        return max(5, min(base, 10))
    return base


def parallel_workers():
    return max(2, min(12, _get_int_setting('parallel_workers', 8)))


def gzip_enabled():
    raw = (_get_setting('http_gzip', 'true') or 'true').lower()
    return raw not in ('false', '0', 'no')


def _cache_file(url):
    os.makedirs(HTTP_CACHE_DIR, exist_ok=True)
    return os.path.join(HTTP_CACHE_DIR, hashlib.sha1(url.encode('utf-8')).hexdigest() + '.json')


# In-memory HTTP cache layer — avoids disk I/O for hot URLs within a single
# Python invocation (e.g. catalog opens, then back, then opens again).
# Bounded to 256 entries, FIFO eviction.
_HTTP_MEM = {}
_HTTP_MEM_ORDER = []
_HTTP_MEM_MAX = 256


def _mem_cache_get(url, ttl_seconds):
    entry = _HTTP_MEM.get(url)
    if not entry:
        return None
    saved_at, data = entry
    if (time.time() - saved_at) > ttl_seconds:
        _HTTP_MEM.pop(url, None)
        return None
    return data


def _mem_cache_put(url, data):
    if url in _HTTP_MEM:
        _HTTP_MEM[url] = (time.time(), data)
        return
    _HTTP_MEM[url] = (time.time(), data)
    _HTTP_MEM_ORDER.append(url)
    if len(_HTTP_MEM_ORDER) > _HTTP_MEM_MAX:
        old = _HTTP_MEM_ORDER.pop(0)
        _HTTP_MEM.pop(old, None)


def purge_meta_cache():
    """Drop ALL cached responses for /meta/ URLs.

    Called after the user changes a meta-source mapping so the next
    catalog/details page actually re-fetches and applies the new source
    instead of serving yesterday's cached art and description.

    Cheap: meta URLs typically number in the tens, not thousands.
    Disk + memory layers both purged.
    """
    # In-memory layer
    drop_keys = [k for k in list(_HTTP_MEM.keys()) if '/meta/' in k]
    for k in drop_keys:
        _HTTP_MEM.pop(k, None)
    try:
        _HTTP_MEM_ORDER[:] = [u for u in _HTTP_MEM_ORDER if u not in set(drop_keys)]
    except Exception:
        pass
    # Disk layer — we hash URLs into filenames, so we can't tell from the
    # filename alone whether it's a meta URL. Just nuke the directory; the
    # next request rebuilds. The cost is one extra HTTP roundtrip per
    # (catalog/stream/manifest) URL the user happens to revisit, which is
    # acceptable for the rarity of the meta-picker change action.
    try:
        if os.path.isdir(HTTP_CACHE_DIR):
            for name in os.listdir(HTTP_CACHE_DIR):
                try:
                    os.remove(os.path.join(HTTP_CACHE_DIR, name))
                except Exception:
                    continue
    except Exception:
        pass


def _read_cache(url, ttl_seconds, memory_only=False):
    if ttl_seconds <= 0:
        return None
    # In-memory first (no disk hit)
    cached = _mem_cache_get(url, ttl_seconds)
    if cached is not None:
        return cached
    if memory_only:
        return None
    path = _cache_file(url)
    try:
        if os.path.exists(path) and (time.time() - os.path.getmtime(path) <= ttl_seconds):
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            _mem_cache_put(url, data)
            return data
    except Exception:
        return None
    return None


def _write_cache(url, data, memory_only=False):
    _mem_cache_put(url, data)
    if memory_only:
        return
    try:
        with open(_cache_file(url), 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
    except Exception:
        pass


def _decode_response(response):
    body = response.read()
    encoding = (response.headers.get('Content-Encoding') or '').lower()
    if 'gzip' in encoding:
        try:
            body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
        except Exception:
            pass
    return body.decode('utf-8', 'replace')


def get_json(url, ttl_seconds=0, timeout_override=None, memory_only=False):
    cached = _read_cache(url, ttl_seconds, memory_only=memory_only)
    if cached is not None:
        return cached
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Kodi DexHub/3.7.106',
    }
    if gzip_enabled():
        headers['Accept-Encoding'] = 'gzip'
    req = Request(url, headers=headers)
    timeout = timeout_seconds() if timeout_override in (None, '') else max(1, int(float(timeout_override)))
    with urlopen(req, timeout=timeout) as response:
        text = _decode_response(response)
    try:
        data = json.loads(text)
    except Exception:
        # Some Stremio addons send JSON with a BOM or extra whitespace.
        data = json.loads(text.strip().lstrip('\ufeff'))
    if ttl_seconds > 0:
        _write_cache(url, data, memory_only=memory_only)
    return data


def validate_manifest(manifest_url):
    data = get_json(manifest_url, ttl_seconds=300)
    if not isinstance(data, dict) or 'resources' not in data:
        raise ValueError('Invalid manifest')
    return data


def _configured_base_and_query(provider):
    """Return the configured addon base URL and any manifest query string.

    Stremio clients derive resource URLs from the exact configured manifest
    URL.  Some addons encode credentials in the path
    (/stremio/<config>/manifest.json); others may put them in the query string
    (manifest.json?...).  Preserve both shapes so Dex Hub calls the same route
    Stremio does.
    """
    manifest_url = str((provider or {}).get('manifest_url') or '').strip()
    if manifest_url and '/manifest.json' in manifest_url:
        try:
            parsed = urlparse(manifest_url)
            path = parsed.path.rsplit('/manifest.json', 1)[0]
            base = urlunparse((parsed.scheme, parsed.netloc, path, '', '', '')).rstrip('/')
            return base, parsed.query or ''
        except Exception:
            return manifest_url.rsplit('/manifest.json', 1)[0].rstrip('/'), ''
    return str(provider.get('base_url') or '').rstrip('/'), ''


def build_resource_url(provider, resource, media_type, item_id, extra=None):
    base, manifest_query = _configured_base_and_query(provider)
    # Episode stream ids use colons: tt1234567:1:2. Keep them readable
    # for stream routes because AIOStreams/Torrentio-style proxies are
    # more reliable with the normal Stremio path shape than an over-encoded id.
    safe_chars = ':' if resource == 'stream' else ''
    encoded_id = quote(str(item_id), safe=safe_chars)
    url = '%s/%s/%s/%s' % (base, resource, media_type, encoded_id)
    if extra:
        parts = []
        for key, value in extra.items():
            if value is None or value == '':
                continue
            parts.append('%s=%s' % (quote(str(key), safe=''), quote(str(value), safe='')))
        if parts:
            url += '/' + '&'.join(parts)
    url += '.json'
    if manifest_query:
        url += '?' + manifest_query
    return url


def fetch_catalog(provider, media_type, catalog_id, extra=None, timeout_override=None):
    return get_json(
        build_resource_url(provider, 'catalog', media_type, catalog_id, extra=extra or {}),
        ttl_seconds=catalog_ttl(),
        timeout_override=timeout_override,
    )


def fetch_meta(provider, media_type, item_id, timeout_override=None):
    return get_json(
        build_resource_url(provider, 'meta', media_type, item_id),
        ttl_seconds=meta_ttl(),
        timeout_override=timeout_override,
    )


def fetch_streams(provider, media_type, video_id, timeout_override=None):
    return get_json(
        build_resource_url(provider, 'stream', media_type, video_id),
        ttl_seconds=stream_ttl(),
        timeout_override=timeout_override,
        memory_only=True,
    )


def fetch_subtitles(provider, media_type, item_id, timeout_seconds=None):
    return get_json(
        build_resource_url(provider, 'subtitles', media_type, item_id),
        ttl_seconds=300,
        timeout_override=timeout_seconds,
    )


# Persistent thread pool — created once, reused for the lifetime of the
# Python invocation. Avoids the ~10-20ms startup cost of creating a new
# pool for every run_parallel call.
_POOL = None
_POOL_SIZE = 0


def _get_pool(size):
    global _POOL, _POOL_SIZE
    if _POOL is None or _POOL_SIZE < size:
        # Recreate larger pool if needed; otherwise reuse.
        if _POOL is not None:
            try:
                _POOL.shutdown(wait=False)
            except Exception:
                pass
        _POOL = ThreadPoolExecutor(max_workers=max(size, 8))
        _POOL_SIZE = max(size, 8)
    return _POOL


def run_parallel(func, items, workers=None, timeout=None):
    """Run func(item) for every item concurrently.

    Returns a list of (item, result_or_exception) tuples in original order.
    Exceptions are captured — they never bubble out of this helper.
    """
    if not items:
        return []
    size = workers if workers else parallel_workers()
    size = max(1, min(size, len(items)))
    results = [None] * len(items)
    pool = _get_pool(size)
    futures = {pool.submit(func, item): idx for idx, item in enumerate(items)}
    for future in as_completed(futures):
        idx = futures[future]
        try:
            results[idx] = (items[idx], future.result(timeout=timeout))
        except Exception as exc:
            results[idx] = (items[idx], exc)
    return results


def supports_resource(provider, resource_name, media_type=None, item_id=None):
    manifest = provider.get('manifest') or {}
    for resource in manifest.get('resources', []):
        if resource == resource_name:
            return True
        if isinstance(resource, dict) and resource.get('name') == resource_name:
            types = resource.get('types') or []
            if media_type and types and media_type not in types:
                continue
            prefixes = resource.get('idPrefixes') or []
            if item_id and prefixes:
                lower_id = str(item_id).lower()
                ok = False
                for prefix in prefixes:
                    if lower_id.startswith(str(prefix).lower()):
                        ok = True
                        break
                if not ok:
                    continue
            return True
    return False


def iter_parallel(func, items, workers=None, timeout=None):
    """Yield (item, result_or_exception) tuples as each task finishes."""
    if not items:
        return
    size = workers if workers else parallel_workers()
    size = max(1, min(size, len(items)))
    pool = _get_pool(size)
    futures = {pool.submit(func, item): idx for idx, item in enumerate(items)}
    for future in as_completed(futures):
        idx = futures[future]
        try:
            yield (items[idx], future.result(timeout=timeout))
        except Exception as exc:
            yield (items[idx], exc)


def clear_http_cache():
    removed = 0
    _HTTP_MEM.clear()
    _HTTP_MEM_ORDER[:] = []
    try:
        if os.path.isdir(HTTP_CACHE_DIR):
            for name in os.listdir(HTTP_CACHE_DIR):
                path = os.path.join(HTTP_CACHE_DIR, name)
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                        removed += 1
                except Exception:
                    continue
    except Exception:
        return removed
    return removed
