# -*- coding: utf-8 -*-
"""
	OneMoar Add-on
"""

from resources.lib.modules.control import addonPath, addonId, getInfinityVersion, joinPath
from resources.lib.windows.textviewer import TextViewerXML


def get(file):
	infinity_path = addonPath(addonId())
	infinity_version = getInfinityVersion()
	helpFile = joinPath(infinity_path, 'resources', 'help', file + '.txt')
	f = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = f.read()
	f.close()
	heading = '[B]Infinity -  v%s - %s[/B]' % (infinity_version, file)
	windows = TextViewerXML('textviewer.xml', infinity_path, heading=heading, text=text)
	windows.run()
	del windows
