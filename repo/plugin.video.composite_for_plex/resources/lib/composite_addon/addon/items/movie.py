# -*- coding: utf-8 -*-

"""
movie_item.py — نسخة محسّنة للأداء والشعارات وعلامات الجودة (Complete Version)
"""

import datetime
import json
import xml.etree.ElementTree as ETree

from ..constants import COMBINED_SECTIONS
from ..constants import CONFIG
from ..constants import MODES
from ..containers import GUIItem
from ..logger import Logger
from ..strings import encode_utf8
from ..strings import i18n
from .common import get_clearlogo_from_db
from .common import get_fanart_image
from .common import get_guid_ids
from .common import get_media_data
from .common import get_metadata
from .common import get_thumb_image
from .context_menu import ContextMenu
from .gui import create_gui_item

try:
    from ..cache import get_media_info as cache_get_media_info
    from ..cache import set_media_info as cache_set_media_info
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

LOG = Logger('movie_item')


def _parse_streams(part_el):
    result = {'hdr_type': '', 'audio_label': '', 'has_atmos': False, 'has_dtsx': False}
    if part_el is None: return result

    found_video = False
    found_audio = False

    for stream in part_el.findall('.//Stream'):
        stype = stream.get('streamType')
        if stype == '1' and not found_video:
            dt = stream.get('displayTitle', '').upper()
            codec_id = stream.get('codecID', '').upper()
            dv_bl = stream.get('DOVIBLPresent', '0')
            dv_rpu = stream.get('DOVIRPUPresent', '0')

            if dv_bl == '1' or dv_rpu == '1' or 'DOVI' in codec_id or 'DV' in dt:
                result['hdr_type'] = 'DV/HDR' if 'HDR' in dt else 'DV'
            elif 'HDR10+' in dt: result['hdr_type'] = 'HDR10+'
            elif 'HDR' in dt or stream.get('colorTransfer', '') in ('smpte2084', 'arib-std-b67'):
                result['hdr_type'] = 'HDR'
            found_video = True

        elif stype == '2' and not found_audio:
            dt = stream.get('displayTitle', '').upper()
            if 'ATMOS' in dt:
                result['has_atmos'] = True
                result['audio_label'] = 'Atmos'
            elif 'DTS:X' in dt or 'DTSX' in dt:
                result['has_dtsx'] = True
                result['audio_label'] = 'DTS:X'
            found_audio = True

        if found_video and found_audio: break
    return result


def _get_media_info(element, rating_key=None):
    if CACHE_AVAILABLE and rating_key:
        cached = cache_get_media_info(rating_key)
        if cached is not None: return cached

    if element is None: return ''
    media = element.find('Media') or element.find('.//Media')
    if media is None: return ''

    parts = []
    resolution = media.get('videoResolution', '')
    if resolution:
        try:
            res_int = int(resolution)
            if res_int > 1088: resolution = '4K'
            elif res_int >= 1080: resolution = '1080p'
            elif res_int >= 720: resolution = '720p'
            else: resolution = 'SD'
        except: resolution = resolution.upper()
        parts.append('[ %s ]' % resolution)

    part_el = media.find('Part') or media.find('.//Part')
    streams = _parse_streams(part_el)

    if streams['hdr_type']: parts.append('[ %s ]' % streams['hdr_type'])

    video_codec = media.get('videoCodec', '').lower()
    if video_codec:
        codec_map = {'hevc': 'HEVC', 'h264': 'H.264', 'h265': 'H.265', 'av1': 'AV1', 'mpeg4': 'MPEG4', 'vc1': 'VC-1'}
        parts.append('[ %s ]' % codec_map.get(video_codec, video_codec.upper()))

    audio_codec = media.get('audioCodec', '').lower()
    audio_channels = media.get('audioChannels', '')
    if audio_codec:
        audio_map = {'truehd': 'TrueHD', 'dca': 'DTS', 'dts': 'DTS', 'dtshd': 'DTS-HD', 'eac3': 'EAC3', 'ac3': 'AC3', 'aac': 'AAC', 'mp3': 'MP3', 'flac': 'FLAC', 'opus': 'Opus'}
        audio_label = audio_map.get(audio_codec, audio_codec.upper())
        if streams['audio_label']: audio_label += ' ' + streams['audio_label']
        if audio_channels:
            try:
                ch_map = {1: '1.0', 2: '2.0', 6: '5.1', 8: '7.1'}
                audio_label += ' %s' % ch_map.get(int(audio_channels), '%sch' % audio_channels)
            except: pass
        parts.append('[ %s ]' % audio_label)

    if part_el is not None:
        size_bytes = part_el.get('size', '')
        if size_bytes:
            try:
                size_gb = int(size_bytes) / (1024 ** 3)
                if size_gb >= 1: parts.append('[ %.1f GB ]' % size_gb)
                else: parts.append('[ %.0f MB ]' % (int(size_bytes) / (1024 ** 2)))
            except: pass

    result = ' • '.join(parts)
    if CACHE_AVAILABLE and rating_key: cache_set_media_info(rating_key, result)
    return result

