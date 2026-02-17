# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcvfs
import xbmcaddon
import unicodedata
import PTN
import re

from xbmcplugin import addDirectoryItem
from xbmcgui import ListItem

##### burekas fix
#from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.parse import quote, quote_plus, unquote

##### burekas fix
from os import path
from json import loads, load, dumps
from time import time
import requests

__addon__ = xbmcaddon.Addon()
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, 'temp', ''))

MyAddonName = __addon__.getAddonInfo('name').replace(" ","_")
MyAddonVersion = __addon__.getAddonInfo('version')

BASE_URL_OS_API = u"https://api.opensubtitles.com/api/v1"
USER_AGENT = '%s v%s' %(MyAddonName, MyAddonVersion)

DEFAULT_USERNAME = 'allsubsplusos'
DEFAULT_PASS = 'allsubsplusos'

DEFAULT_API_KEYS = ['oqro4IKmdKVvoidOYr0pFpVddpsJZnNV', 'NAamjRQzpHhU9u2Ah0skh34shHDf2s82', 'kjQkDtmyPnK1u6uYmMalfcbG6xiRM3PR']
api_keys = DEFAULT_API_KEYS
apiSettings = __addon__.getSetting("OS_API_KEY")

if len(apiSettings) > 0:
    api_keys.insert(0, apiSettings)
OS_API_KEY = api_keys[0]

__scriptid__ = __addon__.getAddonInfo('id')

