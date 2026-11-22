# -*- coding: utf-8 -*-
"""Download → extract → repair → sync → (AI job) → SRT file."""
import bisect
import hashlib
import io
import json
import os
import re
import shutil
import time
import urllib.parse
import zipfile

import xbmcvfs

from .common import (TEMP_DIR, JOBS_DIR, CACHE_DIR, ensure_dirs, log, setting, setting_bool,
                     cache_get, cache_put, cache_del, cache_json, write_atomic)
from . import arabic, subtitle, sync, providers, trace
from .media import release_tokens, release_family, is_arabic_code

def llm_key(pid):
    """The add-on's own key, else the one shared from Dex Hub (Piers edition)."""
    from . import llm
    return llm.key_for(pid)


SUB_EXT = ('.srt', '.ass', '.ssa', '.vtt', '.sub', '.txt', '.smi')


def _pick(names, video):
    subs = [n for n in names if n.lower().endswith(SUB_EXT) and not n.endswith('/')]
    if not subs:
        return None
    if video.get('is_episode') and video.get('episode'):
        s, e = int(video['season'] or 0), int(video['episode'])
        strict = re.compile(r'(?:s0*%d[ ._-]?e0*%d(?!\d)|(?<!\d)0*%dx0*%d(?!\d)|(?<![a-z0-9])ep?\s*0*%d(?!\d)'
                            r'|[ ._-]e0*\d+-e?0*%d(?!\d)|episode[ ._-]*0*%d(?!\d))' % (s, e, s, e, e, e, e), re.I)
        bare = re.compile(r'(?<![\dxXeEsS])0*%d(?![\dpPkK])' % e)
        def other_season(n):
            b = os.path.basename(n)
            for m in re.finditer(r'(?<![a-z0-9])s0*(\d{1,2})[ ._-]?e\d|(?<![a-z0-9.])0*(\d{1,2})x\d{2,3}(?!\d)', b, re.I):
                if int(m.group(1) or m.group(2)) != s:
                    return True
            return False
        if s:
            subs = [n for n in subs if not other_season(n)] or subs
            if all(other_season(n) for n in subs):
                return None      # only other seasons in this archive
        eps = [n for n in subs if strict.search(os.path.basename(n))]
        if not eps:
            # names like "Anime - 02 [1080p]" or "02.srt": number on its own
            def nums_ok(n):
                if re.search(r's\d+[ ._-]?e\d+|(?<![a-z0-9.])\d+x\d+', os.path.basename(n), re.I):
                    return False     # it names its own episode, and it isn't ours
                b = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', os.path.basename(n))
                b = re.sub(r'(?:dd|ddp|eac3|ac3|aac|dts|atmos|truehd)[ ._-]?\d(?:[ ._]\d)?|\d[ ._]\d(?![\d])', ' ', b, flags=re.I)
                b = re.sub(r'(?:19|20)\d\d|\d{3,4}p|[xh]\.?26[45]', ' ', b, flags=re.I)
                return bool(bare.search(b))
            eps = [n for n in subs if nums_ok(n)]
        if eps:
            subs = eps
        elif any(re.search(r's\d+[ ._-]?e\d+|\d+x\d+|(?<![a-z])ep?\s*\d+', os.path.basename(n), re.I)
                                   for n in subs):
            return None          # a pack for other episodes — don't load the wrong one
    vt = release_tokens(video.get('filename'))

    def rank(n):
        ext_pref = 0 if n.lower().endswith('.srt') else 1
        st = release_tokens(n)
        sim = len(vt & st) / float(len(vt | st)) if vt and st else 0
        return (ext_pref, -sim)
    subs.sort(key=rank)
    return subs[0]


def extract(data, video):
    """Return (bytes, name) of the best subtitle inside data (zip/rar/plain)."""
    if data[:2] == b'PK':
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [i.filename for i in z.infolist() if i.file_size < 15 * 1024 * 1024]
            # nested zip (season packs)
            best = _pick(names, video)
            if not best:
                inner = [n for n in names if n.lower().endswith('.zip')]
                for n in inner:
                    r = extract(z.read(n), video)
                    if r[0]:
                        return r
                return None, None
            return z.read(best), best
    if data[:4] == b'Rar!' or data[:2] == b'7z':
        ext = '.rar' if data[:4] == b'Rar!' else '.7z'
        tmp = os.path.join(TEMP_DIR, 'archive_%s%s' % (hashlib.sha1(data[:65536]).hexdigest()[:10] +
                                                    '_%d' % os.getpid(), ext))
        with open(tmp, 'wb') as f:
            f.write(data)
        root = 'archive://%s/' % urllib.parse.quote_plus(tmp)
        try:
            names = []

            def walk(p, prefix=''):
                dirs, files = xbmcvfs.listdir(p)
                for fn in files:
                    names.append(prefix + fn)
                for d in dirs:
                    walk(p + d + '/', prefix + d + '/')
            walk(root)
            best = _pick(names, video)
            if best:
                fh = xbmcvfs.File(root + best)
                content = bytes(fh.readBytes())
                fh.close()
                return content, best
        except Exception as e:
            log('archive read failed (install "Archive support" vfs.libarchive): %s' % e)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        return None, None
    return data, 'subtitle.srt'


GENERIC_NAMES = ('index', 'video', 'download', 'playlist', 'master', 'stream', 'file', 'media',
                 'play', 'watch', 'movie', 'get', 'manifest')


def is_generic_name(filename):
    """'index.m3u8', '/download', a random id... — names that do not tell films apart."""
    b = os.path.splitext(os.path.basename(filename or ''))[0].lower()
    return len(b) < 4 or b in GENERIC_NAMES or is_random_name(filename)


_RANDOM_RE = re.compile(r'^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{16,})$', re.I)


def is_random_name(filename):
    """A link id that changes on every play (e.g. '211fd81f-af5b-46b9-9eb0-ce92ea50c3c1')."""
    b = os.path.splitext(os.path.basename(filename or ''))[0]
    return bool(_RANDOM_RE.match(b))


def _video_key(video):
    name = video.get('filename', '')
    rnd = is_random_name(name)
    k = video.get('hash') or (('' if rnd else name) + video.get('imdb', '') +
                              str(video.get('season')) + str(video.get('episode')))
    if not video.get('hash') and (rnd or not video.get('imdb')) and is_generic_name(name):
        # a generic or random stream name: tell films apart by what Kodi knows about them
        k += '|%s|%s|%s|%d' % (video.get('tvshow') or '', video.get('title') or '', video.get('year') or '',
                               int(float(video.get('duration') or 0)) // 10)
    return hashlib.sha1(k.encode('utf-8')).hexdigest()[:16]


def najd_sub_path(video, lang='ar', tag=''):
    """Where a subtitle made for this video is written. A short file name in a folder of
    its own: Kodi lists an outside subtitle under its file name, so a long release name
    ('The Odyssey 2026 iNTERNAL BluRay 2160p UHD MULTi REMUX...') filled the subtitle
    list and the skin's title. Now Kodi shows «Najd» (or «Najd 30» while a translation
    is at 30 %), and every video still has its own file."""
    d = os.path.join(TEMP_DIR, _video_key(video))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'Najd%s.%s.srt' % (('.' + tag) if tag else '', lang or 'ar'))


def _sim(a, b):
    ta, tb = release_tokens(a), release_tokens(b)
    return len(ta & tb) / float(len(ta | tb)) if ta and tb else 0.0


def _looks_english(cues, sample=400):
    """Sites sometimes label Persian/Arabic/Hindi uploads as English. Check the letters."""
    latin = other = 0
    for c in cues[:sample]:
        for ch in getattr(c, 'text', '') or '':
            if ('a' <= ch <= 'z') or ('A' <= ch <= 'Z'):
                latin += 1
            elif ch.isalpha():
                other += 1
    total = latin + other
    return total > 200 and latin >= 0.75 * total


def get_reference(video, chosen, ar_cues=None):
    """Find an English subtitle that is in sync with this video.
    Tiers: same file (hash) → same release as the video → same release as the chosen
    Arabic subtitle (checked by timing). Uses the site keys AND the subtitle add-ons
    installed in Kodi (a4kSubtitles...), so no keys are required."""
    if chosen.get('hash_match'):
        return None, 'hash'
    key = 'ref_%s.srt' % _video_key(video)
    c = cache_get(key, 30 * 86400)
    if c:
        cached = subtitle.parse(c.decode('utf-8', 'replace'))
        if _looks_english(cached):
            return cached, 'cache'
        log('cached reference is not English text — searching again')
    try:
        cands = providers.search_all(dict(video, interactive=setting_bool('ref_from_addons', True)), ['en'])
    except Exception as e:
        log('reference search failed: %s' % e)
        return None, None
    cands = [x for x in cands if x.get('lang') == 'en']
    if video.get('is_episode') and video.get('episode'):
        se, ep = int(video.get('season') or 0), int(video['episode'])

        def same_episode(x):
            if x.get('episode') not in (None, '', 0):
                try:
                    if int(x['episode']) != ep:
                        return False
                except (TypeError, ValueError):
                    pass
            for r in (x.get('releases') or [x.get('release', '')]):
                m = re.search(r's(\d{1,2})[ ._-]?e(\d{1,3})', r or '', re.I)
                if m and (int(m.group(1)) != se or int(m.group(2)) != ep):
                    return False
            return True
        cands = [x for x in cands if same_episode(x)]
    log('reference: %d English candidates' % len(cands))
    ar_rel = chosen.get('release') or ''
    v_fam = release_family(video.get('filename'))
    tiers = []
    for x in cands:
        rels = x.get('releases') or [x.get('release', '')]
        # a subtitle package lists many releases: judge it by the one closest to the video
        best_rel = max(rels, key=lambda r: _sim(r, video.get('filename'))) if rels else ''
        fam = release_family(best_rel)
        if x.get('hash_match'):
            tiers.append((0, -1.0, x, 'hash'))
        elif x.get('match', 0) >= 0.5:
            tiers.append((1, -x['match'], x, 'release'))
        elif v_fam and fam == v_fam:
            # same kind of release as the video (BluRay ↔ BluRay, WEB ↔ WEB)
            tiers.append((2, -max([_sim(r, video.get('filename')) for r in rels] + [0]), x, 'same-family'))
        else:
            sim = max([_sim(r, ar_rel) for r in rels] + [0])
            tiers.append((3, -sim, x, 'arabic-release'))
    tiers.sort(key=lambda t: (t[0], t[1]))
    tried = 0
    bad = set(_bad_refs(video))
    none_key = 'refnone_%s_%s' % (_video_key(video), hashlib.sha1(
        (chosen.get('release') or str(chosen.get('id') or '')).encode('utf-8')).hexdigest()[:8])
    if cache_get(none_key, 3 * 86400):
        log('reference: none fitted this video last time; not downloading again')
        return None, None
    net_trouble = False
    for tier, _score, cand, how in tiers:
        if tried >= 3:                      # each try is a download from the site's daily allowance
            break
        if providers.limited(cand.get('provider', '')):
            continue
        if (cand.get('release') or '') in bad:
            log('reference skipped (audio showed it is another cut): %s' % cand.get('release'))
            continue
        tried += 1
        try:
            raw, _n = extract(providers.download(cand), video)
            if not raw:
                continue
            cues = subtitle.parse(arabic.decode(raw), video.get('fps') or 23.976)
            if len(cues) <= 20:
                continue
            if not _looks_english(cues):
                log('reference candidate rejected (labelled English but the text is not): %s' % cand.get('release'))
                continue
            if tier == 2 and ar_cues:
                # same kind of release as the VIDEO: this is what we want to follow, even if
                # the Arabic is far off (e.g. 30 s) — only require it to be the same film
                # (clear timing match, normal speed), not the same offset
                _new, info = sync.align(ar_cues, cues, local=False, min_lift=1.5, min_quality=0.6)
                if _new is None or not any(abs(info.get('ratio', 1) - r) < 2e-3 for r in sync.FPS_RATIOS):
                    log('reference candidate rejected (not the same film/cut): %s' % info)
                    continue
                if abs(info.get('offset', 0)) > 1500:
                    log('reference (same family) moves the Arabic by %.1f s' % (info['offset'] / 1000.0))
            if tier == 3:
                # not proven to match the video: accept only if it follows the same
                # timeline as the Arabic subtitle (same cut, at most a small shift)
                if not ar_cues:
                    continue
                _new, info = sync.align(ar_cues, cues, local=False, min_lift=1.6, min_quality=0.5)
                if _new is None or abs(info.get('ratio', 1) - 1) > 1e-3 or abs(info.get('offset', 0)) > 1500:
                    log('reference candidate rejected (different timeline): %s' % info)
                    continue
            cache_put(key, subtitle.to_srt(cues))
            rels = cand.get('releases') or [cand.get('release', '')]
            cache_put('refmeta_%s.json' % _video_key(video), json.dumps(
                {'how': how, 'family': release_family(max(rels, key=lambda r: _sim(r, video.get('filename'))))
                 if rels else '', 'release': cand.get('release') or ''}))
            log('reference chosen (%s): %s' % (how, cand.get('release')))
            trace.event(video, 'english reference found (%s): %s' % (how, cand.get('release')))
            return cues, how
        except providers.DailyLimit as e:
            log('reference: %s — stopped trying' % e)
            net_trouble = True
            break
        except Exception as e:
            log('reference download failed: %s' % e)
            net_trouble = True
    if tried and not net_trouble:
        cache_put(none_key, '1')     # do not spend downloads on it again (for this subtitle)
    return None, None


