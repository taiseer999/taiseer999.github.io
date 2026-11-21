# -*- coding: utf-8 -*-
"""Several AI providers behind one call, tried in order with automatic fallback:
Gemini, DeepSeek, ChatGPT (OpenAI), Claude (Anthropic), Grok (xAI), OpenRouter, Groq, Mistral.

ask_json(system, user) → parsed JSON list. A provider that is out of quota/credit,
has a bad key or keeps failing is skipped (for the day when it's a quota problem) and
the next one with a key is used. When a model name no longer exists the provider's
/models list is read and a small/fast model is picked automatically."""
import json
import re
import threading
import time

from .common import setting_bool, http, HttpError, log, setting, cache_get, cache_put

PROVIDERS = {
    # id: (display name, kind, base url, default models — first that works is kept)
    'gemini': ('Gemini', 'gemini', '', []),
    'deepseek': ('DeepSeek', 'openai', 'https://api.deepseek.com', ['deepseek-flash', 'deepseek-v4-flash']),
    'openai': ('ChatGPT', 'openai', 'https://api.openai.com/v1', ['gpt-5-mini', 'gpt-4.1-mini', 'gpt-4o-mini']),
    'claude': ('Claude', 'anthropic', 'https://api.anthropic.com/v1', ['claude-haiku-5-5', 'claude-sonnet-5-5']),
    'grok': ('Grok', 'openai', 'https://api.x.ai/v1', ['grok-4.7', 'grok-latest', 'grok-4.3']),
    'openrouter': ('OpenRouter', 'openai', 'https://openrouter.ai/api/v1',
                   ['google/gemini-2.5-flash-lite', 'deepseek/deepseek-chat', 'openai/gpt-4.1-mini',
                    'openrouter/auto']),
    'groq': ('Groq', 'openai', 'https://api.groq.com/openai/v1', ['openai/gpt-oss-120b', 'qwen/qwen3.6-27b', 'openai/gpt-oss-20b']),
    'mistral': ('Mistral', 'openai', 'https://api.mistral.ai/v1', ['mistral-small-latest']),
}
DEFAULT_ORDER = 'gemini,deepseek,openai,claude,grok,openrouter,groq,mistral'
PROVIDERS_NO_THINK = set()
SMALL_HINTS = ('flash', 'mini', 'haiku', 'fast', 'lite', 'small', 'chat', 'instant', '8b', 'versatile')


class NoProvider(Exception):
    """No AI provider with a working key / remaining quota."""


_lock = threading.Lock()
_session_dead = set()          # bad key / no credit this session
_model_ok = {}                 # provider -> working model
_json_mode = {}                # provider -> False when response_format is refused


def _day():
    return time.strftime('%Y%m%d', time.gmtime(time.time() - 8 * 3600))


def _quota_dead():
    c = cache_get('ai_quota_%s.json' % _day(), 86400)
    try:
        return set(json.loads(c.decode('utf-8'))) if c else set()
    except ValueError:
        return set()


def _mark_quota(pid):
    with _lock:
        s = _quota_dead()
        s.add(pid)
        cache_put('ai_quota_%s.json' % _day(), json.dumps(sorted(s)))


def key_for(pid):
    own = (setting('%s_key' % pid) or '').strip()
    if own:
        return own
    # Piers edition: Dex Hub's key only with the user's consent (setting
    # use_dexhub_key, asked once) - it spends that account's tokens
    if not setting_bool('use_dexhub_key', False):
        return ''
    from .common import shared_key
    return shared_key(pid)


def dexhub_has_key():
    """Dex Hub holds a key for a provider this add-on can use."""
    from .common import shared_key
    return any(shared_key(p) for p in PROVIDERS)


def configured():
    """Providers with a key, in the user's order."""
    order = [p.strip() for p in (setting('ai_order', DEFAULT_ORDER) or DEFAULT_ORDER).split(',')]
    order += [p for p in PROVIDERS if p not in order]
    return [p for p in order if p in PROVIDERS and key_for(p)]


def available():
    from . import gemini
    out = []
    dead = _quota_dead() | _session_dead
    for p in configured():
        if p in dead:
            continue
        if p == 'gemini' and gemini.all_used_up():
            continue
        out.append(p)
    return out


def any_available():
    return bool(available())


def name(pid):
    return PROVIDERS.get(pid, (pid,))[0]


def _extract_json(text):
    text = (text or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```[a-zA-Z]*\s*|\s*```$', '', text)
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r'(\[.*\]|\{.*\})', text, re.S)
        if m:
            return json.loads(m.group(1))
        raise


def _as_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ('items', 'lines', 'results', 'data', 'output'):
            if isinstance(data.get(k), list):
                return data[k]
        for v in data.values():
            if isinstance(v, list):
                return v
    raise ValueError('no JSON list in answer')


