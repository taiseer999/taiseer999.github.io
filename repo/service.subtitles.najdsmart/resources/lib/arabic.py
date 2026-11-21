# -*- coding: utf-8 -*-
"""Arabic subtitle repair: encoding, letters, punctuation, RTL marks, ads, HI.
Pure Python (no Kodi imports) so it can be tested anywhere."""
import re

ARABIC_RE = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')
LATIN_RE = re.compile(r'[A-Za-z]')
BIDI_MARKS = '‎‏‪‫‬‭‮⁦⁧⁨⁩؜'
RLE, PDF, RLM = '‫', '‬', '‏'

# Leading/trailing punctuation that broken (pre-bidi) Arabic subs put on the wrong side
_PUNCT = '.!?؟،,:;؛…"\'»«'
_LEAD_PUNCT = re.compile(r'^((?:<[^>]+>)*)([%s]+)\s*(.*?)$' % re.escape(_PUNCT), re.S)
_TRAIL_DASH = re.compile(r'^(.*?\S)\s*-\s*((?:</[^>]+>)*)$', re.S)

AD_PATTERNS = [
    r'https?://', r'www\.', r'\b[\w-]+\.(?:com|net|org|tv|me|co|io|ws|xyz|cc|info)\b',
    r'opensubtitles', r'subscene', r'subdl', r'subsource', r'yts', r'yify',
    r'advertise your product', r'support us and become vip', r'osdb\.link',
    r'تيليجرام|تلغرام|telegram', r'انستقرام|إنستغرام|instagram',
    r'تابعونا|تابعوني|للاعلان|للإعلان|اشترك في القناة',
]
CREDIT_PATTERNS = [
    r'^\s*(?:ترجمة|ترجمه|تعريب|تدقيق|مراجعة|تعديل(?: ال)?توقيت|ضبط(?: ال)?توقيت|تزامن|سينك|مزامنة)\s*[:：\-]?',
    r'(?:ترجمة|ترجمه)\s*(?:و|\+)\s*(?:تعديل|ضبط)',
    r'^\s*(?:subtitles?|subbed|translated|synced|sync|resync|corrected|ripped)\s+(?:by|:)',
    r'(?:نتمنى لكم|أتمنى لكم|اتمنى لكم)\s+(?:مشاهدة|مشاهده)\s+(?:ممتعة|ممتعه)',
]
_AD_RE = re.compile('|'.join(AD_PATTERNS), re.I)
BRAND_PATTERNS = [r'opensubtitles', r'subscene', r'subdl\.com', r'subsource\.net', r'osdb\.link',
                  r'advertise your product', r'support us and become vip', r'yts\.(?:mx|am|lt)',
                  r'api\.opensubtitles']
_BRAND_RE = re.compile('|'.join(BRAND_PATTERNS), re.I)
_CREDIT_RE = re.compile('|'.join(CREDIT_PATTERNS), re.I | re.M)


# ---------------------------------------------------------------- encoding
def _arabic_ratio(text):
    letters = len(ARABIC_RE.findall(text)) + len(LATIN_RE.findall(text))
    return len(ARABIC_RE.findall(text)) / float(letters) if letters else 0.0


def _mojibake_score(text):
    # UTF-8 Arabic read as cp1252/latin-1 → Ø§ Ù„ ... ; cp1256 read as cp1252 → Ç á Ó
    return len(re.findall(r'[ØÙÚÛ][\x80-\xBFŒœŠšŸŽžƒˆ˜–-›€™]', text)) + \
        len(re.findall(r'[ÇáÓÊÑÏÌÍÎÐÒÔÕÖØÙÚÛÜÝÞßàâäæçèéêëìíîïñòóôõöùûü]{3,}', text))


def decode(data, letters=True):
    """bytes → best-effort correct unicode text (encoding, mojibake, mirrored letters)."""
    if data.startswith(b'\xef\xbb\xbf'):
        text = data[3:].decode('utf-8', 'replace')
    elif data.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = data.decode('utf-16', 'replace')
    else:
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            candidates = []
            for enc in ('cp1256', 'iso-8859-6', 'cp1252'):
                try:
                    t = data.decode(enc)
                    candidates.append((_arabic_ratio(t), t))
                except UnicodeDecodeError:
                    continue
            text = max(candidates, key=lambda x: x[0])[1] if candidates else \
                data.decode('utf-8', 'replace')
    text = repair_mojibake(text)
    if letters:
        text, _c = fix_letters(text)
    return text


def repair_mojibake(text):
    if _mojibake_score(text) < 5 or _arabic_ratio(text) > 0.5:
        return text
    best = text
    best_ratio = _arabic_ratio(text)
    for src, dst in (('cp1252', 'utf-8'), ('latin-1', 'utf-8'),
                     ('cp1252', 'cp1256'), ('latin-1', 'cp1256')):
        buf = bytearray()
        for ch in text:
            for enc in (src, 'latin-1'):
                try:
                    buf += ch.encode(enc)
                    break
                except UnicodeEncodeError:
                    continue
            else:
                buf += b'\x81' if ch == '�' else b'?'  # lost byte: best guess
        fixed = bytes(buf).decode(dst, 'replace')
        r = _arabic_ratio(fixed)
        if r > best_ratio + 0.2:
            best, best_ratio = fixed, r
    return best


