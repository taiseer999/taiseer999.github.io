# -*- coding: utf-8 -*-
"""
	OneMoar Add-on
"""

from json import dumps as jsdumps
from urllib.parse import quote_plus
from resources.lib.modules.control import joinPath, transPath, dialog, notification, addonFanart, setting as getSetting, getProviderColors
from resources.lib.modules import tools
from resources.lib.windows.base import BaseDialog


class SourceResultsXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2000
		self.results = kwargs.get('results')
		self.uncached = kwargs.get('uncached')
		self.total_results = str(len(self.results))
		self.meta = kwargs.get('meta')
		self.defaultbg = addonFanart()
		self.colors = getProviderColors()
		self.useProviderColors = True if self.colors['useproviders'] == True else False
		self.sourceHighlightColor = self.colors['defaultcolor']
		self.realdebridHighlightColor = self.colors['realdebrid']
		self.alldebridHighlightColor = self.colors['alldebrid']
		self.premiumizeHighlightColor = self.colors['premiumize']
		self.easynewsHighlightColor = self.colors['easynews']
		self.plexHighlightColor = self.colors['plexshare']
		self.gdriveHighlightColor = self.colors['gdrive']
		self.filePursuitHighlightColor = self.colors['filepursuit']
		self.highlight_color = getSetting('highlight.color')
		self.usecoloricons = getSetting('sources.highlightmethod') == '1' and getSetting('sources.usecoloricons') == 'true'
		self.make_items()
		self.set_properties()
		self.dnlds_enabled = True if getSetting('downloads') == 'true' and (getSetting('movie.download.path') != '' or getSetting('tv.download.path') != '') else False

	def onInit(self):
		win = self.getControl(self.window_id)
		win.addItems(self.item_list)
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		self.clearProperties()
		return self.selected

	def onAction(self, action):
		try:
			action_id = action.getId() # change to just "action" as the ID is already returned in that.
			if action_id in self.info_actions:
				chosen_source = self.item_list[self.get_position(self.window_id)]
				chosen_source = chosen_source.getProperty('infinity.source_dict')
				syssource = quote_plus(chosen_source)
				self.execute_code('RunPlugin(plugin://plugin.video.infinity/?action=sourceInfo&source=%s)' % syssource)
			if action_id in self.selection_actions:
				focus_id = self.getFocusId()
				if focus_id == 2001:
					position = self.get_position(self.window_id)
					self.load_uncachedTorrents()
					self.setFocusId(self.window_id)
					self.getControl(self.window_id).selectItem(position)
					self.selected = (None, '')
					return
				if focus_id == 2051:
					self.selected = (None, '')
					return self.close()
				chosen_source = self.item_list[self.get_position(self.window_id)]
				source = chosen_source.getProperty('infinity.source')
				if 'UNCACHED' in source:
					debrid = chosen_source.getProperty('infinity.debrid')
					source_dict = chosen_source.getProperty('infinity.source_dict')
					link_type = 'pack' if 'package' in source_dict else 'single'
					sysname = quote_plus(self.meta.get('title'))
					if 'tvshowtitle' in self.meta and 'season' in self.meta and 'episode' in self.meta:
						poster = self.meta.get('season_poster') or self.meta.get('poster')
						sysname += quote_plus(' S%02dE%02d' % (int(self.meta['season']), int(self.meta['episode'])))
					elif 'year' in self.meta: sysname += quote_plus(' (%s)' % self.meta['year'])
					try: new_sysname = quote_plus(chosen_source.getProperty('infinity.name'))
					except: new_sysname = sysname
					self.execute_code('RunPlugin(plugin://plugin.video.infinity/?action=cacheTorrent&caller=%s&type=%s&title=%s&items=%s&url=%s&source=%s&meta=%s)' %
											(debrid, link_type, sysname, quote_plus(jsdumps(self.results)), quote_plus(chosen_source.getProperty('infinity.url')), quote_plus(source_dict), quote_plus(jsdumps(self.meta))))
					self.selected = (None, '')
				else:
					self.selected = ('play_Item', chosen_source)
				return self.close()
			elif action_id in self.context_actions:
				from re import match as re_match
				chosen_source = self.item_list[self.get_position(self.window_id)]
				source_dict = chosen_source.getProperty('infinity.source_dict')
				cm_list = [('[B]Additional Link Info[/B]', 'sourceInfo')]
				if 'cached (pack)' in source_dict or 'unchecked (pack)' in source_dict:
					cm_list += [('[B]Browse Debrid Pack[/B]', 'showDebridPack')]
				source = chosen_source.getProperty('infinity.source')
				if not 'UNCACHED' in source and self.dnlds_enabled:
					cm_list += [('[B]Download[/B]', 'download')]
					cm_list += [('[B]Create Strm File[/B]', 'strmFile')]
				if re_match(r'^CACHED.*TORRENT', source):
					debrid = chosen_source.getProperty('infinity.debrid')
					cm_list += [('[B]Save to %s Cloud[/B]' % debrid, 'saveToCloud')]
				chosen_cm_item = dialog.contextmenu([i[0] for i in cm_list])
				if chosen_cm_item == -1: return
				cm_action = cm_list[chosen_cm_item][1]
				if cm_action == 'sourceInfo':
					self.execute_code('RunPlugin(plugin://plugin.video.infinity/?action=sourceInfo&source=%s)' % quote_plus(source_dict))
				elif cm_action == 'showDebridPack':
					debrid = chosen_source.getProperty('infinity.debrid')
					name = chosen_source.getProperty('infinity.name')
					hash = chosen_source.getProperty('infinity.hash')
					self.execute_code('RunPlugin(plugin://plugin.video.infinity/?action=showDebridPack&caller=%s&name=%s&url=%s&source=%s)' %
									(quote_plus(debrid), quote_plus(name), quote_plus(chosen_source.getProperty('infinity.url')), quote_plus(hash)))
					self.selected = (None, '')
				elif cm_action == 'download':
					sysname = quote_plus(self.meta.get('title'))
					poster = self.meta.get('poster', '')
					if 'tvshowtitle' in self.meta and 'season' in self.meta and 'episode' in self.meta:
						sysname = quote_plus(self.meta.get('tvshowtitle'))
						poster = self.meta.get('season_poster') or self.meta.get('poster')
						sysname += quote_plus(' S%02dE%02d' % (int(self.meta['season']), int(self.meta['episode'])))
					elif 'year' in self.meta: sysname += quote_plus(' (%s)' % self.meta['year'])
					try: new_sysname = quote_plus(chosen_source.getProperty('infinity.name'))
					except: new_sysname = sysname
					self.execute_code('RunPlugin(plugin://plugin.video.infinity/?action=download&name=%s&image=%s&source=%s&caller=sources&title=%s)' %
										(new_sysname, quote_plus(poster), quote_plus(source_dict), sysname))
					self.selected = (None, '')
				elif cm_action == 'strmFile':
					sysname = quote_plus(self.meta.get('title'))
					poster = self.meta.get('poster', '')
					if 'tvshowtitle' in self.meta and 'season' in self.meta and 'episode' in self.meta:
						sysname = quote_plus(self.meta.get('tvshowtitle'))
						poster = self.meta.get('season_poster') or self.meta.get('poster')
						sysname += quote_plus(' S%02dE%02d' % (int(self.meta['season']), int(self.meta['episode'])))
					elif 'year' in self.meta: sysname += quote_plus(' (%s)' % self.meta['year'])
					try: new_sysname = quote_plus(chosen_source.getProperty('infinity.name'))
					except: new_sysname = sysname
					self.execute_code('RunPlugin(plugin://plugin.video.infinity/?action=createStrm&name=%s&image=%s&source=%s&caller=sources&title=%s)' %
										(new_sysname, quote_plus(poster), quote_plus(source_dict), sysname))
					self.selected = (None, '')
				elif cm_action == 'saveToCloud':
					magnet = chosen_source.getProperty('infinity.url')
					if debrid == 'AD':
						from resources.lib.debrid import alldebrid
						transfer_function = alldebrid.AllDebrid
						debrid_icon = alldebrid.ad_icon
					elif debrid == 'PM':
						from resources.lib.debrid import premiumize
						transfer_function = premiumize.Premiumize
						debrid_icon = premiumize.pm_icon
					elif debrid == 'RD':
						from resources.lib.debrid import realdebrid
						transfer_function = realdebrid.RealDebrid
						debrid_icon = realdebrid.rd_icon
					elif debrid == 'OC':
						from resources.lib.debrid import offcloud
						transfer_function = offcloud.Offcloud
						debrid_icon = offcloud.oc_icon
					elif debrid == 'ED':
						from resources.lib.debrid import easydebrid
						transfer_function = easydebrid.EasyDebrid
						debrid_icon = easydebrid.ed_icon
					elif debrid == 'TB':
						from resources.lib.debrid import torbox
						transfer_function = torbox.TorBox
						debrid_icon = torbox.tb_icon
					result = transfer_function().create_transfer(magnet)
					if result: notification(message='Sending MAGNET to the %s cloud' % debrid, icon=debrid_icon)
			elif action in self.closing_actions:
				self.selected = (None, '')
				self.close()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def get_quality_iconPath(self, quality):
		try:
			return joinPath(transPath('special://home/addons/plugin.video.infinity/resources/skins/Default/media/resolution'), '%s.png' % quality)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def get_provider1_iconPath(self, provider):
		try:
			if provider == 'premiumize.me': provider = 'premiumize'
			return joinPath(transPath('special://home/addons/plugin.video.infinity/resources/skins/Default/media/resolution1'), '%s.png' % provider)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def get_quality1_iconPath(self, quality):
		try:
			return joinPath(transPath('special://home/addons/plugin.video.infinity/resources/skins/Default/media/resolution1'), '%s.png' % quality)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def debrid_abv(self, debrid):
		try:
			d_dict = {'AllDebrid': 'AD', 'EasyDebrid': 'ED', 'Offcloud': 'OC', 'Premiumize.me': 'PM', 'Real-Debrid': 'RD', 'TorBox': 'TB'}
			d = d_dict[debrid]
		except:
			d = ''
		return d

	def make_items(self):
		def builder():
			for count, item in enumerate(self.results, 1):
				try:
					listitem = self.make_listitem()
					quality = item.get('quality', 'SD')
