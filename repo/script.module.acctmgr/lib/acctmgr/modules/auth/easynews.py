# -*- coding: utf-8 -*-
import os
import xbmcgui
from acctmgr.modules import control

joinPath = os.path.join
en_icon = joinPath(control.iconsPath(), 'easynews.png')

class Easynews:
	def auth(self):
		username = control.dialog.input('Enter Easynews Username:')
		if not username:
			control.notification(message="Easynews authorization cancelled!", icon=en_icon)
			return False
		else:
                        control.setSetting('easynews.username', username)

		password = control.dialog.input('Enter Easynews Password:', option=xbmcgui.ALPHANUM_HIDE_INPUT)
		if not password:
			control.notification(message="Easynews authorization cancelled!", icon=en_icon)
			return False
		else:
                        control.setSetting('easynews.password', password)
		return True
