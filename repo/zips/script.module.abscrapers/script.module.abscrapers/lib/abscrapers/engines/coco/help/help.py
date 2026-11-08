# -*- coding: utf-8 -*-
"""
	Fenomscrapers Module
"""

from abscrapers.engines.coco.modules.control import addonPath, addonVersion, joinPath
from abscrapers.engines.coco.windows.textviewer import TextViewerXML


def get(file):
	cocoscrapers_path = addonPath()
	cocoscrapers_version = addonVersion()
	helpFile = joinPath(cocoscrapers_path, 'resources', 'help', file + '.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]AB Scrapers -  v%s - %s[/B]' % (cocoscrapers_version, file)
	windows = TextViewerXML('textviewer.xml', cocoscrapers_path, heading=heading, text=text)
	windows.run()
	del windows