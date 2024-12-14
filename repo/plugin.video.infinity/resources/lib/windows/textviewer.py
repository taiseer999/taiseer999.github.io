# -*- coding: utf-8 -*-

from resources.lib.windows.base import BaseDialog


class TextViewerXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2060
		self.heading = kwargs.get('heading', 'Infinity')
		self.text = kwargs.get('text')
		self.background = 'FF302F2F'
		self.titlebar = 'FF37B6FF'
		self.titletext = 'FFE68B00'
		self.textcolor = 'FFF5F5F5'

	def onInit(self):
		self.set_properties()
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		self.clearProperties()

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.close()

	def set_properties(self):
		self.setProperty('infinity.text', self.text)
		self.setProperty('infinity.heading', self.heading)
		self.setProperty('infinity.background', self.background)
		self.setProperty('infinity.titlebar', self.titlebar)
		self.setProperty('infinity.titletext', self.titletext)
		self.setProperty('infinity.textcolor', self.textcolor)
