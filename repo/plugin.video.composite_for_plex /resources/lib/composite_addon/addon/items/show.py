# -*- coding: utf-8 -*-
"""
    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2026 DPlex (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import hashlib

from ..constants import COMBINED_SECTIONS
from ..constants import MODES
from ..containers import GUIItem
from ..logger import Logger
from ..strings import encode_utf8
from ..strings import i18n
from .common import get_banner_image
from .common import get_clearlogo_from_db
from .common import get_fanart_image
from .common import get_guid_ids
from .common import get_metadata
from .common import get_thumb_image
from .context_menu import ContextMenu
from .gui import create_gui_item

LOG = Logger()


def create_show_item(context, item, library=False):
    metadata = get_metadata(context, item.data)
    guid_ids = get_guid_ids(item.data)

    info_labels = {
        'title': encode_utf8(item.data.get('title', i18n('Unknown'))),
        'sorttitle': encode_utf8(item.data.get('titleSort', item.data.get('title', i18n('Unknown')))),
        'tvshowtitle': encode_utf8(item.data.get('title', i18n('Unknown'))),
        'studio': [encode_utf8(item.data.get('studio', ''))],
        'plot': encode_utf8(item.data.get('summary', '')),
        'season': 0,
        'episode': int(item.data.get('leafCount', 0)),
        'mpaa': item.data.get('contentRating', ''),
        'rating': float(item.data.get('rating', 0)),
        'aired': item.data.get('originallyAvailableAt', ''),
        'cast': metadata['cast'],
        'genre': metadata['genre'],
        'mediatype': 'tvshow',
        'year': int(item.data.get('year', 0) or 0),
        'premiered': item.data.get('originallyAvailableAt', ''),
        'originaltitle': encode_utf8(item.data.get('originalTitle', item.data.get('titleSort', item.data.get('title', i18n('Unknown')))))
    }

    if guid_ids.get('imdb_id'):
        info_labels['imdbnumber'] = guid_ids['imdb_id']

    prefix_server = (context.params.get('mode') in COMBINED_SECTIONS and
                     context.settings.prefix_server_in_combined())

    if prefix_server:
        info_labels['title'] = '%s: %s' % (item.server.get_name(), info_labels['title'])

    header_parts = []
    next_episode_label = item.data.get('next_episode_label', '')
    if next_episode_label:
        header_parts.append('[ %s ]' % next_episode_label)
    library_title = item.data.get('library_title_tag', '')
    if library_title:
        header_parts.append('[ %s ]' % library_title)
    server_name = item.data.get('server_name_tag', '')
    if server_name:
        header_parts.append('[ %s ]' % server_name)
    if header_parts:
        header = ' • '.join(header_parts)
        info_labels['plot'] = '%s\n\n%s' % (header, info_labels['plot']) if info_labels['plot'] else header

    _watched = int(item.data.get('viewedLeafCount', 0))

    tmdb_id = guid_ids.get('tmdb_id', '')
    clearlogo_url = get_clearlogo_from_db(tmdb_id, 'tv') if tmdb_id else ''

    extra_data = {
        'type': 'video',
        'source': 'tvshows',
        'UnWatchedEpisodes': int(info_labels['episode']) - _watched,
        'WatchedEpisodes': _watched,
        'TotalEpisodes': info_labels['episode'],
        'thumb': get_thumb_image(context, item.server, item.data),
        'fanart_image': get_fanart_image(context, item.server, item.data),
        'banner': get_banner_image(context, item.server, item.data),
        'clearlogo': clearlogo_url, 
        'key': item.data.get('key', ''),
        'ratingKey': str(item.data.get('ratingKey', 0)),
        'imdb_id': guid_ids.get('imdb_id', ''),
        'tmdb_id': tmdb_id,
        'tvdb_id': guid_ids.get('tvdb_id', ''),
    }

    if extra_data['WatchedEpisodes'] == 0:
        info_labels['playcount'] = 0
    elif extra_data['UnWatchedEpisodes'] == 0:
        info_labels['playcount'] = 1
    else:
        extra_data['partialTV'] = 1

    if context.settings.flatten_seasons() == '2':
        LOG.debug('Flattening all shows')
        extra_data['mode'] = MODES.TVEPISODES
        item_url = item.server.join_url(item.server.get_url_location(),
                                        extra_data['key'].replace('children', 'allLeaves'))
    else:
        extra_data['mode'] = MODES.TVSEASONS
        item_url = item.server.join_url(item.server.get_url_location(), extra_data['key'])

    if library:
        extra_data['hash'] = _md5_hash(item.data)
        extra_data['path_mode'] = MODES.TXT_TVSHOWS_LIBRARY

    context_menu = None
    if not context.settings.skip_context_menus():
        context_menu = ContextMenu(context, item.server, item.url, extra_data).menu

    gui_item = GUIItem(item_url, info_labels, extra_data, context_menu)
    kodi_item = create_gui_item(context, gui_item)

    # --- Inject Clearlogo & Fake Flags للويدجت ---
    try:
        list_item = kodi_item[1] if isinstance(kodi_item, tuple) else kodi_item
        
        if clearlogo_url:
            list_item.setArt({
                'clearlogo': clearlogo_url,
                'tvshow.clearlogo': clearlogo_url,
                'logo': clearlogo_url
            })
            
        preview_resolution = item.data.get('preview_video_resolution', '')
        preview_vcodec = item.data.get('preview_video_codec', '')
        preview_acodec = item.data.get('preview_audio_codec', '')
        preview_achannels = item.data.get('preview_audio_channels', '')
        preview_hdr = item.data.get('preview_dynamic_range', '')

        if preview_resolution:
            list_item.setProperty('VideoResolution', preview_resolution.upper())
        if preview_vcodec:
            list_item.setProperty('VideoCodec', preview_vcodec)
        if preview_acodec:
            list_item.setProperty('AudioCodec', preview_acodec)
        if preview_achannels:
            list_item.setProperty('AudioChannels', preview_achannels)
        if preview_hdr:
            list_item.setProperty('VideoCodec.HDR', preview_hdr.lower())
        
    except Exception as e:
        LOG.debug('Injection error in show.py: %s' % str(e))

    return kodi_item


def _md5_hash(show):
    show_hash = hashlib.md5()
    show_hash.update(show.get('addedAt', u'').encode('utf-8'))
    show_hash.update(show.get('updatedAt', u'').encode('utf-8'))
    return show_hash.hexdigest().upper()
