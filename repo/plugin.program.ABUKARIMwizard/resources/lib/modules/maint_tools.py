"""
Maintenance tools ported from OpenWizard 2.0.8.1 (drinfernoo, GPL-2.0-or-later)
and adapted to ABUKARIM Wizard (Kodi 21/22, Python 3.14).

Menus live here too so the whole feature is one self-contained module.
Router modes: 200-259 (see plugin.py).
"""
import fnmatch
import glob
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from .addonvar import (addon_id, addon_name, addon_icon, addon_fanart, local_string,
                       setting, setting_set, home, addons_path, data_path, user_path,
                       db_path, packages, textures_db, addons_db, kodi_ver, headers)
from .colors import colors
from .utils import add_dir

try:
    HANDLE = int(sys.argv[1])
except (IndexError, ValueError):
    HANDLE = -1

COLOR1 = colors.color_text1
COLOR2 = colors.color_text2
COLOR3 = colors.color_text3
COLOR4 = colors.color_text4

ON = '[COLOR springgreen]ON[/COLOR]'
OFF = '[COLOR red]OFF[/COLOR]'

translate = xbmcvfs.translatePath
LOGPATH = translate('special://logpath/')
TEMP = translate('special://temp/')
THUMBNAILS = os.path.join(user_path, 'Thumbnails')
ARCHIVE_CACHE = os.path.join(TEMP, 'archive_cache')
SOURCES = os.path.join(user_path, 'sources.xml')
LOGFILES = ['kodi.log', 'kodi.old.log', 'xbmc.log', 'xbmc.old.log', 'spmc.log', 'spmc.old.log']
CLEANFREQ_DAYS = [0, 1, 3, 7, 30]

# Addons that must never be listed for removal / disabling / data wipe
DEFAULTPLUGINS = ['metadata.album.universal', 'metadata.artists.universal',
                  'metadata.common.fanart.tv', 'metadata.common.imdb.com',
                  'metadata.common.musicbrainz.org', 'metadata.themoviedb.org',
                  'metadata.themoviedb.org.python', 'metadata.tvshows.themoviedb.org.python',
                  'metadata.tvdb.com', 'metadata.tvshows.themoviedb.org',
                  'metadata.generic.albums', 'metadata.generic.artists',
                  'plugin.program.super.favourites', 'repository.xbmc.org',
                  'script.module.certifi', 'script.module.chardet', 'script.module.idna',
                  'script.module.requests', 'script.module.urllib3',
                  'skin.estuary', 'skin.estouchy', 'xbmc.python', 'kodi.resource']


def _s(string_id, fallback):
    """Localized string with English fallback (keeps menu readable if a .po lacks the id)."""
    try:
        text = local_string(string_id)
    except Exception:
        text = ''
    return text or fallback


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[%s Maintenance] %s' % (addon_name, msg), level)


def _notify(msg, ms=3000):
    xbmcgui.Dialog().notification(addon_name, msg, addon_icon, ms, sound=False)


def _refresh():
    xbmc.executebuiltin('Container.Refresh()')


def _excludes():
    """User whitelist + the wizard itself are always protected."""
    protected = {addon_id, 'packages', 'temp'}
    try:
        from .whitelist import file_path as wl_file
        if os.path.exists(wl_file):
            with open(wl_file, 'r') as f:
                protected.update(json.load(f).get('whitelist', []))
    except Exception:
        pass
    try:
        from uservar import excludes
        protected.update(excludes)
    except Exception:
        pass
    return protected


@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')


def _yesno(msg, yes, no):
    return xbmcgui.Dialog().yesno(addon_name, msg, yeslabel=yes, nolabel=no)


###########################
#          Sizes          #
###########################

