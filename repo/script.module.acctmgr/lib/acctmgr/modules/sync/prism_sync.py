# -*- coding: utf-8 -*-
"""
prism_sync.py  —  Account Manager Lite

Writes debrid credentials into Prism (plugin.video.prism), a Seren fork.

Prism is NOT backed by a databases/settings.db `settings` table the way
Fenlight / Gears / Red Light are — its PersistedSettingsCache persists straight
to Kodi's settings.xml.  So, exactly like the existing Seren / POV / Otaku
blocks, we write through xbmcaddon.Addon("plugin.video.prism").setSetting().

Prism debrid setting keys (verified against plugin.video.prism 5.0.35):
    Real-Debrid : rd.auth, rd.refresh, rd.secret, rd.client_id, rd.username,
                  realdebrid.premiumstatus, realdebrid.enabled
    Premiumize  : premiumize.token, premiumize.username,
                  premiumize.premiumstatus, premiumize.enabled
    All-Debrid  : alldebrid.apikey, alldebrid.username,
                  alldebrid.premiumstatus, alldebrid.enabled
    TorBox      : tb.token, tb.username, tb.premiumstatus, torbox.enabled
    OffCloud    : oc.token, oc.username, oc.premiumstatus, offcloud.enabled

Prism has no Easynews provider, so there is nothing to sync there.

Each function is a no-op (guarded) unless Prism is installed and initialised.
Trakt is intentionally never touched — Prism uses Simkl, not Trakt, and the
user's requirement is "all services except Trakt".
"""
import xbmc
import xbmcaddon
import xbmcvfs

from acctmgr.modules import var
from acctmgr.modules import log_utils

PRISM_ID = "plugin.video.prism"

exists = xbmcvfs.exists


def _prism_ready():
    """True only when Prism is installed and has a settings.xml (initialised)."""
    return exists(var.chk_prism) and exists(var.chkset_prism)


def _addon():
    return xbmcaddon.Addon(PRISM_ID)


def _apply(settings: dict):
    addon = _addon()
    for k, v in settings.items():
        addon.setSetting(k, v)


def sync_rd(username, token, client_id, refresh, secret, master_token):
    """Authorize Real-Debrid on Prism (leaves PM/AD enable flags per their tokens)."""
    try:
        if not _prism_ready():
            return
        addon = _addon()
        if addon.getSetting("rd.auth") == master_token:
            return
        chk_pm = addon.getSetting("premiumize.token")
        chk_ad = addon.getSetting("alldebrid.apikey")
        _apply({
            "rd.username": username,
            "rd.auth": token,
            "rd.client_id": client_id,
            "rd.refresh": refresh,
            "rd.secret": secret,
            "realdebrid.premiumstatus": "Premium",
            "realdebrid.enabled": "true",
            "premiumize.enabled": "true" if chk_pm else "false",
            "alldebrid.enabled": "true" if chk_ad else "false",
        })
    except Exception as e:
        log_utils.error(f"Prism Real-Debrid Failed: {e}")


def sync_pm(username, token, master_token):
    """Authorize Premiumize on Prism."""
    try:
        if not _prism_ready():
            return
        addon = _addon()
        if addon.getSetting("premiumize.token") == master_token:
            return
        chk_rd = addon.getSetting("rd.auth")
        chk_ad = addon.getSetting("alldebrid.apikey")
        _apply({
            "premiumize.username": username,
            "premiumize.token": token,
            "premiumize.premiumstatus": "Premium",
            "premiumize.enabled": "true",
            "realdebrid.enabled": "true" if chk_rd else "false",
            "alldebrid.enabled": "true" if chk_ad else "false",
        })
    except Exception as e:
        log_utils.error(f"Prism Premiumize Failed: {e}")


def sync_ad(username, token, master_token):
    """Authorize All-Debrid on Prism."""
    try:
        if not _prism_ready():
            return
        addon = _addon()
        if addon.getSetting("alldebrid.apikey") == master_token:
            return
        chk_rd = addon.getSetting("rd.auth")
        chk_pm = addon.getSetting("premiumize.token")
        _apply({
            "alldebrid.username": username,
            "alldebrid.apikey": token,
            "alldebrid.premiumstatus": "Premium",
            "alldebrid.enabled": "true",
            "realdebrid.enabled": "true" if chk_rd else "false",
            "premiumize.enabled": "true" if chk_pm else "false",
        })
    except Exception as e:
        log_utils.error(f"Prism All-Debrid Failed: {e}")


def sync_tb(username, token, master_token):
    """Authorize TorBox on Prism."""
    try:
        if not _prism_ready():
            return
        addon = _addon()
        if addon.getSetting("tb.token") == master_token:
            return
        _apply({
            "tb.username": username,
            "tb.token": token,
            "tb.premiumstatus": "Premium",
            "torbox.enabled": "true",
        })
    except Exception as e:
        log_utils.error(f"Prism TorBox Failed: {e}")


def sync_oc(username, token, master_token):
    """Authorize OffCloud on Prism."""
    try:
        if not _prism_ready():
            return
        addon = _addon()
        if addon.getSetting("oc.token") == master_token:
            return
        _apply({
            "oc.username": username,
            "oc.token": token,
            "oc.premiumstatus": "Premium",
            "offcloud.enabled": "true",
        })
    except Exception as e:
        log_utils.error(f"Prism OffCloud Failed: {e}")


# ---------------------------------------------------------------------------
# Revoke — clear a single service on Prism (used by the Revoke actions).
# ---------------------------------------------------------------------------
def revoke_rd():
    try:
        if not _prism_ready():
            return
        _apply({
            "rd.username": "", "rd.auth": "", "rd.client_id": "",
            "rd.refresh": "", "rd.secret": "", "realdebrid.premiumstatus": "",
            "realdebrid.enabled": "false",
        })
    except Exception as e:
        log_utils.error(f"Prism RD Revoke Failed: {e}")


def revoke_pm():
    try:
        if not _prism_ready():
            return
        _apply({
            "premiumize.username": "", "premiumize.token": "",
            "premiumize.premiumstatus": "", "premiumize.enabled": "false",
        })
    except Exception as e:
        log_utils.error(f"Prism PM Revoke Failed: {e}")


def revoke_ad():
    try:
        if not _prism_ready():
            return
        _apply({
            "alldebrid.username": "", "alldebrid.apikey": "",
            "alldebrid.premiumstatus": "", "alldebrid.enabled": "false",
        })
    except Exception as e:
        log_utils.error(f"Prism AD Revoke Failed: {e}")


def revoke_tb():
    try:
        if not _prism_ready():
            return
        _apply({
            "tb.username": "", "tb.token": "",
            "tb.premiumstatus": "", "torbox.enabled": "false",
        })
    except Exception as e:
        log_utils.error(f"Prism TB Revoke Failed: {e}")


def revoke_oc():
    try:
        if not _prism_ready():
            return
        _apply({
            "oc.username": "", "oc.token": "",
            "oc.premiumstatus": "", "offcloud.enabled": "false",
        })
    except Exception as e:
        log_utils.error(f"Prism OC Revoke Failed: {e}")