class OSDBServer:
    def __init__( self, *args, **kwargs ):
        try:
            usernameSettings = __addon__.getSetting("OSuser")
            passSettings = __addon__.getSetting("OSpass")
            username = usernameSettings if len(usernameSettings) > 0 else DEFAULT_USERNAME
            password = passSettings if len(passSettings) > 0 else DEFAULT_PASS

            payload = {
                "username": username,
                "password": password
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
                "Api-Key": OS_API_KEY
            }

            url = BASE_URL_OS_API + '/login';
            log(__name__, 'OpenSubtitles Login: url - ' + repr(url))
            #myLogger('OpenSubtitles Login: details - ' + repr(payload))
            #myLogger('OpenSubtitles Login: api - ' + repr(OS_API_KEY))

            response = requests.post(url, json=payload, headers=headers)
            response_json = response.json()

            if response.status_code == 200:
                log(__name__, 'OpenSubtitles Login: Succeeded')
                # response_json = response.json()
                log(__name__, 'OpenSubtitles Login: response json - ' + repr(response_json))

                self.osdb_token  = response_json['token']
                log(__name__, 'OpenSubtitles token: ' + repr(self.osdb_token))
            else:
                log(__name__, 'OpenSubtitles Login: Failed - status code: ' + repr (response.status_code))
                self.failedToLoginError(response_json)

        except Exception as e:
            log(__name__, 'OpenSubtitles Login error: ' + repr(e))
            self.failedToLoginError(response_json)
            pass

    def failedToLoginError(self, response_json):
        msg = ("Opensubtitles failed to login: " + repr(response_json['message'])).replace(","," - ").replace("'","")
        log(__name__, msg)
        xbmc.executebuiltin(('Notification(%s,%s,%s)' % (MyAddonName , msg, 5)))

    def searchsubtitles( self, item):
        tvshow = item['tvshow']
        season = item['season']
        episode = item['episode']
        year = item['year']
        title = item['title']

        if (hasattr(self,'osdb_token')):
            url = BASE_URL_OS_API + '/subtitles';

            headers = {
                "User-Agent": USER_AGENT,
                "Api-Key": OS_API_KEY
            }

            lang_string = ",".join(item['3let_language'])
            log(__name__, 'OS Langs: ' + repr(lang_string))

            querystring = {}
            querystring['languages'] = lang_string

            # if item['mansearch']:
            #     OS_search_string = item['mansearchstr'].replace(" ","+");
            #     log( __name__ , "Manual Search String [ %s ]" % (OS_search_string,))

            if item['imdb_id'].startswith('tt'):
                # With imdb (Can be with ot without the 'tt' prefix)
                # querystring['imdb_id'] = imdb_id
                if len(tvshow) > 0:
                # if item['dbtype'] == 'episode':
                    #################################################
                    # option 1 - TV Shows - by imdb/season/episode
                    #################################################
                    querystring['parent_imdb_id'] = item['imdb_id']
                    querystring['season_number'] = season
                    querystring['episode_number'] = episode
                else:
                    #################################################
                    # option 2 - Movies - by imdb
                    #################################################
                    querystring['imdb_id'] = item['imdb_id']

            else:
                # Without imdb
                querystring['query'] = title
                if len(tvshow) > 0:
                # if item['dbtype'] == 'episode':
                    #################################################
                    # option 3 - TV Shows - by tvshow/season/episode
                    #################################################
                    querystring['season_number'] = season
                    querystring['episode_number'] = episode
                else:
                    #################################################
                    # option 4 - Movies - by title/year
                    #################################################
                    querystring['year'] = year

            response_json_data = []

            log(__name__, "Opensubtitles SearchSubtitles querystring: " + repr(querystring))
            response = requests.get(url, headers=headers, params=querystring)
            response_json = response.json()

            log(__name__, "Opensubtitles SearchSubtitles search result: Number of pages - " + repr(response_json['total_pages']))
            for _page in range(response_json['total_pages']):
                querystring['page'] = _page + 1
                log(__name__, "Opensubtitles SearchSubtitles querystring: " + repr(querystring))
                response = requests.get(url, headers=headers, params=querystring)
                response_json = response.json()
                response_json_data.extend(response_json['data'])

            log(__name__, "Opensubtitles SearchSubtitles search result: " + repr(response_json_data))

            try:
                return response_json_data
            except:
                return []

        else:
            return []

    def download(self, ID, dest):
        if (hasattr(self,'osdb_token')):
            url = BASE_URL_OS_API + '/download';
            payload = {"file_id": int(ID)}

            apikey_index = 1
            for _apikey in api_keys:
                log(__name__, "Opensubtitles download API Key (%s)" %(apikey_index))
                apikey_index += 1

                headers = {
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Api-Key": _apikey,
                    "Authorization": "Bearer %s" %(self.osdb_token)
                }

                #try catch

                log(__name__, "Opensubtitles download payload: " + repr(payload))
                response = requests.post(url, json=payload, headers=headers)
                response_json = response.json()
                log(__name__, "Opensubtitles download result: " + repr(response_json))

                if (response.status_code == 200):

                    _filename = response_json['file_name']
                    archive_file = os.path.join(dest, _filename)

                    _url = response_json['link']
                    response = requests.get(_url)

                    subtitle_list = []
                    with open(archive_file, 'wb') as handle:
                        for block in response.iter_content(1024):
                            handle.write(block)

                    subtitle_list.append(archive_file)

                    return subtitle_list

            #If failed after all api_keys attemps
            log(__name__, 'OpenSubtitles download: Failed - status code: ' + repr (response.status_code))
            msg = "Opensubtitles download error: " + repr(response_json['message'])
            log(__name__, msg)
            xbmc.executebuiltin(('Notification(%s,%s,%s)' % (MyAddonName , msg, 5)))
            # return []

def log(module, msg):
    xbmc.log(("### [%s] - %s" % (module,msg,)),level=xbmc.LOGDEBUG )

def normalizeString(_str):
    return unicodedata.normalize('NFKD', _str).encode('ascii','ignore').decode('utf-8')
    #return _str
    #return unicodedata.normalize('NFKD', _str)
    #return unicodedata.normalize('NFKD', _str).encode('ascii','ignore')
    #return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii','ignore')

