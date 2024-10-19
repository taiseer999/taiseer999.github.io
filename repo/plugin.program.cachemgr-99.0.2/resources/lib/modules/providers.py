import xbmcgui
import xbmc, xbmcaddon
import xbmcvfs
from resources.lib.modules import var
from .dataconn import create_conn, clear_db, optimize_db

dialog = xbmcgui.Dialog()
translatePath = xbmcvfs.translatePath
    
def cl_providers():
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
            
        addon_select = []
        dialog_select = dialog.multiselect('Cache Manager - Choose Add-ons to Clear',addon_list) #Select add-ons to clear
        if dialog_select == None:
            return
        else:
            for selection in dialog_select:
                #Create user selected list
                addon_select.append(addon_list[selection])

        if 'Seren' in addon_select:           
            provider = translatePath('special://userdata/addon_data/plugin.video.seren/torrentCache.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'movies')
                    clear_db(conn, 'tvshows')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass
        
        if 'Fen' in addon_select:           
            provider = translatePath('special://userdata/addon_data/plugin.video.fen/databases/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass
            
        if 'Fen Light' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/external.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass
            
        if 'afFENity' in addon_select: 
            provider = translatePath('special://userdata/addon_data/plugin.video.affenity/databases/external.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass
        
        if 'Ezra' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.ezra/databases/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass

        if 'The Coalition' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.coalition/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass
        
        if 'POV' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.pov/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass

        if 'Taz19' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.taz19/providerscache2.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'results_data')
                    optimize_db(conn, provider)
            else:
                pass
        else:
            pass
        
        if 'Umbrella' in addon_select:
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
        else:
            pass

        if 'OneMoar' in addon_select:
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
        else:
            pass
        
        if 'Dradis' in addon_select:
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
        else:
            pass

        if 'Homelander' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.homelander/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'TheLab' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.thelab/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Quicksilver' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.quicksilver/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Chains Genocide' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Absolution' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.absolution/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Shazam' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.shazam/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'The Crew' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.thecrew/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Nightwing' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.nightwing/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Alvin' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.alvin/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Moria' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.moria/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Nine Lives' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.nine/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'Scrubs V2' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.scrubsv2/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        if 'TheLabjr' in addon_select:
            provider = translatePath('special://userdata/addon_data/plugin.video.thelabjr/providers.13.db')
            if xbmcvfs.exists(provider):
                conn = create_conn(provider)
                with conn:
                    clear_db(conn, 'rel_src')
                    clear_db(conn, 'rel_url')
            else:
                pass
        else:
            pass

        xbmcgui.Dialog().notification('Cache Manager', 'Providers Cleared!',xbmcgui.NOTIFICATION_INFO, 3000)
