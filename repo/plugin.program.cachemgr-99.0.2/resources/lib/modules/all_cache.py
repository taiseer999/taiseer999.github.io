import xbmcgui
import xbmc, xbmcaddon
import xbmcvfs
import os
from resources.lib.modules import var
from .dataconn import create_conn, clear_db, clear_h1_db, clear_h2_db, clear_h3_db, optimize_db

dialog = xbmcgui.Dialog()
translatePath = xbmcvfs.translatePath
    
def cl_all_cache():
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
        if xbmcvfs.exists(var.chk_home):
            addon_list.append('Homelander')
        if xbmcvfs.exists(var.chk_lab):
            addon_list.append('TheLab')
        if xbmcvfs.exists(var.chk_quick):
            addon_list.append('Quicksilver')
        if xbmcvfs.exists(var.chk_genocide):
            addon_list.append('Chains Genocide')
        if xbmcvfs.exists(var.chk_absol):
            addon_list.append('Absolution')
        if xbmcvfs.exists(var.chk_shazam):
            addon_list.append('Shazam')
        if xbmcvfs.exists(var.chk_crew):
            addon_list.append('The Crew')
        if xbmcvfs.exists(var.chk_night):
            addon_list.append('Nightwing')
        if xbmcvfs.exists(var.chk_alvin):
            addon_list.append('Alvin')
        if xbmcvfs.exists(var.chk_moria):
            addon_list.append('Moria')
        if xbmcvfs.exists(var.chk_nine):
            addon_list.append('Nine Lives')
        if xbmcvfs.exists(var.chk_scrubs):
            addon_list.append('Scrubs V2')
        if xbmcvfs.exists(var.chk_labjr):
            addon_list.append('TheLabjr')
        if xbmcvfs.exists(var.chk_tmdbh):
            addon_list.append('TheMovieDb Helper')
        if xbmcvfs.exists(var.chk_rurl):
            addon_list.append('ResolveURL')
            
        addon_select = []
        dialog_select = dialog.multiselect('Cache Manager - Choose Add-ons to Clear',addon_list) #Select add-ons to clear
        if dialog_select == None:
            return
        else:
            for selection in dialog_select:
                #Create user selected list
                addon_select.append(addon_list[selection])

        if 'Seren' in addon_select:                
            cache = translatePath('special://userdata/addon_data/plugin.video.seren/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'cache')
                    optimize_db(conn, cache)
            else:
                pass
            torcache = translatePath('special://userdata/addon_data/plugin.video.seren/torrentCache.db')
            if xbmcvfs.exists(torcache):
                conn = create_conn(torcache)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshows')
                    optimize_db(conn, torcache)
            else:
                pass
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
            maincache = translatePath('special://userdata/addon_data/plugin.video.fen/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
            debrid = translatePath('special://userdata/addon_data/plugin.video.fen/databases/debridcache.db')
            if xbmcvfs.exists(debrid):
                conn = create_conn(debrid)
                with conn:
                    clear_db(conn, 'debrid_data')
                    optimize_db(conn, debrid)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.fen/databases/metacache2.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'function_cache')
                    clear_db(conn, 'metadata')
                    clear_db(conn, 'season_metadata')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.fen/databases/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
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
            maincache = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
            debrid = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/debridcache.db')
            if xbmcvfs.exists(debrid):
                conn = create_conn(debrid)
                with conn:
                    clear_db(conn, 'debrid_data')
                    optimize_db(conn, debrid)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/metacache.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'function_cache')
                    clear_db(conn, 'metadata')
                    clear_db(conn, 'season_metadata')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/external.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
            lists = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/lists.db')
            if xbmcvfs.exists(lists):
                conn = create_conn(lists)
                with conn:
                    clear_db(conn, 'lists')
                    optimize_db(conn, lists)
            else:
                pass
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
            watched = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/watched.db')
            if xbmcvfs.exists(watched):
                conn = create_conn(watched)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'watched_status')
                    clear_db(conn, 'watched')
                    optimize_db(conn, watched)
            else:
                pass
        else:
            pass
            
        if 'afFENity' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
            debrid = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/debridcache.db')
            if xbmcvfs.exists(debrid):
                conn = create_conn(debrid)
                with conn:
                    clear_db(conn, 'debrid_data')
                    optimize_db(conn, debrid)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/metacache.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'function_cache')
                    clear_db(conn, 'metadata')
                    clear_db(conn, 'season_metadata')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/external.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
            lists = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/lists.db')
            if xbmcvfs.exists(lists):
                conn = create_conn(lists)
                with conn:
                    clear_db(conn, 'lists')
                    optimize_db(conn, lists)
            else:
                pass
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
            watched = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/watched.db')
            if xbmcvfs.exists(watched):
                conn = create_conn(watched)
                with conn:
                    clear_db(conn, 'progress')
                    clear_db(conn, 'watched_status')
                    clear_db(conn, 'watched')
                    optimize_db(conn, watched)
            else:
                pass
        else:
            pass
        
        if 'Ezra' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.ezra/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
            debrid = translatePath('special://userdata/addon_data/plugin.video.ezra/databases/debridcache.db')
            if xbmcvfs.exists(debrid):
                conn = create_conn(debrid)
                with conn:
                    clear_db(conn, 'debrid_data')
                    optimize_db(conn, debrid)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.ezra/databases/metacache.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'function_cache')
                    clear_db(conn, 'metadata')
                    clear_db(conn, 'season_metadata')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.ezra/databases/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
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
            maincache = translatePath('special://userdata/addon_data/plugin.video.coalition/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
            debrid = translatePath('special://userdata/addon_data/plugin.video.coalition/databases/debridcache.db')
            if xbmcvfs.exists(debrid):
                conn = create_conn(debrid)
                with conn:
                    clear_db(conn, 'debrid_data')
                    optimize_db(conn, debrid)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.coalition/databases/metacache.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'function_cache')
                    clear_db(conn, 'metadata')
                    clear_db(conn, 'season_metadata')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.coalition/databases/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
            trakt = translatePath('special://userdata/addon_data/plugin.video.coalition/databases/traktcache4.db')
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
            maincache = translatePath('special://userdata/addon_data/plugin.video.pov/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
            debrid = translatePath('special://userdata/addon_data/plugin.video.pov/databases/debridcache.db')
            if xbmcvfs.exists(debrid):
                conn = create_conn(debrid)
                with conn:
                    clear_db(conn, 'debrid_data')
                    optimize_db(conn, debrid)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.pov/databases/metacache.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'function_cache')
                    clear_db(conn, 'metadata')
                    clear_db(conn, 'season_metadata')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.pov/databases/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
            trakt = translatePath('special://userdata/addon_data/plugin.video.pov/databases/traktcache4.db')
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
            maincache = translatePath('special://userdata/addon_data/plugin.video.taz19/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
            debrid = translatePath('special://userdata/addon_data/plugin.video.taz19/databases/debridcache.db')
            if xbmcvfs.exists(debrid):
                conn = create_conn(debrid)
                with conn:
                    clear_db(conn, 'debrid_data')
                    optimize_db(conn, debrid)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.taz19/databases/metacache.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'function_cache')
                    clear_db(conn, 'metadata')
                    clear_db(conn, 'season_metadata')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.taz19/databases/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
            trakt = translatePath('special://userdata/addon_data/plugin.video.taz19/databases/traktcache4.db')
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
            cache = translatePath('special://userdata/addon_data/plugin.video.umbrella/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'cache')
                    optimize_db(conn, cache)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.umbrella/providers.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'cache')
                    clear_db(conn, 'rel_aliases')
                    clear_db(conn, 'rel_src')
                    optimize_db(conn, provider)
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.umbrella/search.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
            trakt = translatePath('special://userdata/addon_data/plugin.video.umbrella/traktSync.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'hiddenProgress')
                    clear_db(conn, 'liked_lists')
                    clear_db(conn, 'movies_collection')
                    clear_db(conn, 'movies_watchlist')
                    clear_db(conn, 'public_lists')
                    clear_db(conn, 'service')
                    clear_db(conn, 'shows_collection')
                    clear_db(conn, 'shows_watchlist')
                    clear_db(conn, 'user_lists')
                    clear_db(conn, 'watched')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass

        if 'OneMoar' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.onemoar/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'cache')
                    optimize_db(conn, cache)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.onemoar/providers.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'cache')
                    clear_db(conn, 'rel_aliases')
                    clear_db(conn, 'rel_src')
                    optimize_db(conn, provider)
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.onemoar/search.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
            trakt = translatePath('special://userdata/addon_data/plugin.video.onemoar/traktSync.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'hiddenProgress')
                    clear_db(conn, 'liked_lists')
                    clear_db(conn, 'movies_collection')
                    clear_db(conn, 'movies_watchlist')
                    clear_db(conn, 'public_lists')
                    clear_db(conn, 'service')
                    clear_db(conn, 'shows_collection')
                    clear_db(conn, 'shows_watchlist')
                    clear_db(conn, 'user_lists')
                    clear_db(conn, 'watched')
                    optimize_db(conn, trakt)
            else:
                pass
        else:
            pass
        
        if 'Dradis' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.dradis/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'cache')
                    optimize_db(conn, cache)
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.dradis/search.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.dradis/providers.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'cache')
                    clear_db(conn, 'rel_aliases')
                    clear_db(conn, 'rel_src')
                    optimize_db(conn, provider)
            else:
                pass
            trakt = translatePath('special://userdata/addon_data/plugin.video.dradis/traktsync.db')
            if xbmcvfs.exists(trakt):
                conn = create_conn(trakt)
                with conn:
                    clear_db(conn, 'hiddenProgress')
                    clear_db(conn, 'liked_lists')
                    clear_db(conn, 'movies_collection')
                    clear_db(conn, 'movies_watchlist')
                    clear_db(conn, 'public_lists')
                    clear_db(conn, 'service')
                    clear_db(conn, 'shows_collection')
                    clear_db(conn, 'shows_watchlist')
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
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
                    clear_db(conn, 'search_string2')
                    optimize_db(conn, cache)
            else:
                pass
            sources = translatePath('special://userdata/addon_data/plugin.video.shadow/cache_f/sources.db')
            if xbmcvfs.exists(sources):
                conn = create_conn(sources)
                with conn:
                    clear_db(conn, 'pages')
                    clear_db(conn, 'posters')
                    optimize_db(conn, sources)
            else:
                pass
        else:
            pass

        if 'Ghost' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.ghost/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
                    clear_db(conn, 'search_string2')
                    optimize_db(conn, cache)
            else:
                pass
            sources = translatePath('special://userdata/addon_data/plugin.video.ghost/cache_f/sources.db')
            if xbmcvfs.exists(sources):
                conn = create_conn(sources)
                with conn:
                    clear_db(conn, 'pages')
                    clear_db(conn, 'posters')
                    optimize_db(conn, sources)
            else:
                pass
        else:
            pass
        
        if 'Base' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.base/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
                    clear_db(conn, 'search_string2')
                    optimize_db(conn, cache)
            else:
                pass
            sources = translatePath('special://userdata/addon_data/plugin.video.base/cache_f/sources.db')
            if xbmcvfs.exists(sources):
                conn = create_conn(sources)
                with conn:
                    clear_db(conn, 'pages')
                    clear_db(conn, 'posters')
                    optimize_db(conn, sources)
            else:
                pass
        else:
            pass

        if 'Unleashed' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.unleashed/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
                    clear_db(conn, 'search_string2')
                    optimize_db(conn, cache)
            else:
                pass
            sources = translatePath('special://userdata/addon_data/plugin.video.unleashed/cache_f/sources.db')
            if xbmcvfs.exists(sources):
                conn = create_conn(sources)
                with conn:
                    clear_db(conn, 'pages')
                    clear_db(conn, 'posters')
                    optimize_db(conn, sources)
            else:
                pass
        else:
            pass

        if 'Magic Dragon' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.magicdragon/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
                    clear_db(conn, 'search_string2')
                    optimize_db(conn, cache)
            else:
                pass
            sources = translatePath('special://userdata/addon_data/plugin.video.magicdragon/cache_f/sources.db')
            if xbmcvfs.exists(sources):
                conn = create_conn(sources)
                with conn:
                    clear_db(conn, 'pages')
                    clear_db(conn, 'posters')
                    optimize_db(conn, sources)
            else:
                pass
        else:
            pass

        if 'Asgard' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.asgard/database.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
                    clear_db(conn, 'search_string2')
                    optimize_db(conn, cache)
            else:
                pass
            sources = translatePath('special://userdata/addon_data/plugin.video.asgard/cache_f/sources.db')
            if xbmcvfs.exists(sources):
                conn = create_conn(sources)
                with conn:
                    clear_db(conn, 'pages')
                    clear_db(conn, 'posters')
                    optimize_db(conn, sources)
            else:
                pass
        else:
            pass
        
        if 'Homelander' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.homelander/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.homelander/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.homelander/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.homelander/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'TheLab' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.thelab/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.thelab/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.thelab/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.thelab/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Quicksilver' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.quicksilver/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.quicksilver/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.quicksilver/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.quicksilver/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Chains Genocide' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Absolution' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.absolution/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.absolution/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.absolution/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.absolution/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Shazam' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.shazam/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.shazam/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.shazam/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.shazam/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'The Crew' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.thecrew/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.thecrew/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.thecrew/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.thecrew/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass
        
        if 'Nightwing' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.nightwing/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.nightwing/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.nightwing/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.nightwing/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Alvin' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.alvin/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.alvin/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.alvin/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.alvin/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Moria' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.moria/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.moria/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.moria/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.moria/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Nine Lives' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.nine/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.nine/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.nine/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.nine/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'Scrubs V2' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.scrubsv2/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.scrubsv2/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.scrubsv2/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.scrubsv2/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'TheLabjr' in addon_select:
            cache = translatePath('special://userdata/addon_data/plugin.video.thelabjr/cache.db')
            if xbmcvfs.exists(cache):
                conn = create_conn(cache)
                with conn:
                    clear_db(conn, 'rel_list')
                    clear_db(conn, 'rel_lib')
                    optimize_db(conn, cache)
            else:
                pass
            metadata = translatePath('special://userdata/addon_data/plugin.video.thelabjr/meta.5.db')
            if xbmcvfs.exists(metadata):
                conn = create_conn(metadata)
                with conn:
                    clear_db(conn, 'meta')
                    optimize_db(conn, metadata)
            else:
                pass
            provider = translatePath('special://userdata/addon_data/plugin.video.thelabjr/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
            search = translatePath('special://userdata/addon_data/plugin.video.thelabjr/search.1.db')
            if xbmcvfs.exists(search):
                conn = create_conn(search)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshow')
                    clear_db(conn, 'people')
                    clear_db(conn, 'sqlite_sequence')
                    optimize_db(conn, search)
            else:
                pass
        else:
            pass

        if 'TheMovieDb Helper' in addon_select:
            tmdb = translatePath('special://userdata/addon_data/plugin.video.themoviedb.helper/TMDb.db')
            if xbmcvfs.exists(tmdb):
                conn = create_conn(tmdb)
                with conn:
                    clear_db(conn, 'simple_cache')
                    optimize_db(conn, tmdb)
            else:
                pass
            history = translatePath('special://userdata/addon_data/plugin.video.themoviedb.helper/search_history.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'simple_cache')
                    optimize_db(conn, history)
            else:
                pass
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

        if 'ResolveURL' in addon_select:
            try:
                cache = translatePath('special://userdata/addon_data/script.module.resolveurl/cache/')
                if xbmcvfs.exists(cache):
                    files_dst = os.listdir(cache)
                    for file in files_dst:
                            file_path = os.path.join(cache, file)
                            if os.path.isfile(file_path):
                                    os.remove(file_path)
            except:
                pass
            
        xbmcgui.Dialog().notification('Cache Manager', 'All Cache Cleared!',xbmcgui.NOTIFICATION_INFO, 3000)