def clean_titles(item):
    try:
        if 'title' in item:
            log( __name__, "clean_title [title]")
            item['title'] = clean_title(item['title'])
        if 'tvshow' in item:
            log( __name__, "clean_title [tvshow]")
            item['tvshow'] = clean_title(item['tvshow'])
    except Exception as e:
        log( __name__, "clean_titles Error: " + repr(e))

def clean_title(text):
    try:
        log( __name__, "clean_title - before: " + repr(text))

        temp=re.sub("([\(\[]).*?([\)\]])", "\g<1>\g<2>", text)

        temp=temp.replace("(","")
        temp=temp.replace(")","")
        temp=temp.replace("[","")
        temp=temp.replace("]","")
        temp=temp.replace("1080 HD","")
        temp=temp.replace("720 HD","")

        if "  - " in temp:
            temp=temp.split("  - ")[0]

        title = path.splitext(temp)

        if len(title) > 1:
            if re.match(r'^\.[a-z]{2,4}$', title[1], re.IGNORECASE):
                text = title[0]
            else:
                text = ''.join(title)
        else:
            text = title[0]

        #text = str(text) #unicode(text, "utf-8")		# burekas fix - offline hebrew titles

        # Removes country identifier at the end
        text = re.sub(r'\([^\)]+\)\W*$', '', text).strip()

        log( __name__, "clean_title - after: " + repr(text))
        return text

    except Exception as e:
        log( __name__, "clean_title Error: " + repr(e))


def checkAndParseIfTitleIsTVshowEpisode(manualTitle):
    try:
        pattern = re.compile(r"%20|_|-|\+|\.")
        replaceWith = " "
        manualTitle = re.sub(pattern, replaceWith, manualTitle)

        matchShow = re.search(r'(?i)^(.*?)\sS\d', manualTitle)
        if matchShow == None:
            return ["NotTVShowEpisode", "0", "0",'']
        else:
            tempShow = matchShow.group(1)

        matchSnum = re.search(r'(?i)%s(.*?)E' %(tempShow+" s"), manualTitle)
        if matchSnum == None:
            return ["NotTVShowEpisode", "0", "0",'']
        else:
            tempSnum = matchSnum.group(1)

        matchEnum = re.search(r'(?i)%s(.*?)$' %(tempShow+" s"+tempSnum+"e"), manualTitle)
        if matchEnum == None:
            return ["NotTVShowEpisode", "0", "0",'']
        else:
            tempEnum = matchEnum.group(1)

        return [tempShow, tempSnum, tempEnum, 'episode']

    except Exception as err:
        log( __name__, "checkAndParseIfTitleIsTVshowEpisode error: '%s'" % err)
        return ["NotTVShowEpisode", "0", "0",'']

