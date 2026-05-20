# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcvfs
import urllib.request
import json

ADDON_PATH = xbmcvfs.translatePath(
    "special://home/addons/script.portal"
)

KODI_JSON = (
    "https://raw.githubusercontent.com/"
    "taiseer999/taiseer999.github.io/master/skins.json"
)

CE_JSON = (
    "https://raw.githubusercontent.com/"
    "taiseer999/taiseer999ce.github.io/master/skins.json"
)

def choose_source():

    options = [
        "KODI Repository",
        "CoreELEC Repository"
    ]

    selected = xbmcgui.Dialog().select(
        "Choose Skin Source",
        options
    )

    if selected == -1:
        return None

    if selected == 1:
        return CE_JSON

    return KODI_JSON

def load_feed():

    url = choose_source()

    if not url:
        return []

    try:

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Kodi"}
        )

        response = urllib.request.urlopen(
            req,
            timeout=15
        )

        data = response.read().decode("utf-8")

        return json.loads(data)

    except Exception as e:

        xbmcgui.Dialog().ok(
            "Portal",
            "Failed loading feed:\n%s" % str(e)
        )

        return []

class Portal(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):

        super().__init__()

        self.items = kwargs.get("items", [])

    def onInit(self):

        panel = self.getControl(100)

        panel.reset()

        for item in self.items:

            li = xbmcgui.ListItem(
                item.get("name", "")
            )

            li.setArt({
                "thumb": item.get("screenshot", ""),
                "icon": item.get("screenshot", ""),
                "fanart": item.get("screenshot", "")
            })

            li.setProperty(
                "addonid",
                item.get("id", "")
            )

            panel.addItem(li)

        self.setFocusId(100)

    def onClick(self, controlId):

        if controlId != 100:
            return

        panel = self.getControl(100)

        item = panel.getSelectedItem()

        addonid = item.getProperty("addonid")
        title = item.getLabel()

        yes = xbmcgui.Dialog().yesno(
            "Portal",
            "Install and apply this skin?",
            title
        )

        if not yes:
            return

        xbmc.executebuiltin(
            "InstallAddon(%s)" % addonid
        )

        xbmcgui.Dialog().notification(
            "Portal",
            "Installing %s" % title,
            xbmcgui.NOTIFICATION_INFO,
            3000
        )

        xbmc.sleep(5000)

        xbmc.executebuiltin(
            "Skin.SetSkin(%s)" % addonid
        )

        xbmcgui.Dialog().notification(
            "Portal",
            "Applied %s" % title,
            xbmcgui.NOTIFICATION_INFO,
            3000
        )

items = load_feed()

if items:

    win = Portal(
        "portal.xml",
        ADDON_PATH,
        "Default",
        "1080i",
        items=items
    )

    win.doModal()

    del win
