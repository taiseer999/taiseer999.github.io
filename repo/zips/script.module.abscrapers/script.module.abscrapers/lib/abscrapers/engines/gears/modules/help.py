"""
	Fenomscrapers Module
"""

from abscrapers.engines.gears.modules.control import addonPath, addonVersion, joinPath
from abscrapers.engines.gears.modules.textviewer import TextViewerXML


def get(file):
	gearsscrapers_path = addonPath()
	gearsscrapers_version = addonVersion()
	helpFile = joinPath(gearsscrapers_path, 'resources', 'help', file + '.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]AB Scrapers -  v%s - %s[/B]' % (gearsscrapers_version, file)
	windows = TextViewerXML('textviewer.xml', gearsscrapers_path, heading=heading, text=text)
	windows.run()
	del windows
