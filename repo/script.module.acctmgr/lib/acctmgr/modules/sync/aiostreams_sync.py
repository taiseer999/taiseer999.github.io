# -*- coding: utf-8 -*-
"""Push the AIOStreams server saved in AM Lite to every supported add-on.

Supported add-ons and where each keeps the server:
  * AIOStreams (plugin.video.aiostreams) - settings.xml  manifest_url
  * POV        (plugin.video.pov)        - settings.xml  provider.aiostreams / aio.*
  * Red Light  (plugin.video.redlight)   - settings.db   provider.aiostreams / aiostreams.*
  * AB Scrapers (script.module.abscrapers) - settings.xml scraper login (aiostreams.*)
                                             + AIOStreams player login (aiostreams_instance / aio.*)
"""
import json
import sqlite3

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from acctmgr.modules import var
from acctmgr.modules import control
from acctmgr.modules import log_utils
from acctmgr.modules.auth.aiostreams import preset_name

exists = xbmcvfs.exists
translatePath = xbmcvfs.translatePath

AIO_ID = 'plugin.video.aiostreams'
chk_aio = translatePath('special://home/addons/%s/' % AIO_ID)
ABS_ID = 'script.module.abscrapers'
chk_abs = translatePath('special://home/addons/%s/' % ABS_ID)

# POV enum: Kuu|Custom|Viren|Yeb|Midnight
POV_SLOTS = {'Kuu': '0', 'Viren': '2', 'Yeb': '3', 'Midnight': '4'}
POV_CUSTOM = '1'
# Red Light preset ids (apis/aiostreams_api.py PRESETS); '4' = Custom
RED_SLOTS = {'Kuu': '0', 'Viren': '1', 'Yeb': '2', 'Midnight': '3'}
RED_CUSTOM = '4'

SUPPORTED = (
    ('AIOStreams', AIO_ID),
    ('POV', 'plugin.video.pov'),
    ('Red Light', 'plugin.video.redlight'),
    ('AB Scrapers', ABS_ID),
)


def _abs_wanted(m, name):
    """AB Scrapers keeps two logins: the AIOStreams scraper (Red Light preset order,
    Custom = 4) and the AIOStreams player (POV preset order, Custom = 1)."""
    scraper_slot = RED_SLOTS.get(name, RED_CUSTOM)
    player_slot = POV_SLOTS.get(name, POV_CUSTOM)
    return {
        'provider.aiostreams': 'true',
        'aiostreams.instance': scraper_slot,
        'aiostreams.custom_url': m['url'] if scraper_slot == RED_CUSTOM else '',
        'aiostreams.username': m['uuid'],
        'aiostreams.password': m['password'],
        'aiostreams_instance': player_slot,
        'aio.custom_url': m['url'] if player_slot == POV_CUSTOM else '',
        'aio.username': m['uuid'],
        'aio.password': m['password'],
    }


def master():
    return {
        'url': control.setting('aiostreams.url') or '',
        'uuid': control.setting('aiostreams.uuid') or '',
        'password': control.setting('aiostreams.password') or '',
        'manifest': control.setting('aiostreams.manifest') or '',
    }


def authorized():
    m = master()
    return bool(m['url'] and m['uuid'] and m['password'])


# ---------------------------------------------------------------- Red Light DB
def _red_write(pairs):
    """UPDATE (or INSERT when the row is missing) Red Light settings.db rows."""
    conn = sqlite3.connect(var.red_settings_db, timeout=3)
    try:
        cur = conn.cursor()
        for setting_id, setting_type, value in pairs:
            cur.execute('UPDATE settings SET setting_value = ? WHERE setting_id = ?', (value, setting_id))
            if cur.rowcount == 0:
                default = 'false' if setting_type == 'boolean' else ''
                cur.execute('INSERT OR REPLACE INTO settings VALUES (?, ?, ?, ?)',
                            (setting_id, setting_type, default, value))
        conn.commit()
        cur.close()
    finally:
        conn.close()