def searchForIMDBID(query,item):  ##### burekas
    log( __name__, "searchForIMDBID")
    log( __name__, "searchForIMDBID - item: " + repr(item))
    log( __name__, "searchForIMDBID - query: " + repr(query))

    tmdbKey = '653bb8af90162bd98fc7ee32bcbbfb3d'

    info=(PTN.parse(query))

    if item['tvshow'] and (item['dbtype'] == 'episode' or (item['season'] and item['episode'])):
        type_search='tv'
        temp_query = item["tvshow"]
        year = 0 #year = item["year"]
        url="https://api.tmdb.org/3/search/%s?api_key=%s&query=%s&language=en&append_to_response=external_ids"%(type_search,tmdbKey,quote_plus(temp_query))
        #url="https://api.tmdb.org/3/search/tv?api_key=%s&query=%s&year=%s&language=he&append_to_response=external_ids"%(tmdbKey,quote_plus(temp_query),year)
        #url='https://www.omdbapi.com/?apikey=8e4dcdac&t=%s&year=%s'%(temp_query,item["year"])

    elif info['title']: # and item['dbtype'] == 'movie':
        type_search='movie'
        temp_query = info['title'] # was item['title'] for get_TMDB_data_filtered, and 'query' for filename
        year = item["year"]
        if int(year) > 0:
            url = "https://api.tmdb.org/3/search/%s?api_key=%s&query=%s&year=%s&language=en"%(type_search,tmdbKey,quote(temp_query),year)
        else:
            url = "https://api.tmdb.org/3/search/%s?api_key=%s&query=%s&language=en"%(type_search,tmdbKey,quote(temp_query))

    filename = 'subs.search.tmdb.%s.%s.%s.json'%(type_search,lowercase_with_underscores(temp_query),year)
    #json_results = get_TMDB_data_popularity_and_votes_sorted(url,filename)

    json_results = get_TMDB_data_filtered(url,filename,temp_query,type_search,year)

    try:
        tmdb_id = int(json_results[0]["id"])
    except Exception as e:
        log( __name__, "searchForIMDBID (%s_1) Error: [%s]" % (type_search,e))
        tmdb_id = ''
        pass
        # return "0"

    if tmdb_id == '':
        if item['imdb_id'] != '':
            tmdb_id = item['imdb_id']
        else:
            return "0"

    filename = 'subs.search.tmdb.fulldata.%s.%s.json'%(type_search,tmdb_id)
    url = "https://api.tmdb.org/3/%s/%s?api_key=%s&language=en&append_to_response=external_ids"%(type_search,tmdb_id,tmdbKey)
    #url = "https://api.themoviedb.org/3/%s/%s?api_key=%s&language=en-US&append_to_response=external_ids"%(type_search,tmdb_id,tmdbKey)
    log( __name__, "searchTMDB fulldata id: %s" % url)

    json = caching_json(filename,url)

    try:
        imdb_id = json['external_ids']["imdb_id"]
    except Exception as e:
        log( __name__, "searchForIMDBID (%s_2) Error: [%s]" % (type_search,e))
        return "0"

    return imdb_id

def get_TMDB_data_popularity_and_votes_sorted(url,filename):    ##### burekas
    log( __name__ , "searchTMDB: %s" % url)
    json = caching_json(filename,url)
    json_results = json["results"]
    log( __name__ , "get_TMDB_data_popularity_and_votes_sorted: json_results - " + repr(json_results))
    # 1st priority: popularity
    # 2nd priority: vote_count
    json_results.sort(key = lambda x:(x["popularity"],x["vote_count"]), reverse=True)
    # json_results = sorted(json_results, key = lambda x:(x["popularity"],x["vote_count"]), reverse=True)
    # json_results.sort(key = lambda x:x["popularity"], reverse=True)
    # json_results.sort(key = lambda x:x["vote_count"], reverse=True)
    log( __name__ , "get_TMDB_data_popularity_and_votes_sorted: json_results sorted - " + repr(json_results))

    return json_results

def get_TMDB_data_filtered(url,filename,query,type,year=0):    ##### burekas
    log( __name__ , "searchTMDB: %s" % url)
    log( __name__ , "query filtered: %s" % query)
    json = caching_json(filename,url)
    json_results = json["results"]
    log( __name__ , "get_TMDB_data_filtered: json_results - " + repr(json_results))
    if type=='tv':
        json_results.sort(key = lambda x:x["name"]==query, reverse=True)
    else:
        if int(year) > 0:
            json_results.sort(key = lambda x:(x["title"]==query,str(year) in str(x["release_date"])), reverse=True)
            #json_results.sort(key = lambda x:(x["title"]==query), reverse=True)
        else:
            json_results.sort(key = lambda x:x["title"]==query, reverse=True)
    log( __name__ , "get_TMDB_data_filtered: json_results sorted - " + repr(json_results))

    return json_results

