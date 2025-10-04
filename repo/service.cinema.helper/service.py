# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import time
import simplejson
import xbmcvfs

__addon__      = xbmcaddon.Addon()
__addonid__    = __addon__.getAddonInfo('id')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString
__cwd__        = __addon__.getAddonInfo('path')

class MyPlayer( xbmc.Player ):
  
  def __init__( self, *args, **kwargs ):
    xbmc.Player.__init__( self )
    self.videoFinishedPercentage = 80
    
    self.videolibrary_itemseparator = ""
    
    self.startTimer = time.time()
    self.endTimer = time.time()
    
    self.percentageTimer = time.time()
    self.playerPercentage = 0
    
    self.idleCheckIntervalTimer = time.time()
    
    self.VideoPlayerIsMovie = False
    self.VideoPlayerDbId = -1
    self.VideoPlayerIsMovieInDb = False
    self.PlayerAudioOnly = False
    
    self.movieHasPostCreditsScene = False
    self.nearEndPreReached = False
    self.nearEndReached = ""
    
    self.skinIsACZG = xbmc.getSkinDir() == "skin.aczg"
    
    self.isKodi18plus = False
    self.isKodi19plus = False
    BuildVersionStr = str(xbmc.getInfoLabel('System.BuildVersion')).lower()
    if BuildVersionStr.find("18.") == 0 or BuildVersionStr.find("19.") == 0 or BuildVersionStr.find("20.") == 0 or BuildVersionStr.find("21.") == 0 or BuildVersionStr.find("22.") == 0:
      self.isKodi18plus = True
      if BuildVersionStr.find("19.") == 0 or BuildVersionStr.find("20.") == 0 or BuildVersionStr.find("21.") == 0 or BuildVersionStr.find("22.") == 0:
        self.isKodi19plus = True
    
    if not self.isKodi18plus:
      if sys.version_info.major == 2:# Python 2
        check_23hz_file = xbmc.translatePath('special://xbmc').decode('utf-8') + '_check23hz\display.23hz.available'
      else:
        check_23hz_file = xbmcvfs.translatePath('special://xbmc').decode('utf-8') + '_check23hz\display.23hz.available'
      
      check_23hz_file_ok = xbmcvfs.exists(check_23hz_file)
      if check_23hz_file_ok:
        xbmc.executebuiltin("SetProperty(CinemaHelper.23hz,True,home)")
      else:
        xbmc.executebuiltin("ClearProperty(CinemaHelper.23hz,home)")
  
  
  def onPlayBackEnded( self ):
    self.onPlayBackStopped()
  
  def onPlayBackStopped( self ):
    
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.DBID,home)")
    
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.nearEndPreReached,home)")
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.nearEndReached,home)")
    
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.movieHasPostCreditsScene,home)")
    
    self.movieHasPostCreditsScene = False
    self.nearEndPreReached = False
    self.nearEndReached = ""
    
    self.endTimer = time.time()
    
    
    if not self.PlayerAudioOnly:
      xbmc.executebuiltin("SetProperty(PlayBackJustEnded,True,home)")
    
    self.VideoPlayerIsMovie = False
    self.VideoPlayerDbId = -1
    self.PlayerAudioOnly = False
    
    # studio
    for x in range(1, 51):
      # clear all
      xbmc.executebuiltin('ClearProperty(CinemaHelper.player.studio.'+str(x)+',home)')
    
    if self.VideoPlayerIsMovieInDb:
      self.VideoPlayerIsMovieInDb = False
      
      CinemaPostPlaybackDialogType = int(xbmc.getInfoLabel("Skin.String(CinemaPostPlaybackDialogType)")) if xbmc.getInfoLabel("Skin.String(CinemaPostPlaybackDialogType)") else 0
      
      if self.skinIsACZG and CinemaPostPlaybackDialogType > 0 and self.playerPercentage > self.videoFinishedPercentage:
        
        self.playerPercentage = 0
        
        myPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlistSize = myPlaylist.size()
        playlistPosition = myPlaylist.getposition()
        
        CinemaPostPlaybackDBID = xbmcgui.Window(10000).getProperty('CinemaPostPlaybackDBID')
        
        if CinemaPostPlaybackDBID != "" and playlistSize <= 1 and playlistPosition <= 0:
          
          if CinemaPostPlaybackDialogType > 0:
            
            xbmc.executebuiltin("SetProperty(CinemaPostPlaybackDialogOpensNow,True,home)")
            
            xbmc.executebuiltin("ActivateWindow(1190)")
            
            if CinemaPostPlaybackDialogType == 1:
              
              xbmc.sleep(500)
              
              xbmc.executebuiltin("SetFocus(43260)")
              
              xbmc.sleep(500)
            
              xbmc.executebuiltin("Action(Info)")
            
              xbmc.sleep(500)
            
              xbmc.executebuiltin("Dialog.Close(1190,true)")


  def onPlayBackStarted( self ):
    
    xbmc.executebuiltin("SetProperty(PlayBackJustStarted,True,home)")
    
    addon = xbmcaddon.Addon(id="service.listitem.helper")
    self.videolibrary_itemseparator = addon.getSetting("videolibrary_itemseparator") if addon.getSetting("videolibrary_itemseparator") else ' / '
    
    self.VideoPlayerIsMovie = False
    self.VideoPlayerDbId = -1
    self.playerPercentage = 0
    
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.DBID,home)")
    
    self.startTimer = time.time()
    
    xbmc.executebuiltin("SetProperty(CinemaPostPlaybackDBID,,home)")
    
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.nearEndPreReached,home)")
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.nearEndReached,home)")
    
    xbmc.executebuiltin("ClearProperty(CinemaHelper.player.movieHasPostCreditsScene,home)")
    
    self.movieHasPostCreditsScene = False
    self.nearEndPreReached = False
    self.nearEndReached = ""
    
    
    # studio
    for x in range(1, 51):
      # clear all
      xbmc.executebuiltin('ClearProperty(CinemaHelper.player.studio.'+str(x)+',home)')
    
    xbmc.sleep(1000)
    
    self.VideoPlayerIsMovie = xbmc.getCondVisibility('VideoPlayer.Content(Movies)')
    
    self.VideoPlayerDbId = int(xbmc.getInfoLabel("VideoPlayer.DBID")) if xbmc.getInfoLabel("VideoPlayer.DBID") else -1# int() Python 3 fix
    self.VideoPlayerIsMovieInDb = self.VideoPlayerIsMovie and self.VideoPlayerDbId > 0 and xbmc.getCondVisibility("VideoPlayer.HasInfo")
    self.PlayerAudioOnly = xbmc.getCondVisibility("Player.HasMedia") and xbmc.getCondVisibility("Player.HasAudio") and not xbmc.getCondVisibility("Player.HasVideo")
    
    if self.VideoPlayerDbId > 0:
      xbmc.executebuiltin("SetProperty(CinemaHelper.player.DBID,"+str(self.VideoPlayerDbId)+",home)")
    
    if self.VideoPlayerIsMovieInDb:
      
      tagsQuery = '{"jsonrpc":"2.0","id":"libTags","method":"VideoLibrary.GetMovieDetails","params":{"movieid":'+str(playerMonitor.VideoPlayerDbId)+',"properties":["title","tag"]}}'
      
      jsonQuery = xbmc.executeJSONRPC(tagsQuery)
      
      jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
      
      jsonQuery = simplejson.loads(jsonQuery)
      
      tmpHasKeyCheck = 'result' in jsonQuery and 'moviedetails' in jsonQuery['result'] and 'tag' in jsonQuery['result']['moviedetails']
      
      if tmpHasKeyCheck:
        if 'aftercreditsstinger' in jsonQuery['result']['moviedetails']['tag'] or 'duringcreditsstinger' in jsonQuery['result']['moviedetails']['tag']:
          self.movieHasPostCreditsScene = True
          xbmc.executebuiltin("SetProperty(CinemaHelper.player.movieHasPostCreditsScene,True,home)")
      
      xbmc.executebuiltin('SetProperty(CinemaPostPlaybackDBID,'+str(self.VideoPlayerDbId)+',home)')
      
      VideoPlayerStudio = str(xbmc.getInfoLabel("VideoPlayer.Studio"))
      if VideoPlayerStudio:
        splitString = VideoPlayerStudio.split(self.videolibrary_itemseparator)
        if splitString:
          indexNo = 1
          for item in splitString:
            xbmc.executebuiltin('SetProperty(CinemaHelper.player.studio.'+str(indexNo)+',"'+str(item)+'",home)')
            indexNo += 1

