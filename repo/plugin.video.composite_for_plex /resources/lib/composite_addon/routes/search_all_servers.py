# -*- coding: utf-8 -*-

"""
Copyright (C) 2020 Composite (plugin.video.composite_for_plex)

This file is part of Composite (plugin.video.composite_for_plex)

SPDX-License-Identifier: GPL-2.0-or-later
See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import xbmc  # pylint: disable=import-error
import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.constants import MODES
from ..addon.containers import Item
from ..addon.items.album import create_album_item
from ..addon.items.artist import create_artist_item
from ..addon.items.episode import create_episode_item
from ..addon.items.movie import create_movie_item
from ..addon.items.show import create_show_item
from ..addon.items.track import create_track_item
from ..addon.logger import Logger
from ..addon.strings import i18n
from ..plex import plex

LOG = Logger()

# -----------------------------------------------------------------
# دوال الترتيب الشامل (Global Sort) 
# -----------------------------------------------------------------
def _resolution_rank(content):
    """4K=0, 1080p=1, 720p=2, SD=3"""
    media = content.find('.//Media')
    if media is None:
        return 99
    res = media.get('videoResolution', '').lower()
    try:
        r = int(res)
        if r > 1088: return 0
        if r >= 1080: return 1
        if r >= 720:  return 2
        return 3
    except ValueError:
        if res == '4k': return 0
        return 99

def _group_key(content):
    """مفتاح تجميع ذكي للأفلام والمسلسلات في البحث"""
    ctype = content.get('type')
    title = (content.get('grandparentTitle') or content.get('title') or '').lower()
    
    if ctype == 'episode':
        season  = int(content.get('parentIndex', 0))
        episode = int(content.get('index', 0))
        return (title, season, episode)
    elif ctype == 'movie':
        year = content.get('year', '0')
        return (title, year)
    else:
        return (title,)

def _global_sort_by_quality(raw_items):
    """ترتيب شامل للنتائج الخام مع إعطاء الأولوية للـ 4K"""
    indexed = list(enumerate(raw_items))
    first_seen = {}
    for idx, (server, tree, content) in indexed:
        key = _group_key(content)
        if key not in first_seen:
            first_seen[key] = idx

    result = sorted(
        indexed,
        key=lambda x: (first_seen[_group_key(x[1][2])], _resolution_rank(x[1][2]))
    )
    return [item for _, item in result]

# -----------------------------------------------------------------

def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)

    context.params['query'] = _get_search_query()
    if not context.params['query']:
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    all_sections = context.plex_network.all_sections()
    LOG.debug('Using list of %s sections' % len(all_sections))

    items = search(context, all_sections)

    if items:
        content_type = get_content_type(context)
        add_sort_methods(content_type)
        xbmcplugin.setContent(get_handle(), content_type)
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)

def add_sort_methods(content_type):
    methods_map = {
        'movies': [
            xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
            xbmcplugin.SORT_METHOD_DATEADDED,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_VIDEO_RATING,
            xbmcplugin.SORT_METHOD_VIDEO_RUNTIME,
            xbmcplugin.SORT_METHOD_MPAA_RATING,
            xbmcplugin.SORT_METHOD_UNSORTED,
        ],
        'tvshows': [
            xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_VIDEO_RATING,
            xbmcplugin.SORT_METHOD_MPAA_RATING,
            xbmcplugin.SORT_METHOD_UNSORTED,
        ],
        'episodes': [
            xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
            xbmcplugin.SORT_METHOD_EPISODE,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_DATEADDED,
            xbmcplugin.SORT_METHOD_VIDEO_RATING,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_VIDEO_RUNTIME,
            xbmcplugin.SORT_METHOD_MPAA_RATING,
            xbmcplugin.SORT_METHOD_UNSORTED,
        ],
        'albums': [
            xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE,
            xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE,
            xbmcplugin.SORT_METHOD_LASTPLAYED,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_UNSORTED,
        ],
        'artists': [
            xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE,
            xbmcplugin.SORT_METHOD_LASTPLAYED,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_UNSORTED,
        ],
        'songs': [
            xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,
            xbmcplugin.SORT_METHOD_SONG_RATING,
            xbmcplugin.SORT_METHOD_TRACKNUM,
            xbmcplugin.SORT_METHOD_DURATION,
            xbmcplugin.SORT_METHOD_UNSORTED,
        ],
    }
    methods = methods_map.get(content_type, [
        xbmcplugin.SORT_METHOD_UNSORTED,
        xbmcplugin.SORT_METHOD_DATE,
        xbmcplugin.SORT_METHOD_VIDEO_YEAR,
    ])
    for m in methods:
        xbmcplugin.addSortMethod(get_handle(), m)

def get_section_type(context):
    mode = int(context.params.get('mode', -1))
    return {
        MODES.MOVIES_SEARCH_ALL: 'movie',
        MODES.TVSHOWS_SEARCH_ALL: 'show',
        MODES.EPISODES_SEARCH_ALL: 'show',
        MODES.ARTISTS_SEARCH_ALL: 'artist',
        MODES.ALBUMS_SEARCH_ALL: 'artist',
        MODES.TRACKS_SEARCH_ALL: 'artist',
    }.get(mode, '')

def get_item_type(context):
    mode = int(context.params.get('mode', -1))
    return {
        MODES.MOVIES_SEARCH_ALL: 1,
        MODES.TVSHOWS_SEARCH_ALL: 2,
        MODES.EPISODES_SEARCH_ALL: 4,
        MODES.ARTISTS_SEARCH_ALL: 8,
        MODES.ALBUMS_SEARCH_ALL: 9,
        MODES.TRACKS_SEARCH_ALL: 10,
    }.get(mode, -1)

def get_content_type(context):
    mode = int(context.params.get('mode', -1))
    return {
        MODES.MOVIES_SEARCH_ALL: 'movies',
        MODES.TVSHOWS_SEARCH_ALL: 'tvshows',
        MODES.EPISODES_SEARCH_ALL: 'episodes',
        MODES.ARTISTS_SEARCH_ALL: 'artists',
        MODES.ALBUMS_SEARCH_ALL: 'albums',
        MODES.TRACKS_SEARCH_ALL: 'songs',
    }.get(mode, 'files')

def search(context, sections):
    section_type = get_section_type(context)
    item_type = get_item_type(context)
    query = context.params['query']

    # فلتر الـ sections المطلوبة فقط
    target_sections = [
        (context.plex_network.get_server_from_uuid(sec.get_server_uuid()), sec.get_path())
        for sec in sections
        if sec.get_type() == section_type
    ]

    if not target_sections:
        return []

    raw_items = []

    def _search_one(server, section_path):
        try:
            section_ids = [int(p) for p in section_path.split('/') if p.isdigit()]
            if not section_ids:
                return []
            section_id = section_ids[0]
            tree = server.get_search(query, item_type, section=section_id)
            if tree is None:
                return []
            
            iter_types = {
                1: 'Video', 2: 'Directory', 4: 'Video',
                8: 'Directory', 9: 'Directory', 10: 'Track',
            }
            branches = list(tree.iter(iter_types.get(item_type, 'Directory')))
            return [(server, tree, content) for content in branches]
        except Exception as e:
            LOG.debug('Search error: %s' % str(e))
            return []

    # ✅ بحث متوازي وسريع
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_search_one, srv, path): (srv, path)
            for srv, path in target_sections
        }
        for future in as_completed(futures):
            try:
                raw_items.extend(future.result())
            except Exception as e:
                LOG.debug('Future error: %s' % str(e))

    if not raw_items:
        return []

    # ✅ تطبيق الترتيب الشامل لتقديم الـ 4K 
    sorted_raw_items = _global_sort_by_quality(raw_items)

    # ✅ بناء العناصر وزرع اسم السيرفر
    items = []
    type_map = {
        'show': create_show_item,
        'episode': create_episode_item,
        'movie': create_movie_item,
        'album': create_album_item,
        'artist': create_artist_item,
        'track': create_track_item,
    }

    for server, tree, content in sorted_raw_items:
        # زرع اسم السيرفر بكل أناقة
        server_name = server.get_name() if hasattr(server, 'get_name') else ''
        if server_name:
            content.set('server_name_tag', server_name)

        ctype = content.get('type')
        creator = type_map.get(ctype)
        if creator:
            item = Item(server, server.get_url_location(), tree, content)
            items.append(creator(context, item))

    return items

def _get_search_query():
    keyboard = xbmc.Keyboard('', i18n('Search...'))
    keyboard.setHeading(i18n('Enter search term'))
    keyboard.doModal()
    if keyboard.isConfirmed():
        text = keyboard.getText().strip()
        return text if text else ''
    return ''