# ------------------------------------------------------------------ providers
def _models_for(pid):
    chosen = (setting('%s_model' % pid) or '').strip()
    lst = ([chosen] if chosen else []) + [m for m in PROVIDERS[pid][3] if m != chosen]
    if pid in _model_ok:
        lst = [_model_ok[pid]] + [m for m in lst if m != _model_ok[pid]]
    return lst


def _discover(pid, headers):
    """Model name gone? Read the provider's model list and pick a small/fast one."""
    base = PROVIDERS[pid][2]
    try:
        data = http(base + '/models', headers=headers, timeout=20)
    except Exception as e:
        log('%s: model list failed: %s' % (pid, e))
        return None
    ids = [m.get('id', '') for m in (data.get('data') or []) if isinstance(m, dict)]
    ids = [i for i in ids if not re.search(r'embed|whisper|tts|image|vision|audio|realtime|moderation|'
                                          r'guard|search|transcri|dall|sora|code', i, re.I)]
    for hint in SMALL_HINTS:
        for i in sorted(ids, reverse=True):          # newest-looking names first
            if hint in i.lower():
                return i
    return ids[0] if ids else None


def _free_models(headers):
    """OpenRouter models that cost nothing (id ends with ':free'), best-known families first."""
    try:
        data = http('https://openrouter.ai/api/v1/models', headers=headers, timeout=20)
    except Exception as e:
        log('OpenRouter model list failed: %s' % e)
        return []
    ids = [m.get('id', '') for m in data.get('data') or [] if str(m.get('id', '')).endswith(':free')]
    pref = ('gemini', 'deepseek', 'llama', 'qwen', 'mistral', 'gemma')
    ids.sort(key=lambda i: next((k for k, p in enumerate(pref) if p in i.lower()), 99))
    return ids


def _openai_call(pid, system, user, timeout):
    key = key_for(pid)
    headers = {'Authorization': 'Bearer ' + key}
    if pid == 'openrouter':
        headers.update({'HTTP-Referer': 'https://kodi.tv', 'X-Title': 'Najd Smart Subs'})
    base = PROVIDERS[pid][2]
    sys_txt = (system + '\n' if system else '') + \
        'Answer with ONLY a JSON object of the form {"items": [ ... ]} where items is the requested list.'
    models = _models_for(pid)
    tried_discover = False
    tried_free = [False]
    i = 0
    while i < len(models):
        model = models[i]
        body = {'model': model,
                'messages': [{'role': 'system', 'content': sys_txt}, {'role': 'user', 'content': user}],
                'temperature': 0.2}
        if _json_mode.get(pid) is not False:
            body['response_format'] = {'type': 'json_object'}
        if pid == 'deepseek' and pid not in PROVIDERS_NO_THINK:
            body['thinking'] = {'type': 'disabled'}
        try:
            r = http(base + '/chat/completions', json_body=body, headers=headers,
                     timeout=timeout, retries=0)
            text = r['choices'][0]['message'].get('content') or ''
            _model_ok[pid] = model
            return _as_list(_extract_json(text))
        except HttpError as e:
            b = (e.body or '').lower()
            if pid == 'openrouter' and e.code in (402, 429, 403) and not model.endswith(':free') \
                    and not tried_free[0]:
                # no credit on the account: switch to OpenRouter's free models
                tried_free[0] = True
                free = _free_models(headers)
                if free:
                    log('OpenRouter: no credit — using free model %s' % free[0])
                    models[i + 1:i + 1] = free[:3]
                    i += 1
                    continue
            if e.code == 400 and ('response_format' in b or 'json' in b) and _json_mode.get(pid) is not False:
                _json_mode[pid] = False
                continue
            if e.code == 400 and 'thinking' in b and pid == 'deepseek':
                PROVIDERS_NO_THINK.add(pid)
                continue
            if e.code in (404,) or (e.code == 400 and ('model' in b and ('not' in b or 'invalid' in b))):
                i += 1
                if i >= len(models) and not tried_discover:
                    tried_discover = True
                    found = _discover(pid, headers)
                    if found and found not in models:
                        models.append(found)
                continue
            raise
    raise HttpError(404, 'no working model for %s' % pid)


def _anthropic_call(pid, system, user, timeout):
    key = key_for(pid)
    headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
    base = PROVIDERS[pid][2]
    models = _models_for(pid)
    tried_discover = False
    i = 0
    while i < len(models):
        body = {'model': models[i], 'max_tokens': 16000,
                'system': (system + '\n' if system else '') + 'Answer with ONLY the JSON, no other text.',
                'messages': [{'role': 'user', 'content': user}]}
        try:
            r = http(base + '/messages', json_body=body, headers=headers, timeout=timeout, retries=0)
            text = ''.join(c.get('text', '') for c in r.get('content', []) if c.get('type') == 'text')
            _model_ok[pid] = models[i]
            return _as_list(_extract_json(text))
        except HttpError as e:
            b = (e.body or '').lower()
            if e.code == 404 or (e.code == 400 and 'model' in b):
                i += 1
                if i >= len(models) and not tried_discover:
                    tried_discover = True
                    found = _discover(pid, headers)
                    if found and found not in models:
                        models.append(found)
                continue
            raise
    raise HttpError(404, 'no working model for %s' % pid)


