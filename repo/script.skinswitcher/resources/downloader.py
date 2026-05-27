import xbmcaddon
import xbmcgui
import urllib.request
import urllib.parse
import urllib.error
import sys
import time

ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
COLOR1 = 'white'
COLOR2 = 'white'

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'

def download(url, dest, dp = None):
	if not dp:
		dp = xbmcgui.DialogProgress()
		dp.create(ADDON_ID,"Downloading Content")
	dp.update(0)
	start_time = time.time()
	try:
		req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
		with urllib.request.urlopen(req) as response:
			filesize = int(response.headers.get('Content-Length', 0))
			blocksize = 8192
			numblocks = 0
			with open(dest, 'wb') as f:
				while True:
					block = response.read(blocksize)
					if not block:
						break
					f.write(block)
					numblocks += 1
					_pbhook(numblocks, blocksize, filesize, dp, start_time)
					if dp.iscanceled():
						dp.close()
						import sys; sys.exit()
	except Exception as e:
		import xbmc
		xbmc.log('SkinSwitcher download error: %s' % str(e), xbmc.LOGINFO)

def _pbhook(numblocks, blocksize, filesize, dp, start_time):
	try: 
		percent = min(numblocks * blocksize * 100 / filesize, 100) 
		currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
		kbps_speed = numblocks * blocksize / (time.time() - start_time) 
		if kbps_speed > 0 and not percent == 100: 
			eta = (filesize - numblocks * blocksize) / kbps_speed 
		else: 
			eta = 0
		kbps_speed = kbps_speed / 1024 
		type_speed = 'KB'
		if kbps_speed >= 1024:
			kbps_speed = kbps_speed / 1024 
			type_speed = 'MB'
		total = float(filesize) / (1024 * 1024) 
		mbs = '[COLOR %s][B]Size:[/B] [COLOR %s]%.02f[/COLOR] MB of [COLOR %s]%.02f[/COLOR] MB[/COLOR]' % (COLOR2, COLOR1, currently_downloaded, COLOR1, total) 
		e = '[COLOR %s][B]Speed:[/B] [COLOR %s]%.02f [/COLOR]%s/s ' % (COLOR2, COLOR1, kbps_speed, type_speed)
		e += '[B]ETA:[/B] [COLOR '+COLOR1+']%02d:%02d[/COLOR][/COLOR]' % divmod(eta, 60)
		dp.update(int(percent), str(mbs) + ' ' + str(e))
	except Exception as e:
		return str(e)
	if dp.iscanceled(): 
		dp.close()
		sys.exit()