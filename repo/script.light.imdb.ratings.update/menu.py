# -*- coding: utf-8 -*-

#############################
# Light IMDb Ratings Update #
# by axlt2002               #
#############################

import sys, os
import xbmcgui, xbmcplugin
from six.moves import urllib
from update import StartUpdate
from core.database import update_database
from support.common import *

def main_menu():
	item = xbmcgui.ListItem(addonLanguage(32890))
	item.setArt({'thumb': addonIcon})
	xbmcplugin.addDirectoryItem(int(sys.argv[1]), "plugin://script.light.imdb.ratings.update/?url=&mode=1", item)
	item = xbmcgui.ListItem(addonLanguage(32891))
	item.setArt({'thumb': addonIcon})
	xbmcplugin.addDirectoryItem(int(sys.argv[1]), "plugin://script.light.imdb.ratings.update/?url=&mode=2", item)
	item = xbmcgui.ListItem(addonLanguage(32896))
	item.setArt({'thumb': addonIcon})
	xbmcplugin.addDirectoryItem(int(sys.argv[1]), "plugin://script.light.imdb.ratings.update/?url=&mode=3", item)
	item = xbmcgui.ListItem(addonLanguage(32892))
	item.setArt({'thumb': addonIcon})
	xbmcplugin.addDirectoryItem(int(sys.argv[1]), "plugin://script.light.imdb.ratings.update/?url=&mode=4", item)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def get_params():
	param=[]
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]                 
	return param

params=get_params()
url=None
name=None
mode=None
iconimage=None

try: url=urllib.unquote_plus(params["url"])
except: pass
try: name=urllib.unquote_plus(params["name"])
except: pass
try: mode=int(params["mode"])
except: pass
try: iconimage=urllib.unquote_plus(params["iconimage"])
except: pass

if mode == None:
	main_menu()
elif mode==1:
	StartUpdate()
elif mode==2:
	update_database(True)
elif mode==3:
	database_date = addonSettings.getSetting("LastDatabaseUpdate")
	if database_date == "2000-01-01":
		database_date = addonLanguage(32528)
	dataset_date = addonSettings.getSetting("DatasetDate")
	if dataset_date == "Sat, 01 Jan 2000":
		dataset_date = addonLanguage(32528)
	top250_date = addonSettings.getSetting("Top250Date")
	if top250_date == "Sat, 01 Jan 2000":
		top250_date = addonLanguage(32528)
	infos = "{1}{0}{2}{4}{3}{5}\n".format(addonLanguage(32905), label_open, label_close, database_date, info_open, info_close)
	infos += "{1}{0}{2}{4}{3}{5}\n".format(addonLanguage(32906), label_open, label_close, dataset_date, info_open, info_close)
	infos += "{1}{0}{2}{4}{3}{5}".format(addonLanguage(32907), label_open, label_close, top250_date, info_open, info_close)
	xbmcgui.Dialog().ok("%s" % (addonName), infos)
elif mode==4:
	addonSettings.openSettings()