def _gemini_call(system, user, timeout):
    from . import gemini
    body = {'contents': [{'role': 'user', 'parts': [{'text': user}]}],
            'generationConfig': {'responseMimeType': 'application/json'}}
    if system:
        body['systemInstruction'] = {'parts': [{'text': system}]}
    return _as_list(_extract_json(gemini.generate(body, timeout=timeout)))


# ------------------------------------------------------------------ public
def ask_json(system, user, timeout=120):
    """Ask the first AI that answers; a per-minute limit is waited out once."""
    from . import gemini
    try:
        return _ask_json(system, user, timeout)
    except gemini.RateLimited as e:
        wait = min(max(e.delay, 5), 90)
        log('AI: per-minute limit, waiting %ds and trying again' % wait)
        time.sleep(wait)
        return _ask_json(system, user, timeout)


def _ask_json(system, user, timeout=120):
    """Returns (list, provider_id). Tries every available provider in order."""
    from . import gemini
    errors = []
    for pid in available():
        t0 = time.time()
        try:
            if pid == 'gemini':
                res = _gemini_call(system, user, timeout)
            elif PROVIDERS[pid][1] == 'anthropic':
                res = _anthropic_call(pid, system, user, timeout)
            else:
                res = _openai_call(pid, system, user, timeout)
            log('AI: answered by %s%s in %.1fs' % (name(pid), (' (%s)' % _model_ok[pid]) if pid in _model_ok
                                                   else '', time.time() - t0))
            return res, pid
        except (gemini.QuotaExhausted, gemini.RateLimited) as e:
            errors.append((pid, e))
            continue
        except HttpError as e:
            b = (e.body or '').lower()
            if e.code == 429 and ('per minute' in b or 'rate limit' in b or 'too many' in b) \
                    and 'quota' not in b and 'credit' not in b and 'balance' not in b:
                time.sleep(8)            # brief rate limit: one more try with this provider
                try:
                    if PROVIDERS[pid][1] == 'anthropic':
                        return _anthropic_call(pid, system, user, timeout), pid
                    if pid != 'gemini':
                        return _openai_call(pid, system, user, timeout), pid
                except Exception as e2:
                    errors.append((pid, e2))
                    continue
            if e.code in (402, 429) or 'quota' in b or 'credit' in b or 'balance' in b:
                log('%s: out of quota/credit — trying the next AI' % name(pid))
                _mark_quota(pid)
            elif e.code in (401, 403):
                log('%s: key rejected — trying the next AI' % name(pid))
                _session_dead.add(pid)
            else:
                log('%s failed (%s) — trying the next AI' % (name(pid), e.code))
            errors.append((pid, e))
        except ValueError:          # broken JSON (usually a too-long answer): let caller split
            raise
        except Exception as e:      # network → next provider
            log('%s failed: %s — trying the next AI' % (name(pid), e))
            errors.append((pid, e))
    if not errors:
        raise NoProvider('no AI key')
    limited = [e for _p, e in errors if isinstance(e, gemini.RateLimited)]
    if limited:
        raise limited[0]          # a per-minute limit: the caller waits and tries again
    if all(isinstance(e, (gemini.QuotaExhausted,)) or
           (isinstance(e, HttpError) and e.code in (402, 429)) for _p, e in errors):
        raise gemini.QuotaExhausted('all AI providers are out of quota today')
    raise errors[-1][1]


def check(pid):
    """Tiny live test of one provider. Returns (ok, message)."""
    try:
        if pid == 'gemini':
            from . import checks
            return checks.check_gemini(key_for('gemini'), '')
        kind = PROVIDERS[pid][1]
        call = _anthropic_call if kind == 'anthropic' else _openai_call
        res = call(pid, '', 'Return the list [1, 2, 3].', 60)
        return (bool(res), 'يعمل ✓ (%s)' % _model_ok.get(pid, ''))
    except HttpError as e:
        if e.code in (401, 403):
            return False, 'المفتاح غير صحيح'
        if e.code in (402, 429):
            return False, 'المفتاح صحيح لكن لا يوجد رصيد أو نفد الحد'
        return False, 'خطأ %s' % e.code
    except Exception as e:
        return False, 'لم يعمل: %s' % str(e)[:60]