def _red_read(setting_id):
    conn = sqlite3.connect(var.red_settings_db, timeout=3)
    try:
        row = conn.execute('SELECT setting_value FROM settings WHERE setting_id = ?', (setting_id,)).fetchone()
        return row[0] if row else ''
    finally:
        conn.close()


def _red_properties(pairs, base_url=None, instance_label=None):
    """Mirror the values into Red Light's Home-window cache so a running Red Light sees them now."""
    win = xbmcgui.Window(10000)
    for setting_id, _t, value in pairs:
        win.setProperty('redlight.%s' % setting_id, value)
    if base_url is not None:
        win.setProperty('redlight.aiostreams.base_url', base_url or '(not set — choose instance or enter Custom URL)')
    if instance_label is not None:
        win.setProperty('redlight.aiostreams.instance_name', instance_label)


def _red_profiles(slot, entry):
    try:
        profiles = json.loads(_red_read('aiostreams.profiles') or '{}')
        if not isinstance(profiles, dict):
            profiles = {}
    except Exception:
        profiles = {}
    if entry is None:
        if slot:
            profiles.pop(slot, None)
    else:
        profiles[slot] = entry
    return json.dumps(profiles)


class Auth:

    def aiostreams_auth(self):
        m = master()
        if not (m['url'] and m['uuid'] and m['password']):
            return
        name = preset_name(m['url'])

        # ========================= AIOStreams (Kodi client) =========================
        try:
            if exists(chk_aio) and m['manifest']:
                addon = xbmcaddon.Addon(AIO_ID)
                if addon.getSetting('manifest_url') != m['manifest']:
                    addon.setSetting('manifest_url', m['manifest'])
        except Exception as e:
            log_utils.error('AIOStreams add-on sync failed: %s' % e)

        # ========================= POV =========================
        try:
            if exists(var.chk_pov):
                addon = xbmcaddon.Addon('plugin.video.pov')
                slot = POV_SLOTS.get(name, POV_CUSTOM)
                wanted = {
                    'provider.aiostreams': 'true',
                    'aio.instance': slot,
                    'aio.username': m['uuid'],
                    'aio.password': m['password'],
                }
                if slot == POV_CUSTOM:
                    wanted['aio.custom_url'] = m['url']
                changed = False
                for k, v in wanted.items():
                    if addon.getSetting(k) != v:
                        addon.setSetting(k, v)
                        changed = True
                if changed:
                    xbmc.sleep(200)
                    control.remake_pov_settings()
        except Exception as e:
            log_utils.error('POV AIOStreams sync failed: %s' % e)

        # ========================= Red Light =========================
        try:
            if exists(var.chk_red):
                if not exists(var.chkset_red):
                    control.remake_red_settings()
                    xbmc.sleep(1500)
                if exists(var.chkset_red):
                    slot = RED_SLOTS.get(name, RED_CUSTOM)
                    custom = m['url'] if slot == RED_CUSTOM else ''
                    profile = {'username': m['uuid'], 'password': m['password'],
                               'custom_url': custom, 'variant': ''}
                    pairs = [
                        ('provider.aiostreams', 'boolean', 'true'),
                        ('aiostreams.instance', 'action', slot),
                        ('aiostreams.username', 'string', m['uuid']),
                        ('aiostreams.password', 'string', m['password']),
                        ('aiostreams.custom_url', 'string', custom),
                        ('aiostreams.profiles', 'string', _red_profiles(slot, profile)),
                    ]
                    if (_red_read('aiostreams.username') != m['uuid']
                            or _red_read('aiostreams.password') != m['password']
                            or _red_read('aiostreams.instance') != slot
                            or _red_read('aiostreams.custom_url') != custom
                            or _red_read('provider.aiostreams') != 'true'):
                        _red_write(pairs)
                        _red_properties(pairs, base_url=m['url'], instance_label=name or 'Custom')
                        xbmc.sleep(300)
                        control.remake_red_settings()
        except Exception as e:
            log_utils.error('Red Light AIOStreams sync failed: %s' % e)

        # ========================= AB Scrapers =========================
        try:
            if exists(chk_abs):
                addon = xbmcaddon.Addon(ABS_ID)
                for k, v in _abs_wanted(m, name).items():
                    if addon.getSetting(k) != v:
                        addon.setSetting(k, v)
        except Exception as e:
            log_utils.error('AB Scrapers AIOStreams sync failed: %s' % e)

    def aiostreams_revoke(self):
        # AIOStreams client
        try:
            if exists(chk_aio):
                xbmcaddon.Addon(AIO_ID).setSetting('manifest_url', '')
        except Exception as e:
            log_utils.error('AIOStreams add-on revoke failed: %s' % e)
        # POV
        try:
            if exists(var.chk_pov):
                addon = xbmcaddon.Addon('plugin.video.pov')
                for k, v in (('provider.aiostreams', 'false'), ('aio.instance', '0'),
                             ('aio.custom_url', ''), ('aio.username', ''), ('aio.password', '')):
                    addon.setSetting(k, v)
                xbmc.sleep(200)
                control.remake_pov_settings()
        except Exception as e:
            log_utils.error('POV AIOStreams revoke failed: %s' % e)
        # Red Light
        try:
            if exists(var.chk_red) and exists(var.chkset_red):
                slot = _red_read('aiostreams.instance') or ''
                pairs = [
                    ('provider.aiostreams', 'boolean', 'false'),
                    ('aiostreams.instance', 'action', '0'),
                    ('aiostreams.username', 'string', 'empty_setting'),
                    ('aiostreams.password', 'string', 'empty_setting'),
                    ('aiostreams.custom_url', 'string', ''),
                    ('aiostreams.profiles', 'string', _red_profiles(slot, None)),
                ]
                _red_write(pairs)
                _red_properties(pairs, base_url='https://aiostreams.stremio.ru', instance_label='Kuu')
                xbmc.sleep(300)
                control.remake_red_settings()
        except Exception as e:
            log_utils.error('Red Light AIOStreams revoke failed: %s' % e)
        # AB Scrapers
        try:
            if exists(chk_abs):
                addon = xbmcaddon.Addon(ABS_ID)
                for k, v in (('provider.aiostreams', 'false'), ('aiostreams.instance', '0'),
                             ('aiostreams.custom_url', ''), ('aiostreams.username', ''),
                             ('aiostreams.password', ''), ('aiostreams_instance', '0'),
                             ('aio.custom_url', ''), ('aio.username', ''), ('aio.password', '')):
                    addon.setSetting(k, v)
        except Exception as e:
            log_utils.error('AB Scrapers AIOStreams revoke failed: %s' % e)

    def status_lines(self):
        """Human-readable per-add-on status for the 'View Authorizations' screen."""
        m = master()
        lines = ['[B]AIOStreams server:[/B]  %s' % (m['url'] or '-'),
                 '[B]UUID:[/B]  %s' % (m['uuid'] or '-'), '']
        for label, addon_id in SUPPORTED:
            path = translatePath('special://home/addons/%s/' % addon_id)
            if not exists(path):
                lines.append('%s:  [COLOR FF8F9BA6]not installed[/COLOR]' % label)
                continue
            ok = False
            try:
                if addon_id == AIO_ID:
                    ok = bool(m['manifest']) and xbmcaddon.Addon(AIO_ID).getSetting('manifest_url') == m['manifest']
                elif addon_id == ABS_ID:
                    a = xbmcaddon.Addon(addon_id)
                    ok = (a.getSetting('aiostreams.username') == m['uuid']
                          and a.getSetting('aio.username') == m['uuid'])
                elif addon_id == 'plugin.video.pov':
                    a = xbmcaddon.Addon(addon_id)
                    ok = a.getSetting('aio.username') == m['uuid'] and a.getSetting('provider.aiostreams') == 'true'
                elif exists(var.chkset_red):
                    ok = _red_read('aiostreams.username') == m['uuid'] and _red_read('provider.aiostreams') == 'true'
            except Exception:
                ok = False
            lines.append('%s:  %s' % (label, '[COLOR FF3FD17A]authorized[/COLOR]' if ok
                                      else '[COLOR FFE05252]not synced[/COLOR]'))
        return '\n'.join(lines)
