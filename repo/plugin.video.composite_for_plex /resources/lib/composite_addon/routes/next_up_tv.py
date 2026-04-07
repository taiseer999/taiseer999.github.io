# -*- coding: utf-8 -*-

"""Combined Next Up TV with lightweight preview paging."""

import copy

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.containers import GUIItem, Item
from ..addon.items.episode import create_episode_item
from ..addon.items.gui import create_gui_item
from ..addon.logger import Logger
from ..plex import plex

LOG = Logger()


def _parse_guid(value):
    value = str(value or '')
    if not value:
        return ''
    for prefix in ('thetvdb://', 'tvdb://', 'themoviedb://tv-', 'themoviedb://', 'tmdb://', 'imdb://'):
        if prefix in value:
            return value.split(prefix, 1)[1].split('?', 1)[0]
    return ''


def _show_identity(content):
    parsed = _parse_guid(content.get('grandparentGuid', ''))
    if parsed:
        return parsed.lower()
    title = (content.get('grandparentTitle') or '').strip().lower()
    return '%s::%s' % (title, str(content.get('grandparentYear', '') or content.get('year', '') or ''))


def _resolution_rank(content):
    media = content.find('Media') or content.find('.//Media')
    if media is None:
        return 99
    res = (media.get('videoResolution') or '').lower()
    if res == '4k':
        return 0
    try:
        value = int(res)
    except ValueError:
        return 99
    if value > 1088:
        return 0
    if value >= 1080:
        return 1
    if value >= 720:
        return 2
    return 3


def _bitrate_rank(content):
    media = content.find('Media') or content.find('.//Media')
    if media is None:
        return 0
    try:
        return int(media.get('bitrate', '0') or 0)
    except ValueError:
        return 0


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
        'mode': context.params.get('mode', '50'),
        'parameters': {'start': start, 'page_size': page_size, 'view_all': view_all}
    }
    return create_gui_item(context, GUIItem('http://combined/nextUpTv', details, extra_data))


def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    server_list = context.plex_network.get_server_list()
    grouped = {}
    order_index = 0
    view_all = str(context.params.get('view_all', '0')) == '1'
    start = max(0, _read_int(context, 'start', 0))
    default_page_size = _page_size(context) if view_all else _preview_limit(context)
    page_size = _read_int(context, 'page_size', default_page_size or 0)
    if default_page_size is None and page_size <= 0:
        page_size = 0
    elif page_size <= 0:
        page_size = max(1, default_page_size or 1)

    for server in server_list:
        sections = server.get_sections()
        for section in sections:
            if section.content_type() != 'tvshows':
                continue
            tree = server.get_ondeck(section=int(section.get_key()))
            if tree is None:
                continue
            library_title = section.get_title() if hasattr(section, 'get_title') else ''
            for content in tree.iter('Video'):
                show_key = _show_identity(content)
                group = grouped.setdefault(show_key, {'first_seen': order_index, 'items': []})
                if not group['items']:
                    group['first_seen'] = order_index
                order_index += 1
                episode_copy = copy.deepcopy(content)
                episode_copy.set('server_name_tag', server.get_name() if hasattr(server, 'get_name') else '')
                episode_copy.set('library_title_tag', library_title)
                episode_copy.set('force_show_prefix', '1')
                episode_copy.set('force_sxee_prefix', '1')
                version_key = (
                    server.get_uuid(),
                    episode_copy.get('grandparentRatingKey', ''),
                    episode_copy.get('parentIndex', ''),
                    episode_copy.get('index', ''),
                    episode_copy.find('Media').get('videoResolution', '') if episode_copy.find('Media') is not None else '',
                    episode_copy.find('Media').get('bitrate', '') if episode_copy.find('Media') is not None else ''
                )
                if any(existing['version_key'] == version_key for existing in group['items']):
                    continue
                group['items'].append({
                    'version_key': version_key,
                    'server': server,
                    'tree': tree,
                    'content': episode_copy,
                    'quality_rank': _resolution_rank(episode_copy),
                    'bitrate_rank': _bitrate_rank(episode_copy),
                })

    if not grouped:
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
        return

    flat_entries = []
    for _, group in sorted(grouped.items(), key=lambda pair: pair[1]['first_seen']):
        ordered_versions = sorted(group['items'], key=lambda entry: (entry['quality_rank'], -entry['bitrate_rank'], (entry['server'].get_name() or '').lower()))
        flat_entries.extend(ordered_versions)

    visible_entries = flat_entries[start:start + page_size]
    has_more = start + page_size < len(flat_entries)

    items = []
    for entry in visible_entries:
        item = Item(entry['server'], entry['server'].get_url_location(), entry['tree'], entry['content'])
        items.append(create_episode_item(context, item))

    if items:
        xbmcplugin.setContent(get_handle(), 'episodes')
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    nav_items = []
    if not view_all and len(flat_entries) > page_size:
        nav_items.append(_build_nav_item(context, 'View All', 0, _page_size(context), '1'))
    elif has_more:
        nav_items.append(_build_nav_item(context, 'Next ›', start + page_size, page_size, '1'))
    if nav_items:
        xbmcplugin.addDirectoryItems(get_handle(), nav_items, len(nav_items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
