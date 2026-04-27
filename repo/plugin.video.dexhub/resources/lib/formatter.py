# -*- coding: utf-8 -*-
import json
import os
import re
import time
import urllib.request

import xbmc
import xbmcaddon
import xbmcvfs

from .dexhub.common import profile_path

ADDON = xbmcaddon.Addon()
CACHE_PATH = os.path.join(profile_path(), 'formatter_preset_cache.json')
META_PATH = os.path.join(profile_path(), 'formatter_preset_cache.meta.json')
CACHE_TTL = 6 * 60 * 60
DEFAULT_URL = 'https://raw.githubusercontent.com/9mousaa/BetterFormatter/main/presets/colored-src-sep-always.json'

_COMPILED = {'url': None, 'mtime': 0, 'rules': []}


def _setting(key, default=''):
    try:
        return ADDON.getSetting(key) or default
    except Exception:
        return default


def enabled():
    return (_setting('enable_source_formatter', 'true') or 'true').lower() == 'true'


def preset_url():
    return (_setting('formatter_preset_url', DEFAULT_URL) or DEFAULT_URL).strip()


def max_tags():
    try:
        return max(1, min(8, int(_setting('formatter_max_tags', '4') or '4')))
    except Exception:
        return 4


def clear_cache():
    for path in (CACHE_PATH, META_PATH):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except Exception:
            try:
                xbmcvfs.delete(path)
            except Exception:
                pass
    _COMPILED['url'] = None
    _COMPILED['mtime'] = 0
    _COMPILED['rules'] = []


def _normalize_color(value, fallback):
    text = str(value or '').strip()
    if not text:
        return fallback
    if text.startswith('#'):
        text = text[1:]
    text = text.strip().upper()
    if len(text) == 3:
        text = ''.join(ch * 2 for ch in text)
    if len(text) == 6 and all(ch in '0123456789ABCDEF' for ch in text):
        return 'FF' + text
    if len(text) == 8 and all(ch in '0123456789ABCDEF' for ch in text):
        return text
    return fallback


def _read_text_from_path(path):
    value = str(path or '').strip()
    if not value:
        return ''
    if value.startswith(('http://', 'https://')):
        req = urllib.request.Request(value, headers={'User-Agent': 'DexHub/3.7.83'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8', 'ignore')
    if value.startswith('special://'):
        fh = xbmcvfs.File(value)
        try:
            data = fh.read()
        finally:
            fh.close()
        if isinstance(data, bytes):
            return data.decode('utf-8', 'ignore')
        return str(data or '')
    with open(value, 'r', encoding='utf-8') as fh:
        return fh.read()


def _load_cache_meta():
    try:
        with open(META_PATH, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(raw, url):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    except Exception:
        pass
    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as fh:
            fh.write(raw or '')
        with open(META_PATH, 'w', encoding='utf-8') as fh:
            json.dump({'url': url, 'fetched_at': int(time.time())}, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        xbmc.log('[DexHub] formatter cache save failed: %s' % exc, xbmc.LOGDEBUG)


def _load_raw(force_refresh=False):
    url = preset_url()
    meta = _load_cache_meta()
    if not force_refresh and meta.get('url') == url and os.path.exists(CACHE_PATH):
        age = int(time.time()) - int(meta.get('fetched_at') or 0)
        if age <= CACHE_TTL:
            try:
                with open(CACHE_PATH, 'r', encoding='utf-8') as fh:
                    return fh.read()
            except Exception:
                pass
    try:
        raw = _read_text_from_path(url)
        if raw:
            _save_cache(raw, url)
            return raw
    except Exception as exc:
        xbmc.log('[DexHub] formatter fetch failed: %s' % exc, xbmc.LOGDEBUG)
    try:
        if meta.get('url') == url and os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, 'r', encoding='utf-8') as fh:
                return fh.read()
    except Exception:
        pass
    return ''


def _compile_rules(force_refresh=False):
    url = preset_url()
    try:
        mtime = int(os.path.getmtime(CACHE_PATH)) if os.path.exists(CACHE_PATH) else 0
    except Exception:
        mtime = 0
    if not force_refresh and _COMPILED.get('url') == url and _COMPILED.get('mtime') == mtime and _COMPILED.get('rules'):
        return _COMPILED['rules']
    raw = _load_raw(force_refresh=force_refresh)
    rules = []
    if raw:
        try:
            data = json.loads(raw)
        except Exception as exc:
            xbmc.log('[DexHub] formatter preset parse failed: %s' % exc, xbmc.LOGWARNING)
            data = {}
        filters = data.get('filters') if isinstance(data, dict) else data
        if isinstance(filters, list):
            for idx, row in enumerate(filters):
                if not isinstance(row, dict):
                    continue
                name = str(row.get('name') or '').strip()
                pattern = str(row.get('pattern') or '').strip()
                if not name or not pattern:
                    continue
                try:
                    regex = re.compile(pattern, re.I)
                except Exception:
                    continue
                rules.append({
                    'name': name,
                    'regex': regex,
                    'group': str(row.get('groupId') or '').strip(),
                    'bg': _normalize_color(row.get('tagColor') or '', 'FF2B2F3E'),
                    'fg': _normalize_color(row.get('textColor') or '', 'FFF2F4FB'),
                    'border': _normalize_color(row.get('borderColor') or '', '00000000'),
                    'icon': str(row.get('imageURL') or '').strip(),
                    'index': idx,
                })
    _COMPILED['url'] = url
    _COMPILED['mtime'] = mtime
    _COMPILED['rules'] = rules
    return rules


def _candidate_text(row, provider_name='', facts=None):
    row = row or {}
    facts = facts or {}
    values = [
        row.get('name'), row.get('title'), row.get('description'), row.get('infoHash'),
        row.get('resolution'), row.get('quality'), row.get('audioChannels'), provider_name,
        facts.get('display_name'), facts.get('site'),
    ]
    for key in ('visualTags', 'audioTags'):
        val = row.get(key)
        if isinstance(val, (list, tuple)):
            values.extend(list(val))
        else:
            values.append(val)
    for seq_key in ('video_bits', 'audio_bits'):
        seq = facts.get(seq_key) or []
        if isinstance(seq, (list, tuple)):
            values.extend(seq)
    values.append(facts.get('badges') or '')
    return ' | '.join([str(v) for v in values if v not in (None, '', [], {})])


def format_stream(row, provider_name='', facts=None, force_refresh=False):
    if not enabled():
        return {'tags': [], 'summary': ''}
    text = _candidate_text(row, provider_name=provider_name, facts=facts)
    rules = _compile_rules(force_refresh=force_refresh)
    if not rules or not text:
        return {'tags': [], 'summary': ''}
    seen_names = set()
    seen_groups = set()
    tags = []
    limit = max_tags()
    for rule in rules:
        try:
            if not rule['regex'].search(text):
                continue
        except Exception:
            continue
        group = rule.get('group') or ''
        name = rule.get('name') or ''
        if not name or name in seen_names:
            continue
        if group and group in seen_groups:
            continue
        seen_names.add(name)
        if group:
            seen_groups.add(group)
        tags.append({
            'text': name,
            'bg': rule.get('bg') or 'FF2B2F3E',
            'fg': rule.get('fg') or 'FFF2F4FB',
            'border': rule.get('border') or '00000000',
            'icon': rule.get('icon') or '',
            'group': group,
        })
        if len(tags) >= limit:
            break
    return {'tags': tags, 'summary': ' • '.join([t.get('text') or '' for t in tags if t.get('text')])}
