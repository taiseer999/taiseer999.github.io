# -*- coding: utf-8 -*-

import xbmc

if __name__ == '__main__':
	plugin = 'plugin://plugin.video.infinity/'
	path = 'RunPlugin(%s?action=cache_clearBookmarks&opensettings=false)' % plugin
	xbmc.executebuiltin(path)
