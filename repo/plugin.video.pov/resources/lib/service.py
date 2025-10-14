import time
from threading import Thread
from modules import kodi_utils, settings

logger, ls, path_exists, translate_path = kodi_utils.logger, kodi_utils.local_string, kodi_utils.path_exists, kodi_utils.translate_path
monitor, is_playing, get_visibility = kodi_utils.monitor, kodi_utils.player.isPlaying, kodi_utils.get_visibility
get_property, set_property, clear_property = kodi_utils.get_property, kodi_utils.set_property, kodi_utils.clear_property
get_setting, set_setting, make_settings_dict = kodi_utils.get_setting, kodi_utils.set_setting, kodi_utils.make_settings_dict

def initializeDatabases():
	from modules.cache import check_databases
	logger('POV', 'InitializeDatabases Service Starting')
	check_databases()
	return logger('POV', 'InitializeDatabases Service Finished')

def checkSettingsFile():
	logger('POV', 'CheckSettingsFile Service Starting')
	clear_property('pov_settings')
	profile_dir = kodi_utils.get_addoninfo('profile')
	settings_xml = profile_dir + 'settings.xml'
	if not path_exists(profile_dir):
		kodi_utils.make_directorys(profile_dir)
	if not path_exists(settings_xml):
		kodi_utils.addon().setSetting('kodi_menu_cache', 'true')
		kodi_utils.sleep(500)
	make_settings_dict()
	set_property('pov_kodi_menu_cache', get_setting('kodi_menu_cache'))
	set_property('pov_rli_fix', get_setting('rli_fix'))
	return logger('POV', 'CheckSettingsFile Service Finished')

def databaseMaintenance():
	from modules.cache import clean_databases
	current_time = int(time.time())
	next_clean = current_time + 259200 # 3 days
	due_clean = int(get_setting('database.maintenance.due', '0'))
	if current_time < due_clean: return
	logger('POV', 'Database Maintenance Service Starting')
	clean_databases(current_time, database_check=False, silent=True)
	set_setting('database.maintenance.due', str(next_clean))
	return logger('POV', 'Database Maintenance Service Finished')

def viewsSetWindowProperties():
	logger('POV', 'ViewsSetWindowProperties Service Starting')
	kodi_utils.set_view_properties()
	return logger('POV', 'ViewsSetWindowProperties Service Finished')

def reuseLanguageInvokerCheck():
	import xml.etree.ElementTree as ET
	logger('POV', 'ReuseLanguageInvokerCheck Service Starting')
	addon_xml = translate_path('special://home/addons/plugin.video.pov/addon.xml')
	tree = ET.parse(addon_xml)
	root = tree.getroot()
	current_addon_setting = get_setting('reuse_language_invoker', 'true')
	text = '%s[CR]%s' % ('[B]Reuse Language Invoker[/B] SETTING/XML mismatch', 'POV will reload your profile to refresh the addon.xml')
	item, refresh = next(root.iter('reuselanguageinvoker'), None), False
	if item is None: kodi_utils.notification(text.split('[CR]')[0])
	if not item is None and not item.text == current_addon_setting:
		item.text = current_addon_setting
		tree.write(addon_xml)
		refresh = True
	if refresh and kodi_utils.confirm_dialog(text=text): kodi_utils.execute_builtin('LoadProfile(%s)' % kodi_utils.get_infolabel('system.profilename'))
	return logger('POV', 'ReuseLanguageInvokerCheck Service Finished')

def autoRun():
	logger('POV', 'AutoRun Service Starting')
	if settings.auto_start_pov(): kodi_utils.execute_builtin('RunAddon(plugin.video.pov)')
	return logger('POV', 'AutoRun Service Finished')

def clearSubs():
	logger('POV', 'Clear Subtitles Service Starting')
	sub_formats = ('.srt', '.ssa', '.smi', '.sub', '.idx')
	subtitle_path = 'special://temp/'
	for i in kodi_utils.list_dirs(subtitle_path)[1]:
		if i.startswith('POVSubs_') or i.endswith(sub_formats):
			kodi_utils.delete_file(subtitle_path + i)
	return logger('POV', 'Clear Subtitles Service Finished')