def process(item, video, progress=None):
    """Full pipeline. Returns (path, summary_lines)."""
    def step(pct, msg):
        if progress:
            progress(pct, msg)

    summary = []
    step(10, 'تنزيل الترجمة...')
    raw = providers.download(item)
    trace.start(video, item, 'manual' if progress else 'auto')
    content, name = extract(raw, video)
    if not content:
        raise Exception('لا يحتوي الأرشيف على ترجمة لهذه الحلقة أو هذا الفيلم')

    step(25, 'إصلاح الترميز والنص...')
    text = arabic.decode(content)
    cues = subtitle.parse(text, video.get('fps') or 23.976)
    if not cues:
        raise Exception('ملف الترجمة فارغ أو بصيغة غير مدعومة')

    is_ar = item.get('lang') == 'ar'
    if is_ar and setting_bool('fix_arabic', True):
        cues, st = arabic.fix_cues(cues, rtl_mode=setting('rtl_mode', 'rle'),
                                   remove_ads=setting_bool('remove_ads', True),
                                   remove_hi=setting_bool('remove_hi', False))
        if st['changed'] or st['ads']:
            summary.append('أُصلح %d سطراً وحُذف %d إعلاناً' % (st['changed'], st['ads']))

    steps = []
    verify_orig = None
    method = setting('sync_method', 'smart')
    if method == 'auto':                       # older setting value
        method = 'smart'
    whisper_only = setting_bool('whisper_only', False)     # testing: nothing but Whisper
    if whisper_only:
        method = 'audio'
    from . import llm as _llm
    gemini = is_ar and setting_bool('ai_fix', True) and _llm.any_available()
    emb_ok = False
    ref_used = False
    if setting_bool('auto_sync', True):
        if item.get('hash_match'):
            summary.append('مطابقة لملف الفيديو نفسه ✓')
        if method in ('smart', 'subtitle', 'audio') and setting_bool('embedded_ref', True) and not whisper_only:
            step(35, 'قراءة توقيت الترجمة المدمجة في الفيديو...')
            emb = embedded_reference(video)
            if emb:
                new, einfo = sync.align(cues, emb, local=setting_bool('local_sync', True), min_lift=1.4)
                log('embedded sync: %s' % einfo)
                trace.event(video, 'embedded: %s' % {k: einfo.get(k) for k in
                                                     ('ratio', 'offset', 'quality', 'lift', 'local_fixes', 'reason')})
                try:      # both timelines, small, so a bad match can be replayed
                    trace.put(video, 'emb_data', {'sub': _pack([(c.start, c.end) for c in cues]),
                                                  'emb': _pack([(c.start, c.end) for c in emb])})
                except Exception:
                    pass
                if new is not None:
                    cues, emb_ok = new, True
                    summary.append('ضُبط التوقيت على الترجمة المدمجة في الفيديو ✓ (%s)' % sync.describe(einfo))
        if emb_ok:
            # the film's own subtitle already gave the timing: nothing is downloaded from the
            # subtitle sites for a comparison (their daily downloads are kept for real subtitles)
            log('timing taken from the subtitle inside the video; no English download needed')
        elif method in ('smart', 'subtitle') and not item.get('hash_match'):
            step(45, 'البحث عن ترجمة إنجليزية مرجعية...')
            ref, how = get_reference(video, item, ar_cues=cues)
            if ref and emb_ok:
                # the film's own subtitles are the truth: put the English on that timeline too,
                # then use it only for the line-by-line matching
                eref, rinfo = sync.align(ref, emb, local=True, min_lift=1.4)
                log('reference vs embedded: %s' % rinfo)
                if eref is not None:
                    cache_put('ref_%s.srt' % _video_key(video), subtitle.to_srt(eref))
                    meta = _ref_meta(video)
                    meta.update({'verified': True})
                    cache_put('refmeta_%s.json' % _video_key(video), json.dumps(meta))
                    if method == 'smart' and gemini:
                        steps.append('semantic')
                        summary.append('جارٍ مطابقة كل سطر مع الترجمة الإنجليزية حسب المعنى...')
                else:
                    log('English reference does not fit this video; not used')
                ref = None
            if ref:
                ref_used = True
                before = [subtitle.Cue(c.start, c.end, c.text) for c in cues]
                cues, line = reference_sync_msg(cues, video, item, ref=ref, how=how)
                info = _LAST_REF_INFO.get('info') or {}
                big = abs(info.get('offset', 0)) > 3000 or abs(info.get('ratio', 1) - 1) > 1e-3
                if _needs_verify(video, how) and big and cues is not before:
                    # a big jump that only rests on the English file — check it on the sound
                    # in the background; until then the reference timing is shown
                    orig_path = os.path.join(TEMP_DIR, 'orig_%s.srt' % _video_key(video))
                    with open(orig_path, 'w', encoding='utf-8-sig') as f:
                        f.write(subtitle.to_srt(before))
                    verify_orig = orig_path
                if line:
                    summary.append(line)
                if method == 'smart' and gemini:
                    steps.append('semantic')
                    summary.append('جارٍ مطابقة كل سطر مع الترجمة الإنجليزية حسب المعنى...')
            elif how != 'hash':
                log('no English reference; keeping the subtitle timing as is')
                trace.event(video, 'no english reference with the same timing')
        # nothing that follows this video (no embedded subtitle, no English file of the same
        # release): let Whisper hear the film's own speech and build the timing from that
        if method in ('smart', 'audio') and not emb_ok and not ref_used and 'semantic' not in steps \
                and (setting_bool('whisper_sync', True) or whisper_only):
            from . import whisper as _wsp
            if _wsp.available() and (finetune_possible(video) if is_stream(video) else audio_possible(video)):
                steps.append('whisper')
                summary.append('Whisper يستمع إلى كلام الفيلم لضبط التوقيت في الخلفية...')
            elif whisper_only:
                summary.append('وضع تجربة Whisper: ' + ('اربط Groq أولاً (قائمة الإضافة ← ربط Whisper برمز QR)'
                                                        if not _wsp.available() else 'الاستماع غير متاح لهذا المصدر'))
            elif not _wsp.available() and setting('whisper_hint') != 'shown':
                from .common import ADDON
                ADDON.setSetting('whisper_hint', 'shown')
                summary.append('لضبط أدق على كلام الفيلم: قائمة الإضافة ← ربط Whisper برمز QR (مجاني)')
        listen = not emb_ok and 'whisper' not in steps and not whisper_only and \
            (method == 'audio' or (setting_bool('listen_extra', False) and not steps))
        if listen and audio_possible(video):
            steps.append('audio')
            if llm_key('gemini') and not is_stream(video) and setting_bool('understand_extra', False):
                steps.append('understand')
            summary.append('جارٍ الاستماع إلى الصوت لمزامنة الترجمة...')
        elif method == 'audio':
            summary.append('الاستماع غير متاح لهذا المصدر')

    apply_offset(cues, user_offset(video))
    cues = subtitle.fix_timing(cues)

    step(85, 'حفظ الملف...')
    path = najd_sub_path(video, item.get('lang', 'ar'))
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(subtitle.to_srt(cues))

    if gemini and 'semantic' not in steps:
        steps.append('ai')
    if setting_bool('auto_sync', True) and setting_bool('auto_finetune', True) and not whisper_only and 'audio' not in steps \
            and not emb_ok:
        if not is_stream(video) and audio_possible(video):
            steps.append('finetune')
        elif is_stream(video) and setting_bool('stream_finetune', True) and finetune_possible(video):
            steps.append('finetune')
    if 'finetune' in steps:
        summary.append('ضبط دقيق على الصوت في الخلفية...')
    elif 'ai' in steps:
        summary.append('التصحيح بالذكاء الاصطناعي في الخلفية...')
    if verify_orig and (finetune_possible(video) if is_stream(video) else audio_possible(video)):
        steps.insert(0, 'verify')
    remember_last(path, video, item)
    if steps:
        queue_job(path, video, item, steps, orig=verify_orig if 'verify' in steps else None)
    step(100, 'تم')
    return path, summary


_LAST_REF_INFO = {}


def embedded_reference(video):
    """Timing of the subtitles inside the video file itself (MKV index) as Cue list,
    or None. Read once per video and cached (also the 'nothing there' answer)."""
    key = 'emb_%s.json' % _video_key(video)
    c = cache_get(key, 60 * 86400)
    if c:
        try:
            d = json.loads(c.decode('utf-8'))
            return [subtitle.Cue(a, b, '') for a, b in d['iv']] if d.get('iv') else None
        except (ValueError, KeyError):
            pass
    path = video.get('path') or ''
    if not path or _other_container(video):
        return None
    # links with a random name ('211fd81f-...') are tried too: the file's own first bytes
    # tell whether it is an MKV (one small read; the answer is kept)
    from . import mkvcues, audiosync
    try:
        src, _args, remote = audiosync.media_source(path)
        t0 = time.time()
        track, iv, idx = mkvcues.timeline(path if remote else src,
                                          timeout=12.0 if remote else 6.0)
        log('embedded subtitles: %s in %.1fs (%s) — track %s, %d lines' % (
            'found' if iv else 'none usable', time.time() - t0, idx.get('stats'),
            track and '%s %s %s' % (track['num'], track['codec'], track['lang']), len(iv)))
    except Exception as e:
        log('embedded subtitles: not read (%s)' % e)
        if 'timeout' in str(e) or 'URLError' in type(e).__name__:
            return None                      # network hiccup: try again next time
        iv, track = [], None
    cache_put(key, json.dumps({'iv': iv, 'track': track and track.get('lang')}))
    return [subtitle.Cue(a, b, '') for a, b in iv] if iv else None


def _is_mkv(video):
    path = (video.get('path') or '').split('|')[0]
    return bool(re.search(r'\.(mkv|webm|mk3d)($|[?])', path, re.I)) or \
        (video.get('filename') or '').lower().endswith(('.mkv', '.webm', '.mk3d'))


