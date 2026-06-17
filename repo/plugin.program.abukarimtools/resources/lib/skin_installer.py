# -*- coding: utf-8 -*-
"""
Skin Installer – fetches skins.json from remote and downloads/installs skins.
Adapted from script.portal.
"""

import os
import shutil
import tempfile
import zipfile
import urllib.request
import urllib.error
import json

import xbmc
import xbmcgui
import xbmcvfs

import xbmcaddon as _xbmcaddon
ADDON_PATH    = xbmcvfs.translatePath(_xbmcaddon.Addon('plugin.program.abukarimtools').getAddonInfo('path'))
if not ADDON_PATH.endswith(os.sep):
    ADDON_PATH += os.sep
PACKAGES_PATH = xbmcvfs.translatePath('special://home/addons/packages/')
ADDONS_PATH   = xbmcvfs.translatePath('special://home/addons/')

KODI_JSON  = ('https://raw.githubusercontent.com/taiseer999/'
              'taiseer999.github.io/master/skins.json')
CE_JSON    = ('https://raw.githubusercontent.com/taiseer999/'
              'taiseer999ce.github.io/master/skins.json')
PIERS_JSON = ('https://raw.githubusercontent.com/taiseer999/'
              'taiseer999Piers.github.io/master/skins.json')

TITLE = 'ABUKARIM – Skin Installer'


def _notify(msg, icon=xbmcgui.NOTIFICATION_INFO, ms=3000):
    xbmcgui.Dialog().notification(TITLE, msg, icon, ms)


def _log(msg):
    xbmc.log('[AbukarimTools SkinInstaller] %s' % msg, xbmc.LOGINFO)


def _error(msg):
    xbmcgui.Dialog().ok(TITLE, msg)


