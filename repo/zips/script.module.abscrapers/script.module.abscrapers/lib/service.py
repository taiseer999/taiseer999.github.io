# -*- coding: utf-8 -*-
"""
	AB Scrapers - background service
	* creates the profile settings file
	* keeps the shared settings cache fresh
	* loads Magneto's unwanted.json into the window property its filters read
	* upgrades the shared undesirables database
"""

import traceback
import xbmc
import xbmcvfs
from abscrapers.common import ADDON_ID, dataPath, settingsFile, setSetting, setting, make_settings_dict, clear_cache, log, homeWindow

LOGINFO = xbmc.LOGINFO


class SettingsMonitor(xbmc.Monitor):
	def onSettingsChanged(self):
		clear_cache()
		xbmc.sleep(50)
		make_settings_dict()
		try:
			from abscrapers.engines.gears.modules import control
			if homeWindow.getProperty('abscrapers.debug.reversed') != setting('debug.reversed'):
				homeWindow.setProperty('abscrapers.debug.reversed', setting('debug.reversed'))
				control.execute('RunPlugin(plugin://%s/?action=tools_clearLogFile)' % ADDON_ID)
		except Exception: pass


def check_settings_file():
	try:
		if not xbmcvfs.exists(dataPath): xbmcvfs.mkdirs(dataPath)
		if not xbmcvfs.exists(settingsFile): setSetting('module.provider', 'AB Scrapers')
		clear_cache()
		make_settings_dict()
		homeWindow.setProperty('abscrapers.debug.reversed', setting('debug.reversed'))
	except Exception: traceback.print_exc()


def load_unwanted():
	try:
		path = 'special://home/addons/%s/resources/unwanted.json' % ADDON_ID
		f = xbmcvfs.File(path)
		homeWindow.setProperty('abscrapers_unwanted', f.read())
		f.close()
	except Exception: traceback.print_exc()


def check_undesirables():
	try:
		from abscrapers.engines.gears.modules import undesirables
		if undesirables.Undesirables().check_database(): undesirables.add_new_default_keywords()
	except Exception: traceback.print_exc()


def check_version():
	try:
		from abscrapers.engines.gears.modules import control
		if control.isVersionUpdate():
			control.clean_settings()
			log('Settings file cleaned after update', LOGINFO)
	except Exception: traceback.print_exc()


def main():
	log('Service Started', LOGINFO)
	monitor = SettingsMonitor()
	check_settings_file()
	load_unwanted()
	check_undesirables()
	check_version()
	monitor.waitForAbort()
	log('Service Stopped', LOGINFO)


main()
