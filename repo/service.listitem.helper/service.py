# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcvfs

import arrow
from simplecache import use_cache, SimpleCache
from datetime import datetime

import xbmcgui
import simplejson
import sys

import xml.etree.ElementTree as ET

# Script constants
__addon__      = xbmcaddon.Addon()
__addonid__    = __addon__.getAddonInfo('id')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString
__cwd__        = __addon__.getAddonInfo('path')

def log(txt):
    if isinstance (txt,str):
        if sys.version_info.major == 2:# Python 2
            txt = txt.decode("utf-8")
        else:# Python 3
            txt = txt
    if sys.version_info.major == 2:# Python 2
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)
    else:# Python 3
        message = str(u'%s: %s' % (__addonid__, txt))
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)



class Main:
    
    api_key = None
    cache = None
    
    _addon, _close_called, _omdb, _tmdb, _mdblist = [None] * 5


    def __init__(self, simplecache=None):
        log("version %s started" % __version__)
        
        self.previousitem = ""
        self.selecteditem = ""
        self.dbid = ""
        self.dbype = ""
        self.imdbnumber = ""
        self.imdbnumber_isvalid = False
        self.imdbnumber_corrected = ""
        self.imdbnumber_corrected_isvalid = False
        self.rating = ""
        self.itempath = ""
        self.itemfile = ""
        self.itemfilenameandpath = ""
        
        
        
        self.BuildVersionStr = str(xbmc.getInfoLabel('System.BuildVersion'))
        self.BuildVersionIsBetterUI = self.BuildVersionStr.find("BetterUI") >= 0
        
        
        
        self.videolibrary_itemseparator_default          = ' / ' if not self.BuildVersionIsBetterUI else ' · '
        self.videolibrary_itemseparator_advancedsettings = self.videolibrary_itemseparator_default
        
        self.videolibrary_itemseparator_fallback         = ' / ' if self.BuildVersionIsBetterUI else ""
        
        self.videolibrary_itemseparator_replacewith      = ' · '
        
        
        
        # check for potential advancedsettings.xml user value of "videolibrary.itemseparator"
        
        xmlpath = "special://userdata/advancedsettings.xml"
        if sys.version_info.major == 2:# Python 2
            xmlfile = xbmc.translatePath(xmlpath).decode("utf-8")
        else:
            xmlfile = xbmcvfs.translatePath(xmlpath)
        
        if xmlfile and xbmcvfs.exists(xmlfile):
            try:
                tree = ET.parse(xmlfile)
                root = tree.getroot()
                
                if tree and root:
                    for itemseparator in root.findall("./videolibrary/itemseparator"):
                        if itemseparator.text:
                            self.videolibrary_itemseparator_advancedsettings = str(itemseparator.text)
                            break
            except:
                log('advancedsettings.xml parsing error')
        
        
        
        self.studio = ""
        self.genre = ""
        self.director = ""
        self.writer = ""
        
        self.localratings = ""
        
        self.cache = SimpleCache()
        
        self.monitor = xbmc.Monitor()
        self.run_service()


    def run_service(self):
        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(0.7):
                break
            
            IsScrolling = xbmc.getCondVisibility("Container.Scrolling") or xbmc.getCondVisibility("Container.OnPrevious") or xbmc.getCondVisibility("Container.OnNext") or xbmc.getCondVisibility("Container.OnScrollPrevious") or xbmc.getCondVisibility("Container.OnScrollNext")
            
            if not IsScrolling:
                
                IsVideoLibraryView = xbmc.getCondVisibility("Window.IsActive(Videos)") and xbmc.getCondVisibility("Window.Is(Videos)")
                IsMovieInfoDialogView = xbmc.getCondVisibility("Window.IsActive(MovieInformation)") and xbmc.getCondVisibility("Window.Is(MovieInformation)")
                
                IsMovieContent = xbmc.getCondVisibility("Container.Content(Movies)")
                IsTvShowsContent = xbmc.getCondVisibility("Container.Content(TvShows)")
                IsSeasonsContent = xbmc.getCondVisibility("Container.Content(Seasons)")
                IsEpisodesContent = xbmc.getCondVisibility("Container.Content(Episodes)")
                
                IsValidContent = IsMovieContent or IsTvShowsContent or IsSeasonsContent or IsEpisodesContent
                
                IsAddon = xbmc.getInfoLabel("Container.PluginName") or xbmc.getInfoLabel("Container.FolderPath").startswith('plugin://')
            
            tmpCheckCondition = not IsScrolling and IsValidContent and (IsVideoLibraryView or IsMovieInfoDialogView) and not IsAddon
            
            if tmpCheckCondition:
                
                self.selecteditem = xbmc.getInfoLabel("ListItem.DBID")
                
                if (self.selecteditem and self.selecteditem != self.previousitem):
                    self.previousitem = self.selecteditem
                    
                    tmpDBTYPE = xbmc.getInfoLabel("ListItem.DBTYPE")
                    tmpIMDBNumber = xbmc.getInfoLabel("ListItem.IMDBNumber")
                    
                    IsDbTypeMovie = tmpDBTYPE == 'movie' and not xbmc.getCondVisibility("ListItem.IsFolder") and tmpIMDBNumber
                    IsDbTypeTvShow = tmpDBTYPE == 'tvshow' and tmpIMDBNumber
                    IsDbTypeSeason = tmpDBTYPE == 'season'
                    IsDbTypeEpisode = tmpDBTYPE == 'episode'
                    
                    IsValidDbType = IsDbTypeMovie or IsDbTypeTvShow or IsDbTypeSeason or IsDbTypeEpisode
                    
                    if (IsValidDbType):
                        
                        if IsDbTypeSeason and xbmc.getInfoLabel("ListItem.Label") == xbmc.getLocalizedString(20366) and xbmc.getInfoLabel("ListItem.TvShowDBID"):
                            self.dbid = xbmc.getInfoLabel("ListItem.TvShowDBID")
                        else:
                            self.dbid = xbmc.getInfoLabel("ListItem.DBID")
                        
                        self.dbtype = tmpDBTYPE
                        self.imdbnumber = xbmc.getInfoLabel("ListItem.IMDBNumber")
                        self.imdbnumber_corrected = xbmc.getInfoLabel("ListItem.IMDBNumber")
                        self.imdbnumber_isvalid = False
                        self.imdbnumber_corrected_isvalid = False
                        self.rating = xbmc.getInfoLabel("ListItem.rating")
                        self.rating = self.rating if not self.rating.isspace() else None
                        
                        
                        
                        self.localratings = ""
                        
                        
                        if IsDbTypeMovie:
                            jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":'+str(self.dbid)+',"properties":["ratings"]},"id":1}')
                            
                            jsonResultHasRatings = False
                            
                            if sys.version_info.major == 2:# Python 2
                                jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore')
                            jsonQuery = simplejson.loads(jsonQuery)
                            
                            jsonResultHasRatings = 'result' in jsonQuery and 'moviedetails' in jsonQuery['result'] and 'ratings' in jsonQuery['result']['moviedetails']
                            
                            if jsonResultHasRatings:
                                self.localratings = jsonQuery['result']['moviedetails']['ratings']
                        
                        
                        if IsDbTypeMovie and self.imdbnumber:
                            
                            # Validate self.imdbnumber_corrected. ListItem.IMDBNumber sometimes wrong (some scraper wrongly put their own id into this property)
                            # tt, nm, co, ev, ch, ni
                            isValidIMDBNumber = self.imdbnumber_corrected.startswith('tt') or self.imdbnumber_corrected.startswith('nm') or self.imdbnumber_corrected.startswith('co') or self.imdbnumber_corrected.startswith('ev') or self.imdbnumber_corrected.startswith('ch') or self.imdbnumber_corrected.startswith('ni')
                            
                            if isValidIMDBNumber:
                                self.imdbnumber_isvalid = True
                                self.imdbnumber_corrected_isvalid = True
                            
                            if not isValidIMDBNumber:
                                
                                jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":'+str(self.dbid)+',"properties":["uniqueid"]},"id":1}')
                                if sys.version_info.major == 2:# Python 2
                                    jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore')
                                jsonQuery = simplejson.loads(jsonQuery)
                                
                                jsonResultHasUniqueIds = False
                                jsonResultHasUniqueIdImdb = False
                                jsonResultHasUniqueIdUnknown = False
                                
                                # Check if result contains uniqueid as expected
                                jsonResultHasUniqueIds = 'result' in jsonQuery and 'moviedetails' in jsonQuery['result'] and 'uniqueid' in jsonQuery['result']['moviedetails']
                                
                                # only process if uniqueids found at all
                                if jsonResultHasUniqueIds:
                                    # Check if result contains uniqueid['imdb'] as hoped
                                    jsonResultHasUniqueIdImdb = 'imdb' in jsonQuery['result']['moviedetails']['uniqueid']
                                    
                                    if jsonResultHasUniqueIdImdb:
                                        self.imdbnumber_corrected = str(jsonQuery['result']['moviedetails']['uniqueid']['imdb'])
                                        self.imdbnumber_corrected_isvalid = True
                                    else:
                                        jsonResultHasUniqueIdUnknown = 'unknown' in jsonQuery['result']['moviedetails']['uniqueid']
                                        if jsonResultHasUniqueIdUnknown:
                                            tempImdbOld = self.imdbnumber_corrected
                                            self.imdbnumber_corrected = str(jsonQuery['result']['moviedetails']['uniqueid']['unknown'])
                                            
                                            # Validate self.imdbnumber_corrected again
                                            isValidIMDBNumber = self.imdbnumber_corrected.startswith('tt') or self.imdbnumber_corrected.startswith('nm') or self.imdbnumber_corrected.startswith('co') or self.imdbnumber_corrected.startswith('ev') or self.imdbnumber_corrected.startswith('ch') or self.imdbnumber_corrected.startswith('ni')
                                            
                                            if isValidIMDBNumber:
                                                self.imdbnumber_corrected_isvalid = True
                                                pass
                                            else:
                                                # restore initial value because correct failed
                                                self.imdbnumber_corrected = tempImdbOld
                                                del tempImdbOld
                                        else:
                                            pass
                                
                                del jsonResultHasUniqueIds
                                del jsonResultHasUniqueIdImdb
                                del jsonResultHasUniqueIdUnknown
                        
                        
                        
                        self.itempath = ""
                        self.itemfile = ""
                        self.itemfilenameandpath = ""
                        self.studio = ""
                        self.genre = ""
                        self.director = ""
                        self.writer = ""
                        
                        try:
                            InfoLabel = xbmc.getInfoLabel("ListItem.Path")
                            self.itempath = InfoLabel if InfoLabel else ""
                            
                            InfoLabel = xbmc.getInfoLabel("ListItem.FileName")
                            self.itemfile = InfoLabel if InfoLabel else ""
                            
                            InfoLabel = xbmc.getInfoLabel("ListItem.FileNameAndPath")
                            self.itemfilenameandpath = InfoLabel if InfoLabel else ""
                            
                            InfoLabel = xbmc.getInfoLabel("ListItem.Studio")
                            self.studio = InfoLabel if InfoLabel else ""
                            
                            InfoLabel = xbmc.getInfoLabel("ListItem.Genre")
                            self.genre = InfoLabel if InfoLabel else ""
                            
                            InfoLabel = xbmc.getInfoLabel("ListItem.Director")
                            self.director = InfoLabel if InfoLabel else ""
                            
                            InfoLabel = xbmc.getInfoLabel("ListItem.Writer")
                            self.writer = InfoLabel if InfoLabel else ""
                            
                        except:
                            pass
                        
                        self.set_helper_values()
                        
            else:
                my_container_id = xbmcgui.Window(10000).getProperty('ListItemHelper.WidgetContainerId')
                my_container_window = xbmcgui.Window(10000).getProperty('ListItemHelper.WidgetContainerWindowName')
                
                IsScrollingWidget = xbmc.getCondVisibility("Container("+my_container_id+").Scrolling") or xbmc.getCondVisibility("Container("+my_container_id+").OnPrevious") or xbmc.getCondVisibility("Container("+my_container_id+").OnNext") or xbmc.getCondVisibility("Container("+my_container_id+").OnScrollPrevious") or xbmc.getCondVisibility("Container("+my_container_id+").OnScrollNext")
                
                if not IsScrolling and not IsScrollingWidget:
                    
                    ContainerParentWindowActive = xbmc.getCondVisibility("Window.IsActive("+my_container_window+")") and xbmc.getCondVisibility("Window.Is("+my_container_window+")")
                    ContainerCheckedAndFocus = my_container_id and my_container_window and xbmc.getCondVisibility("Control.HasFocus("+my_container_id+")")
                    IsVideoLibraryOrMovieInfoDialogView = xbmc.getCondVisibility("Window.IsActive(Videos)") or xbmc.getCondVisibility("Window.IsActive(MovieInformation)")
                    
                    IsAddon = xbmc.getInfoLabel("Container("+my_container_id+").PluginName") or xbmc.getInfoLabel("Container("+my_container_id+").FolderPath").startswith('plugin://')
                
                tmpCheckCondition = not IsScrolling and not IsScrollingWidget and not IsVideoLibraryOrMovieInfoDialogView and ContainerParentWindowActive and ContainerCheckedAndFocus and not IsAddon
                
                if tmpCheckCondition:
                    
                    self.selecteditem = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.DBID")
                    
                    if (self.selecteditem and self.selecteditem != self.previousitem):
                        self.previousitem = self.selecteditem
                        
                        tmpDBTYPE = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.DBTYPE")
                        tmpIMDBNumber = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.IMDBNumber")
                        
                        IsDbTypeMovie = tmpDBTYPE == 'movie' and not xbmc.getCondVisibility("Container("+my_container_id+").ListItem.IsFolder") and tmpIMDBNumber
                        IsDbTypeTvShow = tmpDBTYPE == 'tvshow' and tmpIMDBNumber
                        
                        IsDbTypeEpisode = tmpDBTYPE == 'episode'
                        
                        IsValidDbType = IsDbTypeMovie or IsDbTypeTvShow or IsDbTypeEpisode
                        
                        if (IsValidDbType):
                            
                            self.dbid = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.DBID")
                            self.dbtype = tmpDBTYPE
                            self.imdbnumber = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.IMDBNumber")
                            self.imdbnumber_corrected = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.IMDBNumber")
                            self.imdbnumber_isvalid = False
                            self.imdbnumber_corrected_isvalid = False
                            self.rating = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.rating")
                            self.rating = self.rating if not self.rating.isspace() else None
                            
                            
                            
                            self.localratings = ""
                            
                            
                            if IsDbTypeMovie:
                                
                                jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":'+str(self.dbid)+',"properties":["ratings"]},"id":1}')
                                
                                jsonResultHasRatings = False
                                
                                if sys.version_info.major == 2:# Python 2
                                    jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore')
                                jsonQuery = simplejson.loads(jsonQuery)
                                
                                jsonResultHasRatings = 'result' in jsonQuery and 'moviedetails' in jsonQuery['result'] and 'ratings' in jsonQuery['result']['moviedetails']
                                
                                if jsonResultHasRatings:
                                    self.localratings = jsonQuery['result']['moviedetails']['ratings']
                            
                            
                            if IsDbTypeMovie and self.imdbnumber:
                                
                                # Validate self.imdbnumber_corrected. ListItem.IMDBNumber sometimes wrong (some scraper wrongly put their own id into this property)
                                # tt, nm, co, ev, ch, ni
                                isValidIMDBNumber = self.imdbnumber_corrected.startswith('tt') or self.imdbnumber_corrected.startswith('nm') or self.imdbnumber_corrected.startswith('co') or self.imdbnumber_corrected.startswith('ev') or self.imdbnumber_corrected.startswith('ch') or self.imdbnumber_corrected.startswith('ni')
                                
                                if isValidIMDBNumber:
                                    self.imdbnumber_isvalid = True
                                    self.imdbnumber_corrected_isvalid = True
                                
                                if not isValidIMDBNumber:
                                  
                                  jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":'+str(self.dbid)+',"properties":["uniqueid"]},"id":1}')
                                  if sys.version_info.major == 2:# Python 2
                                      jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore')
                                  jsonQuery = simplejson.loads(jsonQuery)
                                  
                                  jsonResultHasUniqueIds = False
                                  jsonResultHasUniqueIdImdb = False
                                  jsonResultHasUniqueIdUnknown = False
                                  
                                  # Check if result contains uniqueid as expected
                                  jsonResultHasUniqueIds = 'result' in jsonQuery and 'moviedetails' in jsonQuery['result'] and 'uniqueid' in jsonQuery['result']['moviedetails']
                                  
                                  # only process if uniqueids found at all
                                  if jsonResultHasUniqueIds:
                                      # Check if result contains uniqueid['imdb'] as hoped
                                      jsonResultHasUniqueIdImdb = 'imdb' in jsonQuery['result']['moviedetails']['uniqueid']
                                      
                                      if jsonResultHasUniqueIdImdb:
                                          self.imdbnumber_corrected = str(jsonQuery['result']['moviedetails']['uniqueid']['imdb'])
                                          self.imdbnumber_corrected_isvalid = True
                                      else:
                                        jsonResultHasUniqueIdUnknown = 'unknown' in jsonQuery['result']['moviedetails']['uniqueid']
                                        if jsonResultHasUniqueIdUnknown:
                                            tempImdbOld = self.imdbnumber_corrected
                                            self.imdbnumber_corrected = str(jsonQuery['result']['moviedetails']['uniqueid']['unknown'])
                                            
                                            # Validate self.imdbnumber_corrected again
                                            isValidIMDBNumber = self.imdbnumber_corrected.startswith('tt') or self.imdbnumber_corrected.startswith('nm') or self.imdbnumber_corrected.startswith('co') or self.imdbnumber_corrected.startswith('ev') or self.imdbnumber_corrected.startswith('ch') or self.imdbnumber_corrected.startswith('ni')
                                            
                                            if isValidIMDBNumber:
                                                self.imdbnumber_corrected_isvalid = True
                                                pass
                                            else:
                                                # restore initial value because correct failed
                                                self.imdbnumber_corrected = tempImdbOld
                                                del tempImdbOld
                                        else:
                                            pass
                                  
                                  del jsonResultHasUniqueIds
                                  del jsonResultHasUniqueIdImdb
                                  del jsonResultHasUniqueIdUnknown
                            
                            
                            
                            self.itempath = ""
                            self.itemfile = ""
                            self.itemfilenameandpath = ""
                            self.studio = ""
                            self.genre = ""
                            self.director = ""
                            self.writer = ""
                            
                            try:
                                InfoLabel = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.Path")
                                self.itempath = InfoLabel if InfoLabel else ""
                                
                                InfoLabel = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.FileName")
                                self.itemfile = InfoLabel if InfoLabel else ""
                                
                                InfoLabel = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.FileNameAndPath")
                                self.itemfilenameandpath = InfoLabel if InfoLabel else ""
                                
                                InfoLabel = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.Studio")
                                self.studio = InfoLabel if InfoLabel else ""
                                
                                InfoLabel = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.Genre")
                                self.genre = InfoLabel if InfoLabel else ""
                                
                                InfoLabel = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.Director")
                                self.director = InfoLabel if InfoLabel else ""
                                
                                InfoLabel = xbmc.getInfoLabel("Container("+my_container_id+").ListItem.Writer")
                                self.writer = InfoLabel if InfoLabel else ""
                                
                            except:
                                pass
                            
                            self.set_helper_values()


            tmpCheckCondition = xbmc.getCondVisibility("Skin.HasSetting(ExperimentalShowNtsFile)") and xbmc.getCondVisibility("Window.IsVisible(1103)") and xbmc.getCondVisibility("Window.IsVisible(MovieInformation)") and not xbmcgui.Window(10000).getProperty('ListItemHelper.internalnotes') and not xbmcgui.Window(10000).getProperty('ListItemHelper.internalnotes2') and self.dbid
            
            if tmpCheckCondition:
                try:
                    if(self.itempath):
                        tmp_internalnotes = ""
                        tmp_internalnotes2 = ""
                        
                        if sys.version_info.major == 2:# Python 2
                            media_file = xbmc.translatePath(self.itemfilenameandpath)
                        else:
                            media_file = xbmcvfs.translatePath(self.itemfilenameandpath)
                        
                        media_file_present = xbmcvfs.exists(media_file)
                        if(media_file_present):
                            try:
                                f = xbmcvfs.File(media_file)
                                fsizegb = round(f.size()/1e+9,2)
                                f.close()
                                tmp_internalnotes = tmp_internalnotes + '[COLOR=orange]' + str(fsizegb) + ' GB    \\"' + str(self.itemfile) + '\\"[/COLOR]'
                            except:
                                pass
                            
                            try:
                                st = xbmcvfs.Stat(media_file)
                                modified = st.st_mtime()
                                modified = datetime.fromtimestamp(modified)
                                tmp_internalnotes = tmp_internalnotes + '[COLOR=orange]    ' + str(modified) + '[/COLOR]'
                            except:
                                pass
                        
                        if sys.version_info.major == 2:# Python 2
                            notes_file = xbmc.translatePath(self.itempath)+'.rls-rmx.nts'
                        else:
                            notes_file = xbmcvfs.translatePath(self.itempath)+'.rls-rmx.nts'
                        
                        notes_file_present = xbmcvfs.exists(notes_file)
                        if(notes_file_present):
                            try:
                                f = xbmcvfs.File(notes_file)
                                if(f):
                                    b = f.read()
                                    b = b.replace('"', r'\"')
                                    tmp_internalnotes = tmp_internalnotes + '[CR][CR]' + str(b)
                                f.close()
                            except:
                                pass
                        
                        if sys.version_info.major == 2:# Python 2
                            nfo_file = xbmc.translatePath(self.itempath)+'.nfo.nts'
                        else:
                            nfo_file = xbmcvfs.translatePath(self.itempath)+'.nfo.nts'
                        
                        nfo_file_present = xbmcvfs.exists(nfo_file)
                        if(nfo_file_present):
                            try:
                                f = xbmcvfs.File(nfo_file)
                                if(f):
                                    b = f.read()
                                    b = b.replace('"', r'\"')
                                    tmp_internalnotes = tmp_internalnotes + '[CR][CR][CR][CR]' + str(b) + '[CR][CR]'
                                f.close()
                            except:
                                pass
                        
                        if sys.version_info.major == 2:# Python 2
                            mediainfo_file = xbmc.translatePath(self.itempath)+'.mediainfo.nts'
                        else:
                            mediainfo_file = xbmcvfs.translatePath(self.itempath)+'.mediainfo.nts'
                        
                        mediainfo_file_present = xbmcvfs.exists(mediainfo_file)
                        if(mediainfo_file_present):
                            try:
                                f = xbmcvfs.File(mediainfo_file)
                                if(f):
                                    b = f.read()
                                    b = b.replace('"', r'\"')
                                    tmp_internalnotes2 = tmp_internalnotes2 + str(b)
                                f.close()
                            except:
                                pass
                        
                        xbmc.executebuiltin('SetProperty(ListItemHelper.internalnotes,"'+tmp_internalnotes+'",home)')
                        xbmc.executebuiltin('SetProperty(ListItemHelper.internalnotes2,"'+tmp_internalnotes2+'",home)')
                except:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.internalnotes,"N/A",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.internalnotes2,"N/A",home)')
    #run_service end


    def set_helper_values(self):
        #log('set_helper_values')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.DBID,home)')
        
        # studio genre writer director
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.formatted,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.formatted,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.formatted,home)')
        
        
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.1,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.1,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.1,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.1,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.2,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.2,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.2,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.2,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.3,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.3,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.3,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.3,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.4,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.4,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.4,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.4,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.5,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.5,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.5,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.5,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.6,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.6,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.6,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.6,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.7,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.7,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.7,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.7,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.8,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.8,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.8,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.8,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.9,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.9,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.9,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.9,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.studio.10,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.genre.10,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.writer.10,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.director.10,home)')
        
        
        
        
        
        
        if self.genre:
            if not self.videolibrary_itemseparator_default == self.videolibrary_itemseparator_advancedsettings and self.videolibrary_itemseparator_advancedsettings in self.genre:
                splitString = self.genre.split(self.videolibrary_itemseparator_advancedsettings)
            else:
                if self.videolibrary_itemseparator_default in self.genre or not self.videolibrary_itemseparator_fallback:
                    splitString = self.genre.split(self.videolibrary_itemseparator_default)
                else:
                    splitString = self.genre.split(self.videolibrary_itemseparator_fallback)
            if splitString:
                indexNo = 1
                allitems = ""
                for item in splitString:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.genre.'+str(indexNo)+',"'+str(item)+'",home)')
                    allitems = allitems + self.videolibrary_itemseparator_replacewith + str(item) if indexNo > 1 else str(item)
                    indexNo += 1
                    if indexNo > 10:
                        break
                xbmc.executebuiltin('SetProperty(ListItemHelper.genre.formatted,"'+str(allitems)+'",home)')
        
        if self.studio:
            if not self.videolibrary_itemseparator_default == self.videolibrary_itemseparator_advancedsettings and self.videolibrary_itemseparator_advancedsettings in self.studio:
                splitString = self.studio.split(self.videolibrary_itemseparator_advancedsettings)
            else:
                if self.videolibrary_itemseparator_default in self.studio or not self.videolibrary_itemseparator_fallback:
                    splitString = self.studio.split(self.videolibrary_itemseparator_default)
                else:
                    splitString = self.studio.split(self.videolibrary_itemseparator_fallback)
            if splitString:
                indexNo = 1
                for item in splitString:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.studio.'+str(indexNo)+',"'+str(item)+'",home)')
                    indexNo += 1
                    if indexNo > 10:
                        break
        
        if self.writer:
            if not self.videolibrary_itemseparator_default == self.videolibrary_itemseparator_advancedsettings and self.videolibrary_itemseparator_advancedsettings in self.writer:
                splitString = self.writer.split(self.videolibrary_itemseparator_advancedsettings)
            else:
                if self.videolibrary_itemseparator_default in self.writer or not self.videolibrary_itemseparator_fallback:
                    splitString = self.writer.split(self.videolibrary_itemseparator_default)
                else:
                    splitString = self.writer.split(self.videolibrary_itemseparator_fallback)
            if splitString:
                indexNo = 1
                allitems = ""
                for item in splitString:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.writer.'+str(indexNo)+',"'+str(item)+'",home)')
                    allitems = allitems + self.videolibrary_itemseparator_replacewith + str(item) if indexNo > 1 else str(item)
                    indexNo += 1
                    if indexNo > 10:
                        break
                xbmc.executebuiltin('SetProperty(ListItemHelper.writer.formatted,"'+str(allitems)+'",home)')
        
        if self.director:
            if not self.videolibrary_itemseparator_default == self.videolibrary_itemseparator_advancedsettings and self.videolibrary_itemseparator_advancedsettings in self.director:
                splitString = self.director.split(self.videolibrary_itemseparator_advancedsettings)
            else:
                if self.videolibrary_itemseparator_default in self.director or not self.videolibrary_itemseparator_fallback:
                    splitString = self.director.split(self.videolibrary_itemseparator_default)
                else:
                    splitString = self.director.split(self.videolibrary_itemseparator_fallback)
            if splitString:
                indexNo = 1
                allitems = ""
                for item in splitString:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.director.'+str(indexNo)+',"'+str(item)+'",home)')
                    allitems = allitems + self.videolibrary_itemseparator_replacewith + str(item) if indexNo > 1 else str(item)
                    indexNo += 1
                    if indexNo > 10:
                        break
                xbmc.executebuiltin('SetProperty(ListItemHelper.director.formatted,"'+str(allitems)+'",home)')
        
        
        
        # OMDb
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.rottentomatoes.percent,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.rottentomatoes.image,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.rottentomatoes.url,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.rottentomatoes.audience,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.metacritic.percent,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.imdb.percent,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.imdb,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.imdb.votes,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.highestScaleTo5,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.highestScaleTo10,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.highestScaleTo100,home)')
        rottentomatoesPercent         = None
        rottentomatoesAudiencePercent = None
        metacriticPercent             = None
        imdbPercent                   = None
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.awards,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.revenue.boxoffice,home)')
        
        # TMDb
        xbmc.executebuiltin('ClearProperty(ListItemHelper.TMDBID,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.TVDBID,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.budget,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.budget.million,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.budget.formatted,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.revenue,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.revenue.million,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.revenue.formatted,home)')
        
        # MDBList
        xbmc.executebuiltin('ClearProperty(ListItemHelper.ageRating.commonsense,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.letterboxd,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.letterboxd.percent,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.letterboxd.votes,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.trakt,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.trakt.percent,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.rating.trakt.votes,home)')
        letterboxdPercent             = None
        traktPercent                  = None
        
        # local ratings
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.tomatometerallcritics,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.tomatometerallcritics.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.tomatometerallcritics,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.rottentomatoes,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.rottentomatoes.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.rottentomatoes,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.tomatometerallaudience,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.tomatometerallaudience.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.tomatometerallaudience,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.metacritic,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.metacritic.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.metacritic,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.metascore,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.metascore.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.metascore,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.imdb,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.imdb.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.imdb,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.letterboxd,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.letterboxd.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.letterboxd,home)')
        
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.trakt,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.rating.trakt.scaleTo100,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.listitem.votes.trakt,home)')
        
        
        # Internal Notes files
        xbmc.executebuiltin('ClearProperty(ListItemHelper.internalnotes,home)')
        xbmc.executebuiltin('ClearProperty(ListItemHelper.internalnotes2,home)')
        
        
        # General
        xbmc.executebuiltin('SetProperty(ListItemHelper.DBID,"'+str(self.dbid)+'",home)')
        xbmc.executebuiltin('SetProperty(ListItemHelper.IMDBNumber,"'+str(self.imdbnumber)+'",home)')
        xbmc.executebuiltin('SetProperty(ListItemHelper.IMDBNumber.isValid,"'+str(self.imdbnumber_isvalid)+'",home)')
        xbmc.executebuiltin('SetProperty(ListItemHelper.IMDBNumber.corrected,"'+str(self.imdbnumber_corrected)+'",home)')
        xbmc.executebuiltin('SetProperty(ListItemHelper.IMDBNumber.corrected.isValid,"'+str(self.imdbnumber_corrected_isvalid)+'",home)')
        
        
        
        localrating_tomatometerallcritics = False
        localrating_rottentomatoes = False
        localrating_tomatometerallaudience = False
        localrating_metacritic = False
        localrating_metascore = False
        localrating_imdb = False
        localrating_letterboxd = False
        localrating_trakt = False
        
        localrating_tomatometerallcritics_ScaleTo100 = False
        localrating_rottentomatoes_ScaleTo100 = False
        localrating_tomatometerallaudience_ScaleTo100 = False
        localrating_metacritic_ScaleTo100 = False
        localrating_metascore_ScaleTo100 = False
        localrating_imdb_ScaleTo100 = False
        localrating_letterboxd_ScaleTo100 = False
        localrating_trakt_ScaleTo100 = False
        
        if self.dbtype == 'movie' and self.localratings:
            # tomatometerallcritics
            ratingkeyfound = 'tomatometerallcritics' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['tomatometerallcritics']
                if ratingkeyfound:
                    localrating_tomatometerallcritics = round(self.localratings['tomatometerallcritics']['rating'],1)
                    localrating_tomatometerallcritics_ScaleTo100 = int(round(float(localrating_tomatometerallcritics)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.tomatometerallcritics,"'+str(localrating_tomatometerallcritics)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.tomatometerallcritics.scaleTo100,"'+str(localrating_tomatometerallcritics_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['tomatometerallcritics']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.tomatometerallcritics,"'+str(round(self.localratings['tomatometerallcritics']['votes']))+'",home)')
            # rottentomatoes
            ratingkeyfound = 'rottentomatoes' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['rottentomatoes']
                if ratingkeyfound:
                    localrating_rottentomatoes = round(self.localratings['rottentomatoes']['rating'],1)
                    localrating_rottentomatoes_ScaleTo100 = int(round(float(localrating_rottentomatoes)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.rottentomatoes,"'+str(localrating_rottentomatoes)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.rottentomatoes.scaleTo100,"'+str(localrating_rottentomatoes_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['rottentomatoes']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.rottentomatoes,"'+str(round(self.localratings['rottentomatoes']['votes']))+'",home)')
            # tomatometerallaudience
            ratingkeyfound = 'tomatometerallaudience' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['tomatometerallaudience']
                if ratingkeyfound:
                    localrating_tomatometerallaudience = round(self.localratings['tomatometerallaudience']['rating'],1)
                    localrating_tomatometerallaudience_ScaleTo100 = int(round(float(localrating_tomatometerallaudience)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.tomatometerallaudience,"'+str(localrating_tomatometerallaudience)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.tomatometerallaudience.scaleTo100,"'+str(localrating_tomatometerallaudience_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['tomatometerallaudience']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.tomatometerallaudience,"'+str(round(self.localratings['tomatometerallaudience']['votes']))+'",home)')
            # metacritic
            ratingkeyfound = 'metacritic' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['metacritic']
                if ratingkeyfound:
                    localrating_metacritic = round(self.localratings['metacritic']['rating'],1)
                    localrating_metacritic_ScaleTo100 = int(round(float(localrating_metacritic)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.metacritic,"'+str(localrating_metacritic)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.metacritic.scaleTo100,"'+str(localrating_metacritic_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['metacritic']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.metacritic,"'+str(round(self.localratings['metacritic']['votes']))+'",home)')
            # metascore
            ratingkeyfound = 'metascore' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['metascore']
                if ratingkeyfound:
                    localrating_metascore = round(self.localratings['metascore']['rating'],1)
                    localrating_metascore_ScaleTo100 = int(round(float(localrating_metascore)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.metascore,"'+str(localrating_metascore)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.metascore.scaleTo100,"'+str(localrating_metascore_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['metascore']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.metascore,"'+str(round(self.localratings['metascore']['votes']))+'",home)')
            # imdb
            ratingkeyfound = 'imdb' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['imdb']
                if ratingkeyfound:
                    localrating_imdb = round(self.localratings['imdb']['rating'],1)
                    localrating_imdb_ScaleTo100 = int(round(float(localrating_imdb)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.imdb,"'+str(localrating_imdb)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.imdb.scaleTo100,"'+str(localrating_imdb_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['imdb']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.imdb,"'+str(round(self.localratings['imdb']['votes']))+'",home)')
            # letterboxd
            ratingkeyfound = 'letterboxd' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['letterboxd']
                if ratingkeyfound:
                    localrating_letterboxd = round(self.localratings['letterboxd']['rating'],1)
                    localrating_letterboxd_ScaleTo100 = int(round(float(localrating_letterboxd)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.letterboxd,"'+str(localrating_letterboxd)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.letterboxd.scaleTo100,"'+str(localrating_letterboxd_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['letterboxd']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.letterboxd,"'+str(round(self.localratings['letterboxd']['votes']))+'",home)')
            # trakt
            ratingkeyfound = 'trakt' in self.localratings
            if ratingkeyfound:
                ratingkeyfound = 'rating' in self.localratings['trakt']
                if ratingkeyfound:
                    localrating_trakt = round(self.localratings['trakt']['rating'],1)
                    localrating_trakt_ScaleTo100 = int(round(float(localrating_trakt)*10))
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.trakt,"'+str(localrating_trakt)+'",home)')
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.rating.trakt.scaleTo100,"'+str(localrating_trakt_ScaleTo100)+'",home)')
                ratingkeyfound = 'votes' in self.localratings['trakt']
                if ratingkeyfound:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.listitem.votes.trakt,"'+str(round(self.localratings['trakt']['votes']))+'",home)')
        
        
        
        MDBListImdb      = None
        MDBListImdbVotes = None
        
        # MDBList
        if self.dbtype == 'movie' and self.imdbnumber_corrected_isvalid:
            self.mdblist_result = self.get_mdblist_details(self.imdbnumber_corrected)
        
        if self.dbtype == 'movie' and self.imdbnumber_corrected_isvalid and self.mdblist_result:
            if 'commonsense' in self.mdblist_result and self.mdblist_result['commonsense']:
                xbmc.executebuiltin('SetProperty(ListItemHelper.ageRating.commonsense,'+str(self.mdblist_result['commonsense'])+',home)')
            
            if 'ratings' in self.mdblist_result:
                for rating in self.mdblist_result['ratings']:
                    if 'source' in rating:
                        # letterboxd
                        if rating['source'] == 'letterboxd':
                            if 'value' in rating and rating['value']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.letterboxd,'+str(rating['value'])+',home)')
                            if 'score' in rating and rating['score']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.letterboxd.percent,'+str(rating['score'])+',home)')
                                letterboxdPercent = int(float(rating['score']))
                            if 'votes' in rating and rating['votes']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.letterboxd.votes,'+str(rating['votes'])+',home)')
                        # imdb
                        if rating['source'] == 'imdb':
                            if 'value' in rating and rating['value']:
                                MDBListImdb = True
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.imdb,'+str(rating['value'])+',home)')
                            if 'score' in rating and rating['score']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.imdb.percent,'+str(rating['score'])+',home)')
                                imdbPercent = int(float(rating['score']))
                            if 'votes' in rating and rating['votes']:
                                MDBListImdbVotes = True
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.imdb.votes,'+str(rating['votes'])+',home)')
                        # rotten tomatoes
                        if rating['source'] == 'tomatoes':
                            if 'score' in rating and rating['score']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.rottentomatoes.percent,'+str(rating['score'])+',home)')
                                rottentomatoesPercent = int(float(rating['score']))
                        # rotten tomatoes audience
                        if rating['source'] == 'tomatoesaudience':
                            if 'score' in rating and rating['score']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.rottentomatoes.audience,'+str(rating['score'])+',home)')
                                rottentomatoesAudiencePercent = int(float(rating['score']))
                        # metacritic
                        if rating['source'] == 'metacritic':
                            if 'score' in rating and rating['score']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.metacritic.percent,'+str(rating['score'])+',home)')
                                metacriticPercent = int(float(rating['score']))
                        # trakt
                        if rating['source'] == 'trakt':
                            if 'value' in rating and rating['value']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.trakt,'+str(rating['value'])+',home)')
                            if 'score' in rating and rating['score']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.trakt.percent,'+str(rating['score'])+',home)')
                                traktPercent = int(float(rating['score']))
                            if 'votes' in rating and rating['votes']:
                                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.trakt.votes,'+str(rating['votes'])+',home)')
        
        
        
        # OMDB
        if self.dbtype == 'movie' and self.imdbnumber_corrected_isvalid:
            self.omdb_result = self.get_omdb_info(self.imdbnumber_corrected)
        
        if self.dbtype == 'movie' and self.imdbnumber_corrected_isvalid and self.omdb_result:
            for key, value in self.omdb_result.items():
                # rotten tomatoes
                if key == "rottentomatoes.rating" and value and not rottentomatoesPercent:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.rottentomatoes.percent,"'+str(value)+'",home)')
                    try:
                        rottentomatoesPercent = int(float(value))
                    except:
                        pass
                if key == "rottentomatoes.image" and value :
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.rottentomatoes.image,"'+str(value)+'",home)')
                if key == "rottentomatoes.audience" and value and not rottentomatoesAudiencePercent:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.rottentomatoes.audience,"'+str(value)+'",home)')
                    try:
                        rottentomatoesAudiencePercent = int(float(value))
                    except:
                        pass
                
                # metacritic
                if key == "metacritic.rating" and value and not metacriticPercent:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.metacritic.percent,"'+str(value)+'",home)')
                    try:
                        metacriticPercent = int(float(value))
                    except:
                        pass
                
                # imdb
                if key == "rating.percent.imdb" and value and not imdbPercent:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.imdb.percent,'+str(value)+',home)')
                    try:
                        imdbPercent = int(float(value))
                    except:
                        pass
                if key == "rating.imdb" and value and not MDBListImdb:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.imdb,'+str(value)+',home)')
                if key == "votes.imdb" and value and not MDBListImdbVotes:
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.imdb.votes,"'+str(value)+'",home)')
                
                if key == "rottentomatoes.url" and value :
                    xbmc.executebuiltin('SetProperty(ListItemHelper.rating.rottentomatoes.url,"'+str(value)+'",home)')
                # awards
                if key == "awards" and value :
                    xbmc.executebuiltin('SetProperty(ListItemHelper.awards,"'+str(value)+'",home)')
                # boxoffice
                if key == "boxoffice" and value :
                    xbmc.executebuiltin('SetProperty(ListItemHelper.revenue.boxoffice,"'+str(value)+'",home)')
        
        
        percentList                       = []
        
        
        
        if rottentomatoesPercent:         percentList.append(rottentomatoesPercent)
        if rottentomatoesAudiencePercent: percentList.append(rottentomatoesAudiencePercent)
        if metacriticPercent:             percentList.append(metacriticPercent)
        if imdbPercent:                   percentList.append(imdbPercent)
        if letterboxdPercent:             percentList.append(letterboxdPercent)
        if traktPercent:                  percentList.append(traktPercent)
        
        
        localRating = localrating_tomatometerallcritics_ScaleTo100
        if localRating: percentList.append(localRating)
        localRating = localrating_rottentomatoes_ScaleTo100
        if localRating: percentList.append(localRating)
        
        localRating = localrating_tomatometerallaudience_ScaleTo100
        if localRating: percentList.append(localRating)
        
        localRating = localrating_metacritic_ScaleTo100
        if localRating: percentList.append(localRating)
        localRating = localrating_metascore_ScaleTo100
        if localRating: percentList.append(localRating)
        
        localRating = localrating_imdb_ScaleTo100
        if localRating: percentList.append(localRating)
        
        localRating = localrating_letterboxd_ScaleTo100
        if localRating: percentList.append(localRating)
        
        localRating = localrating_trakt_ScaleTo100
        if localRating: percentList.append(localRating)
        
        
        
        try:
            if self.rating:               percentList.append(int(float(self.rating)*10))
            
            highestPercent = max(percentList) if percentList else None
            
            highestPercentTo5Rating          = float(highestPercent)/20 if highestPercent else None
            highestPercentTo10Rating         = float(highestPercent)/10 if highestPercent else None
            highestPercentTo100Rating        = float(highestPercent)    if highestPercent else None
            
            if highestPercent:
                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.highestScaleTo5,"'+str(highestPercentTo5Rating)+'",home)')
                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.highestScaleTo10,"'+str(highestPercentTo10Rating)+'",home)')
                xbmc.executebuiltin('SetProperty(ListItemHelper.rating.highestScaleTo100,"'+str(highestPercentTo100Rating)+'",home)')
        
        except:
            pass
        
        
        
        # TMDB
        if self.dbtype == 'movie' and self.imdbnumber_corrected_isvalid:
            self.tmdb_result = self.get_tmdb_details(self.imdbnumber_corrected)
        
        if self.dbtype == 'movie' and self.imdbnumber_corrected_isvalid and self.tmdb_result:
            for key, value in self.tmdb_result.items():
                # tmdb_id
                if key == "tmdb_id" and value :
                    xbmc.executebuiltin('SetProperty(ListItemHelper.TMDBID,"'+str(value)+'",home)')
                # tvdb_id
                if key == "tvdb_id" and value :
                    xbmc.executebuiltin('SetProperty(ListItemHelper.TVDBID,"'+str(value)+'",home)')
                # budget
                if key == "budget" and value :
                    try:
                        tmpval = float(int(value))
                        if (tmpval > 0) :
                            xbmc.executebuiltin('SetProperty(ListItemHelper.budget,"'+str(value)+'",home)')
                            try:
                                tmpval = round(tmpval/1000000, 2)
                                if tmpval.is_integer() :
                                    tmpval = '%.0f' % tmpval
                                else :
                                    if (tmpval >= 10) :
                                        tmpval = round(tmpval,0)
                                        tmpval = '%.0f' % tmpval
                                xbmc.executebuiltin('SetProperty(ListItemHelper.budget.million,"'+str(tmpval)+'",home)')
                            except:
                                pass
                    except:
                        pass
                if key == "budget.formatted" and value :
                    try:
                        if (value != '0') :
                             xbmc.executebuiltin('SetProperty(ListItemHelper.budget.formatted,"'+str(value)+'",home)')
                    except:
                        pass
                # revenue
                if key == "revenue" and value :
                    try:
                        tmpval = float(int(value))
                        if (tmpval > 0) :
                            xbmc.executebuiltin('SetProperty(ListItemHelper.revenue,"'+str(value)+'",home)')
                            try:
                                tmpval = round(tmpval/1000000, 2)
                                if tmpval.is_integer() :
                                    tmpval = '%.0f' % tmpval
                                else :
                                    if (tmpval >= 10) :
                                        tmpval = round(tmpval,0)
                                        tmpval = '%.0f' % tmpval
                                xbmc.executebuiltin('SetProperty(ListItemHelper.revenue.million,"'+str(tmpval)+'",home)')
                            except:
                                pass
                    except:
                        pass
                if key == "revenue.formatted" and value :
                    try:
                        if (value != '0') :
                            xbmc.executebuiltin('SetProperty(ListItemHelper.revenue.formatted,"'+str(value)+'",home)')
                    except:
                        pass
        
        
        
        
    #set_helper_values end

    def get_omdb_info(self, imdb_id="", title="", year="", content_type=""):
        '''Get (kodi compatible formatted) metadata from OMDB, including Rotten tomatoes details'''
        #title = title.split(" (")[0]  # strip year appended to title
        result = {}
        if imdb_id:
            result = self.omdb.get_details_by_imdbid(imdb_id)
        '''
        elif title and content_type in ["seasons", "season", "episodes", "episode", "tvshows", "tvshow"]:
            result = self.omdb.get_details_by_title(title, "", "tvshows")
        elif title and year:
            result = self.get_details_by_title(title, year, content_type)
         if result and result.get("status"):
             result["status"] = self.translate_string(result["status"])
         if result and result.get("runtime"):
             result["runtime"] = result["runtime"] / 60
             result.update(self.get_duration(result["runtime"]))
        '''
        return result


    def get_tmdb_details(self, imdb_id="", tvdb_id="", title="", year="", media_type="",
                         preftype="", manual_select=False, ignore_cache=False):
        '''returns details from tmdb'''
        result = {}
        if imdb_id:
            result = self.tmdb.get_videodetails_by_externalid(
                imdb_id, "imdb_id")
        '''
        elif tvdb_id:
            result = self.tmdb.get_videodetails_by_externalid(
                tvdb_id, "tvdb_id")
        elif title and media_type in ["movies", "setmovies", "movie"]:
            result = self.tmdb.search_movie(
                title, year, manual_select=manual_select, ignore_cache=ignore_cache)
        elif title and media_type in ["tvshows", "tvshow"]:
            result = self.tmdb.search_tvshow(
                title, year, manual_select=manual_select, ignore_cache=ignore_cache)
        elif title:
            result = self.tmdb.search_video(
                title, year, preftype=preftype, manual_select=manual_select, ignore_cache=ignore_cache)
        if result and result.get("status"):
            result["status"] = self.translate_string(result["status"])
        if result and result.get("runtime"):
            result["runtime"] = result["runtime"] / 60
            result.update(self.get_duration(result["runtime"]))
        '''
        return result


    def get_mdblist_details(self, imdb_id="", tvdb_id="", title="", year="", media_type="",
                         preftype="", manual_select=False, ignore_cache=False):
        '''returns details from mdblist'''
        result = {}
        if imdb_id:
            result = self.mdblist.get_details_by_externalid(imdb_id, "imdb_id")
        return result


    @property
    def omdb(self):
        '''public omdb object - for lazy loading'''
        if not self._omdb:
            from lib.omdb import ListItemHelperOmdb
            self._omdb = ListItemHelperOmdb(self.cache)
        return self._omdb


    @property
    def tmdb(self):
        '''public Tmdb object - for lazy loading'''
        if not self._tmdb:
            from lib.tmdb import Tmdb
            self._tmdb = Tmdb(self.cache)
        return self._tmdb


    @property
    def mdblist(self):
        '''public mdblist object - for lazy loading'''
        if not self._mdblist:
            from lib.mdblist import mdblist
            self._mdblist = mdblist(self.cache)
        return self._mdblist


if (__name__ == "__main__"):
    Main()


log('script finished.')

