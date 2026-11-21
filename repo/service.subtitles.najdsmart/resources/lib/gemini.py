# -*- coding: utf-8 -*-
"""One place for every Gemini call: model fallback, 'thinking' switched off,
and careful handling of the free-tier limits (429):
  - per-minute limit  → wait the time Google asks for, once;
  - per-day / quota   → mark that model used up for today and try the next model;
  - every model used up → raise QuotaExhausted (callers keep the subtitle as it is)."""
import json
import re
import threading
import time

from .common import http, HttpError, log, setting, cache_get, cache_put

API = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent'
# Flash-Lite models have the most generous free tier; plain Flash as a last resort.
FALLBACKS = ['gemini-flash-lite-latest', 'gemini-2.5-flash-lite', 'gemini-flash-latest']


class QuotaExhausted(Exception):
    pass


class RateLimited(Exception):
    """The per-MINUTE limit was hit (not the daily one): wait `delay` seconds and retry."""
    def __init__(self, delay):
        Exception.__init__(self, 'rate limited, retry in %ds' % delay)
        self.delay = delay


_lock = threading.Lock()
_no_think = {}          # model -> False when it refuses thinkingConfig


def _day():
    return time.strftime('%Y%m%d', time.gmtime(time.time() - 8 * 3600))   # resets ~midnight Pacific


def _exhausted():
    c = cache_get('gemini_quota_%s.json' % _day(), 86400)
    try:
        return set(json.loads(c.decode('utf-8'))) if c else set()
    except ValueError:
        return set()


def _mark_exhausted(model):
    with _lock:
        s = _exhausted()
        s.add(model)
        cache_put('gemini_quota_%s.json' % _day(), json.dumps(sorted(s)))


def models():
    chosen = (setting('gemini_model', '') or '').strip()
    order = []
    if chosen and chosen != 'gemini-flash-latest':      # old default → prefer Lite now
        order.append(chosen)
    for m in FALLBACKS:
        if m not in order:
            order.append(m)
    dead = _exhausted()
    return [m for m in order if m not in dead]


def all_used_up():
    return not models()


def _retry_delay(body):
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body or '')
    return float(m.group(1)) if m else None


# per-model request "shape" that the model accepted: drop optional parts on 400
_LADDER = ('full', 'no_think', 'no_schema', 'plain')


def _load_shapes():
    c = cache_get('gemini_shapes.json', 30 * 86400)
    try:
        return json.loads(c.decode('utf-8')) if c else {}
    except ValueError:
        return {}


_shape = _load_shapes()      # remembered across restarts: no wasted first request


def _shape_body(body, level):
    req = json.loads(json.dumps(body))
    gc = req.setdefault('generationConfig', {})
    if level in ('full', 'no_think'):
        gc.setdefault('maxOutputTokens', 32768)  # long Arabic answers must not be cut off
    if level == 'full':
        gc['thinkingConfig'] = {'thinkingBudget': 0}
    if level in ('no_schema', 'plain'):
        gc.pop('responseSchema', None)
    if level == 'plain':
        gc.pop('responseMimeType', None)
        if not gc:
            req.pop('generationConfig', None)
    return req


def generate(body, timeout=90):
    """POST generateContent with fallbacks. Returns the text of the answer."""
    from . import llm
    key = llm.key_for('gemini')
    if not key:
        raise Exception('no_key')
    tried = []
    last_err = None
    minute_wait = 0
    for model in models():
        start = _LADDER.index(_shape.get(model, 'full'))
        level_i = start
        waited = False
        while level_i < len(_LADDER):
            level = _LADDER[level_i]
            req = _shape_body(body, level)
            try:
                resp = http(API % model, json_body=req, headers={'x-goog-api-key': key},
                            timeout=timeout, retries=0)
                parts = resp['candidates'][0]['content']['parts']
                if _shape.get(model) != level:
                    _shape[model] = level
                    log('Gemini %s works with request shape: %s' % (model, level))
                    try:
                        cache_put('gemini_shapes.json', json.dumps(_shape))
                    except Exception:
                        pass
                text = ''.join(p.get('text', '') for p in parts if not p.get('thought')).strip()
                if text and text[0] not in '[{':    # fenced / chatty answer: cut out the JSON
                    m = re.search(r'(\[.*\]|\{.*\})', text, re.S)
                    text = m.group(1) if m else text
                return text
            except HttpError as e:
                b = (e.body or '').lower()
                last_err = e
                if e.code == 400 and ('invalid' in b or 'think' in b or 'schema' in b):
                    log('Gemini %s rejected shape %s: %s' % (model, level, (e.body or '')[:160]))
                    level_i += 1           # drop the next optional part and retry
                    continue
                if e.code == 429:
                    per_minute = 'perminute' in b.replace('_', '').replace(' ', '') or 'per minute' in b
                    delay = _retry_delay(e.body)
                    if per_minute and not waited and (delay is None or delay <= 70):
                        waited = True
                        time.sleep(delay or 20)
                        continue
                    log('Gemini %s: quota used up (%s)' % (model, 'minute' if per_minute else 'day'))
                    if per_minute:
                        minute_wait = max(minute_wait, delay or 60)
                    else:
                        _mark_exhausted(model)
                    tried.append(model)
                    break
                if e.code == 404 or (e.code == 400 and 'not supported' in b):
                    tried.append(model)
                    break
                if e.code in (500, 503, 504):          # overloaded: short pause, once, then next model
                    if not waited:
                        waited = True
                        time.sleep(3)
                        continue
                    log('Gemini %s overloaded (%s) — trying the next model' % (model, e.code))
                    tried.append(model)
                    break
                raise
        else:
            tried.append(model)            # every shape rejected → try the next model
    if last_err is not None and getattr(last_err, 'code', 0) in (400, 500, 503, 504):
        raise last_err
    if minute_wait:
        raise RateLimited(int(minute_wait))      # only the per-minute limit: not used up today
    raise QuotaExhausted('all models used up: %s' % ', '.join(tried))
