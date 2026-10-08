import xbmc, xbmcgui
from resources.libs.common.config import CONFIG

def log(msg, level=xbmc.LOGDEBUG):
    if CONFIG.DEBUGLEVEL == '0':  # No Logging
        return False
    if CONFIG.DEBUGLEVEL == '1':  # Normal Logging
        pass
    if CONFIG.DEBUGLEVEL == '2':  # Full Logging
        level = xbmc.LOGINFO
    
    xbmc.log('{0}: {1}'.format(CONFIG.ADDONTITLE, msg), level)

def log_notify(title, message, times=2000, icon=CONFIG.ADDON_ICON, sound=False):
    from resources.libs.common.i18n import tr
    xbmcgui.Dialog().notification(tr(title), tr(message), icon, int(times), sound)

