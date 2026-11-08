# -*- coding: utf-8 -*-

#############################
# Light IMDb Ratings Update #
# by axlt2002               #
#############################

import xbmc, xbmcgui
import sys, re
import math
import datetime
if sys.version_info[0] >= 3:
	import json as jSon
else:
	import simplejson as jSon
from support.common import *
from core.update_common import *
from core.update_main import TVShows
from core.imdb_scraper import parse_IMDb_page
from core.database import *
	
def open_context_menu(filename, label):
	updateitem = ""
	movieid = -1; episodeid = -1; tvshowid = -1; setid = -1
	rating = -1; votes = -1; top250 = 0
	Title = ""
	IMDb = None; TVDB = None; TMDB = None
	season = -1
	episode = ""
	filename = filename.replace("/"," ")
	id_parts = re.findall(r"[+-]?\d+(?:\.\d+)?", filename)
	tag = 0
	if "genreid" in filename or "year" in filename or "actorid" in filename or "directorid" in filename or "studioid" in filename or "setid" in filename or "countryid" in filename or "tagid" in filename or "videoversions" in filename:
		tag = 1
	if "movies" in filename or "recentlyaddedmovies" in filename:
		if len(id_parts) != 2:
			updateitem = "movie"
			movieid = int(id_parts[0 + tag])
			jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":' + str( movieid ) + ',"properties":["uniqueid","ratings","top250","title"]},"id":1}'
		else:
			updateitem = "movieset"
			setid = int(id_parts[0])
	elif ("tvshows" in filename or "inprogresstvshows" in filename) and "season" in filename and "tvshowid" in filename:
		updateitem = "episode"
		episodeid = int(id_parts[2 + tag])
		jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetEpisodeDetails","params":{"episodeid":' + str( episodeid ) + ',"properties":["uniqueid","ratings","episode","season","showtitle","tvshowid"]},"id":1}'
	elif ("tvshows" in filename or "inprogresstvshows" in filename) and "tvshowid" in filename:
		season = int(id_parts[1 + tag])
		if season == -1 and not label.startswith("* "):
			updateitem = "episode"
			episodeid = int(id_parts[2 + tag])
			jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetEpisodeDetails","params":{"episodeid":' + str( episodeid ) + ',"properties":["uniqueid","ratings","episode","season","showtitle","tvshowid"]},"id":1}'
		else:
			updateitem = "season"
			tvshowid = int(id_parts[0 + tag])
			jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":' + str( tvshowid ) + ',"properties":["uniqueid","ratings","title"]},"id":1}'
	elif ("tvshows" in filename or "inprogresstvshows" in filename):
		tvshowid = int(id_parts[0 + tag])
		if tvshowid ==  -1:
			updateitem = "episode"
			episodeid = int(id_parts[2])
			jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetEpisodeDetails","params":{"episodeid":' + str( episodeid ) + ',"properties":["uniqueid","ratings","episode","season","showtitle","tvshowid"]},"id":1}'
		else:
			updateitem = "tvshow"
			jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":' + str( tvshowid ) + ',"properties":["uniqueid","ratings","title"]},"id":1}'
	elif "recentlyaddedepisodes" in filename:
		updateitem = "episode"
		episodeid = int(id_parts[0])
		jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetEpisodeDetails","params":{"episodeid":' + str( episodeid ) + ',"properties":["uniqueid","ratings","episode","season","showtitle","tvshowid"]},"id":1}'
	jSonResponse = ""
	if updateitem != "movieset":
		jSonResponse = xbmc.executeJSONRPC( jSonQuery )
		jSonResponse = jSon.loads( jSonResponse )
	if jSonResponse and 'moviedetails' in jSonResponse['result']:
		item = jSonResponse['result']['moviedetails']
		unique_id = item.get('uniqueid')
		if unique_id != None:
			IMDb = unique_id.get('imdb')
			TVDB = unique_id.get('tvdb')
			TMDB = unique_id.get('tmdb')
			IMDb, TVDB, TMDB = normalize_IDs(IMDb, TVDB, TMDB)
		Title = item.get('title')
		ratings = item.get('ratings')
		top250 = item.get('top250')
		imdb_rating = ratings.get('imdb')
		if imdb_rating != None:
			rating = imdb_rating.get('rating')
			votes = imdb_rating.get('votes')
	elif jSonResponse and 'episodedetails' in jSonResponse['result']:
		item = jSonResponse['result']['episodedetails']
		unique_id = item.get('uniqueid')
		if unique_id != None:
			IMDb = unique_id.get('imdb')
			TVDB = unique_id.get('tvdb')
			TMDB = unique_id.get('tmdb')
			IMDb, TVDB, TMDB = normalize_IDs(IMDb, TVDB, TMDB)
		tvshowid = item.get('tvshowid')
		season = item.get('season')
		episode = "%02d"%item.get('episode')
		Title = item.get('showtitle') + " " + str( season ) + "x" + str( episode )
		ratings = item.get('ratings')
		imdb_rating = ratings.get('imdb')
		if imdb_rating != None:
			rating = imdb_rating.get('rating')
			votes = imdb_rating.get('votes')
	elif jSonResponse and 'tvshowdetails' in jSonResponse['result']:
		item = jSonResponse['result']['tvshowdetails']
		unique_id = item.get('uniqueid')
		if unique_id != None:
			IMDb = unique_id.get('imdb')
			TVDB = unique_id.get('tvdb')
			TMDB = unique_id.get('tmdb')
			IMDb, TVDB, TMDB = normalize_IDs(IMDb, TVDB, TMDB)
		Title = item.get('title')
		ratings = item.get('ratings')
		imdb_rating = ratings.get('imdb')
		if imdb_rating != None:
			rating = imdb_rating.get('rating')
			votes = imdb_rating.get('votes')
	context_menu_options(updateitem, movieid, episodeid, tvshowid, season, episode, IMDb, TVDB, TMDB, Title, rating, votes, top250, setid)

