import xbmcgui
import xbmc, xbmcaddon
import xbmcvfs
import os
from resources.lib.modules import var
from .dataconn import create_conn, clear_db, optimize_db

dialog = xbmcgui.Dialog()
translatePath = xbmcvfs.translatePath
    
def cl_cache():
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
        else:
            pass

        if 'The Coalition' in addon_select:
            maincache = translatePath('special://userdata/addon_data/plugin.video.coalition/maincache.db')
            if xbmcvfs.exists(maincache):
                conn = create_conn(maincache)
                with conn:
                    clear_db(conn, 'maincache')
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
                    clear_db(conn, 'maincache')
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
                    clear_db(conn, 'maincache')
                    optimize_db(conn, maincache)
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
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
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
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
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
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
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
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
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
                    clear_db(conn, 'add_cat')
                    clear_db(conn, 'lastlinkmovie')
                    clear_db(conn, 'lastlinktv')
                    clear_db(conn, 'local_cache')
                    clear_db(conn, 'nextup')
                    clear_db(conn, 'playback')
                    optimize_db(conn, cache)
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


        xbmcgui.Dialog().notification('Cache Manager', 'Cache Cleared!',xbmcgui.NOTIFICATION_INFO, 3000)
