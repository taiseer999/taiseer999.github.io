"""
	Fenomscrapers Module
"""

from json import dumps as jsdumps, loads as jsloads
import os.path
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import xml.etree.ElementTree as ET

log = xbmc.log
def addon(id='script.module.abscrapers'):
	return xbmcaddon.Addon(id)
condVisibility = xbmc.getCondVisibility
infoLabel = xbmc.getInfoLabel
execute = xbmc.executebuiltin
jsonrpc = xbmc.executeJSONRPC
monitor_class = xbmc.Monitor

dialog = xbmcgui.Dialog
progressDialog = xbmcgui.DialogProgress
progress_line = '%s[CR]%s[CR]%s'

deleteFile = xbmcvfs.delete
existsPath = xbmcvfs.exists
listDir = xbmcvfs.listdir
openFile = xbmcvfs.File
makeFile = xbmcvfs.mkdir
makeDirs = xbmcvfs.mkdirs
renameFile = xbmcvfs.rename
transPath = xbmcvfs.translatePath
joinPath = os.path.join

SETTINGS_PATH = transPath(joinPath(addon().getAddonInfo('path'), 'resources', 'settings.xml'))
dataPath = transPath(addon().getAddonInfo('profile'))
cacheFile = joinPath(dataPath, 'cache.db')
undesirablescacheFile = joinPath(dataPath, 'undesirables.db')
settingsFile = joinPath(dataPath, 'settings.xml')

def addonInfo(info):
	return addon().getAddonInfo(info)

def getLangString(language_id):
	return addon().getLocalizedString(language_id)

def homeWindow():
	return xbmcgui.Window(10000)

def getKodiVersion(full=False):
	if full: return xbmc.getInfoLabel("System.BuildVersion")
	else: return int(xbmc.getInfoLabel("System.BuildVersion")[:2])

def setting(id, fallback=None):
	try: settings_dict = jsloads(homeWindow().getProperty('magneto_settings'))
	except: settings_dict = make_settings_dict()
	if settings_dict is None: settings_dict = settings_fallback(id)
	value = settings_dict.get(id, '')
	if fallback is None: return value
	if value == '': return fallback
	return value

def settings_fallback(id):
	return {id: addon().getSetting(id)}

def setSetting(id, value):
	return addon().setSetting(id, value)

def make_settings_dict(): # service runs upon a setting change
	try:
		with openFile(settingsFile) as xml_file: root = ET.fromstring(xml_file.read())
		settings_dict = {}
		for item in root:
			dict_item = {}
			setting_id = item.get('id')
			setting_value = item.text
			if setting_value is None: setting_value = ''
			dict_item = {setting_id: setting_value}
			settings_dict.update(dict_item)
		homeWindow().setProperty('magneto_settings', jsdumps(settings_dict))
		return settings_dict
	except:
		return None

def refresh_debugReversed(): # called from service "onSettingsChanged" to clear magneto.log if setting to reverse has been changed
	if homeWindow().getProperty('magneto.debug.reversed') != setting('debug.reversed'):
		homeWindow().setProperty('magneto.debug.reversed', setting('debug.reversed'))
		execute('RunPlugin(plugin://script.module.abscrapers/?action=tools_clearLogFile)')

def lang(language_id):
	return getLangString(language_id)

def sleep(time): # Modified `sleep` command that honors a user exit request
	monitor = monitor_class()
	while time > 0 and not monitor.abortRequested():
		xbmc.sleep(min(100, time))
		time = time - 100

def isVersionUpdate():
	addon_folder = transPath('special://profile/addon_data/script.module.abscrapers/')
	versionFile = joinPath(dataPath, 'installed.version')
	curVersion = addon('script.module.abscrapers').getAddonInfo('version')
	try:
		if not xbmcvfs.exists(addon_folder):
			LOGINFO = 1 # (LOGNOTICE(2) deprecated in 19, use LOGINFO(1))
			xbmc.log('AB Scrapers Addon Data Path Does not Exist. Creating Folder....', LOGINFO)
			xbmcvfs.mkdirs(addon_folder)
		with open(versionFile, 'a+') as fh:
			fh.seek(0)
			try: oldVersion = fh.read().strip()
			except: oldVersion = '0'
			if oldVersion == curVersion: return False
			fh.seek(0)
			fh.truncate(0)
			fh.write(curVersion)
		checkPackages()
		return True
	except:
		from abscrapers.engines.magneto.modules import log_utils
		log_utils.error()
		return False

