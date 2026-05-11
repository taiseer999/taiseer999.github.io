# -*- coding: utf-8 -*-
"""
    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2026 DPlex (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from urllib.parse import quote_plus
import xbmcvfs
import sqlite3 as _sq 

from ..constants import CONFIG
from ..logger import Logger
from ..strings import encode_utf8

LOG = Logger()

# --- Clearlogo Cache and DB Setup ---
_clearlogo_cache = {}
_TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/original'
_TMDBHELPER_DB = 'special://userdata/addon_data/plugin.video.themoviedb.helper/database_07/ItemDetails.db'

def get_clearlogo_from_db(tmdb_id, media_type='movie'):
    if not tmdb_id: return ''
    if media_type in ['tvshow', 'episode', 'season']: media_type = 'tv'
    
    cache_key = '%s*%s' % (tmdb_id, media_type)
    if cache_key in _clearlogo_cache: return _clearlogo_cache[cache_key]
        
    try:
        parent_id = '%s.%s' % (media_type, tmdb_id)
        db_path = xbmcvfs.translatePath(_TMDBHELPER_DB)
        conn = _sq.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT icon FROM art WHERE type='logos' AND parent_id=? "
            "ORDER BY CASE WHEN iso_language='en' THEN 0 ELSE 1 END, rating DESC LIMIT 1",
            (parent_id,)
        )
        row = cur.fetchone()
        conn.close()
        
        icon = row[0] if row and row[0] else ''
        if icon and '](' in icon: icon = icon.split('](')[-1].replace(')', '')
        logo = icon if icon.startswith('http') else _TMDB_IMAGE_BASE + icon if icon else ''
        _clearlogo_cache[cache_key] = logo
        return logo
    except Exception as e:
        LOG.debug('Clearlogo DB Error: %s' % str(e))
        _clearlogo_cache[cache_key] = ''
        return ''

def get_guid_ids(data):
    guid_ids = {'imdb_id': '', 'tmdb_id': '', 'tvdb_id': ''}
    if data is None: return guid_ids

    for guid_tag in data.findall('Guid'):
        guid_value = guid_tag.get('id', '')
        if guid_value.startswith('imdb://'): guid_ids['imdb_id'] = guid_value.replace('imdb://', '')
        elif guid_value.startswith('tmdb://'): guid_ids['tmdb_id'] = guid_value.replace('tmdb://', '')
        elif guid_value.startswith('tvdb://'): guid_ids['tvdb_id'] = guid_value.replace('tvdb://', '')

    legacy_guid = data.get('guid', '')
    if not guid_ids['imdb_id'] and 'imdb://' in legacy_guid:
        try: guid_ids['imdb_id'] = legacy_guid.split('imdb://')[1].split('?')[0]
        except: pass
    if not guid_ids['tmdb_id'] and 'themoviedb://' in legacy_guid:
        try: guid_ids['tmdb_id'] = legacy_guid.split('themoviedb://')[1].split('?')[0]
        except: pass
    if not guid_ids['tvdb_id'] and 'thetvdb://' in legacy_guid:
        try: guid_ids['tvdb_id'] = legacy_guid.split('thetvdb://')[1].split('?')[0]
        except: pass
    return guid_ids

def get_link_url(server, url, path_data):
    path = path_data.get('key', '')
    if path == '': return ''
    if path.startswith('http'): return path
    if path.startswith('/'): return server.join_url(server.get_url_location(), path)
    if path.startswith('plex:'):
        components = path.split('&')
        for idx in components:
            if 'prefix=' in idx:
                components.remove(idx)
                break
        if path_data.get('identifier'): components.append('identifier=' + path_data['identifier'])
        path = '&'.join(components)
        return 'plex://' + server.get_location() + '/' + '/'.join(path.split('/')[3:])
    if path.startswith('rtmp'): return path
    return server.join_url(url, path)

def _build_plex_transcode_url(path, width, height, fmt='jpeg'):
    """Build a Plex /photo/:/transcode URL with explicit JPEG output.

    `format=jpeg` overrides Plex's content negotiation so we always get JPEG
    even on Plex builds that would otherwise serve WebP — Kodi's WebP support
    is patchy across versions/skins and skin overlay drawing depends on the
    underlying poster being decoded in time.

    `minSize=1` + `upscale=0` keep aspect and avoid blurry upscaling.
    """
    return '/photo/:/transcode?url=%s&width=%s&height=%s&minSize=1&upscale=0&format=%s' % (
        quote_plus('http://localhost:32400' + path), width, height, fmt
    )


def _is_plex_placeholder(path):
    path = encode_utf8(path or '')
    return path == '' or '/:/resources/' in path


def get_thumb_image(context, server, data, width=720, height=720, fallback=None):
    if context.settings.skip_images():
        return ''

    if fallback is None:
        fallback = CONFIG['icon']

    thumbnail = encode_utf8((data.get('thumb', '') or '').split('?t')[0])
    if thumbnail.startswith('http'):
        return thumbnail
    if thumbnail.startswith('/') and not _is_plex_placeholder(thumbnail):
        # Full-resolution thumbs (default ON in DPlex): hand back the raw
        # path. Plex serves the original from cache — no server-side
        # transcode load, full quality, fast. In practice almost all Plex
        # posters are JPEG already; the rare uploaded WebP collection
        # poster is the trade-off, but skin overlays still render because
        # the network request is short and the image is decoded promptly.
        if context.settings.full_resolution_thumbnails():
            return server.get_kodi_header_formatted_url(thumbnail + '.jpg')
        # Reduced-quality path: go through the transcoder. Pin format=jpeg
        # so we don't get WebP back (that was the silent breakage cause for
        # users who had full-res thumbs disabled).
        return server.get_kodi_header_formatted_url(
            _build_plex_transcode_url(thumbnail, width, height)
        )
    return fallback


def get_banner_image(context, server, data, width=720, height=720):
    if context.settings.skip_images():
        return ''

    banner = encode_utf8(data.get('banner', '').split('?t')[0])
    if banner.startswith('http'):
        return banner
    if banner.startswith('/'):
        if context.settings.full_resolution_thumbnails():
            return server.get_kodi_header_formatted_url(banner + '.jpg')
        return server.get_kodi_header_formatted_url(
            _build_plex_transcode_url(banner, width, height)
        )
    return ''


def get_fanart_image(context, server, data, width=1280, height=720):
    if context.settings.skip_images():
        return ''

    fanart = encode_utf8((data.get('art', '') or '').split('?t')[0])
    if fanart.startswith('http'):
        return fanart
    if fanart.startswith('/') and not _is_plex_placeholder(fanart):
        if context.settings.full_resolution_fanart():
            return server.get_kodi_header_formatted_url(fanart + '.jpg')
        return server.get_kodi_header_formatted_url(
            _build_plex_transcode_url(fanart, width, height)
        )
    return ''

def get_media_data(tag_dict):
    """استخراج دقيق لتفاصيل الميديا لتظهر كعلامات (Flags) في كودي"""
    audio_codec_map = {'aac': 'AAC', 'ac3': 'Dolby Digital', 'dca': 'DTS', 'dca-ma': 'DTS-HD MA', 'eac3': 'Dolby Digital+', 'mp3': 'MP3', 'flac': 'FLAC', 'truehd': 'Dolby TrueHD'}
    video_codec_map = {'av1': 'AV1', 'h264': 'H264', 'hevc': 'H265', 'mpeg4': 'MPEG-4'}
    resolution_map = {'sd': 'SD', '480': '480p', '576': '576p', '720': '720p', '1080': '1080p', '4k': '4K'}
    
    audio_channels_raw = tag_dict.get('audioChannels', '')
    bitrate_raw = tag_dict.get('bitrate', '')
    try: bitrate = f"{round(int(bitrate_raw) / 1000, 1)} Mbps" if bitrate_raw else ''
    except: bitrate = ''

    codec_audio = audio_codec_map.get(tag_dict.get('audioCodec', ''), tag_dict.get('audioCodec', ''))
    codec_video = video_codec_map.get(tag_dict.get('videoCodec', ''), tag_dict.get('videoCodec', ''))
    res_video = resolution_map.get(tag_dict.get('videoResolution', ''), tag_dict.get('videoResolution', ''))
    channels = audio_channels_raw + '.0' if audio_channels_raw.isdigit() and len(audio_channels_raw) == 1 else audio_channels_raw

    audio_full = f"{codec_audio} {channels}".strip()

    # Pixel width: prefer Plex's explicit `width`. Fallback to a value derived
    # from `videoResolution` so skins that key off stream info (Aura, Arctic
    # Fuse, Estuary Mod) still see a non-zero width and render the resolution
    # badge. Without this, Plex sources missing `width` would silently fail.
    explicit_width = 0
    try:
        explicit_width = int(tag_dict.get('width', 0) or 0)
    except (TypeError, ValueError):
        explicit_width = 0
    fallback_width = 0
    _vr = (tag_dict.get('videoResolution', '') or '').lower().strip()
    if _vr in ('4k', 'uhd', '2160', '2160p'): fallback_width = 3840
    elif _vr in ('1440', '1440p', 'qhd', '2k'): fallback_width = 2560
    elif _vr in ('1080', '1080p', 'fhd'): fallback_width = 1920
    elif _vr in ('720', '720p', 'hd'): fallback_width = 1280
    elif _vr in ('480', '480p', 'sd'): fallback_width = 720
    final_width = explicit_width or fallback_width

    return {
        'VideoResolution': res_video or tag_dict.get('videoResolution', ''),
        'VideoCodec': codec_video or tag_dict.get('videoCodec', ''),
        'AudioCodec': codec_audio or tag_dict.get('audioCodec', ''),
        'AudioChannels': channels,
        'VideoAspect': tag_dict.get('aspectRatio', ''),
        'stream_info': {
            'video': {
                'codec': codec_video or tag_dict.get('videoCodec', ''),
                'aspect': float(tag_dict.get('aspectRatio', '1.78') or '1.78'),
                'height': int(tag_dict.get('height', 0) or 0),
                'width': final_width,
                'duration': int(tag_dict.get('duration', 0) or 0) / 1000
            },
            'audio': {'codec': audio_full, 'channels': 0},
        },
    }

def get_metadata(context, data):
    metadata = {'attributes': {}, 'cast': [], 'collections': [], 'director': [], 'genre': [], 'writer': []}
    media_tag = data.find('Media')
    if media_tag is not None: metadata['attributes'] = dict(media_tag.items())

    if not context.settings.skip_metadata():
        for child in data:
            val = child.get('tag')
            if not val: continue
            if child.tag == 'Genre': metadata['genre'].append(val)
            elif child.tag == 'Writer': metadata['writer'].append(val)
            elif child.tag == 'Director': metadata['director'].append(val)
            elif child.tag == 'Role': metadata['cast'].append(val)
            elif child.tag == 'Collection': metadata['collections'].append(val)
    return metadata
