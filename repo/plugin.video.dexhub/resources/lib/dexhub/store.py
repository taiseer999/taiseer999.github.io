# -*- coding: utf-8 -*-
import json
import os
import uuid

from .common import profile_path

PROVIDERS_PATH = os.path.join(profile_path(), 'providers.json')
CATALOG_STATE_PATH = os.path.join(profile_path(), 'catalog_state.json')

_PROVIDERS_CACHE = None
_PROVIDERS_MTIME = None
_STATE_CACHE = None
_STATE_MTIME = None


def _file_mtime(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return None


def _read_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                if isinstance(data, type(default)):
                    return data
    except Exception:
        pass
    return default


def _write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)


def _invalidate_providers_cache(rows=None):
    global _PROVIDERS_CACHE, _PROVIDERS_MTIME
    _PROVIDERS_CACHE = rows
    _PROVIDERS_MTIME = _file_mtime(PROVIDERS_PATH)


def _invalidate_state_cache(state=None):
    global _STATE_CACHE, _STATE_MTIME
    _STATE_CACHE = state
    _STATE_MTIME = _file_mtime(CATALOG_STATE_PATH)


def list_providers():
    global _PROVIDERS_CACHE, _PROVIDERS_MTIME
    mtime = _file_mtime(PROVIDERS_PATH)
    if _PROVIDERS_CACHE is not None and mtime == _PROVIDERS_MTIME:
        return list(_PROVIDERS_CACHE)
    rows = _read_json(PROVIDERS_PATH, [])
    _PROVIDERS_CACHE = rows
    _PROVIDERS_MTIME = mtime
    return list(rows)


def add_provider(name, manifest_url, manifest):
    rows = list_providers()
    base_url = manifest_url.rsplit('/manifest.json', 1)[0]
    for row in rows:
        if row.get('manifest_url') == manifest_url:
            row.update({'name': name, 'base_url': base_url, 'manifest': manifest})
            _write_json(PROVIDERS_PATH, rows)
            _invalidate_providers_cache(rows)
            return row
    row = {
        'id': uuid.uuid4().hex[:10],
        'name': name,
        'manifest_url': manifest_url,
        'base_url': base_url,
        'manifest': manifest,
    }
    rows.append(row)
    _write_json(PROVIDERS_PATH, rows)
    _invalidate_providers_cache(rows)
    return row


def refresh_provider_manifest(provider_id, new_manifest):
    """Update a provider's manifest snapshot without touching its id/name."""
    rows = list_providers()
    for row in rows:
        if row.get('id') == provider_id:
            row['manifest'] = new_manifest
            if new_manifest and new_manifest.get('name') and not row.get('name'):
                row['name'] = new_manifest.get('name')
            _write_json(PROVIDERS_PATH, rows)
            _invalidate_providers_cache(rows)
            return row
    return None


def remove_provider(provider_id):
    rows = [row for row in list_providers() if row.get('id') != provider_id]
    _write_json(PROVIDERS_PATH, rows)
    _invalidate_providers_cache(rows)
    state = _catalog_state()
    state = {k: v for k, v in state.items() if not k.startswith(provider_id + ':')}
    _write_json(CATALOG_STATE_PATH, state)
    _invalidate_state_cache(state)


def get_provider(provider_id):
    for row in list_providers():
        if row.get('id') == provider_id:
            return row
    return None


def _catalog_state():
    global _STATE_CACHE, _STATE_MTIME
    mtime = _file_mtime(CATALOG_STATE_PATH)
    if _STATE_CACHE is not None and mtime == _STATE_MTIME:
        return dict(_STATE_CACHE)
    state = _read_json(CATALOG_STATE_PATH, {})
    _STATE_CACHE = state
    _STATE_MTIME = mtime
    return dict(state)


def _catalog_key(provider_id, catalog_id):
    return '%s:%s' % (provider_id or '', catalog_id or '')


def get_catalog_state(provider_id, catalog_id):
    return _catalog_state().get(_catalog_key(provider_id, catalog_id), {})


def set_catalog_filter(provider_id, catalog_id, name, value):
    state = _catalog_state()
    key = _catalog_key(provider_id, catalog_id)
    current = dict(state.get(key, {}))
    if value in (None, '', '__clear__'):
        current.pop(name, None)
    else:
        current[name] = value
    state[key] = current
    _write_json(CATALOG_STATE_PATH, state)
    _invalidate_state_cache(state)
    return current


def clear_catalog_filters(provider_id, catalog_id):
    state = _catalog_state()
    key = _catalog_key(provider_id, catalog_id)
    if key in state:
        del state[key]
        _write_json(CATALOG_STATE_PATH, state)
        _invalidate_state_cache(state)