def checkPackages():
	packages = transPath('special://home/addons/packages/')
	files = listDir(packages)[1]
	for item in files:
		if '.magneto' in item and item.endswith('zip'):
			try: deleteFile(packages + item)
			except: pass

def clean_settings():
	addon_ids, addon_name = addonInfo('id'), addonInfo('name')
	default_xml = 'special://home/addons/%s/resources/settings.xml' % addon_ids
	profile_xml = 'special://profile/addon_data/%s/settings.xml' % addon_ids
	try:
		removed_settings = []
		removed_append = removed_settings.append
		with openFile(default_xml) as xml_file: root = ET.fromstring(xml_file.read())
		active_settings = [item.get('id') for item in root.iter('setting') if item.get('id')]
		with openFile(profile_xml) as xml_file: root = ET.fromstring(xml_file.read())
		for item in root.iter('setting'):
			if item.get('id') in active_settings: continue
			removed_append(item)
		for item in removed_settings: root.remove(item)
		with openFile(profile_xml, 'w') as xml_file: xml_file.write(ET.tostring(root))
		notification(title=addon_name, message='%s Obsolete Settings Entries Removed' % len(removed_settings))
	except:
		from abscrapers.engines.magneto.modules import log_utils
		log_utils.error()
		notification(title=addon_name, message='Error Cleaning Settings.xml. Old settings.xml files Restored.')

def addonId():
	return addonInfo('id')

def addonName():
	return addonInfo('name')

def addonVersion():
	return addonInfo('version')

def addonIcon():
	return addonInfo('icon')

def addonPath():
	return transPath(addonInfo('path'))

def addonEnabled(addon_id):
	return condVisibility('System.AddonIsEnabled(%s)' % addon_id)

def addonInstalled(addon_id):
	return condVisibility('System.HasAddon(%s)' % addon_id)

def openSettings(query=None, id=addonInfo('id')):
	try:
		hide()
		execute('Addon.OpenSettings(%s)' % id)
		if not query: return
		c, f = query.split('.')
		execute('SetFocus(%i)' % (int(c) - 100))
		execute('SetFocus(%i)' % (int(f) - 80))
	except:
		return

def getProviderDefaults():
	provider_defaults = {}
	try:
		with openFile(SETTINGS_PATH) as xml_file: root = ET.fromstring(xml_file.read())
		for item in root.findall(r'./category/setting'):
			setting_id, setting_default = item.get('id', ''), item.get('default', '')
			if not setting_id.startswith('provider.') or setting_default is None: continue
			provider_defaults[setting_id] = setting_default or 'false'
	except: pass
	return provider_defaults

def hide():
	execute('Dialog.Close(busydialog)')
	execute('Dialog.Close(busydialognocancel)')

def yesnoDialog(line, heading=addonInfo('name'), nolabel='', yeslabel=''):
	return dialog().yesno(heading, line, nolabel, yeslabel)

def selectDialog(list, heading=addonInfo('name')):
	return dialog().select(heading, list)

def multiselectDialog(list, preselect=[], heading=addonInfo('name')):
	return dialog().multiselect(heading, list, preselect=preselect)

def notification(title=None, message=None, icon=None, time=3000, sound=False):
	if title == 'default' or title is None: title = addonName()
	if isinstance(title, int): heading = lang(title)
	else: heading = str(title)
	if isinstance(message, int): body = lang(message)
	else: body = str(message)
	if icon in (None, '', 'default'): icon = joinPath(addonInfo('path'), 'resources', 'abscrapers_small.png')
	elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
	elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
	elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
	dialog().notification(heading, body, icon, time, sound=sound)

# --- AB Scrapers: every engine reads/writes the single unified settings store ---
from abscrapers.common import setting, setSetting, make_settings_dict, settings_fallback, getProviderDefaults  # noqa: E402,F401
