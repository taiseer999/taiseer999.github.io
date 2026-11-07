# -*- coding: utf-8 -*-
"""Build Kodi ListItems from Stremio meta objects."""
import os
import re

import xbmc
import xbmcgui

from . import kodi

TYPE_LABELS = {'movie': 30010, 'series': 30011, 'anime': 30012, 'channel': 30013, 'tv': 30014}


def type_label(type_):
    sid = TYPE_LABELS.get(type_)
    return kodi.s(sid) if sid else (type_ or '').title()


def _year(meta):
    for key in ('year', 'releaseInfo', 'released'):
        m = re.search(r'(\d{4})', str(meta.get(key) or ''))
        if m:
            return int(m.group(1))
    return 0


def _runtime(meta):
    m = re.search(r'(\d+)\s*(h|hr|m|min)?', str(meta.get('runtime') or ''))
    if not m:
        return 0
    val = int(m.group(1))
    hours = re.search(r'(\d+)\s*h\D*(\d+)?', str(meta.get('runtime')))
    if hours:
        return int(hours.group(1)) * 3600 + int(hours.group(2) or 0) * 60
    return val * 60


def _unique_ids(meta_id):
    ids = {}
    if meta_id.startswith('tt'):
        ids['imdb'] = meta_id.split(':')[0]
    for prefix in ('tmdb', 'tvdb', 'kitsu', 'mal', 'anilist', 'anidb'):
        if meta_id.startswith(prefix + ':'):
            ids[prefix] = meta_id.split(':')[1]
    return ids


def _people(meta, key):
    val = meta.get(key) or []
    if isinstance(val, str):
        val = [v.strip() for v in val.split(',')]
    out = []
    for v in val:
        out.append(v.get('name') if isinstance(v, dict) else str(v))
    return [v for v in out if v]


def _links(meta, category):
    return [l.get('name') for l in meta.get('links') or []
            if isinstance(l, dict) and str(l.get('category', '')).lower() == category and l.get('name')]


def _trailer(meta):
    for t in meta.get('trailerStreams') or meta.get('trailers') or []:
        yt = t.get('ytId') or (t.get('source') if t.get('type') == 'Trailer' else None)
        if yt:
            return 'plugin://plugin.video.youtube/play/?video_id=' + yt
    return ''


def media_type_for(type_):
    return 'movie' if type_ == 'movie' else 'tvshow'


def meta_item(meta, type_, label=None, playable=False, path=None):
    li = xbmcgui.ListItem(label or meta.get('name') or meta.get('id'), offscreen=True)
    if path:
        li.setPath(path)
    tag = li.getVideoInfoTag()
    tag.setTitle(meta.get('name') or '')
    tag.setMediaType(media_type_for(type_) if type_ in ('movie', 'series', 'anime') else 'video')
    if type_ != 'movie':
        tag.setTvShowTitle(meta.get('name') or '')
    plot = meta.get('description') or ''
    tag.setPlot(plot)
    tag.setPlotOutline(plot[:250])
    y = _year(meta)
    if y:
        tag.setYear(y)
    if meta.get('released'):
        tag.setPremiered(str(meta['released'])[:10])
    genres = meta.get('genres') or meta.get('genre') or _links(meta, 'genres')
    if genres:
        tag.setGenres([g for g in genres if isinstance(g, str)])
    try:
        rating = float(meta.get('imdbRating') or 0)
        if rating:
            tag.setRating(rating, type='imdb', isdefault=True)
    except (TypeError, ValueError):
        pass
    rt = _runtime(meta)
    if rt:
        tag.setDuration(rt)
    directors = _people(meta, 'director') or _links(meta, 'directors')
    if directors:
        tag.setDirectors(directors)
    writers = _people(meta, 'writer') or _links(meta, 'writers')
    if writers:
        tag.setWriters(writers)
    cast = _people(meta, 'cast') or _links(meta, 'cast')
    if cast:
        tag.setCast([xbmc.Actor(name, '', i) for i, name in enumerate(cast[:20])])
    if meta.get('country'):
        tag.setCountries([c.strip() for c in str(meta['country']).split(',')])
    ids = _unique_ids(str(meta.get('id') or ''))
    if ids:
        tag.setUniqueIDs(ids, 'imdb' if 'imdb' in ids else next(iter(ids)))
    if meta.get('imdb_id') and 'imdb' not in ids:
        tag.setIMDBNumber(meta['imdb_id'])
    trailer = _trailer(meta)
    if trailer:
        tag.setTrailer(trailer)

    poster = meta.get('poster') or ''
    fanart = meta.get('background') or ''
    art = {'poster': poster, 'thumb': poster, 'fanart': fanart or kodi.FANART,
           'clearlogo': meta.get('logo') or '', 'icon': poster or kodi.ICON}
    if meta.get('posterShape') == 'landscape':
        art['landscape'] = poster
        art['thumb'] = poster
    li.setArt({k: v for k, v in art.items() if v})
    if playable:
        li.setProperty('IsPlayable', 'true')
    return li


def episode_item(meta, video, type_, path):
    se, ep = video.get('season'), video.get('episode') or video.get('number')
    title = video.get('name') or video.get('title') or ''
    if se is not None and ep is not None:
        label = '%sx%02d. %s' % (se, int(ep), title) if title else '%sx%02d' % (se, int(ep))
    else:
        label = title or video.get('id')
    li = xbmcgui.ListItem(label, offscreen=True)
    li.setPath(path)
    tag = li.getVideoInfoTag()
    tag.setMediaType('episode')
    tag.setTitle(title or label)
    tag.setTvShowTitle(meta.get('name') or '')
    if se is not None:
        tag.setSeason(int(se))
    if ep is not None:
        tag.setEpisode(int(ep))
    plot = video.get('overview') or video.get('description') or ''
    tag.setPlot(plot)
    rel = str(video.get('released') or video.get('firstAired') or '')[:10]
    if rel:
        tag.setFirstAired(rel)
        tag.setPremiered(rel)
    try:
        rating = float(video.get('rating') or 0)
        if rating:
            tag.setRating(rating)
    except (TypeError, ValueError):
        pass
    ids = _unique_ids(str(meta.get('id') or ''))
    if ids:
        tag.setUniqueIDs(ids, 'imdb' if 'imdb' in ids else next(iter(ids)))
    thumb = video.get('thumbnail') or meta.get('background') or meta.get('poster') or ''
    li.setArt({k: v for k, v in {
        'thumb': thumb, 'poster': meta.get('poster') or '', 'fanart': meta.get('background') or kodi.FANART,
        'clearlogo': meta.get('logo') or '', 'tvshow.poster': meta.get('poster') or ''}.items() if v})
    li.setProperty('IsPlayable', 'true')
    return li


TYPE_ICONS = {'movie': 'movie', 'series': 'series', 'anime': 'anime', 'channel': 'channel', 'tv': 'channel'}


def icon(name):
    """Menu icon from resources/media (BoxIcons, as in the AIOStreams web UI)."""
    path = os.path.join(kodi.ADDON_PATH, 'resources', 'media', name + '.png')
    return path if os.path.exists(path) else kodi.ICON


def type_icon(type_):
    return icon(TYPE_ICONS.get(type_, 'catalog'))


def folder_item(label, icon=None, plot=None):
    li = xbmcgui.ListItem(label, offscreen=True)
    li.setArt({'icon': icon or kodi.ICON, 'thumb': icon or kodi.ICON, 'fanart': kodi.FANART})
    if plot:
        li.getVideoInfoTag().setPlot(plot)
    return li
