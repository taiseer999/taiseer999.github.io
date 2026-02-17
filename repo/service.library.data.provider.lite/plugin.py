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
import xbmcplugin
import xbmcaddon
from resources.lib import data
from resources.lib import router

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_LANGUAGE = ADDON.getLocalizedString


def log(txt):
    message = '%s: %s' % (ADDON_NAME, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


class Main:

    def __init__(self):
        self._parse_argv()
        if not self.TYPE:
            router.run()
        for content_type in self.TYPE.split("+"):
            full_liz = list()
            if content_type == "movie":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                data.parse_dbid('movie', self.dbid, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "episode":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                data.parse_dbid('episode', self.dbid, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "song":
                xbmcplugin.setContent(int(sys.argv[1]), 'songs')
                data.parse_dbid('song', self.dbid, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def _parse_argv(self):
        try:
            params = dict(arg.split("=") for arg in sys.argv[2].split("&"))
        except:
            params = {}
        self.TYPE = params.get("?type", "")
        self.dbid = params.get("dbid", "")
        self.dbtype = params.get("dbtype", False)


log('script version %s started' % ADDON_VERSION)
Main()
log('script version %s stopped' % ADDON_VERSION)
