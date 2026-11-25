# -*- coding: utf-8 -*-
"""AIOStreams server authorization for AM Lite.

The user gives AM the AIOStreams server once: the instance URL (or a full
manifest URL copied from the AIOStreams configure page), the UUID and the
password.  AM checks them against the server (GET /api/v1/user with Basic
auth), which also returns the encrypted password used in manifest URLs, then
stores everything so aiostreams_sync can push it to every supported add-on.
"""
import os
import re
import base64
import json
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcgui

from acctmgr.modules import control
from acctmgr.modules import log_utils

joinPath = os.path.join
aio_icon = joinPath(control.iconsPath(), 'aiostreams.png')
ADDON_NAME = 'AIOStreams'
TIMEOUT = 20

# Public instances as named by POV / Red Light (used to pick their preset slot).
PUBLIC_INSTANCES = (
    ('Kuu', 'https://aiostreams.stremio.ru'),
    ('Viren', 'https://aiostreams.viren070.me'),
    ('Yeb', 'https://aiostreams.fortheweak.cloud'),
    ('Midnight', 'https://aiostreamsfortheweebsstable.midnightignite.me'),
)

_UUID_RE = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')

SETTING_KEYS = ('aiostreams.url', 'aiostreams.uuid', 'aiostreams.password',
                'aiostreams.encrypted', 'aiostreams.manifest')


def parse_server(text):
    """Return (base_url, uuid_or_empty) from an instance, configure or manifest URL."""
    text = (text or '').strip()
    if not text:
        return '', ''
    if text.startswith('stremio://'):
        text = 'https://' + text[len('stremio://'):]
    if not re.match(r'^https?://', text, re.I):
        text = 'https://' + text
    parts = urllib.parse.urlsplit(text)
    path = parts.path or ''
    uuid = ''
    m = _UUID_RE.search(path)
    if m:
        uuid = m.group(0)
    # Everything before /stremio/ (or /configure, /api) is the instance base.
    cut = re.split(r'/(?:stremio|configure|api)(?:/|$)', path, maxsplit=1, flags=re.I)[0]
    base = urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc, cut.rstrip('/'), '', ''))
    return base.rstrip('/'), uuid


def manifest_url(base, uuid, encrypted):
    return '%s/stremio/%s/%s/manifest.json' % (base.rstrip('/'), uuid, encrypted)


def preset_name(base):
    base = (base or '').rstrip('/').lower()
    for name, url in PUBLIC_INSTANCES:
        if url.lower() == base:
            return name
    return ''


def verify(base, uuid, password):
    """Check the credentials on the server.

    Returns (ok, message, encrypted_password).
    """
    url = '%s/api/v1/user' % base.rstrip('/')
    token = base64.b64encode(('%s:%s' % (uuid.strip(), password.strip())).encode('utf-8')).decode('ascii')
    req = urllib.request.Request(url, headers={
        'Authorization': 'Basic %s' % token,
        'Accept': 'application/json',
        'User-Agent': 'AM Lite (Kodi)',
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode('utf-8', 'ignore') or '{}')
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            body = json.loads(e.read().decode('utf-8', 'ignore') or '{}')
            detail = (body.get('error') or {}).get('message') or body.get('detail') or ''
        except Exception:
            pass
        if e.code in (401, 403):
            return False, detail or 'Wrong UUID or password', ''
        if e.code == 404:
            return False, detail or 'UUID not found on this server', ''
        return False, detail or 'Server error %s' % e.code, ''
    except Exception as e:
        log_utils.error('AIOStreams verify failed: %s' % e)
        return False, 'Could not reach the server', ''
    if not data.get('success'):
        msg = (data.get('error') or {}).get('message') or data.get('detail') or 'Rejected by the server'
        return False, msg, ''
    encrypted = ((data.get('data') or {}).get('encryptedPassword') or '').strip()
    return True, '', encrypted


class AIOStreams:

    def _notify(self, message):
        control.notification(ADDON_NAME, message, icon=aio_icon)

    def _keyboard(self, heading, default='', hidden=False):
        kb = xbmc.Keyboard(default, heading, hidden)
        kb.doModal()
        if not kb.isConfirmed():
            return None
        return (kb.getText() or '').strip()

    def _ask_server_phone(self):
        """Phone entry for the long URL (paste the manifest URL from the browser)."""
        try:
            from acctmgr.modules.auth.remote_entry import RemoteKeyEntry
        except Exception:
            return None
        if not RemoteKeyEntry.available():
            return None

        def _validate(value):
            base, uuid = parse_server(value)
            if not base:
                return False, 'That is not a URL', None
            return True, '', {'base': base, 'uuid': uuid}

        result = RemoteKeyEntry('AIOStreams server', _validate, icon=aio_icon,
                                field_label='AIOStreams URL or manifest URL').run()
        if result:
            return result.get('base', ''), result.get('uuid', '')
        return None

    def _ask_server(self):
        current = control.setting('aiostreams.url') or ''
        choice = 0
        try:
            from acctmgr.modules.auth.remote_entry import RemoteKeyEntry
            if RemoteKeyEntry.available():
                choice = xbmcgui.Dialog().select('AIOStreams server - how to enter it?', [
                    'Type with the remote',
                    'Paste from my phone (manifest URL from the AIOStreams page)',
                ])
                if choice < 0:
                    return None
        except Exception:
            choice = 0
        if choice == 1:
            got = self._ask_server_phone()
            if got:
                return got
            if not control.yesnoDialog('Phone entry did not complete.\nType it with the remote instead?',
                                       ADDON_NAME, 'No', 'Yes'):
                return None
        text = self._keyboard('AIOStreams server URL (or full manifest URL)', current or 'https://')
        if not text or text in ('https://', 'http://'):
            return None
        base, uuid = parse_server(text)
        if not base:
            return None
        return base, uuid

    def auth(self):
        server = self._ask_server()
        if not server:
            self._notify('AIOStreams authorization cancelled!')
            return False
        base, uuid = server

        if not uuid:
            uuid = self._keyboard('AIOStreams UUID', control.setting('aiostreams.uuid') or '')
            if not uuid:
                self._notify('AIOStreams authorization cancelled!')
                return False
            m = _UUID_RE.search(uuid)
            if m:
                uuid = m.group(0)

        for attempt in range(3):
            password = self._keyboard('AIOStreams password', '', hidden=True)
            if not password:
                self._notify('AIOStreams authorization cancelled!')
                return False
            progress = xbmcgui.DialogProgress()
            progress.create(ADDON_NAME, 'Checking the account on %s ...' % base)
            try:
                ok, msg, encrypted = verify(base, uuid, password)
            finally:
                progress.close()
            if ok and encrypted:
                break
            if ok and not encrypted:
                msg = 'The server did not return an encrypted password'
            if attempt == 2 or not control.yesnoDialog('%s.\nTry again?' % msg, ADDON_NAME, 'No', 'Yes'):
                self._notify('AIOStreams authorization failed!')
                return False
        else:
            return False

        control.setSetting('aiostreams.url', base)
        control.setSetting('aiostreams.uuid', uuid)
        control.setSetting('aiostreams.password', password)
        control.setSetting('aiostreams.encrypted', encrypted)
        control.setSetting('aiostreams.manifest', manifest_url(base, uuid, encrypted))
        self._notify('AIOStreams server authorized')
        return True

    def revoke_am(self):
        for k in SETTING_KEYS:
            control.setSetting(k, '')
