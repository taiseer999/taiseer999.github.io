"""
	Venom Add-on
"""

from json import dumps as jsdumps
from urllib.parse import quote_plus
import xbmc
from resources.lib.modules.control import dialog, getHighlightColor, yesnoDialog, sleep, condVisibility, setting as getSetting
from resources.lib.windows.base import BaseDialog

monitor = xbmc.Monitor()


class TraktHiddenManagerXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2040
		self.results = kwargs.get('results')
		self.total_results = str(len(self.results))
		self.chosen_hide = []
		self.chosen_unhide = []
		self.hide_watched = getSetting('trakt.HiddenManager.hideWatched') == 'true'
		self.make_items()
		self.set_properties()
		self.hasVideo = False

	def onInit(self):
		win = self.getControl(self.window_id)
		win.addItems(self.item_list)
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		self.clearProperties()
		return (self.chosen_hide, self.chosen_unhide)

	# def onClick(self, controlID):
		# from resources.lib.modules import log_utils
		# log_utils.log('controlID=%s' % controlID)

	def onAction(self, action):
		try:
			if action in self.selection_actions:
				focus_id = self.getFocusId()
				if focus_id == 2040: # listItems
					chosen_listitem = self.item_list[self.get_position(self.window_id)]
					tvdb = chosen_listitem.getProperty('dradis.tvdb')
					if chosen_listitem.getProperty('dradis.isHidden') == 'true':
						if chosen_listitem.getProperty('dradis.isSelected') == 'true':
							chosen_listitem.setProperty('dradis.isSelected', '')
							self.chosen_unhide.append(tvdb)
						else:
							chosen_listitem.setProperty('dradis.isSelected', 'true')
							if tvdb in self.chosen_unhide: self.chosen_unhide.remove(tvdb)
					else:
						if chosen_listitem.getProperty('dradis.isSelected') == '':
							chosen_listitem.setProperty('dradis.isSelected', 'true')
							self.chosen_hide.append(tvdb)
						else:
							chosen_listitem.setProperty('dradis.isSelected', '')
							if tvdb in self.chosen_hide: self.chosen_hide.remove(tvdb)
				elif focus_id == 2041: # OK Button
					self.close()
				elif focus_id == 2042: # Cancel Button
					self.chosen_hide, self.chosen_unhide = None, None
					self.close()
				elif focus_id == 2045: # Stop Trailer Playback Button
					self.execute_code('PlayerControl(Stop)')
					sleep(500)
					self.setFocusId(self.window_id)

			elif action in self.context_actions:
				cm = []
				chosen_listitem = self.item_list[self.get_position(self.window_id)]
				source_trailer = chosen_listitem.getProperty('dradis.trailer')
				if not source_trailer:
					from resources.lib.modules import trailer
					source_trailer = trailer.Trailer().worker('show', chosen_listitem.getProperty('dradis.tvshowtitle'), chosen_listitem.getProperty('dradis.year'), None, chosen_listitem.getProperty('dradis.imdb'))

				if source_trailer: cm += [('[B]Play Trailer[/B]', 'playTrailer')]
				cm += [('[B]Browse Series[/B]', 'browseSeries')]
				chosen_cm_item = dialog.contextmenu([i[0] for i in cm])
				if chosen_cm_item == -1: return
				cm_action = cm[chosen_cm_item][1]

				if cm_action == 'playTrailer':
					self.execute_code('PlayMedia(%s, 1)' % source_trailer)
					total_sleep = 0
					while True:
						sleep(500)
						total_sleep += 500
						self.hasVideo = condVisibility('Player.HasVideo')
						if self.hasVideo or total_sleep >= 10000: break
					if self.hasVideo:
						self.setFocusId(2045)
						while (condVisibility('Player.HasVideo') and not monitor.abortRequested()):
							self.setProgressBar()
							sleep(1000)
						self.hasVideo = False
						self.progressBarReset()
						self.setFocusId(self.window_id)
					else: self.setFocusId(self.window_id)

				if cm_action == 'browseSeries':
					systvshowtitle = quote_plus(chosen_listitem.getProperty('dradis.tvshowtitle'))
					year = chosen_listitem.getProperty('dradis.year')
					imdb = chosen_listitem.getProperty('dradis.imdb')
					tmdb = chosen_listitem.getProperty('dradis.tmdb')
					tvdb = chosen_listitem.getProperty('dradis.tvdb')
					from resources.lib.modules.control import lang
					if not yesnoDialog(lang(32182), '', ''): return
					self.chosen_hide, self.chosen_unhide = None, None
					self.close()
					sysart = quote_plus(chosen_listitem.getProperty('dradis.art'))
					self.execute_code('ActivateWindow(Videos,plugin://plugin.video.dradis/?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&art=%s,return)' % (
							systvshowtitle, year, imdb, tmdb, tvdb, sysart))

			elif action in self.closing_actions:
				self.chosen_hide, self.chosen_unhide = None, None
				if self.hasVideo: self.execute_code('PlayerControl(Stop)')
				else: self.close()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def setProgressBar(self):
		try: progress_bar = self.getControlProgress(2046)
		except: progress_bar = None
		if progress_bar is not None:
			progress_bar.setPercent(self.calculate_percent())

	def calculate_percent(self):
		return (xbmc.Player().getTime() / float(xbmc.Player().getTotalTime())) * 100

	def progressBarReset(self):
		try: progress_bar = self.getControlProgress(2046)
		except: progress_bar = None
		if progress_bar is not None:
			progress_bar.setPercent(0)

	def make_items(self):
		def filerWatched():
			if self.hide_watched:
				self.results = [i for i in self.results if i.get('watched_count').get('watched') != i.get('watched_count').get('total')]
		def builder():
			for count, item in enumerate(self.results, 1):
				try:
					listitem = self.make_listitem()
					listitem.setProperty('dradis.tvshowtitle', item.get('tvshowtitle'))
					listitem.setProperty('dradis.year', str(item.get('year')))
					listitem.setProperty('dradis.isHidden', str(item.get('isHidden')))
					listitem.setProperty('dradis.isSelected', str(item.get('isHidden')))
					listitem.setProperty('dradis.imdb', item.get('imdb'))
					listitem.setProperty('dradis.tmdb', str(item.get('tmdb')))
					listitem.setProperty('dradis.tvdb', str(item.get('tvdb')))
					listitem.setProperty('dradis.status', item.get('status'))
					try: listitem.setProperty('dradis.watched_count', '(watched ' + str(item.get('watched_count').get('watched')) + ' of ' + str(item.get('watched_count').get('total')) + ')')
					except: pass
					listitem.setProperty('dradis.rating', str(round(float(item.get('rating', '0')), 1)))
					listitem.setProperty('dradis.trailer', item.get('trailer'))
					listitem.setProperty('dradis.studio', item.get('studio'))
					listitem.setProperty('dradis.genre', item.get('genre', ''))
					# listitem.setProperty('dradis.duration', str(item.get('duration'))) # not used
					listitem.setProperty('dradis.mpaa', item.get('mpaa') or 'NA')
					listitem.setProperty('dradis.plot', item.get('plot'))
					poster = item.get('season_poster', '') or item.get('poster', '') or item.get('poster2', '') or item.get('poster3', '')
					fanart = item.get('fanart', '') or item.get('fanart2', '') or item.get('fanart3', '')
					clearlogo = item.get('clearlogo', '')
					clearart = item.get('clearart', '')
					art = {'poster': poster, 'tvshow.poster': poster, 'fanart': fanart, 'icon': item.get('icon') or poster, 'thumb': item.get('thumb', ''), 'banner': item.get('banner2', ''), 'clearlogo': clearlogo,
								'tvshow.clearlogo': clearlogo, 'clearart': clearart, 'tvshow.clearart': clearart, 'landscape': item.get('landscape', '')}
					listitem.setProperty('dradis.poster', poster)
					listitem.setProperty('dradis.clearlogo', clearlogo)
					listitem.setProperty('dradis.art', jsdumps(art))
					listitem.setProperty('dradis.count', '%02d.)' % count)
					yield listitem
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
		try:
			filerWatched()
			self.item_list = list(builder())
			self.total_results = str(len(self.item_list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def set_properties(self):
		try:
			self.setProperty('dradis.total_results', self.total_results)
			self.setProperty('dradis.highlight.color', getHighlightColor())
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