def convert_size(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G']:
        if abs(num) < 1024.0:
            return '%3.02f %s%s' % (num, unit, suffix)
        num /= 1024.0
    return '%.02f %s%s' % (num, 'T', suffix)


def get_size(path, total=0):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def _cache_targets():
    """Folders wiped whole, and the addon_data root where only '*cache*' sub-dirs are wiped."""
    whole = [os.path.join(home, 'cache'), TEMP,
             os.path.join(data_path, 'script.module.simple.downloader'),
             os.path.join(data_path, 'script.extendedinfo', 'images'),
             os.path.join(data_path, 'script.extendedinfo', 'TheMovieDB'),
             os.path.join(data_path, 'script.extendedinfo', 'YouTube'),
             os.path.join(data_path, 'plugin.program.autocompletion', 'Google'),
             os.path.join(data_path, 'plugin.program.autocompletion', 'Bing')]
    return whole, data_path


def _is_protected_temp_file(name):
    return name in LOGFILES or name.endswith('.log') or name.endswith('.pid')


def get_cache_size():
    whole, addon_data_root = _cache_targets()
    total = 0
    for item in whole:
        if not os.path.exists(item):
            continue
        for root, dirs, files in os.walk(item):
            dirs[:] = [d for d in dirs if d.lower() not in ('archive_cache', 'meta_cache')]
            for f in files:
                if _is_protected_temp_file(f):
                    continue
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    protected = _excludes()
    if os.path.exists(addon_data_root):
        for entry in os.listdir(addon_data_root):
            if entry in protected:
                continue
            for root, dirs, files in os.walk(os.path.join(addon_data_root, entry)):
                for d in list(dirs):
                    if 'cache' in d.lower() and d.lower() != 'meta_cache':
                        total = get_size(os.path.join(root, d), total)
                        dirs.remove(d)
    return total


###########################
#     Cleaning Tools      #
###########################

def clear_cache(silent=False):
    whole, addon_data_root = _cache_targets()
    removed = 0
    for item in whole:
        if not os.path.exists(item):
            continue
        for root, dirs, files in os.walk(item, topdown=True):
            dirs[:] = [d for d in dirs if d.lower() not in ('archive_cache', 'meta_cache')]
            for f in files:
                if _is_protected_temp_file(f):
                    continue
                try:
                    os.unlink(os.path.join(root, f))
                    removed += 1
                except OSError:
                    pass
            for d in dirs:
                try:
                    shutil.rmtree(os.path.join(root, d))
                    removed += 1
                except OSError:
                    _log('Failed to wipe %s' % os.path.join(root, d))
            dirs[:] = []
    protected = _excludes()
    if os.path.exists(addon_data_root):
        for entry in os.listdir(addon_data_root):
            if entry in protected:
                continue
            for root, dirs, files in os.walk(os.path.join(addon_data_root, entry), topdown=True):
                for d in list(dirs):
                    if 'cache' in d.lower() and d.lower() != 'meta_cache':
                        try:
                            shutil.rmtree(os.path.join(root, d))
                            removed += 1
                            _log('Wiped %s' % os.path.join(root, d), xbmc.LOGDEBUG)
                        except OSError:
                            pass
                        dirs.remove(d)
    if not silent:
        _notify(_s(30240, 'Clear Cache: Removed %s items') % removed)
    return removed


def clear_function_cache(over=False):
    if not over and not _yesno(_s(30241, 'Would you like to clear resolver function caches?'),
                               _s(30242, 'Clear Cache'), _s(30243, 'Cancel')):
        return
    if xbmc.getCondVisibility('System.HasAddon(script.module.resolveurl)'):
        xbmc.executebuiltin('RunPlugin(plugin://script.module.resolveurl/?mode=reset_cache)')
    if xbmc.getCondVisibility('System.HasAddon(script.module.urlresolver)'):
        xbmc.executebuiltin('RunPlugin(plugin://script.module.urlresolver/?mode=reset_cache)')


def clear_archive(over=False):
    if not os.path.exists(ARCHIVE_CACHE):
        return
    if not over and not _yesno(_s(30244, "Would you like to clear the 'Archive_Cache' folder?"),
                               _s(30245, 'Yes, Clear'), _s(30243, 'Cancel')):
        return
    for entry in os.listdir(ARCHIVE_CACHE):
        path = os.path.join(ARCHIVE_CACHE, entry)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
        except OSError:
            pass


def _clear_packages_quiet():
    if not os.path.exists(packages):
        return
    for entry in os.listdir(packages):
        path = os.path.join(packages, entry)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
        except OSError:
            pass


def _redo_thumbs():
    os.makedirs(THUMBNAILS, exist_ok=True)
    for item in '0123456789abcdef':
        os.makedirs(os.path.join(THUMBNAILS, item), exist_ok=True)
    os.makedirs(os.path.join(THUMBNAILS, 'Video', 'Bookmarks'), exist_ok=True)


def _clear_thumbs_quiet():
    from .maintenance import purge_db
    try:
        purge_db(textures_db)
    except Exception as e:
        _log('Textures purge failed: %s' % e)
    for folder in (THUMBNAILS,
                   os.path.join(data_path, 'script.module.metadatautils', 'animatedgifs'),
                   os.path.join(data_path, 'script.extendedinfo', 'images')):
        shutil.rmtree(folder, ignore_errors=True)
    _redo_thumbs()


def total_clean():
    if not _yesno(_s(30246, 'Would you like to clear cache, packages and thumbnails?'),
                  _s(30247, 'Clean All'), _s(30243, 'Cancel')):
        return
    with busy_dialog():
        clear_archive(over=True)
        removed = clear_cache(silent=True)
        clear_function_cache(over=True)
        _clear_packages_quiet()
        _clear_thumbs_quiet()
    _notify(_s(30248, 'Total Clean Up complete (%s cache items)') % removed)


def old_thumbs(silent=False):
    dbfile = textures_db
    if not dbfile or not os.path.exists(dbfile):
        _log('Textures DB not found')
        return False
    week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    images, size = [], 0
    try:
        con = sqlite3.connect(dbfile, timeout=10)
        cur = con.cursor()
        cur.execute('SELECT idtexture FROM sizes WHERE usecount < ? AND lastusetime < ?', (30, week))
        ids = [row[0] for row in cur.fetchall()]
        for idfound in ids:
            cur.execute('SELECT cachedurl FROM texture WHERE id = ?', (idfound,))
            images.extend(row[0] for row in cur.fetchall())
        for idfound in ids:
            cur.execute('DELETE FROM sizes WHERE idtexture = ?', (idfound,))
            cur.execute('DELETE FROM texture WHERE id = ?', (idfound,))
        con.commit()
        con.execute('VACUUM')
        con.close()
    except sqlite3.Error as e:
        _log('Old thumbs DB error: %s' % e, xbmc.LOGERROR)
        return False
    for image in images:
        path = os.path.join(THUMBNAILS, image)
        try:
            size += os.path.getsize(path)
            os.remove(path)
        except OSError:
            pass
    _log('%s old thumbs cleaned up' % len(images))
    if not silent:
        if images:
            _notify(_s(30249, 'Clear Old Thumbs: %s files / %s') % (len(images), convert_size(size)))
        else:
            _notify(_s(30250, 'Clear Old Thumbs: none found'))
    return True


def _crash_logs():
    found = set()
    for folder in (LOGPATH, TEMP, home):
        found.update(glob.glob(os.path.join(folder, '*crashlog*.*')))
        found.update(glob.glob(os.path.join(folder, 'core*')) if folder == TEMP else [])
    return sorted(f for f in found if os.path.isfile(f))


def clear_crash():
    files = _crash_logs()
    if not files:
        _notify(_s(30251, 'No crash logs found'))
        return
    if _yesno(_s(30252, 'Delete the crash logs?') + '\n' + _s(30253, '%s files found') % len(files),
              _s(30254, 'Remove Logs'), _s(30255, 'Keep Logs')):
        for f in files:
            try:
                os.remove(f)
            except OSError:
                pass
        _notify(_s(30256, '%s crash logs removed') % len(files))


def _purge_db_file(path):
    try:
        con = sqlite3.connect(path, timeout=10)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        for (table,) in cur.fetchall():
            if table in ('version', 'sqlite_sequence'):
                continue
            try:
                cur.execute('DELETE FROM "%s"' % table)
            except sqlite3.Error as e:
                _log('DB table %s error: %s' % (table, e), xbmc.LOGERROR)
        con.commit()
        con.execute('VACUUM')
        con.close()
        return True
    except sqlite3.Error as e:
        _log('Purge %s failed: %s' % (path, e), xbmc.LOGERROR)
        return False


def purge_databases():
    dbs, display = [], []
    for dirpath, dirnames, files in os.walk(home):
        dirnames[:] = [d for d in dirnames if d not in ('packages', 'temp')]
        for f in fnmatch.filter(files, '*.db'):
            if f == 'Thumbs.db':
                continue
            full = os.path.join(dirpath, f)
            dbs.append(full)
            display.append('(%s) %s' % (os.path.basename(dirpath), f))
    if not dbs:
        _notify(_s(30257, 'No databases found'))
        return
    choice = xbmcgui.Dialog().multiselect(_s(30258, 'Select DB files to purge'), display)
    if not choice:
        return
    done = 0
    for idx in choice:
        if _purge_db_file(dbs[idx]):
            done += 1
    _notify(_s(30259, 'Purged %s database(s)') % done)


def toggle_setting(setting_id):
    setting_set(setting_id, 'false' if setting(setting_id) == 'true' else 'true')
    _refresh()


def change_freq():
    options = [_s(30260, 'Every Startup'), _s(30261, 'Every Day'), _s(30262, 'Every Three Days'),
               _s(30263, 'Every Week'), _s(30264, 'Every Month')]
    change = xbmcgui.Dialog().select(_s(30265, 'How often would you like to Auto Clean on Startup?'), options)
    if change != -1:
        setting_set('autocleanfreq', str(change))
        setting_set('nextautocleanup', '2000-01-01 00:00:00')
        _notify(_s(30266, 'Auto Clean frequency: %s') % options[change])
    _refresh()


def change_package_freq():
    options = [_s(30267, 'Disabled'), _s(30260, 'Every Startup'), _s(30268, '10 packages'), _s(30269, '20 packages')]
    change = xbmcgui.Dialog().select(_s(30270, 'Clear Packages on Startup'), options)
    if change != -1:
        setting_set('autoclearpackages', str(change))
    _refresh()


def auto_clean():
    """Called from the service at startup (packages are handled by autoclearpackages)."""
    if setting('autoclean') != 'true':
        return
    try:
        freq = int(setting('autocleanfreq') or 3)
    except ValueError:
        freq = 3
    freq = max(0, min(freq, len(CLEANFREQ_DAYS) - 1))
    now = datetime.now()
    try:
        next_run = datetime.strptime(setting('nextautocleanup'), '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        next_run = datetime(2000, 1, 1)
    if freq != 0 and next_run > now:
        _log('Auto Clean: next run %s' % next_run)
        return
    setting_set('nextautocleanup', (now + timedelta(days=CLEANFREQ_DAYS[freq])).strftime('%Y-%m-%d %H:%M:%S'))
    if setting('autoclean_cache') != 'false':
        _log('Auto Clean: cache')
        clear_cache(silent=True)
    if setting('autoclean_thumbs') != 'false':
        _log('Auto Clean: old thumbs')
        old_thumbs(silent=True)


###########################
#       Addon Tools       #
###########################

def _addon_folders():
    """(id, name, folder) for user-removable addons."""
    protected = _excludes() | {xbmc.getSkinDir()}
    out = []
    for folder in sorted(glob.glob(os.path.join(addons_path, '*/'))):
        foldername = os.path.basename(os.path.normpath(folder))
        if foldername in protected or foldername in DEFAULTPLUGINS:
            continue
        xml = os.path.join(folder, 'addon.xml')
        if not os.path.exists(xml):
            continue
        try:
            root = ElementTree.parse(xml).getroot()
            aid = root.get('id') or foldername
            name = re.sub(r'\[[^\]]+\]', '', root.get('name') or aid).strip() or aid
            out.append((aid, name, folder))
        except ElementTree.ParseError:
            continue
    return out


def _jsonrpc(method, params):
    query = json.dumps({'jsonrpc': '2.0', 'method': method, 'params': params, 'id': 1})
    try:
        return json.loads(xbmc.executeJSONRPC(query))
    except (ValueError, TypeError):
        return {}


def _get_kodi_setting(name):
    return _jsonrpc('Settings.GetSettingValue', {'setting': name}).get('result', {}).get('value')


def _set_kodi_setting(name, value):
    return _jsonrpc('Settings.SetSettingValue', {'setting': name, 'value': value})


def _addon_updates(do):
    """Temporarily stop Kodi auto-updating while removing addons."""
    if do == 'set':
        current = _get_kodi_setting('general.addonupdates')
        setting_set('default_addonupdate', str(current if current is not None else 0))
        _set_kodi_setting('general.addonupdates', 2)
    elif do == 'reset':
        try:
            value = int(float(setting('default_addonupdate') or 0))
        except ValueError:
            value = 0
        _set_kodi_setting('general.addonupdates', value if value in (0, 1, 2) else 0)


def _remove_addon(aid, folder, with_data=True):
    xbmc.executebuiltin('StopScript(%s)' % aid)
    xbmc.sleep(200)
    if addons_db and os.path.exists(addons_db):
        try:
            con = sqlite3.connect(addons_db, timeout=10)
            for table in ('addons', 'installed', 'package'):
                try:
                    con.execute('DELETE FROM %s WHERE addonID = ?' % table, (aid,))
                except sqlite3.Error:
                    pass
            con.commit()
            con.close()
        except sqlite3.Error as e:
            _log('Addons DB error removing %s: %s' % (aid, e), xbmc.LOGERROR)
    shutil.rmtree(folder, ignore_errors=True)
    if with_data:
        shutil.rmtree(os.path.join(data_path, aid), ignore_errors=True)


def remove_addons_menu():
    items = _addon_folders()
    if not items:
        _notify(_s(30271, 'No addons to remove'))
        return
    selected = xbmcgui.Dialog().multiselect(_s(30272, 'Select the addons you wish to remove'),
                                            [n for _, n, _ in items])
    if not selected:
        return
    also_data = _yesno(_s(30273, 'Also remove the addon data (settings) of the selected addons?'),
                       _s(30274, 'Remove Data'), _s(30275, 'Keep Data'))
    _addon_updates('set')
    with busy_dialog():
        for idx in selected:
            aid, name, folder = items[idx]
            _log('Removing addon %s' % aid)
            _remove_addon(aid, folder, with_data=also_data)
    xbmc.sleep(500)
    _addon_updates('reset')
    _log('Addons removed - force closing Kodi')
    os._exit(1)


def force_close():
    os._exit(1)


def remove_addon_data_menu():
    xbmcplugin.setPluginCategory(HANDLE, _s(30277, 'Remove Addon Data'))
    if not os.path.exists(data_path):
        add_dir(COLOR2(_s(30278, 'No addon data folder found.')), '', '', addon_icon, addon_fanart, '', isFolder=False)
        return
    rm = '[COLOR red][B][%s][/B][/COLOR] ' % _s(30279, 'REMOVE')
    add_dir(rm + COLOR2(_s(30280, 'All Addon Data')), 'all', 227, addon_icon, addon_fanart, '', isFolder=False)
    add_dir(rm + COLOR2(_s(30281, 'All Addon Data for Uninstalled Addons')), 'uninstalled', 227, addon_icon, addon_fanart, '', isFolder=False)
    add_dir(rm + COLOR2(_s(30282, 'All Empty Folders in Addon Data')), 'empty', 227, addon_icon, addon_fanart, '', isFolder=False)
    protected = _excludes()
    tags = {'audio.': '[COLOR orange][AUDIO][/COLOR] ', 'metadata.': '[COLOR cyan][METADATA][/COLOR] ',
            'module.': '[COLOR orange][MODULE][/COLOR] ', 'plugin.': '[COLOR blue][PLUGIN][/COLOR] ',
            'program.': '[COLOR orange][PROGRAM][/COLOR] ', 'repository.': '[COLOR gold][REPO][/COLOR] ',
            'script.': '[COLOR springgreen][SCRIPT][/COLOR] ', 'service.': '[COLOR springgreen][SERVICE][/COLOR] ',
            'skin.': '[COLOR dodgerblue][SKIN][/COLOR] ', 'video.': '[COLOR orange][VIDEO][/COLOR] ',
            'weather.': '[COLOR yellow][WEATHER][/COLOR] '}
    for folder in sorted(glob.glob(os.path.join(data_path, '*/'))):
        foldername = os.path.basename(os.path.normpath(folder))
        display = foldername
        for k, v in tags.items():
            display = display.replace(k, v)
        icon = os.path.join(addons_path, foldername, 'icon.png')
        icon = icon if os.path.exists(icon) else addon_icon
        if foldername in protected:
            label = '[COLOR springgreen][B][%s][/B][/COLOR] %s' % (_s(30283, 'PROTECTED'), display)
        else:
            label = rm + display
        add_dir(label, foldername, 227, icon, addon_fanart, foldername, isFolder=False)


def remove_addon_data(target):
    protected = _excludes()
    if target == 'all':
        if not _yesno(_s(30284, 'Remove ALL addon data stored in your userdata folder?'),
                      _s(30274, 'Remove Data'), _s(30243, 'Cancel')):
            return
        for folder in glob.glob(os.path.join(data_path, '*')):
            if os.path.basename(folder) in protected:
                continue
            shutil.rmtree(folder, ignore_errors=True) if os.path.isdir(folder) else os.remove(folder)
        _notify(_s(30285, 'Addon data removed'))
    elif target == 'uninstalled':
        if not _yesno(_s(30286, 'Remove addon data of addons that are no longer installed?'),
                      _s(30274, 'Remove Data'), _s(30243, 'Cancel')):
            return
        total = 0
        for folder in glob.glob(os.path.join(data_path, '*/')):
            name = os.path.basename(os.path.normpath(folder))
            if name in protected or os.path.exists(os.path.join(addons_path, name)):
                continue
            shutil.rmtree(folder, ignore_errors=True)
            total += 1
        _notify(_s(30287, '%s folder(s) removed') % total)
    elif target == 'empty':
        if not _yesno(_s(30288, 'Remove ALL empty folders in addon data?'),
                      _s(30274, 'Remove Data'), _s(30243, 'Cancel')):
            return
        total = 0
        for root, dirs, files in os.walk(data_path, topdown=False):
            rel = os.path.relpath(root, data_path)
            if rel == '.' or rel.split(os.sep)[0] in protected:
                continue
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                    total += 1
                except OSError:
                    pass
        _notify(_s(30287, '%s folder(s) removed') % total)
    else:
        if target in protected:
            _notify(_s(30289, 'Protected addon - data not removed'))
            return
        folder = os.path.join(data_path, target)
        if os.path.exists(folder) and _yesno(_s(30290, 'Remove the addon data for:') + '\n' + target,
                                             _s(30274, 'Remove Data'), _s(30243, 'Cancel')):
            shutil.rmtree(folder, ignore_errors=True)
    _refresh()


def _is_enabled(aid):
    res = _jsonrpc('Addons.GetAddonDetails', {'addonid': aid, 'properties': ['enabled']})
    return bool(res.get('result', {}).get('addon', {}).get('enabled', False))


def enable_addons_menu():
    xbmcplugin.setPluginCategory(HANDLE, _s(30291, 'Enable/Disable Addons'))
    items = _addon_folders()
    if not items:
        add_dir(COLOR2(_s(30292, 'No addons found to enable or disable.')), '', '', addon_icon, addon_fanart, '', isFolder=False)
        return
    add_dir('[I][B][COLOR red]%s[/COLOR][/B][/I]' % _s(30293, '!! Notice: Disabling some addons can cause issues !!'),
            '', '', addon_icon, addon_fanart, '', isFolder=False)
    add_dir(COLOR2(_s(30294, 'Enable All Addons')), '', 223, addon_icon, addon_fanart, '', isFolder=False)
    for aid, name, folder in items:
        icon = os.path.join(folder, 'icon.png')
        icon = icon if os.path.exists(icon) else addon_icon
        fanart = os.path.join(folder, 'fanart.jpg')
        fanart = fanart if os.path.exists(fanart) else addon_fanart
        if _is_enabled(aid):
            state, goto = '[COLOR springgreen][%s][/COLOR]' % _s(30295, 'Enabled'), 'false'
        else:
            state, goto = '[COLOR red][%s][/COLOR]' % _s(30296, 'Disabled'), 'true'
        add_dir('%s %s' % (state, name), goto, 224, icon, fanart, aid, name2=aid, isFolder=False)


def toggle_addon(aid, value, silent=False):
    enabled = value == 'true'
    xml = os.path.join(addons_path, aid, 'addon.xml')
    if not enabled and os.path.exists(xml):
        try:
            root = ElementTree.parse(xml).getroot()
            if any(ext.get('point') == 'xbmc.service' for ext in root.findall('extension')):
                xbmc.executebuiltin('StopScript(%s)' % aid)
                xbmc.sleep(500)
        except ElementTree.ParseError:
            pass
    res = _jsonrpc('Addons.SetAddonEnabled', {'addonid': aid, 'enabled': enabled})
    if 'error' in res and not silent:
        xbmcgui.Dialog().ok(addon_name, _s(30297, 'Error toggling %s. Make sure the addon list is up to date and try again.') % aid)
    if not silent:
        _refresh()


def enable_all_addons():
    with busy_dialog():
        for aid, _, _ in _addon_folders():
            toggle_addon(aid, 'true', silent=True)
    _refresh()


def force_check_updates(auto=False):
    _notify(_s(30298, 'Force checking for updates...'))
    if not addons_db or not os.path.exists(addons_db):
        xbmc.executebuiltin('UpdateAddonRepos')
        if auto:
            xbmc.executebuiltin('UpdateLocalAddons')
        return
    con = sqlite3.connect(addons_db, timeout=10)
    cur = con.cursor()
    cur.execute('UPDATE repo SET version = ?, checksum = ?, lastcheck = ?', ('', '', ''))
    con.commit()
    xbmc.executebuiltin('UpdateAddonRepos')
    monitor = xbmc.Monitor()
    with busy_dialog():
        repos = [r[0] for r in cur.execute('SELECT addonID FROM repo').fetchall()]
        start = time.time()
        for repo in repos:
            while not monitor.abortRequested():
                if time.time() >= start + 20 + 2 * len(repos):
                    _log('%s timed out during force check' % repo)
                    break
                row = cur.execute('SELECT lastcheck FROM repo WHERE addonID = ?', (repo,)).fetchone()
                checked = 0
                if row and row[0]:
                    try:
                        checked = time.mktime(time.strptime(row[0], '%Y-%m-%d %H:%M:%S'))
                    except ValueError:
                        checked = 0
                if checked >= start - 1:
                    break
                monitor.waitForAbort(1)
    con.close()
    _notify(_s(30299, '%s repositories force checked') % len(repos))
    if auto:
        xbmc.executebuiltin('UpdateLocalAddons')


###########################
#      Logging Tools      #
###########################

def _log_file(old=False):
    for name in (('kodi.old.log', 'xbmc.old.log') if old else ('kodi.log', 'xbmc.log')):
        path = os.path.join(LOGPATH, name)
        if os.path.exists(path):
            return path
    return None


def _error_list(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.read()
    except OSError:
        return []
    pattern = re.compile(r'EXCEPTION Thrown(.+?)-->End of Python script error report<--|'
                         r'-->Python callback/script returned the following error<--(.+?)'
                         r'-->End of Python script error report<--', re.DOTALL)
    return [(a or b).strip() for a, b in pattern.findall(data)]


def error_checking(count=False, last=False):
    errors = []
    for path in (_log_file(old=True), _log_file()):
        if path:
            errors.extend(_error_list(path))
    errors.reverse()  # newest first
    if count:
        return len(errors)
    if not errors:
        _notify(_s(30300, 'No errors found'))
        return
    from .quick_log import show_text
    if last:
        text = '[B][COLOR red]%s[/COLOR][/B]\n%s' % (_s(30301, 'Last Error in Log:'), errors[0].replace(home, '/'))
    else:
        text = '\n'.join('[B][COLOR red]%s %d:[/COLOR][/B] %s\n' % (_s(30302, 'ERROR NUMBER'), i + 1, e.replace(home, '/'))
                         for i, e in enumerate(errors))
    show_text(text)


def _dialog_watch():
    x = 0
    while not xbmc.getCondVisibility('Window.isVisible(yesnodialog)') and x < 100:
        x += 1
        xbmc.sleep(100)
    if xbmc.getCondVisibility('Window.isVisible(yesnodialog)'):
        xbmc.executebuiltin('SendClick(yesnodialog, 11)')


def _swap_bool_kodi_setting(name, label):
    current = _get_kodi_setting(name)
    if current is None:
        _notify(_s(30303, 'Setting not available: %s') % name)
        return
    new = not bool(current)
    threading.Thread(target=_dialog_watch).start()
    xbmc.sleep(200)
    _set_kodi_setting(name, new)
    _notify('%s: %s' % (label, _s(30295, 'Enabled') if new else _s(30296, 'Disabled')))
    _refresh()


def swap_debug():
    _swap_bool_kodi_setting('debug.showloginfo', _s(30304, 'Debug Logging'))


###########################
#    Misc Maintenance     #
###########################

def swap_unknown_sources():
    _swap_bool_kodi_setting('addons.unknownsources', _s(30305, 'Unknown Sources'))


def toggle_addon_updates():
    options = [_s(30306, 'Install updates automatically'),
               _s(30307, "Notify, but don't install updates"),
               _s(30308, 'Never check for updates')]
    selected = xbmcgui.Dialog().select(addon_name, options)
    if selected == -1:
        return
    _set_kodi_setting('general.addonupdates', selected)
    _notify(_s(30309, 'Addon updates: %s') % options[selected])
    _refresh()


def reload_profile():
    profile = xbmc.getInfoLabel('System.ProfileName') or 'Master user'
    xbmc.executebuiltin('LoadProfile(%s)' % profile)


def _info_label(label):
    value = xbmc.getInfoLabel(label)
    tries = 0
    while value == 'Busy' and tries < 10:
        xbmc.sleep(200)
        value = xbmc.getInfoLabel(label)
        tries += 1
    return value


def net_info():
    mac = _info_label('Network.MacAddress')
    inter_ip = _info_label('Network.IPAddress')
    ip = city = state = country = isp = _s(30310, 'Unavailable')
    for url in ('https://ipwho.is/', 'http://ip-api.com/json'):
        try:
            geo = json.loads(urlopen(Request(url, headers=headers), timeout=5).read().decode('utf-8'))
            ip = geo.get('ip') or geo.get('query') or ip
            city = geo.get('city') or city
            state = geo.get('region') or geo.get('regionName') or state
            country = geo.get('country') or country
            conn = geo.get('connection') if isinstance(geo.get('connection'), dict) else {}
            isp = conn.get('isp') or geo.get('isp') or geo.get('org') or isp
            break
        except Exception as e:
            _log('Geo lookup failed (%s): %s' % (url, e), xbmc.LOGDEBUG)
    return mac, inter_ip, ip, city, state, country, isp


def _kv(key, value):
    return '%s [COLOR white]%s[/COLOR]' % (COLOR1(key), value)


def _info_row(text):
    add_dir(text, '', '', addon_icon, addon_fanart, '', isFolder=False)


def view_ip():
    xbmcplugin.setPluginCategory(HANDLE, _s(30311, 'Network Information'))
    mac, inter_ip, ip, city, state, country, isp = net_info()
    _info_row(_kv(_s(30312, 'MAC:'), mac))
    _info_row(_kv(_s(30313, 'Internal IP:'), inter_ip))
    _info_row(_kv(_s(30314, 'External IP:'), ip))
    _info_row(_kv(_s(30315, 'City:'), city))
    _info_row(_kv(_s(30316, 'State:'), state))
    _info_row(_kv(_s(30317, 'Country:'), country))
    _info_row(_kv(_s(30318, 'ISP:'), isp))


def _mb_to_size(value):
    """'1234 MB' / '1234MB' -> human size; passthrough on anything unparsable."""
    m = re.match(r'\s*([\d.,]+)\s*([KMGT]?B)', value or '')
    if not m:
        return value
    try:
        num = float(m.group(1).replace(',', ''))
    except ValueError:
        return value
    mult = {'B': 1, 'KB': 1024, 'MB': 1024 ** 2, 'GB': 1024 ** 3, 'TB': 1024 ** 4}[m.group(2)]
    return convert_size(num * mult)


def system_info():
    xbmcplugin.setPluginCategory(HANDLE, _s(30319, 'System Information'))
    labels = ['System.FriendlyName', 'System.BuildVersion', 'System.CpuUsage', 'System.ScreenMode',
              'System.Uptime', 'System.TotalUptime', 'System.FreeSpace', 'System.UsedSpace',
              'System.TotalSpace', 'System.Memory(free)', 'System.Memory(used)', 'System.Memory(total)',
              'System.CPUTemperature', 'System.VideoEncoderInfo', 'System.KernelVersion']
    d = {lb: _info_label(lb) for lb in labels}

    counts = {'video': 0, 'program': 0, 'audio': 0, 'image': 0, 'repo': 0, 'skin': 0, 'script': 0}
    for folder in glob.glob(os.path.join(addons_path, '*/')):
        name = os.path.basename(os.path.normpath(folder))
        xml = os.path.join(folder, 'addon.xml')
        if name == 'packages' or not os.path.exists(xml):
            continue
        try:
            with open(xml, 'r', encoding='utf-8', errors='ignore') as f:
                prov = re.findall(r'<provides>(.+?)</provides>', f.read())
        except OSError:
            continue
        if not prov:
            key = 'skin' if name.startswith('skin') else 'repo' if name.startswith('repo') else 'script'
        elif 'executable' in prov[0]:
            key = 'program'
        elif 'video' in prov[0]:
            key = 'video'
        elif 'audio' in prov[0]:
            key = 'audio'
        elif 'image' in prov[0]:
            key = 'image'
        else:
            key = 'script'
        counts[key] += 1

    _info_row(COLOR2('[B]%s[/B]' % _s(30320, 'Media Center Info:')))
    _info_row(_kv(_s(30321, 'Name:'), d['System.FriendlyName']))
    _info_row(_kv(_s(30322, 'Version:'), d['System.BuildVersion']))
    _info_row(_kv(_s(30323, 'Kernel:'), d['System.KernelVersion']))
    _info_row(_kv(_s(30324, 'CPU Usage:'), d['System.CpuUsage']))
    if d['System.CPUTemperature']:
        _info_row(_kv(_s(30325, 'CPU Temperature:'), d['System.CPUTemperature']))
    _info_row(_kv(_s(30326, 'Screen Mode:'), d['System.ScreenMode']))

    _info_row(COLOR2('[B]%s[/B]' % _s(30327, 'Uptime:')))
    _info_row(_kv(_s(30328, 'Current Uptime:'), d['System.Uptime']))
    _info_row(_kv(_s(30329, 'Total Uptime:'), d['System.TotalUptime']))

    _info_row(COLOR2('[B]%s[/B]' % _s(30330, 'Local Storage:')))
    _info_row(_kv(_s(30331, 'Used Storage:'), _mb_to_size(d['System.UsedSpace'])))
    _info_row(_kv(_s(30332, 'Free Storage:'), _mb_to_size(d['System.FreeSpace'])))
    _info_row(_kv(_s(30333, 'Total Storage:'), _mb_to_size(d['System.TotalSpace'])))

    _info_row(COLOR2('[B]%s[/B]' % _s(30334, 'RAM Usage:')))
    _info_row(_kv(_s(30335, 'Used Memory:'), _mb_to_size(d['System.Memory(used)'])))
    _info_row(_kv(_s(30336, 'Free Memory:'), _mb_to_size(d['System.Memory(free)'])))
    _info_row(_kv(_s(30337, 'Total Memory:'), _mb_to_size(d['System.Memory(total)'])))

    mac, inter_ip, ip, city, state, country, isp = net_info()
    _info_row(COLOR2('[B]%s[/B]' % _s(30338, 'Network:')))
    _info_row(_kv(_s(30312, 'MAC:'), mac))
    _info_row(_kv(_s(30313, 'Internal IP:'), inter_ip))
    _info_row(_kv(_s(30314, 'External IP:'), ip))
    _info_row(_kv(_s(30317, 'Country:'), country))
    _info_row(_kv(_s(30318, 'ISP:'), isp))

    _info_row(COLOR2('[B]%s (%s)[/B]' % (_s(30339, 'Addons'), sum(counts.values()))))
    _info_row(_kv(_s(30340, 'Video Addons:'), counts['video']))
    _info_row(_kv(_s(30341, 'Program Addons:'), counts['program']))
    _info_row(_kv(_s(30342, 'Music Addons:'), counts['audio']))
    _info_row(_kv(_s(30343, 'Picture Addons:'), counts['image']))
    _info_row(_kv(_s(30344, 'Repositories:'), counts['repo']))
    _info_row(_kv(_s(30345, 'Skins:'), counts['skin']))
    _info_row(_kv(_s(30346, 'Scripts/Modules:'), counts['script']))


###########################
#  System Tweaks / Fixes  #
###########################

def _source_alive(path):
    if path.startswith(('http://', 'https://')):
        try:
            req = Request(path, headers=headers, method='HEAD')
            return urlopen(req, timeout=8).status < 400
        except Exception:
            try:
                return urlopen(Request(path, headers=headers), timeout=8).status < 400
            except Exception:
                return False
    if urlparse(path).scheme in ('', 'special') or os.path.isabs(path):
        return xbmcvfs.exists(path if path.endswith(('/', '\\')) else path + '/')
    # smb://, nfs://, ftp://, upnp:// ... let Kodi's VFS decide
    try:
        return xbmcvfs.exists(path)
    except Exception:
        return False


def check_sources():
    if not os.path.exists(SOURCES):
        _notify(_s(30347, 'No sources.xml file found'))
        return
    try:
        tree = ElementTree.parse(SOURCES)
    except ElementTree.ParseError:
        _notify(_s(30348, 'sources.xml could not be read'))
        return
    root = tree.getroot()
    entries = []
    for section in root:
        for src in section.findall('source'):
            name = src.findtext('name', '')
            for p in src.findall('path'):
                if p.text:
                    entries.append((section, src, name, p.text.strip()))
    if not entries:
        _notify(_s(30349, 'No sources found'))
        return
    dp = xbmcgui.DialogProgress()
    dp.create(addon_name, _s(30350, 'Scanning sources for broken links'))
    bad = []
    for i, (section, src, name, path) in enumerate(entries):
        if dp.iscanceled():
            break
        dp.update(int(100 * (i + 1) / len(entries)), '%s\n%s' % (name, path))
        if not _source_alive(path):
            bad.append((section, src, name, path))
    dp.close()
    if not bad:
        _notify(_s(30351, 'All sources are working'))
        return
    dialog = xbmcgui.Dialog()
    remove_all = dialog.yesno(addon_name, _s(30352, '%s source(s) appear to be broken.\nRemove all, or choose one by one?') % len(bad),
                              yeslabel=_s(30353, 'Remove All'), nolabel=_s(30354, 'Choose'))
    removed = 0
    seen = set()
    for section, src, name, path in bad:
        if id(src) in seen:
            continue
        if remove_all or dialog.yesno(addon_name, _s(30355, '%s was reported as not working:\n%s') % (name, path),
                                      yeslabel=_s(30356, 'Remove Source'), nolabel=_s(30357, 'Keep Source')):
            section.remove(src)
            seen.add(id(src))
            removed += 1
    if removed:
        shutil.copyfile(SOURCES, SOURCES + '.bak')
        tree.write(SOURCES, encoding='utf-8', xml_declaration=False)
    dialog.ok(addon_name, _s(30358, 'Source check complete.\nBroken: %s | Removed: %s') % (len(bad), removed))


def check_repos():
    repolist = glob.glob(os.path.join(addons_path, 'repository.*')) + glob.glob(os.path.join(addons_path, 'repo.*'))
    if not repolist:
        _notify(_s(30359, 'No repositories found'))
        return
    log_path = _log_file()
    offset = os.path.getsize(log_path) if log_path else 0
    xbmc.executebuiltin('UpdateAddonRepos')
    dp = xbmcgui.DialogProgress()
    dp.create(addon_name, _s(30360, 'Checking repositories...'))
    for i, repo in enumerate(repolist):
        if dp.iscanceled():
            dp.close()
            return
        dp.update(int(100 * (i + 1) / len(repolist)), os.path.basename(repo))
        xbmc.sleep(1000)
    dp.close()
    bad = set()
    if log_path:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(offset)
            new = f.read()
        for m in re.findall(r'CRepositoryUpdateJob\[(.+?)\].*?failed', new):
            bad.add(m.strip())
        for m in re.findall(r'Repository.*?(repository\.[\w.\-]+).*?(?:failed|error)', new, re.IGNORECASE):
            bad.add(m.strip())
    if bad:
        from .quick_log import show_text
        show_text('%s\n\n[COLOR red]%s[/COLOR]' % (
            _s(30361, 'These repositories did not resolve. Hosts can be down temporarily, so scan a few times before removing one.'),
            '\n'.join(sorted(bad))))
    else:
        _notify(_s(30362, 'All repositories working'))


def convert_special():
    files = []
    for root, dirs, fnames in os.walk(home):
        dirs[:] = [d for d in dirs if d not in ('packages', 'temp', 'Thumbnails')]
        files.extend(os.path.join(root, f) for f in fnames if f.endswith(('.xml', '.hash', '.properties')))
    if not files:
        return
    dp = xbmcgui.DialogProgress()
    dp.create(addon_name, _s(30363, 'Changing physical paths to special://home/'))
    home_n = home.rstrip('/\\')
    enc1 = quote(home_n)
    enc2 = enc1.replace('%3A', '%3a').replace('%5C', '%5c')
    changed = 0
    for i, path in enumerate(files):
        if dp.iscanceled():
            break
        dp.update(int(100 * (i + 1) / len(files)), path.replace(home, ''))
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        new = data
        for needle in (home_n + '/', home_n + '\\', enc1 + '%2F', enc2 + '%2f'):
            new = new.replace(needle, 'special://home/')
        if new != data:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new)
                changed += 1
            except OSError as e:
                _log('Could not convert %s: %s' % (path, e))
    dp.close()
    _notify(_s(30364, 'Convert paths complete: %s file(s) changed') % changed)


###########################
#      Backup folder      #
###########################

def cleanup_backup_folder():
    folder = translate(setting('backupfolder') or 'special://home/backups')
    if not os.path.isdir(folder) or not os.listdir(folder):
        _notify(_s(30365, 'Backup folder is empty'))
        return
    size = convert_size(get_size(folder))
    if not _yesno(_s(30366, 'Delete everything in the backup folder?') + '\n%s (%s)' % (folder, size),
                  _s(30367, 'Clean Up'), _s(30243, 'Cancel')):
        return
    for entry in os.listdir(folder):
        path = os.path.join(folder, entry)
        try:
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        except OSError:
            pass
    _notify(_s(30368, 'Backup folder cleaned'))


###########################
#          Menus          #
###########################

def _item(label, url, mode, desc='', folder=False):
    add_dir(label, url, mode, addon_icon, addon_fanart, COLOR2(desc or label), isFolder=folder)


def _header(text):
    add_dir(COLOR1('<><> [B]%s[/B] <><>' % text), '', '', addon_icon, addon_fanart, COLOR1(text), isFolder=False)


def maintenance_menu():
    xbmcplugin.setPluginCategory(HANDLE, COLOR1(local_string(30022)))
    _header(local_string(30022) or 'Maintenance')
    _item(COLOR2(_s(30200, 'Cleaning Tools')), '', 200, folder=True)
    _item(COLOR2(_s(30201, 'Addon Tools')), '', 201, folder=True)
    _item(COLOR2(_s(30202, 'Logging Tools')), '', 202, folder=True)
    _item(COLOR2(_s(30203, 'Misc Maintenance')), '', 203, folder=True)
    _item(COLOR2(_s(30204, 'Backup/Restore Build')), '', 12, folder=True)
    _item(COLOR2(_s(30205, 'Backup/Restore GUI & Skin Settings')), '', 19, folder=True)
    _item(COLOR2(_s(30206, 'System Tweaks/Fixes')), '', 204, folder=True)


def clean_menu():
    xbmcplugin.setPluginCategory(HANDLE, _s(30200, 'Cleaning Tools'))
    sizepack = get_size(packages)
    sizethumb = get_size(THUMBNAILS)
    sizearchive = get_size(ARCHIVE_CACHE) if os.path.exists(ARCHIVE_CACHE) else 0
    sizecache = get_cache_size()
    total = sizepack + sizethumb + sizecache + sizearchive
    val = lambda n: '[COLOR springgreen][B]%s[/B][/COLOR]' % convert_size(n)

    _header(_s(30200, 'Cleaning Tools'))
    _item('%s: %s' % (COLOR2(_s(30207, 'Total Clean Up')), val(total)), '', 210)
    _item('%s: %s' % (COLOR2(_s(30208, 'Clear Cache')), val(sizecache)), '', 211)
    if xbmc.getCondVisibility('System.HasAddon(script.module.resolveurl)') or \
            xbmc.getCondVisibility('System.HasAddon(script.module.urlresolver)'):
        _item(COLOR2(_s(30209, 'Clear Resolver Function Caches')), '', 212)
    _item('%s: %s' % (COLOR2(local_string(30023) or 'Clear Packages'), val(sizepack)), '', 6)
    _item('%s: %s' % (COLOR2(local_string(30024) or 'Clear Thumbnails'), val(sizethumb)), '', 7)
    if os.path.exists(ARCHIVE_CACHE):
        _item('%s: %s' % (COLOR2(_s(30210, 'Clear Archive_Cache')), val(sizearchive)), '', 213)
    _item(COLOR2(_s(30211, 'Clear Old Thumbnails')), '', 214)
    _item(COLOR2(_s(30212, 'Clear Crash Logs')), '', 215)
    _item(COLOR2(_s(30213, 'Purge Databases')), '', 216)
    _item(COLOR2(local_string(30012) or 'Fresh Start'), '', 4)

    _header(_s(30214, 'Auto Clean'))
    auto = setting('autoclean') == 'true'
    _item('%s: %s' % (COLOR2(_s(30215, 'Auto Clean Up On Startup')), ON if auto else OFF), 'autoclean', 217)
    if auto:
        freqs = [_s(30260, 'Every Startup'), _s(30261, 'Every Day'), _s(30262, 'Every Three Days'),
                 _s(30263, 'Every Week'), _s(30264, 'Every Month')]
        try:
            f = freqs[int(setting('autocleanfreq') or 3)]
        except (ValueError, IndexError):
            f = freqs[3]
        _item('--- %s: [COLOR springgreen]%s[/COLOR]' % (COLOR2(_s(30216, 'Auto Clean Frequency')), f), '', 218)
        _item('--- %s: %s' % (COLOR2(_s(30217, 'Clear Cache on Startup')),
                              OFF if setting('autoclean_cache') == 'false' else ON), 'autoclean_cache', 217)
        _item('--- %s: %s' % (COLOR2(_s(30218, 'Clear Old Thumbs on Startup')),
                              OFF if setting('autoclean_thumbs') == 'false' else ON), 'autoclean_thumbs', 217)
    pk = [_s(30267, 'Disabled'), _s(30260, 'Every Startup'), _s(30268, '10 packages'), _s(30269, '20 packages')]
    try:
        pv = pk[int(setting('autoclearpackages') or 1)]
    except (ValueError, IndexError):
        pv = pk[1]
    _item('%s: [COLOR springgreen]%s[/COLOR]' % (COLOR2(_s(30270, 'Clear Packages on Startup')), pv), '', 219)


def addon_menu():
    xbmcplugin.setPluginCategory(HANDLE, _s(30201, 'Addon Tools'))
    _header(_s(30201, 'Addon Tools'))
    _item(COLOR2(_s(30219, 'Remove Addons')), '', 220)
    _item(COLOR2(_s(30277, 'Remove Addon Data')), '', 221, folder=True)
    _item(COLOR2(_s(30291, 'Enable/Disable Addons')), '', 222, folder=True)
    _item(COLOR2(_s(30220, 'Force Refresh All Repositories')), '', 225)
    _item(COLOR2(_s(30221, 'Force Update All Addons')), '', 226)
    _item(COLOR2(local_string(30064) or 'Edit Whitelist'), '', 11)


def logging_menu():
    xbmcplugin.setPluginCategory(HANDLE, _s(30202, 'Logging Tools'))
    _header(_s(30202, 'Logging Tools'))
    errors = error_checking(count=True)
    found = ('[COLOR red]%s[/COLOR]' % (_s(30222, '%s Error(s) Found') % errors)) if errors else \
            '[COLOR springgreen]%s[/COLOR]' % _s(30223, 'None Found')
    debug = _get_kodi_setting('debug.showloginfo')
    _item('%s: %s' % (COLOR2(_s(30304, 'Debug Logging')), ON if debug else OFF), '', 230)
    _item(COLOR2(_s(30224, 'View Log File')), '', 26)
    _item('%s: %s' % (COLOR2(_s(30225, 'View Errors in Log')), found), '', 231)
    if errors:
        _item(COLOR2(_s(30226, 'View Last Error in Log')), '', 232)


def misc_menu():
    xbmcplugin.setPluginCategory(HANDLE, _s(30203, 'Misc Maintenance'))
    _header(_s(30203, 'Misc Maintenance'))
    us = _get_kodi_setting('addons.unknownsources')
    upd = _get_kodi_setting('general.addonupdates')
    upd_labels = [_s(30227, 'Auto'), _s(30228, 'Notify'), _s(30229, 'Never')]
    upd_txt = upd_labels[upd] if isinstance(upd, int) and 0 <= upd < 3 else '?'
    _item(COLOR2(_s(30311, 'Network Information')), '', 240, folder=True)
    _item(COLOR2(_s(30230, 'Speed Test')), '', 28)
    _item('%s: %s' % (COLOR2(_s(30305, 'Unknown Sources')), ON if us else OFF), '', 241)
    _item('%s: [COLOR springgreen]%s[/COLOR]' % (COLOR2(_s(30231, 'Addon Updates')), upd_txt), '', 242)
    _item(COLOR2(_s(30232, 'Reload Skin')), '', 243)
    _item(COLOR2(_s(30233, 'Reload Profile')), '', 244)
    _item(COLOR2(_s(30234, 'Force Close Kodi')), '', 245)


def tweaks_menu():
    xbmcplugin.setPluginCategory(HANDLE, _s(30206, 'System Tweaks/Fixes'))
    _header(_s(30206, 'System Tweaks/Fixes'))
    if '20' in kodi_ver:
        _item(COLOR2(local_string(30025)), '', 8, local_string(30009))
    if '21' in kodi_ver:
        _item(COLOR2(local_string(30106)), '', 29, local_string(30009))
    if '22' in kodi_ver:
        _item(COLOR2(local_string(30112)), '', 31, local_string(30009))
    _item(COLOR2(_s(30235, 'Scan Sources for Broken Links')), '', 250)
    _item(COLOR2(_s(30236, 'Scan for Broken Repositories')), '', 251)
    _item(COLOR2(_s(30237, 'Convert Paths to special://')), '', 252)
    _item(COLOR2(_s(30319, 'System Information')), '', 253, folder=True)
