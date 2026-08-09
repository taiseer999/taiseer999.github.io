import os
import json
from datetime import datetime
import time
import sqlite3
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pathlib import Path
import shutil
import xbmc
import xbmcvfs
import xbmcaddon
from .downloader import Downloader
from .save_data import save_backup_restore
from .maintenance import fresh_start, clean_backups, truncate_tables
from .addonvar import dp, dialog, zippath, addon_name, addon_id, home, setting, setting_set, local_string, addons_db
from .colors import colors

COLOR1 = colors.color_text1
COLOR2 = colors.color_text2

addons_path = Path(xbmcvfs.translatePath('special://home/addons'))
user_data = Path(xbmcvfs.translatePath('special://userdata'))
binaries_path = Path(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))) / 'binaries.json'

def build_install(name, name2, version, url):
    # Ready to install, Cancel, Continue
    if not dialog.yesno(
        COLOR2(name),
        COLOR2(local_string(30028)),
        nolabel=local_string(30029),
        yeslabel=local_string(30030)
    ):
        return
    
    download_build(name, url)
    save_backup_restore('backup')
    fresh_start()
    extract_build()
    if name2 == setting('buildname'):
        save_backup_restore('restore_gui')
    else:
        save_backup_restore('restore')
    clean_backups()
    setting_set('buildname', name2)
    setting_set('buildversion', version)
    setting_set('update_passed', 'false')
    setting_set('firstrun', 'true')
    check_binary()
    enable_wizard()
    truncate_tables()
    
    dialog.ok(addon_name, local_string(30036))  # Install Complete
    os._exit(1)

def patch_gui(url):
    if not url or url in ('', 'http://', None):
        dialog.ok(addon_name, local_string(30116))  # No GUI Patch Available For This Build!
        return

    # Patch GUI, Cancel, Continue
    if not dialog.yesno(
        COLOR2(local_string(30113)),  # Patch GUI
        COLOR2(local_string(30115)),  # This will update your GUI/skin files in place...
        nolabel=local_string(30029),
        yeslabel=local_string(30030)
    ):
        return

    download_build(local_string(30113), url)
    extract_gui_patch()

    # Some skins (e.g. Arctic Fuse 3, via script.skinvariables) only rebuild
    # their home menu/widgets on skin load if this skin string has changed
    # since they last processed it - exactly what happens when a user opens
    # and exits that skin's own shortcuts/variables editor. Bumping it here
    # mirrors that, so the rebuild fires automatically as part of ReloadSkin()
    # below. Harmless no-op on skins that don't use this convention.
    xbmc.executebuiltin('Skin.SetString(Shortcuts.RebuildDateTime,{0})'.format(datetime.now().strftime('%Y-%m-%d_%H:%M:%S')))
    xbmc.executebuiltin('ReloadSkin()')

    dialog.ok(addon_name, local_string(30117))  # GUI Patch Applied Successfully!

def extract_gui_patch():
    if os.path.exists(zippath):
        dp.create(addon_name, 'Patching GUI')
        counter = 1
        with ZipFile(zippath, 'r') as z:
            files = z.infolist()
            for file in files:
                filename = file.filename
                progress_percentage = int(counter/len(files)*100)
                try:
                    z.extract(file, home)
                except Exception as e:
                    xbmc.log(f'Error extracting {filename} - {e}', xbmc.LOGINFO)
                dp.update(progress_percentage, f'Patching GUI...\n{progress_percentage}%\n{filename}')
                counter += 1
        dp.update(100, local_string(30035))  # Done Extracting
        xbmc.sleep(500)
        dp.close()
        os.unlink(zippath)

def patch_gui_no_wipe(url):
    if not url or url in ('', 'http://', 'https://', None):
        dialog.ok(addon_name, local_string(30116))  # No GUI Patch Available For This Build!
        return

    # No Wipe (Option 2), Cancel, Continue
    if not dialog.yesno(
        COLOR2(local_string(30118)),  # No Wipe (Option 2)
        COLOR2(local_string(30115)),  # This will update your files in place without wiping. Continue?
        nolabel=local_string(30029),
        yeslabel=local_string(30030)
    ):
        return

    download_build(local_string(30118), url)
    extract_userdata_patch()

    # Option 2 patches both the skin/menu templates (addons/skin.../shortcuts/)
    # and userdata (guisettings.xml, Database, addon_data). Kodi holds userdata
    # in memory and writes it back on exit, which would overwrite the freshly
    # extracted files, and ReloadSkin() won't reload them. So force-close: on
    # next start Kodi loads the patched userdata fresh AND script.skinvariables
    # rebuilds the menu from the updated templates under addons/.
    dialog.ok(addon_name, local_string(30119))  # Update applied. Kodi will now close - reopen it to finish.
    os._exit(1)

