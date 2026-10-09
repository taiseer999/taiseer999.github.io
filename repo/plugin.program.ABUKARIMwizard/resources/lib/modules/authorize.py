"""Debrid / Trakt authorization menu - driven entirely by Account Manager
(script.module.acctmgr, "AM").

Every action is a RunScript() call into AM, which authorizes the service once
(QR / device code) and then syncs the token to every supported add-on.  The
menu reads AM's own settings to show which services are already authorized.
"""
import os
import sys
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import xbmcplugin
from .addonvar import addon_name, addon_icon, addon_fanart, addon_path, local_string
from .utils import add_dir
from .colors import colors

AM_ID = 'script.module.acctmgr'
AM_VIEWER_ID = 'script.module.acctvwr'

COLOR1 = colors.color_text1
COLOR2 = colors.color_text2
COLOR3 = colors.color_text3
COLOR4 = colors.color_text4

try:
    HANDLE = int(sys.argv[1])
except (IndexError, ValueError):
    HANDLE = -1

DEBRID_ICON = os.path.join(addon_path, 'resources', 'media', 'icons', 'debrid.png')

# key -> display name, AM action prefix, settings that prove authorization
# (first non-empty one is shown as the account name), has "Acct" action,
# AM "ShowSupported_*" suffix.
SERVICES = [
    ('realdebrid', 'Real-Debrid', ('realdebrid.username', 'realdebrid.token'), True,  'Debrid'),
    ('premiumize', 'Premiumize',  ('premiumize.username', 'premiumize.token'), True,  'Debrid'),
    ('alldebrid',  'AllDebrid',   ('alldebrid.username', 'alldebrid.token'),   True,  'Debrid'),
    ('torbox',     'TorBox',      ('torbox.token',),                           True,  'Torbox'),
    ('easydebrid', 'Easy Debrid', ('easydebrid.token',),                       False, 'Easydebrid'),
    ('offcloud',   'OffCloud',    ('offcloud.userid', 'offcloud.token'),       False, 'Offcloud'),
    ('easynews',   'Easynews',    ('easynews.username',),                      False, 'Easynews'),
    ('trakt',      'Trakt',       ('trakt.username', 'trakt.token'),           True,  'Trakt'),
    ('mdblist',    'MDBList',     ('mdblist.username', 'mdblist.apikey'),      False, 'MDBList'),
]
_BY_KEY = {s[0]: s for s in SERVICES}
_TOKEN_ONLY = {'torbox', 'easydebrid'}      # no account name stored -> just "Authorized"


def _has(addon_id):
    return xbmc.getCondVisibility(f'System.HasAddon({addon_id})')


def _am():
    try:
        return xbmcaddon.Addon(AM_ID)
    except Exception:
        return None


def _am_icon(key):
    # Bundled service logos in their original brand colours (resources/media/icons/svc_*.png)
    path = os.path.join(addon_path, 'resources', 'media', 'icons', f'svc_{key}.png')
    return path if os.path.isfile(path) else DEBRID_ICON


def _run(action):
    return f'RunScript({AM_ID}, action={action})'


def _status(am, key):
    """Return the account label if the service is authorized in AM, else ''."""
    for sid in _BY_KEY[key][2]:
        try:
            val = am.getSetting(sid)
        except Exception:
            val = ''
        if val:
            if key in _TOKEN_ONLY or sid.endswith(('.token', '.apikey')):
                return local_string(30405)              # Authorized
            return val
    return ''


def _not_installed():
    add_dir(COLOR3(f'[B]{local_string(30402)}[/B]'), '', '', DEBRID_ICON, addon_fanart,
            COLOR2(local_string(30403)), isFolder=False)                          # AM not installed
    add_dir(COLOR2(local_string(30404)), '', 41, DEBRID_ICON, addon_fanart,
            COLOR2(local_string(30403)), isFolder=False)                          # Install AM