def context_menu_options(updateitem, movieid, episodeid, tvshowid, season, episode, IMDb, TVDB, TMDB, Title, rating, votes, top250, setid):
	if EnableContextMenu == "false":
		if updateitem == "movieset":
			statusLog( datetime.datetime.now().strftime("%H:%M:%S") + " - " + "Context menu ratings update for movie set" )
			doUpdateMovieSet(setid)
		else:
			statusLog( datetime.datetime.now().strftime("%H:%M:%S") + " - " + "Context menu ratings update" )
			doUpdateItem(updateitem, movieid, episodeid, tvshowid, season, episode, IMDb, TVDB, TMDB, Title, top250)
		return
	option = -1
	while True:
		id_label = ""; update_label = ""
		sIMDb, sTVDB, sTMDB = printable_IDs(IMDb, TVDB, TMDB)
		stringList = []
		if updateitem == "movieset":
			update_label = addonLanguage(32900)
		elif updateitem == "season" and season == -1:
			update_label = addonLanguage(32901)
		elif updateitem == "season" and season != -1:
			update_label = addonLanguage(32902)
		else:
			update_label = addonLanguage(32253)
		stringList += [ "{1}{0}{2}".format(update_label, label_open, label_close) ]
		if updateitem != "season" and updateitem != "movieset":
			if rating != -1:
				rating = round(rating, 2)
				stringList += [ "{1}{0}{2}{4}{3}{5}".format(addonLanguage(32263) + ": ", label_open, label_close, str(rating) + " (" + '{0:,}'.format(votes) + " " + addonLanguage(32264) + ")", info_open, info_close) ]
			else:
				stringList += [ "{1}{0}{2}{4}{3}{5}".format(addonLanguage(32263) + ": ", label_open, label_close, addonLanguage(32528), info_open, info_close) ]
		if updateitem == "movie":
			if top250 != 0:
				stringList += [ "{1}{0}{2}{4}{3}{5}".format(addonLanguage(32265) + ": ", label_open, label_close, str(top250), info_open, info_close) ]
			else:
				stringList += [ "{1}{0}{2}{4}{3}{5}".format(addonLanguage(32265) + ": ", label_open, label_close, addonLanguage(32528), info_open, info_close) ]
		elif updateitem != "season" and updateitem != "movieset":
			stringList += [ "{1}{0}{2}{4}{3}{5}".format("TVDB ID: ", label_open, label_close, sTVDB, info_open, info_close) ]
		if updateitem != "season" and updateitem != "movieset":
			stringList += [ "{1}{0}{2}{4}{3}{5}".format("TMDB ID: ", label_open, label_close, sTMDB, info_open, info_close) ]
			stringList += [ "{1}{0}{2}{4}{3}{5}".format("IMDb ID: ", label_open, label_close, sIMDb, info_open, info_close) ]
		option = xbmcgui.Dialog().select(addonName, stringList)
		if option == -1:
			return
		elif option == 0:
			if updateitem == "movieset":
				statusLog( datetime.datetime.now().strftime("%H:%M:%S") + " - " + "Context menu ratings update for movie set" )
				doUpdateMovieSet(setid)
				return
			statusLog( datetime.datetime.now().strftime("%H:%M:%S") + " - " + "Context menu ratings update" )
			_rating, _votes, _top250, _IMDb = doUpdateItem(updateitem, movieid, episodeid, tvshowid, season, episode, IMDb, TVDB, TMDB, Title, top250)
			if not (_rating == -1 and _votes == -1 and _top250 == -1):
				rating = _rating
				votes = int(_votes)
				top250 = _top250
			if _IMDb != None:
				IMDb = _IMDb
			if updateitem == "season":
				return
			else:
				continue
		elif option == 1:
			continue
		elif option == 2 and updateitem == "movie":
			continue
		elif option == 2:
			id = xbmcgui.Dialog().input("TVDB ID", sTVDB)
			if id:
				TVDB = id
				id_label = "tvdb"
		elif option == 3:
			id = xbmcgui.Dialog().input("TMDB ID", sTMDB)
			if id:
				TMDB = id
				id_label = "tmdb"
		elif option == 4:
			id = xbmcgui.Dialog().input("IMDb ID", sIMDb)
			if id:
				IMDb = id
				id_label = "imdb"
		if id_label:
			if updateitem == "movie":
				jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.SetMovieDetails","params":{"movieid":' + str( movieid ) + ',"uniqueid": {"' + id_label + '": "' + id + '"}},"id":1}'
			elif updateitem == "tvshow":
				jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.SetTVShowDetails","params":{"tvshowid":' + str( tvshowid ) + ',"uniqueid": {"' + id_label + '": "' + id + '"}},"id":1}'
			elif updateitem == "episode":
				jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":' + str( episodeid ) + ',"uniqueid": {"' + id_label + '": "' + id + '"}},"id":1}'
			jSonResponse = xbmc.executeJSONRPC( jSonQuery )

