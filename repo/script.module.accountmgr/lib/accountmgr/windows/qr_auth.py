# -*- coding: utf-8 -*-
"""
	Account Manager - QR Authorization Window
"""

import os
import xbmcgui
import xbmcvfs
import xbmcaddon
from accountmgr.windows.base import BaseDialog

addon_id = 'script.module.accountmgr'


def _addon_path():
	return xbmcvfs.translatePath(xbmcaddon.Addon(addon_id).getAddonInfo('path'))


def _data_path():
	profile = xbmcvfs.translatePath(xbmcaddon.Addon(addon_id).getAddonInfo('profile'))
	qr_dir = os.path.join(profile, 'qrcodes')
	if not os.path.exists(qr_dir):
		os.makedirs(qr_dir)
	return qr_dir


def generate_qr(content, name='auth'):
	import segno
	imagefile = os.path.join(_data_path(), '%s.png' % name)
	try:
		if os.path.exists(imagefile): os.remove(imagefile)
	except:
		pass
	qr = segno.make(content)
	qr.save(imagefile, scale=10, border=2)
	return imagefile


class QRAuthXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		super(QRAuthXML, self).__init__(self, args)
		self.heading = kwargs.get('heading', '')
		self.url = kwargs.get('url', '')
		self.pin = kwargs.get('pin', '')
		self.qr_image = kwargs.get('qr_image', '')
		self.canceled = False
		self.cancel_button = 3001
		self.progress_control = 3002

	def onInit(self):
		self.set_properties()
		try: self.setFocusId(self.cancel_button)
		except: pass

	def set_properties(self):
		self.setProperty('qrauth.heading', self.heading)
		self.setProperty('qrauth.url', self.url)
		self.setProperty('qrauth.pin', self.pin)
		self.setProperty('qrauth.qr', self.qr_image)

	def set_percent(self, percent):
		try: self.getControlProgress(self.progress_control).setPercent(percent)
		except: pass

	def onClick(self, controlID):
		if controlID == self.cancel_button:
			self.canceled = True
			self.close()

	def onAction(self, action):
		try: action_id = action.getId()
		except: action_id = action
		if action_id in self.closing_actions:
			self.canceled = True
			self.close()


class QRProgressDialog:
	"""
	Drop-in replacement for xbmcgui.DialogProgress used by the auth flows.
	Shows a QR authorization window (qr_auth.xml). If anything goes wrong
	(e.g. QR generation fails), it silently falls back to the standard
	Kodi progress dialog so authorization always remains possible.
	"""

	def __init__(self):
		self.window = None
		self.fallback = None

	def create(self, heading, url, pin, qr_url=None):
		try:
			qr_image = generate_qr(qr_url or url, name='auth_qr')
			self.window = QRAuthXML('qr_auth.xml', _addon_path(), 'Default', '1080i',
									heading=heading, url=url, pin=str(pin), qr_image=qr_image)
			self.window.show()
		except:
			from accountmgr.modules import log_utils
			log_utils.error()
			from accountmgr.modules import control
			self.fallback = xbmcgui.DialogProgress()
			self.fallback.create(heading, control.progress_line % (control.lang(32513) % url, control.lang(32514) % pin, ''))

	def update(self, percent, message=''):
		try:
			if self.fallback: self.fallback.update(int(percent))
			elif self.window: self.window.set_percent(max(0, min(100, int(percent))))
		except:
			pass

	def iscanceled(self):
		if self.fallback: return self.fallback.iscanceled()
		if self.window: return self.window.canceled
		return False

	def close(self):
		try:
			if self.fallback:
				self.fallback.close()
				self.fallback = None
			elif self.window:
				self.window.close()
				del self.window
				self.window = None
		except:
			pass
