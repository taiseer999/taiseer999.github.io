# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse


def size_to_bytes(value):
    try:
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value or '').strip().upper().replace('GIB', 'GB').replace('MIB', 'MB')
        m = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|KB|TB)', text)
        if not m:
            return 0
        num = float(m.group(1))
        unit = m.group(2)
        mult = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}.get(unit, 1)
        return int(num * mult)
    except Exception:
        return 0


def quality_rank(value):
    """Return quality tier (0-4) from entry dict or text blob."""
    if isinstance(value, dict):
        value = entry_text_blob(value)
    q = str(value or '').upper()
    if any(token in q for token in ('2160', '4K', 'UHD')):
        return 4
    if any(token in q for token in ('1080', 'FHD')):
        return 3
    if '720' in q:
        return 2
    if any(token in q for token in ('480', 'SD')):
        return 1
    return 0

def entry_text_blob(entry):
    return ' '.join([
        str(entry.get('quality') or ''),
        str(entry.get('badges') or ''),
        str(entry.get('name') or ''),
        str(entry.get('label2') or ''),
        str(entry.get('source_info') or ''),
        str(entry.get('addon') or ''),
        str(entry.get('source_site') or ''),
        str(entry.get('provider_name_raw') or ''),
        str(entry.get('provider') or ''),
    ]).upper()


def is_cam_entry(entry):
    blob = ' %s ' % entry_text_blob(entry)
    return any(token in blob for token in (' CAM ', ' CAMRIP ', ' HDCAM ', ' TS ', ' TELESYNC ', ' HDTS ', ' TC ', ' TELECINE ', ' SCREENER '))


def is_debrid_entry(entry):
    badge = str(entry.get('provider') or '').upper()
    return badge in ('RD+', 'AD+', 'PM', 'TB', 'ED+')


def entry_matches_last_source(entry, pref):
    if not pref:
        return False
    provider_name = str((pref or {}).get('provider_name') or '').strip().lower()
    provider_id = str((pref or {}).get('provider_id') or '').strip().lower()
    host = str((pref or {}).get('stream_url_host') or '').strip().lower()
    hay = ' '.join([
        str(entry.get('provider_name_raw') or '').lower(),
        str(entry.get('provider') or '').lower(),
        str(entry.get('addon') or '').lower(),
        str(entry.get('source_site') or '').lower(),
        str(entry.get('name') or '').lower(),
        str(entry.get('source_info') or '').lower(),
    ])
    if provider_name and provider_name in hay:
        return True
    if provider_id and provider_id in hay:
        return True
    stream_url = str(entry.get('stream_url') or '').strip()
    entry_host = (urlparse(stream_url).netloc or '').lower() if stream_url else ''
    if host and entry_host and host == entry_host:
        return True
    return bool(host and host in hay)


def _min_quality_required_rank(raw):
    mapping = {
        'بدون فلترة': 0, 'no filter': 0,
        '480p فأعلى': 1, '480p+': 1,
        '720p فأعلى': 2, '720p+': 2,
        '1080p فأعلى': 3, '1080p+': 3,
        '4k فقط': 4, '4k only': 4,
    }
    return mapping.get(str(raw or 'No filter').strip().lower(), 0)


def source_settings(addon):
    try:
        min_quality = addon.getSetting('min_quality') or 'No filter'
    except Exception:
        min_quality = 'No filter'

    def _bool(name, default=False):
        try:
            raw = (addon.getSetting(name) or ('true' if default else 'false')).strip().lower()
        except Exception:
            raw = 'true' if default else 'false'
        return raw in ('true', '1', 'yes', 'on')

    return {
        'hide_cam_ts': _bool('hide_cam_ts', True),
        'prefer_debrid': _bool('prefer_debrid', True),
        'prefer_hdr': _bool('prefer_hdr', True),
        'prefer_atmos': _bool('prefer_atmos', True),
        'min_quality_rank': _min_quality_required_rank(min_quality),
    }


def filter_stream_entries(entries, settings):
    filtered = list(entries or [])
    if settings.get('hide_cam_ts', True):
        filtered = [e for e in filtered if not is_cam_entry(e)]
    min_rank = int(settings.get('min_quality_rank', 0) or 0)
    if min_rank > 0:
        filtered = [e for e in filtered if (quality_rank(e) or quality_rank(e.get('quality'))) >= min_rank]
    return filtered


def stream_sort_key(entry, settings, preferred_source=None):
    badge_text = str(entry.get('badges') or '').upper()
    # User-facing source order: quality first, then size. Debrid/source memory
    # remain tie-breakers only, so a preferred source does not outrank a better
    # quality/size result.
    q_rank = quality_rank(entry) or quality_rank(entry.get('quality'))
    size_rank = size_to_bytes(entry.get('size_label'))
    hdr_bonus = 0
    if settings.get('prefer_hdr', True) and any(x in badge_text for x in ('DV', 'DOVI', 'HDR10+', 'HDR10', 'HDR')):
        hdr_bonus = 1
    audio_bonus = 0
    if settings.get('prefer_atmos', True):
        for token, score in (('ATMOS', 6), ('TRUEHD', 5), ('DTS-X', 4), ('DTS-HD', 3), ('DD+', 2), ('7.1', 2), ('5.1', 1)):
            if token in badge_text:
                audio_bonus = max(audio_bonus, score)
    debrid_bonus = 1 if (settings.get('prefer_debrid', True) and is_debrid_entry(entry)) else 0
    remembered_bonus = 1 if entry_matches_last_source(entry, preferred_source) else 0
    return (
        q_rank,
        size_rank,
        debrid_bonus,
        remembered_bonus,
        hdr_bonus,
        audio_bonus,
        str(entry.get('addon') or ''),
        str(entry.get('name') or ''),
    )

