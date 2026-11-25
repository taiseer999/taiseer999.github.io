# -*- coding: utf-8 -*-
"""Subtitle accounts for AM Lite: SubDL and SubSource API keys.
(OpenSubtitles is not handled - each add-on keeps its own OpenSubtitles login.)

Each one is entered once here, checked live against its API, and then pushed
by sync/subtitles_sync.py to every installed subtitle add-on.
"""
import os
import json
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcgui

from acctmgr.modules import control
from acctmgr.modules import log_utils

joinPath = os.path.join
subs_icon = joinPath(control.iconsPath(), 'subtitles.png')
ADDON_NAME = 'Subtitles'
TIMEOUT = 20
UA = 'AM Lite (Kodi)'

SETTING_KEYS = ('subs.subdl_key', 'subs.subsource_key')
# Left by AM 1.2.1f (OpenSubtitles support was removed in 1.2.1h) - cleared, never used.
LEGACY_KEYS = ('subs.os_user', 'subs.os_pass', 'subs.os_key')


class CheckError(Exception):
    pass


def _http(url, params=None, headers=None, json_body=None):
    if params:
        url += '?' + urllib.parse.urlencode(params)
    hdrs = {'User-Agent': UA, 'Accept': 'application/json'}
    hdrs.update(headers or {})
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode('utf-8')
        hdrs['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=hdrs, method='POST' if body else 'GET')
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read().decode('utf-8', 'ignore')
    try:
        return json.loads(raw or '{}')
    except Exception:
        return {}


def _err(e):
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403):
            return 'Key / login rejected'
        if e.code == 429:
            return 'Accepted, but the daily limit is reached - try later'
        return 'Server error %s' % e.code
    return 'Could not reach the server'



def check_subdl(key):
    try:
        d = _http('https://api.subdl.com/api/v1/subtitles',
                  params={'api_key': key, 'film_name': 'Inception', 'type': 'movie',
                          'languages': 'AR', 'subs_per_page': 1})
    except Exception as e:
        return False, _err(e)
    if d.get('status') is False and 'key' in str(d.get('error', '')).lower():
        return False, 'API key rejected'
    return True, 'API key works'


def check_subsource(key):
    try:
        _http('https://api.subsource.net/api/v1/movies/search',
              params={'searchType': 'text', 'q': 'inception'}, headers={'X-API-Key': key})
    except Exception as e:
        return False, _err(e)
    return True, 'API key works'


class Subtitles:

    def _notify(self, message):
        control.notification(ADDON_NAME, message, icon=subs_icon)

    def _kb(self, heading, default='', hidden=False):
        kb = xbmc.Keyboard(default, heading, hidden)
        kb.doModal()
        if not kb.isConfirmed():
            return None
        return (kb.getText() or '').strip()

    def _key_entry(self, label, current, help_url):
        """Phone entry when possible (API keys are long), else the remote keyboard."""
        try:
            from acctmgr.modules.auth.remote_entry import RemoteKeyEntry
            if RemoteKeyEntry.available():
                pick = xbmcgui.Dialog().select('%s - how to enter it?' % label,
                                               ['Type with the remote', 'Paste from my phone'])
                if pick < 0:
                    return None
                if pick == 1:
                    res = RemoteKeyEntry(label, lambda v: (bool(v.strip()), 'Empty', None), icon=subs_icon,
                                         field_label=label, help_url=help_url).run()
                    if res:
                        return (res.get('value') or '').strip()
        except Exception as e:
            log_utils.error('Subtitles phone entry failed: %s' % e)
        return self._kb(label, current)

    def _status(self, key):
        return '[COLOR FF3FD17A]set[/COLOR]' if control.setting(key) else '[COLOR FF8F9BA6]not set[/COLOR]'

    def auth(self):
        """Pick a service, enter and check it. Returns True if anything was saved."""
        saved = False
        while True:
            rows = [
                'SubDL API key   [%s]' % self._status('subs.subdl_key'),
                'SubSource API key   [%s]' % self._status('subs.subsource_key'),
                '[B]Done[/B]',
            ]
            pick = xbmcgui.Dialog().select('Subtitle accounts', rows)
            if pick < 0 or pick == 2:
                break
            if pick == 0:
                saved = self._auth_key('SubDL API key', 'subs.subdl_key', check_subdl,
                                       'https://subdl.com/panel/api') or saved
            elif pick == 1:
                saved = self._auth_key('SubSource API key', 'subs.subsource_key', check_subsource,
                                       'https://subsource.net/api-docs') or saved
        return saved


    def _auth_key(self, label, setting_id, checker, help_url):
        key = self._key_entry(label, control.setting(setting_id), help_url)
        if not key:
            return False
        progress = xbmcgui.DialogProgress()
        progress.create(ADDON_NAME, 'Checking %s ...' % label)
        try:
            ok, msg = checker(key)
        finally:
            progress.close()
        if not ok:
            xbmcgui.Dialog().ok(ADDON_NAME, '%s: %s' % (label, msg))
            return False
        control.setSetting(setting_id, key)
        self._notify('%s: %s' % (label, msg))
        return True

    def revoke_am(self):
        for k in SETTING_KEYS + LEGACY_KEYS:
            control.setSetting(k, '')
