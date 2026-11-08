# -*- coding: utf-8 -*-

#############################
# Light IMDb Ratings Update #
# by axlt2002               #
#############################

import json, sys, platform

import xbmc, xbmcaddon, xbmcvfs, xbmcgui
import os, unicodedata
import datetime
from dateutil.relativedelta import relativedelta

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass

addonSettings = xbmcaddon.Addon( "script.light.imdb.ratings.update" )
addonName     = addonSettings.getAddonInfo( "name" )
addonVersion  = addonSettings.getAddonInfo( "version" )
addonIcon     = os.path.join( addonSettings.getAddonInfo( "path" ), "icon.png" )
addonProfile  = xbmc.translatePath( addonSettings.getAddonInfo( "profile" ) )
addonLanguage = addonSettings.getLocalizedString

onMovies              = addonSettings.getSetting( "Movies" )
onTVShows             = addonSettings.getSetting( "TVShows" )
ShowNotifications     = addonSettings.getSetting( "ShowNotifications" )
ShowProgress          = addonSettings.getSetting( "ShowProgress" )
ShowErrorMessage      = addonSettings.getSetting( "ShowErrorMessage" )
IgnoreNotFound        = addonSettings.getSetting( "IgnoreNotFound" )
CompleteLog           = addonSettings.getSetting( "CompleteLog" )
IncludeEpisodes       = addonSettings.getSetting( "IncludeEpisodes" )
IncludeTop250         = addonSettings.getSetting( "IncludeTop250" )
UpdateMode            = addonSettings.getSetting( "UpdateMode" )
IMDbDefault           = addonSettings.getSetting( "IMDbRatingDefault" )
Sound                 = addonSettings.getSetting( "NotificationsSound" )
ScheduleEnabled       = addonSettings.getSetting( "ScheduleEnabled" )
ScheduleType          = addonSettings.getSetting( "ScheduleType" )
ScheduledWeekDay      = addonSettings.getSetting( "ScheduledWeekDay" )
DayTime               = addonSettings.getSetting( "DayTime" )
DatasetDate           = addonSettings.getSetting( "DatasetDate" )
Top250Date            = addonSettings.getSetting( "Top250Date" )
UpdateDatabaseStartup = addonSettings.getSetting( "UpdateDatabaseStartup" )
UpdateDatabaseRatings = addonSettings.getSetting( "UpdateDatabaseRatings" )
LastDatabaseUpdate    = addonSettings.getSetting( "LastDatabaseUpdate" )
EnableContextMenu     = addonSettings.getSetting( "EnableContextMenu" )
UseEstuaryColors      = addonSettings.getSetting( "UseEstuaryColors" )

NumberOfThreads = addonSettings.getSetting( "NumberOfThreads" )

FilterByDateAdded = addonSettings.getSetting( "FilterByDateAdded" )
Months = int(addonSettings.getSetting( "Months" ))
DateAddedThreshold = (datetime.datetime.now() - relativedelta( months = Months )).strftime('%Y-%m-%d')
FilterByYear = addonSettings.getSetting( "FilterByYear" )
YearThreshold = str(addonSettings.getSetting( "Year" ))

label_open, label_close = "", ""
info_open, info_close   = "", ""
if UseEstuaryColors == "true":
    label_open, label_close = "[COLOR white]", "[/COLOR]"
    info_open, info_close   = "[COLOR button_focus]", "[/COLOR]"

def doUnicode( textMessage ):
    try: textMessage = unicode( textMessage, 'utf-8' )
    except: pass
    return textMessage

def doNormalize( textMessage ):
    try: textMessage = unicodedata.normalize( 'NFKD', doUnicode( textMessage ) ).encode( 'utf-8' )
    except: pass
    return textMessage

def defaultLog( textMessage ):
    xbmc.log( "[%s] - %s" % ( addonName, doNormalize( textMessage ) ) )

def debugLog( textMessage ):
    xbmc.log( "[%s] - %s" % ( addonName, doNormalize( textMessage ) ), level = xbmc.LOGDEBUG )

def doNotify( textMessage, millSec ):
    dialog = xbmcgui.Dialog()
    if Sound == "true":
        playSound = True
    else:
        playSound = False
    dialog.notification(addonName, textMessage, addonIcon, millSec, playSound)