def caching_json(filename, url):   ####### burekas
    import requests

    if (__addon__.getSetting( "json_cache" ) == "true"):
        json_file = path.join(__temp__, filename)
        if not path.exists(json_file) or not path.getsize(json_file) > 20 or (time()-path.getmtime(json_file) > 30*60):
            data = requests.get(url, verify=False)
            open(json_file, 'wb').write(data.content)
        if path.exists(json_file) and path.getsize(json_file) > 20:
            with open(json_file,'r',encoding='utf-8') as json_data:
                json_object = load(json_data)
            return json_object
        else:
            return 0

    else:
        try:
          json_object = requests.get(url).json()
        except:
          json_object = {}
          pass
        return json_object

def get_now_played():
    """
    Get info about the currently played file via JSON-RPC

    :return: currently played item's data
    :rtype: dict
    """
    request = dumps({
        'jsonrpc': '2.0',
        'method': 'Player.GetItem',
        'params': {
            'playerid': 1,
            'properties': ['showtitle', 'season', 'episode']
         },
        'id': '1'
    })
    item = loads(xbmc.executeJSONRPC(request))['result']['item']
    item['file'] = xbmc.Player().getPlayingFile()  # It provides more correct result
    return item

def get_more_data(filename):
    title, year = xbmc.getCleanMovieTitle(filename)
    log( __name__ , "CleanMovieTitle: title - %s, year - %s " %(title, year))
    tvshow=' '
    season=0
    episode=0
    try:
        yearval = int(year)
    except ValueError:
        yearval = 0

    patterns = [
                '\WS(?P<season>\d\d)E(?P<episode>\d\d)',
                '\W(?P<season1>\d)x(?P<episode1>\d\d)'
                ]

    for pattern in patterns:
        pattern = r'%s' % pattern
        match = re.search(pattern, filename, flags=re.IGNORECASE)
        log( __name__ , "regex match: " + repr(match))

        if match is None:
            continue
        else:
            title = title[:match.start('season') - 1].strip()
            season = match.group('season').lstrip('0')
            episode = match.group('episode').lstrip('0')
            log( __name__ , "regex parse: title = %s , season = %s, episode = %s " %(title,season,episode))
            return title,yearval,season,episode

    return title,yearval,season,episode

def is_local_file_tvshow(item):
    return item["title"] and item["year"]==0

def lowercase_with_underscores(_str):
    return unicodedata.normalize('NFKD', _str).encode('utf-8','ignore').decode('utf-8')
    #return unicodedata.normalize('NFKD', (str)).encode('utf-8', 'ignore')

def is_to_check_percent(item):
    # Check % only when player is playing
    # or not playing and library based on local file:
    # Without 'strm' which is video addon file or 'plugin://' which is video addon menu
    # Or not Manual Search
    return ((xbmc.Player().isPlaying()
            or (not xbmc.Player().isPlaying()
                and (not any(s in item['full_path'] for s in ['strm','plugin://']))))
            and ('mansearch' in item and item['mansearch'] == False))

def orginaize_video_filename_for_compare(_text, _index):
    text = remove_brackets_content_from_text(_text)
    text = replace_chars_from_text(text)
    text = (text.replace(".avi","").replace(".mp4","").replace(".mkv",""))
    log(__name__, "Video source %s for compare: %s" %(_index, text))

    _array = (text.split("."))
    log(__name__, "Video source %s for compare (array): %s" %(_index, _array))

    return _array

def remove_brackets_content_from_text(text):
    # # Count the number of bracket pairs in the text
    # bracket_count = text.count('[')
    # # If there are more than one pair of brackets, remove the last pair and their content
    # if bracket_count > 1:

    # Find the last occurrence of '[' and ']'
    last_open_bracket = text.rfind('[')
    last_close_bracket = text.rfind(']')

    if last_open_bracket != -1 and last_close_bracket != -1 and last_open_bracket < last_close_bracket:
        # Remove the last set of brackets and their content
        text = text[:last_open_bracket] + text[last_close_bracket + 1:]

    return text

def replace_chars_from_text(_text):
    text = (_text.strip()
            .replace("_",".").replace(" ",".")
            .replace("/",".")
            .replace(":","")
            .replace("-",".").replace("+",".")
            .replace("[",".").replace("]",".")
            .replace("(",".").replace(")","."))

    return text

