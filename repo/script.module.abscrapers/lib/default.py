# -*- coding: utf-8 -*-
"""
	AB Scrapers - plugin router (settings actions + AIOStreams player menu)
"""

import sys
from urllib.parse import parse_qsl, urlencode
from abscrapers.common import ADDON_ID, setSetting, getProviderDefaults
from abscrapers.strings import ls
from abscrapers.engines.gears.modules import control

params = dict(parse_qsl(sys.argv[2].replace('?', ''))) if len(sys.argv) > 2 else {}
action = params.get('action')
name = params.get('name')


def main_menu():
	import xbmcgui, xbmcplugin, xbmcaddon
	handle = int(sys.argv[1])
	icon = xbmcaddon.Addon(ADDON_ID).getAddonInfo('icon')
	items = (
		('Settings', {'action': 'Settings'}, icon, False),
		('Provider health check', {'action': 'healthCheck'}, 'DefaultAddonService.png', False),
		('AIOStreams: test movies', {'action': 'Movies'}, 'DefaultMovies.png', True),
		('AIOStreams: test series', {'action': 'Series'}, 'DefaultTVShows.png', True),
		('AIOStreams README', {'action': 'ShowReadme'}, 'DefaultIconInfo.png', False),
		('Install TMDbHelper player (AIOStreams)', {'action': 'InstallJson'}, 'DefaultAddon.png', False),
		('Changelog', {'action': 'ShowChangelog'}, 'DefaultPlaylist.png', False),
	)
	for label, query, art, folder in items:
		li = xbmcgui.ListItem(ls(label), offscreen=True)
		li.setArt({'icon': art, 'thumb': art, 'poster': art})
		xbmcplugin.addDirectoryItem(handle, 'plugin://%s/?%s' % (ADDON_ID, urlencode(query)), li, folder)
	xbmcplugin.endOfDirectory(handle)


def toggle(names, value_for):
	for n in names: setSetting('provider.' + n, value_for(n))
	control.notification(message=ls('Done'))


if action is None:
	main_menu()

elif action in ('Settings', 'abscrapersSettings'):
	control.openSettings(None, ADDON_ID)

elif action == 'ShowChangelog':
	from abscrapers.engines.gears.modules import changelog
	changelog.get()

elif action == 'ShowHelp':
	from abscrapers.engines.gears.modules import help
	help.get(name)

elif action == 'Defaults':
	import abscrapers
	try:
		defaults = getProviderDefaults()
		toggle(abscrapers.provider_names(), lambda n: defaults.get('provider.' + n) or 'false')
	except Exception: control.notification(message=ls('Error'))

elif action in ('toggleAll', 'toggleAllTorrent'):
	import abscrapers
	toggle(abscrapers.provider_names(), lambda n: params.get('setting', 'true'))

elif action == 'toggleAllPackTorrent':
	import abscrapers
	packs = set(abscrapers.pack_sources())
	toggle(abscrapers.provider_names(), lambda n: 'true' if n in packs else 'false')

elif action == 'cleanSettings':
	control.clean_settings()

elif action in ('undesirablesSelect', 'undesirablesInput', 'undesirablesUserRemove', 'undesirablesUserRemoveAll'):
	from abscrapers.engines.gears.modules import undesirables
	getattr(undesirables, action)()

elif action == 'tools_clearLogFile':
	from abscrapers.engines.gears.modules import log_utils
	cleared = log_utils.clear_logFile()
	if cleared == 'canceled': pass
	elif cleared: control.notification(message=ls('Done'))
	else: control.notification(message=ls('Error'))

elif action == 'tools_viewLogFile':
	from abscrapers.engines.gears.modules import log_utils
	log_utils.view_LogFile(name or 'AB Scrapers')

elif action == 'tools_uploadLogFile':
	from abscrapers.engines.gears.modules import log_utils
	log_utils.upload_LogFile()

elif action == 'healthCheck':
	from abscrapers.health import run
	run()

elif action == 'telegram_pair':
	from abscrapers.engines.gears.modules.telegram_auth import pair_with_telegram
	pair_with_telegram()

elif action == 'telegram_status':
	from abscrapers.engines.gears.modules.telegram_auth import show_status
	show_status()

elif action == 'TestProwlarrConnection':
	from abscrapers.engines.coco.modules.prowlarr import Prowlarr
	Prowlarr().test()

elif action == 'ProwlarrIndexers':
	from abscrapers.engines.coco.modules.prowlarr import Prowlarr
	Prowlarr().get_indexers()

elif action == 'mediafusionAuth':
	from abscrapers.engines.coco.modules.mediafusion import MediaFusion
	MediaFusion().auth()

elif action == 'mediafusionReset':
	from abscrapers.engines.coco.modules.mediafusion import MediaFusion
	MediaFusion().clear()

# ---- AIOStreams player (from Magneto) ----
elif action == 'MediaPlay':
	from abscrapers.engines.magneto import player
	player.MagnetoPlayer().source_select(params)

elif action in ('Movies', 'Series', 'Episodes'):
	from abscrapers.engines.magneto.player import navigator
	cls = {'Episodes': navigator.Episodes, 'Series': navigator.Series}.get(action, navigator.Movies)()
	cls.run(params)

elif action == 'ShowReadme':
	from abscrapers.engines.gears.modules import help
	help.get('aioStreams')

elif action == 'InstallJson':
	from abscrapers.engines.magneto.player import settings
	settings.install_json()

elif action == 'ColorPick':
	from abscrapers.engines.magneto.player import settings
	settings.color_pick(params)
