"""
	Venom Add-on
"""

from resources.lib.modules.control import addonPath, addonId, getDradisVersion, joinPath
from resources.lib.windows.textviewer import TextViewerXML


def get(file):
	dradis_path = addonPath(addonId())
	dradis_version = getDradisVersion()
	helpFile = joinPath(dradis_path, 'resources', 'help', file + '.txt')
	f = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = f.read()
	f.close()
	heading = '[B]Dradis -  v%s - %s[/B]' % (dradis_version, file)
	windows = TextViewerXML('textviewer.xml', dradis_path, heading=heading, text=text)
	windows.run()
	del windows