# ---------------------------------------------------------------- reversed / glyph text
_PRES_RE = re.compile(r'[\uFB50-\uFDFF\uFE70-\uFEFF]')
_WORD_RE = re.compile(r'[\u0621-\u064A]+')
_LTR_RUN = re.compile(r'[0-9A-Za-z][0-9A-Za-z.,:%/\-]*[0-9A-Za-z]|[0-9A-Za-z]')


def _reverse_visual(line):
    """Visual-order line → logical order, keeping numbers/Latin runs readable."""
    tags = re.findall(r'<[^>]+>', line)
    bare = re.sub(r'<[^>]+>', '', line)
    rev = bare[::-1]
    rev = _LTR_RUN.sub(lambda m: m.group(0)[::-1], rev)
    swap = {'(': ')', ')': '(', '[': ']', ']': '[', '«': '»', '»': '«', '<': '>', '>': '<'}
    rev = ''.join(swap.get(ch, ch) for ch in rev)
    opening = ''.join(t for t in tags if not t.startswith('</'))
    closing = ''.join(t for t in tags if t.startswith('</'))
    return opening + rev + closing


def fix_letters(text):
    """Repair 'mirrored' Arabic: presentation-form glyphs and/or reversed letter order.
    Decided for the whole file. Returns (text, changed)."""
    import unicodedata
    pres = len(_PRES_RE.findall(text)) > max(20, len(ARABIC_RE.findall(text)) * 0.3)
    probe = unicodedata.normalize('NFKC', text) if pres else text
    words = _WORD_RE.findall(probe)
    starts = sum(1 for w in words if len(w) > 3 and w.startswith('ال'))
    ends = sum(1 for w in words if len(w) > 3 and w.endswith('لا'))
    reversed_ = ends >= 10 and ends > starts * 2
    if reversed_:
        # reverse BEFORE expanding ligatures (لا glyph must stay one unit)
        text = '\n'.join(_reverse_visual(l) if ARABIC_RE.search(l) and '-->' not in l else l
                         for l in text.split('\n'))
    if pres:
        text = unicodedata.normalize('NFKC', text)
    changed = pres or reversed_
    return text, changed


# ---------------------------------------------------------------- per line
_PERSIAN = str.maketrans({'ی': 'ي', 'ک': 'ك', 'ە': 'ه', 'ۀ': 'ة'})


def _is_arabic_line(s):
    return _arabic_ratio(s) >= 0.5


def _move_lead_punct(line):
    """'؟كيف حالك' → 'كيف حالك؟'   '...لا أعرف' → 'لا أعرف...'"""
    m = _LEAD_PUNCT.match(line)
    if not m:
        return line
    tags, punct, rest = m.groups()
    if not rest or not _is_arabic_line(rest):
        return line
    stripped = re.sub(r'<[^>]+>', '', rest).rstrip()
    if stripped and stripped[-1] in _PUNCT:  # already has ending punctuation
        return line
    # keep a leading ellipsis if the line also clearly continues ("...ثم")? rare; move.
    punct = punct.replace('?', '؟').replace(',', '،').replace(';', '؛')
    close = re.search(r'((?:</[^>]+>)*)$', rest).group(1)
    core = rest[:len(rest) - len(close)] if close else rest
    return tags + core.rstrip() + punct + close


def _move_trail_dash(line):
    """'كيف حالك؟ -' → '- كيف حالك؟' (dialogue dash on wrong side)."""
    m = _TRAIL_DASH.match(line)
    if not m:
        return line
    body, close = m.groups()
    if not _is_arabic_line(body):
        return line
    lead = re.match(r'^((?:<[^>]+>)*)(.*)$', body, re.S)
    return lead.group(1) + '- ' + lead.group(2).strip() + close


def _arabic_punctuation(line):
    if not _is_arabic_line(line):
        return line
    line = re.sub(r'(?<!\d),(?!\d)', '،', line)
    line = line.replace('?', '؟').replace(';', '؛')
    # no space before punctuation, one space after
    line = re.sub(r'\s+([،؛؟!.:…])', r'\1', line)
    line = re.sub(r'([،؛؟!:])(?=[^\s\d<"\'.!؟…])', r'\1 ', line)
    line = re.sub(r'\.{4,}', '...', line)
    line = re.sub(r'(?<!\.)\.\.(?!\.)', '...', line)
    line = re.sub(r'([؟!]){3,}', r'\1\1', line)
    line = re.sub(r'ـ{2,}', 'ـ', line)          # tatweel spam
    line = re.sub(r'[ \t]{2,}', ' ', line)
    return line.strip()


