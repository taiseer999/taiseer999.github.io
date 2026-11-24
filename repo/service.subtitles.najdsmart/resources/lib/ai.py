# -*- coding: utf-8 -*-
"""Gemini-based Arabic subtitle proofreading."""
import concurrent.futures
import hashlib
import json

from .common import http, log, cache_get, cache_put, setting, HttpError
from . import arabic

API = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent'

SYSTEM_PROMPT = (
    'أنت مدقق ترجمات أفلام ومسلسلات عربي محترف. ستصلك أسطر ترجمة عربية مرقمة بصيغة JSON. '
    'مهمتك تصحيح كل سطر فقط:\n'
    '- الأخطاء الإملائية والنحوية (الهمزات، التاء المربوطة، الألف المقصورة).\n'
    '- الحروف المتقطعة أو المقلوبة أو الكلمات الملتصقة.\n'
    '- الصياغة الركيكة أو الحرفية الناتجة عن الترجمة الآلية لتصبح عربية فصحى طبيعية سلسة.\n'
    '- موضع علامات الترقيم (؟ ، ! ...) في نهاية الجملة العربية.\n'
    'قواعد صارمة: لا تغير المعنى، لا تضف معلومات أو شرحاً، لا تدمج الأسطر ولا تقسمها، '
    'حافظ على نفس عدد الأسطر ونفس الأرقام، أبقِ رمز " | " كما هو لأنه فاصل سطر داخل نفس الترجمة، '
    'أبقِ وسوم <i> و <b> كما هي، أبقِ الأسماء والأرقام كما هي، واجعل الطول قريباً من الأصل. '
    'إذا كان السطر سليماً أعده كما هو حرفياً.\n'
    'أعد JSON فقط بالشكل: [{"i": رقم, "t": "النص المصحح"}, ...]'
)

SCHEMA = {
    'type': 'ARRAY',
    'items': {
        'type': 'OBJECT',
        'properties': {'i': {'type': 'INTEGER'}, 't': {'type': 'STRING'}},
        'required': ['i', 't'],
    },
}


class AIError(Exception):
    pass


_NO_THINK = [None]   # None = not tried yet, True = accepted, False = model refuses it


def _call(api_key, model, items, context_title=''):
    from . import llm
    user = ''
    if context_title:
        user += 'اسم العمل: %s\n' % context_title
    user += json.dumps(items, ensure_ascii=False)
    data, pid = llm.ask_json(SYSTEM_PROMPT, user)
    return {int(d['i']): d['t'] for d in data if isinstance(d, dict) and 'i' in d and 't' in d}


def _sane(orig, new):
    """Reject AI output that drifted too far (hallucination guard)."""
    if not new or not new.strip():
        return False
    lo, ln = len(orig), len(new)
    if ln > lo * 1.8 + 15 or ln < lo * 0.4 - 5:
        return False
    if orig.count('|') != new.count('|'):
        return False
    return True


def _apply(cues, texts, results):
    changed = 0
    for k, new in results.items():
        if k < 0 or k >= len(cues):
            continue
        orig = texts[k]
        new = (new or '').strip()
        if new == orig or not _sane(orig, new):
            continue
        cues[k].text = '\n'.join(p.strip() for p in new.split('|'))
        changed += 1
    return changed


def proofread(cues, title='', progress=None, batch=150, workers=2, abort=None,
              position=None, on_partial=None):
    """Correct cue texts with Gemini. Returns number of changed cues.
    position(): current playback time in ms — the lines you are about to see are
    corrected first, and on_partial(n) is called as soon as they are ready."""
    from . import llm
    if not llm.any_available():
        raise AIError('no_key')
    api_key, model = '', 'multi'
    if batch is None:
        batch = llm.batch_for(250, 150)      # fewer, bigger requests on Gemini

    texts = [arabic.plain(c.text).replace('\n', ' | ') for c in cues]
    digest = hashlib.sha1(('\n'.join(texts) + model).encode('utf-8')).hexdigest()
    cached = cache_get('ai_%s.json' % digest, 60 * 86400)
    if cached:
        try:
            results = {int(k): v for k, v in json.loads(cached.decode('utf-8')).items()}
            return _apply(cues, texts, results)
        except ValueError:
            pass

    now = 0
    try:
        now = int(position()) if position else 0
    except Exception:
        now = 0
    from .semsync import plan_chunks
    chunks = []
    for ch in plan_chunks([c.start for c in cues], now, chunk=batch):
        items = [{'i': k, 't': texts[k]} for k in ch if arabic.ARABIC_RE.search(texts[k])]
        if items:
            chunks.append(items)
    results = {}
    errors = []
    done = [0]
    partial_sent = [False]

    def run(chunk):
        from . import gemini
        if any(isinstance(x, gemini.QuotaExhausted) for x in errors):
            return {}
        def attempt(items):
            try:
                return _call(api_key, model, items, title)
            except ValueError:                   # broken/cut JSON: halve and retry
                if len(items) > 15:
                    h = len(items) // 2
                    r = attempt(items[:h])
                    r.update(attempt(items[h:]))
                    return r
                raise
        try:
            return attempt(chunk)
        except Exception as e:  # keep other chunks going
            errors.append(e)
            log('Gemini chunk failed: %s' % e)
            return {}

    from .semsync import _workers
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=_workers(workers))
    futs = {ex.submit(run, c): k for k, c in enumerate(chunks)}
    first_wave = set(f for f, k in futs.items() if k == 0)     # the next 5 minutes
    try:
        pending = set(futs)
        while pending:
            done_set, pending = concurrent.futures.wait(pending, timeout=0.5)
            for f in done_set:
                results.update(f.result())
                done[0] += 1
                if progress:
                    progress(int(done[0] * 100 / max(1, len(chunks))), done[0], len(chunks))
            if on_partial and not partial_sent[0] and pending and \
                    not (first_wave & pending) and results:
                partial_sent[0] = True
                tmp = [type(c)(c.start, c.end, c.text) for c in cues]
                n = _apply(tmp, texts, results)
                if n:
                    on_partial(tmp, n)
            if pending and abort and abort():
                for f in pending:
                    f.cancel()
                raise AIError('aborted')
    finally:
        ex.shutdown(wait=False)
    if errors and not results:
        raise errors[0]
    if not errors:
        cache_put('ai_%s.json' % digest, json.dumps(results, ensure_ascii=False))
    return _apply(cues, texts, results)