#					quality_icon = self.get_quality_iconPath(quality.lower())
					quality_icon = (
						self.get_quality1_iconPath(quality.lower())
						if self.usecoloricons else
						self.get_quality_iconPath(quality.lower())
					)
					extra_info = item.get('info')
					extra_info = extra_info.replace('/', '')
					extra_info = extra_info.split('GB ', 1)[-1]
					if self.useProviderColors == True:
						if item.get('debrid') is not None and item.get('debrid') !='':
							if str(item.get('debrid')).lower() == 'real-debrid':
								providerHighlight = self.realdebridHighlightColor
							elif str(item.get('debrid')).lower() == 'alldebrid':
								providerHighlight = self.alldebridHighlightColor
							elif str(item.get('debrid')).lower()== 'premiumize.me':
								providerHighlight = self.premiumizeHighlightColor
							else:
								providerHighlight = self.sourceHighlightColor
						else:
							if item.get('provider') == 'easynews':
								providerHighlight = self.easynewsHighlightColor
							elif str(item.get('provider')).lower() == 'plexshare':
								providerHighlight = self.plexHighlightColor
							elif str(item.get('provider')).lower() == 'gdrive':
								providerHighlight = self.gdriveHighlightColor
							elif str(item.get('provider')).lower() == 'filepursuit':
								providerHighlight = self.filePursuitHighlightColor
							else:
								providerHighlight = self.sourceHighlightColor
					else:
						providerHighlight = self.sourceHighlightColor
					size_label = str(round(item.get('size', ''), 2)) + ' GB' if item.get('size') else 'NA'
					listitem.setProperty('infinity.source_dict', jsdumps([item]))
					listitem.setProperty('infinity.debrid', self.debrid_abv(item.get('debrid')))
					listitem.setProperty('infinity.provider', item.get('provider').upper())
					listitem.setProperty('infinity.plexsource', item.get('plexsource', '').upper())
					listitem.setProperty('infinity.source', item.get('source').upper())
					listitem.setProperty('infinity.seeders', str(item.get('seeders')))
					listitem.setProperty('infinity.hash', item.get('hash', 'N/A'))
					listitem.setProperty('infinity.name', item.get('name'))
					listitem.setProperty('infinity.quality', quality.upper())
					listitem.setProperty('infinity.quality_icon', quality_icon)
					listitem.setProperty('infinity.url', item.get('url'))
					listitem.setProperty('infinity.extra_info', extra_info)
					listitem.setProperty('infinity.size_label', size_label)
					listitem.setProperty('infinity.count', '%02d. ' % count)
					listitem.setProperty('infinity.providerhighlight', str(providerHighlight))
					yield listitem
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
		try:
			self.item_list = list(builder())
			self.total_results = str(len(self.item_list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def set_properties(self):
		if self.meta is None: return
		try:
			if 'tvshowtitle' in self.meta and 'season' in self.meta and 'episode' in self.meta: 
				self.setProperty('infinity.seas_ep', 'S%02dE%02d' % (int(self.meta['season']), int(self.meta['episode'])))
				self.setProperty('infinity.season', str(self.meta.get('season', '')))
				self.setProperty('infinity.episode', str(self.meta.get('episode', '')))
			if self.meta.get('title'): self.setProperty('infinity.title', self.meta.get('title'))
			if self.meta.get('season_poster'): self.setProperty('infinity.poster', self.meta.get('season_poster', ''))
			else: self.setProperty('infinity.poster', self.meta.get('poster', ''))
			self.setProperty('infinity.fanart', self.meta.get('fanart', '') if getSetting('sources.select.fanartBG') == 'true' else self.defaultbg)
			self.setProperty('infinity.clearlogo', self.meta.get('clearlogo', ''))
			self.setProperty('infinity.plot', self.meta.get('plot', ''))
			self.setProperty('infinity.rating', '%.1f' % self.meta.get('rating', 'NA'))
			if self.meta.get('premiered'):
				pdate = str(self.meta.get('premiered'))[:4]
				self.setProperty('infinity.year', str(pdate))
			new_date = tools.convert_time(stringTime=str(self.meta.get('premiered', '')), formatInput='%Y-%m-%d', formatOutput='%m-%d-%Y', zoneFrom='utc', zoneTo='utc')
			self.setProperty('infinity.premiered', new_date)
			if self.meta.get('mpaa'): self.setProperty('infinity.mpaa', self.meta.get('mpaa'))
			else: self.setProperty('infinity.mpaa', 'NA ')
			if self.meta.get('duration'):
				duration = int(self.meta.get('duration')) / 60
				self.setProperty('infinity.duration', str(int(duration)))
			else: self.setProperty('infinity.duration', 'NA ')
			self.setProperty('infinity.uncached_results', 'true' if self.uncached else 'false')
			self.setProperty('infinity.total_results', self.total_results)
			self.setProperty('infinity.highlight.color', self.highlight_color)
			self.setProperty('infinity.sourcebackbutton', 'true' if getSetting('sources.backbutton') == 'true' else 'false')
			self.setProperty('infinity.usecoloricons', 'true' if self.usecoloricons else 'false')
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def load_uncachedTorrents(self):
		try:
			from resources.lib.windows.uncached_results import UncachedResultsXML
			from resources.lib.modules.control import addonPath, addonId
			window = UncachedResultsXML('uncached_results.xml', addonPath(addonId()), uncached=self.uncached, meta=self.meta, colors=self.colors)
			window.run()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