def _fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={'User-Agent': 'Kodi'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _skin_installed(addonid):
    return xbmcvfs.exists(os.path.join(ADDONS_PATH, addonid, ''))


_REPO_ENTRIES = [
    ('Kodi 21.3 Repository',              'repo_kodi.png',     KODI_JSON,  'backgroundkodi.jpg'),
    ('CoreELEC 21.3 "NG" Repository',     'repo_coreelec.png', CE_JSON,    'backgroundcoreelec.jpg'),
    ('Piers and Kodi 22 "NO" Repository', 'repo_piers.png',    PIERS_JSON, 'backgroundpiers.jpg'),
]


class _RepoSelectDialog(xbmcgui.WindowXMLDialog):
    """Custom dialog that shows icon + label for each repository option."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._result = [-1]   # mutable so GUI thread writes, caller reads after doModal

    def onInit(self):
        try:
            media_base = ('special://home/addons/plugin.program.abukarimtools'
                          '/resources/media/')
            # Static fallback background (first repo's image) shown before the
            # list gains focus or if a per-item background can't be resolved.
            self.setProperty('background', media_base + _REPO_ENTRIES[0][3])

            panel = self.getControl(100)
            panel.reset()
            icons_path = os.path.join(ADDON_PATH, 'resources', 'icons')
            for label, icon_file, _json, bg in _REPO_ENTRIES:
                li = xbmcgui.ListItem(label)
                icon_full = os.path.join(icons_path, icon_file)
                li.setArt({'icon': icon_full, 'thumb': icon_full})
                # Per-repo background so the window photo follows the focus.
                li.setProperty('repo_bg', media_base + bg)
                panel.addItem(li)
            self.setFocusId(100)
        except Exception as e:
            xbmc.log('[AbukarimTools] onInit error: %s' % str(e), xbmc.LOGERROR)

    def onClick(self, control_id):
        if control_id == 100:
            self._result[0] = self.getControl(100).getSelectedPosition()
        self.close()

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_NAV_BACK,
                               xbmcgui.ACTION_PREVIOUS_MENU,
                               xbmcgui.ACTION_STOP):
            self.close()


def _choose_source():
    dlg = _RepoSelectDialog('select_repo.xml', ADDON_PATH, 'Default', '1080i')
    dlg.doModal()
    idx = dlg._result[0]
    del dlg
    if idx < 0:
        return None, None
    _label, _icon, json_url, bg = _REPO_ENTRIES[idx]
    return json_url, bg


def _download_zip(url, addonid):
    if not xbmcvfs.exists(PACKAGES_PATH):
        xbmcvfs.mkdirs(PACKAGES_PATH)

    # على Android لا توجد /tmp — نحدد المجلد صراحةً
    _tmp_dir = xbmcvfs.translatePath('special://temp/')
    os.makedirs(_tmp_dir, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.zip', prefix='abukarim_dl_', dir=_tmp_dir)
    progress = xbmcgui.DialogProgress()
    progress.create(TITLE, 'Connecting…')

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Kodi'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            total       = int(resp.headers.get('Content-Length', 0))
            chunk_size  = 65536
            downloaded  = 0
            with os.fdopen(tmp_fd, 'wb') as fh:
                tmp_fd = None
                while True:
                    if progress.iscanceled():
                        progress.close()
                        _notify('Download cancelled.', xbmcgui.NOTIFICATION_WARNING)
                        return None
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded * 100 / total)
                        progress.update(pct, 'Downloading… %d / %d KB'
                                        % (downloaded // 1024, total // 1024))
                    else:
                        progress.update(0, 'Downloading… %d KB' % (downloaded // 1024))

        progress.update(100, 'Verifying…')
        if not zipfile.is_zipfile(tmp_path):
            _error('Download incomplete or corrupt. Please try again.')
            return None

        zip_path = os.path.join(PACKAGES_PATH, '%s.zip' % addonid)
        try:
            os.replace(tmp_path, zip_path)
        except OSError:
            shutil.copy2(tmp_path, zip_path)
            os.remove(tmp_path)
        tmp_path = None
        progress.close()
        return zip_path

    except urllib.error.URLError as e:
        progress.close()
        _error('Download failed:\n%s' % e.reason)
    except Exception as e:
        progress.close()
        _error('Download failed:\n%s' % e)
    finally:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    return None


def _extract_zip(zip_path):
    progress = xbmcgui.DialogProgress()
    progress.create(TITLE, 'Preparing extraction…')
    staging_parent = os.path.join(ADDONS_PATH, '.abukarim_staging')
    staging_dir    = None

    try:
        os.makedirs(staging_parent, exist_ok=True)
        staging_dir = tempfile.mkdtemp(dir=staging_parent, prefix='extract_')

        with zipfile.ZipFile(zip_path, 'r') as zf:
            progress.update(0, 'Checking archive integrity…')
            bad = zf.testzip()
            if bad:
                progress.close()
                _error('ZIP integrity check failed.\nFirst bad file: %s' % bad)
                return False

            members     = zf.infolist()
            total_bytes = sum(m.file_size for m in members) or 1
            done_bytes  = 0

            for info in members:
                if progress.iscanceled():
                    progress.close()
                    _notify('Extraction cancelled.', xbmcgui.NOTIFICATION_WARNING)
                    return False
                zf.extract(info, staging_dir)
                if not info.filename.endswith('/'):
                    dest   = os.path.join(staging_dir, info.filename)
                    actual = os.path.getsize(dest) if os.path.exists(dest) else -1
                    if actual != info.file_size:
                        progress.close()
                        _error('Extraction error: size mismatch for\n%s' % info.filename)
                        return False
                done_bytes += info.file_size
                progress.update(int(done_bytes * 100 / total_bytes),
                                'Extracting: %s' % os.path.basename(info.filename))

        progress.update(99, 'Installing…')
        for top_name in os.listdir(staging_dir):
            src  = os.path.join(staging_dir, top_name)
            dest = os.path.join(ADDONS_PATH, top_name)
            if os.path.exists(dest):
                shutil.rmtree(dest) if os.path.isdir(dest) else os.remove(dest)
            try:
                os.rename(src, dest)
            except OSError:
                shutil.copytree(src, dest) if os.path.isdir(src) else shutil.copy2(src, dest)

        progress.update(100, 'Done.')
        progress.close()

    except zipfile.BadZipFile:
        progress.close()
        _error('The downloaded file is not a valid ZIP archive.')
        return False
    except Exception as e:
        progress.close()
        _error('Extraction failed:\n%s' % e)
        return False
    finally:
        if staging_dir and os.path.exists(staging_dir):
            try:
                shutil.rmtree(staging_dir)
            except Exception:
                pass
        try:
            if os.path.exists(staging_parent) and not os.listdir(staging_parent):
                os.rmdir(staging_parent)
        except Exception:
            pass

    try:
        xbmcvfs.delete(zip_path)
    except Exception:
        try:
            os.remove(zip_path)
        except Exception:
            pass

    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(3000)
    return True


def _addon_is_enabled(addonid):
    """True only when Kodi reports the addon as ENABLED (not merely installed).

    System.HasAddon() is true even for disabled addons, which is why the skin
    apply used to proceed while the skin was still disabled — Kodi then threw
    the 'Add-on required / enable this add-on?' prompt and reverted. We query
    the real enabled state via JSON-RPC instead.
    """
    try:
        query = ('{"jsonrpc":"2.0","method":"Addons.GetAddonDetails",'
                 '"params":{"addonid":"%s","properties":["enabled"]},"id":1}'
                 % addonid)
        resp = json.loads(xbmc.executeJSONRPC(query))
        return resp.get('result', {}).get('addon', {}).get('enabled', False)
    except Exception:
        return False


def _enable_addon(addonid):
    """Enable the addon via JSON-RPC (reliable/synchronous) and verify it."""
    try:
        query = ('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
                 '"params":{"addonid":"%s","enabled":true},"id":1}' % addonid)
        resp = xbmc.executeJSONRPC(query)
        _log('SetAddonEnabled(%s) -> %s' % (addonid, resp))
    except Exception as e:
        _log('SetAddonEnabled failed: %s' % e)
    # Builtin as a secondary path.
    xbmc.executebuiltin('EnableAddon(%s)' % addonid)


def _wait_addon_enabled(addonid, timeout_ms=10000):
    """Poll until Kodi reports the addon as ENABLED, or timeout."""
    waited = 0
    step = 400
    while waited < timeout_ms:
        if _addon_is_enabled(addonid):
            return True
        xbmc.sleep(step)
        waited += step
    return _addon_is_enabled(addonid)


def _set_skin_setting(addonid):
    """Set the active skin.

    The JSON-RPC Settings.SetSettingValue write is silently ignored when the
    skin is not yet considered a settable value, or when called off the GUI
    thread (which is what was happening on first-run: the setting was written
    but Kodi never loaded the skin and stayed on Estuary). We therefore:
      1) try JSON-RPC and actually read the result,
    Returns True if the JSON-RPC call reported success. (Kodi may still
    show a 'keep this skin?' confirmation afterwards which the caller
    handles.)
    """
    ok = False
    try:
        query = ('{"jsonrpc":"2.0","method":"Settings.SetSettingValue",'
                 '"params":{"setting":"lookandfeel.skin","value":"%s"},"id":1}'
                 % addonid)
        resp = xbmc.executeJSONRPC(query)
        try:
            ok = json.loads(resp).get('result') is True
        except Exception:
            ok = False
        _log('SetSettingValue(lookandfeel.skin=%s) -> %s' % (addonid, resp))
    except Exception as e:
        xbmc.log('[AbukarimTools] set skin setting failed: %s' % e, xbmc.LOGERROR)
    return ok



def _current_skin():
    """Return the currently active skin addon id, or '' if unknown."""
    try:
        return xbmc.getSkinDir() or ''
    except Exception:
        pass
    try:
        import json as _json
        resp = xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Settings.GetSettingValue",'
            '"params":{"setting":"lookandfeel.skin"},"id":1}')
        return _json.loads(resp).get('result', {}).get('value', '') or ''
    except Exception:
        return ''


def _apply_skin(addonid, title):
    _log('apply start: %s (%s)' % (title, addonid))
    _notify('Enabling %s…' % title)
    # Enable via JSON-RPC (reliable) BEFORE touching the skin setting. If the
    # skin is still disabled when we set it, Kodi pops an 'Add-on required /
    # enable this add-on?' prompt (defaulting to No) and reverts to Estuary —
    # that was the prompt the user kept seeing flash by. Enabling it up front
    # means that prompt never appears.
    _enable_addon(addonid)

    # Ensure the skin is registered + enabled before switching, otherwise the
    # skin setting silently fails to apply and Kodi keeps the current skin.
    if not _wait_addon_enabled(addonid):
        _log('addon never became enabled: %s' % addonid)
        _error('Could not enable %s. Try selecting it manually in '
               'Settings > Interface > Skin.' % title)
        return False
    _log('addon enabled (verified): %s' % addonid)

    # A freshly-installed skin is not immediately a valid value for
    # lookandfeel.skin — Kodi needs time to load its addon.xml into the
    # settings/addon system. Refreshing local addons and pausing lets the
    # skin become selectable before we switch (this is why running the swap
    # as a deferred step succeeds where an immediate set was rejected).
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(2000)

    _notify('Applying %s…' % title)

    # Use the build's proven Skin Switcher routine to perform the swap.
    try:
        from resources.lib import skin_switcher
    except Exception as e:
        _log('skin_switcher import failed: %s' % e)
        skin_switcher = None

    for attempt in range(1, 7):
        if _current_skin() == addonid:
            _log('skin active after %d attempt(s): %s' % (attempt - 1, addonid))
            break

        # Apply the skin. Kodi then shows its own 'Keep this skin?' yes/no
        # confirmation with a ~5s countdown that reverts to the previous skin
        # if it isn't answered in time. The user shouldn't have to catch that
        # prompt — selecting the skin already IS the confirmation. So from the
        # instant we apply, we relentlessly answer that dialog 'Yes' (keep)
        # the moment it appears, for long enough to outlast the countdown, and
        # treat the skin as confirmed without any user interaction.
        rpc_ok = _set_skin_setting(addonid)
        _log('swap attempt %d: lookandfeel.skin=%s (rpc_ok=%s)'
             % (attempt, addonid, rpc_ok))

        watched = 0
        confirmed_click = False
        while watched < 10000:
            # Safety net: if any yes/no prompt appears (e.g. 'Add-on required /
            # enable this add-on?' or a keep-skin confirmation), answer YES.
            # IMPORTANT: on the 'Add-on required' dialog the Yes button is the
            # LEFT one (control 10); on other yes/no dialogs Yes can be control
            # 11. We click both so we always land on Yes regardless of layout.
            if xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)') \
                    or xbmc.getCondVisibility('Window.IsVisible(yesnodialog)') \
                    or xbmc.getCondVisibility('System.HasModalDialog'):
                xbmc.executebuiltin('SendClick(10100,10)')   # Yes (left) on enable prompt
                xbmc.executebuiltin('SendClick(11)')         # Yes on keep-skin prompt
                xbmc.sleep(40)
                xbmc.executebuiltin('SendClick(10)')
                confirmed_click = True
                xbmc.sleep(200)

            if _current_skin() == addonid:
                if not (xbmc.getCondVisibility('Window.IsVisible(yesnodialog)')
                        or xbmc.getCondVisibility('Window.IsVisible(DialogYesNo.xml)')):
                    break
            xbmc.sleep(100)
            watched += 100

        if _current_skin() == addonid:
            _log('verified active after attempt %d (confirmed=%s): %s'
                 % (attempt, confirmed_click, addonid))
            break

        _log('not active yet after attempt %d (current=%s)'
             % (attempt, _current_skin()))
        xbmc.sleep(1000)

    if _current_skin() != addonid:
        _log('FAILED to activate %s (current=%s)' % (addonid, _current_skin()))
        _error('%s was installed but could not be selected automatically.\n'
               'Select it in Settings > Interface > Skin.' % title)
        return False

    _log('skin activated: %s' % addonid)
    return True


class SkinPortal(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.items      = kwargs.get('items', [])
        self.background = kwargs.get('background', 'backgroundkodi.jpg')
        # first_run mode: close the portal right after a successful install
        # and let the caller apply the skin AFTER the modal is gone, so
        # ReloadSkin never fires while this window is still open.
        self.first_run  = kwargs.get('first_run', False)
        self.pending    = None      # (addonid, title) applied by run() afterwards

    def onInit(self):
        bg_path = ('special://home/addons/plugin.program.abukarimtools'
                   '/resources/media/%s' % self.background)
        self.setProperty('background', bg_path)
        panel = self.getControl(100)
        panel.reset()
        for item in self.items:
            li = xbmcgui.ListItem(item.get('name', ''))
            li.setArt({'thumb': item.get('screenshot', ''),
                       'icon':  item.get('screenshot', '')})
            li.setProperty('addonid',  item.get('id', ''))
            li.setProperty('zipurl',   item.get('zip', ''))
            li.setProperty('version',  item.get('version', ''))
            if _skin_installed(item.get('id', '')):
                li.setProperty('installed', 'true')
            panel.addItem(li)
        if self.items:
            self.setFocusId(100)

    def onClick(self, controlId):
        if controlId != 100:
            return
        panel   = self.getControl(100)
        item    = panel.getSelectedItem()
        addonid = item.getProperty('addonid')
        zipurl  = item.getProperty('zipurl')
        title   = item.getLabel()
        already = item.getProperty('installed') == 'true'

        if not zipurl:
            _error('No ZIP URL found for this skin.')
            return

        # Selecting a skin is treated as confirmation — no prompt. The previous
        # yesno() dialog was dismissed too quickly to be usable, so the click
        # on the skin itself now goes straight to install/apply.
        zip_path = _download_zip(zipurl, addonid)
        if not zip_path:
            return
        if not _extract_zip(zip_path):
            return
        _log('installed via portal: %s (first_run=%s)' % (addonid, self.first_run))

        if self.first_run:
            # Defer the skin switch until this modal is closed: the keep-skin
            # confirmation must be handled with no custom WindowXMLDialog open.
            # Close now, apply in run().
            self.pending = (addonid, title)
            item.setProperty('installed', 'true')
            self.close()
            return

        _apply_skin(addonid, title)
        _notify('✓ %s installed successfully.' % title)
        item.setProperty('installed', 'true')

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_NAV_BACK,
                               xbmcgui.ACTION_PREVIOUS_MENU):
            self.close()


def run(first_run=False):
    url, background = _choose_source()
    if not url:
        return False

    try:
        items = _fetch_json(url)
    except urllib.error.URLError as e:
        _error('Network error:\n%s' % e.reason)
        return False
    except json.JSONDecodeError:
        _error('The feed returned invalid JSON.')
        return False
    except Exception as e:
        _error('Feed error:\n%s' % e)
        return False

    if not items:
        return False

    win = SkinPortal(
        'portal.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        items=items,
        background=background,
        first_run=first_run,
    )
    win.doModal()
    pending = win.pending
    del win

    # first_run mode: the portal closed itself after a successful install;
    # apply the skin now that no custom modal window is open.
    if pending:
        addonid, title = pending
        _log('deferred apply (first_run): %s' % addonid)
        ok = _apply_skin(addonid, title)
        if ok:
            _notify('✓ %s installed successfully.' % title)
        return ok

    _log('portal closed with no pending skin to apply')
    return False
