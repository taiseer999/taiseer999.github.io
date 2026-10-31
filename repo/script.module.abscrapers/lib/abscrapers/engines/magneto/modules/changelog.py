"""
	Fenomscrapers Module
"""

from abscrapers.engines.magneto.modules.control import addonPath, addonVersion, joinPath
from abscrapers.engines.magneto.modules.textviewer import TextViewerXML


def get():
	magneto_path = addonPath()
	magneto_version = addonVersion()
	changelogfile = joinPath(magneto_path, 'changelog.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]AB Scrapers -  v%s - ChangeLog[/B]' % magneto_version
	windows = TextViewerXML('textviewer.xml', magneto_path, heading=heading, text=text)
	windows.run()
	del windows
