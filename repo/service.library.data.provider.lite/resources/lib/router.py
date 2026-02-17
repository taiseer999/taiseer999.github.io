#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2017 BigNoid
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

import sys# for Python 2/3 version check
import xbmcplugin
import xbmcgui
import xbmcaddon
import routing

ADDON_LANGUAGE = xbmcaddon.Addon().getLocalizedString


plugin = routing.Plugin()


def run():
    plugin.run()


@plugin.route('/')
def root():
    xbmcplugin.setPluginCategory(plugin.handle, "Media")
    items = []
    for call, title, thumb in items:
        if sys.version_info.major == 3:# Python 3
            liz = xbmcgui.ListItem(title)
            liz.setArt({"thumb": thumb})
        else:# Python 2
            liz = xbmcgui.ListItem(label=title,thumbnailImage=thumb)
        url = 'plugin://service.library.data.provider.lite?type=%s' % call
        xbmcplugin.addDirectoryItem(handle=plugin.handle,
                                    url=url,
                                    listitem=liz,
                                    isFolder=True)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(plugin.handle)
