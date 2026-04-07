# -*- coding: utf-8 -*-

"""
episode_item.py — نسخة محسّنة للأداء والشعارات وعلامات الجودة (Complete Version)
"""

import json
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

LOG = Logger('episode_item')


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
        audio_map = {'truehd': 'TrueHD', 'dca': 'DTS', 'dts': 'DTS', 'dtshd': 'DTS-HD', 'eac3': 'EAC3', 'ac3': 'AC3', 'aac': 'AAC', 'mp3': 'MP3', 'flac': 'FLAC'}
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


def create_episode_item(context, item, library=False):
    metadata = get_metadata(context, item.data)
    guid_ids = get_guid_ids(item.data)
    rating_key = str(item.data.get('ratingKey', ''))

    info_labels = {
        'plot': encode_utf8(item.data.get('summary', '')),
        'title': encode_utf8(item.data.get('title', i18n('Unknown'))),
        'sorttitle': encode_utf8(item.data.get('titleSort', item.data.get('title', i18n('Unknown')))),
        'rating': float(item.data.get('rating', 0)),
        'studio': [encode_utf8(item.data.get('studio', item.tree.get('studio', '')))],
        'mpaa': item.data.get('contentRating', item.tree.get('grandparentContentRating', '')),
        'year': int(item.data.get('year', 0)),
        'tagline': encode_utf8(item.data.get('tagline', '')),
        'episode': int(item.data.get('index', 0)),
        'aired': item.data.get('originallyAvailableAt', ''),
        'tvshowtitle': encode_utf8(item.data.get('grandparentTitle', item.tree.get('grandparentTitle', ''))),
        'season': int(item.data.get('parentIndex', item.tree.get('parentIndex', 0))),
        'mediatype': 'episode',
        'playcount': int(int(item.data.get('viewCount', 0)) > 0),
        'cast': metadata['cast'],
        'director': metadata['director'],
        'genre': metadata['genre'],
        'writer': metadata['writer'],
    }

    media_info_text = _get_media_info(item.data, rating_key=rating_key)
    library_title = item.data.get('library_title_tag', '')
    server_name = item.data.get('server_name_tag', '')
    if library_title:
        media_info_text = ('%s • [ %s ]' % (media_info_text, library_title)) if media_info_text else ('[ %s ]' % library_title)
    if server_name:
        media_info_text = ('%s • [ %s ]' % (media_info_text, server_name)) if media_info_text else ('[ %s ]' % server_name)
    if media_info_text:
        info_labels['plot'] = '%s\n\n%s' % (media_info_text, info_labels['plot'])

    if guid_ids.get('imdb_id'): info_labels['imdbnumber'] = guid_ids['imdb_id']

    prefix_sxee = (item.tree.get('mixedParents') == '1' or context.settings.episode_sort_method() == 'plex' or item.data.get('force_sxee_prefix') == '1')
    prefix_tvshow = ((item.tree.get('parentIndex') != '1' and context.params.get('mode') == '0') or item.data.get('force_show_prefix') == '1')
    prefix_server = (context.params.get('mode') in COMBINED_SECTIONS and context.settings.prefix_server_in_combined())

    if not library:
        if prefix_sxee:
            info_labels['title'] = '%sx%s %s' % (info_labels['season'], str(info_labels['episode']).zfill(2), info_labels['title'])
            if prefix_tvshow: info_labels['title'] = '%s - %s' % (info_labels['tvshowtitle'], info_labels['title'])
        if prefix_server:
            info_labels['title'] = '%s: %s' % (item.server.get_name(), info_labels['title'])

    view_offset = item.data.get('viewOffset', 0)
    duration = int(metadata['attributes'].get('duration', item.data.get('duration', 0))) / 1000
    art = _get_art(context, item)

    # --- [الحل الجذري للوجو المسلسلات في On Deck] ---
    show_tmdb_id = ''
    gp_guid = item.data.get('grandparentGuid', '')
    if 'themoviedb://' in gp_guid: show_tmdb_id = gp_guid.split('themoviedb://')[1].split('?')[0].replace('tv-', '')
    elif 'tmdb://' in gp_guid: show_tmdb_id = gp_guid.split('tmdb://')[1].split('?')[0]

    # إذا وكيل بليكس الجديد أخفى الـ ID، نرسل العميل السري لسيرفر بليكس يطلعه بالقوة!
    if not show_tmdb_id and item.data.get('grandparentRatingKey'):
        try:
            gp_meta = item.server.get_metadata(item.data.get('grandparentRatingKey'))
            if gp_meta is not None:
                dir_tag = gp_meta.find('.//Directory')
                if dir_tag is not None:
                    show_guids = get_guid_ids(dir_tag)
                    show_tmdb_id = show_guids.get('tmdb_id', '')
        except Exception as e:
            LOG.debug('Failed to fetch fallback Show TMDB ID: %s' % str(e))
    
    clearlogo_url = get_clearlogo_from_db(show_tmdb_id, 'tv') if show_tmdb_id else ''
    # ------------------------------------------------

    extra_data = {
        'type': 'Video',
        'source': 'tvepisodes',
        'thumb': art.get('thumb', ''),
        'fanart_image': art.get('fanart', ''),
        'banner': art.get('banner', ''),
        'season_thumb': art.get('season_thumb', ''),
        'clearlogo': clearlogo_url,
        'key': item.data.get('key', ''),
        'ratingKey': rating_key,
        'parentRatingKey': str(item.data.get('parentRatingKey', 0)),
        'grandparentRatingKey': str(item.data.get('grandparentRatingKey', 0)),
        'duration': duration,
        'resume': int(int(view_offset) / 1000),
        'season': info_labels.get('season'),
        'tvshowtitle': info_labels.get('tvshowtitle'),
        'imdb_id': guid_ids.get('imdb_id', ''),
        'tmdb_id': guid_ids.get('tmdb_id', ''),
        'tvdb_id': guid_ids.get('tvdb_id', ''),
        'mode': MODES.PLAYLIBRARY
    }

    if item.up_next is False: extra_data['parameters'] = {'up_next': str(item.up_next).lower()}
    if item.tree.tag == 'MediaContainer': extra_data['library_section_uuid'] = item.tree.get('librarySectionUUID')
    
    # تفويض استخراج بيانات الميديا العادية (الكوديك/الأبعاد) لملف gui.py
    if not context.settings.skip_flags():
        extra_data.update(get_media_data(metadata['attributes']))
        
    if library: extra_data['path_mode'] = MODES.TXT_TVSHOWS_LIBRARY

    context_menu = None
    if not context.settings.skip_context_menus():
        context_menu = ContextMenu(context, item.server, item.url, extra_data).menu

    item_url = item.server.join_url(item.server.get_url_location(), extra_data['key'])
    gui_item = GUIItem(item_url, info_labels, extra_data, context_menu)
    gui_item.is_folder = False

    kodi_item = create_gui_item(context, gui_item)

    # --- [حقن خصائص الـ HDR والـ Atmos المتقدمة لسكين Arctic Fuse فقط] ---
    try:
        list_item = kodi_item[1] if isinstance(kodi_item, tuple) else kodi_item
        media = item.data.find('Media') or item.data.find('.//Media')
        if media is not None:
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

        if clearlogo_url:
            list_item.setArt({'clearlogo': clearlogo_url, 'tvshow.clearlogo': clearlogo_url})
            
    except Exception as e:
        LOG.debug('Advanced properties injection error: %s' % str(e))

    return kodi_item


