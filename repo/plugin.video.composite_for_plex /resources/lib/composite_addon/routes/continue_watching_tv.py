# -*- coding: utf-8 -*-

"""Combined Continue Watching TV with cached metadata resolution and lightweight paging."""

import copy

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.containers import GUIItem, Item
from ..addon.items.gui import create_gui_item
from ..addon.items.show import create_show_item
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
    for key in ('grandparentGuid', 'guid'):
        parsed = _parse_guid(content.get(key, ''))
        if parsed:
            return parsed.lower()
    title = (content.get('grandparentTitle') or content.get('title') or '').strip().lower()
    year = str(content.get('year', '') or content.get('grandparentYear', '') or '')
    return '%s::%s' % (title, year)


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


def _episode_label(content):
    season = str(content.get('parentIndex', '')).zfill(2)
    episode = str(content.get('index', '')).zfill(2)
    if season == '00' and episode == '00':
        return 'Continue Watching'
    return 'Continue at S%sE%s' % (season, episode)


def _apply_preview_from_episode(show_content, episode_content):
    media = episode_content.find('Media') or episode_content.find('.//Media')
    part = media.find('Part') if media is not None else None
    show_content.set('preview_video_resolution', media.get('videoResolution', '') if media is not None else '')
    show_content.set('preview_video_codec', media.get('videoCodec', '') if media is not None else '')
    show_content.set('preview_audio_codec', media.get('audioCodec', '') if media is not None else '')
    show_content.set('preview_audio_channels', media.get('audioChannels', '') if media is not None else '')
    dynamic_range = ''
    if part is not None:
        for stream in part.findall('.//Stream'):
            if stream.get('streamType') != '1':
                continue
            display_title = (stream.get('displayTitle') or '').upper()
            codec_id = (stream.get('codecID') or '').upper()
            if stream.get('DOVIBLPresent') == '1' or stream.get('DOVIRPUPresent') == '1' or 'DOVI' in codec_id or 'DV' in display_title:
                dynamic_range = 'dv'
                break
            if 'HDR10+' in display_title:
                dynamic_range = 'hdr10plus'
                break
            if 'HDR' in display_title or stream.get('colorTransfer') in ('smpte2084', 'arib-std-b67'):
                dynamic_range = 'hdr10'
                break
    show_content.set('preview_dynamic_range', dynamic_range)


def _resolve_show(server, content, metadata_cache):
    item_type = (content.get('type') or content.tag or '').lower()
    if item_type == 'show' or content.tag == 'Directory':
        show_tree = server.get_metadata(content.get('ratingKey', '')) if content.get('ratingKey') else None
        if show_tree is None:
            return None, None
        show_content = show_tree.find('.//Directory') or show_tree.find('Directory') or content
        resolved = copy.deepcopy(show_content)
        return show_tree, resolved

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
            LOG.debug('Continue Watching TV resolve error: %s' % str(error))
            metadata_cache[cache_key] = None
            show_tree = None
    if show_tree is None:
        return None, None
    show_content = show_tree.find('.//Directory') or show_tree.find('Directory')
    if show_content is None:
        return None, None
    resolved = copy.deepcopy(show_content)
    _apply_preview_from_episode(resolved, content)
    resolved.set('next_episode_label', _episode_label(content))
    return show_tree, resolved


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
        'mode': context.params.get('mode', '49'),
        'parameters': {'start': start, 'page_size': page_size, 'view_all': view_all}
    }
    return create_gui_item(context, GUIItem('http://combined/continueWatchingTv', details, extra_data))


def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    server_list = context.plex_network.get_server_list()
    grouped = {}
    first_seen_counter = 0
    metadata_cache = {}
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
                group = grouped.setdefault(show_key, {'first_seen': first_seen_counter, 'items': []})
                if not group['items']:
                    group['first_seen'] = first_seen_counter
                first_seen_counter += 1
                version_key = (
                    server.get_uuid(),
                    content.get('grandparentRatingKey', ''),
                    content.get('ratingKey', ''),
                    (content.find('Media').get('videoResolution', '') if content.find('Media') is not None else ''),
                    (content.find('Media').get('videoCodec', '') if content.find('Media') is not None else ''),
                    (content.find('Media').get('audioCodec', '') if content.find('Media') is not None else '')
                )
                if any(existing['version_key'] == version_key for existing in group['items']):
                    continue
                group['items'].append({
                    'version_key': version_key,
                    'server': server,
                    'tree': tree,
                    'content': copy.deepcopy(content),
                    'library_title': library_title,
                    'quality_rank': _resolution_rank(content),
                    'bitrate_rank': _bitrate_rank(content),
                })

    if not grouped:
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
        return

    flat_entries = []
    for _, group in sorted(grouped.items(), key=lambda pair: pair[1]['first_seen']):
        ordered_versions = sorted(
            group['items'],
            key=lambda entry: (entry['quality_rank'], -entry['bitrate_rank'], (entry['server'].get_name() or '').lower())
        )
        flat_entries.extend(ordered_versions)

    visible_entries = flat_entries[start:start + page_size]
    has_more = start + page_size < len(flat_entries)

    items = []
    for entry in visible_entries:
        show_tree, show_content = _resolve_show(entry['server'], entry['content'], metadata_cache)
        if show_content is None:
            continue
        show_content.set('server_name_tag', entry['server'].get_name() if hasattr(entry['server'], 'get_name') else '')
        show_content.set('library_title_tag', entry.get('library_title', ''))
        item = Item(entry['server'], entry['server'].get_url_location(), show_tree, show_content)
        items.append(create_show_item(context, item))

    if items:
        xbmcplugin.setContent(get_handle(), 'tvshows')
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    nav_items = []
    if not view_all and len(flat_entries) > page_size:
        nav_items.append(_build_nav_item(context, 'View All', 0, _page_size(context), '1'))
    elif has_more:
        nav_items.append(_build_nav_item(context, 'Next ›', start + page_size, page_size, '1'))
    if nav_items:
        xbmcplugin.addDirectoryItems(get_handle(), nav_items, len(nav_items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)
