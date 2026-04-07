# -*- coding: utf-8 -*-

"""
Copyright (C) 2020-2026 DPlex (plugin.video.composite_for_plex)
Advanced Global Search with Media Info Injection (Multi-Threaded).
Supports direct GUID search (IMDb/TMDb/TVDb) with resilient title fallback.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, unquote
import re

import xbmc
import xbmcgui
import xbmcplugin

from ..addon.common import get_handle
from ..addon.containers import Item
from ..addon.items.episode import create_episode_item
from ..addon.items.movie import create_movie_item
from ..addon.items.show import create_show_item
from ..addon.logger import Logger
from ..addon.strings import i18n
from ..plex import plex

LOG = Logger()

VIDEO_TYPES = {
    'movie': {'content_type': 'movie', 'search_type': '1', 'content': 'movies'},
    'show': {'content_type': 'show', 'search_type': '2', 'content': 'tvshows'},
    'episode': {'content_type': 'show', 'search_type': '4', 'content': 'episodes'},
}


def _normalize_text(value):
    value = unquote(str(value or '')).strip().lower()
    value = value.replace('&', ' and ')
    value = re.sub(r'[^\w\s]', ' ', value, flags=re.UNICODE)
    value = re.sub(r'\s+', ' ', value, flags=re.UNICODE).strip()
    return value


def _fetch_full_metadata(server, rating_key):
    try:
        url = '/library/metadata/%s?includeGuids=1' % rating_key
        try:
            from .plex_request import cached_get
            tree = cached_get(server, url)
        except ImportError:
            tree = server.processed_xml(url)
        if tree is None:
            return None
        return tree.find('.//Video') or tree.find('.//Directory') or tree.find('Video') or tree.find('Directory')
    except Exception as error:
        LOG.debug('Error fetching metadata: %s' % str(error))
        return None


def _extract_guid_ids(element):
    ids = {'imdb_id': '', 'tmdb_id': '', 'tvdb_id': ''}
    if element is None:
        return ids

    for child in element.findall('Guid'):
        guid_value = child.get('id', '')
        if guid_value.startswith('imdb://'):
            ids['imdb_id'] = guid_value.replace('imdb://', '')
        elif guid_value.startswith('tmdb://'):
            ids['tmdb_id'] = guid_value.replace('tmdb://', '')
        elif guid_value.startswith('tvdb://'):
            ids['tvdb_id'] = guid_value.replace('tvdb://', '')
        elif guid_value.startswith('themoviedb://'):
            ids['tmdb_id'] = guid_value.replace('themoviedb://', '').replace('tv-', '')
        elif guid_value.startswith('thetvdb://'):
            ids['tvdb_id'] = guid_value.replace('thetvdb://', '')

    legacy_guid = element.get('guid', '')
    if not ids['imdb_id'] and 'imdb://' in legacy_guid:
        ids['imdb_id'] = legacy_guid.split('imdb://', 1)[1].split('?', 1)[0]
    if not ids['tmdb_id'] and 'tmdb://' in legacy_guid:
        ids['tmdb_id'] = legacy_guid.split('tmdb://', 1)[1].split('?', 1)[0]
    if not ids['tmdb_id'] and 'themoviedb://' in legacy_guid:
        ids['tmdb_id'] = legacy_guid.split('themoviedb://', 1)[1].split('?', 1)[0].replace('tv-', '')
    if not ids['tvdb_id'] and 'tvdb://' in legacy_guid:
        ids['tvdb_id'] = legacy_guid.split('tvdb://', 1)[1].split('?', 1)[0]
    if not ids['tvdb_id'] and 'thetvdb://' in legacy_guid:
        ids['tvdb_id'] = legacy_guid.split('thetvdb://', 1)[1].split('?', 1)[0]
    return ids


def _get_media_info(element):
    if element is None:
        return '', ''

    media = element.find('Media') or element.find('.//Media')
    if media is None:
        return '', ''

    parts = []

    res = media.get('videoResolution', '')
    if res:
        try:
            r = int(res)
            res_label = '4K' if r > 1088 else ('1080p' if r >= 1080 else ('720p' if r >= 720 else 'SD'))
        except ValueError:
            res_label = res.upper()
        parts.append('[ %s ]' % res_label)

    part_el = media.find('Part') or media.find('.//Part')
    hdr_type = ''
    audio_extra = ''

    if part_el is not None:
        for stream in part_el.findall('.//Stream'):
            stype = stream.get('streamType')
            if stype == '1' and not hdr_type:
                dt = stream.get('displayTitle', '').upper()
                cid = stream.get('codecID', '').upper()
                if stream.get('DOVIBLPresent') == '1' or 'DOVI' in cid or 'DV' in dt:
                    hdr_type = 'DV/HDR' if 'HDR' in dt else 'DV'
                elif 'HDR10+' in dt:
                    hdr_type = 'HDR10+'
                elif 'HDR' in dt or stream.get('colorTransfer') in ('smpte2084', 'arib-std-b67'):
                    hdr_type = 'HDR'
            elif stype == '2' and not audio_extra:
                dt = stream.get('displayTitle', '').upper()
                if 'ATMOS' in dt:
                    audio_extra = 'Atmos'
                elif 'DTS:X' in dt or 'DTSX' in dt:
                    audio_extra = 'DTS:X'
            if hdr_type and audio_extra:
                break

    if hdr_type:
        parts.append('[ %s ]' % hdr_type)

    v_codec = media.get('videoCodec', '').lower()
    if v_codec:
        cmap = {'hevc': 'HEVC', 'h264': 'H.264', 'h265': 'H.265', 'av1': 'AV1'}
        parts.append('[ %s ]' % cmap.get(v_codec, v_codec.upper()))

    a_codec = media.get('audioCodec', '').lower()
    a_ch = media.get('audioChannels', '')
    if a_codec:
        amap = {
            'truehd': 'TrueHD', 'dca': 'DTS', 'dts': 'DTS',
            'dtshd': 'DTS-HD', 'eac3': 'EAC3', 'ac3': 'AC3',
            'aac': 'AAC', 'mp3': 'MP3', 'flac': 'FLAC',
        }
        a_label = amap.get(a_codec, a_codec.upper())
        if audio_extra:
            a_label += ' ' + audio_extra
        if a_ch:
            ch_map = {'1': '1.0', '2': '2.0', '6': '5.1', '8': '7.1'}
            a_label += ' ' + ch_map.get(str(a_ch), '%sch' % a_ch)
        parts.append('[ %s ]' % a_label)

    size_str = ''
    if part_el is not None:
        sz = part_el.get('size', '')
        if sz:
            try:
                gb = int(sz) / (1024 ** 3)
                size_str = ('[ %.1f GB ]' % gb) if gb >= 1 else ('[ %.0f MB ]' % (int(sz) / (1024 ** 2)))
                parts.append(size_str)
            except ValueError:
                pass

    return ' • '.join(parts), size_str


def _get_show_preview_media_info(server, element):
    if element is None:
        return '', ''

    media_info, size_str = _get_media_info(element)
    if media_info:
        return media_info, size_str

    rating_key = element.get('ratingKey', '')
    if not rating_key:
        return '', ''

    try:
        preview_tree = server.processed_xml('/library/metadata/%s/allLeaves?X-Plex-Container-Start=0&X-Plex-Container-Size=1' % rating_key)
        if preview_tree is None:
            return '', ''
        preview = preview_tree.find('.//Video') or preview_tree.find('Video')
        if preview is None:
            return '', ''
        return _get_media_info(preview)
    except Exception as error:
        LOG.debug('Show preview media info error: %s' % str(error))
        return '', ''


def _build_list_item(server, res, video_type, media_info, size_str, srv_name, score=0, original_title=''):
    if video_type == 'movie':
        year = res.get('year', '')
        main_title = '%s (%s)' % (res.get('title', ''), year) if year else res.get('title', '')
    elif video_type == 'show':
        year = res.get('year', '')
        main_title = '%s (%s)' % (res.get('title', ''), year) if year else res.get('title', '')
    else:
        main_title = '%s  S%sE%s - %s' % (
            res.get('grandparentTitle', ''),
            str(res.get('parentIndex', '')).zfill(2),
            str(res.get('index', '')).zfill(2),
            res.get('title', i18n('Unknown')),
        )

    list_item = xbmcgui.ListItem(label=main_title)

    sub = []
    quality = media_info.replace(size_str, '').rstrip(' •').strip() if media_info else ''
    if quality:
        sub.append(quality)
    if original_title and _normalize_text(original_title) != _normalize_text(res.get('title', '')):
        sub.append(original_title)
    if srv_name:
        sub.append('[%s]' % srv_name)
    if size_str:
        sub.append(size_str)
    if score and video_type in ('movie', 'show'):
        sub.append('score:%s' % score)
    if sub:
        list_item.setLabel2('  |  '.join(p for p in sub if p))

    thumb = res.get('thumb') or res.get('grandparentThumb') or res.get('parentThumb') or ''
    if thumb:
        try:
            art_url = server.get_formatted_url(thumb)
            list_item.setArt({'thumb': art_url, 'poster': art_url, 'icon': art_url})
        except Exception as error:
            LOG.debug('Art error: %s' % str(error))

    return list_item


def _candidate_ids(params, *names):
    values = []
    seen = set()
    for name in names:
        value = params.get(name, '')
        if value:
            value = unquote(str(value)).strip()
            if value and value not in seen:
                seen.add(value)
                values.append(value)
    return values


def _guid_candidates(params, video_type):
    imdb_ids = _candidate_ids(params, 'imdb_id', 'imdb', 'imdbid')
    tmdb_ids = _candidate_ids(params, 'tmdb_id', 'tmdb', 'tmdbid')
    tvdb_ids = _candidate_ids(params, 'tvdb_id', 'tvdb', 'tvdbid')

    guids = []
    seen = set()

    def add(candidate):
        if candidate and candidate not in seen:
            seen.add(candidate)
            guids.append(candidate)

    if video_type == 'movie':
        for imdb_id in imdb_ids:
            add('imdb://%s' % imdb_id)
        for tmdb_id in tmdb_ids:
            add('tmdb://%s' % tmdb_id)
            add('themoviedb://%s' % tmdb_id)
    elif video_type == 'show':
        for tvdb_id in tvdb_ids:
            add('tvdb://%s' % tvdb_id)
            add('thetvdb://%s' % tvdb_id)
        for tmdb_id in tmdb_ids:
            add('tmdb://%s' % tmdb_id)
            add('themoviedb://%s' % tmdb_id)
            add('themoviedb://tv-%s' % tmdb_id)
        for imdb_id in imdb_ids:
            add('imdb://%s' % imdb_id)
    else:
        for tvdb_id in tvdb_ids:
            add('tvdb://%s' % tvdb_id)
            add('thetvdb://%s' % tvdb_id)
        for tmdb_id in tmdb_ids:
            add('tmdb://%s' % tmdb_id)
            add('themoviedb://%s' % tmdb_id)
            add('themoviedb://tv-%s' % tmdb_id)
        for imdb_id in imdb_ids:
            add('imdb://%s' % imdb_id)

    return guids


def _normalized_query_list(params):
    seen = set()
    queries = []
    for key in ('original_title', 'query', 'title', 'show_title', 'grandparentTitle'):
        value = params.get(key, '')
        if not value:
            continue
        value = unquote(str(value)).strip()
        if not value:
            continue
        for candidate in (value, value.replace(':', ' ').replace('  ', ' ').strip()):
            normalized = candidate.lower()
            if candidate and normalized not in seen:
                seen.add(normalized)
                queries.append(candidate)
    return queries


def _search_by_guid(server, guid_url):
    results = []
    try:
        url = '/library/all?guid=%s&includeGuids=1' % quote(guid_url)
        xml = server.processed_xml(url)
        if xml is not None and xml.get('size', '0') != '0':
            results = [(server.get_uuid(), xml, x) for x in xml]
    except Exception as error:
        LOG.debug('GUID search error on %s: %s' % (server.get_uuid(), str(error)))
    return results


def _search_section(server, section, content_type, search_type, query):
    results = []
    if section.get_type() != content_type:
        return results

    encoded_query = quote(query)
    candidate_urls = [
        '%s/search?type=%s&query=%s' % (section.get_path(), search_type, encoded_query),
        '%s/all?type=%s&title=%s' % (section.get_path(), search_type, encoded_query),
    ]

    for url in candidate_urls:
        try:
            xml = server.processed_xml(url)
            if xml is not None and xml.get('size', '0') != '0':
                results.extend((server.get_uuid(), xml, x) for x in xml)
        except Exception as error:
            LOG.debug('Section search error [%s]: %s' % (url, str(error)))
    return results


def _get_servers_and_sections(context):
    servers = []
    search_tasks = []
    for server in context.plex_network.get_server_list():
        try:
            if server.is_offline():
                continue
            servers.append(server)
            for section in server.get_sections():
                search_tasks.append((server, section))
        except Exception as error:
            LOG.debug('Server error: %s' % str(error))
    return servers, search_tasks


def _dedupe_results(raw_results):
    deduped = []
    seen = set()
    for s_uuid, tree, res in raw_results:
        key = (s_uuid, res.get('ratingKey', ''), res.get('key', ''), res.get('type', ''), res.get('title', ''))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((s_uuid, tree, res))
    return deduped


def _expected_type(video_type, result_type):
    result_type = str(result_type or '').lower()
    if video_type == 'movie':
        return result_type == 'movie'
    if video_type == 'show':
        return result_type in ('show', 'directory')
    return result_type == 'episode'


def _match_score(params, video_type, res, full_element=None):
    element = full_element if full_element is not None else res
    result_type = str(element.get('type', res.get('type', '')) or element.tag or '').lower()
    if not _expected_type(video_type, result_type):
        return -1000

    score = 0
    result_ids = _extract_guid_ids(element)
    requested_ids = {
        'imdb_id': _candidate_ids(params, 'imdb_id', 'imdb', 'imdbid'),
        'tmdb_id': _candidate_ids(params, 'tmdb_id', 'tmdb', 'tmdbid'),
        'tvdb_id': _candidate_ids(params, 'tvdb_id', 'tvdb', 'tvdbid'),
    }

    for key, bonus in (('imdb_id', 900), ('tmdb_id', 800), ('tvdb_id', 850)):
        if result_ids.get(key) and result_ids[key] in requested_ids[key]:
            score += bonus

    result_title = _normalize_text(element.get('title', res.get('title', '')))
    result_original = _normalize_text(element.get('originalTitle', '') or element.get('titleSort', ''))
    queries = [_normalize_text(q) for q in _normalized_query_list(params)]
    queries = [q for q in queries if q]

    for query in queries:
        if query == result_title:
            score += 220
        elif query and query in result_title:
            score += 120
        if query and result_original and query == result_original:
            score += 260
        elif query and result_original and query in result_original:
            score += 140

    requested_year = str(unquote(str(params.get('year', '') or ''))).strip()
    result_year = str(element.get('year', res.get('year', '')) or '').strip()
    if requested_year and result_year and requested_year == result_year:
        score += 80

    requested_season = str(unquote(str(params.get('season', '') or ''))).strip()
    requested_episode = str(unquote(str(params.get('episode', '') or ''))).strip()
    if video_type == 'episode':
        if requested_season and requested_season == str(element.get('parentIndex', '') or res.get('parentIndex', '')):
            score += 120
        if requested_episode and requested_episode == str(element.get('index', '') or res.get('index', '')):
            score += 120

    server_name = res.get('server_name_tag', '')
    if server_name:
        score += 1
    return score


def run(context):
    context.plex_network = plex.Plex(context.settings, load=True)
    params = context.params

    video_type = params.get('video_type')
    if video_type not in VIDEO_TYPES:
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    search_config = VIDEO_TYPES[video_type]
    servers, search_tasks = _get_servers_and_sections(context)
    raw_results = []

    guid_candidates = _guid_candidates(params, video_type)
    if guid_candidates:
        LOG.debug('Searching by GUID candidates: %s' % guid_candidates)
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(_search_by_guid, server, guid) for server in servers for guid in guid_candidates]
            for future in as_completed(futures):
                try:
                    raw_results.extend(future.result())
                except Exception as error:
                    LOG.debug('GUID future error: %s' % str(error))
        raw_results = _dedupe_results(raw_results)

    if not raw_results:
        search_queries = _normalized_query_list(params)
        if not search_queries:
            user_query = _get_search_query()
            if user_query:
                search_queries = [user_query]
        if not search_queries:
            xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
            return

        LOG.debug('Falling back to title search: %s' % search_queries)
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(_search_section, server, section,
                                search_config['content_type'], search_config['search_type'], query)
                for query in search_queries for server, section in search_tasks
            ]
            for future in as_completed(futures):
                try:
                    raw_results.extend(future.result())
                except Exception as error:
                    LOG.debug('Title future error: %s' % str(error))
        raw_results = _dedupe_results(raw_results)

    if not raw_results:
        xbmcgui.Dialog().notification(
            i18n('Search'), i18n('No results found'),
            xbmcgui.NOTIFICATION_INFO, 3000
        )
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    items = []
    dialog_items = []

    def _process_result(entry):
        s_uuid, tree, res = entry
        try:
            server = context.plex_network.get_server_from_uuid(s_uuid)
            server_name = server.get_name() if hasattr(server, 'get_name') else ''
            rating_key = res.get('ratingKey', '')
            full = _fetch_full_metadata(server, rating_key) if rating_key else None
            element = full if full is not None else res
            media_info, size_str = _get_media_info(element)
            if video_type == 'show' and not media_info:
                media_info, size_str = _get_show_preview_media_info(server, element)
            score = _match_score(params, video_type, res, element)
            if score < 0:
                return None

            original_title = element.get('originalTitle', '') or element.get('titleSort', '')
            list_item = _build_list_item(server, element, video_type, media_info, size_str, server_name, score, original_title)
            item = Item(server, '', tree, element)
            item.data.set('server_name_tag', server_name)
            item.data.set('match_score', str(score))
            return score, list_item, item
        except Exception as error:
            LOG.debug('Process error: %s' % str(error))
            return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_process_result, entry) for entry in raw_results]
        for future in as_completed(futures):
            result = future.result()
            if result:
                score, list_item, item = result
                dialog_items.append((score, list_item))
                items.append((score, item))

    if not items:
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    combined = list(zip(dialog_items, items))
    combined.sort(key=lambda pair: (-pair[0][0], pair[1][1].data.get('title', '').lower()))
    dialog_items = [pair[0][1] for pair in combined]
    items = [pair[1][1] for pair in combined]

    if guid_candidates and len(items) == 1:
        selected = 0
    else:
        selected = xbmcgui.Dialog().select(i18n('Select to play'), dialog_items, useDetails=True)

    if selected < 0:
        xbmcplugin.endOfDirectory(get_handle(), succeeded=False, cacheToDisc=False)
        return

    final_item = items[selected]
    if video_type == 'movie':
        ready = create_movie_item(context, final_item)
    elif video_type == 'show':
        ready = create_show_item(context, final_item)
    else:
        ready = create_episode_item(context, final_item)

    xbmcplugin.addDirectoryItems(get_handle(), [ready], 1)
    xbmcplugin.setContent(get_handle(), search_config['content'])
    xbmcplugin.endOfDirectory(get_handle(), succeeded=True, cacheToDisc=False)


def _get_search_query():
    kb = xbmc.Keyboard('', i18n('Search...'))
    kb.setHeading(i18n('Enter search term'))
    kb.doModal()
    if kb.isConfirmed():
        text = kb.getText().strip()
        return text if text else ''
    return ''
