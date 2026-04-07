# -*- coding: utf-8 -*-

"""Combined on-deck with cached TV resolution and lightweight preview paging."""

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.containers import GUIItem, Item
from ..addon.items.gui import create_gui_item
from ..addon.items.movie import create_movie_item
from ..addon.items.show import create_show_item
from ..addon.logger import Logger
from ..plex import plex

LOG = Logger()


def _resolution_rank(content):
    media = content.find('.//Media')
    if media is None:
        return 99
    res = media.get('videoResolution', '').lower()
    try:
        r = int(res)
        if r > 1088:
            return 0
        if r >= 1080:
            return 1
        if r >= 720:
            return 2
        return 3
    except ValueError:
        if res == '4k':
            return 0
        return 99


def _group_key(content, content_type):
    media_type = (content.get('type') or content.tag or '').lower()
    if content_type == 'tvshows':
        return ('show', (content.get('ratingKey') or content.get('grandparentRatingKey') or content.get('key') or content.get('title') or '').lower())

    title = (content.get('grandparentTitle') or content.get('title') or '').lower()
    season = int(content.get('parentIndex', 0) or 0)
    episode = int(content.get('index', 0) or 0)
    return (media_type, title, season, episode)


def _global_sort_by_quality(raw_items, content_type):
    indexed = list(enumerate(raw_items))
    first_seen = {}
    for idx, (server, tree, content) in indexed:
        key = _group_key(content, content_type)
        if key not in first_seen:
            first_seen[key] = idx

    result = sorted(indexed, key=lambda x: (first_seen[_group_key(x[1][2], content_type)], _resolution_rank(x[1][2])))
    return [item for _, item in result]


def _iter_on_deck_items(tree, content_type):
    if tree is None:
        return []

    items = []
    if content_type == 'tvshows':
        items.extend(tree.iter('Directory'))
        items.extend(tree.iter('Video'))
    else:
        items.extend(tree.iter('Video'))

    return list(items)


def _resolve_tvshow_content(server, tree, content, metadata_cache):
    item_type = (content.get('type') or content.tag or '').lower()
    if item_type == 'show' or content.tag == 'Directory':
        return tree, content

    grandparent_key = content.get('grandparentRatingKey', '')
    if not grandparent_key:
        return None, None
    cache_key = '%s:%s' % (server.get_uuid(), grandparent_key)
    if cache_key in metadata_cache:
        show_tree = metadata_cache[cache_key]
    else:
        try:
            show_tree = server.get_metadata(grandparent_key)
            metadata_cache[cache_key] = show_tree
        except Exception as error:
            LOG.debug('TV On Deck resolve error: %s' % str(error))
            metadata_cache[cache_key] = None
            show_tree = None
    if show_tree is None:
        return None, None
    show_content = show_tree.find('.//Directory') or show_tree.find('Directory')
    return show_tree, show_content


def _preview_limit(context):
    value = context.settings.performance_home_limit()
    return None if value is None else max(1, value)


def _page_size(context):
    page = context.settings.performance_page_size()
    preview = _preview_limit(context)
    if page is None:
        return None
    if preview is None:
        return max(1, page)
    return max(preview, page)


def _read_int(context, name, default):
    try:
        return int(context.params.get(name, default))
    except (TypeError, ValueError):
        return default


def _build_nav_item(context, title, start, page_size, view_all='1'):
    details = {'title': title}
    extra_data = {
        'type': 'Folder',
        'mode': context.params.get('mode', '33'),
        'parameters': {'content_type': context.params.get('content_type', ''), 'start': start, 'page_size': page_size, 'view_all': view_all}
    }
    return create_gui_item(context, GUIItem('http://combined/onDeck', details, extra_data))


def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    content_type = context.params.get('content_type')
    server_list = context.plex_network.get_server_list()
    metadata_cache = {}
    view_all = str(context.params.get('view_all', '0')) == '1'
    start = max(0, _read_int(context, 'start', 0))
    default_page_size = _page_size(context) if view_all else _preview_limit(context)
    page_size = _read_int(context, 'page_size', default_page_size or 0)
    if default_page_size is None and page_size <= 0:
        page_size = 0
    elif page_size <= 0:
        page_size = max(1, default_page_size or 1)

    raw_items = []
    LOG.debug('Using list of %s servers' % len(server_list))

    for server in server_list:
        sections = server.get_sections()
        for section in sections:
            if section.content_type() != content_type:
                continue
            tree = server.get_ondeck(section=int(section.get_key()))
            if tree is None:
                continue
            for content in _iter_on_deck_items(tree, content_type):
                if content_type == 'tvshows':
                    resolved_tree, resolved_content = _resolve_tvshow_content(server, tree, content, metadata_cache)
                    if resolved_content is None:
                        continue
                    raw_items.append((server, resolved_tree, resolved_content))
                else:
                    raw_items.append((server, tree, content))

    if not raw_items:
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
        return

    sorted_raw_items = _global_sort_by_quality(raw_items, content_type)

    items = []
    seen = set()
    visible_count = 0
    nav_start = 0
    for idx, (server, tree, content) in enumerate(sorted_raw_items):
        if idx < start:
            continue
        if visible_count >= page_size:
            nav_start = idx
            break

        server_name = server.get_name() if hasattr(server, 'get_name') else ''
        if server_name:
            content.set('server_name_tag', server_name)

        dedupe_key = (server.get_uuid(), content.get('ratingKey', ''), content.get('key', ''))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        item = Item(server, server.get_url_location(), tree, content)
        item_type = (content.get('type') or content.tag or '').lower()

        if content_type == 'tvshows':
            if item_type in ('show', 'directory'):
                items.append(create_show_item(context, item))
                visible_count += 1
        elif item_type == 'movie':
            items.append(create_movie_item(context, item))
            visible_count += 1

    if items:
        xbmcplugin.setContent(get_handle(), content_type)
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    total_items = len(sorted_raw_items)
    nav_items = []
    if not view_all and total_items > page_size:
        nav_items.append(_build_nav_item(context, 'View All', 0, _page_size(context), '1'))
    elif nav_start:
        nav_items.append(_build_nav_item(context, 'Next ›', nav_start, page_size, '1'))
    if nav_items:
        xbmcplugin.addDirectoryItems(get_handle(), nav_items, len(nav_items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