def renumber_stream_entries(entries):
    ordered = list(entries or [])
    for idx, row in enumerate(ordered, start=1):
        row['count'] = '%02d.' % idx
    return ordered


def finalize_stream_entries(entries, settings, preferred_source=None, resort=True):
    original = list(entries or [])
    filtered = filter_stream_entries(original, settings)
    ordered_source = filtered if filtered else original
    if resort:
        ordered = sorted(ordered_source, key=lambda e: stream_sort_key(e, settings, preferred_source=preferred_source), reverse=True)
    else:
        ordered = list(ordered_source)
    return renumber_stream_entries(ordered)

# ── Regex-based stream facts ────────────────────────────────────────────────
_STREAM_REGEX_RULES = [
    ('resolution', '2160P', r'(?<!\d)(?:2160p|4k|uhd)(?!\d)'),
    ('resolution', '1080P', r'(?<!\d)1080p?(?!\d)'),
    ('resolution', '720P',  r'(?<!\d)720p?(?!\d)'),
    ('resolution', '480P',  r'(?<!\d)480p?(?!\d)'),
    ('resolution', 'SD',    r'\b(?:sd|576p|360p)\b'),
    ('dynamic_range', 'DV', r'\b(?:dolby[ ._-]?vision|dovi|dv)\b'),
    ('dynamic_range', 'HDR10+', r'\bhdr10\+\b'),
    ('dynamic_range', 'HDR10', r'\bhdr10\b'),
    ('dynamic_range', 'HDR', r'\b(?:hdr|hlg)\b'),
    ('video_codec', 'AV1', r'\bav1\b'),
    ('video_codec', 'HEVC', r'\b(?:hevc|h\.265|x265|h265)\b'),
    ('video_codec', 'H264', r'\b(?:h\.264|x264|h264|avc)\b'),
    ('source', 'REMUX', r'\b(?:remux|bdremux)\b'),
    ('source', 'BLURAY', r'\b(?:blu[ ._-]?ray|bdrip|brrip|bd25|bd50)\b'),
    ('source', 'WEB-DL', r'\b(?:web[ ._-]?dl|webdl)\b'),
    ('source', 'WEBRIP', r'\bweb[ ._-]?rip\b'),
    ('source', 'HDTV', r'\bhdtv\b'),
    ('audio_codec', 'ATMOS', r'\batmos\b'),
    ('audio_codec', 'TRUEHD', r'\btrue[ ._-]?hd\b'),
    ('audio_codec', 'DTS-X', r'\bdts[ ._-]?x\b'),
    ('audio_codec', 'DTS-HD', r'\bdts[ ._-]?hd(?:[ ._-]?ma)?\b'),
    ('audio_codec', 'DTS', r'\bdts\b'),
    ('audio_codec', 'DD+', r'\b(?:dd\+|eac3|e-ac-3|ec-3|dolby[ ._-]?digital[ ._-]?plus)\b'),
    ('audio_codec', 'DD', r'\b(?:ac3|ac-3|dolby[ ._-]?digital)\b'),
    ('audio_channels', '7.1', r'\b7[ ._-]?1\b'),
    ('audio_channels', '5.1', r'\b5[ ._-]?1\b'),
    ('audio_channels', '2.0', r'\b2[ ._-]?0\b'),
    ('language', 'MULTI', r'\b(?:multi|multilang|dual[ ._-]?audio)\b'),
    ('language', 'AR', r'\b(?:arabic|ara|ar)\b|[\u0600-\u06FF]'),
    ('flags', 'SUBS', r'\b(?:subbed|subs|subtitles?)\b'),
    ('flags', 'DUBBED', r'\b(?:dubbed|dub)\b'),
]
_COMPILED_STREAM_REGEX_RULES = [(g, n, re.compile(p, re.I)) for g, n, p in _STREAM_REGEX_RULES]


def parse_stream_traits(*parts):
    text = ' | '.join(str(p) for p in parts if p not in (None, '', [], {}, ()))
    groups = {}
    ordered = []
    if not text:
        return {'resolution': '', 'video_bits': [], 'audio_bits': [], 'source_bits': [], 'tags': [], 'groups': groups}
    for group, name, regex in _COMPILED_STREAM_REGEX_RULES:
        try:
            if not regex.search(text):
                continue
        except Exception:
            continue
        bucket = groups.setdefault(group, [])
        if name not in bucket:
            bucket.append(name)
        if name not in ordered:
            ordered.append(name)
    resolution = ''
    for q in ('2160P', '1080P', '720P', '480P', 'SD'):
        if q in groups.get('resolution', []):
            resolution = q
            break
    video_bits = []
    for key in ('resolution', 'dynamic_range', 'video_codec', 'source'):
        for val in groups.get(key, []):
            if val not in video_bits:
                video_bits.append(val)
    audio_bits = []
    for key in ('audio_codec', 'audio_channels', 'language', 'flags'):
        for val in groups.get(key, []):
            if val not in audio_bits:
                audio_bits.append(val)
    return {'resolution': resolution, 'video_bits': video_bits, 'audio_bits': audio_bits, 'source_bits': list(groups.get('source', [])), 'tags': ordered, 'groups': groups}


def _enhanced_quality_rank(value):
    """Enhanced quality_rank using regex-based stream trait parsing."""
    if isinstance(value, dict):
        value = entry_text_blob(value)
    traits = parse_stream_traits(value)
    q = traits.get('resolution') or str(value or '').upper()
    if any(token in q for token in ('2160', '4K', 'UHD')):
        return 4
    if any(token in q for token in ('1080', 'FHD')):
        return 3
    if '720' in q:
        return 2
    if any(token in q for token in ('480', 'SD')):
        return 1
    return 0