#/class


playerMonitor = MyPlayer()

monitor = xbmc.Monitor()

xbmc.executebuiltin("SetProperty(PlayBackJustStarted,,home)")
xbmc.executebuiltin("SetProperty(PlayBackJustEnded,,home)")




TimerInterval_2_Enabled = True
TimerInterval_3_Enabled = True

TimerInterval_2_ResetSec = float(0.995)
TimerInterval_3_ResetSec = float(4.00)

TimerInterval_2 = time.time()
TimerInterval_3 = time.time()

nearEndPreReached_Minutes = 30
nearEndReached_Minutes    = 10



lastContainerPath = ""
lastWindowAndContainerPath = ""
nearEndReachedTimeOutDurationCount = 0

TimerInterval_2_FirstRunDone = -1

showParentDirItems = False

if not playerMonitor.isKodi19plus:# Python 2
  checkAbortRequested = xbmc.abortRequested
else:# Python 3
  checkAbortRequested = monitor.abortRequested()
while not checkAbortRequested:
  if monitor.waitForAbort(0.2):
    break
  
  timeNow = time.time()
  
  
  # INTERVAL DEFAULT
  
  if TimerInterval_2_FirstRunDone == 2:
    
    
    if playerMonitor.skinIsACZG:
      if xbmc.getCondVisibility("Container.Content(TvShows)"):
        
        TvShowDBID = xbmc.getInfoLabel("Control.GetLabel(12201)")
        
        if TvShowDBID and TvShowDBID != xbmcgui.Window(10000).getProperty('CinemaHelper.ListItem.TvShowDBID'):
          
          TvShowTitle = xbmc.getInfoLabel("Control.GetLabel(12202)").replace("'","\'").replace('"','\\"')
          TvShowTotalSeasons = xbmc.getInfoLabel("Control.GetLabel(12203)")
          xbmc.executebuiltin("SetProperty(CinemaHelper.ListItem.TvShowDBID,"+TvShowDBID+",home)")
          xbmc.executebuiltin('SetProperty(CinemaHelper.ListItem.TvShowTitle,"'+TvShowTitle+'",home)')
          xbmc.executebuiltin("SetProperty(CinemaHelper.ListItem.TvShowTotalSeasons,"+TvShowTotalSeasons+",home)")
    set_focus_now = xbmcgui.Window(10000).getProperty('set_focus_now')
    set_focus_now_child = xbmcgui.Window(10000).getProperty('set_focus_now_child')
    
    if set_focus_now:
      
      xbmcgui.Window(10000).clearProperty('set_focus_now')
      xbmcgui.Window(10000).clearProperty('set_focus_now_child')
      
      if not set_focus_now_child:
        xbmc.executebuiltin("SetFocus("+set_focus_now+")")
      else:
        xbmc.executebuiltin("SetFocus("+set_focus_now+","+set_focus_now_child+")")
    
    
    
    CurrentWindow = str(xbmcgui.getCurrentWindowId())
    lastContainerPathCompare = xbmc.getInfoLabel("Container.FolderPath")
    
    lastWindowAndContainerPathCompare = CurrentWindow + '_' + lastContainerPathCompare
    
    
    if lastWindowAndContainerPath != lastWindowAndContainerPathCompare:
      
      
      playerMonitor.skinIsACZG = xbmc.getSkinDir() == "skin.aczg"
      
      showParentDirItems = xbmc.getCondVisibility("System.GetBool(filelists.showparentdiritems)")
      
      lastContainerPathWasEmpty = True if lastContainerPath == "" else False
      
      lastContainerPath = lastContainerPathCompare
      lastWindowAndContainerPath = CurrentWindow + '_' + lastContainerPathCompare
      
      
      if playerMonitor.skinIsACZG:
        
        
        ForcePresetViewsDisable = xbmc.getCondVisibility("Skin.HasSetting(ForcePresetViewsDisable)")
        
        
        xbmc.sleep(10)#short wait 10-25ms to let Kodi populate properties like Container.PluginName which are otherwise wrongly empty leading to detection issues (Container.FolderPath maybe also affected)
        
        
        #################################
        # OOB Experience for View Modes #
        #################################
        
        IsAddon = xbmc.getInfoLabel("Container.PluginName") or lastContainerPathCompare.startswith('plugin://')
        
        
        if not ForcePresetViewsDisable and not IsAddon:
          
          #################################
          # View Modes CONFIG             #
          #################################
          
          # MOVIES
          
          ForcePresetViewsMoviesCategory_A = 500
          ForcePresetViewsMoviesCategory_B = 508
          ForcePresetViewsMoviesCategory_C = 508
          
          try:
            ForcePresetViewsMoviesCategories = str(xbmc.getInfoLabel("Skin.String(ForcePresetViewsMoviesCategories)"))
            if ForcePresetViewsMoviesCategories:
              ForcePresetViewsMoviesCategoriesArr = ForcePresetViewsMoviesCategories.split(',',3)
              
              if int(ForcePresetViewsMoviesCategoriesArr[0]) > 0:
                ForcePresetViewsMoviesCategory_A = int(ForcePresetViewsMoviesCategoriesArr[0])
              if int(ForcePresetViewsMoviesCategoriesArr[1]) > 0:
                ForcePresetViewsMoviesCategory_B = int(ForcePresetViewsMoviesCategoriesArr[1])
              if int(ForcePresetViewsMoviesCategoriesArr[2]) > 0:
                ForcePresetViewsMoviesCategory_C = int(ForcePresetViewsMoviesCategoriesArr[2])
              
          except:
            pass
          
          # TV SHOWS
          
          ForcePresetViewsTvShowsCategory_A = 508
          ForcePresetViewsTvShowsCategory_B = 508
          ForcePresetViewsTvShowsCategory_C = 509
          ForcePresetViewsTvShowsCategory_D = 510
          ForcePresetViewsTvShowsCategory_E = 52
          
          try:
            ForcePresetViewsTvShowsCategories = str(xbmc.getInfoLabel("Skin.String(ForcePresetViewsTvShowsCategories)"))
            if ForcePresetViewsTvShowsCategories:
              ForcePresetViewsTvShowsCategoriesArr = ForcePresetViewsTvShowsCategories.split(',',5)
              
              if int(ForcePresetViewsTvShowsCategoriesArr[0]) > 0:
                ForcePresetViewsTvShowsCategory_A = int(ForcePresetViewsTvShowsCategoriesArr[0])
              if int(ForcePresetViewsTvShowsCategoriesArr[1]) > 0:
                ForcePresetViewsTvShowsCategory_B = int(ForcePresetViewsTvShowsCategoriesArr[1])
              if int(ForcePresetViewsTvShowsCategoriesArr[2]) > 0:
                ForcePresetViewsTvShowsCategory_C = int(ForcePresetViewsTvShowsCategoriesArr[2])
              if int(ForcePresetViewsTvShowsCategoriesArr[3]) > 0:
                ForcePresetViewsTvShowsCategory_D = int(ForcePresetViewsTvShowsCategoriesArr[3])
              if int(ForcePresetViewsTvShowsCategoriesArr[4]) > 0:
                ForcePresetViewsTvShowsCategory_E = int(ForcePresetViewsTvShowsCategoriesArr[4])
              
          except:
            pass
          
          # MUSIC / PICTURES
          
          ForcePresetViewsMusicPicturesCategory_A = 500
          ForcePresetViewsMusicPicturesCategory_B = 588
          ForcePresetViewsMusicPicturesCategory_C = 500
          
          try:
            ForcePresetViewsMusicPicturesCategories = str(xbmc.getInfoLabel("Skin.String(ForcePresetViewsMusicPicturesCategories)"))
            if ForcePresetViewsMusicPicturesCategories:
              ForcePresetViewsMusicPicturesCategoriesArr = ForcePresetViewsMusicPicturesCategories.split(',',3)
              
              if int(ForcePresetViewsMusicPicturesCategoriesArr[0]) > 0:
                ForcePresetViewsMusicPicturesCategory_A = int(ForcePresetViewsMusicPicturesCategoriesArr[0])
              if int(ForcePresetViewsMusicPicturesCategoriesArr[1]) > 0:
                ForcePresetViewsMusicPicturesCategory_B = int(ForcePresetViewsMusicPicturesCategoriesArr[1])
              if int(ForcePresetViewsMusicPicturesCategoriesArr[2]) > 0:
                ForcePresetViewsMusicPicturesCategory_C = int(ForcePresetViewsMusicPicturesCategoriesArr[2])
              
          except:
            pass
          
           # GLOBAL / MISC
          
          ForcePresetViewsGlobalMiscCategory_A = 500
          ForcePresetViewsGlobalMiscCategory_B = 500
          ForcePresetViewsGlobalMiscCategory_C = 500
          ForcePresetViewsGlobalMiscCategory_D = 500
          ForcePresetViewsGlobalMiscCategory_E = 500
          
          try:
            ForcePresetViewsGlobalMiscCategories = str(xbmc.getInfoLabel("Skin.String(ForcePresetViewsGlobalMiscCategories)"))
            if ForcePresetViewsGlobalMiscCategories:
              ForcePresetViewsGlobalMiscCategoriesArr = ForcePresetViewsGlobalMiscCategories.split(',',5)
              
              if int(ForcePresetViewsGlobalMiscCategoriesArr[0]) > 0:
                ForcePresetViewsGlobalMiscCategory_A = int(ForcePresetViewsGlobalMiscCategoriesArr[0])
              if int(ForcePresetViewsGlobalMiscCategoriesArr[1]) > 0:
                ForcePresetViewsGlobalMiscCategory_B = int(ForcePresetViewsGlobalMiscCategoriesArr[1])
              if int(ForcePresetViewsGlobalMiscCategoriesArr[2]) > 0:
                ForcePresetViewsGlobalMiscCategory_C = int(ForcePresetViewsGlobalMiscCategoriesArr[2])
              if int(ForcePresetViewsGlobalMiscCategoriesArr[3]) > 0:
                ForcePresetViewsGlobalMiscCategory_D = int(ForcePresetViewsGlobalMiscCategoriesArr[3])
              if int(ForcePresetViewsGlobalMiscCategoriesArr[4]) > 0:
                ForcePresetViewsGlobalMiscCategory_E = int(ForcePresetViewsGlobalMiscCategoriesArr[4])
              
          except:
            pass
          
          
          
      
          
          
          
          
          
          
          
          # GLOBAL
          
          ForcePresetViewsGlobalCategory_A = ForcePresetViewsGlobalMiscCategory_A#500#global root + fallback
          ForcePresetViewsGlobalCategory_B = ForcePresetViewsGlobalMiscCategory_B#500#actors + artists
          
          # VIDEOS
          
          ForcePresetViewsVideosCategory_A = ForcePresetViewsGlobalCategory_A#videos root + fallback
          ForcePresetViewsVideosCategory_B = ForcePresetViewsGlobalMiscCategory_C#52#files
          
          # ADDONS
          
          ForcePresetViewsAddonsCategory_A = ForcePresetViewsGlobalCategory_A#addons root + fallback
          ForcePresetViewsAddonsCategory_B = ForcePresetViewsGlobalMiscCategory_D#500#addons
          
          # MUSIC
          
          ForcePresetViewsMusicCategory_A = ForcePresetViewsGlobalCategory_A#music root + fallback
          ForcePresetViewsMusicCategory_B = ForcePresetViewsMusicPicturesCategory_A#500#albums + music videos
          ForcePresetViewsMusicCategory_C = ForcePresetViewsMusicPicturesCategory_B#588#songs
          
          # PICTURES
          
          ForcePresetViewsPicturesCategory_A = ForcePresetViewsGlobalCategory_A#pictures root + fallback
          ForcePresetViewsPicturesCategory_B = ForcePresetViewsMusicPicturesCategory_C#500#pictures
          
          # GAMES
          
          ForcePresetViewsGamesCategory_A = ForcePresetViewsGlobalMiscCategory_E#games
          
          
          
          
          
          
          #################################
          # View Modes SET switchToView   #
          #################################
          
          switchToView = False
          
          
          
          IsMusicWindow = xbmc.getCondVisibility("Window.IsActive(Music)") and xbmc.getCondVisibility("Window.Is(Music)")
          IsPicturesWindow = xbmc.getCondVisibility("Window.IsActive(Pictures)") and xbmc.getCondVisibility("Window.Is(Pictures)")
          
          IsAddonBrowserWindow = xbmc.getCondVisibility("Window.IsActive(AddonBrowser)") and xbmc.getCondVisibility("Window.Is(AddonBrowser)")
          
          IsContainerContentAddons = xbmc.getCondVisibility("Container.Content(Addons)")
          
          IsWindowGames = xbmc.getCondVisibility("Window.IsActive(Games)")
          IsFolderPathEmpty = xbmc.getCondVisibility("String.IsEmpty(Container.FolderPath)")
          
          
          # MUSIC
          
          if (IsMusicWindow and not xbmc.getCondVisibility("Container.Content(Genres)") and not xbmc.getCondVisibility("Container.Content(Songs)") and not xbmc.getCondVisibility("Container.Content(Years)") and not xbmc.getCondVisibility("Container.Content(Addons)") and not xbmc.getCondVisibility("Container.Content(Files)") and not xbmc.getCondVisibility("Container.Content(Directors)") and not xbmc.getCondVisibility("Container.Content(Studios)") and not xbmc.getCondVisibility("Container.Content(Tags)")) and not (xbmc.getCondVisibility("Container.Content(MusicVideos)") or xbmc.getCondVisibility("Container.Content(Albums)")):
            switchToView = ForcePresetViewsMusicCategory_A
          
          if xbmc.getCondVisibility("Container.Content(MusicVideos)") or xbmc.getCondVisibility("Container.Content(Albums)"):
            switchToView = ForcePresetViewsMusicCategory_B
          
          if xbmc.getCondVisibility("Container.Content(Songs)"):
            switchToView = ForcePresetViewsMusicCategory_C
          
          if xbmc.getCondVisibility("Container.Content(Artists)"):
            switchToView = ForcePresetViewsGlobalCategory_B
          
          # PICTURES
          
          if IsPicturesWindow and not IsContainerContentAddons and not xbmc.getCondVisibility("Container.Content(Images)"):
            switchToView = ForcePresetViewsPicturesCategory_A
          
          if xbmc.getCondVisibility("Container.Content(Images)"):
            switchToView = ForcePresetViewsPicturesCategory_B
          
          # ADDONS
          
          if IsAddonBrowserWindow and not IsContainerContentAddons:
            switchToView = ForcePresetViewsAddonsCategory_A
          
          if IsContainerContentAddons and not IsWindowGames:
            switchToView = ForcePresetViewsAddonsCategory_B
          
          # GAMES
          
          if IsWindowGames:
            if IsFolderPathEmpty:
              switchToView = ForcePresetViewsGlobalCategory_A
            else:
              switchToView = ForcePresetViewsGamesCategory_A
          
          
          
          IsVideoLibraryView = xbmc.getCondVisibility("Window.IsActive(Videos)") and xbmc.getCondVisibility("Window.Is(Videos)")
          
          if IsVideoLibraryView:
            
            IsVideoDb = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,videodb://)")
            IsFilesContent = xbmc.getCondVisibility("Container.Content(Files)") or xbmc.getCondVisibility("Container.Content(Mixed)")
            
            # actors
            IsActorsContent = xbmc.getCondVisibility("Container.Content(Actors)")
            
            # music videos
            IsMusicVideosContent = xbmc.getCondVisibility("Container.Content(MusicVideos)")
            
            # addons
            IsAddonsContent = xbmc.getCondVisibility("Container.Content(Addons)")
            
            # movies
            IsMovieContent = xbmc.getCondVisibility("Container.Content(Movies)")
            IsSetsContent = xbmc.getCondVisibility("Container.Content(Sets)")
            
            #tv shows
            IsTvShowsContent = xbmc.getCondVisibility("Container.Content(TvShows)")
            IsSeasonsContent = xbmc.getCondVisibility("Container.Content(Seasons)")
            IsEpisodesContent = xbmc.getCondVisibility("Container.Content(Episodes)")
            
            #genres
            IsGenresContent = xbmc.getCondVisibility("Container.Content(Genres)")
            
            IsSpecialList = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,special://skin/Special Lists/)") and xbmc.getCondVisibility("String.Contains(Container.FolderPath,- Special Lists)")
            
            #folder path movies
            IsSetsMoviesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,videodb://movies/sets/)")
            IsGenresMoviesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,videodb://movies/genres/)")
            IsRecentlyAddedMoviesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,videodb://recentlyaddedmovies/)")
            IsMyListMoviesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,special://skin/Special Lists/Movies - Special Lists/_mylist_movies.xsp)")
            #unused for now:
            IsRecentlyWatchedMoviesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,special://skin/Special Lists/Movies - Special Lists - Special Lists/movies_by_recently_played.xsp)")
            
            #folder path tv shows
            IsGenresTvShowsFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,videodb://tvshows/genres/)")
            IsMyListTvShowsFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,special://skin/Special Lists/TV shows - Special Lists/_mylist_tvshows.xsp)")
            IsRecentlyAddedEpisodesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,videodb://recentlyaddedepisodes/)")
            IsRecentlyWatchedEpisodesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,special://skin/Special Lists/TV shows - Special Lists/episodes_by_recently_played.xsp)")
            IsMyListEpisodesFolderPath = xbmc.getCondVisibility("String.StartsWith(Container.FolderPath,special://skin/Special Lists/TV shows - Special Lists/_mylist_episodes.xsp)")
            
            #switchToView = False
            
            # 901 = "Text"
            #  52 = "Modern"
            # 500 = "Wall 2X"
            # 908 = "Wall 3X"
            # 909 = "Wall 4X"
            # 508 = "Fanart"
            # 509 = "Seasons"
            # 510 = "Episodes"
            
            
            # standard video files without db entries
            if IsFilesContent and not IsVideoDb:
              switchToView = ForcePresetViewsVideosCategory_B
            
            
            # global movies
            if IsMovieContent and not IsSetsMoviesFolderPath and not IsGenresMoviesFolderPath and not IsRecentlyAddedMoviesFolderPath and not IsSpecialList and not IsMyListMoviesFolderPath:
              switchToView = ForcePresetViewsMoviesCategory_A#CAT A   "Wall 2X"
            if IsMovieContent and not IsSetsMoviesFolderPath and not IsGenresMoviesFolderPath and not IsRecentlyAddedMoviesFolderPath and IsSpecialList and not IsMyListMoviesFolderPath:
              switchToView = ForcePresetViewsMoviesCategory_A#CAT A   "Wall 2X"
            
            # actors
            if IsActorsContent:
              switchToView = ForcePresetViewsGlobalCategory_B
            
            # movies: "my list"
            if IsMovieContent and IsMyListMoviesFolderPath:
              switchToView = ForcePresetViewsMoviesCategory_C#CAT C   "Fanart"
            
            # movie genres: list movies of selected genre
            if IsMovieContent and IsGenresMoviesFolderPath:
              switchToView = ForcePresetViewsMoviesCategory_A#CAT A   "Wall 2X"
            
            # movie sets: list sets
            if IsSetsContent:
              switchToView = ForcePresetViewsMoviesCategory_A#CAT A   "Wall 2X"
            
            # movie sets: list movies of set
            if IsMovieContent and IsSetsMoviesFolderPath:
              switchToView = ForcePresetViewsMoviesCategory_B#CAT B   "Fanart"
            
            # recently added movies
            if IsRecentlyAddedMoviesFolderPath:
              switchToView = ForcePresetViewsMoviesCategory_C#CAT C   "Fanart"
            
          
            # global tv shows
            if (IsTvShowsContent and not IsGenresTvShowsFolderPath and not IsSpecialList and not IsMyListTvShowsFolderPath) or (IsTvShowsContent and not IsMyListTvShowsFolderPath and IsSpecialList):
              switchToView = ForcePresetViewsTvShowsCategory_A#CAT J   "Fanart"
            
            # global tv show seasons
            if IsSeasonsContent and not IsGenresTvShowsFolderPath:
              switchToView = ForcePresetViewsTvShowsCategory_C# "Seasons" view is best ######
            
            # tv shows genres: list shows in selected genre
            if IsTvShowsContent and IsGenresTvShowsFolderPath:
              switchToView = ForcePresetViewsTvShowsCategory_A#CAT J   "Fanart"
            
            # tv show seasons: list seasons in selected genre
            if IsSeasonsContent and IsGenresTvShowsFolderPath:
              switchToView = ForcePresetViewsTvShowsCategory_C# "Seasons" view is best ######
            
            # tv shows: list shows in "my list"
            if IsTvShowsContent and IsMyListTvShowsFolderPath:
              switchToView = ForcePresetViewsTvShowsCategory_B#CAT K
            
            
            # episodes: recently added
            if IsEpisodesContent and IsVideoDb and IsRecentlyAddedEpisodesFolderPath:
              switchToView = ForcePresetViewsTvShowsCategory_E
            
            # episodes: recently watched
            if IsEpisodesContent and not IsVideoDb and (IsRecentlyWatchedEpisodesFolderPath or IsMyListEpisodesFolderPath):
              switchToView = ForcePresetViewsTvShowsCategory_E
            
            # episodes
            if IsEpisodesContent and not IsRecentlyAddedEpisodesFolderPath and not IsRecentlyWatchedEpisodesFolderPath and not IsMyListEpisodesFolderPath:# removed "and IsVideoDb" TEST
              
              switchToView = ForcePresetViewsTvShowsCategory_D
              
              isSortMethodEpisode = xbmc.getCondVisibility('String.IsEqual(Container.SortMethod,$LOCALIZE[20359])')#20359="Episode"
              
              ForceFirstEpisodeItemFocus = not xbmc.getCondVisibility("Skin.HasSetting(ForceFirstEpisodeItemFocusDisable)") and not lastContainerPathWasEmpty
              
              finalFirstPageActions = 0
              
              if ForceFirstEpisodeItemFocus:
                xbmc.executebuiltin('Action(firstpage)')
              
              if not isSortMethodEpisode and not lastContainerPathWasEmpty:
                finalFirstPageActions = 1
                xbmc.executebuiltin('Container.SetSortMethod(23)')#23=Episode (conflicting Forum+Wiki Info about this. 23 works for Krypton)
                if ForceFirstEpisodeItemFocus:
                  xbmc.executebuiltin('Action(firstpage)')
                xbmc.sleep(25)#short wait before SortDirection check
              else:
                if ForceFirstEpisodeItemFocus:
                  xbmc.executebuiltin('Action(firstpage)')
              
              if xbmc.getCondVisibility('Container.SortDirection(descending)') and not lastContainerPathWasEmpty:
                finalFirstPageActions = 1
                xbmc.executebuiltin('Container.SetSortDirection()')
                if ForceFirstEpisodeItemFocus:
                  xbmc.executebuiltin('Action(firstpage)')
              else:
                if ForceFirstEpisodeItemFocus:
                  xbmc.executebuiltin('Action(firstpage)')
              
              if finalFirstPageActions and ForceFirstEpisodeItemFocus:
                xbmc.sleep(25)#short wait before final firstpage actions (making sure first item is always selected when viewing episodes)
                for x in range(finalFirstPageActions):
                  xbmc.executebuiltin('Action(firstpage)')
            
            
            if not switchToView and not xbmc.getCondVisibility("Container.Content(Genres)") and not xbmc.getCondVisibility("Container.Content(Years)") and not xbmc.getCondVisibility("Container.Content(Directors)") and not xbmc.getCondVisibility("Container.Content(Studios)") and not xbmc.getCondVisibility("Container.Content(Countries)") and not xbmc.getCondVisibility("Container.Content(Tags)") and not IsAddonsContent and not IsAddon:
              switchToView = ForcePresetViewsVideosCategory_A
          
          
          
          if switchToView:
            viewLabelCompare = ''
            if switchToView == 500:
              viewLabelCompare = 'Wall 2X'
            if switchToView == 908:
              viewLabelCompare = 'Wall 3X'
            if switchToView == 909:
              viewLabelCompare = 'Wall 4X'
            if switchToView == 508:
              viewLabelCompare = xbmc.getLocalizedString(31029)#'Fanart'
            if switchToView == 901:
              viewLabelCompare = 'Text'
            if switchToView == 509:
              viewLabelCompare = 'Seasons'
            if switchToView == 510:
              viewLabelCompare = 'Episodes'
            if switchToView == 52:
              viewLabelCompare = 'Modern'
            
            #ViewsVideoLibrary
            if switchToView == 50:
              viewLabelCompare = xbmc.getLocalizedString(535)#'List'
            if switchToView == 51:
              viewLabelCompare = 'List Wide'
            if switchToView == 503:
              viewLabelCompare = xbmc.getLocalizedString(544)+' 2'#'Media info 2'
            if switchToView == 504:
              viewLabelCompare = xbmc.getLocalizedString(544)#'Media info'
            if switchToView == 515:
              viewLabelCompare = xbmc.getLocalizedString(544)+' 3'#'Media info 3'
            
            #ViewsFileMode
            if switchToView == 505:
              viewLabelCompare = xbmc.getLocalizedString(539)#'Wide'
            
            #ViewsMusicLibrary
            if switchToView == 588:
              viewLabelCompare = 'Songs'
            
            currentView = xbmc.getInfoLabel("Container.ViewMode")
            
            
            
            if currentView != viewLabelCompare:
              xbmc.executebuiltin('Container.SetViewMode('+str(switchToView)+')')
              if (switchToView == 508 or switchToView == 509) and showParentDirItems:
                # if we just switched to fanart view (508)
                # wait a bit before proceeding to ParentFolder Item skip
                xbmc.sleep(25)
            
            
            if showParentDirItems:
              # Move-Skip ParentFolderItem for Fanart View (on content load)
              FanartViewHasFocus = xbmc.getCondVisibility("Control.HasFocus(508)")
              if FanartViewHasFocus:
                ListItemIsParentFolder = xbmc.getCondVisibility("Container(508).ListItem.IsParentFolder")
                if ListItemIsParentFolder:
                  xbmc.executebuiltin("Control.Move(508,1)")
              SeasonsViewHasFocus = xbmc.getCondVisibility("Control.HasFocus(509)")
              if SeasonsViewHasFocus:
                ListItemIsParentFolder = xbmc.getCondVisibility("Container(509).ListItem.IsParentFolder")
                if ListItemIsParentFolder:
                  xbmc.executebuiltin("Control.Move(509,1)")
  
  
  
  
  
  
  # INTERVAL 2
  
  if TimerInterval_2_Enabled and (timeNow - TimerInterval_2) > TimerInterval_2_ResetSec:
    
    
    if TimerInterval_2_FirstRunDone == 1:
      TimerInterval_2_FirstRunDone = 2
    elif TimerInterval_2_FirstRunDone < 1:
        TimerInterval_2_FirstRunDone = 1
    
    
    TimerInterval_2 = time.time()
    
    IsScrolling = xbmc.getCondVisibility("Container.Scrolling")
    
    if not IsScrolling:
      
      # --------------------------------------------------------------------------------
      # Get System.ProfileName Initials
      # --------------------------------------------------------------------------------
      SystemProfileName = xbmc.getInfoLabel('System.ProfileName')
      ProfileNameInitial = SystemProfileName[:1] if SystemProfileName else ''
      if ProfileNameInitial != xbmcgui.Window(10000).getProperty('CinemaHelper.ProfileNameInitial'):
        xbmc.executebuiltin('SetProperty(CinemaHelper.ProfileNameInitial,'+ProfileNameInitial+',home)')
      
      # --------------------------------------------------------------------------------
      # Move-Skip ParentFolderItem for Fanart View (on Idle)
      # --------------------------------------------------------------------------------
      if playerMonitor.skinIsACZG and showParentDirItems:
        # Move-Skip ParentFolderItem for Fanart View (on Idle)
        FanartViewHasFocus = xbmc.getCondVisibility("Control.HasFocus(508)")
        if FanartViewHasFocus:# and bool(xbmc.getCondVisibility("Window.Is(Videos)"))
          FanartViewListItemIsParentFolder = xbmc.getCondVisibility("Container(508).ListItem.IsParentFolder")
          tmpKodiIdleTime = xbmc.getGlobalIdleTime()
          if FanartViewListItemIsParentFolder and tmpKodiIdleTime > 1:
            xbmc.executebuiltin("Control.Move(508,1)")
      
      
      # --------------------------------------------------------------------------------
      # Clear PlayBackJustStarted / PlayBackJustEnded after X seconds
      # --------------------------------------------------------------------------------
      PlayBackJustStarted = xbmcgui.Window(10000).getProperty('PlayBackJustStarted')
      
      if PlayBackJustStarted == "True":
        tmpTimerDifference = timeNow - playerMonitor.startTimer
        if tmpTimerDifference > float(0.80):
          xbmc.executebuiltin("SetProperty(PlayBackJustStarted,,home)")
      
      PlayBackJustEnded = xbmcgui.Window(10000).getProperty('PlayBackJustEnded')
      
      if PlayBackJustEnded == "True":
        tmpTimerDifference = timeNow - playerMonitor.endTimer
        if tmpTimerDifference > float(0.80):
          xbmc.executebuiltin("SetProperty(PlayBackJustEnded,,home)")
      
      
      
      PlayerHasMedia = xbmc.getCondVisibility("Player.HasMedia")
      PlayerHasVideo = xbmc.getCondVisibility("Player.HasVideo")
      PlayerHasAudio = xbmc.getCondVisibility("Player.HasAudio")
      
      playingVideo = PlayerHasMedia and PlayerHasVideo
      playingAudio = PlayerHasMedia and PlayerHasAudio and not PlayerHasVideo
      
      
      # --------------------------------------------------------------------------------
      # Auto Close VideoOSD/MusicOSD when Idle
      # --------------------------------------------------------------------------------
      if (playingVideo or playingAudio):
        tmpTimerDifference = timeNow - playerMonitor.idleCheckIntervalTimer
        
        if tmpTimerDifference > float(2.50):
          
          if playerMonitor.skinIsACZG:
            
            tmpKodiIdleTime = xbmc.getGlobalIdleTime()
            
            if tmpKodiIdleTime > 6:
              
              # Only auto close if subtitle search dialog and similar dialogs are not open
              
              # Check for OsdSubtitleSettings on Kodi 18+, skip this check on Kodi 17
              OsdSubtitleSettingsIsOpen = xbmc.getCondVisibility('Window.IsVisible(OsdSubtitleSettings)') if playerMonitor.isKodi18plus else False
              
              checkForOpenDialogsPassed = not OsdSubtitleSettingsIsOpen and not xbmc.getCondVisibility('Window.IsVisible(OsdVideoSettings)') and not xbmc.getCondVisibility('Window.IsVisible(OsdAudioSettings)') and not xbmc.getCondVisibility('Window.IsVisible(SubtitleSearch)') and not xbmc.getCondVisibility('Window.IsVisible(VideoBookmarks)') and not xbmc.getCondVisibility('Window.IsVisible(SelectDialog)')
              
              if checkForOpenDialogsPassed:
                  
                  if xbmc.getCondVisibility('Window.IsActive(VideoOSD)'):
                    xbmc.executebuiltin('Dialog.Close(VideoOSD)')
                  if xbmc.getCondVisibility('Window.IsActive(MusicOSD)'):
                    xbmc.executebuiltin('Dialog.Close(MusicOSD)')
            
            
            playerMonitor.idleCheckIntervalTimer = time.time()
      
      
      # --------------------------------------------------------------------------------
      # Save Player DB Movie progress %
      # --------------------------------------------------------------------------------
      if playingVideo and playerMonitor.VideoPlayerIsMovieInDb:
        
        tmpTimerDifference = timeNow - playerMonitor.percentageTimer
        
        if tmpTimerDifference > float(5.00):
          
          jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetProperties","params":{"playerid":1,"properties":["percentage"]},"id":"1"}')
          jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
          jsonQuery = simplejson.loads(jsonQuery)
          
          tmpHasKeyCheck = 'result' in jsonQuery and 'percentage' in jsonQuery['result']
          if tmpHasKeyCheck:
            playerMonitor.playerPercentage = int(jsonQuery['result']['percentage'])
          
          playerMonitor.percentageTimer = time.time()


      # --------------------------------------------------------------------------------
      # CinemaHelper.UserRating
      # --------------------------------------------------------------------------------
      UserRatingPROCESS = bool(xbmcgui.Window(10000).getProperty('CinemaHelper.UserRating.PROCESS'))
      
      if UserRatingPROCESS:
        UserRatingDbId   = int(xbmcgui.Window(10000).getProperty('CinemaHelper.UserRating.DbId'))
        UserRatingDbType = str(xbmcgui.Window(10000).getProperty('CinemaHelper.UserRating.DbType'))
        UserRatingAction = str(xbmcgui.Window(10000).getProperty('CinemaHelper.UserRating.Action'))
        
        UserRatingIsMovie = UserRatingDbType == "movie"
        UserRatingIsEpisode = UserRatingDbType == "episode"
        UserRatingIsTvShow = UserRatingDbType == "tvshow"
        
        if UserRatingAction and UserRatingDbId and (UserRatingIsMovie or UserRatingIsEpisode or UserRatingIsTvShow):
          
          if UserRatingAction == "WatchListAdd":
            
            if UserRatingIsMovie:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetMovieDetails","params":{"movieid":'+str(UserRatingDbId)+',"userrating":1}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
            
            if UserRatingIsEpisode:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":'+str(UserRatingDbId)+',"userrating":1}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
            
            if UserRatingIsTvShow:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetTvShowDetails","params":{"tvshowid":'+str(UserRatingDbId)+',"userrating":1}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
          
          if UserRatingAction == "WatchListRemove":
            
            if UserRatingIsMovie:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetMovieDetails","params":{"movieid":'+str(UserRatingDbId)+',"userrating":0}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
            
            if UserRatingIsEpisode:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":'+str(UserRatingDbId)+',"userrating":0}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
            
            if UserRatingIsTvShow:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetTvShowDetails","params":{"tvshowid":'+str(UserRatingDbId)+',"userrating":0}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
        
        
        xbmc.executebuiltin("ClearProperty(CinemaHelper.UserRating.PROCESS,home)")
      
      
      # --------------------------------------------------------------------------------
      # CinemaHelper.WatchedState
      # --------------------------------------------------------------------------------
      WatchedStatePROCESS = bool(xbmcgui.Window(10000).getProperty('CinemaHelper.WatchedState.PROCESS'))
      
      if(WatchedStatePROCESS):
        WatchedStateDbId   = int(xbmcgui.Window(10000).getProperty('CinemaHelper.WatchedState.DbId'))
        WatchedStateDbType = str(xbmcgui.Window(10000).getProperty('CinemaHelper.WatchedState.DbType'))
        WatchedStateAction = str(xbmcgui.Window(10000).getProperty('CinemaHelper.WatchedState.Action'))
        
        WatchedStateIsMovie = WatchedStateDbType == "movie"
        WatchedStateIsEpisode = WatchedStateDbType == "episode"
        
        if WatchedStateAction and WatchedStateDbId and (WatchedStateIsMovie or WatchedStateIsEpisode):
          
          if WatchedStateAction == "SetWatched":
            if WatchedStateIsMovie:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetMovieDetails","params":{"movieid":'+str(WatchedStateDbId)+',"playcount":1,"lastplayed":""}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
            if WatchedStateIsEpisode:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":'+str(WatchedStateDbId)+',"playcount":1,"lastplayed":""}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
          
          if WatchedStateAction == "SetNotWatched":
            if WatchedStateIsMovie:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetMovieDetails","params":{"movieid":'+str(WatchedStateDbId)+',"playcount":0,"lastplayed":""}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
            if WatchedStateIsEpisode:
              jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":'+str(WatchedStateDbId)+',"playcount":0,"lastplayed":""}}')
              jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
              jsonQuery = simplejson.loads(jsonQuery)
        
        xbmc.executebuiltin("ClearProperty(CinemaHelper.WatchedState.PROCESS,home)")
  
  
  
  # INTERVAL 3
  
  if TimerInterval_3_Enabled and (timeNow - TimerInterval_3) > TimerInterval_3_ResetSec:
    TimerInterval_3 = time.time()
    
    IsScrolling = xbmc.getCondVisibility("Container.Scrolling")
    
    if not IsScrolling:
      
      
      
      
      
      
      if playerMonitor.skinIsACZG:
        
        
        jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"videolibrary.flattentvshows"},"id":1}')
        jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
        jsonQuery = simplejson.loads(jsonQuery)
        
        tmpHasKeyCheck = 'result' in jsonQuery and 'value' in jsonQuery['result']
        if tmpHasKeyCheck:
          xbmc.executebuiltin("SetProperty(CinemaHelper.GetSettingValue.videolibrary.flattentvshows,"+str(jsonQuery['result']['value'])+",home)")
        else:
          xbmc.executebuiltin("ClearProperty(CinemaHelper.GetSettingValue.videolibrary.flattentvshows,home)")
        
        
        
        
        
        
        
        # Check and synchronize UI accent color scheme with skin themes and skin colors
        
        uiColorVariant = xbmc.getInfoLabel('Skin.String(uiColorVariant)')
        
        jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.skintheme"},"id":1}')
        jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
        jsonQuery = simplejson.loads(jsonQuery)
        lookandfeelSkintheme = jsonQuery['result']['value'] if 'result' in jsonQuery and 'value' in jsonQuery['result'] else ''
        
        jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.skincolors"},"id":1}')
        jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
        jsonQuery = simplejson.loads(jsonQuery)
        lookandfeelSkincolors = jsonQuery['result']['value'] if 'result' in jsonQuery and 'value' in jsonQuery['result'] else ''
        
        
        if lookandfeelSkintheme and lookandfeelSkincolors:
          if uiColorVariant == '':
            if lookandfeelSkintheme != 'SKINDEFAULT':
              xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"lookandfeel.skintheme","value":"SKINDEFAULT"}}')
            if lookandfeelSkincolors != 'SKINDEFAULT':
              xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"lookandfeel.skincolors","value":"SKINDEFAULT"}}')
          elif uiColorVariant == '1':
            if lookandfeelSkintheme != 'Perfect Pink':
              xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"lookandfeel.skintheme","value":"Perfect Pink"}}')
            if lookandfeelSkincolors != 'Perfect Pink':
              xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"lookandfeel.skincolors","value":"Perfect Pink"}}')
          elif uiColorVariant == '2':
            if lookandfeelSkintheme != 'Electric Violet':
              xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"lookandfeel.skintheme","value":"Electric Violet"}}')
            if lookandfeelSkincolors != 'Electric Violet':
              xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"lookandfeel.skincolors","value":"Electric Violet"}}')
        
        
        
        
        
        
        
        
        AllowShowParentDirItems = xbmc.getCondVisibility("Skin.HasSetting(AllowShowParentDirItems)")
        
        if showParentDirItems and not AllowShowParentDirItems:
          jsonQuery = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"filelists.showparentdiritems","value":false},"id":1}')
          jsonQuery = unicode(jsonQuery, 'utf-8', errors='ignore') if not playerMonitor.isKodi19plus else jsonQuery# Python 2/3
          jsonQuery = simplejson.loads(jsonQuery)
      
      
      
      if playerMonitor.VideoPlayerIsMovieInDb and playerMonitor.movieHasPostCreditsScene and playerMonitor.isPlayingVideo():
        
        timeremaining = (playerMonitor.getTotalTime() - playerMonitor.getTime()) // 60
        
        if timeremaining < nearEndPreReached_Minutes:
          if not playerMonitor.nearEndPreReached:
            playerMonitor.nearEndPreReached = True
            xbmc.executebuiltin("SetProperty(CinemaHelper.player.nearEndPreReached,True,home)")
        else:
          if playerMonitor.nearEndPreReached:
            playerMonitor.nearEndPreReached = False
            xbmc.executebuiltin("ClearProperty(CinemaHelper.player.nearEndPreReached,home)")
        
        if timeremaining < nearEndReached_Minutes:
          if playerMonitor.nearEndReached == "":
            playerMonitor.nearEndReached = "True"
            xbmc.executebuiltin("SetProperty(CinemaHelper.player.nearEndReached,True,home)")
            nearEndReachedTimeOutDurationCount = 0
        
        if playerMonitor.nearEndReached == "True":
          if not playerMonitor.nearEndReached == "TrueAndTimeOut":
            if nearEndReachedTimeOutDurationCount == 2:
              playerMonitor.nearEndReached = "TrueAndTimeOut"
              xbmc.executebuiltin("SetProperty(CinemaHelper.player.nearEndReached,TrueAndTimeOut,home)")
            else:
              nearEndReachedTimeOutDurationCount += 1
      else:
        pass

#/while


