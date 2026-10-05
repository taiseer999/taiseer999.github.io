import sys
from inspect import getframeinfo, stack
from urllib.parse import quote_plus, unquote_plus
import xbmc
import xbmcgui
import xbmcplugin
from .addonvar import addon_name, addon_version

# Menu icons (ABUKARIM line-icon set, same family as ABUKARIM TOOLS). Applied
# only where the caller passed the add-on's own icon, so build / authorize /
# video items keep their own art.
_ICON_BY_MODE = {
    '1': 'builds', '32': 'update_alert', '33': 'patcher', '35': 'patcher', '5': 'maintenance',
    '10': 'debrid', '101': 'changelog', '100': 'bell', '30': 'video', '9': 'hw_tuning',
    '6': 'binary_install', '7': 'icons_toggle', '4': 'fresh', '8': 'advanced', '29': 'advanced',
    '31': 'advanced', '11': 'menu_reconcile', '12': 'backup', '19': 'cat_profiles',
    '18': 'power', '245': 'power', '28': 'speedtest', '26': 'log_share',
    '13': 'backup_up', '14': 'backup_down', '15': 'backup_down', '16': 'folder',
    '17': 'folder_reset', '254': 'clear_cache', '22': 'profile_export', '23': 'profile_restore',
    '24': 'profile_restore', '20': 'fresh', '21': 'fresh',
    '200': 'broom', '201': 'addon_portal', '202': 'log_share', '203': 'grid', '204': 'wrench',
    '210': 'broom', '211': 'clear_cache', '212': 'clear_cache', '213': 'clear_cache',
    '214': 'icons_toggle', '215': 'log_share', '216': 'database', '218': 'clock', '219': 'clock',
    '220': 'addon_remove', '221': 'folder', '222': 'cat_toggle', '223': 'cat_toggle',
    '225': 'refresh', '226': 'update', '227': 'clear_cache', '231': 'alert', '232': 'alert',
    '240': 'webserver', '242': 'addons_auto', '243': 'refresh', '244': 'profile',
    '250': 'sources', '251': 'remote_refresh', '252': 'advanced', '253': 'info',
}
_SWITCH_MODES = {'217', '230', '241'}          # rows that show ON / OFF


def _menu_icon(name, mode, icon):
    try:
        from .addonvar import addon_icon, addon_path
    except Exception:
        return icon
    if icon != addon_icon:
        return icon
    import os
    m = str(mode)
    key = None
    if m in _SWITCH_MODES:
        key = 'toggle_on' if ']ON[' in name else 'toggle_off' if ']OFF[' in name else None
    key = key or _ICON_BY_MODE.get(m)
    if not key:
        return icon
    path = os.path.join(addon_path, 'resources', 'media', 'icons', key + '.png')
    return path if os.path.isfile(path) else icon


def add_dir(name,url,mode,icon,fanart,description, name2='', version='', kodi='', addcontext=False,isFolder=True):
    icon = _menu_icon(name, mode, icon)
    u=sys.argv[0]+"?url="+quote_plus(url)+"&mode="+str(mode)+"&name="+quote_plus(name)+"&icon="+quote_plus(icon) +"&fanart="+quote_plus(fanart)+"&description="+quote_plus(description)+"&name2="+quote_plus(name2)+"&version="+quote_plus(version)+"&kodi="+quote_plus(kodi)
    liz=xbmcgui.ListItem(name)
    liz.setArt({'fanart':fanart,'icon':icon,'thumb':icon})
    liz.setInfo(type="Video", infoLabels={ "Title": name, "Plot": description, "plotoutline": description})
    if addcontext:
        contextMenu = []
        liz.addContextMenuItems(contextMenu)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=isFolder)

def play_video(name, url, icon, description):
    xbmcplugin.setPluginCategory(int(sys.argv[1]), name)
    url = unquote_plus(url)
    if url.endswith('.jpg') or url.endswith('.jpeg') or url.endswith('.png'):
        string = "ShowPicture(%s)" %url
        xbmc.executebuiltin(string)
        return
    liz = xbmcgui.ListItem(name)
    liz.setInfo('video', {'title': name, 'plot': description})
    liz.setArt({'thumb': icon, 'icon': icon})
    xbmc.Player().play(url, liz)

def GetParams():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=sys.argv[2]
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

def get_mode():
    params=GetParams()
    mode = None
    try:
        mode=int(params["mode"])
    except:
        pass
    return mode

def Log(msg):
    fileinfo = getframeinfo(stack()[1][0])
    xbmc.log('*__{}__{}*{} Python file name = {} Line Number = {}'.format(addon_name,addon_version,msg,fileinfo.filename,fileinfo.lineno), level=xbmc.LOGINFO)

def log(_text, _var):
    xbmc.log(f'{_text} = {str(_var)}', xbmc.LOGINFO)
