# -*- coding: utf-8 -*-
"""Parse SRT / VTT / ASS / MicroDVD into cues and write SRT. Pure Python."""
import html
import re

_TIME = r'(\d{1,2}):(\d{1,2}):(\d{1,2})(?:[,.:](\d{1,3}))?'
_SRT_TIME = re.compile(_TIME + r'\s*-->\s*' + _TIME)
_VTT_SHORT = re.compile(r'(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})[.,](\d{1,3})\s*-->\s*'
                        r'(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})[.,](\d{1,3})')
_MICRODVD = re.compile(r'^\{(\d+)\}\{(\d*)\}(.*)$')
_ASS_TIME = re.compile(r'(\d+):(\d{1,2}):(\d{1,2})[.:](\d{1,2})')


class Cue(object):
    __slots__ = ('start', 'end', 'text')

    def __init__(self, start, end, text):
        self.start = int(start)
        self.end = int(end)
        self.text = text

    def __repr__(self):
        return 'Cue(%d,%d,%r)' % (self.start, self.end, self.text)


def _ms(h, m, s, frac):
    frac = (frac or '0')
    frac_ms = int(frac.ljust(3, '0')[:3])
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + frac_ms


def detect_format(text):
    head = text.lstrip('﻿ \r\n\t')[:4000]
    if head.startswith('WEBVTT'):
        return 'vtt'
    if '[Script Info]' in head or re.search(r'^Dialogue:', text, re.M):
        return 'ass'
    if _MICRODVD.match(head.split('\n', 1)[0].strip()):
        return 'microdvd'
    if _SRT_TIME.search(head):
        return 'srt'
    if _VTT_SHORT.search(head):
        return 'vtt'
    return 'unknown'


def parse_srt(text):
    cues = []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    i, n = 0, len(lines)
    while i < n:
        m = _SRT_TIME.search(lines[i])
        if not m:
            i += 1
            continue
        g = m.groups()
        start = _ms(*g[0:4])
        end = _ms(*g[4:8])
        i += 1
        body = []
        while i < n:
            line = lines[i]
            if _SRT_TIME.search(line):
                # timing line without blank separator; drop trailing index number
                if body and body[-1].strip().isdigit():
                    body.pop()
                break
            if not line.strip():
                # blank: end of cue unless next non-blank is not index/time
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j >= n:
                    i = j
                    break
                nxt = lines[j].strip()
                nxt2 = lines[j + 1] if j + 1 < n else ''
                if (nxt.isdigit() and _SRT_TIME.search(nxt2)) or _SRT_TIME.search(nxt):
                    i = j
                    break
                body.append('')
                i += 1
                continue
            body.append(line.rstrip())
            i += 1
        txt = '\n'.join(l for l in body).strip('\n')
        if txt.strip():
            cues.append(Cue(start, end, txt))
    return cues


def parse_vtt(text):
    cues = []
    blocks = re.split(r'\n\s*\n', text.replace('\r\n', '\n').replace('\r', '\n'))
    for block in blocks:
        lines = block.strip('\n').split('\n')
        for k, line in enumerate(lines):
            m = _VTT_SHORT.search(line)
            if m:
                g = m.groups()
                start = _ms(g[0] or 0, g[1], g[2], g[3])
                end = _ms(g[4] or 0, g[5], g[6], g[7])
                body = '\n'.join(lines[k + 1:]).strip()
                body = re.sub(r'</?c[^>]*>|</?v[^>]*>', '', body)
                body = html.unescape(body)          # &amp; &lt; &nbsp; ...
                if body:
                    cues.append(Cue(start, end, body))
                break
    return cues


def parse_ass(text):
    cues = []
    fmt = None
    for raw in text.replace('\r\n', '\n').split('\n'):
        line = raw.strip()
        if line.lower().startswith('format:') and fmt is None and 'start' in line.lower():
            fmt = [f.strip().lower() for f in line.split(':', 1)[1].split(',')]
            continue
        if not line.startswith('Dialogue:'):
            continue
        fields = fmt or ['layer', 'start', 'end', 'style', 'name', 'marginl',
                         'marginr', 'marginv', 'effect', 'text']
        parts = line.split(':', 1)[1].split(',', len(fields) - 1)
        if len(parts) < len(fields):
            continue
        rec = dict(zip(fields, parts))
        ms = _ASS_TIME.match(rec.get('start', '').strip())
        me = _ASS_TIME.match(rec.get('end', '').strip())
        if not ms or not me:
            continue
        s = _ms(ms.group(1), ms.group(2), ms.group(3), ms.group(4).ljust(2, '0') + '0')
        e = _ms(me.group(1), me.group(2), me.group(3), me.group(4).ljust(2, '0') + '0')
        body = rec.get('text', '')
        italic = '{\\i1}' in body
        body = re.sub(r'\{[^}]*\}', '', body)
        body = body.replace('\\N', '\n').replace('\\n', '\n').replace('\\h', ' ').strip()
        if italic and body:
            body = '<i>%s</i>' % body
        if body:
            cues.append(Cue(s, e, body))
    cues.sort(key=lambda c: c.start)
    return cues


def parse_microdvd(text, fps=23.976):
    cues = []
    lines = text.replace('\r\n', '\n').split('\n')
    for line in lines:
        m = _MICRODVD.match(line.strip())
        if not m:
            continue
        f1, f2, body = m.groups()
        if f1 == '1' and f2 == '1':
            try:
                fps = float(body.strip())
            except ValueError:
                pass
            continue
        start = int(int(f1) * 1000 / fps)
        end = int(int(f2) * 1000 / fps) if f2 else start + 2500
        body = re.sub(r'\{[^}]*\}', '', body).replace('|', '\n').strip()
        if body:
            cues.append(Cue(start, end, body))
    return cues


def parse(text, fps=23.976):
    fmt = detect_format(text)
    if fmt == 'vtt':
        cues = parse_vtt(text)
    elif fmt == 'ass':
        cues = parse_ass(text)
    elif fmt == 'microdvd':
        cues = parse_microdvd(text, fps or 23.976)
    else:
        cues = parse_srt(text)
    return cues


def _fmt(ms):
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return '%02d:%02d:%02d,%03d' % (h, m, s, ms)


def to_srt(cues):
    out = []
    for idx, c in enumerate(cues, 1):
        out.append('%d\n%s --> %s\n%s\n' % (idx, _fmt(c.start), _fmt(c.end), c.text))
    return '\n'.join(out)


def fix_timing(cues, min_ms=700, chars_per_sec=17.0, gap_ms=40):
    """Sort, drop broken cues, remove overlaps, give short cues reading time."""
    cues = [c for c in cues if c.text.strip()]
    for c in cues:
        if c.end < c.start:
            c.start, c.end = c.end, c.start
    cues.sort(key=lambda c: (c.start, c.end))
    # merge exact duplicates
    dedup = []
    for c in cues:
        if dedup and dedup[-1].text == c.text and c.start - dedup[-1].end < 200:
            dedup[-1].end = max(dedup[-1].end, c.end)
            continue
        dedup.append(c)
    cues = dedup
    for i, c in enumerate(cues):
        nxt = cues[i + 1].start if i + 1 < len(cues) else None
        plain = re.sub(r'<[^>]+>', '', c.text)
        want = max(min_ms, int(len(plain) / chars_per_sec * 1000))
        if c.end - c.start < want:
            c.end = c.start + want
        if nxt is not None and c.end > nxt - gap_ms:
            c.end = max(c.start + 300, nxt - gap_ms)
            if c.end > nxt:  # cues start too close; keep minimal overlap
                c.end = nxt
    return cues
