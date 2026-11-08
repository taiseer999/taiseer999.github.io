# -*- coding: utf-8 -*-

#############################
# Light IMDb Ratings Update #
# by axlt2002               #
#############################

import xbmc, xbmcvfs
import datetime
import gzip, csv, re
import sqlite3, sys
from support.common import *
from support.httptools import *

database_folder = os.path.join(addonProfile, "database")
gz_file = os.path.join(database_folder, "title.ratings.tsv.gz")
html_file = os.path.join(database_folder, "top250_charts.html")

IMDb_dataset_url = "https://datasets.imdbws.com/title.ratings.tsv.gz"
Top250_charts_url = "http://top250.info/charts/"

def update_database(forced = False):
	addonSettings.setSetting( "UpdatingDatabase", "true" )

	if ShowProgress == "true":
		progress = xbmcgui.DialogProgressBG()
		progress.create(addonName)
		progress.update(10, addonName, addonLanguage(32880))
	database_date = addonSettings.getSetting("LastDatabaseUpdate")
	dataset_date = addonSettings.getSetting("DatasetDate")
	top250_date = addonSettings.getSetting("Top250Date")
	update_ok = True
	status_ok = {"Verified and downloaded", "No update available"}
	dataset_info = {
		"status": "Pending",
		"last_modified": None,
	}

	top250_info = {
		"status": "Pending",
		"last_modified": None,
	}

	if forced:
		label = "Manual database update"
	else:
		label = "Database update"
	database_log = datetime.datetime.now().strftime("%H:%M:%S") + " - " + label + "\n"
	database_log += "----------------------------------------------------------------------------------------------------------------\n"
	database_log += "Last database update: {}\n".format(database_date)
	database_log += "Current IMDb ratings dataset: {}\n".format(dataset_date)
	database_log += "Current Top 250 chart: {}\n".format(top250_date)
	if not os.path.exists(database_folder):
		os.makedirs(database_folder)

	if ShowProgress == "true":
		progress.update(20, addonName, addonLanguage(32880))

	database_log += "Connect to database...\n"
	try:
		conn = sqlite3.connect(os.path.join(database_folder, "database.db"))
	except sqlite3.Error as e:
		database_log += "SQLite error: {}\n".format(e)
		dump_database_StatusLog(database_log)
		xbmcgui.Dialog().ok("%s" % (addonName), addonLanguage(32250))
		addonSettings.setSetting( "UpdatingDatabase", "false" )
		return False
	cursor = conn.cursor()

	if ShowProgress == "true":
		progress.update(30, addonName, addonLanguage(32880))

	database_log += "Verifying and downloading IMDb ratings dataset...\n"
	date = "Sat, 01 Jan 2000" if forced else dataset_date
	dataset_info = verify_and_download(IMDb_dataset_url, gz_file, date)
	database_log += "{}\n".format(dataset_info["status"])

	if ShowProgress == "true":
		progress.update(40, addonName, addonLanguage(32880))

	if dataset_info["status"] == "Verified and downloaded":
		database_log += "Inserting IMDb ratings dataset into database...\n"
		cursor.execute("DROP TABLE IF EXISTS ratings")
		cursor.execute("CREATE TABLE ratings (imdb_id TEXT, rating TEXT, votes TEXT)")
		if sys.version_info < (3, 0):
			with gzip.open(gz_file, 'rb') as f:
				reader = csv.reader(f, delimiter='\t')
				next(reader)
				cursor.executemany("INSERT INTO ratings (imdb_id, rating, votes) VALUES (?, ?, ?)", reader)
		else:
			with gzip.open(gz_file, 'rt', encoding='utf-8') as f:
				reader = csv.reader(f, delimiter='\t')
				next(reader)
				cursor.executemany("INSERT INTO ratings (imdb_id, rating, votes) VALUES (?, ?, ?)", reader)
		addonSettings.setSetting("DatasetDate", dataset_info["last_modified"])
		database_log += "New IMDb ratings dataset: {}\n".format(dataset_info["last_modified"])

	if ShowProgress == "true":
		progress.update(50, addonName, addonLanguage(32880))

	if addonSettings.getSetting( "IncludeTop250" ) == "true":
		database_log += "Verifying and downloading Top 250 chart...\n"
		date = "Sat, 01 Jan 2000" if forced else top250_date
		top250_info = verify_and_download(Top250_charts_url, html_file, date)
		database_log += "{}\n".format(top250_info["status"])

		if ShowProgress == "true":
			progress.update(60, addonName, addonLanguage(32880))

		if top250_info["status"] == "Verified and downloaded":
			if sys.version_info < (3, 0):
				with open(html_file, 'rb') as f:
					html = f.read()
			else:
				with open(html_file, "r", encoding="utf-8") as f:
					html = f.read()
			regex = r'movie/[?](\d+)"><'
			list_top250 = [(i, "tt{}".format(imdb_id)) for i, imdb_id in enumerate(re.findall(regex, html), start=1)]
			database_log += "Inserting Top 250 chart into database...\n"
			cursor.execute("DROP TABLE IF EXISTS charts")
			cursor.execute("CREATE TABLE charts (position TEXT, imdb_id TEXT)")
			cursor.executemany("INSERT INTO charts (position, imdb_id) VALUES (?, ?)", list_top250)
			addonSettings.setSetting( "Top250Date", top250_info["last_modified"])
			database_log += "New Top 250 chart: {}\n".format(top250_info["last_modified"])

	if ShowProgress == "true":
		progress.update(70, addonName, addonLanguage(32880))

	cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ratings'")
	if cursor.fetchone() == None:
		update_ok = False
	elif dataset_info["status"] not in status_ok:
		database_log += "Using the IMDBb ratings dataset from {}\n".format(dataset_date)

	if ShowProgress == "true":
		progress.update(80, addonName, addonLanguage(32880))

	if addonSettings.getSetting( "IncludeTop250" ) == "true":
		cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='charts'")
		if cursor.fetchone() == None:
			update_ok = False
		elif top250_info["status"] not in status_ok:
			database_log += "Using the Top 250 chart from {}\n".format(top250_date)

	if ShowProgress == "true":
		progress.update(90, addonName, addonLanguage(32880))

	conn.commit()
	conn.close()
	database_log += "Deleting temp files (if any)...\n"
	delete_temp_files()

	if ShowProgress == "true":
		progress.update(100, addonName, addonLanguage(32880))
		xbmc.sleep(1000)
		progress.close()

	if update_ok and (dataset_info["status"] == "Verified and downloaded" or top250_info["status"] == "Verified and downloaded"):
		database_log += "The database has been successfully updated\n"
		if ShowNotifications == "true":
			doNotify( addonLanguage(32881), 5000 )
	if not update_ok:
		xbmcgui.Dialog().ok("%s" % (addonName), addonLanguage(32257))
	else:
		database_date = datetime.datetime.now().strftime("%Y-%m-%d")
		addonSettings.setSetting("LastDatabaseUpdate", database_date)
		database_log += "Database updated: {}\n".format(database_date)
	dump_database_StatusLog(database_log)

	addonSettings.setSetting( "UpdatingDatabase", "false" )
	return update_ok

def get_database(imdb_id):
	rating_and_votes = (None, None)
	top250 = -1
	StatusInfo = "IMDb ID not found in the database"

	conn = sqlite3.connect(os.path.join(database_folder, "database.db"))
	cursor = conn.cursor()

	cursor.execute('''SELECT rating, votes FROM ratings WHERE imdb_id = ?''', (imdb_id,))
	rating_votes = cursor.fetchone()
	if rating_votes != None:
		rating_and_votes = (rating_votes[0], rating_votes[1])

	if addonSettings.getSetting( "IncludeTop250" ) == "true":
		cursor.execute('''SELECT position FROM charts WHERE imdb_id = ?''', (imdb_id,))
		position = cursor.fetchone()
		if position != None:
			top250 = int(position[0])
		else:
			top250 = 0

	conn.close()
	return (rating_and_votes[0], rating_and_votes[1], top250, StatusInfo)

def delete_temp_files():
	if xbmcvfs.exists(gz_file):
		xbmcvfs.delete(gz_file)
	if xbmcvfs.exists(html_file):
		xbmcvfs.delete(html_file)