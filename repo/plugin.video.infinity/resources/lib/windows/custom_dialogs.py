# -*- coding: utf-8 -*-
"""
	OneMoar Add-on (Yay for new custom dialogs. thanks Peter for the help)
"""

from resources.lib.modules import colors
from resources.lib.modules.control import addonIcon, lang as getLS, setting as getSetting
from resources.lib.windows.base import BaseDialog

class OK(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.ok_label = kwargs.get('ok_label')
		self.text = kwargs.get('text')
		self.heading = kwargs.get('heading', getLS(40414))
		self.icon = kwargs.get('icon', addonIcon())
		self.customBackgroundColor = getSetting('dialogs.customcolor')
		self.customButtonColor = getSetting('dialogs.button.color')
		self.customTitleColor = getSetting('dialogs.titlebar.color')
		self.useCustomTitleColor = getSetting('dialogs.usecolortitle') == 'true'
		self.highlight_color = getSetting('sources.highlight.color')
		self.mode = getSetting('dialogs.lightordarkmode')
		self.lightcolor = 'FFF5F5F5'
		self.darkcolor = 'FF302F2F'
		self.set_properties()

	def run(self):
		self.doModal()

	def onClick(self, controlID):
		self.close()

	def onAction(self, action):
		if action in self.closing_actions: self.close()

	def set_properties(self):
		self.setProperty('ok_label', self.ok_label)
		self.setProperty('text', self.text)
		self.setProperty('heading', self.heading)
		background = {'0': self.darkcolor, '1': self.lightcolor, '2': self.customBackgroundColor}[self.mode]
		titlebar = self.customTitleColor if self.useCustomTitleColor else background
		spinner = self.highlight_color if background == titlebar else titlebar
		if self.mode not in ('0', '1'): self.mode = '0' if colors.isDarkColor(background) else '1'
		text = self.lightcolor if self.mode == '0' else self.darkcolor
		buttontext = self.darkcolor if self.mode == '0' else self.lightcolor
		buttontextns = self.lightcolor if self.mode == '0' else self.darkcolor
		buttonnf = '33F5F5F5' if self.mode == '0' else '33302F2F'
		if self.mode == '0' and background == titlebar: titletext = self.lightcolor
		else: titletext = self.darkcolor

		self.setProperty('infinity.backgroundColor', background)
		self.setProperty('infinity.titleBarColor', titlebar)
		self.setProperty('infinity.titleTextColor', titletext)
		self.setProperty('infinity.buttonColor', self.customButtonColor)
		self.setProperty('infinity.buttonColorNF', buttonnf)
		self.setProperty('infinity.buttonTextColor', buttontext)
		self.setProperty('infinity.buttonTextColorNS', buttontextns)
		self.setProperty('infinity.spinnerColor', spinner)
		self.setProperty('infinity.textColor', text)

class Confirm(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.selected = None
		self.default_control = kwargs.get('default_control')
		self.ok_label = kwargs.get('ok_label')
		self.cancel_label = kwargs.get('cancel_label')
		self.text = kwargs.get('text')
		self.heading = kwargs.get('heading', getLS(40414))
		self.icon = kwargs.get('icon', addonIcon())
		self.customBackgroundColor = getSetting('dialogs.customcolor')
		self.customButtonColor = getSetting('dialogs.button.color')
		self.customTitleColor =getSetting('dialogs.titlebar.color')
		self.useCustomTitleColor = getSetting('dialogs.usecolortitle') == 'true'
		self.highlight_color = getSetting('sources.highlight.color')
		self.mode = getSetting('dialogs.lightordarkmode')
		self.lightcolor = 'FFF5F5F5'
		self.darkcolor = 'FF302F2F'
		self.set_properties()

	def onInit(self):
		self.setFocusId(self.default_control)

	def run(self):
		self.doModal()
		return self.selected

	def onClick(self, controlID):
		self.selected = {10: True, 11: False}[controlID]
		self.close()

	def onAction(self, action):
		if action in self.closing_actions: self.close()

	def set_properties(self):
		self.setProperty('ok_label', self.ok_label)
		self.setProperty('cancel_label', self.cancel_label)
		self.setProperty('text', self.text)
		self.setProperty('heading', self.heading)
		background = {'0': self.darkcolor, '1': self.lightcolor, '2': self.customBackgroundColor}[self.mode]
		titlebar = self.customTitleColor if self.useCustomTitleColor else background
		spinner = self.highlight_color if background == titlebar else titlebar
		if self.mode not in ('0', '1'): self.mode = '0' if colors.isDarkColor(background) else '1'
		text = self.lightcolor if self.mode == '0' else self.darkcolor
		buttontext = self.darkcolor if self.mode == '0' else self.lightcolor
		buttontextns = self.lightcolor if self.mode == '0' else self.darkcolor
		buttonnf = '33F5F5F5' if self.mode == '0' else '33302F2F'
		if self.mode == '0' and background == titlebar: titletext = self.lightcolor
		else: titletext = self.darkcolor

		self.setProperty('infinity.backgroundColor', background)
		self.setProperty('infinity.titleBarColor', titlebar)
		self.setProperty('infinity.titleTextColor', titletext)
		self.setProperty('infinity.buttonColor', self.customButtonColor)
		self.setProperty('infinity.buttonColorNF', buttonnf)
		self.setProperty('infinity.buttonTextColor', buttontext)
		self.setProperty('infinity.buttonTextColorNS', buttontextns)
		self.setProperty('infinity.spinnerColor', spinner)
		self.setProperty('infinity.textColor', text)

class Progress(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.closed = False
		self.heading = kwargs.get('heading', getLS(40414))
		self.icon = kwargs.get('icon') or ''
		self.customBackgroundColor = getSetting('dialogs.customcolor')
		self.customButtonColor = getSetting('dialogs.button.color')
		self.customTitleColor = getSetting('dialogs.titlebar.color')
		self.useCustomTitleColor = getSetting('dialogs.usecolortitle') == 'true'
		self.highlight_color = getSetting('sources.highlight.color')
		self.mode = getSetting('dialogs.lightordarkmode')
		self.lightcolor = 'FFF5F5F5'
		self.darkcolor = 'FF302F2F'
		self.set_properties()

	def run(self):
		self.doModal()
		self.clearProperties()

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.doClose()

	def doClose(self):
		self.closed = True
		self.close()
		del self

	def iscanceled(self):
		return self.closed

	def set_properties(self):
		self.setProperty('infinity.heading', self.heading)
		self.setProperty('infinity.icon', self.icon)
		background = {'0': self.darkcolor, '1': self.lightcolor, '2': self.customBackgroundColor}[self.mode]
		titlebar = self.customTitleColor if self.useCustomTitleColor else background
		spinner = self.highlight_color if background == titlebar else titlebar
		if self.mode not in ('0', '1'): self.mode = '0' if colors.isDarkColor(background) else '1'
		text = self.lightcolor if self.mode == '0' else self.darkcolor
		buttontext = self.darkcolor if self.mode == '0' else self.lightcolor
		buttontextns = self.lightcolor if self.mode == '0' else self.darkcolor
		buttonnf = '33F5F5F5' if self.mode == '0' else '33302F2F'
		if self.mode == '0' and background == titlebar: titletext = self.lightcolor
		else: titletext = self.darkcolor

		self.setProperty('infinity.backgroundColor', background)
		self.setProperty('infinity.titleBarColor', titlebar)
		self.setProperty('infinity.titleTextColor', titletext)
		self.setProperty('infinity.buttonColor', self.customButtonColor)
		self.setProperty('infinity.buttonColorNF', buttonnf)
		self.setProperty('infinity.buttonTextColor', buttontext)
		self.setProperty('infinity.buttonTextColorNS', buttontextns)
		self.setProperty('infinity.spinnerColor', spinner)
		self.setProperty('infinity.textColor', text)

	def update(self, percent=0, content=''):
		try:
			self.getControl(2001).setText(content)
			self.getControl(5000).setPercent(percent)
		except: pass