def _other_container(video):
    path = (video.get('path') or '').split('|')[0].lower()
    name = (video.get('filename') or '').lower()
    return not _is_mkv(video) and bool(
        re.search(r'\.(mp4|m4v|avi|ts|m3u8|mpd|mov|wmv|flv|mpg|mpeg)($|[?])', path + ' ' + name))


def embedded_text_possible(video):
    """Worth offering «translate the built-in subtitle»? (cheap: no network)"""
    path = (video.get('path') or '').split('|')[0].lower()
    name = (video.get('filename') or '').lower()
    if not _is_mkv(video) and re.search(r'\.(mp4|m4v|avi|ts|m3u8|mpd|mov|wmv)($|[?])', path + ' ' + name):
        return False          # clearly another container; unknown links still get the option
    c = cache_get('emb_%s.json' % _video_key(video), 60 * 86400)
    if c:
        try:
            d = json.loads(c.decode('utf-8'))
            if d.get('text') is False:
                return False
        except ValueError:
            pass
    return True


def _net_msg(e, what):
    log('embedded text failed: %r' % (e,))
    t = str(e).lower()
    if 'timed out' in t or 'timeout' in t or 'handshake' in t or 'reset' in t or 'urlopen' in t:
        return what + ':\nخادم الفيلم بطيء أو قطع الاتصال. حاول مرة أخرى بعد قليل.'
    if 'no_range' in t:
        return what + ':\nخادم الفيلم لا يسمح بالقراءة الجزئية.'
    if 'no_relative_positions' in t or 'block_not_found' in t:
        return what + ':\nبنية ملف الفيديو لا تسمح باستخراج الترجمة منه.'
    return '%s (%s)' % (what, e)


def _read_text(mkvcues, where, track, idx, remote, abort, step):
    return mkvcues.read_text(where, track, idx, workers=4 if remote else 2,
                             timeout=240.0 if remote else 60.0, abort=abort,
                             progress=lambda d, n: step(10 + int(20 * d / max(1, n)),
                                                        'استخراج الترجمة من داخل الفيديو (%d/%d)...' % (d, n)))


LANG_AR = {'en': 'الإنجليزية', 'eng': 'الإنجليزية', 'fr': 'الفرنسية', 'fre': 'الفرنسية', 'fra': 'الفرنسية',
           'es': 'الإسبانية', 'spa': 'الإسبانية', 'de': 'الألمانية', 'ger': 'الألمانية', 'deu': 'الألمانية',
           'it': 'الإيطالية', 'ita': 'الإيطالية', 'pt': 'البرتغالية', 'por': 'البرتغالية', 'tr': 'التركية',
           'tur': 'التركية', 'ru': 'الروسية', 'rus': 'الروسية', 'ja': 'اليابانية', 'jpn': 'اليابانية',
           'ko': 'الكورية', 'kor': 'الكورية', 'zh': 'الصينية', 'chi': 'الصينية', 'hi': 'الهندية', 'hin': 'الهندية'}


def embedded_text_info(video):
    """Quick check (a few small reads): is there a text subtitle inside the video worth
    translating? → language name in Arabic, or None."""
    if not embedded_text_possible(video):
        return None
    from . import mkvcues, audiosync
    try:
        src, _a, remote = audiosync.media_source(video.get('path'))
        idx = mkvcues.read_index(video.get('path') if remote else src, positions=True,
                                 timeout=15.0 if remote else 6.0)
    except Exception as e:
        log('embedded check: %s' % e)
        return None
    tracks = mkvcues.text_tracks(idx)
    if not tracks:
        return None
    best = max(tracks, key=lambda t: (1 if (t.get('lang') or '').lower().startswith('en') else 0,
                                      len(idx['cues'].get(t['num']) or [])))
    lang = (best.get('lang') or '').lower()
    if is_arabic_code(lang):
        return None
    return LANG_AR.get(lang.split('-')[0], lang or 'أجنبية')


