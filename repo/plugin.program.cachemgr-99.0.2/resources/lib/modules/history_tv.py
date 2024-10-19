import xbmcgui
import xbmc, xbmcaddon
import xbmcvfs
import sqlite3 as sqlt
from resources.lib.modules import var
from .dataconn import create_conn, clear_db, clear_h1_db, clear_h2_db, clear_h3_db, clear_h4_db, optimize_db

dialog = xbmcgui.Dialog()
translatePath = xbmcvfs.translatePath
    
def cl_tvhistory():
        addon_list = []
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
            
        addon_select = []
        dialog_select = dialog.multiselect('Cache Manager - Choose Add-ons to Clear',addon_list) #Select add-ons to clear
        if dialog_select == None:
            return
        else:
            for selection in dialog_select:
                #Create user selected list
                addon_select.append(addon_list[selection])

        if 'Fen' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.fen/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_h1_db(conn, '%tv_search%', 'maincache')
                    clear_h1_db(conn, '%tvshow_queries%', 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
        else:
            pass
            
        if 'Fen Light' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_h1_db(conn, '%tv_search%', 'maincache')
                    clear_h1_db(conn, '%tvshow_queries%', 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
        else:
            pass
            
        if 'afFENity' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_h1_db(conn, '%tv_search%', 'maincache')
                    clear_h1_db(conn, '%tvshow_queries%', 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
        else:
            pass
        
        if 'Ezra' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.ezra/databases/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_h1_db(conn, '%tv_search%', 'maincache')
                    clear_h1_db(conn, '%tvshow_queries%', 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
        else:
            pass

        if 'The Coalition' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.coalition/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_h1_db(conn, '%tv_search%', 'maincache')
                    clear_h1_db(conn, '%tvshow_queries%', 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
        else:
            pass
        
        if 'POV' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.pov/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_h1_db(conn, '%tv_search%', 'maincache')
                    clear_h1_db(conn, '%tvshow_queries%', 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
        else:
            pass

        if 'Taz19' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.taz19/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_h1_db(conn, '%tv_search%', 'maincache')
                    clear_h1_db(conn, '%tvshow_queries%', 'maincache')
                    optimize_db(conn, maincache)
            else:
                pass
        else:
            pass
        
        if 'Umbrella' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.umbrella/search.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'OneMoar' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.onemoar/search.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass
        
        if 'Dradis' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.dradis/search.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Shadow' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.shadow/database.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_h4_db(conn, 'tv', 'search_string2')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Ghost' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.ghost/database.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_h4_db(conn, 'tv', 'search_string2')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass
        
        if 'Base' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.base/database.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_h4_db(conn, 'tv', 'search_string2')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Unleashed' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.unleashed/database.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_h4_db(conn, 'tv', 'search_string2')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Magic Dragon' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.magicdragon/database.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_h4_db(conn, 'tv', 'search_string2')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Asgard' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.asgard/database.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_h4_db(conn, 'tv', 'search_string2')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass
        
        if 'Homelander' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.homelander/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'TheLab' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.thelab/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Quicksilver' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.quicksilver/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Chains Genocide' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Absolution' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.absolution/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Shazam' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.shazam/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'The Crew' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.thecrew/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Nightwing' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.nightwing/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Alvin' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.alvin/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Moria' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.moria/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Nine Lives' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.nine/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'Scrubs V2' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.scrubsv2/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'TheLabjr' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.thelabjr/search.1.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_db(conn, 'tvshow')
                    clear_h2_db(conn, 'tvshow', 'sqlite_sequence')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        if 'TheMovieDb Helper' in addon_select:
            history = translatePath('special://userdata/addon_data/plugin.video.themoviedb.helper/search_history.db')
            if xbmcvfs.exists(history):
                conn = create_conn(history)
                with conn:
                    clear_h3_db(conn, 'tv')
                    optimize_db(conn, history)
            else:
                pass
        else:
            pass

        xbmcgui.Dialog().notification('Cache Manager', 'Search History Cleared!',xbmcgui.NOTIFICATION_INFO, 3000)
