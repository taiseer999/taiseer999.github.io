#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create and delete playlists on the Kodi side of things
"""
from logging import getLogger
import re

from .common import Playlist, kodi_playlist_hash
from . import db, pms

from ..plex_api import API
from .. import utils, path_ops, variables as v
from ..exceptions import PlaylistError

###############################################################################
LOG = getLogger('PLEX.playlists.kodi_pl')
REGEX_FILE_NUMBERING = re.compile(r'''_(\d\d)\.\w+$''')
# Avoid endless loops. Store the Kodi paths
IGNORE_KODI_PLAYLIST_CHANGE = list()
###############################################################################


def create(plex_id):
    """
    Creates a new Kodi playlist file. Will also add (or modify an existing)
    Plex playlist table entry.
    Assumes that the Plex playlist is indeed new. A NEW Kodi playlist will be
    created in any case (not replaced). Thus make sure that the "same" playlist
    is deleted from both disk and the Plex database.
    Returns the playlist or raises PlaylistError
    """
    xml_metadata = pms.metadata(plex_id)
    if xml_metadata is None:
        LOG.error('Could not get Plex playlist metadata %s', plex_id)
        raise PlaylistError('Could not get Plex playlist %s' % plex_id)
    api = API(xml_metadata[0])
    playlist = Playlist()
    playlist.plex_id = api.plex_id
    playlist.kodi_type = v.KODI_PLAYLIST_TYPE_FROM_PLEX[api.playlist_type()]
    playlist.plex_name = api.title()
    playlist.plex_updatedat = api.updated_at()
    LOG.debug('Creating new Kodi playlist from Plex playlist: %s', playlist)
    # Derive filename close to Plex playlist name
    name = utils.valid_filename(playlist.plex_name)
    path = path_ops.path.join(v.PLAYLIST_PATH, playlist.kodi_type,
                              '%s.m3u' % name)
    while path_ops.exists(path) or db.get_playlist(path=path):
        # In case the Plex playlist names are not unique
        occurance = REGEX_FILE_NUMBERING.search(path)
        if not occurance:
            path = path_ops.path.join(v.PLAYLIST_PATH,
                                      playlist.kodi_type,
                                      '%s_01.m3u' % name[:min(len(name), 248)])
        else:
            number = int(occurance.group(1)) + 1
            if number > 3:
                LOG.warn('Detected spanning tree issue, abort sync for %s',
                         playlist)
                raise PlaylistError('Spanning tree warning')
            basename = re.sub(REGEX_FILE_NUMBERING, '', path)
            path = '%s_%02d.m3u' % (basename, number)
    LOG.debug('Kodi playlist path: %s', path)
    playlist.kodi_path = path
    xml_playlist = pms.get_playlist(plex_id)
    if xml_playlist is None:
        LOG.error('Could not get Plex playlist %s', plex_id)
        raise PlaylistError('Could not get Plex playlist %s' % plex_id)
    IGNORE_KODI_PLAYLIST_CHANGE.append(playlist.kodi_path)
    try:
        _write_playlist_to_file(playlist, xml_playlist)
    except Exception:
        IGNORE_KODI_PLAYLIST_CHANGE.remove(playlist.kodi_path)
        raise
    playlist.kodi_hash = kodi_playlist_hash(path)
    db.update_playlist(playlist)
    LOG.debug('Created Kodi playlist based on Plex playlist: %s', playlist)


def delete(playlist):
    """
    Removes the corresponding Kodi file for playlist Playlist from
    disk. Be sure that playlist.kodi_path is set. Will also delete the entry in
    the Plex playlist table.
    Returns None or raises PlaylistError
    """
    if path_ops.exists(playlist.kodi_path):
        IGNORE_KODI_PLAYLIST_CHANGE.append(playlist.kodi_path)
        try:
            path_ops.remove(playlist.kodi_path)
            LOG.debug('Deleted Kodi playlist: %s', playlist)
        except (OSError, IOError) as err:
            LOG.error('Could not delete Kodi playlist file %s. Error:\n%s: %s',
                      playlist, err.errno, err.strerror)
            IGNORE_KODI_PLAYLIST_CHANGE.remove(playlist.kodi_path)
            raise PlaylistError('Could not delete %s' % playlist.kodi_path)
    db.update_playlist(playlist, delete=True)


def delete_kodi_playlists(playlist_paths):
    """
    Deletes all the the playlist files passed in; WILL IGNORE THIS CHANGE ON
    THE PLEX SIDE!
    """
    for path in playlist_paths:
        try:
            path_ops.remove(path)
            # Ensure we're not deleting the playlists on the Plex side later
            IGNORE_KODI_PLAYLIST_CHANGE.append(path)
            LOG.info('Removed playlist %s', path)
        except (OSError, IOError):
            LOG.warn('Could not remove playlist %s', path)


def _write_playlist_to_file(playlist, xml):
    """
    Feed with playlist Playlist. Will write the playlist to a m3u file
    Returns None or raises PlaylistError
    """
    text = '#EXTCPlayListM3U::M3U\n'
    for xml_element in xml:
        text += _m3u_element(xml_element)
    text += '\n'
    text = text.encode(v.M3U_ENCODING, 'ignore')
    try:
        with open(playlist.kodi_path, 'wb') as f:
            f.write(text)
    except EnvironmentError as err:
        LOG.error('Could not write Kodi playlist file: %s', playlist)
        LOG.error('Error message %s: %s', err.errno, err.strerror)
        raise PlaylistError('Cannot write Kodi playlist to path for %s'
                            % playlist)


def _m3u_element(xml_element):
    api = API(xml_element)
    if api.plex_type == v.PLEX_TYPE_EPISODE:
        if api.season_number() is not None and api.index() is not None:
            return '#EXTINF:{},{} S{:2d}E{:2d} - {}\n{}\n'.format(
                    api.runtime(),
                    api.show_title(),
                    api.season_number(),
                    api.index(),
                    api.title(),
                    api.fullpath(force_addon=True)[0])
        else:
            # Only append the TV show name
            return '#EXTINF:{},{} - {}\n{}\n'.format(
                api.runtime(),
                api.show_title(),
                api.title(),
                api.fullpath(force_addon=True)[0])
    elif api.plex_type == v.PLEX_TYPE_SONG:
        if api.index() is not None:
            return '#EXTINF:{},{:02d}. {} - {}\n{}\n'.format(
                api.runtime(),
                api.index(),
                api.grandparent_title(),
                api.title(),
                api.fullpath(force_first_media=True,
                             omit_check=True)[0])
        else:
            return '#EXTINF:{},{} - {}\n{}\n'.format(
                api.runtime(),
                api.grandparent_title(),
                api.title(),
                api.fullpath(force_first_media=True,
                             omit_check=True)[0])
    else:
        return '#EXTINF:{},{}\n{}\n'.format(
            api.runtime(),
            api.title(),
            api.fullpath(force_first_media=True,
                         omit_check=True)[0])