def embedded_translate(video, progress=None, abort=None, position=None):
    """Take the text subtitle built into the video and turn it into Arabic with AI.
    It is already timed for this exact video, so no sync is needed. → (path, summary)"""
    from . import mkvcues, audiosync, ai, llm
    def step(pct, msg):
        if progress:
            progress(pct, msg)
    if not embedded_text_possible(video):
        raise Exception('هذه الميزة لملفات MKV فقط')
    step(5, 'قراءة قائمة الترجمات داخل الفيديو...')
    try:
        src, _a, remote = audiosync.media_source(video.get('path'))
    except audiosync.AudioSyncError as e:
        raise Exception('تعذر فتح الفيديو (%s)' % e)
    where = video.get('path') if remote else src
    idx = None
    for attempt in range(3):
        try:
            idx = mkvcues.read_index(where, positions=True, timeout=25.0 if remote else 10.0)
            break
        except Exception as e:
            err = e
            if 'not_mkv' in str(e) or 'no_' in str(e) or attempt == 2:
                break
            time.sleep(1.5)
    if idx is None:
        e = err
        if 'not_mkv' in str(e):
            raise Exception('هذا الفيديو ليس MKV، فلا توجد فيه ترجمة مدمجة يمكن استخراجها')
        raise Exception(_net_msg(e, 'تعذرت قراءة فهرس الفيديو'))
    tracks = mkvcues.text_tracks(idx)
    if not tracks:
        imgs = [t for t in idx.get('tracks', []) if t['type'] == mkvcues.SUBTITLE]
        key = 'emb_%s.json' % _video_key(video)
        try:
            d = json.loads((cache_get(key, 60 * 86400) or b'{}').decode('utf-8'))
        except ValueError:
            d = {}
        d['text'] = False
        cache_put(key, json.dumps(d))
        raise Exception('الترجمة المدمجة في هذا الفيديو صور (PGS) وليست نصاً، فلا يمكن قراءتها'
                        if imgs else 'لا توجد ترجمة مدمجة داخل هذا الفيديو')

    def rank(t):
        lang = (t.get('lang') or '').lower()
        name = (t.get('name') or '').lower()
        return (2 if is_arabic_code(lang) else 1 if lang.startswith('en') else 0,
                0 if ('sdh' in name or 'cc' in name.split()) else 1,
                len(idx['cues'].get(t['num']) or []))
    track = max(tracks, key=rank)
    is_ar = is_arabic_code(track.get('lang'))
    log('embedded text: track %s %s %s (%d lines)' % (track['num'], track['codec'], track['lang'],
                                                       len(idx['cues'].get(track['num']) or [])))
    if not is_ar and not llm.any_available():
        raise Exception('يلزم مفتاح ذكاء اصطناعي (Gemini أو غيره) في الإعدادات للترجمة')
    item = {'provider': 'embedded', 'id': 'track%s' % track['num'], 'lang': 'ar',
            'release': 'embedded', 'hash_match': True}
    state = _emb_state(video, track)
    dur = _emb_duration(idx, track)
    now = 0
    try:
        now = int(position()) if position else 0
    except Exception:
        now = 0
    if is_ar:
        todo = list(range(EMB_SLICES))              # nothing to translate: read it all at once
    else:
        todo = _emb_next(state, dur, now, first=True)
    summary = []
    if todo:
        step(10, 'استخراج الترجمة من داخل الفيديو...')
        _emb_run_slices(state, todo, video, where, track, idx, remote, dur, is_ar, abort,
                        lambda pct, msg: step(10 + int(pct * 0.85), msg))
    if not state['lines']:
        raise Exception('الترجمة المدمجة فارغة')
    path = _emb_write(video, state)
    remember_last(path, video, item)
    left = [k for k in range(EMB_SLICES) if k not in state['done']]
    if left:
        summary.append('جاهز %d٪ من الترجمة، ويكتمل الباقي في الخلفية أثناء المشاهدة' % (len(state['done']) * 100 // EMB_SLICES))
        queue_job(path, video, item, ['embedded_more'])
    else:
        summary.append('الترجمة المدمجة جاهزة كاملة ✓ (%d سطراً)' % len(state['lines']))
    step(100, 'تم')
    return path, summary


EMB_SLICES = 10


def _emb_key(video, track):
    return 'embtr_%s_%s.json' % (_video_key(video), track['num'])


def _emb_state(video, track):
    c = cache_get(_emb_key(video, track), 120 * 86400)
    try:
        d = json.loads(c.decode('utf-8')) if c else None
    except ValueError:
        d = None
    if not d or d.get('n') != EMB_SLICES:
        d = {'n': EMB_SLICES, 'done': [], 'lines': []}
    d['key'] = _emb_key(video, track)
    return d


def _emb_save(state):
    cache_put(state['key'], json.dumps({k: state[k] for k in ('n', 'done', 'lines')}, ensure_ascii=False))


def _emb_duration(idx, track):
    sc = idx['scale']
    last = max([e[0] for e in (idx.get('where') or {}).get(track['num']) or [(0,)]]) * sc / 1e6
    return int(max(idx.get('duration_ms') or 0, last + 5000)) or 1


def _emb_slice(k, dur):
    w = dur / float(EMB_SLICES)
    return int(k * w), (int((k + 1) * w) if k < EMB_SLICES - 1 else dur + 3600000)


def _emb_next(state, dur, now, first=False):
    """Which part(s) to do next: the one you are watching, then ahead of you, then behind."""
    left = [k for k in range(EMB_SLICES) if k not in state['done']]
    if not left:
        return []
    cur = min(EMB_SLICES - 1, max(0, int(now * EMB_SLICES // max(1, dur))))
    ahead = [k for k in left if k >= cur]
    behind = sorted([k for k in left if k < cur], reverse=True)
    pick = (ahead + behind)[:1]
    if first and pick and pick[0] == cur and cur + 1 in left:
        a, b = _emb_slice(cur, dur)
        if b - now < 4 * 60000:          # almost through this part: take the next one too
            pick.append(cur + 1)
    return pick


def _emb_run_slices(state, ks, video, where, track, idx, remote, dur, is_ar, abort, step):
    from . import mkvcues, ai
    title = video.get('tvshow') or video.get('title') or ''
    for j, k in enumerate(ks):
        a, b = _emb_slice(k, dur)
        base = 100.0 * j / len(ks)
        span = 100.0 / len(ks)
        step(base, 'استخراج الجزء %d من 10...' % (k + 1))
        try:
            lines = mkvcues.read_text(where, track, idx, workers=4 if remote else 2,
                                      timeout=240.0 if remote else 60.0, abort=abort, t_range=(a, b),
                                      progress=lambda d, n: step(base + span * 0.4 * d / max(1, n),
                                                                 'استخراج الجزء %d من 10 (%d/%d)...' % (k + 1, d, n)))
        except mkvcues.MkvError as e:
            if 'aborted' in str(e):
                raise
            raise Exception(_net_msg(e, 'تعذر استخراج الترجمة من الفيديو'))
        cues = [subtitle.Cue(s, e, t) for s, e, t in lines]
        if cues and not is_ar:
            step(base + span * 0.4, 'ترجمة الجزء %d من 10 بالذكاء الاصطناعي...' % (k + 1))
            originals = [c.text for c in cues]
            n = 0
            for attempt in range(2):          # the 2nd pass only asks for the missing lines (cached)
                for c, t in zip(cues, originals):
                    c.text = t
                n = ai.translate(cues, title=title, abort=abort,
                                 progress=lambda d, t: step(base + span * (0.4 + 0.6 * d / max(1, t)),
                                                            'ترجمة الجزء %d من 10 (%d/%d)...' % (k + 1, d, t)))
                if n >= len(cues) * 0.95:
                    break
            complete = n >= len(cues) * 0.95
            cues = [c for c in cues if arabic.ARABIC_RE.search(c.text)]
            if not complete:
                if n < len(originals) * 0.6:
                    raise Exception('لم تكتمل ترجمة الجزء %d (%d من %d سطراً) — حاول مرة أخرى'
                                    % (k + 1, n, len(originals)))
                tries = state.setdefault('_tries', {})
                tries[k] = tries.get(k, 0) + 1
            if not complete and tries[k] < 3:
                # keep what is translated (shown now), but leave the part open: the
                # background job comes back to it and only the missing lines are asked again
                state['lines'] = [l for l in state['lines'] if not (a <= l[0] < b)] + \
                    [[c.start, c.end, c.text] for c in cues]
                state['lines'].sort()
                _emb_save(state)
                log('embedded: part %d/10 only %d of %d lines — will finish it later' % (k + 1, n, len(originals)))
                continue
        state['lines'] = [l for l in state['lines'] if not (a <= l[0] < b)] + \
            [[c.start, c.end, c.text] for c in cues]
        state['lines'].sort()
        state['done'] = sorted(set(state['done']) | {k})
        _emb_save(state)
        log('embedded: part %d/10 ready (%d lines)' % (k + 1, len(cues)))


def _emb_write(video, state):
    cues = [subtitle.Cue(s, e, t) for s, e, t in state['lines']]
    if setting_bool('fix_arabic', True):
        cues, _st = arabic.fix_cues(cues, rtl_mode=setting('rtl_mode', 'rle'),
                                    remove_ads=setting_bool('remove_ads', True),
                                    remove_hi=setting_bool('remove_hi', False))
    apply_offset(cues, user_offset(video))
    cues = subtitle.fix_timing(cues)
    base = re.sub(r'[\\/:*?"<>|]+', '_', os.path.splitext(video.get('filename') or 'subtitle')[0])[:80]
    pct = len(state['done']) * 100 // EMB_SLICES
    path = najd_sub_path(video, 'ar', '' if pct >= 100 else str(pct))
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(subtitle.to_srt(cues))
    if pct >= 100:
        # a permanent copy (the temp folder is cleaned after 12 hours)
        try:
            from .common import PROFILE
            keep = os.path.join(PROFILE, 'translated')
            os.makedirs(keep, exist_ok=True)
            with open(os.path.join(keep, os.path.basename(path)), 'w', encoding='utf-8-sig') as f:
                f.write(subtitle.to_srt(cues))
        except OSError as e:
            log('could not keep a copy: %s' % e)
    return path


def embedded_resume(video):
    """The film started again and its built-in subtitle was only partly translated:
    load what is ready and carry on in the background. → path or None"""
    key = _video_key(video)
    best = None
    ensure_dirs()
    for name in os.listdir(CACHE_DIR):
        if not (name.startswith('embtr_%s_' % key) and name.endswith('.json')):
            continue
        try:
            with open(os.path.join(CACHE_DIR, name), encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if d.get('n') == EMB_SLICES and d.get('done') and d.get('lines'):
            d['key'] = name
            d['num'] = name[len('embtr_%s_' % key):-5]
            if best is None or len(d['done']) > len(best['done']):
                best = d
    if not best:
        # the cached state may be gone: a finished translation kept in translated/ still counts
        try:
            from .common import PROFILE
            base = re.sub(r'[\\/:*?"<>|]+', '_', os.path.splitext(video.get('filename') or 'subtitle')[0])[:80]
            kept = os.path.join(PROFILE, 'translated', '%s.ar.srt' % (base or 'subtitle'))
            if video.get('filename') and not is_generic_name(video.get('filename')) and os.path.exists(kept):
                # shown under the short name, like every subtitle Najd makes
                shown = najd_sub_path(video, 'ar')
                shutil.copyfile(kept, shown)
                remember_last(shown, video, {'provider': 'embedded', 'id': 'kept', 'lang': 'ar',
                                             'release': 'embedded', 'hash_match': True})
                log('embedded: using the finished translation kept in translated/')
                return shown, 100
        except OSError:
            pass
        return None
    item = {'provider': 'embedded', 'id': 'track%s' % best['num'], 'lang': 'ar',
            'release': 'embedded', 'hash_match': True}
    path = _emb_write(video, best)
    remember_last(path, video, item)
    if len(best['done']) < EMB_SLICES:
        queue_job(path, video, item, ['embedded_more'])
    log('embedded: resumed at %d%%' % (len(best['done']) * 100 // EMB_SLICES))
    return path, len(best['done']) * 100 // EMB_SLICES


def embedded_more(job, progress=None, abort=None, on_update=None, position=None):
    """Background: keep pulling and translating the next part, always ahead of where you are."""
    from . import mkvcues, audiosync
    video = job['video']
    src, _a, remote = audiosync.media_source(video.get('path'))
    where = video.get('path') if remote else src
    idx = None
    for attempt in range(3):
        try:
            idx = mkvcues.read_index(where, positions=True, timeout=25.0 if remote else 10.0)
            break
        except Exception as e:
            log('embedded_more: index read failed (%s)' % e)
            if abort and abort():
                return None, []
            time.sleep(3)
    if idx is None:
        return None, ['تعذر إكمال استخراج الترجمة المدمجة (الاتصال)']
    num = int(str(job['item'].get('id', 'track0'))[5:] or 0)
    track = next((t for t in idx['tracks'] if t['num'] == num), None)
    if not track:
        return None, []
    is_ar = is_arabic_code(track.get('lang'))
    state = _emb_state(video, track)
    dur = _emb_duration(idx, track)
    path = None
    while True:
        if abort and abort():
            return None, []
        try:
            now = int(position()) if position else 0
        except Exception:
            now = 0
        ks = _emb_next(state, dur, now)
        if not ks:
            break
        failed = None
        for attempt in range(4):
            try:
                _emb_run_slices(state, ks, video, where, track, idx, remote, dur, is_ar, abort,
                                lambda pct, msg: progress and progress(
                                    int((len(state['done']) * 100 + pct) / EMB_SLICES), msg))
                failed = None
                break
            except Exception as e:
                if 'aborted' in str(e):
                    return None, []
                failed = e
                log('embedded_more: part %s failed (try %d): %r' % ([k + 1 for k in ks], attempt + 1, e))
                # free AI keys have a per-minute limit; servers hiccup — wait and try again
                wait = 20 * (attempt + 1)
                if 'quota' in str(e).lower() or '429' in str(e) or 'rate' in str(e).lower():
                    wait = 65
                for _ in range(wait):
                    if abort and abort():
                        return None, []
                    time.sleep(1)
                ks = [k for k in ks if k not in state['done']] or ks
        if failed is not None:
            rounds = job.setdefault('_rounds', 0) + 1
            job['_rounds'] = rounds
            if rounds >= 8:
                return None, ['توقف استخراج الترجمة المدمجة عند %d٪ — وسيكتمل تلقائياً في المرة القادمة التي تشغّل فيها الفيلم' %
                              (len(state['done']) * 100 // EMB_SLICES)]
            if progress:
                progress(len(state['done']) * 100 // EMB_SLICES, 'الاتصال متعثر — ستُعاد المحاولة بعد دقائق...')
            for _ in range(180):                 # rest 3 minutes, then carry on by itself
                if abort and abort():
                    return None, []
                time.sleep(1)
            continue
        path = _emb_write(video, state)
        left = len(state['done']) < EMB_SLICES
        if on_update and left:
            on_update(path, ['جاهز %d٪ من الترجمة' % (len(state['done']) * 100 // EMB_SLICES)])
    return path, ['الترجمة المدمجة جاهزة كاملة ✓ (%d سطراً)' % len(state['lines'])]


def _ref_meta(video):
    c = cache_get('refmeta_%s.json' % _video_key(video), 90 * 86400)
    try:
        return json.loads(c.decode('utf-8')) if c else {}
    except ValueError:
        return {}


def _needs_verify(video, how):
    """A reference that was not proven on this very file (hash) and not yet checked by ear."""
    meta = _ref_meta(video)
    if how == 'cache':
        how = meta.get('how', '')
    return how in ('same-family', 'release') and not meta.get('verified')


def _mark_ref_good(video):
    meta = _ref_meta(video)
    if meta:
        meta['verified'] = True
        cache_put('refmeta_%s.json' % _video_key(video), json.dumps(meta))


def _bad_refs(video):
    c = cache_get('refbad_%s.json' % _video_key(video), 90 * 86400)
    try:
        return json.loads(c.decode('utf-8')) if c else []
    except ValueError:
        return []


def _mark_ref_bad(video):
    key = _video_key(video)
    meta = cache_get('refmeta_%s.json' % key, 90 * 86400)
    try:
        rel = json.loads(meta.decode('utf-8')).get('release', '') if meta else ''
    except ValueError:
        rel = ''
    bad = _bad_refs(video)
    if rel and rel not in bad:
        bad.append(rel)
    cache_put('refbad_%s.json' % key, json.dumps(bad))
    for name in ('ref_%s.srt' % key, 'refmeta_%s.json' % key):
        try:
            os.remove(os.path.join(CACHE_DIR, name))
        except OSError:
            pass


def audio_compare(a_cues, b_cues, video, abort=None, progress=None):
    """Listen to a few busy moments and say which timing follows the speech:
    'a', 'b', or None when the sound can't tell them apart."""
    from . import audiosync
    eng = ffmpeg_path()
    if not eng:
        return None
    try:
        src, args, remote = audiosync.media_source(video.get('path'))
    except audiosync.AudioSyncError:
        return None
    audiosync.STATS.update(short=0, refused=0)
    dur = video.get('duration') or (max(c.end for c in a_cues) / 1000.0 if a_cues else 0)
    if dur < 600 or not a_cues or not b_cues:
        return None
    if remote:
        length, count = (25000 if _is_4k(video) else 40000), 2
    else:
        length, count = 60000, 3
    wins = _dense_windows(a_cues, int(dur * 1000), length, count, lo=0.05, hi=0.9)
    if not wins:
        return None
    votes, sa, sb = [], 0.0, 0.0
    for k, w0 in enumerate(wins):
        if progress:
            progress(3 + k * 2, 'التأكد من التوقيت على الصوت (%d/%d)...' % (k + 1, len(wins)))
        try:
            pcm = audiosync._run_ffmpeg(eng, src, args, start=w0 / 1000.0, dur=length / 1000.0,
                                        abort=abort, timeout=180 if remote else 120)
        except audiosync.AudioSyncError as e:
            if 'aborted' in str(e):
                raise
            log('verify: read failed: %s' % e)
            continue
        sp = sorted((c.start, c.end) for c in audiosync.detect_speech(pcm, offset_ms=w0))
        if len(sp) < 5:
            continue
        res = []
        for cs in (a_cues, b_cues):
            inside = sorted((c.start, c.end) for c in cs if w0 + 1000 <= c.start and c.end <= w0 + length - 1000)
            tot = sum(e - s for s, e in inside)
            if len(inside) < 3 or tot <= 0:
                res.append(0.0)
                continue
            _d, sc = sync._refine(inside, sp, 1.0, 0, 800, 40)
            res.append(sc / float(tot))
        log('verify window @%ds: original %.2f / reference %.2f' % (w0 // 1000, res[0], res[1]))
        sa += res[0]
        sb += res[1]
        if max(res) > 0:
            votes.append('a' if res[0] > res[1] else 'b')
    if not votes or len(set(votes)) > 1:
        return None
    if votes[0] == 'a' and sa >= sb * 1.15 and sa / len(votes) > 0.35:
        return 'a'
    if votes[0] == 'b' and sb >= sa * 1.15 and sb / len(votes) > 0.35:
        return 'b'
    return None


def reference_sync_msg(cues, video, item, ref=None, how=None):
    """Sync against an English subtitle of the same release. Returns (cues, summary_line)."""
    if ref is None:
        ref, how = get_reference(video, item)
    if not ref:
        return cues, ('لم يُعثر على مرجع للمزامنة' if how is None else '')
    t0 = time.time()
    new, info = sync.align(cues, ref, local=setting_bool('local_sync', True), min_lift=1.45)
    log('ref sync (%s) %.1fs: %s' % (how, time.time() - t0, info))
    _LAST_REF_INFO['info'] = info if new is not None else {}
    if new is None:
        return cues, 'المزامنة: المرجع لا يطابق، فتُركت كما هي'
    return new, 'مزامنة: ' + sync.describe(info)


def ffmpeg_path():
    from . import audiosync
    return audiosync.find_engine(setting('ffmpeg_path', ''))


def is_stream(video):
    return (video.get('path') or '').startswith(('http://', 'https://'))


def audio_possible(video):
    """Listening to the audio means reading the video again. For a local file that is
    cheap; for an internet stream it competes with playback, so it is off unless the
    user chose the light mode."""
    from . import audiosync
    if is_stream(video) and setting('stream_audio', 'off') != 'light':
        return False
    if not ffmpeg_path():
        return False
    try:
        audiosync.media_source(video.get('path'))
        return True
    except audiosync.AudioSyncError:
        return False


def audio_sync(cues, video, progress=None, abort=None):
    """Align cues to the speech in the video's audio. Returns (cues|None, info)."""
    from . import audiosync
    ff = ffmpeg_path()
    if not ff:
        raise audiosync.AudioSyncError('no_ffmpeg')
    key = 'speech_%s.json' % _video_key(video)
    cached = cache_json(key, 30 * 86400)
    if cached:
        speech = [subtitle.Cue(s, e, '') for s, e in cached]
    else:
        speech = audiosync.speech_reference(ff, video['path'], video.get('duration') or 0,
                                            mode=setting('audio_mode', 'auto'),
                                            progress=progress, abort=abort)
        if len(speech) < 20:
            raise audiosync.AudioSyncError('لم يُسمع كلام كافٍ في الصوت')
        cache_put(key, json.dumps([[c.start, c.end] for c in speech]))
    if progress:
        progress(80, 'مطابقة الترجمة مع الكلام...')
    t0 = time.time()
    new, info = sync.align(cues, speech, local=setting_bool('local_sync', True),
                           min_quality=0.2, min_lift=1.4, local_min_abs=0.3)
    log('audio sync %.1fs (%d speech segs): %s' % (time.time() - t0, len(speech), info))
    return new, info


def understand_sync(cues, video, progress=None, abort=None):
    from . import understand, audiosync
    ff = ffmpeg_path()
    if not ff:
        raise audiosync.AudioSyncError('no_ffmpeg')
    key = llm_key('gemini')
    if not key:
        raise audiosync.AudioSyncError('no Gemini key')
    model = setting('gemini_model', 'gemini-flash-latest').strip() or 'gemini-flash-latest'
    anchors = understand.collect_anchors(cues, ff, video['path'], video.get('duration') or 0,
                                         key, model, progress=progress, abort=abort)
    speech = None
    c = cache_json('speech_%s.json' % _video_key(video), 30 * 86400)
    if c:
        speech = [subtitle.Cue(s, e, '') for s, e in c]
    if progress:
        progress(90, 'ضبط كل سطر على بداية الكلام...')
    new, info = understand.apply_anchors(cues, anchors, speech)
    log('understand: %s' % info)
    return new, info


def understand_describe(info):
    from . import understand
    return understand.describe(info)


def _pair(video):
    """'web>bluray' style key: which kind of reference timed this video's subtitle."""
    meta = cache_json('refmeta_%s.json' % _video_key(video), 365 * 86400)
    if not meta:
        return None
    if meta.get('how') == 'hash':
        return None
    return '%s>%s' % (meta.get('family') or meta.get('how') or '?', release_family(video.get('filename')) or '?')


def _learned():
    c = cache_get('learned_offsets.json', 10 * 365 * 86400)
    return json.loads(c.decode('utf-8')) if c else {}


def learned_offset(video):
    """What you usually correct for this kind of reference/video pair (learned from ⏪/⏩)."""
    pair = _pair(video)
    samples = _learned().get(pair) if pair else None
    if not samples:
        return 0
    v = sorted(samples)
    return v[len(v) // 2]


def _season_key(video):
    if not video.get('is_episode') or not video.get('tvshow'):
        return None
    show = re.sub(r'[^a-z0-9\u0600-\u06ff]+', '_', video['tvshow'].lower())
    return 'season_%s_%s.json' % (show, video.get('season') or '0')


def _season_offset(video):
    k = _season_key(video)
    c = cache_get(k, 365 * 86400) if k else None
    return json.loads(c.decode('utf-8')).get('ms') if c else None


def _video_offset(video):
    c = cache_get('offset_%s.json' % _video_key(video), 365 * 86400)
    return json.loads(c.decode('utf-8')).get('ms') if c else None


def user_offset(video):
    """Your own fixed correction from the settings (التوقيت → تقديم/تأخير ثابت).
    The per-episode / per-season / learned offsets of the old ¼-second buttons are gone
    (the buttons were removed in 2.8.2 and nothing could reset them any more)."""
    try:
        return int(float(setting('global_offset_ms', '0') or 0))
    except ValueError:
        return 0


def forget_old_offsets():
    """One-time cleanup of the hidden offsets left by the removed ¼-second buttons."""
    n = 0
    try:
        for name in os.listdir(CACHE_DIR):
            if name == 'learned_offsets.json' or (name.endswith('.json') and
                                                  name.startswith(('offset_', 'season_'))):
                os.remove(os.path.join(CACHE_DIR, name))
                n += 1
    except OSError:
        pass
    if n:
        log('removed %d old hidden offsets' % n)

def _has_embedded(video):
    c = cache_get('emb_%s.json' % _video_key(video), 60 * 86400)
    return bool(c) and b'"iv": [[' in c


def apply_offset(cues, ms):
    if ms:
        for c in cues:
            c.start = max(0, c.start + ms)
            c.end = max(c.start + 200, c.end + ms)
    return cues


def nudge(video, ms):
    """Shift the current subtitle by ms, remember it for this video. Returns new path."""
    last = last_for(video)
    if not last:
        return None
    with open(last['path'], 'rb') as f:
        cues = subtitle.parse(arabic.decode(f.read()))
    apply_offset(cues, ms)
    key = 'offset_%s.json' % _video_key(video)
    own = _video_offset(video)
    if own is None:
        own = _season_offset(video)
    total = (own if own is not None else learned_offset(video)) + ms
    cache_put(key, json.dumps({'ms': total}))
    sk = _season_key(video)
    if sk:                         # the rest of this season's episodes follow
        cache_put(sk, json.dumps({'ms': total}))
    pair = _pair(video)
    if pair:                       # learn: next films with the same kind of reference
        data = _learned()
        data[pair] = (data.get(pair, []) + [total])[-7:]
        cache_put('learned_offsets.json', json.dumps(data))
    base = re.sub(r'\.(?:n-?\d+)$', '', last['path'][:-4])
    new_path = '%s.n%d.srt' % (base, total)
    with open(new_path, 'w', encoding='utf-8-sig') as f:
        f.write(subtitle.to_srt(cues))
    remember_last(new_path, video, last.get('item') or {})
    return new_path, total


def _dense_windows(cues, dur_ms, length_ms, count, lo=0.10, hi=0.85):
    """The `count` windows with the most dialogue (so a short listen measures well)."""
    starts = [c.start for c in cues]
    best = []
    step = 15000
    t = int(dur_ms * lo)
    while t + length_ms < dur_ms * hi:
        a = bisect.bisect_left(starts, t + 1500)
        b = bisect.bisect_right(starts, t + length_ms - 1500)
        best.append((b - a, t))
        t += step
    best.sort(reverse=True)
    out = []
    for n, t in best:
        if n < 5:
            break
        if all(abs(t - u) > dur_ms * 0.15 for u in out):
            out.append(t)
        if len(out) >= count:
            break
    return sorted(out)


def _is_4k(video):
    name = (video.get('filename') or '').lower()
    return any(x in name for x in ('2160p', '4k', 'uhd', 'remux'))


def finetune_offset(cues, video, abort=None, progress=None):
    """Listen to a little of the film and measure the small constant gap left between the
    subtitle and the speech. Local files: 4 one-minute pieces. Internet streams: only the
    2 busiest dialogue moments, 30 s each (15 s for 4K) — one time per film.
    Returns ms to shift, 0 when already right, None when it could not tell."""
    from . import audiosync
    eng = ffmpeg_path()
    if not eng:
        return None
    try:
        src, args, remote = audiosync.media_source(video.get('path'))
    except audiosync.AudioSyncError:
        return None
    audiosync.STATS.update(short=0, refused=0)
    dur = video.get('duration') or (max(c.end for c in cues) / 1000.0 if cues else 0)
    if dur < 600 or not cues:
        return None
    if remote:
        length = 15000 if _is_4k(video) else 30000
        wins_ms = _dense_windows(cues, int(dur * 1000), length, 2)
    else:
        length = 60000
        wins_ms = [int(dur * f * 1000) for f in (0.15, 0.38, 0.62, 0.85)]
    if not wins_ms:
        return None
    per, wl, tw = [], [], []
    for k, w0 in enumerate(wins_ms):
        if progress:
            progress(85 + k * 3, 'ضبط دقيق على الصوت (%d/%d)...' % (k + 1, len(wins_ms)))
        try:
            pcm = audiosync._run_ffmpeg(eng, src, args, start=w0 / 1000.0, dur=length / 1000.0,
                                        abort=abort, timeout=180 if remote else 120)
        except audiosync.AudioSyncError as e:
            if 'aborted' in str(e):
                raise
            log('finetune: read failed: %s' % e)
            continue
        sp = sorted((c.start, c.end) for c in audiosync.detect_speech(pcm, offset_ms=w0))
        inside = [(c.start, c.end) for c in cues if w0 + 1500 <= c.start <= w0 + length - 1500]
        if len(inside) < 5 or len(sp) < 5:
            continue
        base = sync._overlap(inside, sp)
        d, score = sync._refine(inside, sp, 1.0, 0, 1500, 20)
        dur_in = sum(e - s for s, e in inside) or 1
        per.append((d, score, base, score / float(dur_in)))
        wl.append((inside, sp))
        tw.append((w0, inside, sp))
        log('finetune window @%ds: shift %d ms (overlap %d → %d)' % (w0 // 1000, d, base, score))
    try:
        trace.windows(video, 'finetune', tw, dict(audiosync.STATS, asked=len(wins_ms), heard=len(tw),
                                                  each=[p[0] for p in per]))
    except Exception:
        pass
    if not per:
        return None
    if len(per) >= 2:
        ds = sorted(p[0] for p in per)
        if ds[-1] - ds[0] > 300:
            # same direction and close (e.g. -1500 / -1110): the gap is real, take the
            # middle if that helps every window; opposite directions: don't guess
            if ds[-1] - ds[0] <= 600 and (ds[0] >= 0 or ds[-1] <= 0):
                dj = int(round(sum(ds) / float(len(ds)) / 10.0)) * 10
                sc = [sync._overlap(_shifted(ins, dj), sp) for ins, sp in wl]
                bases = [p[2] for p in per]
                if all(x >= b * 1.03 for x, b in zip(sc, bases)) and abs(dj) >= 80 and \
                        chance_lift(wl, dj) >= MIN_LIFT:
                    log('finetune: windows %s agree on the direction → %+d ms' % (ds, dj))
                    return dj
            log('finetune: windows disagree %s' % ds)
            return None
        d = ds[len(ds) // 2]
        # two separate moments agreeing on the same shift is strong evidence by itself
        gain_ok = (ds[-1] - ds[0] <= 150 and all(p[1] >= p[2] * 1.02 for p in per)) or \
            sum(p[1] for p in per) >= sum(p[2] for p in per) * 1.06
    else:
        d, score, base, cov = per[0]
        gain_ok = score >= base * 1.12 and cov > 0.4      # one window: be stricter
    if abs(d) < 80 or not gain_ok:
        return 0
    lift = chance_lift(wl, d)
    if lift < MIN_LIFT:
        log('finetune: %+d ms is no better than chance (lift %.2f) — leaving the timing alone' % (d, lift))
        return None
    return d


def _window_shift(inside, sp, span=6000):
    """Best shift (ms) of the subtitle lines in one listening window, or None if unsure."""
    scores = []
    d = -span
    while d <= span:
        scores.append((d, sync._overlap([(a + d, b + d) for a, b in inside], sp)))
        d += 100
    best_d, best = max(scores, key=lambda x: x[1])
    if best <= 0:
        return None
    second = max([sc for dd, sc in scores if abs(dd - best_d) > 700] or [0])
    fine, score = sync._refine(inside, sp, 1.0, best_d, 120, 10)
    dur_in = sum(b - a for a, b in inside) or 1
    cov = score / float(dur_in)
    if cov < 0.3 or score < second * 1.08:
        return None
    return fine, cov


def _shifted(iv, d):
    return [(a + d, b + d) for a, b in iv]


def _curve(windows, span=6000, step=100):
    """Overlap score of every shift, summed over all windows (one joint measurement)."""
    out = []
    d = -span
    while d <= span:
        out.append((d, sum(sync._overlap(_shifted(ins, d), sp) for ins, sp in windows)))
        d += step
    return out


def _peaks(scores, sep=700):
    """Best shift and the best *separate* peak: [(shift, score), ...] high→low.
    A second peak counts only if the curve dips between them (not the main peak's shoulder)."""
    best_i = max(range(len(scores)), key=lambda i: scores[i][1])
    best = scores[best_i]
    out = [best]
    cand = []
    for i in range(1, len(scores) - 1):
        d, sc = scores[i]
        if abs(d - best[0]) <= sep or sc <= 0 or sc < scores[i - 1][1] or sc < scores[i + 1][1]:
            continue
        lo, hi = sorted((i, best_i))
        dip = min(x[1] for x in scores[lo:hi + 1])
        if dip < sc * 0.85:
            cand.append((d, sc))
    if cand:
        out.append(max(cand, key=lambda x: x[1]))
    return out


def _fine(windows, d0, span=120, step=10):
    best = (d0, sum(sync._overlap(_shifted(ins, d0), sp) for ins, sp in windows))
    d = d0 - span
    while d <= d0 + span:
        sc = sum(sync._overlap(_shifted(ins, d), sp) for ins, sp in windows)
        if sc > best[1]:
            best = (d, sc)
        d += step
    return best


def chance_lift(windows, d):
    # d: one shift for all windows, or a list with each window's own shift
    """How much better than pure chance the shift d fits. With speech everywhere (music,
    a narrator, noise) ANY shift overlaps a lot; what counts is the overlap above what the
    same amount of subtitle and speech would give at random."""
    got = exp = 0.0
    ds = d if isinstance(d, (list, tuple)) else [d] * len(windows)
    for (ins, sp), dw in zip(windows, ds):
        if not ins or not sp:
            continue
        lo = min(ins[0][0], sp[0][0])
        hi = max(max(b for _a, b in ins), max(b for _a, b in sp))
        span = float(max(1, hi - lo))
        dens = min(1.0, sum(b - a for a, b in sp) / span)
        exp += sum(b - a for a, b in ins) * dens
        got += sync._overlap(_shifted(ins, dw), sp)
    return got / exp if exp > 0 else 0.0


MIN_LIFT = 1.12
LAST_LIFT = [0.0]


def joint_shift(windows, span=6000):
    """Like ffsubsync's multi-segment sync: the windows are scored together, so the right
    shift adds up across all of them while each window's chance matches cancel out.
    Returns (shift_ms, coverage) or None when the evidence is not clear."""
    if not windows:
        return None
    pk = _peaks(_curve(windows, span))
    if pk[0][1] <= 0:
        return None
    fine, fs = _fine(windows, pk[0][0])
    dur_in = sum(b - a for ins, _sp in windows for a, b in ins) or 1
    cov = fs / float(dur_in)
    second = pk[1][1] if len(pk) > 1 else 0
    need = 1.08 if len(windows) == 1 else 1.04
    if cov < 0.25 or fs < second * need:
        return None
    if chance_lift(windows, fine) < MIN_LIFT:
        return None          # no better than chance: the sound doesn't follow this subtitle
    return fine, cov


def _which_shift(inside, sp, d_a, d_b, margin=1.12):
    """Which of two shifts fits this window clearly better? (None = can't tell)"""
    sa = sync._overlap(_shifted(inside, d_a), sp)
    sb = sync._overlap(_shifted(inside, d_b), sp)
    if max(sa, sb) <= 0:
        return None
    if sa >= sb * margin:
        return d_a
    if sb >= sa * margin:
        return d_b
    return None


def sections_from_windows(data, min_run=2):
    """data: [(time_ms, subtitle_lines, speech)] in film order.
    1. score all windows together: one clear shift for the film, or two (a cut part);
    2. each window says which of those shifts fits it; a window may only bring a shift of
       its own when its evidence is clear and clearly better;
    3. a section needs at least `min_run` neighbouring windows agreeing — a lone window
       (at the edges too) never moves a whole part of the film.
    Returns (main_shift, [(time_ms, shift_ms)]) or None."""
    if len(data) < 3:
        return None
    wl = [(ins, sp) for _t, ins, sp in data]
    pk = _peaks(_curve(wl))
    if pk[0][1] <= 0:
        return None
    c0, s0 = _fine(wl, pk[0][0])
    cands = [c0]
    dur_in = sum(b - a for ins, _sp in wl for a, b in ins) or 1
    two = False
    if len(pk) > 1 and pk[1][1] >= pk[0][1] * 0.45:
        # maybe two parts with different shifts (a cut scene): keep the second shift only
        # if it explains the sound much better and whole neighbouring windows ask for it
        c1 = _fine(wl, pk[1][0])[0]
        prefs = [_which_shift(ins, sp, c0, c1, 1.2) for ins, sp in wl]
        s2 = sum(max(sync._overlap(_shifted(ins, c0), sp), sync._overlap(_shifted(ins, c1), sp))
                 for ins, sp in wl)
        pair = any(prefs[k] == c1 and prefs[k + 1] == c1 for k in range(len(prefs) - 1))
        if s2 >= s0 * 1.06 and pair:
            cands.append(c1)
            two = True
    if s0 / float(dur_in) < 0.25 or (not two and len(pk) > 1 and s0 < pk[1][1] * 1.04):
        log('sections: windows together give no clear answer')
        return None
    if two:
        best_each = [max(cands, key=lambda c: sync._overlap(_shifted(ins, c), sp)) for ins, sp in wl]
        lift = chance_lift(wl, best_each)
    else:
        lift = chance_lift(wl, c0)
    LAST_LIFT[0] = lift
    if lift < MIN_LIFT:
        log('sections: best shift is no better than chance (lift %.2f): the sound does not follow '
            'this subtitle (other cut, music or narration)' % lift)
        return None
    log('sections: joint shift %s from %d windows' % (' / '.join('%+d ms' % c for c in cands), len(data)))
    # the main shift must be confirmed by at least two windows that are clear ON THEIR OWN —
    # a joint answer carried by a single window (the others just 'unclear') moves nothing
    own_r = [_window_shift(ins, sp) for ins, sp in wl]
    support = sum(1 for r in own_r if r and abs(r[0] - c0) <= 350)
    if support < 2:
        log('sections: only %d window(s) clearly agree with %+d ms — leaving the timing alone' % (support, c0))
        return None

    lab = []
    for t, ins, sp in data:
        got = None
        if len(cands) == 2:
            got = _which_shift(ins, sp, cands[0], cands[1])
        r = _window_shift(ins, sp)
        if got is None and r:
            near = [c for c in cands if abs(r[0] - c) <= 350]
            if near:
                got = near[0]
        if r and all(abs(r[0] - c) > 350 for c in cands):
            s_own = sync._overlap(_shifted(ins, r[0]), sp)
            if all(s_own >= sync._overlap(_shifted(ins, c), sp) * 1.25 for c in cands):
                got = r[0]
        log('sections: window @%ds → %s' % (t // 1000, 'unclear' if got is None else '%+d ms' % got))
        lab.append(got)
    own = list(lab)
    # windows without a clear answer of their own, next to a window that differs: ask
    # them which of the two shifts fits better
    for _ in range(3):
        for k in range(len(lab)):
            if own[k] is not None:
                continue
            near = set(lab[x] for x in (k - 1, k + 1) if 0 <= x < len(lab) and lab[x] is not None)
            base = lab[k] if lab[k] is not None else cands[0]
            for other in near - {base}:
                pick = _which_shift(data[k][1], data[k][2], base, other)
                if pick is not None:
                    lab[k] = pick
                    break
    if len(cands) == 1:
        lab = [cands[0] if v is None else v for v in lab]     # still unclear: follow the film

    def runs(values):
        out, k = [], 0
        while k < len(values):
            m = k
            while m + 1 < len(values) and values[m + 1] is not None and values[k] is not None and \
                    abs(values[m + 1] - values[k]) <= 400:
                m += 1
            out.append((k, m))
            k = m + 1
        return out

    # unclear windows take the side their neighbours agree on (or the nearer clear one)
    for k in range(len(lab)):
        if lab[k] is None:
            left = next((lab[x] for x in range(k - 1, -1, -1) if lab[x] is not None), None)
            right = next((lab[x] for x in range(k + 1, len(lab)) if lab[x] is not None), None)
            lab[k] = left if left is not None else right
    if any(v is None for v in lab):
        return None
    # lone windows never make a section: they follow the longer neighbouring section
    for _ in range(3):
        rs = runs(lab)
        new = list(lab)
        for n, (a, b) in enumerate(rs):
            if b - a + 1 >= min_run:
                continue
            nbs = [rs[x] for x in (n - 1, n + 1) if 0 <= x < len(rs)]
            if not nbs:
                continue
            nbs.sort(key=lambda r: -(r[1] - r[0]))
            long_ = [r for r in nbs if r[1] - r[0] == nbs[0][1] - nbs[0][0]]
            log('sections: lone window @%ds ignored' % (data[a][0] // 1000))
            for x in range(a, b + 1):
                if len(long_) == 2 and lab[long_[0][0]] != lab[long_[1][0]]:
                    new[x] = _which_shift(data[x][1], data[x][2], lab[long_[0][0]], lab[long_[1][0]], 1.0) \
                        or lab[long_[0][0]]
                else:
                    new[x] = lab[long_[0][0]]
        if new == lab:
            break
        lab = new
    # each run takes its median shift
    out = list(lab)
    for a, b in runs(lab):
        ds = sorted(lab[a:b + 1])
        for x in range(a, b + 1):
            out[x] = ds[len(ds) // 2]
    counts = {}
    for v in out:
        counts[v] = counts.get(v, 0) + 1
    main = max(counts, key=counts.get)
    return main, [(data[k][0], out[k]) for k in range(len(out))]


def section_offsets(cues, video, abort=None, progress=None):
    """Listen at many points across the whole film and measure the gap in each part.
    Returns [(from_ms, to_ms, shift_ms)] covering the film, or None if it could not tell.
    Different parts can need different shifts (a cut scene, a recap, a different intro)."""
    from . import audiosync
    eng = ffmpeg_path()
    if not eng or not cues:
        return None
    try:
        src, args, remote = audiosync.media_source(video.get('path'))
    except audiosync.AudioSyncError:
        return None
    audiosync.STATS.update(short=0, refused=0)
    dur = video.get('duration') or (max(c.end for c in cues) / 1000.0)
    if dur < 600:
        return None
    dur_ms = int(dur * 1000)
    if remote:
        count, length = (8, 15000) if _is_4k(video) else (8, 20000)
    else:
        count, length = 12, 40000
    # one busy-dialogue window inside each equal slice of the film
    starts = [c.start for c in cues]
    wins = []
    lo, hi = int(dur_ms * 0.03), int(dur_ms * 0.97)
    slice_len = (hi - lo) // count
    for k in range(count):
        a0, a1 = lo + k * slice_len, lo + (k + 1) * slice_len - length
        best = None
        t = a0
        while t <= a1:
            n = bisect.bisect_right(starts, t + length - 1500) - bisect.bisect_left(starts, t + 1500)
            if best is None or n > best[0]:
                best = (n, t)
            t += 10000
        if best and best[0] >= 5:
            wins.append(best[1])
    if len(wins) < 3:
        return None
    def listen(w0, ln):
        """(subtitle lines, detected speech) inside one window, or None."""
        inside = [(c.start, c.end) for c in cues if w0 + 1500 <= c.start and c.end <= w0 + ln - 1500]
        if len(inside) < 4:
            return None
        try:
            pcm = audiosync._run_ffmpeg(eng, src, args, start=w0 / 1000.0, dur=ln / 1000.0,
                                        abort=abort, timeout=180 if remote else 120)
        except audiosync.AudioSyncError as e:
            if 'aborted' in str(e):
                raise
            log('sections: read failed @%ds: %s' % (w0 // 1000, e))
            return None
        sp = sorted((c.start, c.end) for c in audiosync.detect_speech(pcm, offset_ms=w0))
        if len(sp) < 4:
            return None
        return inside, sp

    data = []
    for k, w0 in enumerate(wins):
        if progress:
            progress(84 + int(12 * k / len(wins)), 'ضبط كل قسم على الصوت (%d/%d)...' % (k + 1, len(wins)))
        r = listen(w0, length)
        if r:
            data.append((w0 + length // 2, r[0], r[1]))
    LAST_LIFT[0] = 0.0
    plan = sections_from_windows(data)
    trace.windows(video, 'sections', data, dict(audiosync.STATS, asked=len(wins), heard=len(data),
                                                 lift=round(LAST_LIFT[0], 3),
                                                 answer=plan and sorted(set(d for _t, d in plan[1]))))
    if not plan:
        trace.event(video, 'sections: no clear answer (%d of %d windows heard)' % (len(data), len(wins)))
        return None
    d0, labels = plan

    # group neighbouring windows with the same shift into sections
    groups = []
    for t, d in labels:
        if groups and groups[-1][1] == d:
            groups[-1][0].append(t)
        else:
            groups.append([[t], d])
    secs = []
    for i, (ts, shift) in enumerate(groups):
        if i == 0:
            start = 0
        else:
            # find where the change happens: listen in between (halving the gap) ...
            a, b = groups[i - 1][0][-1], ts[0]
            prev_shift = groups[i - 1][1]
            probe = 15000 if remote else 20000
            for _ in range(4):
                if b - a < 90000:
                    break
                mid = (a + b) // 2
                side = None
                for w0 in (mid - probe // 2, mid - probe * 2, mid + probe):   # a spot with dialogue
                    r = listen(w0, probe)
                    side = r and _which_shift(r[0], r[1], prev_shift, shift)
                    if side is not None:
                        break
                if side is None:
                    break
                if side == prev_shift:
                    a = w0 + probe
                else:
                    b = w0
            # ... then cut at the longest silence left in that range
            best_gap, cut = -1, (a + b) // 2
            for k in range(1, len(cues)):
                if a <= cues[k].start <= b:
                    gap = cues[k].start - cues[k - 1].end
                    if gap > best_gap:
                        best_gap, cut = gap, cues[k].start - min(gap // 2, 1000)
            start = cut
        secs.append([start, None, 0 if abs(shift) < 80 else shift])
    for i in range(len(secs) - 1):
        secs[i][1] = secs[i + 1][0]
    secs[-1][1] = dur_ms + 3600000
    log('sections: %s' % [(a // 1000, d) for a, _b, d in secs])
    trace.event(video, 'sections: %s' % [(a // 1000, d) for a, _b, d in secs])
    return [tuple(x) for x in secs]


# ---------------------------------------------------------------- Piers edition
def sync_external(src, video, progress=None):
    """Time a subtitle that another add-on (or a file beside the video) put on
    the player, the same way Najd times its own: on the video's own subtitle
    timeline (MKV index) at once, else on the sound in the background.
    Returns (path, mode, summary_lines) - mode 'now' (path is ready, show it),
    'job' (queued; process_jobs swaps it in when done), 'same' (already in
    time, nothing to change) - or None when it cannot be timed here."""
    def step(pct, msg):
        if progress:
            progress(pct, msg)

    with open(src, 'rb') as f:
        raw = f.read()
    text = arabic.decode(raw)
    cues = subtitle.parse(text, video.get('fps') or 23.976)
    if len(cues) < 20:
        log('external sync: %s has %d lines - skipped' % (os.path.basename(src), len(cues)))
        return None
    is_ar = arabic._arabic_ratio(' '.join(c.text for c in cues[:200])) > 0.3
    item = {'lang': 'ar' if is_ar else 'xx', 'external': src}
    summary = []
    if is_ar and setting_bool('fix_arabic', True):
        cues, _st = arabic.fix_cues(cues, rtl_mode=setting('rtl_mode', 'rle'),
                                    remove_ads=setting_bool('remove_ads', True), remove_hi=False)
    method = setting('sync_method', 'smart')
    emb_ok = same = False
    if method in ('smart', 'auto', 'subtitle', 'audio') and setting_bool('embedded_ref', True):
        step(30, 'قراءة توقيت الترجمة المدمجة في الفيديو...')
        emb = embedded_reference(video)
        if emb:
            new, einfo = sync.align(cues, emb, local=setting_bool('local_sync', True), min_lift=1.4)
            log('external sync on embedded: %s' % einfo)
            if new is not None:
                cues, emb_ok = new, True
                same = abs(einfo.get('offset', 0)) < 80 and abs(einfo.get('ratio', 1) - 1) < 1e-4 \
                    and not einfo.get('local_fixes')
                summary.append('تم ضبط الترجمة على الترجمة المدمجة في الفيديو ✓ (%s)' % sync.describe(einfo))
    steps = []
    if not emb_ok:
        try:
            from . import whisper as _wsp
            if setting_bool('whisper_sync', True) and _wsp.available() and \
                    (finetune_possible(video) if is_stream(video) else audio_possible(video)):
                # the free listening first; Whisper only when that is not sure (as process())
                steps = ['finetune', 'whisper'] if setting_bool('auto_finetune', True) else ['whisper']
        except Exception as e:
            log('external sync: whisper check: %s' % e)
        if steps:
            pass
        elif not is_stream(video) and audio_possible(video):
            steps.append('audio')
        elif is_stream(video) and setting_bool('stream_finetune', True) and finetune_possible(video):
            steps.append('finetune')
        elif is_stream(video) and audio_possible(video):
            steps.append('audio')
        if not steps:
            log('external sync: no embedded timeline and no audio for %s' % (video.get('filename') or ''))
            return None
    apply_offset(cues, user_offset(video))
    cues = subtitle.fix_timing(cues)
    path = najd_sub_path(video, 'ar', 'ext')
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(subtitle.to_srt(cues))
    remember_last(path, video, item)
    if steps:
        queue_job(path, video, item, steps)
        return path, 'job', ['جارٍ ضبط الترجمة على صوت الفيلم في الخلفية...']
    if same and not is_ar:
        return path, 'same', ['الترجمة مضبوطة أصلاً ✓']
    return path, 'now', summary


def apply_sections(cues, secs):
    for c in cues:
        for a, b, d in secs:
            if a <= c.start < b:
                if d:
                    c.start = max(0, c.start + d)
                    c.end = max(c.start + 200, c.end + d)
                break
    cues.sort(key=lambda c: c.start)
    return cues


def describe_sections(secs):
    def mmss(ms):
        return '%d:%02d' % (ms // 60000, (ms // 1000) % 60)
    parts = []
    for a, b, d in secs:
        parts.append('%s %+.1fث' % (mmss(a), d / 1000.0))
    return '، '.join(parts)


def finetune_possible(video):
    from . import audiosync
    if not ffmpeg_path():
        return False
    try:
        audiosync.media_source(video.get('path'))
        return True
    except audiosync.AudioSyncError:
        return False


def has_reference(video):
    return bool(cache_get('ref_%s.srt' % _video_key(video), 30 * 86400))


def remember_last(path, video, item, lineage=None):
    """The subtitle now on screen. `lineage` = the file it was made from by the add-on
    itself (a background step or the live check), so a later step can tell its own newer
    versions apart from a subtitle the viewer picked."""
    try:
        cache_put('last.json', json.dumps({'path': path, 'video': video.get('path', ''),
                                           'item': item, 'lineage': lineage or path}, ensure_ascii=False))
    except Exception:
        pass


def last_for(video):
    c = cache_get('last.json', 12 * 3600)
    if not c:
        return None
    try:
        d = json.loads(c.decode('utf-8'))
    except ValueError:
        cache_del('last.json')
        return None
    if d.get('video') == video.get('path') and os.path.exists(d.get('path', '')):
        return d
    return None


def queue_job(path, video, item, steps, resync=False, orig=None):
    job = {'path': path, 'video': video, 'item': item, 'steps': steps, 'resync': resync, 'orig': orig,
           'title': video.get('tvshow') or video.get('title') or '', 'time': time.time()}
    name = os.path.join(JOBS_DIR, 'job_%d.json' % int(time.time() * 1000))
    write_atomic(name, json.dumps(job, ensure_ascii=False))


def _write_version(job, cues, item, suffix, retimed=False):
    cues = [subtitle.Cue(c.start, c.end, c.text) for c in cues]
    if retimed:            # timing was rebuilt from a reference: re-apply your own offset
        apply_offset(cues, user_offset(job.get('video') or {}))
    cues = subtitle.fix_timing(cues)
    if item.get('lang', 'ar') == 'ar':
        cues, _st = arabic.fix_cues(cues, rtl_mode=setting('rtl_mode', 'rle'), remove_ads=False)
    base = job['path'][:-4]
    for suf in ('.synced', '.ai', '.v2'):
        if base.endswith(suf):
            base = base[:-len(suf)]
    new_path = base + suffix + '.srt'
    if new_path == job['path']:
        new_path = base + suffix + '.v2.srt'
    with open(new_path, 'w', encoding='utf-8-sig') as f:
        f.write(subtitle.to_srt(cues))
    return new_path


def _pack(iv):
    """[(a_ms, b_ms)...] → small ints (tenths of a second, each start from the last end)."""
    out, last = [], 0
    for a, b in iv:
        a, b = int(a) // 100, int(b) // 100
        out += [a - last, max(0, b - a)]
        last = b
    return out


def _trace_whisper(video, cues, ref, covered):
    """What Whisper heard and the subtitle's timing, kept small, for replaying the match."""
    try:
        trace.put(video, 'whisper_data', {'sub': _pack([(c.start, c.end) for c in cues]),
                                          'heard': _pack([(c.start, c.end) for c in ref]),
                                          'covered': _pack(covered)})
    except Exception:
        pass


def run_job(job, progress=None, abort=None, on_update=None, position=None):
    """Background steps on an already processed SRT.
    Text correction runs FIRST (small, quick) and is swapped in right away through
    on_update(path, lines); listening to the audio comes after.
    Returns (new_path or None, list of summary lines)."""
    if 'embedded_more' in job['steps']:
        return embedded_more(job, progress=progress, abort=abort, on_update=on_update, position=position)
    from . import audiosync
    with open(job['path'], 'rb') as f:
        cues = subtitle.parse(arabic.decode(f.read()))
    video, item = job['video'], job.get('item') or {}
    out = []
    changed = False
    audio_truth = False
    rebuilt = False          # timing rebuilt from a reference: your offset goes back on
    if 'verify' in job['steps'] and job.get('orig') and os.path.exists(job['orig']):
        try:
            with open(job['orig'], 'rb') as f:
                orig = subtitle.parse(arabic.decode(f.read()))
            apply_offset(orig, user_offset(video))
            verdict = audio_compare(orig, cues, video, abort=abort, progress=progress)
            log('verify: big reference jump — sound says %s' % {
                'a': 'the ORIGINAL timing is right', 'b': 'the reference is right'}.get(verdict, 'not sure'))
            if verdict == 'a':
                cues, changed, audio_truth = orig, True, True
                _mark_ref_bad(video)
                job = dict(job, steps=[st if st != 'semantic' else 'ai' for st in job['steps']])
                out.append('أثبت الصوت أن توقيت الترجمة الأصلي هو الصحيح — فأُعيد')
                if on_update:
                    on_update(_write_version(job, cues, item, '.synced'), list(out))
            elif verdict == 'b':
                _mark_ref_good(video)
        except Exception as e:
            if 'aborted' in str(e):
                return None, []
            log('verify failed: %s' % e)
    if 'semantic' in job['steps']:
        from . import semsync
        c = cache_get('ref_%s.srt' % _video_key(video), 30 * 86400)
        en = subtitle.parse(c.decode('utf-8', 'replace')) if c else []
        if en:
            def sem_progress(pct, k, total):
                if progress:
                    progress(pct, 'مطابقة الترجمة مع الإنجليزية (%d/%d)' % (k, total))

            def sem_partial(part, info):
                if on_update:
                    on_update(_write_version(job, part, item, '.ai-part', retimed=True),
                              ['ضُبطت الأسطر التالية ✓ ويكتمل الباقي...'])
            try:
                new, info = semsync.semantic_sync(cues, en, title=job.get('title', ''),
                                                  position=position, progress=sem_progress,
                                                  abort=abort, on_partial=sem_partial)
                log('semantic: %s' % info)
                if new is not None:
                    cues, changed, rebuilt = new, True, True
                    out.append(semsync.describe(info))
            except Exception as e:
                if 'aborted' in str(e):
                    return None, []
                log('semantic failed: %s' % e)
                from . import gemini
                if isinstance(e, gemini.QuotaExhausted):
                    out.append('نفد حد الذكاء الاصطناعي اليوم — الترجمة تعمل بتوقيت الإنجليزية')
                    job = dict(job, steps=[st for st in job['steps'] if st not in ('semantic', 'ai')])
                else:
                    job = dict(job, steps=[st for st in job['steps'] if st != 'semantic'] + ['ai'])
        else:
            job = dict(job, steps=[st for st in job['steps'] if st != 'semantic'] + ['ai'])
        if changed and on_update and 'audio' in job['steps']:
            on_update(_write_version(job, cues, item, '.ai', retimed=True), list(out))
    if 'ai' in job['steps']:
        from . import ai
        if progress:
            progress(5, 'تصحيح النص بالذكاء الاصطناعي...')
        try:
            def ai_progress(pct, k, total):
                if progress:
                    progress(5 + pct * 40 // 100 if any(st in job['steps'] for st in ('audio', 'understand'))
                             else pct, 'تصحيح النص بالذكاء الاصطناعي (%d/%d)' % (k, total))

            def ai_partial(tmp_cues, n):
                if on_update:
                    on_update(_write_version(job, tmp_cues, item, '.ai-part'),
                              ['صُحّحت الأسطر التالية (%d سطراً) ويكتمل الباقي...' % n])

            n = ai.proofread(cues, title=job.get('title', ''), abort=abort, position=position,
                             progress=ai_progress, on_partial=ai_partial)
            if n:
                changed = True
                out.append('تم تصحيح %d سطراً بالذكاء الاصطناعي' % n)
                if on_update and any(st in job['steps'] for st in ('audio', 'understand')):
                    on_update(_write_version(job, cues, item, '.ai'), list(out))
        except Exception as e:
            if 'aborted' in str(e):
                return None, []
            log('AI failed: %s' % e)
            from . import gemini
            if isinstance(e, gemini.QuotaExhausted):
                out.append('نفد حد الذكاء الاصطناعي اليوم — الترجمة تعمل دون تصحيح')
            else:
                out.append('مفتاح Gemini غير صحيح' if any(x in str(e) for x in ('no_key', '400', '403'))
                           else 'تعذر التصحيح بالذكاء الاصطناعي')
        if abort and abort():
            return None, []
    if 'audio' in job['steps']:
        try:
            new, info = audio_sync(cues, video, progress=progress, abort=abort)
            if new is not None:
                cues, changed, rebuilt = new, True, True
                out.append('تمت المزامنة مع الصوت: ' + sync.describe(info))
            else:
                out.append('الصوت لا يطابق الترجمة (ربما تكون الترجمة لنسخة أخرى)')
        except audiosync.AudioSyncError as e:
            if 'aborted' in str(e):
                return None, []
            log('audio sync failed: %s' % e)
            out.append(audiosync.describe_error(e))
            if any(x in str(e) for x in ('no_ffmpeg', 'unsupported_path', 'no_path')):
                job = dict(job, steps=[st for st in job['steps'] if st != 'understand'])
            if setting('sync_method', 'smart') in ('auto', 'smart') and not job.get('resync'):
                cues2, line = reference_sync_msg(cues, video, item)
                if cues2 is not cues:
                    cues, changed, rebuilt = cues2, True, True
                if line:
                    out.append(line)
    if 'understand' in job['steps']:
        try:
            new, info = understand_sync(cues, video, progress=progress, abort=abort)
            if new is not None:
                cues, changed, rebuilt = new, True, True
                out = [l for l in out if not l.startswith('تمت المزامنة مع الصوت')]
                out.append('فهم الكلام: ' + understand_describe(info))
            else:
                out.append('تعذرت مطابقة الكلام مع الترجمة (ربما تكون الترجمة لنسخة أخرى)')
        except audiosync.AudioSyncError as e:
            if 'aborted' in str(e):
                return None, []
            log('understand failed: %s' % e)
            out.append('تعذر فهم الكلام: ' + (
                'مفتاح Gemini غير صحيح' if any(x in str(e) for x in ('400', '403')) else
                'نفد حد Gemini المجاني، حاول لاحقاً' if '429' in str(e) else str(e)[:80]))
    if 'emb_alt' in job['steps']:
        # «re-time» on a video whose own subtitle gave the timing: look again piece by piece
        # (2-minute pieces over the whole video), so a part that went wrong gets its own shift
        from . import refalign
        emb = embedded_reference(video)
        if emb:
            dur = int(float(video.get('duration') or 0) * 1000) or (emb[-1].end + 60000)
            cov = [(t, t + 120000) for t in range(0, dur, 120000)]
            new, info = refalign.align([subtitle.Cue(c.start, c.end, c.text) for c in cues], emb, cov)
            trace.event(video, 'resync on embedded: %s' % (info,))
            if new is not None:
                cues, changed, audio_truth = new, True, True
                sh = info.get('shifts')
                out.append('أُعيد الضبط على الترجمة المدمجة: ' + (' / '.join('%+.1f ث' % (d / 1000.0) for d in sh)
                                                               if sh else '%+.1f ث' % (info['shift'] / 1000.0)))
            elif info == 'in_sync':
                out.append('التوقيت مطابق للترجمة المدمجة ✓')
            else:
                out.append('تعذّر تحسين التوقيت على الترجمة المدمجة')
    if 'finetune' in job['steps']:
        try:
            if changed and any(st in job['steps'] for st in ('semantic',)):
                # measure on what will actually be shown (reference timing + your offset)
                apply_offset(cues, user_offset(video))
                pre_offset = True
            else:
                pre_offset = False
            secs = section_offsets(cues, video, abort=abort, progress=progress) \
                if setting_bool('section_sync', True) else None
            if secs and len(set(x[2] for x in secs)) > 1:
                apply_sections(cues, secs)
                audio_truth = True
                changed = True
                out.append('ضبط كل قسم على الصوت: ' + describe_sections(secs))
                d = 'sections'
            elif secs:
                d = secs[0][2]
            else:
                d = finetune_offset(cues, video, abort=abort, progress=progress)
            if d == 'sections':
                pass
            elif d is None and pre_offset:
                apply_offset(cues, -user_offset(video))
            elif d is not None:
                apply_offset(cues, d)
                audio_truth = True
                changed = True
                if d:
                    out.append('ضبط دقيق على الصوت: %+.2f ث' % (d / 1000.0))
        except Exception as e:
            if 'aborted' in str(e):
                return None, []
            log('finetune failed: %s' % e)
    # Whisper only when the free listening above was not sure — it costs from the daily allowance
    if 'whisper' in job['steps'] and not audio_truth:
        from . import whisper as wsp, refalign
        try:
            pos = 0
            try:
                pos = int((position() if position else 0) or 0)
            except Exception:
                pos = 0
            base = [subtitle.Cue(c.start, c.end, c.text) for c in cues]
            new, info, stage = None, 'no_match', ''
            # a little first; more only while the answer is "same film, not sure yet"
            for stage in ('probe', 'probe2', 'more'):
                if stage == 'probe2' and info not in ('no_match', 'weak'):
                    break
                if stage == 'more' and info != 'weak':
                    break
                ref, covered = wsp.reference(video, _video_key(video), ffmpeg_path(),
                                             progress=progress, abort=abort, position_s=pos, stage=stage)
                new, info = refalign.align(base, ref, covered)
                trace.event(video, 'whisper %s: %d sentences, %s' % (stage, len(ref), info))
                _trace_whisper(video, base, ref, covered)
                if new is not None or info == 'in_sync':
                    break
            if new is not None:
                apply_offset(new, user_offset(video))      # your own fixed correction stays
                cues, changed, audio_truth = new, True, True
                out = [l for l in out if not l.startswith('ضبط دقيق على الصوت')]
                shifts = info.get('shifts')
                if shifts:
                    out.append('ضُبطت على كلام الفيلم (Whisper): الفيلم نسخة مقصوصة مختلفة، وضُبط كل جزء بإزاحته: %s'
                               % ' / '.join('%+.1f ث' % (d / 1000.0) for d in shifts))
                else:
                    out.append('ضُبطت على كلام الفيلم (Whisper): إزاحة %+.1f ث' % (info['shift'] / 1000.0))
                if on_update:      # show it now — do not wait for anything else
                    on_update(_write_version(job, cues, item, '.synced'), list(out))
            elif info == 'in_sync':
                out.append('Whisper: التوقيت مضبوط أصلاً ✓')
            elif info == 'weak':
                out.append('Whisper: الفيلم نفسه لكن التوقيت لم يتأكد — تُركت كما هي')
            else:
                out.append('استمع Whisper إلى الفيلم لكن الترجمة لا تطابق كلامه (ربما لفيلم أو نسخة أخرى)')
        except wsp.WhisperError as e:
            if 'aborted' in str(e):
                return None, []
            log('whisper failed: %s' % e)
            if str(e) == 'key':
                out.append('مفتاح Groq غير صحيح')
    try:
        trace.put(video, 'result', out or ['no change'])
        trace.put(video, 'took', int(time.time() - job.get('time', time.time())))
    except Exception:
        pass
    if not changed:
        return None, out
    synced = rebuilt or audio_truth
    return _write_version(job, cues, item, '.synced' if synced else '.ai',
                          retimed=rebuilt and not audio_truth), out