def calc_sub_percent_sync(sub_filename,array_original):
    #json_value is the subtitle filename
    #array_original is the video/source filename

    release_names=['bluray','blu-ray','bdrip','brrip','brip',
                   'hdtv','hdtvrip','pdtv','tvrip','hdrip','hd-rip','hc',
                   'web','web-dl','web dl','web-dlrip','webrip','web-rip',
                   'dvdr','dvd-r','dvd-rip','dvdrip','cam','hdcam','cam-rip',
                   'screener','dvdscr','dvd-full',
                   'tc','telecine','ts','hdts','telesync']

    resolutions = ['720p','1080p','1440p','2160p','2k','4320p','4k']

    quality = xbmc.getInfoLabel("VideoPlayer.VideoResolution")+'p'

    text = sub_filename

    text = replace_chars_from_text(text)
    text = (text.replace(".srt",''))
    # text = remove_brackets_content_from_text(text)
    array_subs = (text.split("."))
    ##array_subs.pop(0)

    #remove empty items from sub array
    array_subs = [element.strip().lower() for element in array_subs if element != '']
    #array_subs=[str(x).lower() for x in array_subs if x != '']

    # remove language code if exist
    if array_subs[-1].lower() != 'hi' and len(array_subs[-1]) == 2:
        array_subs.pop(-1)

    # fix for 'Opensubtitles" subs - remove 'cc' addition ('hi', 'no hi') if exist
    if array_subs[-1].lower()=='hi' and array_subs[-2].lower()=='no':
        array_subs.pop(-1)
        array_subs.pop(-1)
    #array_subs=[element for element in array_subs if element not in ('hi')] # was ('-','no','hi')

    #log(__name__, "Video source array before compare: %s" %array_original)
    #log(__name__, "Subtitle array before compare: %s" %array_subs)

    array_original=[element.strip().lower() for element in array_original if element != '']
    #array_original=[element.strip().lower() for element in array_original]
    #array_original=[str(x).lower() for x in array_original if x != '']

    #----------------------------------------------------------------------------------#
    # 1st priority "release name" (+3 if "release name" are equal)
    # 2nd priority "release type" (+2 if "release name" and "release type" are equal)
    # 3th priority "resolution"   (+1 if "release name" and "release type" and "resolution" are equal)
    #----------------------------------------------------------------------------------#

    # Give "release name" more weight (x3) to the ratio score of the compare
    # 1st priority "release name"
    #log(__name__, "Video source release: %s" %array_original[-1])
    #log(__name__, "Subtitle release: %s" %array_subs[-1])
    release_name_position = -2 if array_subs[-1].lower()=='hi' else -1
    sub_release_name = array_subs[release_name_position]
    video_release_name = array_original[-1]
    if sub_release_name.lower() == video_release_name.lower():
        for i in range(3):
            array_subs.append(sub_release_name)
            array_original.append(video_release_name)

        # Give "release type" more weight (x2) to the ratio score of the compare
        # 2nd priority "release type"
        sub_release_type = list(set(array_subs).intersection(release_names))
        video_release_type = list(set(array_original).intersection(release_names))
        if len(sub_release_type) > 0 and len(video_release_type) > 0 and sub_release_type[-1] == video_release_type[-1]:
            for i in range(2):
                array_original.append(video_release_type[-1])
                array_subs.append(sub_release_type[-1])

            # 3th priority "resolution"
            video_quality = list(set(array_original).intersection(resolutions))
            sub_quality = list(set(array_subs).intersection(resolutions))
            if len(video_quality) > 0 and len(sub_quality) > 0 and sub_quality[-1] == video_quality[-1]:
                for i in range(1):
                    array_original.append(video_quality[-1])
                    array_subs.append(sub_quality[-1])
                    #wlog("Video source quality: %s" %repr(video_quality[0]))
                    #wlog("Subtitle quality: %s" %repr(sub_quality[0]))

    #wlog("Video source array for compare: %s" %array_original)
    #wlog("Subtitle array for compare: %s" %array_subs)
    precent = similar(array_original,array_subs)
    return precent

