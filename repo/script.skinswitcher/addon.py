import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import os
import sys
import glob
import urllib.request
import urllib.error
import urllib.parse
from urllib.parse import parse_qsl
from resources import tools

ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
ADDON_ICON = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('icon'))
ADDON_FANART = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('fanart'))
HOME = xbmcvfs.translatePath('special://home/')
ADDONS = os.path.join(HOME, 'addons')
USER_DATA = os.path.join(HOME,      'userdata')
ADDON_DATA = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
DIALOG = xbmcgui.Dialog()
KODI_VER = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
repositoryurl = ''
repositoryxml = ''

def MainMenu():
	addItem('Current Skin -- %s' % currSkin(), 'url', '', ADDON_ICON, ADDON_FANART, '')
	addItem('Click here to change skins ', 'url', 1, ADDON_ICON, ADDON_FANART, '')

#---Example how to add more skins---#
#addItem('Skin Name' ,'url', 5, ADDON_ICON, ADDON_FANART, '') The number will be the mode at the bottom
#addItem('Skin Name', 'url', 6, ADDON_ICON, ADDON_FANART, '') The number will be the mode at the bottom

def skinWIN():
	xbmc.executebuiltin('Dialog.Close(busydialog)')
	fold = glob.glob(os.path.join(ADDONS, 'skin*'))
	name = []; addonids = []
	for folder in sorted(fold, key = lambda x: x):
		foldername = os.path.split(folder[:-1])[1]
		xml = os.path.join(folder, 'addon.xml')
		if os.path.exists(xml):
			xbmc.log('xml = ' + str(xml), xbmc.LOGINFO)
			f = open(xml, encoding = 'utf-8')
			a = f.read()
			match = tools.parseDOM(a, 'addon', ret='id')
			addid  = foldername if len(match) == 0 else match[0]
			try: 
				add = xbmcaddon.Addon(id=addid)
				name.append(add.getAddonInfo('name'))
				addonids.append(addid)
			except:
				pass
	selected = []; choice = 0
	skin = ["Current Skin -- %s" % currSkin()] + name
	choice = DIALOG.select("Choose a skin below.", skin)
	if choice == -1: return
	else: 
		choice1 = (choice-1)
		selected.append(choice1)
		skin[choice] = "%s" % ( name[choice1])
	if selected == None: return
	for addon in selected:
		swapSkins(name,addonids[addon])

def Skin_install(name, skin):
	popup = DIALOG.yesno(ADDON_ID, "In order to use this build you must install the %s skin."% name + '\n' + "Do you want to install it?" , yeslabel="[B][COLOR springgreen]Yes Install[/COLOR][/B]", nolabel="[B][COLOR red]No[/COLOR][/B]")
	if popup == 1:
		ver = tools.parseDOM(tools.openURL(repositoryxml), 'addon', ret='version', attrs = {'id': skin})
		if len(ver) > 0:
			skinzip = '%s/%s/%s-%s.zip' % (repositoryurl, skin, skin, ver[0])
			if KODI_VER >= 17: tools.addonDatabase(skin, 1)
			tools.installAddon(skin, skinzip)
			xbmc.executebuiltin('UpdateAddonRepos()')
			swapSkins(name,skin)
			sys.exit(0)			
	else:return

def currSkin():
	skin_name = xbmc.getSkinDir()
	skin_name = xbmcaddon.Addon(skin_name).getAddonInfo('name')
	return skin_name

def swapSkins(name, skin):
	if not xbmc.getCondVisibility('System.HasAddon('+skin+')'):
		Skin_install(name, skin)
	else:
		setNew('lookandfeel.skin', skin)
		x = 0
		while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and x < 100:
			x += 1
			xbmc.sleep(100)
		if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
			xbmc.executebuiltin('SendClick(11)')
		sys.exit(0)

def setNew(new, value):
	try:
		new = '"%s"' % new
		value = '"%s"' % value
		query = '{"jsonrpc":"2.0", "method":"Settings.SetSettingValue","params":{"setting":%s,"value":%s}, "id":1}' % (new, value)
		xbmc.executeJSONRPC(query)
	except:
		pass
	return None

def addItem(name, url, mode, iconimage, fanart, description=None):
	if description == None: description = ''
	description = '[COLOR white]' + description + '[/COLOR]'
	u = sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)+"&fanart="+urllib.parse.quote_plus(fanart)
	liz=xbmcgui.ListItem(name)
	liz.setArt({'icon': iconimage, 'thumb': iconimage, 'fanart': fanart})	
	set_info(liz, {"title": name, "plot": description })
	liz.setProperty("fanart_Image", fanart)
	liz.setProperty("icon_Image", iconimage )
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u,listitem=liz, isFolder=False)

def set_info(liz: xbmcgui.ListItem, infolabels: dict, cast: list=None):
    if cast is None:
        cast = []
    if KODI_VER < 20:
        liz.setInfo("video", infolabels)
        if cast:
            liz.setCast(cast)
    else:
        i = liz.getVideoInfoTag()
        i.setMediaType(infolabels.get("mediatype", "video"))
        i.setTitle(infolabels.get("title", "Unknown"))
        i.setPlot(infolabels.get("plot", infolabels.get("title", "")))
        i.setTagLine(infolabels.get("tagline", ""))
        i.setPremiered(infolabels.get("premiered", ""))
        i.setGenres(infolabels.get("genre", []))
        i.setMpaa(infolabels.get("mpaa", ""))
        i.setDirectors(infolabels.get("director", []))
        i.setWriters(infolabels.get("writer", []))
        i.setRating(infolabels.get("rating", 0))
        i.setVotes(infolabels.get("votes", 0))
        i.setStudios(infolabels.get("studio", []))
        i.setCountries(infolabels.get("country", []))
        i.setSet(infolabels.get("set", ""))
        i.setTvShowStatus(infolabels.get("status", ""))
        i.setDuration(infolabels.get("duration", 0))
        i.setTrailer(infolabels.get("trailer", ""))
        if cast:
            cast_list = []
            for actor in cast:
                name = actor.get("name", "")
                role = actor.get("role", "")
                thumbnail = actor.get("thumbnail", "")
                actor = xbmc.Actor(
                    name=name,
                    role=role,
                    thumbnail=thumbnail
                )
                cast_list.append(actor)
            i.setCast(cast_list)

def router():
    params = dict(parse_qsl(sys.argv[2][1:]))
    mode = params.get('mode')
    try: mode = int(mode)
    except: pass
    name = params.get('name')
    
    if mode is None: 
	    MainMenu()#change to skinWIN() to open select window automaticly
    elif mode==1:
	    skinWIN()
	
	#---How to add more modes---#
    #elif mode==4:swapSkins(name, 'Exact skin folder')
    #elif mode==5:swapSkins(name, 'Exact skin folder')
    
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

if __name__ == '__main__':
    router()