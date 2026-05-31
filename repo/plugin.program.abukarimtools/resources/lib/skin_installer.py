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


def _error(msg):
    xbmcgui.Dialog().ok(TITLE, msg)


def _fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={'User-Agent': 'Kodi'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _skin_installed(addonid):
    return xbmcvfs.exists(os.path.join(ADDONS_PATH, addonid, ''))


def _choose_source():
    options = [
        'Kodi 21.3 Repository',
        'CoreELEC 21.3 "NG" Repository',
        'Piers and Kodi 22 "NO" Repository',
    ]
    idx = xbmcgui.Dialog().select('Select Repository', options)
    if idx == -1:
        return None, None
    if idx == 1:
        return CE_JSON, 'backgroundcoreelec.jpg'
    if idx == 2:
        return PIERS_JSON, 'backgroundpiers.jpg'
    return KODI_JSON, 'backgroundkodi.jpg'


def _download_zip(url, addonid):
    if not xbmcvfs.exists(PACKAGES_PATH):
        xbmcvfs.mkdirs(PACKAGES_PATH)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.zip', prefix='abukarim_dl_')
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


def _apply_skin(addonid, title):
    _notify('Enabling %s…' % title)
    xbmc.executebuiltin('EnableAddon(%s)' % addonid)
    xbmc.sleep(3000)
    _notify('Applying %s…' % title)
    xbmc.executebuiltin('Skin.SetSkin(%s)' % addonid)
    xbmc.sleep(5000)
    xbmc.executebuiltin('ReloadSkin()')


class SkinPortal(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.items      = kwargs.get('items', [])
        self.background = kwargs.get('background', 'backgroundkodi.jpg')

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

        msg = ('This skin is already installed.\nReinstall %s?' % title
               if already else 'Install %s?' % title)
        if not xbmcgui.Dialog().yesno(TITLE, msg):
            return

        zip_path = _download_zip(zipurl, addonid)
        if not zip_path:
            return
        if not _extract_zip(zip_path):
            return
        _apply_skin(addonid, title)
        _notify('✓ %s installed successfully.' % title)
        item.setProperty('installed', 'true')

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_NAV_BACK,
                               xbmcgui.ACTION_PREVIOUS_MENU):
            self.close()


def run():
    url, background = _choose_source()
    if not url:
        return

    try:
        items = _fetch_json(url)
    except urllib.error.URLError as e:
        _error('Network error:\n%s' % e.reason)
        return
    except json.JSONDecodeError:
        _error('The feed returned invalid JSON.')
        return
    except Exception as e:
        _error('Feed error:\n%s' % e)
        return

    if not items:
        return

    win = SkinPortal(
        'portal.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        items=items,
        background=background,
    )
    win.doModal()
    del win
