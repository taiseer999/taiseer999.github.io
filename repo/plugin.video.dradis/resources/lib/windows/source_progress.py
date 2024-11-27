from threading import Thread
from resources.lib.modules.control import homeWindow, sleep
from resources.lib.windows.base import BaseDialog


class SourceProgressXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.heading = kwargs.get('heading')
		self.meta = kwargs.get('meta')
		self.monitor = None

	def onInit(self):
		self.set_properties()
		homeWindow.setProperty('dradis.source_progress_is_alive', 'true')
		if self.monitor: Thread(target=self._monitor).start()

	def onAction(self, action):
		if action in self.closing_actions:
			self.close()

	def run(self):
		self.doModal()
		self.clearProperties()
		homeWindow.clearProperty('dradis.source_progress_is_alive')

	def create(self):
		self.monitor = True
		Thread(target=self.run).start()

	def set_properties(self):
		if self.meta is None: return
		self.setProperty('dradis.heading', self.heading)
		self.setProperty('dradis.fanart', self.meta.get('fanart', ''))
		self.setProperty('dradis.clearlogo', self.meta.get('clearlogo', ''))

	def update(self, percent='', content=''):
		try: self.getControl(2000).setText(content)
		except: pass

	def _monitor(self):
		while homeWindow.getProperty('dradis.source_progress_is_alive') == 'true': sleep(200)
		try: self.close()
		except: pass