def _inject_stream_info(list_item, item_data, duration, streams_cache=None):
    try:
        from infotagger.listitem import ListItemInfoTag

        media = item_data.find('Media') or item_data.find('.//Media')
        if media is None:
            return

        video_res = media.get('videoResolution', '')
        v_width = 0
        if video_res == '4k':     v_width = 3840
        elif video_res == '1080': v_width = 1920
        elif video_res == '720':  v_width = 1280

        # 🌟 الوشم الإجباري لسكين Arctic Fuse لكي يرى الجودة في جميع قوائم الويدجت
        list_item.setProperty('VideoResolution', video_res)
        list_item.setProperty('VideoCodec', media.get('videoCodec', ''))
        list_item.setProperty('AudioCodec', media.get('audioCodec', ''))
        list_item.setProperty('AudioChannels', media.get('audioChannels', '2') or '2')

        info_tag = ListItemInfoTag(list_item)
        info_tag.add_stream_info('video', {
            'codec': media.get('videoCodec', ''),
            'width': v_width,
            'duration': int(duration),
        })
        info_tag.add_stream_info('audio', {
            'codec': media.get('audioCodec', ''),
            'channels': int(media.get('audioChannels', '2') or '2'),
        })

        for stream in media.findall('.//Stream'):
            if stream.get('streamType') == '3':
                info_tag.add_stream_info('subtitle', {
                    'language': stream.get('languageCode', stream.get('language', 'unk'))
                })

        if streams_cache is None:
            part_el = media.find('.//Part')
            streams_cache = _parse_streams(part_el)

        hdr = streams_cache.get('hdr_type', '')
        if 'DV' in hdr:
            list_item.setProperty('VideoCodec.HDR', 'dolbyvision')
            list_item.setProperty('hdr', 'dolbyvision')
        elif 'HDR' in hdr:
            list_item.setProperty('VideoCodec.HDR', 'hdr10')
            list_item.setProperty('hdr', 'hdr10')

        if streams_cache.get('has_atmos'):
            list_item.setProperty('AudioCodec.Atmos', 'true')
            list_item.setProperty('audio_codec', 'atmos')
        elif streams_cache.get('has_dtsx'):
            list_item.setProperty('AudioCodec.DTSX', 'true')
            list_item.setProperty('audio_codec', 'dtsx')

    except Exception as e:
        LOG.debug('Failed to inject StreamInfo in movie: %s' % str(e))


