# -*- coding: utf-8 -*-
"""
binary_installer.py  –  ABUKARIM TOOLS

Installs binary add-ons that require platform-specific builds:
    - inputstream.adaptive
    - vfs.libarchive

Source repo is chosen automatically:
    - CoreELEC  → repository.coreelec   (has CE-optimised binaries)
    - Other     → repository.xbmc.org   (official Kodi repo)

The install uses Kodi's built-in JSON-RPC (Addons.GetAddonDetails +
ExecuteAddon InstallAddon) so no manual download/extract is needed.
"""

import os
import json
import xbmc
import xbmcgui
import xbmcvfs

# ---------------------------------------------------------------------------
ADDON_NAME = 'ABUKARIM TOOLS'
HOME       = xbmcvfs.translatePath('special://home/')
ADDONS_DIR = os.path.join(HOME, 'addons')
DIALOG     = xbmcgui.Dialog()
DP         = xbmcgui.DialogProgress()

# Binary add-ons to install
BINARIES = [
    'inputstream.adaptive',
    'vfs.libarchive',
]

# Repo add-on IDs
REPO_COREELEC = 'repository.coreelec'
REPO_KODI     = 'repository.xbmc.org'


# ---------------------------------------------------------------------------
def _log(msg):
    xbmc.log('[AbukarimTools BinaryInstaller] %s' % msg, xbmc.LOGINFO)


def _is_coreelec():
    """Return True when running on a CoreELEC installation."""
    if os.path.isdir('/etc/coreelec'):
        return True
    try:
        with open('/etc/os-release') as f:
            return any('coreelec' in line.lower() for line in f)
    except OSError:
        return False


def _jsonrpc(method, params=None):
    """Execute a Kodi JSON-RPC call and return the parsed result dict."""
    query = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params:
        query['params'] = params
    raw    = xbmc.executeJSONRPC(json.dumps(query))
    result = json.loads(raw)
    return result  # caller checks result.get('result') / result.get('error')


def _addon_installed(addon_id):
    """Return True if the addon is already installed and enabled."""
    r = _jsonrpc('Addons.GetAddonDetails', {'addonid': addon_id, 'properties': ['enabled']})
    if 'error' in r:
        return False
    return r.get('result', {}).get('addon', {}).get('enabled', False)


def _repo_available(repo_id):
    """Return True if the repo addon is installed (enabled or disabled)."""
    r = _jsonrpc('Addons.GetAddonDetails', {'addonid': repo_id})
    return 'error' not in r


def _install_via_jsonrpc(addon_id):
    """
    Trigger Kodi's own addon installer via JSON-RPC.
    Returns True if the addon appears installed afterwards.
    """
    # Kodi 19+ supports Addons.InstallAddon directly
    r = _jsonrpc('Addons.InstallAddon', {'addonid': addon_id})
    if 'error' not in r:
        xbmc.sleep(1500)
        return _addon_installed(addon_id)
    # Fallback: use ExecuteAddon to trigger Kodi's built-in installer dialog
    xbmc.executebuiltin('InstallAddon(%s)' % addon_id)
    # Wait up to 30 s for the installer to finish
    for _ in range(60):
        xbmc.sleep(500)
        if _addon_installed(addon_id):
            return True
    return _addon_installed(addon_id)


def _ensure_repo(repo_id):
    """
    Make sure the repo is installed and enabled.
    Returns (ok: bool, msg: str)
    """
    if _repo_available(repo_id):
        # ensure it is enabled
        _jsonrpc('Addons.SetAddonEnabled', {'addonid': repo_id, 'enabled': True})
        _log('Repo already present: %s' % repo_id)
        return True, 'Repo ready: %s' % repo_id

    _log('Repo not found, attempting install: %s' % repo_id)
    ok = _install_via_jsonrpc(repo_id)
    if ok:
        return True, 'Repo installed: %s' % repo_id
    return False, 'Could not install repo: %s' % repo_id


# ---------------------------------------------------------------------------
def run():
    """Entry point called from default.py router."""
    on_coreelec = _is_coreelec()
    repo_id     = REPO_COREELEC if on_coreelec else REPO_KODI
    platform    = 'CoreELEC' if on_coreelec else 'Kodi'

    _log('Platform detected: %s  →  using repo: %s' % (platform, repo_id))

    # Confirm with user
    msg = ('Platform: [B]%s[/B][CR]'
           'Repo: [B]%s[/B][CR][CR]'
           'Install the following binary add-ons?[CR][CR]%s'
           % (platform, repo_id, '[CR]'.join('  • ' + b for b in BINARIES)))

    if not DIALOG.yesno(ADDON_NAME, msg):
        _log('User cancelled.')
        return

    # Ensure the repo is available
    DP.create(ADDON_NAME, 'Checking repository…')
    DP.update(5)
    repo_ok, repo_msg = _ensure_repo(repo_id)
    _log(repo_msg)

    if not repo_ok:
        DP.close()
        DIALOG.ok(ADDON_NAME,
                  '[COLOR red]✘[/COLOR]  Could not reach [B]%s[/B].[CR][CR]'
                  'Check your internet connection and that the repo is available '
                  'for your platform.' % repo_id)
        return

    # Install each binary
    results   = []
    total     = len(BINARIES)

    for idx, addon_id in enumerate(BINARIES):
        pct = 10 + int(((idx) / total) * 85)
        DP.update(pct, 'Installing [B]%s[/B]…' % addon_id)
        _log('Processing: %s' % addon_id)

        if _addon_installed(addon_id):
            msg_line = '[COLOR lime]✔[/COLOR]  %s – already installed' % addon_id
            _log('%s already installed, skipping.' % addon_id)
            results.append((True, msg_line))
            continue

        ok = _install_via_jsonrpc(addon_id)
        if ok:
            msg_line = '[COLOR lime]✔[/COLOR]  %s – installed OK' % addon_id
            _log('%s installed successfully.' % addon_id)
        else:
            msg_line = '[COLOR red]✘[/COLOR]  %s – install failed' % addon_id
            _log('%s install FAILED.' % addon_id)
        results.append((ok, msg_line))

    DP.update(100, 'Done.')
    xbmc.sleep(400)
    DP.close()

    # Refresh addon list
    xbmc.executebuiltin('UpdateLocalAddons()')

    # Summary dialog
    succeeded = sum(1 for ok, _ in results if ok)
    failed    = len(results) - succeeded
    body      = '[B]Binary Install Results[/B] ([I]%s[/I])[CR][CR]' % platform
    body     += '[CR]'.join(m for _, m in results)
    body     += '[CR][CR]%d succeeded,  %d failed.' % (succeeded, failed)

    DIALOG.ok(ADDON_NAME, body)
    _log('Binary install run complete: %d OK, %d failed.' % (succeeded, failed))
