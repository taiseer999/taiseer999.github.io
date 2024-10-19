import xbmc
import xbmcplugin
import xbmcaddon
import xbmcvfs
import sys
import os
from .params import Params
from .menu import main_menu
from .cache import cl_cache
from .all_cache import cl_all_cache
from .providers import cl_providers
from .trakt import cl_trakt
from .history import cl_mvhistory
from .history_tv import cl_tvhistory
from .history_all import cl_allhistory

handle = int(sys.argv[1])

def router(paramstring):

    p = Params(paramstring)
    xbmc.log(str(p.get_params()),xbmc.LOGDEBUG)

    mode = p.get_mode()
    
    xbmcplugin.setContent(handle, 'files')

    if mode is None:
        main_menu()

    elif mode == 1:
        cl_cache()
        
    elif mode == 2:
        cl_all_cache()

    elif mode == 3:
        cl_providers()

    elif mode == 4:
        cl_trakt()

    elif mode == 5:
        cl_mvhistory()

    elif mode == 6:
        cl_tvhistory()

    elif mode == 7:
        cl_allhistory()

    xbmcplugin.endOfDirectory(handle)
