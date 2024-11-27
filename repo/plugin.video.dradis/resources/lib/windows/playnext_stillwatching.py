"""
	Venom Add-on
"""

from datetime import datetime, timedelta
import xbmc
from resources.lib.modules.control import getSourceHighlightColor, setting as getSetting, playerWindow
from resources.lib.modules import tools
from resources.lib.windows.base import BaseDialog

monitor = xbmc.Monitor()


class StillWatchingXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 3011
		self.meta = kwargs.get('meta')
		self.playing_file = self.getPlayingFile()
		self.duration = self.getTotalTime() - self.getTime()
		self.default_action = int(getSetting('stillwatching.default.action'))
		self.closed = False

	def onInit(self):
		self.set_properties()
		self.background_tasks()

	def run(self):
		self.doModal()
		self.clearProperties()

	def doClose(self):
		self.closed = True
		self.close()

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.doClose()

	def onClick(self, control_id):
		if control_id == 3011: # Play Now, skip to end of current
			xbmc.executebuiltin('PlayerControl(BigSkipForward)')
			self.doClose()
		if control_id == 3012: # Stop playback
			xbmc.executebuiltin('PlayerControl(Playlist.Clear)')
			xbmc.executebuiltin('PlayerControl(Stop)')
			playerWindow.clearProperty('dradis.preResolved_nextUrl')
			self.doClose()
		if control_id == 3013: # Cancel/Close xml dialog
			self.doClose()

	def getTotalTime(self):
		if self.isPlaying():
			return xbmc.Player().getTotalTime() # total time of playing video
		else:
			return 0

	def getTime(self):
		if self.isPlaying():
			return xbmc.Player().getTime() # current position of playing video
		else:
			return 0

	def isPlaying(self):
		return xbmc.Player().isPlaying()

	def getPlayingFile(self):
		return xbmc.Player().getPlayingFile()

	def calculate_percent(self):
		return ((int(self.getTotalTime()) - int(self.getTime())) / float(self.duration)) * 100

	def background_tasks(self):
		try:
			try: progress_bar = self.getControlProgress(3014)
			except: progress_bar = None

			while (
				int(self.getTotalTime()) - int(self.getTime()) > 2
				and not self.closed
				and self.playing_file == self.getPlayingFile()
				and not monitor.abortRequested()
			):
				xbmc.sleep(500)
				if progress_bar is not None:
					progress_bar.setPercent(self.calculate_percent())

			if self.closed: return
			if (self.default_action == 1 and self.playing_file == self.getPlayingFile()):
				xbmc.executebuiltin('PlayerControl(Playlist.Clear)')
				xbmc.executebuiltin('PlayerControl(Stop)')

			if (self.default_action == 2 and self.playing_file == self.getPlayingFile()):
				xbmc.Player().pause()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		self.doClose()

	def set_properties(self):
		if self.meta is None: return
		try:
			self.setProperty('dradis.highlight.color', getSourceHighlightColor())
			self.setProperty('dradis.tvshowtitle', self.meta.get('tvshowtitle'))
			self.setProperty('dradis.title', self.meta.get('title'))
			self.setProperty('dradis.year', str(self.meta.get('year', '')))
			new_date = tools.convert_time(stringTime=str(self.meta.get('premiered', '')), formatInput='%Y-%m-%d', formatOutput='%m-%d-%Y', zoneFrom='utc', zoneTo='utc')
			self.setProperty('dradis.premiered', new_date)
			self.setProperty('dradis.season', str(self.meta.get('season', '')))
			self.setProperty('dradis.episode', str(self.meta.get('episode', '')))
			self.setProperty('dradis.rating', str(self.meta.get('rating', '')))
			self.setProperty('dradis.landscape', self.meta.get('landscape', ''))
			self.setProperty('dradis.fanart', self.meta.get('fanart', ''))
			self.setProperty('dradis.thumb', self.meta.get('thumb', ''))
			next_duration = int(self.meta.get('duration')) if self.meta.get('duration') else ''
			self.setProperty('dradis.duration', str(int(next_duration)))
			endtime = (datetime.now() + timedelta(seconds=next_duration)).strftime('%I:%M %p').lstrip('0') if next_duration else ''
			self.setProperty('dradis.endtime', endtime)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
