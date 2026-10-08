# -*- coding: utf-8 -*-
from acctmgr.modules.control import addonPath, addonVersion, joinPath
from acctmgr.windows.textviewer import TextViewerXML
from acctmgr.modules.i18n import is_arabic
import os


def _localized(path):
	if is_arabic():
		root, ext = os.path.splitext(path)
		ar_path = root + '_ar' + ext
		if os.path.exists(ar_path):
			return ar_path
	return path

def get(file):
	acctmgr_path = addonPath()
	acctmgr_version = addonVersion()
	helpFile = joinPath(acctmgr_path, 'lib', 'acctmgr', 'help', file + '.txt')
	r = open(_localized(helpFile), 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]AM Lite -  v%s - %s[/B]' % (acctmgr_version, file)
	windows = TextViewerXML('textviewer.xml', acctmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_login():
	acctmgr_path = addonPath()
	acctmgr_version = addonVersion()
	helpFile = joinPath(acctmgr_path, 'lib', 'acctmgr', 'help', 'login.txt')
	r = open(_localized(helpFile), 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]AM Lite -  v%s - Torbox & OffCloud Auth Help[/B]' % (acctmgr_version)
	windows = TextViewerXML('textviewer.xml', acctmgr_path, heading=heading, text=text)
	windows.run()
	del windows
	
def get_restore():
	acctmgr_path = addonPath()
	acctmgr_version = addonVersion()
	helpFile = joinPath(acctmgr_path, 'lib', 'acctmgr', 'help', 'restore.txt')
	r = open(_localized(helpFile), 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]AM Lite -  v%s - Restore to Default[/B]' % (acctmgr_version)
	windows = TextViewerXML('textviewer.xml', acctmgr_path, heading=heading, text=text)
	windows.run()
	del windows