def traktMonitor():
	from caches.trakt_cache import clear_trakt_list_contents_data
	from indexers.trakt_api import trakt_sync_activities
	from indexers.tmdb_api import tmdb_clean_watchlist
	logger('POV', 'TraktMonitor Service Starting')
	trakt_service_string = 'TraktMonitor Service Update %s - %s'
	update_string = 'Next Update in %s minutes...'
	if not kodi_utils.get_property('pov_traktmonitor_first_run') == 'true':
		for i in ('public', 'user_lists'): clear_trakt_list_contents_data(i)
		kodi_utils.set_property('pov_traktmonitor_first_run', 'true')
	while not monitor.abortRequested():
		while is_playing() or get_visibility('Container().isUpdating') or get_property('pov_pause_services') == 'true': monitor.waitForAbort(10)
		if not kodi_utils.get_property('pov_traktmonitor_first_run') == 'true': monitor.waitForAbort(5)
		value, interval = settings.trakt_sync_interval()
		next_update_string = update_string % value
		status = trakt_sync_activities()
		if status == 'success':
			logger('POV', trakt_service_string % ('POV TraktMonitor - Success', 'Trakt Update Performed'))
			if settings.trakt_sync_refresh_widgets():
				kodi_utils.widget_refresh()
				logger('POV', trakt_service_string % ('POV TraktMonitor - Widgets Refresh', 'Setting Activated. Widget Refresh Performed'))
			else: logger('POV', trakt_service_string % ('POV TraktMonitor - Widgets Refresh', 'Setting Disabled. Skipping Widget Refresh'))
		elif status == 'no account':
			logger('POV', trakt_service_string % ('POV TraktMonitor - Aborted. No Trakt Account Active', next_update_string))
		elif status == 'failed':
			logger('POV', trakt_service_string % ('POV TraktMonitor - Failed. Error from Trakt', next_update_string))
		else:# 'not needed'
			logger('POV', trakt_service_string % ('POV TraktMonitor - Success. No Changes Needed', next_update_string))
		if get_setting('tmdb.token') and get_setting('tmdblist.watchlist_sync') == 'true':
			status = tmdb_clean_watchlist(silent=True)
			if status: logger('POV', 'TMDB Lists Service Update - Success. %s' % status)
		monitor.waitForAbort(interval)
	return logger('POV', 'TraktMonitor Service Finished')

def premAccntNotification():
	logger('POV', 'Debrid Account Expiry Notification Service Starting')
	if get_setting('ad.account_id') != '':
		if limit := int(get_setting('ad.expires', '7')):
			from debrids.alldebrid_api import AllDebridAPI
			days_remaining = AllDebridAPI().days_remaining()
			if not days_remaining is None and days_remaining <= limit:
				kodi_utils.notification('AllDebrid expires in %s days' % days_remaining)
	if get_setting('pm.account_id') != '':
		if limit := int(get_setting('pm.expires', '7')):
			from debrids.premiumize_api import PremiumizeAPI
			days_remaining = PremiumizeAPI().days_remaining()
			if not days_remaining is None and days_remaining <= limit:
				kodi_utils.notification('Premiumize.me expires in %s days' % days_remaining)
	if get_setting('rd.username') != '':
		if limit := int(get_setting('rd.expires', '7')):
			from debrids.real_debrid_api import RealDebridAPI
			days_remaining = RealDebridAPI().days_remaining()
			if not days_remaining is None and days_remaining <= limit:
				kodi_utils.notification('Real-Debrid expires in %s days' % days_remaining)
	if get_setting('ed.account_id') != '':
		if limit := int(get_setting('ed.expires', '7')):
			from debrids.easydebrid_api import EasyDebridAPI
			days_remaining = EasyDebridAPI().days_remaining()
			if not days_remaining is None and days_remaining <= limit:
				kodi_utils.notification('EasyDebrid expires in %s days' % days_remaining)
	if get_setting('tb.account_id') != '':
		if limit := int(get_setting('tb.expires', '7')):
			from debrids.torbox_api import TorBoxAPI
			days_remaining = TorBoxAPI().days_remaining()
			if not days_remaining is None and days_remaining <= limit:
				kodi_utils.notification('TorBox expires in %s days' % days_remaining)
	return logger('POV', 'Debrid Account Expiry Notification Service Finished')

def checkUndesirablesDatabase():
	from fenom.undesirables import Undesirables, add_new_default_keywords
	logger('POV', 'CheckUndesirablesDatabase Service Starting')
	old_database = Undesirables().check_database()
	if old_database: add_new_default_keywords()
	return logger('POV', 'CheckUndesirablesDatabase Service Finished')

class POVMonitor(kodi_utils.xbmc_monitor):
	def __enter__(self):
		self.threads = (Thread(target=traktMonitor), Thread(target=premAccntNotification))
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		for i in self.threads: i.join()

	def startUpServices(self):
		try: initializeDatabases()
		except: pass
		try: checkSettingsFile()
		except: pass
		try: databaseMaintenance()
		except: pass
		try: viewsSetWindowProperties()
		except: pass
		try: reuseLanguageInvokerCheck()
		except: pass
		for i in self.threads: i.start()
		try: autoRun()
		except: pass
		try: clearSubs()
		except: pass
		try: checkUndesirablesDatabase()
		except: pass

	def onScreensaverActivated(self):
		set_property('pov_pause_services', 'true')

	def onScreensaverDeactivated(self):
		clear_property('pov_pause_services')

	def onSettingsChanged(self):
		clear_property('pov_settings')
		kodi_utils.sleep(50)
		make_settings_dict()
		set_property('pov_kodi_menu_cache', get_setting('kodi_menu_cache'))
		set_property('pov_rli_fix', get_setting('rli_fix'))

	def onNotification(self, sender, method, data):
		if method == 'System.OnSleep': set_property('pov_pause_services', 'true')
		elif method == 'System.OnWake': clear_property('pov_pause_services')


logger('POV', 'Main Monitor Service Starting')
logger('POV', 'Settings Monitor Service Starting')

with POVMonitor() as pov:
	pov.startUpServices()
	pov.waitForAbort()

logger('POV', 'Settings Monitor Service Finished')
logger('POV', 'Main Monitor Service Finished')

