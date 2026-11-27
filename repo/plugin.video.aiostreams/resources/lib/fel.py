# -*- coding: utf-8 -*-
"""Curated Dolby Vision Profile 7 FEL movie catalog (merged from FEL Cinema).
Browsing is local (resources/data/fel_catalog.json); streams come from the
user's AIOStreams instance like everything else."""
import json
import os

from . import kodi

CATALOG_PATH = os.path.join(kodi.ADDON_PATH, 'resources', 'data', 'fel_catalog.json')
DECADES = ('2020', '2010', '2000', '1990', '1980', 'classic')

_CACHE = None


def load():
    global _CACHE
    if _CACHE is None:
        try:
            with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
                _CACHE = json.load(f)
        except (OSError, ValueError) as e:
            kodi.log('FEL catalog load failed: %s' % e)
            _CACHE = []
    return _CACHE


def find(imdb_id):
    imdb_id = str(imdb_id or '').split(':')[0]
    for m in load():
        if m.get('imdb_id') == imdb_id:
            return m
    return None


def is_fel_title(imdb_id):
    return find(imdb_id) is not None


def _year(m):
    try:
        return int(m.get('year') or 0)
    except (TypeError, ValueError):
        return 0


def _rating(m):
    try:
        return float(m.get('rating') or 0)
    except (TypeError, ValueError):
        return 0.0


def in_decade(m, key):
    y = _year(m)
    if key == 'classic':
        return 0 < y < 1980
    start = int(key)
    return start <= y < start + 10


GENRES_DIR = os.path.join(kodi.ADDON_PATH, 'resources', 'media', 'genres')

# Arabic (Fusha) names for the catalog's genres - labels only, filtering stays on the English name.
GENRES_AR = {
    'Action': 'حركة', 'Adventure': 'مغامرة', 'Animation': 'رسوم متحركة', 'Biography': 'سيرة ذاتية',
    'Comedy': 'كوميديا', 'Crime': 'جريمة', 'Documentary': 'وثائقي', 'Drama': 'دراما', 'Family': 'عائلي',
    'Fantasy': 'خيال', 'Film-Noir': 'فيلم نوار', 'History': 'تاريخ', 'Horror': 'رعب', 'Music': 'موسيقى',
    'Musical': 'استعراض موسيقي', 'Mystery': 'غموض', 'Romance': 'رومانسي', 'Sci-Fi': 'خيال علمي',
    'Sport': 'رياضة', 'Thriller': 'إثارة', 'War': 'حرب', 'Western': 'غربي',
}


def genre_tile(name):
    """Square tile for a genre (resources/media/genres/<Name>.jpg), '' if none."""
    path = os.path.join(GENRES_DIR, '%s.jpg' % name)
    return path if os.path.isfile(path) else ''


DECADES_DIR = os.path.join(kodi.ADDON_PATH, 'resources', 'media', 'decades')


def decade_tile(key):
    """Square tile for a decade key (2020 ... 1980, classic), '' if none."""
    path = os.path.join(DECADES_DIR, '%s.jpg' % key)
    return path if os.path.isfile(path) else ''


def genre_counts():
    counts = {}
    for m in load():
        for g in m.get('genres') or []:
            counts[g] = counts.get(g, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))


def movies(mode, value=''):
    cat = load()
    newest = lambda m: (-_year(m), -_rating(m), (m.get('title') or '').lower())
    if mode == 'top_rated':
        return sorted(cat, key=lambda m: (-_rating(m), -_year(m), (m.get('title') or '').lower()))
    if mode == 'az':
        return sorted(cat, key=lambda m: (m.get('title') or '').lower())
    if mode == 'decade':
        return sorted([m for m in cat if in_decade(m, value)], key=newest)
    if mode == 'genre':
        return sorted([m for m in cat if value in (m.get('genres') or [])], key=newest)
    if mode == 'search':
        q = (value or '').strip().lower()
        return sorted([m for m in cat if q in (m.get('title') or '').lower()
                       or q in (m.get('original_title') or '').lower()
                       or q == str(m.get('year') or '')], key=newest)
    return sorted(cat, key=newest)  # newest


def to_meta(m):
    """Stremio-shaped meta so items.meta_item can render it."""
    return {
        'id': m.get('imdb_id'),
        'type': 'movie',
        'name': m.get('title') or m.get('original_title'),
        'year': m.get('year'),
        'releaseInfo': str(m.get('year') or ''),
        'imdbRating': m.get('rating'),
        'runtime': m.get('runtime'),
        'genres': m.get('genres') or [],
        'description': m.get('plot') or '',
        'cast': m.get('cast') or [],
        'director': m.get('director') or [],
        'poster': m.get('poster'),
        'background': m.get('fanart'),
        'logo': m.get('logo'),
    }


def header(m):
    """Picker header for a catalog title."""
    return {
        'title': m.get('title') or '',
        'poster': m.get('poster') or '',
        'fanart': m.get('fanart') or '',
        'plot': m.get('plot') or '',
        'year': str(m.get('year') or ''),
        'rating': str(m.get('rating') or ''),
        'genre': ', '.join((m.get('genres') or [])[:3]),
        'duration': m.get('runtime') or '',
    }