def _get_art(context, item):
    art = {'banner': '', 'fanart': '', 'season_thumb': '', 'section_art': '', 'thumb': ''}

    if not context.settings.skip_images():
        art.update({
            'banner': get_banner_image(context, item.server, item.tree),
            'fanart': get_fanart_image(context, item.server, item.data),
            'season_thumb': '',
            'section_art': get_fanart_image(context, item.server, item.tree),
            'thumb': get_thumb_image(context, item.server, item.data),
        })

        if '/:/resources/show-fanart.jpg' in art['section_art']:
            art['section_art'] = art.get('fanart', '')
        if art['fanart'] == '' or '-1' in art['fanart']:
            art['fanart'] = art.get('section_art', '')
        if art.get('season_thumb') and '/:/resources/show.png' not in art.get('season_thumb', ''):
            art['season_thumb'] = get_thumb_image(context, item.server, {'thumb': art.get('season_thumb')})
        if not art.get('season_thumb') and item.data.get('parentThumb', '') and '/:/resources/show.png' not in item.data.get('parentThumb', ''):
            art['season_thumb'] = get_thumb_image(context, item.server, {'thumb': item.data.get('parentThumb', '')})
        elif not art.get('season_thumb') and item.data.get('grandparentThumb', '') and '/:/resources/show.png' not in item.data.get('grandparentThumb', ''):
            art['season_thumb'] = get_thumb_image(context, item.server, {'thumb': item.data.get('grandparentThumb', '')})
    return art
