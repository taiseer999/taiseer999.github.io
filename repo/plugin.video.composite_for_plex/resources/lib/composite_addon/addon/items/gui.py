# -*- coding: utf-8 -*-

"""
gui.py — النسخة النهائية (فك الحظر عن جودة المجلدات والحقن الشامل)
"""

import copy
import json
from urllib.parse import quote, urlparse

import xbmcgui
from infotagger.listitem import ListItemInfoTag

from ..common import get_argv
from ..constants import CONFIG
from ..logger import Logger
from ..strings import i18n, item_translate
from .common import get_clearlogo_from_db 

LOG = Logger('gui_item')

def create_gui_item(context, item):
    url = _get_url(item)
    title = item_translate(item.info_labels.get('title', i18n('Unknown')), item.extra.get('source'), item.is_folder)

    list_item = item.CONSTRUCTOR(title, offscreen=True)
    _, info_labels = _get_info(item)
    
    info_tag = ListItemInfoTag(list_item)
    # ✅ إجبار كودي على قراءة معلومات الميديا حتى لو كان مجلد (مسلسل)
    info_tag.set_info(info_labels)
        
    item_source = str(item.extra.get('source', '')).lower()
    item_type = str(item.extra.get('type', 'video')).lower()
    
    # أضفنا tvshows و show لقائمة الأنواع المسموح لها بعرض الجودة
    allowed_types = ('video', 'movie', 'episode', 'clip', 'tvshows', 'show', 'tvepisodes')
    
    if not context.settings.skip_flags() and (item_type in allowed_types or item_source in allowed_types):
        stream_info = item.extra.get('stream_info', {})
        if stream_info:
            info_tag.add_stream_info('video', stream_info.get('video', {}))
            info_tag.add_stream_info('audio', stream_info.get('audio', {}))

    # --- [محرك الحقن التلقائي للشعارات] ---
    art = _get_art(item)
    try:
        tmdb_id = item.extra.get('tmdb_id')
        if not tmdb_id:
            guid = str(item.info_labels.get('guid', '') or item.extra.get('guid', ''))
            if 'tmdb://' in guid:
                tmdb_id = guid.split('tmdb://')[1].split('?')[0]
            elif 'themoviedb://' in guid:
                tmdb_id = guid.split('themoviedb://')[1].split('?')[0]

        lookup_type = 'movie' if ('movie' in item_source or 'movie' in str(item.info_labels.get('mediatype', '')).lower()) else 'tv'
        
        clearlogo = item.extra.get('clearlogo')
        if not clearlogo and tmdb_id:
            clearlogo = get_clearlogo_from_db(tmdb_id, lookup_type)
            
        if clearlogo:
            art['clearlogo'] = clearlogo
            art['tvshow.clearlogo'] = clearlogo
            art['logo'] = clearlogo
            item.extra['clearlogo'] = clearlogo
    except Exception as e:
        LOG.debug("Auto Injection Error: %s" % str(e))
    list_item.setArt(art)
    # -------------------------------------

    if item.context_menu is not None:
        if not item.is_folder and item_type in allowed_types:
            item.context_menu.insert(0, (i18n('Play Transcoded'), 'PlayMedia(%s&transcode=1)' % url))
        list_item.addContextMenuItems(item.context_menu)

    item_properties = _get_properties(context, item)
    item_properties = info_tag.set_resume_point(item_properties)
    item_properties.pop('TotalTime', None)
    item_properties.pop('ResumeTime', None)
    list_item.setProperties(item_properties)

    if item.url.startswith('cmd:'):
        item.is_folder = False

    return url, list_item, item.is_folder


def _get_url(item):
    path_mode = item.extra.get('path_mode')
    plugin_url = get_argv()[0]
    url_parts = urlparse(plugin_url)
    plugin_url = 'plugin://%s/' % url_parts.netloc
    if path_mode and '/' in path_mode: plugin_url += path_mode.rstrip('/') + '/'

    if not item.is_folder and item.extra.get('type') == 'image': url = item.url
    elif item.url.startswith('http') or item.url.startswith('file'): url = '%s?url=%s&mode=%s' % (plugin_url, quote(item.url), item.extra.get('mode', 0))
    else: url = '%s?url=%s&mode=%s' % (plugin_url, item.url, item.extra.get('mode', 0))

    if item.extra.get('parameters'):
        for argument, value in item.extra.get('parameters').items():
            url = '%s&%s=%s' % (url, argument, quote(str(value)))
    return url


