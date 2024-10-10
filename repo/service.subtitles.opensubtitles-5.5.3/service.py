# -*- coding: utf-8 -*-

import os
import shutil
import sys
import urllib
import xbmc
import xbmcaddon
import xbmcgui,xbmcplugin
import xbmcvfs
import uuid
import json

if sys.version_info[0] == 2:
    p2 = True
else:
    unicode = str
    p2 = False

from resources.lib.dualsubs import mergesubs

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

try:
    translatePath = xbmcvfs.translatePath
except AttributeError:
    translatePath = xbmc.translatePath

__cwd__        = translatePath( __addon__.getAddonInfo('path') )
if p2:
    __cwd__ = __cwd__.decode("utf-8")

__profile__    = translatePath( __addon__.getAddonInfo('profile') )
if p2:
    __profile__ = __profile__.decode("utf-8")

__resource__   = translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
if p2:
    __resource__ = __resource__.decode("utf-8")

__temp__       = translatePath( os.path.join( __profile__, 'temp', '') )
if p2:
    __temp__ = __temp__.decode("utf-8")

__msg_box__    = xbmcgui.Dialog()

if xbmcvfs.exists(__temp__):
  shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

sys.path.append (__resource__)

from OSUtilities import OSDBServer, log, hashFile, normalizeString

try:
    from urllib.parse import unquote
    from urllib.parse import quote
except:
    from urllib import unquote
    from urllib import quote

def Search( item ):
  search_data = []
  try:
    search_data = OSDBServer().searchsubtitles(item)
  except Exception as e:
    log( __name__, "failed to connect to service for subtitle search (%s)" % str(e))
    xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__ , __language__(32001))))
    return

  if search_data != None:
    search_data.sort(key=lambda x: [not x['MatchedBy'] == 'moviehash',
				     not os.path.splitext(x['SubFileName'])[0] == os.path.splitext(os.path.basename(unquote(item['file_original_path'])))[0],
				     not normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")).lower() in x['SubFileName'].replace('.',' ').lower(),
				     not x['LanguageName'] == PreferredSub])
    listitems=[]
    for item_data in search_data:
      ## hack to work around issue where Brazilian is not found as language in XBMC
      if item_data["LanguageName"] == "Brazilian":
        item_data["LanguageName"] = "Portuguese (Brazil)"

      if ((item['season'] == item_data['SeriesSeason'] and
          item['episode'] == item_data['SeriesEpisode']) or
          (item['season'] == "" and item['episode'] == "") ## for file search, season and episode == ""
         ):
        if p2:
          listitem = xbmcgui.ListItem(label          = item_data["LanguageName"],
                                      label2         = item_data["SubFileName"],
                                      iconImage      = str(int(round(float(item_data["SubRating"])/2))),
                                      thumbnailImage = item_data["ISO639"]
                                      )
        else:
          listitem = xbmcgui.ListItem(label          = item_data["LanguageName"],
                                      label2         = item_data["SubFileName"]
                                      )
          listitem.setArt( { "icon": str(int(round(float(item_data["SubRating"])/2))), "thumb" : item_data["ISO639"] } )

        listitem.setProperty( "sync", ("false", "true")[str(item_data["MatchedBy"]) == "moviehash"] )
        listitem.setProperty( "hearing_imp", ("false", "true")[int(item_data["SubHearingImpaired"]) != 0] )
        listitems.append(listitem)
        if(__addon__.getSetting('dualsub_enable') != 'true'):
          url = "plugin://%s/?action=download&link=%s&ID=%s&filename=%s&format=%s" % (__scriptid__,
                                                                            item_data["ZipDownloadLink"],
                                                                            item_data["IDSubtitleFile"],
                                                                            item_data["SubFileName"],
                                                                            item_data["SubFormat"]
                                                                            )

          xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

    if(__addon__.getSetting('dualsub_enable') == 'true'):
      while True:
        ret = __msg_box__.multiselect(__language__(32607), [i for i in listitems],useDetails=True)
        if ret and len(ret) > 2:
          __msg_box__.ok('', __language__(32608))
        else:
          break
      if ret and len(ret) > 0:
        subs=[]
        url=''
        for sub in ret:
          subs.append({'ID':search_data[sub]['IDSubtitleFile'],
            'link':search_data[sub]['ZipDownloadLink'],
            'filename':search_data[sub]['SubFileName'],
            'format':search_data[sub]['SubFormat']})
          if len(ret) < 2:
            url = "plugin://%s/?action=downloadstd&link=%s&ID=%s&filename=%s&format=%s" % (__scriptid__,
                                                                              search_data[sub]['ZipDownloadLink'],
                                                                              search_data[sub]['IDSubtitleFile'],
                                                                              search_data[sub]['SubFileName'],
                                                                              search_data[sub]['SubFormat']
                                                                              )

        payload=json.dumps(subs[:2])
        payload=quote(payload)

        if len(subs) < 2:
          listitem = xbmcgui.ListItem(label2=__language__(32602))
          xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

          listitem = xbmcgui.ListItem(label2=__language__(32603))
          url = "plugin://%s/?action=download&payload=%s"% (__scriptid__,payload)
          xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
        else:
          listitem = xbmcgui.ListItem(label2=__language__(32604))
          url = "plugin://%s/?action=download&payload=%s"% (__scriptid__,payload)
          xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

          listitem = xbmcgui.ListItem(label2=__language__(32605))
          url = "plugin://%s/?action=downloadswap&payload=%s"% (__scriptid__,payload)
          xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

        listitem = xbmcgui.ListItem(label2=__language__(32606))
        url = "plugin://%s/?action=settings"% (__scriptid__)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

