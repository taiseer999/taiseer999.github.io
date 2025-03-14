import sys, urllib.parse
from xbmc import executebuiltin, getInfoLabel
from modules.router import routing

if __name__ == '__main__':
	try: params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
	except:
		if 'refresh_widgets' in sys.argv[1]:
			executebuiltin('UpdateLibrary(video,special://skin/foo)')
	else: routing(params)
#	if 'pov' not in getInfoLabel('Container.PluginName'): sys.exit(1)