def doUpdateItem(updateitem, movieid, episodeid, tvshowid, season, episode, IMDb, TVDB, TMDB, Title, top250):
	if UpdateDatabaseRatings == "true" and datetime.datetime.now().strftime("%Y-%m-%d") != addonSettings.getSetting( "LastDatabaseUpdate" ):
		if not update_database():
			return -1, -1, -1, None
	if addonSettings.getSetting( "PerformingUpdate" ) == "true":
		xbmcgui.Dialog().ok( "%s" % ( addonName ), addonLanguage(32251) )
		return -1, -1, -1, None
	if addonSettings.getSetting( "UpdatingDatabase" ) == "true":
		xbmcgui.Dialog().ok( "%s" % ( addonName ), addonLanguage(32252) )
		return -1, -1, -1, None
	addonSettings.setSetting( "PerformingUpdate", "true" )
	progress = xbmcgui.DialogProgressBG()
	progress.create( addonLanguage(32260), Title )
	exit = False
	if updateitem == "movie":
		if IMDb == None:
			IMDb, statusInfo = get_IMDb_ID_from_TMDb(updateitem, TMDB)
	elif updateitem == "tvshow" or updateitem == "season":
		if IMDb == None:
			IMDb, statusInfo = get_tvshow_IMDb_ID(updateitem, tvshowid, TVDB, TMDB, Title)
	elif updateitem == "episode":
		if IMDb == None:
			if (updateitem == "episode"):
				tvshowTMDB = None
				jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":' + str( tvshowid ) + ',"properties":["uniqueid","ratings","title"]},"id":1}'
				jSonResponse = xbmc.executeJSONRPC( jSonQuery )
				jSonResponse = jSon.loads( jSonResponse )
				item = jSonResponse['result']['tvshowdetails']
				unique_id = item.get('uniqueid')
				if unique_id != None:
					tvshowTMDB = unique_id.get('tmdb')
					if tvshowTMDB == "": tvshowTMDB = None
			IMDb, statusInfo = get_IMDb_ID_from_TMDb(updateitem, tvshowTMDB, season, episode)
	if IMDb == None:
		sIMDb, sTVDB, sTMDB = printable_IDs(IMDb, TVDB, TMDB)
		statusLog( Title + " (IMDb ID: " + sIMDb + ", TVDB ID: " + sTVDB + ", TMDB ID: "+ sTMDB + ")" + "\n" + statusInfo )
		if ShowErrorMessage == "true":
			addonSettings.setSetting( "LogDialog", "true" )
		exit = True
	else:
		#(updatedRating, updatedVotes, updatedTop250, statusInfo) = parse_IMDb_page(IMDb)
		(updatedRating, updatedVotes, updatedTop250, statusInfo) = get_database(IMDb)
		if updatedRating != None:
			statusInfo = "Rating: %s, Votes: %s" % (updatedRating, updatedVotes)
			if updateitem == "movie":
				if updatedTop250 == -1:
					updatedTop250 = top250
					statusInfo = statusInfo + ", Top250: %s" % str(updatedTop250)
				elif updatedTop250 == 0:
					statusInfo = statusInfo + ", Top250: n/a"
				else:
					statusInfo = statusInfo + ", Top250: %s" % str(updatedTop250)
		if updatedRating == None or CompleteLog == "true":
			sIMDb, sTVDB, sTMDB = printable_IDs(IMDb, TVDB, TMDB)
			statusLog( Title + " (IMDb ID: " + sIMDb + ", TVDB ID: " + sTVDB + ", TMDB ID: "+ sTMDB + ")" + "\n" + statusInfo )
		if updatedRating == None:
			if ShowErrorMessage == "true" and statusInfo == "IMDb ID not found in the database" and IgnoreNotFound == "false":
				addonSettings.setSetting( "LogDialog", "true" )
			exit = True
	if exit == True:
		progress.update( 100, addonLanguage(32260), Title )
		xbmc.sleep(1000)
		progress.close()
		addonSettings.setSetting( "PerformingUpdate", "false" )
		if ShowErrorMessage == "true" and addonSettings.getSetting( "LogDialog") == "true":
			xbmcgui.Dialog().ok( "%s" % ( addonName ), addonLanguage(32824) )
			if ShowErrorMessage == "true":
				addonSettings.setSetting( "LogDialog", "false" )
		return -1, -1, -1, None
	if updateitem == "movie":
		jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.SetMovieDetails","params":{"movieid":' + str( movieid ) + ',"uniqueid": {"imdb": "' + IMDb + '"},"ratings":{"imdb":{"rating":' + str( updatedRating ) + ',"votes":' + str( updatedVotes ).replace(",", "") + ',"default":' + IMDbDefault + '}},"top250":' + str( updatedTop250 ) + '},"id":1}'
	elif updateitem == "tvshow" or updateitem == "season":
		jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.SetTVShowDetails","params":{"tvshowid":' + str( tvshowid ) + ',"ratings":{"imdb":{"rating":' + str( updatedRating ) + ',"votes":' + str( updatedVotes ).replace(",", "") + ',"default":' + IMDbDefault + '}}},"id":1}'
	elif updateitem == "episode":
		jSonQuery = '{"jsonrpc":"2.0","method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":' + str( episodeid ) + ',"uniqueid": {"imdb": "' + IMDb + '"},"ratings":{"imdb":{"rating":' + str( updatedRating ) + ',"votes":' + str( updatedVotes ).replace(",", "") + ',"default":' + IMDbDefault + '}}},"id":1}'
	jSonResponse = xbmc.executeJSONRPC( jSonQuery )
	if (updateitem == "tvshow" and IncludeEpisodes == "true") or updateitem == "season":
		if int(UpdateMode) == 0:
			TVShows().doUpdateEpisodes(tvshowid, TMDB, season, progress, 0, True)
		else:
			doUpdateEpisodesBySeason(tvshowid, IMDb, season, progress, 0, None)
	progress.update( 100, addonLanguage(32260), Title )
	xbmc.sleep(1000)
	progress.close()
	addonSettings.setSetting( "PerformingUpdate", "false" )
	if ShowErrorMessage == "true" and addonSettings.getSetting( "LogDialog") == "true":
		xbmcgui.Dialog().ok( "%s" % ( addonName ), addonLanguage(32824) )
		addonSettings.setSetting( "LogDialog", "false" )
	return float(updatedRating), updatedVotes.replace(",", ""), updatedTop250, IMDb

def doUpdateMovieSet(setid):
	jSonQuery = '{"jsonrpc":"2.0","method": "VideoLibrary.GetMovieSetDetails","params": {"setid":' + str(setid) + ',"movies":{"properties":["uniqueid","title","top250"]}},"id":1}'
	jSonResponse = xbmc.executeJSONRPC( jSonQuery )
	jSonResponse = jSon.loads( jSonResponse )
	if 'setdetails' in jSonResponse['result'] and 'movies' in jSonResponse['result']['setdetails']:
		for item in jSonResponse['result']['setdetails']['movies']:
			IMDb = None; TVDB = None; TMDB = None
			unique_id = item.get('uniqueid')
			if unique_id != None:
				IMDb = unique_id.get('imdb')
				TVDB = unique_id.get('tvdb')
				TMDB = unique_id.get('tmdb')
				IMDb, TVDB, TMDB = normalize_IDs(IMDb, TVDB, TMDB)
			movieid = item.get('movieid')
			Title = item.get('title')
			top250 = item.get('top250')
			doUpdateItem("movie", movieid, -1, -1, -1, "", IMDb, TVDB, TMDB, Title, top250)