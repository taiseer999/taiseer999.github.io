import os
import sys
import json
import xbmc
import xbmcplugin
import xbmcvfs
import xbmcgui
import xbmcaddon
from .utils import add_dir, add_dir_lists

icon_path = xbmcvfs.translatePath('special://home/addons/plugin.program.cachemgr/icons/')

#Icon Paths
addon_fanart = icon_path + 'fanart.jpg'
cache_icon = icon_path + 'cache.png'

handle = int(sys.argv[1])

def main_menu():
    xbmcplugin.setPluginCategory(handle, 'Main Menu')
    
    add_dir('Clear Cache','',1,cache_icon,addon_fanart,isFolder=False)
    add_dir('Clear All Cache','',2,cache_icon,addon_fanart,isFolder=False)
    add_dir('Clear Providers Cache','',3,cache_icon,addon_fanart,isFolder=False)
    add_dir('Clear Trakt Cache','',4,cache_icon,addon_fanart,isFolder=False)
    add_dir('Clear Movie Search History','',5,cache_icon,addon_fanart,isFolder=False)
    add_dir('Clear TV Search History','',6,cache_icon,addon_fanart,isFolder=False)
    add_dir('Clear All Search History','',7,cache_icon,addon_fanart,isFolder=False)
   