def _get_info(item):
    info_type = item.extra.get('type', 'Video')
    info_labels = copy.deepcopy(item.info_labels)

    if info_type.lower() in ('folder', 'file'): info_type = 'Video'
    elif info_type.lower() == 'image': info_type = 'Picture'

    if info_type == 'Video':
        if not info_labels.get('plot'): info_labels['plot'] = u'\u2008'
        if not info_labels.get('plotoutline'): info_labels['plotoutline'] = u'\u2008'
    return info_type, info_labels


def _get_art(item):
    fanart = item.extra.get('fanart_image', '')
    thumb = item.extra.get('thumb', CONFIG['icon'])
    banner = item.extra.get('banner', '')
    poster = item.extra.get('season_thumb', '')
    
    if not poster:
        if not item.is_folder: poster = item.extra.get('thumb', 'DefaultPoster.png')
        else: poster = thumb

    return {'fanart': fanart, 'poster': poster, 'banner': banner, 'thumb': thumb, 'icon': thumb}


def _get_properties(context, item):
    item_properties = {}
    
    if item.extra.get('type', '').lower() == 'music':
        item_properties['Artist_Genre'] = item.info_labels.get('genre', '')
        item_properties['Artist_Description'] = item.extra.get('plot', '')
        item_properties['Album_Description'] = item.extra.get('plot', '')

    if not item.is_folder:
        item_properties['IsPlayable'] = 'true'
        
    # ✅ فك الحظر: نقلنا خصائص الجودة لتُطبق حتى لو كان العنصر مجلداً (مسلسل)
    item_source = str(item.extra.get('source', '')).lower()
    item_type = str(item.extra.get('type', 'video')).lower()
    allowed_types = ('video', 'movie', 'episode', 'clip', 'tvshows', 'show', 'tvepisodes')

    if item_type in allowed_types or item_source in allowed_types:
        item_properties['TotalTime'] = int(item.extra.get('duration') or 0)
        item_properties['ResumeTime'] = int(item.extra.get('resume') or 0)

        if not context.settings.skip_flags():
            item_properties['VideoResolution'] = item.extra.get('VideoResolution', '')
            item_properties['VideoCodec'] = item.extra.get('VideoCodec', '')
            item_properties['AudioCodec'] = item.extra.get('AudioCodec', '')
            item_properties['AudioChannels'] = item.extra.get('AudioChannels', '')
            item_properties['VideoAspect'] = item.extra.get('VideoAspect', '')

    if item.extra.get('imdb_id'): item_properties['imdb_id'] = item.extra['imdb_id']
    if item.extra.get('tmdb_id'): item_properties['tmdb_id'] = item.extra['tmdb_id']
    if item.extra.get('tvdb_id'): item_properties['tvdb_id'] = item.extra['tvdb_id']

    if item.extra.get('source') in ('tvshows', 'tvseasons'):
        item_properties['TotalEpisodes'] = str(item.extra.get('TotalEpisodes', 0))
        item_properties['WatchedEpisodes'] = str(item.extra.get('WatchedEpisodes', 0))
        item_properties['UnWatchedEpisodes'] = str(item.extra.get('UnWatchedEpisodes', 0))

        if item.extra.get('partialTV') == 1:
            item_properties['TotalTime'] = 100
            item_properties['ResumeTime'] = 50

    if item.extra.get('season_thumb', ''): item_properties['seasonThumb'] = item.extra.get('season_thumb', '')
    if item.url.startswith('cmd:'): item_properties['IsPlayable'] = 'false'

    mediatype = item.info_labels.get('mediatype')
    if mediatype: item_properties['content_type'] = mediatype + 's'
    if item.extra.get('hash'): item_properties['hash'] = item.extra['hash']

    return item_properties