TRANSLATE_PROMPT = (
    'أنت مترجم أفلام ومسلسلات محترف. ستصلك أسطر ترجمة مرقمة بصيغة JSON بلغة أجنبية (غالباً إنجليزية). '
    'ترجم كل سطر إلى عربية فصحى بسيطة وطبيعية كما في ترجمات الأفلام الاحترافية:\n'
    '- الترجمة بالفصحى فقط، ولا تستخدم أي لهجة عامية حتى لو كان الكلام الأصلي عامياً.\n'
    '- جمل قصيرة سهلة القراءة على الشاشة، بدون ترجمة حرفية ركيكة.\n'
    '- افهم السياق من الأسطر المجاورة (من يتكلم، المذكر والمؤنث، المفرد والجمع).\n'
    '- الأسماء تكتب بالعربي كما تنطق، والأرقام تبقى كما هي.\n'
    '- الشتائم القوية خففها لما يناسب الترجمة العربية المعتادة.\n'
    '- أصوات ووصف للصم مثل [music] ترجمها بين قوسين [موسيقى].\n'
    'قواعد صارمة: سطر مقابل سطر بنفس الرقم، لا تدمج ولا تقسم ولا تحذف، '
    'أبقِ رمز " | " بنفس العدد لأنه فاصل سطر داخل نفس الترجمة، أبقِ وسوم <i> كما هي.\n'
    'أعد JSON فقط بالشكل: [{"i": رقم, "t": "الترجمة العربية"}, ...]'
)


def _tr_call(items, title):
    from . import llm
    user = ('اسم العمل: %s\n' % title) if title else ''
    user += json.dumps(items, ensure_ascii=False)
    data, _pid = llm.ask_json(TRANSLATE_PROMPT, user, timeout=70)
    return {int(d['i']): d['t'] for d in data if isinstance(d, dict) and 'i' in d and 't' in d}


def translate(cues, title='', progress=None, batch=100, workers=3, abort=None):
    """Translate cue texts to Arabic in place. Returns the number of translated lines."""
    from . import llm
    if not llm.any_available():
        raise AIError('no_key')
    if batch is None:
        batch = llm.batch_for(170, 70)       # one 10-minute part = one request on Gemini
    texts = [arabic.plain(c.text).replace('\n', ' | ') for c in cues]
    digest = hashlib.sha1(('tr\n' + '\n'.join(texts)).encode('utf-8')).hexdigest()
    cached = cache_get('tr_%s.json' % digest, 120 * 86400)
    results = {}
    if cached:
        try:
            results = {int(k): v for k, v in json.loads(cached.decode('utf-8')).items()}
        except ValueError:
            results = {}
    todo = [k for k in range(len(texts)) if k not in results and texts[k].strip()]
    chunks = [[{'i': k, 't': texts[k]} for k in todo[a:a + batch]] for a in range(0, len(todo), batch)]
    errors = []
    done = [0]

    def run(chunk):
        if abort and abort():
            return {}
        def attempt(items):
            try:
                r = _tr_call(items, title)
            except ValueError:
                if len(items) > 12:
                    h = len(items) // 2
                    r = attempt(items[:h])
                    r.update(attempt(items[h:]))
                    return r
                raise
            missing = [it for it in items if it['i'] not in r]
            if missing and len(missing) < len(items):
                try:
                    r.update(_tr_call(missing, title))
                except Exception:
                    pass
            return r
        try:
            return attempt(chunk)
        except Exception as e:
            errors.append(e)
            log('translate chunk failed: %s' % e)
            return {}

    if chunks:
        from .semsync import _workers
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=_workers(workers))
        try:
            pending = set(ex.submit(run, c) for c in chunks)
            while pending:
                fin, pending = concurrent.futures.wait(pending, timeout=0.5)
                for f in fin:
                    results.update(f.result())
                    done[0] += 1
                    if progress:
                        progress(done[0], len(chunks))
                if pending and abort and abort():
                    for f in pending:
                        f.cancel()
                    raise AIError('aborted')
        finally:
            ex.shutdown(wait=False)
    if errors and not results:
        raise errors[0]
    good = {k: v for k, v in results.items() if isinstance(v, str) and arabic.ARABIC_RE.search(v)}
    if good:
        cache_put('tr_%s.json' % digest, json.dumps(good, ensure_ascii=False))
    n = 0
    for k, v in good.items():
        if 0 <= k < len(cues):
            cues[k].text = '\n'.join(p.strip() for p in v.split('|') if p.strip())
            n += 1
    return n
