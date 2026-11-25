# -*- coding: utf-8 -*-
"""Push the subtitle API keys saved in AM Lite to every installed subtitle add-on.

                         SubDL key        SubSource key
  a4kSubtitles           subdl.apikey     subsource.apikey
  Najd Smart Subtitles   subdl_key        subsource_key
  SubDL.com              APIKey           -

OpenSubtitles is not handled: AM never reads or writes any OpenSubtitles setting.
"""
import xbmc
import xbmcaddon
import xbmcvfs

from acctmgr.modules import control
from acctmgr.modules import log_utils

translatePath = xbmcvfs.translatePath
exists = xbmcvfs.exists

A4K = 'service.subtitles.a4ksubtitles'
NAJD = 'service.subtitles.najdsmart'
SUBDL = 'service.subtitles.subdl-com'

SUPPORTED = (
    ('a4kSubtitles', A4K),
    ('Najd Smart Subtitles', NAJD),
    ('SubDL.com', SUBDL),
)

LEGACY_KEYS = ('subs.os_user', 'subs.os_pass', 'subs.os_key')


def master():
    return {k: control.setting('subs.%s' % k) or '' for k in ('subdl_key', 'subsource_key')}


def authorized():
    m = master()
    return bool(m['subdl_key'] or m['subsource_key'])


def installed(addon_id):
    return exists(translatePath('special://home/addons/%s/' % addon_id))


def _wanted(addon_id, m):
    """Settings each add-on should hold for the keys AM has (empty ones are skipped)."""
    w = {}
    if addon_id == A4K:
        if m['subdl_key']:
            w.update({'subdl.apikey': m['subdl_key'], 'subdl.enabled': 'true'})
        if m['subsource_key']:
            w.update({'subsource.apikey': m['subsource_key'], 'subsource.enabled': 'true'})
    elif addon_id == NAJD:
        if m['subdl_key']:
            w.update({'subdl_key': m['subdl_key'], 'use_subdl': 'true'})
        if m['subsource_key']:
            w.update({'subsource_key': m['subsource_key'], 'use_subsource': 'true'})
    elif addon_id == SUBDL:
        if m['subdl_key']:
            w.update({'APIKey': m['subdl_key']})
    return w


# Cleared on revoke - only when they still hold AM's value, so a key typed into
# an add-on by hand is left alone.
_REVOKE = {
    A4K: (('subdl.apikey', 'subdl_key'), ('subsource.apikey', 'subsource_key')),
    NAJD: (('subdl_key', 'subdl_key'), ('subsource_key', 'subsource_key')),
    SUBDL: (('APIKey', 'subdl_key'),),
}


def _drop_legacy():
    """AM 1.2.1f could hold an OpenSubtitles login; forget it (add-ons are not touched)."""
    for k in LEGACY_KEYS:
        try:
            if control.setting(k):
                control.setSetting(k, '')
        except Exception:
            pass


class Auth:

    def subtitles_auth(self):
        _drop_legacy()
        m = master()
        for label, addon_id in SUPPORTED:
            if not installed(addon_id):
                continue
            try:
                addon = xbmcaddon.Addon(addon_id)
                for k, v in _wanted(addon_id, m).items():
                    if addon.getSetting(k) != v:
                        addon.setSetting(k, v)
                        xbmc.sleep(50)
            except Exception as e:
                log_utils.error('%s subtitles sync failed: %s' % (label, e))

    def subtitles_revoke(self):
        m = master()
        for label, addon_id in SUPPORTED:
            if not installed(addon_id):
                continue
            try:
                addon = xbmcaddon.Addon(addon_id)
                for setting_id, am_key in _REVOKE[addon_id]:
                    if m[am_key] and addon.getSetting(setting_id) == m[am_key]:
                        addon.setSetting(setting_id, '')
            except Exception as e:
                log_utils.error('%s subtitles revoke failed: %s' % (label, e))

    def status_lines(self):
        m = master()
        lines = [
            '[B]SubDL API key:[/B]  %s' % ('set' if m['subdl_key'] else '-'),
            '[B]SubSource API key:[/B]  %s' % ('set' if m['subsource_key'] else '-'),
            '',
        ]
        for label, addon_id in SUPPORTED:
            if not installed(addon_id):
                lines.append('%s:  [COLOR FF8F9BA6]not installed[/COLOR]' % label)
                continue
            wanted = _wanted(addon_id, m)
            if not wanted:
                lines.append('%s:  [COLOR FF8F9BA6]nothing to sync[/COLOR]' % label)
                continue
            try:
                addon = xbmcaddon.Addon(addon_id)
                ok = all(addon.getSetting(k) == v for k, v in wanted.items())
            except Exception:
                ok = False
            lines.append('%s:  %s' % (label, '[COLOR FF3FD17A]authorized[/COLOR]' if ok
                                      else '[COLOR FFE05252]not synced[/COLOR]'))
        return '\n'.join(lines)