def _strip_hi(text):
    text = re.sub(r'[\[\(（][^\]\)）]{1,60}[\]\)）]', '', text)
    text = re.sub(r'♪+[^♪\n]*♪+|^\s*♪.*$', '', text, flags=re.M)
    text = re.sub(r'^\s*(?:-\s*)?[A-Z][A-Z .\'-]{1,25}:\s*', lambda m: '- ' if m.group(0).lstrip().startswith('-') else '', text, flags=re.M)
    text = re.sub(r'^\s*(?:-\s*)?[؀-ۿ]{2,15}(?: [؀-ۿ]{2,15})?\s*:\s+', '', text, flags=re.M)
    lines = [l.strip() for l in text.split('\n')]
    lines = [l for l in lines if l and l not in ('-', '- ')]
    return '\n'.join(lines)


def _clean_tags(text):
    text = re.sub(r'</?font[^>]*>', '', text, flags=re.I)
    text = re.sub(r'\{\\[^}]*\}', '', text)                    # leftover ASS tags
    text = re.sub(r'<(?!/?[ibu]>)[^>]*>', '', text, flags=re.I)  # keep <i><b><u>
    return text


def is_ad(text):
    plain = re.sub(r'<[^>]+>', '', text)
    return bool(_AD_RE.search(plain))


def is_brand_ad(text):
    return bool(_BRAND_RE.search(re.sub(r'<[^>]+>', '', text)))


def is_credit(text):
    plain = re.sub(r'<[^>]+>', '', text)
    return bool(_CREDIT_RE.search(plain)) and len(plain) < 120


_TAGS = re.compile(r'<[^>]+>|\{[^}]*\}')
_END_P = '.!?؟،,:;؛…'


def detect_style(cues):
    """Was this file written for players without RTL support (punctuation on the
    wrong side)? Decided for the whole file so correct files are never touched."""
    lead = trail = dash_end = dash_start = 0
    for c in cues:
        for raw in c.text.split('\n'):
            line = _TAGS.sub('', raw)
            for ch in BIDI_MARKS:
                line = line.replace(ch, '')
            line = line.strip()
            if len(line) < 3 or not _is_arabic_line(line):
                continue
            core = line.lstrip('- ').rstrip(' -')
            if core and core[0] in _END_P:
                lead += 1
            if core and core[-1] in _END_P:
                trail += 1
            if line.endswith('-') and not line.startswith('-'):
                dash_end += 1
            if line.startswith('-'):
                dash_start += 1
    rp = lead >= 3 and lead > trail * 1.5
    return {'reversed_punct': rp,
            'reversed_dash': dash_end > dash_start and dash_end >= (1 if rp else 3)}


def fix_line(line, rtl_mode='rle', style=None):
    style = style or {'reversed_punct': True, 'reversed_dash': True}
    for ch in BIDI_MARKS:
        line = line.replace(ch, '')
    line = line.translate(_PERSIAN)
    line = line.strip()
    if not line:
        return line
    if style.get('reversed_dash'):
        line = _move_trail_dash(line)
    if style.get('reversed_punct'):
        dm = re.match(r'^((?:<[^>]+>)*)(-\s*)(.*)$', line, re.S)
        if dm:
            line = dm.group(1) + '- ' + _move_lead_punct(dm.group(3))
        else:
            line = _move_lead_punct(line)
    line = _arabic_punctuation(line)
    if _is_arabic_line(line) or ARABIC_RE.search(line):
        if rtl_mode == 'rle':
            line = RLE + line
        elif rtl_mode == 'rlm':
            line = RLM + line + RLM
    return line


def fix_cues(cues, rtl_mode='rle', remove_ads=True, remove_hi=False):
    """In-place style repair. Returns (cues, stats)."""
    stats = {'ads': 0, 'changed': 0}
    out = []
    n = len(cues)
    style = detect_style(cues)
    stats.update(style)
    for idx, c in enumerate(cues):
        text = _clean_tags(c.text)
        if remove_ads:
            near_edge = idx < 8 or idx >= n - 8
            if is_brand_ad(text) or (near_edge and (is_ad(text) or is_credit(text))):
                stats['ads'] += 1
                continue
        if remove_hi:
            text = _strip_hi(text)
            if not text.strip():
                continue
        new_lines = [fix_line(l, rtl_mode, style) for l in text.split('\n')]
        new_text = '\n'.join(l for l in new_lines if l.strip(BIDI_MARKS + ' '))
        if not new_text:
            continue
        if new_text.replace(RLE, '').replace(RLM, '') != c.text:
            stats['changed'] += 1
        c.text = new_text
        out.append(c)
    return out, stats


def plain(text):
    """Text without bidi marks (for AI input / comparison)."""
    for ch in BIDI_MARKS:
        text = text.replace(ch, '')
    return text