def authorize_menu():
    xbmcplugin.setPluginCategory(HANDLE, local_string(30026))
    add_dir(COLOR1(f'<><> [B]{local_string(30400)}[/B] <><>'), '', '', DEBRID_ICON, addon_fanart,
            COLOR1(local_string(30401)), isFolder=False)                          # Header

    am = _am()
    if am is None:
        _not_installed()
        return

    for key, label, _ids, _acct, _sup in SERVICES:
        icon = _am_icon(key)
        state = _status(am, key)
        if state:
            row = f'{label}   {COLOR4("[" + state + "]")}'
            desc = local_string(30406).format(label, state)                       # Authorized as ...
        else:
            row = f'{label}   [COLOR grey][{local_string(30407)}][/COLOR]'
            desc = local_string(30408).format(label)                              # Not authorized
        add_dir(COLOR2(row), '', 27, icon, addon_fanart, COLOR2(desc), name2=key)

    add_dir(COLOR2(local_string(30420)), _run('allRevoke'), 25, DEBRID_ICON, addon_fanart,
            COLOR2(local_string(30421)), isFolder=False)                          # Revoke all
    add_dir(COLOR2(local_string(30422)), '', 40, DEBRID_ICON, addon_fanart,
            COLOR2(local_string(30423)), isFolder=False)                          # AM settings


def authorize_submenu(name, icon=None):
    key = name if name in _BY_KEY else None
    am = _am()
    if am is None or key is None:
        if am is None:
            _not_installed()
        return

    _key, label, _ids, has_acct, supported = _BY_KEY[key]
    icon = _am_icon(key)
    state = _status(am, key)
    xbmcplugin.setPluginCategory(HANDLE, label)

    if state:
        add_dir(COLOR4(f'[B]{label}[/B]   [{state}]'), '', '', icon, addon_fanart,
                COLOR2(local_string(30406).format(label, state)), isFolder=False)
        if has_acct:
            add_dir(COLOR2(local_string(30410)), _run(f'{key}Acct'), 25, icon, addon_fanart,
                    COLOR2(local_string(30411)), isFolder=False)                  # Account info
        add_dir(COLOR2(local_string(30412)), _run(f'{key}ReSync'), 25, icon, addon_fanart,
                COLOR2(local_string(30413) if key != 'trakt' else local_string(30419)),
                isFolder=False)                                                   # Re-sync
        if key == 'trakt':
            add_dir(COLOR2(local_string(30418)), _run('traktEditSyncList'), 25, icon, addon_fanart,
                    COLOR2(local_string(30419)), isFolder=False)                  # Edit Trakt sync list
        if _has(AM_VIEWER_ID):
            add_dir(COLOR2(local_string(30414)), _run(f'{key}Viewer'), 25, icon, addon_fanart,
                    COLOR2(local_string(30415)), isFolder=False)                  # View authorized add-ons
        add_dir(COLOR3(local_string(30416)), _run(f'{key}Revoke'), 25, icon, addon_fanart,
                COLOR2(local_string(30417)), isFolder=False)                       # Revoke
    else:
        add_dir(COLOR4(f'[B]{label}[/B]   [{local_string(30407)}]'), '', '', icon, addon_fanart,
                COLOR2(local_string(30408).format(label)), isFolder=False)
        auth_desc = local_string(30425) if key == 'trakt' else local_string(30409)
        add_dir(COLOR2(local_string(30424).format(label)), _run(f'{key}Auth'), 25, icon, addon_fanart,
                COLOR2(auth_desc), isFolder=False)                                # Authorize

    add_dir(COLOR2(local_string(30426)), _run(f'ShowSupported_{supported}'), 25, icon, addon_fanart,
            COLOR2(local_string(30427)), isFolder=False)                          # Supported add-ons


def open_am_settings():
    if _am() is None:
        install_am()
        return
    xbmc.executebuiltin(f'Addon.OpenSettings({AM_ID})')


def install_am():
    if _has(AM_ID):
        xbmc.executebuiltin('Container.Refresh')
        return
    xbmc.executebuiltin(f'InstallAddon({AM_ID})', True)
    monitor = xbmc.Monitor()
    for _ in range(60):                                   # up to ~30 s
        if _has(AM_ID) or monitor.abortRequested():
            break
        if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)'):
            xbmc.executebuiltin('SendClick(yesnodialog,11)')
        monitor.waitForAbort(0.5)
    if _has(AM_ID):
        xbmcgui.Dialog().notification(addon_name, local_string(30428), addon_icon, 3000)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().ok(addon_name, local_string(30429))