def create_movie_item(context, item, library=False):
    metadata = get_metadata(context, item.data)
    guid_ids = get_guid_ids(item.data)
    rating_key = str(item.data.get('ratingKey', ''))

    try: date_added = str(datetime.datetime.fromtimestamp(int(item.data.get('addedAt', 86400))))
    except: date_added = str(datetime.datetime.fromtimestamp(86400))

    info_labels = {
        'plot': encode_utf8(item.data.get('summary', '')),
        'title': encode_utf8(item.data.get('title', i18n('Unknown'))),
        'sorttitle': encode_utf8(item.data.get('titleSort', item.data.get('title', i18n('Unknown')))),
        'rating': float(item.data.get('rating', 0)),
        'studio': [encode_utf8(item.data.get('studio', ''))],
        'mpaa': encode_utf8(item.data.get('contentRating', '')),
        'year': int(item.data.get('year', 0)),
        'date': item.data.get('originallyAvailableAt', '1970-01-01'),
        'premiered': item.data.get('originallyAvailableAt', '1970-01-01'),
        'tagline': item.data.get('tagline', ''),
        'dateadded': date_added,
        'mediatype': 'movie',
        'playcount': int(int(item.data.get('viewCount', 0)) > 0),
        'cast': metadata['cast'],
        'director': metadata['director'],
        'genre': metadata['genre'],
        'set': ' / '.join(metadata['collections']),
        'writer': metadata['writer'],
    }

    media_info_text = _get_media_info(item.data, rating_key=rating_key)
    server_name = item.data.get('server_name_tag', '')
    if server_name: media_info_text = ('%s • [ %s ]' % (media_info_text, server_name)) if media_info_text else ('[ %s ]' % server_name)
    if media_info_text: info_labels['plot'] = '%s\n\n%s' % (media_info_text, info_labels['plot'])

    if guid_ids.get('imdb_id'): info_labels['imdbnumber'] = guid_ids['imdb_id']

    prefix_server = (context.params.get('mode') in COMBINED_SECTIONS and context.settings.prefix_server_in_combined())
    if prefix_server: info_labels['title'] = '%s: %s' % (item.server.get_name(), info_labels['title'])

    if item.data.get('primaryExtraKey') is not None:
        info_labels['trailer'] = 'plugin://' + CONFIG['id'] + '/?url=%s%s?mode=%s' % \
                                 (item.server.get_url_location(), item.data.get('primaryExtraKey', ''), MODES.PLAYLIBRARY)

    view_offset = item.data.get('viewOffset', 0)
    duration = int(metadata['attributes'].get('duration', item.data.get('duration', 0))) / 1000

    tmdb_id = guid_ids.get('tmdb_id', '')
    clearlogo_url = get_clearlogo_from_db(tmdb_id, 'movie') if tmdb_id else ''

    extra_data = {
        'type': 'Video',
        'source': 'movies',
        'thumb': get_thumb_image(context, item.server, item.data),
        'fanart_image': get_fanart_image(context, item.server, item.data),
        'clearlogo': clearlogo_url,
        'key': item.data.get('key', ''),
        'ratingKey': rating_key,
        'duration': duration,
        'resume': int(int(view_offset) / 1000),
        'imdb_id': guid_ids.get('imdb_id', ''),
        'tmdb_id': tmdb_id,
        'tvdb_id': guid_ids.get('tvdb_id', ''),
        'mode': MODES.PLAYLIBRARY
    }

    if item.up_next is False: extra_data['parameters'] = {'up_next': str(item.up_next).lower()}

    if item.tree.get('playlistType'):
        playlist_key = str(item.tree.get('ratingKey', 0))
        if item.data.get('playlistItemID') and playlist_key:
            extra_data.update({
                'playlist_item_id': item.data.get('playlistItemID'),
                'playlist_title': item.tree.get('title'),
                'playlist_url': '/playlists/%s/items' % playlist_key
            })

    if item.tree.tag == 'MediaContainer':
        extra_data['library_section_uuid'] = item.tree.get('librarySectionUUID')

    if not context.settings.skip_flags():
        extra_data.update(get_media_data(metadata['attributes']))

    context_menu = None
    if not context.settings.skip_context_menus():
        context_menu = ContextMenu(context, item.server, item.url, extra_data).menu

    if library: extra_data['path_mode'] = MODES.TXT_MOVIES_LIBRARY

    item_url = item.server.join_url(item.server.get_url_location(), extra_data['key'])
    gui_item = GUIItem(item_url, info_labels, extra_data, context_menu)
    gui_item.is_folder = False

    kodi_item = create_gui_item(context, gui_item)

    try:
        list_item = kodi_item[1] if isinstance(kodi_item, tuple) else kodi_item
        media = item.data.find('Media') or item.data.find('.//Media')
        streams_cache = None
        if media is not None:
            part_el = media.find('.//Part')
            streams_cache = _parse_streams(part_el)
        
        _inject_stream_info(list_item, item.data, duration, streams_cache)
        
        if clearlogo_url:
            list_item.setArt({'clearlogo': clearlogo_url, 'logo': clearlogo_url})
            
    except Exception as e:
        LOG.debug('Advanced properties injection error in movie: %s' % str(e))

    return kodi_item