def extract_userdata_patch():
    if os.path.exists(zippath):
        dp.create(addon_name, 'Updating')
        counter = 1
        with ZipFile(zippath, 'r') as z:
            files = z.infolist()

            # Decide the extract target from the zip's own structure so files
            # never land in the wrong place:
            #   - entries prefixed with 'userdata/'  -> extract to special://home
            #       (home + userdata/... = home/userdata/...)
            #   - entries already relative to userdata (addon_data/..., *.xml)
            #       -> extract to special://userdata
            names = [f.filename for f in files if f.filename and not f.filename.startswith('__MACOSX')]
            top_levels = sorted({ (n.split('/', 1)[0] if '/' in n else n) for n in names })

            # Option 2 now patches BOTH the skin/menu (addons/) and settings
            # (userdata/) so it can update menus too. Pick the target from the
            # zip's own top-level folders:
            #   - if entries are rooted at 'addons/' and/or 'userdata/', they are
            #     already relative to the Kodi home dir -> extract to
            #     special://home so addons/... and userdata/... both land right.
            #   - otherwise the entries are relative to userdata itself
            #     (addon_data/..., *.xml) -> extract to special://userdata.
            rooted_at_home = any(
                n == 'addons/' or n.startswith('addons/') or
                n == 'userdata/' or n.startswith('userdata/')
                for n in names
            )
            target = str(home) if rooted_at_home else str(user_data)
            xbmc.log(f'ABUKARIMwizard extract_userdata_patch: top_levels={top_levels} rooted_at_home={rooted_at_home} target={target}', xbmc.LOGINFO)

            for file in files:
                filename = file.filename
                if not filename or filename.startswith('__MACOSX'):
                    counter += 1
                    continue
                progress_percentage = int(counter/len(files)*100)
                try:
                    z.extract(file, target)
                except Exception as e:
                    xbmc.log(f'Error extracting {filename} - {e}', xbmc.LOGINFO)
                dp.update(progress_percentage, f'Updating...\\n{progress_percentage}%\\n{filename}')
                counter += 1
        dp.update(100, local_string(30035))  # Done Extracting
        xbmc.sleep(500)
        dp.close()
        os.unlink(zippath)

def download_build(name, url):
    if os.path.exists(zippath):
        os.unlink(zippath)
    d = Downloader(url)
    d.download_build(name, zippath)

def extract_build():
    if os.path.exists(zippath):
        dp.create(addon_name, local_string(30034))  # Extracting files
        counter = 1
        with ZipFile(zippath, 'r') as z:
            files = z.infolist()
            for file in files:
                filename = file.filename
                filename_path = os.path.join(home, filename)
                progress_percentage = int(counter/len(files)*100)
                try:
                    if not os.path.exists(filename_path) or 'Addons33.db' in filename:
                        z.extract(file, home)
                except Exception as e:
                    xbmc.log(f'Error extracting {filename} - {e}', xbmc.LOGINFO)
                dp.update(progress_percentage, f'{local_string(30034)}...\n{progress_percentage}%\n{filename}')
                counter += 1
        dp.update(100, local_string(30035))  # Done Extracting
        xbmc.sleep(500)
        dp.close()
        os.unlink(zippath)

def check_binary():
    binary_list = []
    for folder in addons_path.iterdir():
        if folder.is_dir():
            addon_xml = folder / 'addon.xml'
            if addon_xml.exists():
              with open(addon_xml, 'r', encoding='utf-8', errors='ignore') as f:
                  _xml = f.read()
              if 'kodi.binary' in _xml:
                  try:
                      root = ET.fromstring(_xml)
                      binary_list.append(root.attrib['id'])
                  except:
                      binary_list.append(folder.name)
                  try:
                      shutil.rmtree(folder)
                  except PermissionError as e:
                      xbmc.log(f'Unable to delete binary {folder} - {e}')
    if len(binary_list) > 0:
        with open(binaries_path, 'w', encoding='utf-8') as f:
            json.dump({'items': binary_list}, f, indent = 4)

def restore_binary():
    with open(binaries_path, 'r', encoding='utf-8', errors='ignore') as f:
        binaries_list = json.loads(f.read())['items']
    failed = []
    for plugin_id in binaries_list:
        install = install_addon(plugin_id)
        if install is not True:
            failed.append(plugin_id)
    if len(failed) == 0:
        binaries_path.unlink()
    else:
        with open(binaries_path, 'w', encoding='utf-8') as f:
            json.dump({'items': failed}, f, indent = 4)

def install_addon(plugin_id):
    if xbmc.getCondVisibility(f'System.HasAddon({plugin_id})'):
        return True
    xbmc.executebuiltin(f'InstallAddon({plugin_id})')
    clicked = False
    start = time.time()
    timeout = 20
    while not xbmc.getCondVisibility(f'System.HasAddon({plugin_id})'):
        if time.time() >= start + timeout:
            return False
        xbmc.sleep(500)
        if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)') and not clicked:
            xbmc.executebuiltin('SendClick(yesnodialog, 11)')
            clicked = True
    return True
# Binaries inspired Dr. Infernoo

def enable_wizard():
    try:
        timestamp = str(datetime.now())[:-7]

        con = sqlite3.connect(addons_db)
        cursor = con.cursor()
        cursor.execute('INSERT or IGNORE into installed (addonID , enabled, installDate) VALUES (?,?,?)', (addon_id, 1, timestamp,))

        cursor.execute('UPDATE installed SET enabled = ? WHERE addonID = ? ', (1, addon_id,))
        con.commit()
    except sqlite3.Error as e:
        xbmc.log('There was an error writing to the database - %s' %e, xbmc.LOGINFO)
        return
    finally:
        try:
            if con:
                con.close()
        except UnboundLocalError as e:
            xbmc.log('%s: There was an error connecting to the database - %s' % (xbmcaddon.Addon().getAddonInfo('name'), e), xbmc.LOGINFO)
