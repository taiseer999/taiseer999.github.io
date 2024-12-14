# -*- coding: utf-8 -*-
"""
	OneMoar Add-on
"""

from threading import Thread
from resources.lib.modules.control import addonFanart, jsonrpc, setting as getSetting, homeWindow, sleep
from resources.lib.windows.base import BaseDialog

class SourceProgress(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.closed = False
		self.monitor = None
		self.meta = kwargs.get('meta')
		self.imdb = self.meta.get('imdb')
		self.tvdb = self.meta.get('tvdb')
		self.year = self.meta.get('year')
		self.season = self.meta.get('season')
		self.episode = self.meta.get('episode')
		self.icon_only = 'true' if getSetting('progress.dialog') == '3' else 'false'
		self.use_fanart = getSetting('sources.dialog.fanartBG') == 'true'
		self.source_color = getSetting('sources.highlight.color')
		self.set_controls()

	def _monitor(self):
		while homeWindow.getProperty('infinity.source_progress_is_alive') == 'true': sleep(200)
		try: self.doClose()
		except: pass

	def create(self):
		self.monitor = True
		Thread(target=self.run).start()

	def run(self):
		homeWindow.setProperty('infinity.source_progress_is_alive', 'true')
		if self.monitor: Thread(target=self._monitor).start()
		self.doModal()
		self.clearProperties()
		homeWindow.clearProperty('infinity.source_progress_is_alive')

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.doClose()

	def doClose(self):
		self.closed = True
		self.close()
		del self

	def iscanceled(self):
		return self.closed

	def set_controls(self):
		if self.meta:
			if self.meta.get('fanart') and self.use_fanart: self.setProperty('infinity.fanart', self.meta.get('fanart'))
			else: self.setProperty('infinity.fanart', addonFanart())
			if self.meta.get('clearlogo'): self.setProperty('infinity.clearlogo', self.meta.get('clearlogo'))
			if self.meta.get('title'): self.setProperty('infinity.title', self.meta.get('title'))
			if 'tvshowtitle' in self.meta: self.setProperty('infinity.tvtitle', self.meta.get('tvshowtitle'))
			if self.meta.get('plot'): self.setProperty('infinity.plot', self.meta.get('plot', ''))
		else:
			self.setProperty('infinity.fanart', addonFanart())
		self.setProperty('infinity.icononly', self.icon_only)
		self.setProperty('infinity.sources_highlight_color', self.source_color)

	def update(self, percent=0, content=''):
		try:
			self.getControl(2001).setText(content)
			self.getControl(5000).setPercent(percent)
		except: pass