def Download(id,url,format,stack=False):
  subtitle_list = []
  exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass" ]
  if stack:         ## we only want XMLRPC download if movie is not in stack,
                    ## you can only retreive multiple subs in zip
    result = False
  else:
    subtitle = os.path.join(__temp__, "%s.%s" %(str(uuid.uuid4()), format))
    try:
      result = OSDBServer().download(id, subtitle)
    except:
      log( __name__, "failed to connect to service for subtitle download")
      return subtitle_list
  if not result:
    log( __name__,"Download Using HTTP")
    zip = os.path.join( __temp__, "OpenSubtitles.zip")
    f = urllib.urlopen(url)
    if not os.path.exists( __temp__ ):
        os.mkdir( __temp__, mode=0o775 )
    with open(zip, "wb") as subFile:
      subFile.write(f.read())
    subFile.close()
    xbmc.sleep(500)
    xbmc.executebuiltin(('Extract("%s","%s")' % (zip,__temp__,)).encode('utf-8'), True)
    for file in xbmcvfs.listdir(zip)[1]:
      file = os.path.join(__temp__, file)
      if (os.path.splitext( file )[1] in exts):
        subtitle_list.append(file)
  else:
    subtitle_list.append(subtitle)

  if xbmcvfs.exists(subtitle_list[0]):
    return subtitle_list

def takeTitleFromFocusedItem():
    labelMovieTitle = xbmc.getInfoLabel("ListItem.OriginalTitle")
    labelYear = xbmc.getInfoLabel("ListItem.Year")
    labelTVShowTitle = xbmc.getInfoLabel("ListItem.TVShowTitle")
    labelSeason = xbmc.getInfoLabel("ListItem.Season")
    labelEpisode = xbmc.getInfoLabel("ListItem.Episode")
    labelType = xbmc.getInfoLabel("ListItem.DBTYPE")  #movie/tvshow/season/episode
    isItMovie = labelType == 'movie' or xbmc.getCondVisibility("Container.Content(movies)")
    isItEpisode = labelType == 'episode' or xbmc.getCondVisibility("Container.Content(episodes)")

    title = 'SearchFor...'
    if isItMovie and labelMovieTitle and labelYear:
        title = labelMovieTitle + " " + labelYear
    elif isItEpisode and labelTVShowTitle and labelSeason and labelEpisode:
        title = ("%s S%.2dE%.2d" % (labelTVShowTitle, int(labelSeason), int(labelEpisode)))

    return title

def get_params(string=""):
  param=[]
  if string == "":
    paramstring=sys.argv[2]
  else:
    paramstring=string
  if len(paramstring)>=2:
    params=paramstring
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

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
  log( __name__, "action '%s' called" % params['action'])
  item = {}

  if xbmc.Player().isPlaying():
    item['temp']               = False
    item['rar']                = False
    item['mansearch']          = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    item['file_original_path'] = xbmc.Player().getPlayingFile()                                 # Full path of a playing file
    item['3let_language']      = [] #['scc','eng']

  else:
    item['temp'] = False
    item['rar'] = False
    item['mansearch'] = False
    item['year'] = ""
    item['season'] = ""
    item['episode'] = ""
    item['tvshow'] = ""
    item['title'] = takeTitleFromFocusedItem()
    item['file_original_path'] = ""
    item['3let_language'] = []

  PreferredSub = params.get('preferredlanguage')

  if 'searchstring' in params:
    item['mansearch'] = True
    item['mansearchstr'] = params['searchstring']

  for lang in unquote(params['languages']).split(","):
    if lang == "Portuguese (Brazil)":
      lan = "pob"
    elif lang == "Greek":
      lan = "ell"
    else:
      lan = xbmc.convertLanguage(lang,xbmc.ISO_639_2)

    item['3let_language'].append(lan)

  if item['title'] == "":
    log( __name__, "VideoPlayer.OriginalTitle not found")
    item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

  if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
    item['season'] = "0"                                                          #
    item['episode'] = item['episode'][-1:]

  if ( item['file_original_path'].find("http") > -1 ):
    item['temp'] = True

  elif ( item['file_original_path'].find("rar://") > -1 ):
    item['rar']  = True
    item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

  elif ( item['file_original_path'].find("stack://") > -1 ):
    stackPath = item['file_original_path'].split(" , ")
    item['file_original_path'] = stackPath[0][8:]

  Search(item)

elif params['action'] == 'downloadstd' or params['action'] == 'download' or params['action'] == 'downloadswap':
  if(__addon__.getSetting('dualsub_enable') == 'true') and params['action'] != 'downloadstd':
    payload=json.loads(unquote(params['payload']))
    subs=[]
    for sub in payload:
      subs.append(Download(sub["ID"], sub["link"],sub["format"])[0])
    if params['action'] == 'downloadswap':
      subs.reverse()
    if(__addon__.getSetting('dualsub_swap') == 'true'):
      subs.reverse()
    finalfile = mergesubs(subs)
    listitem = xbmcgui.ListItem(label=finalfile)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=finalfile,listitem=listitem,isFolder=False)
  else:
    subs = Download(params["ID"], params["link"],params["format"])
    for sub in subs:
      listitem = xbmcgui.ListItem(label=sub)
      xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)

elif params['action'] == 'settings':
  __addon__.openSettings()
  __msg_box__.ok('', __language__(32530))

xbmcplugin.endOfDirectory(int(sys.argv[1]))
