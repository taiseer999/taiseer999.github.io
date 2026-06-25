from entry import logger, POVMonitor

if __name__ == '__main__':
	# ----- AM Lite Trakt startup sync patch BEGIN -----
	def wait_for_am_trakt(timeout=120, max_age=180):
		import time
		import xbmc
		import xbmcaddon

		waited = 0

		while waited < timeout:
			try:
				am = xbmcaddon.Addon('script.module.acctmgr')
				ready = am.getSetting('am_trakt_ready')
				last_prepare = am.getSetting('am_last_prepare')

				if ready == 'true' and last_prepare:
					age = int(time.time()) - int(last_prepare)
					if 0 <= age <= max_age:
						return True
			except Exception:
				pass

			xbmc.sleep(1000)
			waited += 1

		return False

	wait_for_am_trakt()
	# ----- AM Lite Trakt startup sync patch END -----
	logger('POV', 'Main Monitor Service Starting (%s)' % POVMonitor.ver())
	logger('POV', 'Settings Monitor Service Starting')

	with POVMonitor() as pov:
		pov.startUpServices()
		pov.waitForAbort()

	logger('POV', 'Settings Monitor Service Finished')
	logger('POV', 'Main Monitor Service Finished')

