import xbmcgui
import xbmc, xbmcaddon
import xbmcvfs
import sqlite3 as sqlt
from resources.lib.modules import var
from .dataconn import create_conn, clear_db, optimize_db

dialog = xbmcgui.Dialog()
translatePath = xbmcvfs.translatePath
    
def cl_trakt():
        addon_list = []
        if xbmcvfs.exists(var.chk_seren):
            addon_list.append('Seren')
        if xbmcvfs.exists(var.chk_fen):
            addon_list.append('Fen')
        if xbmcvfs.exists(var.chk_fen_light):
            addon_list.append('Fen Light')
        if xbmcvfs.exists(var.chk_affen):
            addon_list.append('afFENity')
        if xbmcvfs.exists(var.chk_ezra):
            addon_list.append('Ezra')
        if xbmcvfs.exists(var.chk_coal):
            addon_list.append('The Coalition')
        if xbmcvfs.exists(var.chk_pov):
            addon_list.append('POV')
        if xbmcvfs.exists(var.chk_umb):
            addon_list.append('Umbrella')
        if xbmcvfs.exists(var.chk_onem):
            addon_list.append('OneMoar')
        if xbmcvfs.exists(var.chk_dradis):
            addon_list.append('Dradis')
        if xbmcvfs.exists(var.chk_taz):
            addon_list.append('Taz19')
        if xbmcvfs.exists(var.chk_shadow):
            addon_list.append('Shadow')
        if xbmcvfs.exists(var.chk_ghost):
            addon_list.append('Ghost')
        if xbmcvfs.exists(var.chk_base):
            addon_list.append('Base')
        if xbmcvfs.exists(var.chk_unleashed):
            addon_list.append('Unleashed')
        if xbmcvfs.exists(var.chk_md):
            addon_list.append('Magic Dragon')
        if xbmcvfs.exists(var.chk_asgard):
            addon_list.append('Asgard')
        if xbmcvfs.exists(var.chk_tmdbh):
            addon_list.append('TheMovieDb Helper')
            
        addon_select = []
        dialog_select = dialog.multiselect('Cache Manager - Choose Add-ons to Clear',addon_list) #Select add-ons to clear
        if dialog_select == None:
            return
        else:
            for selection in dialog_select:
                #Create user selected list
                addon_select.append(addon_list[selection])

        if 'Seren' in addon_select:                
            trakt = translatePath('special://userdata/addon_data/plugin.video.seren/traktSync.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'activities')
                    clear_db(conn, 'bookmarks')
                    clear_db(conn, 'episodes')
                    clear_db(conn, 'episodes_meta')
                    clear_db(conn, 'hidden')
                    clear_db(conn, 'lists')
                    clear_db(conn, 'movies')
                    clear_db(conn, 'movies_meta')
                    clear_db(conn, 'seasons')
                    clear_db(conn, 'seasons_meta')
                    clear_db(conn, 'shows')
                    clear_db(conn, 'shows_meta')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
            
        if 'Fen' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.fen/databases/traktcache4.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'trakt_data')
                    clear_db(conn, 'watched_status')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
            
        if 'Fen Light' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/traktcache.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'trakt_data')
                    clear_db(conn, 'watched_status')
                    clear_db(conn, 'watched')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
            
        if 'afFENity' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/traktcache.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'trakt_data')
                    clear_db(conn, 'watched_status')
                    clear_db(conn, 'watched')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
        
        if 'Ezra' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.ezra/databases/traktcache4.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'trakt_data')
                    clear_db(conn, 'watched_status')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass

        if 'The Coalition' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.coalition/traktcache4.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'trakt_data')
                    clear_db(conn, 'watched_status')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
        
        if 'POV' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.pov/traktcache4.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'trakt_data')
                    clear_db(conn, 'watched_status')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass

        if 'Taz19' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.taz19/traktcache4.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'trakt_data')
                    clear_db(conn, 'watched_status')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
        
        if 'Umbrella' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.umbrella/traktSync.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'bookmarks')
                    clear_db(conn, 'hiddenProgress')
                    clear_db(conn, 'liked_lists')
                    clear_db(conn, 'movies_collection')
                    clear_db(conn, 'movies_watchlist')
                    clear_db(conn, 'public_lists')
                    clear_db(conn, 'popular_lists')
                    clear_db(conn, 'service')
                    clear_db(conn, 'shows_collection')
                    clear_db(conn, 'shows_watchlist')
                    clear_db(conn, 'trending_lists')
                    clear_db(conn, 'user_lists')
                    clear_db(conn, 'watched')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass

        if 'OneMoar' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.onemoar/traktSync.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'bookmarks')
                    clear_db(conn, 'hiddenProgress')
                    clear_db(conn, 'liked_lists')
                    clear_db(conn, 'movies_collection')
                    clear_db(conn, 'movies_watchlist')
                    clear_db(conn, 'public_lists')
                    clear_db(conn, 'popular_lists')
                    clear_db(conn, 'service')
                    clear_db(conn, 'shows_collection')
                    clear_db(conn, 'shows_watchlist')
                    clear_db(conn, 'trending_lists')
                    clear_db(conn, 'user_lists')
                    clear_db(conn, 'watched')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
        
        if 'Dradis' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.dradis/traktsync.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'bookmarks')
                    clear_db(conn, 'hiddenProgress')
                    clear_db(conn, 'liked_lists')
                    clear_db(conn, 'movies_collection')
                    clear_db(conn, 'movies_watchlist')
                    clear_db(conn, 'public_lists')
                    clear_db(conn, 'popular_lists')
                    clear_db(conn, 'service')
                    clear_db(conn, 'shows_collection')
                    clear_db(conn, 'shows_watchlist')
                    clear_db(conn, 'trending_lists')
                    clear_db(conn, 'user_lists')
                    clear_db(conn, 'watched')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass

        if 'Shadow' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.shadow/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'lastepisode')
                    optimize_db(conn, cache)
                    optimize_db(conn, cache)
            else:
                pass
        else:
            pass

        if 'Ghost' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.ghost/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'lastepisode')
                    optimize_db(conn, cache)
                    optimize_db(conn, cache)
            else:
                pass
        else:
            pass
        
        if 'Base' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.base/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'lastepisode')
                    optimize_db(conn, cache)
                    optimize_db(conn, cache)
            else:
                pass
        else:
            pass

        if 'Unleashed' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.unleashed/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'lastepisode')
                    optimize_db(conn, cache)
                    optimize_db(conn, cache)
            else:
                pass
        else:
            pass

        if 'Magic Dragon' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.magicdragon/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'lastepisode')
                    optimize_db(conn, cache)
                    optimize_db(conn, cache)
            else:
                pass
        else:
            pass

        if 'Asgard' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.asgard/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'lastepisode')
                    optimize_db(conn, cache)
            else:
                pass
        else:
            pass
        
        if 'TheMovieDb Helper' in addon_select:
            trakt = translatePath('special://userdata/addon_data/plugin.video.themoviedb.helper/TraktAPI.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'simple_cache')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
        
        xbmcgui.Dialog().notification('Cache Manager', 'Trakt Cache Cleared!',xbmcgui.NOTIFICATION_INFO, 3000)