def start_StatusLog():
	if xbmcvfs.exists( addonProfile + "/update.old.log" ):
		os.remove( addonProfile + "/update.old.log" )
	if xbmcvfs.exists( addonProfile + "/update.log" ):
		os.rename( addonProfile + "/update.log", addonProfile + "/update.old.log" )
	f = open( addonProfile + "/update.log", 'wb' )
	f.write( doNormalize( "----------------------------------------------------------------------------------------------------------------\n" ) )
	f.write( doNormalize( "Starting " + addonName + " (" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")\n" ) )
	f.write( doNormalize( "Add-on version: " + addonVersion + "\n" ) )
	f.write( doNormalize( "OS: " + platform.system() + " " + platform.release() + "\n" ) )
	f.write( doNormalize( "Kodi version: " + get_kodi_version() + "\n" ) )
	f.write( doNormalize( "Build: " + xbmc.getInfoLabel('System.BuildVersion') + "\n" ) )
	f.write( doNormalize( "Movies update: " + onMovies + "\n" ) )
	f.write( doNormalize( "TV shows update: " + onTVShows + "\n" ) )
	if onTVShows == "true":
		f.write( doNormalize( "Include episodes: " + IncludeEpisodes + "\n" ) )
	f.write( doNormalize( "Include Top 250 for movies: " + IncludeTop250 + "\n" ) )
	f.write( doNormalize( "IMDb ratings as default: " + IMDbDefault + "\n" ) )
	f.write( doNormalize( "Update database at Kodi startup: " + UpdateDatabaseStartup + "\n" ) )
	f.write( doNormalize( "Update database when ratings update starts: " + UpdateDatabaseRatings + "\n" ) )
	f.write( doNormalize( "Last database update: " + LastDatabaseUpdate + "\n" ) )
	f.write( doNormalize( "IMDb ratings dataset: " + DatasetDate + "\n" ) )
	f.write( doNormalize( "Top 250 chart: " + Top250Date + "\n" ) )
	if FilterByDateAdded == "true":
		f.write( doNormalize( "Filter by date added: " + str(Months) + " months (" + DateAddedThreshold + ")\n" ) )
	else:
		f.write( doNormalize( "Filter by date added: update all\n" ) )
	if FilterByYear == "true":
		f.write( doNormalize( "Filter by year: " + YearThreshold + "\n" ) )
	else:
		f.write( doNormalize( "Filter by year: update all\n" ) )
	f.write( doNormalize( "Number of threads: " + str(NumberOfThreads) + "\n" ) )
	f.write( doNormalize( "Schedule enabled: " + ScheduleEnabled + "\n" ) )
	if ScheduleEnabled == "true":
		if ScheduleType == '0':
			schedule_type = "weekly"
		else:
			schedule_type = "daily"
		f.write( doNormalize( "Schedule period: " + schedule_type + "\n" ) )
		f.write( doNormalize( "Next scheduled update: " + ScheduledWeekDay + " at " + DayTime + "\n" ) )
	f.write( doNormalize( "----------------------------------------------------------------------------------------------------------------\n" ) )
	f.close()

def dump_settings_StatusLog( updateitem ):
	f = open( addonProfile + "/update.log", 'ab' )
	f.write( doNormalize( "----------------------------------------------------------------------------------------------------------------\n" ) )
	'''if updateitem == "tvshow" or updateitem == "season":
		f.write( doNormalize( "Include episodes: " + IncludeEpisodes + "\n" ) )
		if int(UpdateMode) == 0:
			updatemode = "episode"
		else:
			updatemode = "season"
		f.write( doNormalize( "UpdateMode: " + updatemode + "\n" ) )'''
	if FilterByDateAdded == "true":
		f.write( doNormalize( "Filter by date added: " + str(Months) + " months (" + DateAddedThreshold + ")\n" ) )
	else:
		f.write( doNormalize( "Filter by date added: update all\n" ) )
	if FilterByYear == "true":
		f.write( doNormalize( "Filter by year: " + YearThreshold + "\n" ) )
	else:
		f.write( doNormalize( "Filter by year: update all\n" ) )
	f.write( doNormalize( "----------------------------------------------------------------------------------------------------------------\n" ) )
	f.close()

def dump_database_StatusLog( log ):
	f = open( addonProfile + "/update.log", 'ab' )
	f.write( doNormalize( "\n" + log ) )
	f.write( doNormalize( "----------------------------------------------------------------------------------------------------------------\n" ) )
	f.close()

def statusLog( textMessage ):
	f = open( addonProfile + "/update.log", 'ab' )
	f.write( doNormalize( "\n" + textMessage + "\n" ) )
	f.close()

def get_kodi_version():
	codenames = {
		22: "Piers",
		21: "Omega",
		20: "Nexus",
		19: "Matrix",
		18: "Leia",
		17: "Krypton",
		16: "Jarvis"
	}

	query = {
		"jsonrpc": "2.0",
		"method": "Application.GetProperties",
		"params": {
			"properties": ["version", "name"]
		},
		"id": 1
	}
	json_query = xbmc.executeJSONRPC(json.dumps(query))
	if sys.version_info[0] >= 3:
		json_query = str(json_query)
	else:
		json_query = unicode(json_query, 'utf-8', errors='ignore')
	json_query = json.loads(json_query)
	version_installed = []
	if 'result' in json_query and 'version' in json_query['result']:
		version_installed = json_query['result']['version']
		return str(version_installed['major']) + "." + str(version_installed['minor']) + " (" + codenames.get(version_installed['major'], "Unknown") + ")"
	else:
		return ""