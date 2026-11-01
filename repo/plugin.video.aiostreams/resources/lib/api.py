# -*- coding: utf-8 -*-
"""
Client for an AIOStreams instance, speaking the Stremio addon protocol that
AIOStreams serves at  <host>/stremio/<uuid>/<encryptedPassword>/...

Notes taken from the AIOStreams 2.37.0 source:
  * Any User-Agent starting with "AIO" makes the stream route attach a
    `streamData` object (type, service, parsedFile, size, ...) to each stream.
  * Error / statistic pseudo-streams are tagged streamData.type = error|statistic.
  * Error catalog entries use ids starting with "aiostreamserror.".
  * Config variants are selected with the `v` query parameter, which must be
    carried to every resource URL (the /stremio/u/<alias> redirect keeps it).
"""
import hashlib
import json
import os
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from . import kodi

USER_AGENT = 'AIOStreams-Kodi/%s (Kodi)' % kodi.ADDON_VERSION
CACHE_DIR = os.path.join(kodi.PROFILE, 'cache')


class ApiError(Exception):
    pass


def normalise_manifest_url(url):
    """Accept manifest/configure/stremio:// URLs and return (base, query)."""
    url = (url or '').strip()
    if not url:
        raise ApiError(kodi.s(30100))
    if url.startswith('stremio://'):
        url = 'https://' + url[len('stremio://'):]
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parts = urlsplit(url)
    path = parts.path.rstrip('/')
    for suffix in ('/manifest.json', '/configure'):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    if '/stremio/' not in path + '/':
        raise ApiError(kodi.s(30101))
    base = urlunsplit((parts.scheme, parts.netloc, path, '', ''))
    return base, parts.query


def _ssl_context():
    ctx = ssl.create_default_context()
    if kodi.setting_bool('insecure_ssl'):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def http_get_json(url, timeout=30):
    kodi.debug('GET %s' % url)
    req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            final_url = resp.geturl()
            data = resp.read()
    except HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8', 'replace')
            body = json.loads(body).get('error', {}).get('message', body)
        except Exception:
            pass
        raise ApiError('HTTP %s %s' % (e.code, body or e.reason))
    except URLError as e:
        raise ApiError(str(e.reason))
    except Exception as e:  # timeouts, ssl, etc
        raise ApiError(str(e))
    try:
        return json.loads(data.decode('utf-8')), final_url
    except ValueError:
        raise ApiError(kodi.s(30102))


# --------------------------------------------------------------------------
# Disk cache
# --------------------------------------------------------------------------

def _cache_path(key):
    return os.path.join(CACHE_DIR, hashlib.sha1(key.encode('utf-8')).hexdigest() + '.json')


def cache_get(key, ttl):
    if ttl <= 0:
        return None
    path = _cache_path(key)
    try:
        if time.time() - os.path.getmtime(path) > ttl:
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def cache_set(key, value):
    try:
        kodi.ensure_dir(CACHE_DIR)
        with open(_cache_path(key), 'w', encoding='utf-8') as f:
            json.dump(value, f)
    except OSError as e:
        kodi.log('cache write failed: %s' % e)


def cache_clear():
    n = 0
    if os.path.isdir(CACHE_DIR):
        for name in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, name))
                n += 1
            except OSError:
                pass
    return n


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------

def _enc(value):
    return quote(str(value), safe='')


class AIOStreams(object):

    def __init__(self, manifest_url=None):
        self.base, self.query = normalise_manifest_url(manifest_url or kodi.setting('manifest_url'))
        self.timeout = max(10, kodi.setting_int('timeout', 60))
        self.ttl = max(0, kodi.setting_int('cache_minutes', 60)) * 60
        self._manifest = None
        self._origin = self.base
        resolved = cache_get('resolved:' + self._origin, 86400)
        if resolved:
            self.base = resolved

    # -- url helpers -------------------------------------------------------
    def _url(self, *segments, extras=None):
        path = '/'.join(_enc(seg) for seg in segments)
        if extras:
            path += '/' + '&'.join('%s=%s' % (_enc(k), _enc(v)) for k, v in extras)
        url = '%s/%s.json' % (self.base, path)
        if self.query:
            url += '?' + self.query
        return url

    def _get(self, url, ttl=None, timeout=None):
        ttl = self.ttl if ttl is None else ttl
        cached = cache_get(url, ttl)
        if cached is not None:
            return cached
        data, final_url = http_get_json(url, timeout or self.timeout)
        if ttl > 0:
            cache_set(url, data)
        return data

    # -- resources ---------------------------------------------------------
    def manifest(self, force=False):
        if self._manifest is not None and not force:
            return self._manifest
        if force:
            self.base = self._origin
        url = self.base + '/manifest.json' + ('?' + self.query if self.query else '')
        cached = None if force else cache_get(url, self.ttl)
        if cached is None:
            data, final_url = http_get_json(url, self.timeout)
            # follow /stremio/u/<alias> redirects so later calls skip the hop
            if final_url and final_url != url and final_url.split('?')[0].endswith('/manifest.json'):
                self.base = final_url.split('?')[0][: -len('/manifest.json')]
                cache_set('resolved:' + self._origin, self.base)
            if not isinstance(data, dict) or 'id' not in data:
                raise ApiError(kodi.s(30102))
            cache_set(url, data)
            cached = data
        self._manifest = cached
        return cached

    def has_resource(self, name, type_=None):
        for res in self.manifest().get('resources', []):
            if isinstance(res, str):
                if res == name:
                    return True
            elif res.get('name') == name and (type_ is None or type_ in res.get('types', [type_])):
                return True
        return False

    def catalogs(self):
        return self.manifest().get('catalogs', []) or []

    def find_catalog(self, type_, cat_id):
        for cat in self.catalogs():
            if cat.get('type') == type_ and cat.get('id') == cat_id:
                return cat
        return None

    def catalog(self, type_, cat_id, extras=None):
        extras = [(k, v) for k, v in (extras or []) if v not in (None, '')]
        data = self._get(self._url('catalog', type_, cat_id, extras=extras))
        metas = data.get('metas', []) if isinstance(data, dict) else []
        return [m for m in metas if not str(m.get('id', '')).startswith('aiostreamserror.')], \
               [m for m in metas if str(m.get('id', '')).startswith('aiostreamserror.')]

    def meta(self, type_, meta_id):
        data = self._get(self._url('meta', type_, meta_id), ttl=max(self.ttl, 6 * 3600))
        meta = data.get('meta') if isinstance(data, dict) else None
        if meta and str(meta.get('id', '')).startswith('aiostreamserror.'):
            raise ApiError('%s: %s' % (meta.get('name', ''), meta.get('description', '')))
        return meta

    def streams(self, type_, video_id):
        # AIOStreams caches upstream itself; keep a short local cache only so
        # the directory view and the resolver share one response.
        data = self._get(self._url('stream', type_, video_id), ttl=300)
        return data.get('streams', []) if isinstance(data, dict) else []

    def subtitles(self, type_, video_id, filename=None, size=None, video_hash=None):
        if not self.has_resource('subtitles', type_):
            return []
        extras = []
        if video_hash:
            extras.append(('videoHash', video_hash))
        if size:
            extras.append(('videoSize', size))
        if filename:
            extras.append(('filename', filename))
        try:
            data = self._get(self._url('subtitles', type_, video_id, extras=extras), ttl=3600, timeout=20)
        except ApiError as e:
            kodi.log('subtitles failed: %s' % e)
            return []
        subs = data.get('subtitles', []) if isinstance(data, dict) else []
        return [x for x in subs if not str(x.get('id', '')).startswith('error.')]
