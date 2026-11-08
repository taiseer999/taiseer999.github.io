# -*- coding: utf-8 -*-
"""
	AB Scrapers - shared settings store.
	All three engines (coco / gears / magneto) import setting()/setSetting() from here,
	so one settings.xml drives everything.
"""

import os
from json import dumps as jsdumps, loads as jsloads
import xml.etree.ElementTree as ET
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'script.module.abscrapers'
ADDON_NAME = 'AB Scrapers'

_PROP = 'abscrapers_settings'
_PROP_MTIME = 'abscrapers_settings_mtime'

homeWindow = xbmcgui.Window(10000)
translatePath = xbmcvfs.translatePath
dataPath = translatePath('special://profile/addon_data/%s/' % ADDON_ID)
settingsFile = os.path.join(dataPath, 'settings.xml')
SETTINGS_PATH = translatePath('special://home/addons/%s/resources/settings.xml' % ADDON_ID)


def addon():
	return xbmcaddon.Addon(ADDON_ID)


def _mtime():
	try: return str(os.path.getmtime(settingsFile))
	except Exception: return ''


_ADDON_DEFAULTS = None

def addon_defaults():
	"""{setting_id: default} from the add-on's own resources/settings.xml."""
	global _ADDON_DEFAULTS
	if _ADDON_DEFAULTS is None:
		defaults = {}
		try:
			for item in ET.parse(SETTINGS_PATH).getroot().iter('setting'):
				setting_id = item.get('id')
				if setting_id and item.get('default') is not None: defaults[setting_id] = item.get('default')
		except Exception: pass
		_ADDON_DEFAULTS = defaults
	return _ADDON_DEFAULTS


def make_settings_dict():
	try:
		root = ET.parse(settingsFile).getroot()
		defaults = addon_defaults()
		settings_dict = {}
		for item in root.iter('setting'):
			setting_id = item.get('id')
			if not setting_id: continue
			# Kodi marks values the user never changed with default="true" and itself loads
			# the add-on's CURRENT default for them - do the same, so a changed default in a
			# new version (e.g. a provider switched off) reaches existing installs too.
			if item.get('default') == 'true' and setting_id in defaults:
				settings_dict[setting_id] = defaults[setting_id]
			else:
				settings_dict[setting_id] = item.text or ''
		homeWindow.setProperty(_PROP, jsdumps(settings_dict))
		homeWindow.setProperty(_PROP_MTIME, _mtime())
		return settings_dict
	except Exception:
		return None


def settings_fallback(id):
	try: return {id: addon().getSetting(id)}
	except Exception: return {id: ''}


def setting(id, fallback=None):
	# mtime-aware cache (from gears): settings.xml edited on disk or by another
	# process is picked up on the next call without a Kodi restart.
	settings_dict = None
	try:
		current = _mtime()
		if current and current != homeWindow.getProperty(_PROP_MTIME): settings_dict = make_settings_dict()
		else: settings_dict = jsloads(homeWindow.getProperty(_PROP))
	except Exception:
		settings_dict = make_settings_dict()
	if not settings_dict or id not in settings_dict:
		settings_dict = settings_fallback(id) # not in the profile yet -> addon default
	value = settings_dict.get(id, '')
	if fallback is None: return value
	if value == '': return fallback
	return value


def setSetting(id, value):
	addon().setSetting(id, value)
	try: # keep the in-window cache coherent immediately
		cached = jsloads(homeWindow.getProperty(_PROP))
		cached[id] = value
		homeWindow.setProperty(_PROP, jsdumps(cached))
	except Exception:
		homeWindow.clearProperty(_PROP_MTIME)


def clear_cache():
	homeWindow.clearProperty(_PROP)
	homeWindow.clearProperty(_PROP_MTIME)


def getProviderDefaults():
	provider_defaults = {}
	try:
		root = ET.parse(SETTINGS_PATH).getroot()
		for item in root.iter('setting'):
			setting_id = item.get('id', '')
			if setting_id.startswith('provider.'):
				provider_defaults[setting_id] = item.get('default') or 'false'
	except Exception: pass
	return provider_defaults


def log(msg, level=xbmc.LOGINFO):
	xbmc.log('[ %s ] %s' % (ADDON_ID, msg), level)


def debug_enabled():
	return setting('debug.enabled') == 'true'


def trace_enabled():
	"""Always-on provider trace in kodi.log (Maintenance > Log provider results), default ON."""
	return setting('log.providers') != 'false'


def caller_id():
	"""Which add-on is using us (plugin://plugin.video.umbrella/ -> plugin.video.umbrella)."""
	try:
		import sys
		arg0 = sys.argv[0] if sys.argv else ''
		if arg0.startswith('plugin://'): return arg0.split('/')[2]
		import xbmcaddon
		return xbmcaddon.Addon().getAddonInfo('id')
	except Exception:
		return '?'


def trace(provider, engine, method, run):
	"""Run one provider call, log result count / time / error, return its result unchanged."""
	import time
	if not trace_enabled(): return run()
	start = time.monotonic()
	try:
		res = run()
	except Exception as e:
		log('%s[%s].%s FAILED after %.1fs: %s: %s' % (provider, engine, method, time.monotonic() - start, type(e).__name__, e), xbmc.LOGWARNING)
		raise
	try: n = len(res)
	except Exception: n = -1
	log('%s[%s].%s -> %d results in %.1fs' % (provider, engine, method, n, time.monotonic() - start))
	return res
