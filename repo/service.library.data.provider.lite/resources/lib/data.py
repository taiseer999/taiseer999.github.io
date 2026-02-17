#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import json as simplejson


ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_LANGUAGE = ADDON.getLocalizedString


def parse_dbid(dbtype, dbid, full_liz):
    json_query = _get_query(dbtype, dbid)
    item = False
    liz = False
    while json_query == "LOADING" and not json_query['result']:
        xbmc.sleep(100)
    if json_query:
        if sys.version_info.major == 2:# Python 2
            json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'moviedetails' in json_query['result']:
            item = json_query['result']['moviedetails']
        elif 'result' in json_query and 'episodedetails' in json_query['result']:
            item = json_query['result']['episodedetails']
        elif 'result' in json_query and 'songdetails' in json_query['result']:
            item = json_query['result']['songdetails']
        # create a list item
        if item and xbmcgui.ListItem(item['label']):
            liz = xbmcgui.ListItem(item['label'])
            if dbtype == "movie":
                liz.setInfo(type="Video", infoLabels={"mediatype": "movie"})
            if dbtype == "episode":
                liz.setInfo(type="Video", infoLabels={"mediatype": "episode"})
            if dbtype == "song":
                liz.setInfo(type="Music", infoLabels={"mediatype": "song"})
        if item and liz:
            full_liz.append((item['file'], liz, False))

        del json_query


def _get_query(dbtype, dbid):
    if not dbtype:
        if xbmc.getCondVisibility("VideoPlayer.Content(movies)"):
            dbtype = 'movie'
        elif xbmc.getCondVisibility("VideoPlayer.Content(episodes)"):
            dbtype = 'episode'
        elif xbmc.getCondVisibility("VideoPlayer.Content(musicvideos)"):
            dbtype = 'musicvideo'
    if dbtype == "movie":
        method = '"VideoLibrary.GetMovieDetails"'
        param = '"movieid"'
    elif dbtype == "tvshow":
        method = '"VideoLibrary.GetTVShowDetails"'
        param = '"tvshowid"'
    elif dbtype == "episode":
        method = '"VideoLibrary.GetEpisodeDetails"'
        param = '"episodeid"'
    elif dbtype == "musicvideo":
        method = '"VideoLibrary.GetMusicVideoDetails"'
        param = '"musicvideoid"'
    elif dbtype == "song":
        method = '"AudioLibrary.GetSongDetails"'
        param = '"songid"'
    json_query = xbmc.executeJSONRPC('''{ "jsonrpc": "2.0", "method": %s,
                                                            "params": {%s: %d,
                                                            "properties": ["title", "file", "cast"]},
                                                            "id": 1 }''' % (method, param, int(dbid)))
    return json_query

