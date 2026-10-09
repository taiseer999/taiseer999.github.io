# -*- coding: utf-8 -*-
import xbmc, xbmcaddon
import xbmcvfs

from acctmgr.modules import var
from acctmgr.modules import control
from acctmgr.modules import log_utils

# Variables
exists = xbmcvfs.exists

# Simkl-supported add-ons: (name, plugin id, chk_addon, chk_settings, ud_path, base settings.xml, {setting: value-key})
# value-keys: token / username / userid / joindate / 'true'
SIMKL_ADDONS = (
    ("Otaku", "plugin.video.otaku", var.chk_otaku, var.chkset_otaku, var.otaku_ud, var.otaku, {
        "simkl.token": "token",
        "simkl.username": "username",
        "simkl.userid": "userid",
        "simkl.enabled": "true",
        "watchlist.update.enabled": "true",
    }),
    ("Umbrella", "plugin.video.umbrella", var.chk_umb, var.chkset_umb, var.umb_ud, var.umb, {
        "simkltoken": "token",
        "simklusername": "username",
        "simkljoindate": "joindate",
    }),
)

# Setting that proves the add-on holds the current token
TOKEN_KEY = {"plugin.video.otaku": "simkl.token", "plugin.video.umbrella": "simkltoken"}


class Auth:
    def simkl_auth(self):

        # ========================= AM Lite Variables =========================
        acctmgr = xbmcaddon.Addon("script.module.acctmgr")
        values = {
            "token": acctmgr.getSetting("simkl.token"),
            "username": acctmgr.getSetting("simkl.username"),
            "userid": acctmgr.getSetting("simkl.userid"),
            "joindate": acctmgr.getSetting("simkl.joindate"),
            "true": "true",
        }
        master_token = values["token"]
        if not master_token:
            return

        for name, plugin, chk_addon, chk_setting, ud_path, base_path, mapping in SIMKL_ADDONS:
            try:
                if not exists(chk_addon):
                    continue
                # Create settings.xml from AM's template if the add-on was never opened
                control.copy_addon_settings(name, chk_addon, ud_path, chk_setting, base_path)
                if not exists(chk_setting):
                    continue
                addon = xbmcaddon.Addon(plugin)
                if addon.getSetting(TOKEN_KEY[plugin]) == master_token:
                    continue
                for k, v in mapping.items():
                    addon.setSetting(k, values[v])
                xbmc.sleep(100)
            except Exception as e:
                log_utils.error(f"{name} Simkl Failed: {e}")


def revoke_all():
    """Clear Simkl from every supported add-on (used by simklRevoke / allRevoke)."""
    for name, plugin, chk_addon, chk_setting, ud_path, base_path, mapping in SIMKL_ADDONS:
        try:
            if exists(chk_addon) and exists(chk_setting):
                addon = xbmcaddon.Addon(plugin)
                for k, v in mapping.items():
                    if v != "true":
                        addon.setSetting(k, "")          # token / username / ids
                    elif k == "simkl.enabled":
                        addon.setSetting(k, "false")     # Otaku: disable the Simkl watchlist
        except Exception as e:
            log_utils.error(f"{name} Simkl Revoke Failed: {e}")