def similar(w1, w2):
    from difflib import SequenceMatcher

    s = SequenceMatcher(None, w1, w2)
    return int(round(s.ratio()*100))

def prepare_video_filename(filename):
    clean_filename = unquote(filename)
    clean_filename = clean_filename.split("?")
    clean_filename = path.basename(clean_filename[0])[:-4]
    return clean_filename

def build_subs_list_with_percentage(json, item):
    subs = []

    video_player_title = xbmc.getInfoLabel("VideoPlayer.OriginalTitle") if item['episode'] == 0 else xbmc.getInfoLabel("VideoPlayer.TVShowTitle")
    array_original = orginaize_video_filename_for_compare(item['file_original_path'], 1)
    array_original2 = orginaize_video_filename_for_compare(video_player_title, 2)

    if json != 0:
        check_sub_sync = is_to_check_percent(item)

        for json_item in json:
            item_data = json_item['attributes']
            sub = {}
            sub['title'] = item_data['files'][0]['file_name']
            sub['LanguageName'] = xbmc.convertLanguage(item_data['language'], xbmc.ENGLISH_NAME)
            sub["ISO639"] = item_data['language']
            sub["SubHearingImpaired"] = "true" if item_data["hearing_impaired"] == True else "false"
            sub["IDSubtitleFile"] = str(item_data['files'][0]['file_id'])
            sub["SubFileName"] = item_data['files'][0]['file_name']

            if check_sub_sync:
                percent = calc_sub_percent_sync(sub['title'], array_original) if len(array_original) > 1 else 0
                percent2 = calc_sub_percent_sync(sub['title'], array_original2) if len(array_original2) > 1 else 0

                if percent2 > percent:
                    percent = percent2

                sub['percent'] = percent
                sub['score'] = str(round(float(percent / 20)))
                sub['sub_percent'] = str(percent) + "% | "
                sub['synced'] = "true" if percent > 80 else "false"
            else:
                percent = 0
                sub['percent'] = percent
                sub['score'] = ''
                sub['sub_percent'] = ''
                sub['synced'] = "false"

            subs.append(sub)

        # Sort list by sync percentages
        subs = sorted(subs, key=lambda x: (x['LanguageName'],x['percent']), reverse=True)
        log( __name__, "search_data sorted: %s" %repr(subs))

    return subs

def generate_subs_results_list(subs):
    for item_data in subs:
        ## hack to work around issue where Brazilian is not found as language in XBMC
        if item_data["LanguageName"] == "Brazilian":
            item_data["LanguageName"] = "Portuguese (Brazil)"

    #   if ((item['season'] == item_data['SeriesSeason'] and
    #       item['episode'] == item_data['SeriesEpisode']) or
    #       (item['season'] == 0 and item['episode'] == 0) or
    #       (item['season'] == '' and item['episode'] == '') ## for file search, season and episode == ""
    #      ):

        listitem = ListItem(label          = item_data["LanguageName"],
                            label2         = str(item_data['sub_percent'] + item_data['title'])
                            )
        listitem.setArt({'icon': item_data['score'],
                        'thumb': item_data["ISO639"]}
                        )

        listitem.setProperty( "sync", item_data["synced"] )
        listitem.setProperty( "hearing_imp", item_data["SubHearingImpaired"] )
        url = "plugin://%s/?action=&ID=%s&filename=%s" % (__scriptid__,
                                                        item_data["IDSubtitleFile"],
                                                        item_data["SubFileName"]
                                                        )

        addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

def arrange_subs_results(item, json):
    if json != 0:
        subs = build_subs_list_with_percentage(json, item)
        generate_subs_results_list(subs)