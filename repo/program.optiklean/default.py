import sys
import sqlite3
import os
import errno
import fnmatch
import re
import json
import time
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

try:
    addon_handle = int(sys.argv[1])
except IndexError:
    addon_handle = -1
    
base_url = sys.argv[0]

addon = xbmcaddon.Addon()
# Path to addon_data for storing logs
addon_data_folder = xbmcvfs.translatePath(f"special://profile/addon_data/{addon.getAddonInfo('id')}/")

# Ensure addon_data directory exists
if not xbmcvfs.exists(addon_data_folder):
    xbmcvfs.mkdirs(addon_data_folder)


def ensure_path_format(path):
    """
    Ensures consistent path formatting across different platforms,
    especially for Android where path handling can be tricky.
    """
    # Remove any trailing slashes
    path = path.rstrip('/')
    # Ensure we have exactly one trailing slash
    return path + '/'


# Definisce i percorsi per i file di log
log_files = {
    "clear_kodi_temp_folder": os.path.join(addon_data_folder, "clear_kodi_temp_folder.log"),
    "clear_cache_files_from_addon_data": os.path.join(addon_data_folder, "clear_cache_files_from_addon_data.log"),
    "clear_temp_folders_from_addon_data": os.path.join(addon_data_folder, "clear_temp_folders_from_addon_data.log"),
    "clear_temp_folder_from_addons": os.path.join(addon_data_folder, "clear_temp_folder_from_addons.log"), 
    "clear_unused_thumbnails": os.path.join(addon_data_folder, "clear_unused_thumbnails.log"),
    "clear_addon_leftovers": os.path.join(addon_data_folder, "clear_addon_leftovers.log"),
    "clear_kodi_packages": os.path.join(addon_data_folder, "clear_kodi_packages.log"),
    "optimize_databases": os.path.join(addon_data_folder, "optimize_databases.log"),
}


def get_file_size(file_path):
    """Returns file size in bytes or 0 if file doesn't exist"""
    try:
        if xbmcvfs.exists(file_path):
            file = xbmcvfs.File(file_path)
            size = file.size()
            file.close()
            return size
            
        # Fallback to os.path if xbmcvfs fails
        if os.path.exists(file_path):
            return os.path.getsize(file_path)

    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Error getting size for {file_path}: {str(e)}", xbmc.LOGERROR)
    return 0


def update_automatic_settings_log():
    """Genera/Aggiorna il log delle impostazioni automatiche con stato e prossima esecuzione"""

    log_path = os.path.join(addon_data_folder, "automatic_cleaning_settings.log")
    cleaning_types = [
        "clear_cache_and_temp",
        "clear_unused_thumbnails",
        "clear_addon_leftovers",
        "clear_kodi_packages",
        "optimize_databases"
    ]

    # Ottieni il formato data/ora dalle impostazioni regionali di Kodi
    date_format = xbmc.getRegion('dateshort')
    time_format = xbmc.getRegion('time').replace('%H', 'HH').replace('%I', 'hh').replace('%M', 'mm')

    # Mappa per convertire i pattern regionali in formato Python
    format_map = {
        'DD': '%d', 'MM': '%m', 'YYYY': '%Y',
        'hh': '%I', 'mm': '%M', 'ss': '%S', 'HH': '%H',
        'AP': '%p' if '%p' in xbmc.getRegion('time') else ''
    }

    # Converti i formati regionali in formato Python
    py_date_format = date_format
    py_time_format = time_format
    for k, v in format_map.items():
        py_date_format = py_date_format.replace(k, v)
        py_time_format = py_time_format.replace(k, v)

    full_format = f"{py_date_format} {py_time_format}"

    log_content = "Automatic cleaning settings status:\n\n"

    for cleaning in cleaning_types:
        enabled = addon.getSettingBool(f"{cleaning}_enable")
        interval_days = addon.getSettingInt(f"{cleaning}_interval")

        if not enabled:
            log_content += f"Automatic {cleaning.replace('_', ' ')} -> disabled\n"
            continue

        # Leggi il file JSON dell'ultima esecuzione
        last_run_file = os.path.join(addon_data_folder, f"last_{cleaning}.json")
        next_run_info = ""

        if xbmcvfs.exists(last_run_file):
            try:
                with open(last_run_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_run_timestamp = data.get('timestamp', 0)
                    last_run_human = data.get('human_readable', '')

                    if last_run_timestamp > 0:
                        last_run_local = datetime.fromtimestamp(last_run_timestamp).strftime(full_format)
                        next_run = datetime.fromtimestamp(last_run_timestamp + (interval_days * 86400))
                        next_run_local = next_run.strftime(full_format)
                        day_label = "day" if interval_days == 1 else "days"
                        next_run_info = (
                            f" (set on {last_run_local})\n"
                            f"next run time: {next_run_local} (every {interval_days} {day_label})"
                        )
                    elif last_run_human:
                        next_run_info = f" (set on {last_run_human})\nnext run time: unknown"
            except Exception as e:
                xbmc.log(f"OptiKlean: Error reading {last_run_file}: {str(e)}", xbmc.LOGERROR)
                next_run_info = "\n(last run time unknown)"
        else:
            next_run_info = "\n(first run pending)"

        log_content += f"Automatic {cleaning.replace('_', ' ')} -> enabled{next_run_info}\n\n"

    # Scrivi il file di log usando xbmcvfs
    try:
        file = xbmcvfs.File(log_path, 'w')
        file.write(log_content)
        file.close()
        xbmc.log("OptiKlean: Updated automatic settings log", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"OptiKlean: Error writing automatic settings log: {str(e)}", xbmc.LOGERROR)


def update_last_run(cleaning_type):
    """
    Aggiorna il file JSON con i valori correnti per una determinata opzione attiva.
    """
    try:
        last_run_file = os.path.join(addon_data_folder, f"last_{cleaning_type}.json")
        data = {
            "enabled": addon.getSettingBool(f"{cleaning_type}_enable"),
            "interval": addon.getSettingInt(f"{cleaning_type}_interval"),
            "timestamp": int(time.time()),
            "human_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(last_run_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        xbmc.log(f"OptiKlean: Updated last run info for {cleaning_type}", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"OptiKlean: Failed to update last run for {cleaning_type}: {str(e)}", xbmc.LOGERROR)


def monitor_settings_changes():
    """Monitora le modifiche alle impostazioni e aggiorna il log quando cambiano"""
    try:
        settings_to_monitor = [
            ("clear_cache_and_temp", "enable", "interval"),
            ("clear_unused_thumbnails", "enable", "interval"),
            ("clear_addon_leftovers", "enable", "interval"),
            ("clear_kodi_packages", "enable", "interval"),
            ("optimize_databases", "enable", "interval")
        ]

        settings_changed = False

        for prefix, enable_suffix, interval_suffix in settings_to_monitor:
            current_enable = addon.getSettingBool(f"{prefix}_{enable_suffix}")
            current_interval = addon.getSettingInt(f"{prefix}_{interval_suffix}")

            last_run_file = os.path.join(addon_data_folder, f"last_{prefix}.json")

            if xbmcvfs.exists(last_run_file):
                with open(last_run_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_enable = data.get("enabled", False)
                    last_interval = data.get("interval", 7)
            else:
                last_enable = not current_enable
                last_interval = current_interval + 1

            if (current_enable != last_enable) or (current_interval != last_interval):
                settings_changed = True
                if current_enable:
                    update_last_run(prefix)
                else:
                    if xbmcvfs.exists(last_run_file):
                        xbmcvfs.delete(last_run_file)
                        xbmc.log(f"OptiKlean: Eliminato file {last_run_file} perché disabilitato", xbmc.LOGINFO)

        if settings_changed:
            update_automatic_settings_log()
            xbmc.log("OptiKlean: Log impostazioni aggiornato!", xbmc.LOGINFO)

    except Exception as e:
        xbmc.log(f"OptiKlean: Errore nel monitoraggio: {str(e)}", xbmc.LOGERROR)
        

# Funzione per mostrare il menu principale
def show_menu():
    addon_path = xbmcvfs.translatePath(addon.getAddonInfo("path"))
    media_path = f"{addon_path}/resources/media/"
    fanart_path = f"{media_path}fanart.jpg"
    logo_path = f"{media_path}logo.png"
    
    # Set fanart per tutto il menu (sfondo dietro le voci)
    xbmcplugin.setPluginFanart(addon_handle, fanart_path)

    # Mappa azioni -> icone
    icons = {
        "clear_cache_and_temp": f"{media_path}cache.png",
        "clear_unused_thumbnails": f"{media_path}thumbnails.png",
        "clear_addon_leftovers": f"{media_path}leftovers.png",
        "clear_kodi_packages": f"{media_path}packages.png",
        "optimize_databases": f"{media_path}databases.png",
        "view_logs": f"{media_path}logs.png",
        "show_support": f"{media_path}help.png"
    }

    menu_items = [
        ("Clear cache and temp", "clear_cache_and_temp"),
        ("Clear unused thumbnails", "clear_unused_thumbnails"),
        ("Clear addons leftovers", "clear_addon_leftovers"),
        ("Clear packages", "clear_kodi_packages"),
        ("Optimize databases", "optimize_databases"),
        ("View logs", "view_logs"),
        ("Support", "show_support")
    ]

    for label, action in menu_items:
        li = xbmcgui.ListItem(label)
        li.setArt({
            "icon": icons.get(action, ""),
            "thumb": icons.get(action, ""),
            "poster": logo_path,
            "fanart": fanart_path
        })
        li.setProperty("fanart_image", fanart_path)

        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=f"{base_url}?action={action}",
            listitem=li,
            isFolder=False
        )

    xbmcplugin.endOfDirectory(addon_handle)

    # Aggiorna il log sia all'apertura che dopo modifiche
    try:
        monitor_settings_changes()  # Prima verifica le modifiche
    except Exception as e:
        xbmc.log(f"OptiKlean: Error updating logs: {str(e)}", xbmc.LOGERROR)


# Funzione helper per scrivere il log
def write_log(log_key, content, append=False):
    """
    Writes content to the specified log file with automatic timestamp footer.
    If append is True, the content will be appended to the file instead of overwriting it.
    """
    def get_localized_datetime():
        """Get current datetime formatted according to Kodi's regional settings"""
        # Get Kodi's time format (12h vs 24h)
        time_format = xbmc.getRegion('time').replace('%H', 'HH').replace('%I', 'hh').replace('%M', 'mm')
        
        # Get date format based on region
        date_format = xbmc.getRegion('dateshort')
        
        # Convert to Python datetime format
        format_map = {
            'DD': '%d', 'MM': '%m', 'YYYY': '%Y',
            'hh': '%I', 'mm': '%M', 'ss': '%S', 'HH': '%H',
            'AP': '%p' if '%p' in xbmc.getRegion('time') else ''
        }
        
        for k, v in format_map.items():
            date_format = date_format.replace(k, v)
            time_format = time_format.replace(k, v)
        
        full_format = f"{date_format} {time_format}"
        return time.strftime(full_format)
    
    log_path = log_files.get(log_key)
    mode = "a" if append else "w"
    
    try:
        with open(log_path, mode, encoding="utf-8") as f:
            f.write(content)
            if not content.endswith('\n'):
                f.write('\n')
            # Fix: content is a string, not a dictionary
            f.write(f"\nDate and time: {get_localized_datetime()}\n")
    except Exception as e:
        xbmc.log(f"Error writing log file {log_path}: {e}", xbmc.LOGERROR)


# Costanti per lo stato di eliminazione file
DELETE_SUCCESS = "success"
DELETE_LOCKED = "locked"
DELETE_ERROR = "error"


# Funzione helper migliorata per eliminare file con rilevamento file lock
def delete_file(file_path, retry_count=2, retry_delay=0.5, progress_dialog=None):
    """
    Delete a file with lock detection and retry logic.
    Returns:
        tuple: (status, error_message)
        status can be: "success", "locked", or "error"
    """
    xbmc.log(f"OptiKlean DEBUG: Attempting to delete file: {file_path}", xbmc.LOGINFO)
    
    if not xbmcvfs.exists(file_path):
        xbmc.log(f"OptiKlean DEBUG: File doesn't exist: {file_path}", xbmc.LOGINFO)
        return DELETE_SUCCESS, ""
    
    # Aggiorna la dialog di progresso se fornita
    if progress_dialog:
        filename = file_path.split('/')[-1] if file_path else ""
        # Fix: use getPercentage() instead of getPercent()
        try:
            percent = progress_dialog.getPercentage()
        except AttributeError:
            # Fallback for older Kodi versions
            percent = 0
        progress_dialog.update(percent, f"Processing: {filename}")
    
    # Rest of the function remains unchanged
    for attempt in range(retry_count + 1):
        try:
            xbmc.log(f"OptiKlean DEBUG: Delete attempt {attempt+1}/{retry_count+1} for {file_path}", xbmc.LOGINFO)
            if xbmcvfs.delete(file_path):
                xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {file_path}", xbmc.LOGINFO)
                return DELETE_SUCCESS, ""
            else:
                xbmc.log(f"OptiKlean DEBUG: xbmcvfs.delete returned False for {file_path}", xbmc.LOGINFO)
                return DELETE_ERROR, "Failed to delete (unknown error)"
        except OSError as e:
            # Controlla i codici di errore comuni per file bloccati
            if e.errno in (errno.EACCES, errno.EPERM, errno.EBUSY, errno.EAGAIN):
                xbmc.log(f"OptiKlean DEBUG: File locked (attempt {attempt+1}): {file_path} - {e}", xbmc.LOGINFO)
                if attempt < retry_count:
                    time.sleep(retry_delay)
                    continue
                return DELETE_LOCKED, f"File locked: {e}"
            else:
                xbmc.log(f"OptiKlean DEBUG: OS error deleting file: {file_path} - {e}", xbmc.LOGINFO)
                return DELETE_ERROR, f"Error: {e}"
        except Exception as e:
            xbmc.log(f"OptiKlean DEBUG: Unexpected error deleting file: {file_path} - {e}", xbmc.LOGINFO)
            return DELETE_ERROR, f"Unexpected error: {e}"
    
    xbmc.log(f"OptiKlean DEBUG: File appears to be locked after all retry attempts: {file_path}", xbmc.LOGINFO)
    return DELETE_LOCKED, "File appears to be locked by another process"


# Funzione per verificare se è sicuro eliminare un file
def is_safe_to_delete(file_path, temp_path=None, addon_id=None, critical_cache_addons=None):
    """
    Check if a file can be safely deleted
    :param file_path: Full path to the file
    :param temp_path: Path to temp folder (optional)
    :param addon_id: Addon ID (optional)
    :param critical_cache_addons: List of protected addons (optional)
    :return: True if safe to delete, False if protected
    """
    # Files always protected in temp folder
    temp_protected_files = [
        'kodi.log',
        'kodi.old.log',
        'commoncache.db',
        'commoncache.socket'
    ]
    
    # Check if in temp folder
    is_temp_file = temp_path and temp_path in file_path
    
    # 1. Protect specific files in temp folder
    if is_temp_file:
        filename = file_path.split('/')[-1]
        if filename in temp_protected_files:
            return False
        # Skip all other checks for temp folder
        return True
    
    # 2. Protect critical addon caches (only outside temp folder)
    if (
        critical_cache_addons
        and addon_id
        and addon_id in critical_cache_addons
        and (
            "cache" in file_path.lower()
            or "temp" in file_path.lower()
        )
    ):

        return False
    
    # 3. Protect specific extensions (only outside temp folder)
    protected_extensions = ['.db', '.xml', '.json', '.ini', '.cfg']
    if any(file_path.lower().endswith(ext) for ext in protected_extensions):
        return False
        
    return True


# Funzione per verificare se una cartella deve essere esclusa dalla pulizia
def is_excluded_folder(folder_path, temp_path=None):
    """Verifica se una cartella deve essere esclusa dalla pulizia"""
    # Lista di cartelle da escludere - inizialmente vuota
    excluded_folders = []
    
    # Estrai il nome della cartella dal percorso
    folder_name = folder_path.rstrip('/').split('/')[-1]
    
    # Controllo se è una cartella esclusa
    if folder_name in excluded_folders:
        return True
    
    return False


# Funzione per verificare se il percorso è una cache critica da preservare
def is_critical_cache(addon_id, folder_path, critical_cache_addons):
    """Verifica se il percorso è una cache critica da preservare"""
    if addon_id in critical_cache_addons:
        # Per inputstreamhelper, potremmo voler preservare cartelle specifiche
        if addon_id == "script.module.inputstreamhelper":
            # Ad esempio, preservare il contenuto delle sottocartelle "storage" o "download"
            if "storage" in folder_path or "download" in folder_path:
                return True
        # Per default, preserviamo tutte le cache degli addon critici
        return True
    return False


# Funzione per eliminare ricorsivamente file e cartelle in modo sicuro
def delete_directory_recursive(directory_path, progress_dialog=None, parent_results=None):
    """
    Elimina ricorsivamente una cartella e tutti i suoi contenuti.
    - Restituisce True se la cartella è stata eliminata o non esisteva
    - Restituisce False se c'è stato un problema nell'eliminazione
    """

    # Ensure consistent path format
    directory_path = ensure_path_format(directory_path)
    xbmc.log(f"OptiKlean DEBUG: Entering delete_directory_recursive for {directory_path}", xbmc.LOGINFO)   
 
    # Se la cartella non esiste, consideriamo che l'operazione sia riuscita
    if not xbmcvfs.exists(directory_path):
        xbmc.log(f"OptiKlean DEBUG: Directory doesn't exist: {directory_path}", xbmc.LOGINFO)
        return True

    # Inizializza i risultati se non sono stati forniti dal chiamante
    if parent_results is None:
        parent_results = {
            "deleted": [],
            "locked": [],
            "errors": [],
            "protected": []
        }
    
    try:
        # Ottiene liste di file e cartelle
        xbmc.log(f"OptiKlean DEBUG: Attempting to list contents of {directory_path}", xbmc.LOGINFO)
        dirs, files = xbmcvfs.listdir(directory_path)
        xbmc.log(f"OptiKlean DEBUG: Files found in {directory_path}: {files}", xbmc.LOGINFO)
        xbmc.log(f"OptiKlean DEBUG: Subdirectories found in {directory_path}: {dirs}", xbmc.LOGINFO)
        
        # Prima elimina tutti i file
        for file in files:
            file_path = xbmcvfs.makeLegalFilename(ensure_path_format(directory_path) + file)
            xbmc.log(f"OptiKlean DEBUG: Attempting to delete file: {file_path}", xbmc.LOGINFO)
            
            # Aggiorna progresso se fornito
            if progress_dialog:
                # Fix: use getPercentage() with fallback
                try:
                    percent = progress_dialog.getPercentage()
                except AttributeError:
                    percent = 0
                progress_dialog.update(percent, f"Deleting file: {file}")
            
            # Elimina il file
            status, error = delete_file(file_path, progress_dialog=progress_dialog)
            if status == DELETE_SUCCESS:
                parent_results["deleted"].append(file_path)
                xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {file_path}", xbmc.LOGINFO)
            elif status == DELETE_LOCKED:
                parent_results["locked"].append(f"{file_path} (locked)")
                xbmc.log(f"OptiKlean DEBUG: File is locked: {file_path}", xbmc.LOGINFO)
                return False  # Non possiamo eliminare la cartella se un file è bloccato
            else:
                parent_results["errors"].append(f"{file_path} ({error})")
                xbmc.log(f"OptiKlean DEBUG: Error deleting file: {file_path} - {error}", xbmc.LOGINFO)
                return False  # Non possiamo eliminare la cartella se c'è un errore
        
        # Poi elimina ricorsivamente tutte le sottocartelle
        for folder in dirs:
            folder_path = xbmcvfs.makeLegalFilename(ensure_path_format(directory_path) + folder)
            xbmc.log(f"OptiKlean DEBUG: Processing subfolder: {folder_path}", xbmc.LOGINFO)
            
            # Aggiorna progresso se fornito
            if progress_dialog:
                # Fix: use getPercentage() with fallback
                try:
                    percent = progress_dialog.getPercentage()
                except AttributeError:
                    percent = 0
                progress_dialog.update(percent, f"Processing folder: {folder}")
            
            # Chiamata ricorsiva per eliminare la sottocartella
            subfolder_result = delete_directory_recursive(folder_path, progress_dialog, parent_results)
            xbmc.log(f"OptiKlean DEBUG: Subfolder processing result: {subfolder_result} for {folder_path}", xbmc.LOGINFO)
            if not subfolder_result:
                xbmc.log(f"OptiKlean DEBUG: Failed to process subfolder: {folder_path}", xbmc.LOGINFO)
                return False  # Non possiamo eliminare la cartella principale se una sottocartella non può essere eliminata
        
        # Infine, elimina la cartella stessa
        xbmc.log(f"OptiKlean DEBUG: Attempting to remove directory: {directory_path}", xbmc.LOGINFO)
        if xbmcvfs.rmdir(directory_path):
            parent_results["deleted"].append(f"Deleted folder: {directory_path}")
            xbmc.log(f"OptiKlean DEBUG: Successfully removed directory: {directory_path}", xbmc.LOGINFO)
            return True
        else:
            parent_results["errors"].append(f"Failed to delete folder: {directory_path}")
            xbmc.log(f"OptiKlean DEBUG: Failed to remove directory: {directory_path}", xbmc.LOGINFO)
            return False
    
    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Exception in delete_directory_recursive: {str(e)}", xbmc.LOGERROR)
        parent_results["errors"].append(f"Error processing folder {directory_path}: {str(e)}")
        return False


# Funzione per eliminare file e cartelle in modo sicuro con report dei risultati
def delete_files_in_folder(
    folder, 
    progress_dialog=None, 
    safe_check=True,
    addon_id=None, 
    temp_path=None, 
    critical_cache_addons=None,
):
    """
    Elimina file e cartelle in modo sicuro con report dei risultati
    """
    # Ensure consistent path format
    folder = ensure_path_format(folder)
    xbmc.log(f"OptiKlean DEBUG: Starting delete_files_in_folder for {folder}", xbmc.LOGINFO)
    
    results = {
        "deleted": [],
        "locked": [],
        "errors": [],
        "protected": []
    }

    if not xbmcvfs.exists(folder):
        xbmc.log(f"OptiKlean DEBUG: Folder does not exist: {folder}", xbmc.LOGINFO)
        results["errors"].append(f"Folder does not exist: {folder}")
        return results

    try:
        # Ottiene liste separate di cartelle e file
        xbmc.log(f"OptiKlean DEBUG: Attempting to list contents of {folder}", xbmc.LOGINFO)
        dirs, files = xbmcvfs.listdir(folder)
        xbmc.log(f"OptiKlean DEBUG: Directories found in {folder}: {dirs}", xbmc.LOGINFO)
        xbmc.log(f"OptiKlean DEBUG: Files found in {folder}: {files}", xbmc.LOGINFO)
        total_items = len(dirs) + len(files)
        
        # Processa prima i file
        for index, item in enumerate(files):
            if progress_dialog and progress_dialog.iscanceled():
                xbmc.log("OptiKlean DEBUG: Operation canceled by user", xbmc.LOGINFO)
                break

            item_path = xbmcvfs.makeLegalFilename(ensure_path_format(folder) + item)
            xbmc.log(f"OptiKlean DEBUG: Processing file: {item_path}", xbmc.LOGINFO)
            
            # Aggiorna progresso
            if progress_dialog:
                percent = int((index / total_items) * 100) if total_items > 0 else 0
                progress_dialog.update(percent, f"Processing file: {item}")

            if safe_check and not is_safe_to_delete(item_path, temp_path):
                xbmc.log(f"OptiKlean DEBUG: File protected (not safe to delete): {item_path}", xbmc.LOGINFO)
                results["protected"].append(item_path)
                continue

            success, error = delete_file(item_path)
            if success == DELETE_SUCCESS:
                xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {item_path}", xbmc.LOGINFO)
                results["deleted"].append(item_path)
            elif success == DELETE_LOCKED:
                xbmc.log(f"OptiKlean DEBUG: File is locked: {item_path}", xbmc.LOGINFO)
                results["locked"].append(f"{item_path} (locked)")
            else:
                xbmc.log(f"OptiKlean DEBUG: Error deleting file: {item_path} - {error}", xbmc.LOGINFO)
                results["errors"].append(f"{item_path} ({error})")

        # Poi processa le cartelle
        for index, item in enumerate(dirs, start=len(files)):
            if progress_dialog and progress_dialog.iscanceled():
                xbmc.log("OptiKlean DEBUG: Operation canceled by user", xbmc.LOGINFO)
                break

            item_path = xbmcvfs.makeLegalFilename(ensure_path_format(folder) + item)
            xbmc.log(f"OptiKlean DEBUG: Processing folder: {item_path}", xbmc.LOGINFO)
            
            # Aggiorna progresso
            if progress_dialog:
                percent = int((index / total_items) * 100) if total_items > 0 else 0
                progress_dialog.update(percent, f"Processing folder: {item}")
            
            # Controlla se è una cartella esclusa
            if is_excluded_folder(item_path, temp_path):
                xbmc.log(f"OptiKlean DEBUG: Folder excluded from processing: {item_path}", xbmc.LOGINFO)
                results["protected"].append(f"Excluded folder (protected): {item_path}")
                continue
            
            # Controllo se è una cache critica prima di procedere
            if critical_cache_addons and addon_id and is_critical_cache(addon_id, item_path, critical_cache_addons):
                xbmc.log(f"OptiKlean DEBUG: Folder is a critical cache (protected): {item_path}", xbmc.LOGINFO)
                results["protected"].append(f"Protected cache (critical addon): {item_path}")
                continue

            xbmc.log(f"OptiKlean DEBUG: About to process directory recursively: {item_path}", xbmc.LOGINFO)

            # Elimina ricorsivamente la cartella
            folder_deleted = delete_directory_recursive(item_path, progress_dialog, results)
            xbmc.log(f"OptiKlean DEBUG: Result of recursive deletion: {folder_deleted} for {item_path}", xbmc.LOGINFO)

    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Exception in delete_files_in_folder: {str(e)}", xbmc.LOGERROR)
        results["errors"].append(f"Error listing {folder}: {str(e)}")

    xbmc.log(f"OptiKlean DEBUG: Completed delete_files_in_folder for {folder}. Results: deleted={len(results['deleted'])}, locked={len(results['locked'])}, errors={len(results['errors'])}, protected={len(results['protected'])}", xbmc.LOGINFO)
    return results


def map_directory_structure(folder_path):
    """
    Recursively maps the directory structure using xbmcvfs.listdir() with try/except
    Returns a dictionary representing the folder structure or None if path is invalid
    """
    folder_path = ensure_path_format(folder_path)
    structure = {
        'path': folder_path,
        'files': [],
        'subfolders': [],
        'accessible': False
    }
    
    try:
        dirs, files = xbmcvfs.listdir(folder_path)
        structure['accessible'] = True
        structure['files'] = files
        
        xbmc.log(f"OptiKlean DEBUG: Mapped {folder_path} - files: {files}", xbmc.LOGINFO)
        
        for dir_name in dirs:
            # Fix: properly join paths without duplicate base paths
            subfolder_path = ensure_path_format(os.path.join(folder_path, dir_name))
            xbmc.log(f"OptiKlean DEBUG: Processing subfolder: {subfolder_path}", xbmc.LOGINFO)
            subfolder_structure = map_directory_structure(subfolder_path)
            if subfolder_structure:
                structure['subfolders'].append(subfolder_structure)
                xbmc.log(f"OptiKlean DEBUG: Added subfolder {subfolder_path} with {len(subfolder_structure['files'])} files and {len(subfolder_structure['subfolders'])} subfolders", xbmc.LOGINFO)
                
    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Error mapping directory {folder_path}: {str(e)}", xbmc.LOGERROR)
        structure['accessible'] = False
        
    return structure if structure['accessible'] else None


def clear_kodi_temp_folder(temp_path, progress_dialog=None, critical_cache_addons=None, safe_check=True):
    """
    Clears the Kodi temp folder while preserving log files and critical caches
    Returns dictionary with results (deleted, locked, errors, protected)
    """
    results = {
        "deleted": [],
        "locked": [],
        "errors": [],
        "protected": [],
        "total_size": 0
    }

    # Folders that are created by Kodi itself everytime so don't need to be deleted
    protected_folders = ["temp", "archive_cache"]  # These are in special://temp/
    
    temp_path = ensure_path_format(temp_path)
    xbmc.log(f"OptiKlean DEBUG: Starting clear_kodi_temp_folder for {temp_path} with safe_check={safe_check}", xbmc.LOGINFO)
    
    try:
        # First map the entire directory structure
        progress_dialog and progress_dialog.update(0, "Mapping temp folder structure...")
        folder_structure = map_directory_structure(temp_path)
        
        if not folder_structure:
            results["errors"].append(f"Could not access temp folder: {temp_path}")
            xbmc.log("OptiKlean DEBUG: Could not map temp folder structure", xbmc.LOGERROR)
            return results
        
        xbmc.log(f"OptiKlean DEBUG: Completed mapping temp folder structure. Root files: {len(folder_structure['files'])}, Subfolders: {len(folder_structure['subfolders'])}", xbmc.LOGINFO)
        
        # Process all files in the root first - ALWAYS protect log files regardless of safe_check
        for file_name in folder_structure['files']:
            if progress_dialog and progress_dialog.iscanceled():
                break
                
            file_path = os.path.join(temp_path, file_name)
            xbmc.log(f"OptiKlean DEBUG: Processing root file: {file_path}", xbmc.LOGINFO)
            
            # First check if this is a protected file (like kodi.log)
            if not is_safe_to_delete(file_path, temp_path):
                xbmc.log(f"OptiKlean DEBUG: Protected file skipped: {file_path}", xbmc.LOGINFO)
                results["protected"].append(file_path)
                continue
            
            # Get file size BEFORE deletion
            file_size = get_file_size(file_path) or 0
                
            status, error = delete_file(file_path, progress_dialog=progress_dialog)
            if status == DELETE_SUCCESS:
                results["deleted"].append((file_path, file_size))  # Store as tuple with size
                results["total_size"] += file_size
                xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {file_path} (size: {file_size} bytes)", xbmc.LOGINFO)
            elif status == DELETE_LOCKED:
                results["locked"].append(file_path)
            else:
                results["errors"].append(f"{file_path} ({error})")
    
        # Then process all subfolders recursively
        def process_folder(folder, parent_results):
            full_path = folder['path']
            xbmc.log(f"OptiKlean DEBUG: Processing folder: {full_path}", xbmc.LOGINFO)
            
            # Skip excluded folders
            if is_excluded_folder(full_path, temp_path):
                xbmc.log(f"OptiKlean DEBUG: Excluded folder skipped: {full_path}", xbmc.LOGINFO)
                parent_results["protected"].append(f"Excluded folder: {full_path}")
                return True
                
            # Get folder name and relative path
            folder_name = full_path.rstrip('/').split('/')[-1]
                  
            if (folder_name in protected_folders):
                xbmc.log(f"OptiKlean DEBUG: Protected folder in temp - processing contents only: {full_path}", xbmc.LOGINFO)
                
                # Process files in this folder
                for file_name in folder['files']:
                    if progress_dialog and progress_dialog.iscanceled():
                        return False
                        
                    file_path = os.path.join(full_path, file_name)
                    xbmc.log(f"OptiKlean DEBUG: Processing file: {file_path}", xbmc.LOGINFO)
                    
                    if safe_check and not is_safe_to_delete(file_path, temp_path):
                        xbmc.log(f"OptiKlean DEBUG: Protected file skipped: {file_path}", xbmc.LOGINFO)
                        parent_results["protected"].append(file_path)
                        continue
                    
                    # Get file size BEFORE deletion
                    file_size = get_file_size(file_path) or 0
                        
                    status, error = delete_file(file_path, progress_dialog=progress_dialog)
                    if status == DELETE_SUCCESS:
                        parent_results["deleted"].append((file_path, file_size))  # Store as tuple
                        parent_results["total_size"] += file_size
                        xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {file_path} (size: {file_size} bytes)", xbmc.LOGINFO)
                    elif status == DELETE_LOCKED:
                        parent_results["locked"].append(file_path)
                    else:
                        parent_results["errors"].append(f"{file_path} ({error})")
                
                # Process all subfolders recursively
                for subfolder in folder['subfolders']:
                    process_folder(subfolder, parent_results)
                
                return True            

            # Process files in this folder (for non-protected folders)
            for file_name in folder['files']:
                if progress_dialog and progress_dialog.iscanceled():
                    return False
                    
                file_path = os.path.join(full_path, file_name)
                xbmc.log(f"OptiKlean DEBUG: Processing file: {file_path}", xbmc.LOGINFO)
                
                # Only check protected files if safe_check is True (for non-root files)
                if safe_check and not is_safe_to_delete(file_path, temp_path):
                    xbmc.log(f"OptiKlean DEBUG: Protected file skipped: {file_path}", xbmc.LOGINFO)
                    parent_results["protected"].append(file_path)
                    continue

                # Get file size BEFORE deletion
                file_size = get_file_size(file_path) or 0
                
                status, error = delete_file(file_path, progress_dialog=progress_dialog)

                if status == DELETE_SUCCESS:
                    parent_results["deleted"].append((file_path, file_size))  # Store as tuple
                    parent_results["total_size"] += file_size
                    xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {file_path} (size: {file_size} bytes)", xbmc.LOGINFO)
                elif status == DELETE_LOCKED:
                    parent_results["locked"].append(file_path)
                else:
                    parent_results["errors"].append(f"{file_path} ({error})")
            
            # Process all subfolders recursively
            for subfolder in folder['subfolders']:
                process_folder(subfolder, parent_results)
                
            # Try to delete the folder itself if empty
            try:
                dirs, files = xbmcvfs.listdir(full_path)
                if not dirs and not files:
                    if xbmcvfs.rmdir(full_path):
                        parent_results["deleted"].append((f"Deleted folder: {full_path}", 0))  # Store as tuple with size 0
                        xbmc.log(f"OptiKlean DEBUG: Successfully deleted folder: {full_path}", xbmc.LOGINFO)
                    else:
                        parent_results["errors"].append(f"Failed to delete folder: {full_path}")
                        xbmc.log(f"OptiKlean DEBUG: Failed to delete folder: {full_path} (may not be empty)", xbmc.LOGINFO)
                else:
                    remaining = len(dirs) + len(files)
                    parent_results["errors"].append(f"Folder not empty: {full_path} ({remaining} items remaining)")
                    xbmc.log(f"OptiKlean DEBUG: Folder not empty, contains {remaining} items: {full_path}", xbmc.LOGINFO)
            except Exception as e:
                parent_results["errors"].append(f"Error deleting folder {full_path}: {str(e)}")
                xbmc.log(f"OptiKlean DEBUG: Exception deleting folder {full_path}: {str(e)}", xbmc.LOGERROR)
                
            return True
        
        # Process all top-level folders (this will recursively process their contents)
        for folder in folder_structure['subfolders']:
            if progress_dialog and progress_dialog.iscanceled():
                break
            process_folder(folder, results)
        
    except Exception as e:
        results["errors"].append(f"General error in clear_kodi_temp_folder: {str(e)}")
        xbmc.log(f"OptiKlean DEBUG: General error in clear_kodi_temp_folder: {str(e)}", xbmc.LOGERROR)
    
    xbmc.log(f"OptiKlean DEBUG: Completed clear_kodi_temp_folder. Results: deleted={len(results['deleted'])}, locked={len(results['locked'])}, errors={len(results['errors'])}, protected={len(results['protected'])}", xbmc.LOGINFO)
    return results


def clear_cache_and_temp(auto_mode=False):

    # Inizializza il totale cumulativo
    total_freed_all_options = 0

    # Opzioni:
    # 0: Clear Kodi temp folder (preserving log files)
    # 1: Clear cache files from addon data
    # 2: Clear temp folders from addon data
    # 3: Clear temp folder from addons
    choices = [
        "Clear Kodi temp folder (preserving logs)",
        "Clear cache files from addon data",
        "Clear temp folders from addon data",
        "Clear temp folder from addons"
    ]
    
    temp_path = ensure_path_format(xbmcvfs.translatePath("special://temp/"))
    addon_data_path = ensure_path_format(xbmcvfs.translatePath("special://profile/addon_data/"))

    if not auto_mode:
        selected = xbmcgui.Dialog().multiselect("Select cache/temp to clear", choices)
        if selected is None:
            return
    else:
        selected = [0, 1, 2, 3]
  
    # Lista di addon con cache essenziali da non cancellare
    critical_cache_addons = [
        "script.module.inputstreamhelper",
        "inputstream.adaptive",
        "inputstream.rtmp",
        "script.module.resolveurl",
        "plugin.video.youtube",
        'plugin.video.netflix',
        'plugin.video.amazon',
        'plugin.video.disneyplus',
        'script.common.plugin.cache',
        'pvr.iptvsimple'
    ]
    
    progress = xbmcgui.DialogProgress()
    progress.create("OptiKlean", "Preparing to clear cache...")
    
    try:
        # Opzione 0: Clear Kodi temp folder (preserving logs)
        if selected and 0 in selected:
            start_time = time.perf_counter()
            progress.update(0, "Clearing Kodi temp folder (preserving log files)...")
            
            # Log che stiamo iniziando l'operazione
            xbmc.log("OptiKlean: Starting to clear Kodi temp folder", xbmc.LOGINFO)
            xbmc.log(f"OptiKlean: Using temp path: {temp_path}", xbmc.LOGINFO)
            
            # Use safe_check=False to delete all files except protected ones
            results = clear_kodi_temp_folder(temp_path, progress, 
                                          critical_cache_addons=critical_cache_addons,
                                          safe_check=True)
                                          
            total_freed_all_options += results.get("total_size", 0)
            
            # Verifica effettiva prima di segnare come completato
            if results and (results.get("deleted") or results.get("total_size", 0) > 0):
                xbmc.log(f"OptiKlean: Temp folder cleanup successful, deleted {len(results.get('deleted', []))} items", xbmc.LOGINFO)
            else:
                xbmc.log("OptiKlean: Temp folder cleanup didn't delete any files", xbmc.LOGINFO)

            log_content = "Kodi temp folder cleaning results:\n\n"
            
            if results["deleted"]:
                # Separate files and folders, calculate precise total
                deleted_files = []
                deleted_folders = []
                total_bytes = 0
                
                for item in results["deleted"]:
                    if isinstance(item, tuple):
                        file_path, file_size = item
                        if "Deleted folder:" in file_path:  # It's a folder entry
                            _, full_path = file_path.split(":", 1)
                            folder_name = os.path.basename(full_path.strip().rstrip("/"))
                            deleted_folders.append(folder_name)
                        elif file_size > 0:  # It's a file with size
                            deleted_files.append((os.path.basename(file_path), file_size))
                            total_bytes += file_size
                
                # Precise size conversion (bytes → MB)
                total_mb = total_bytes / (1024 * 1024)
                
                # Build log output
                if deleted_files:
                    log_content += f"Files deleted: {len(deleted_files)} ({total_mb:.3f} MB freed)\n"
                    for filename, size in deleted_files:
                        if size >= 1048576:  # ≥1MB
                            log_content += f"  - {filename} ({size/1048576:.3f} MB)\n"
                        elif size >= 1024:  # ≥1KB
                            log_content += f"  - {filename} ({size/1024:.3f} KB)\n"
                        else:
                            log_content += f"  - {filename} ({size} B)\n"
                
                if deleted_folders:
                    log_content += f"\nFolders deleted: {len(deleted_folders)}\n"
                    for folder in deleted_folders:
                        log_content += f"  - {folder}\n"
                
                log_content += "\n"
            
            if results["locked"]:
                log_content += "Files in use (locked):\n"
                log_content += "  " + "\n  ".join([os.path.basename(f) for f in results["locked"]]) + "\n\n"
            
            if results["errors"]:
                log_content += "Errors:\n"
                log_content += "  " + "\n  ".join(results["errors"]) + "\n\n"
            
            if results["protected"]:
                log_content += "Protected items (not deleted):\n"
                protected_items = [os.path.basename(f) for f in results["protected"][:20]]
                log_content += "  " + "\n  ".join(protected_items)
                if len(results["protected"]) > 20:
                    log_content += f"\n  ... and {len(results['protected']) - 20} more items"
                log_content += "\n\n"

            # Log completion
            xbmc.log(f"OptiKlean: Completed clearing Kodi temp folder. Deleted: {len(results['deleted'])}, Protected: {len(results['protected'])}, Errors: {len(results['errors'])}", xbmc.LOGINFO)
            execution_time = round(time.perf_counter() - start_time, 2)
            log_content += f"Running time: {execution_time}s\n"
            write_log("clear_kodi_temp_folder", log_content.rstrip() + "\n")

        # Opzione 1: Clear cache files from addon data
        if selected and 1 in selected and not progress.iscanceled():
            start_time = time.perf_counter()
            progress.update(0, "Scanning addon data...")
            
            log_content = "Addon cache folders cleaning results:\n\n"
            xbmc.log("OptiKlean: Starting addon cache cleaning", xbmc.LOGINFO)
            total_size_freed = 0
            option1_size_freed = 0

            if not xbmcvfs.exists(addon_data_path):
                error_msg = f"Addon data path does not exist: {addon_data_path}"
                xbmc.log(f"OptiKlean: {error_msg}", xbmc.LOGERROR)
                log_content += error_msg + "\n"
            else:
                try:
                    addon_folders, _ = xbmcvfs.listdir(addon_data_path)
                    xbmc.log(f"OptiKlean: Found {len(addon_folders)} addon folders", xbmc.LOGINFO)
                    
                    if not addon_folders:
                        log_content += "No addon folders found\n"
                    else:
                        total_addons = len(addon_folders)
                        has_skips = False

                        for index, addon_id in enumerate(addon_folders):
                            if progress.iscanceled():
                                break
                            
                            progress.update((index * 100) // total_addons, f"Checking {addon_id}...")
                            
                            # Skip critical addons
                            if addon_id in critical_cache_addons:
                                if not has_skips:
                                    log_content += "\n"
                                    has_skips = True
                                log_content += f"[SKIPPED] Critical addon: {addon_id}\n"
                                continue
                            
                            cache_path = xbmcvfs.makeLegalFilename(f"{addon_data_path}/{addon_id}/cache/")
                            
                            if xbmcvfs.exists(cache_path):
                                try:
                                    _, files = xbmcvfs.listdir(cache_path)
                                    addon_deleted = []
                                    addon_size_freed = 0
                                    addon_errors = []
                                    addon_protected = []

                                    for file_name in files:
                                        if progress.iscanceled():
                                            break
                                            
                                        file_path = xbmcvfs.makeLegalFilename(f"{cache_path}/{file_name}")
                                        
                                        # Get file size before deletion
                                        file_size = get_file_size(file_path) or 0
                                        
                                        xbmc.log(f"OptiKlean DEBUG: File {file_path} size: {file_size} bytes", xbmc.LOGDEBUG)
                                        
                                        if is_safe_to_delete(file_path, addon_id=addon_id, 
                                                          critical_cache_addons=critical_cache_addons):
                                            status, error = delete_file(file_path)
                                            
                                            if status == DELETE_SUCCESS:
                                                addon_deleted.append((file_name, file_size))
                                                addon_size_freed += file_size
                                                total_size_freed += file_size
                                                option1_size_freed += file_size
                                                
                                                xbmc.log(f"OptiKlean DEBUG: Successfully deleted {file_path}, added {file_size} bytes to total", xbmc.LOGDEBUG)
                                            elif status == DELETE_LOCKED:
                                                addon_errors.append(f"Locked: {file_name}")
                                            else:
                                                addon_errors.append(f"Error: {file_name} ({error})")
                                        else:
                                            addon_protected.append(file_name)
                                    
                                    # Add results to log
                                    if addon_deleted or addon_errors or addon_protected:
                                        log_content += f"{addon_id} (cache):\n"
                                        
                                        if addon_deleted:
                                            size_kb = addon_size_freed / 1024
                                            log_content += f"  Deleted {len(addon_deleted)} files ({size_kb:.2f} KB freed):\n"
                                            for file_name, file_size in addon_deleted:
                                                size_str = f"{file_size/1024:.2f}KB" if file_size >= 1024 else f"{file_size}B"
                                                log_content += f"    - {file_name} ({size_str})\n"
                                        
                                        if addon_protected:
                                            log_content += f"  Protected files ({len(addon_protected)}):\n"
                                            for file_name in addon_protected:
                                                log_content += f"    - {file_name}\n"
                                        
                                        if addon_errors:
                                            log_content += f"  Errors ({len(addon_errors)}):\n"
                                            for error in addon_errors:
                                                log_content += f"    - {error}\n"
                                        
                                        log_content += "\n"
                                
                                except Exception as e:
                                    log_content += f"{addon_id} ERROR: {str(e)}\n"
                    
                except Exception as e:
                    log_content += f"Error listing addon_data: {str(e)}\n"

            xbmc.log(f"OptiKlean DEBUG: Total size freed in option 1: {total_size_freed} bytes ({total_size_freed/1024/1024:.2f} MB)", xbmc.LOGINFO)

            # Add total at the end (after all addon entries)
            if total_size_freed > 0:
                total_mb = total_size_freed / (1024 * 1024)
                log_content += f"Total space freed: {total_mb:.2f} MB\n\n"

                total_freed_all_options += option1_size_freed

            execution_time = round(time.perf_counter() - start_time, 2)
            log_content += f"Running time: {execution_time}s\n"
            write_log("clear_cache_files_from_addon_data", log_content.rstrip() + "\n")
            
        # Opzione 2: Clear temp folders from addon data
        if selected and 2 in selected and not progress.iscanceled():
            start_time = time.perf_counter()
            progress.update(0, "Preparing to clear addon data temp folders...")
            total_size_freed = 0
            option2_size_freed = 0
            
            log_content = "Addon temp folders cleaning results:\n\n"
            xbmc.log("OptiKlean: Starting addon temp folders cleaning", xbmc.LOGINFO)
            xbmc.log(f"OptiKlean: Using addon_data path: {addon_data_path}", xbmc.LOGINFO)
            
            if not xbmcvfs.exists(addon_data_path):
                error_msg = f"Addon data path does not exist: {addon_data_path}"
                xbmc.log(f"OptiKlean: {error_msg}", xbmc.LOGERROR)
                log_content += error_msg + "\n"
            else:
                try:
                    addon_folders, _ = xbmcvfs.listdir(addon_data_path)
                    xbmc.log(f"OptiKlean: Found {len(addon_folders)} addon folders", xbmc.LOGINFO)
                    
                    if not addon_folders:
                        log_content += "No addon folders found\n"
                        xbmc.log("OptiKlean: No addon folders found", xbmc.LOGINFO)
                    else:
                        total_addons = len(addon_folders)
                        has_skips = False
                        last_was_skip = False
                        total_size_freed = 0
                        
                        for index, addon_id in enumerate(addon_folders):
                            if progress.iscanceled():
                                break
                            
                            progress.update((index * 100) // total_addons, f"Checking {addon_id}...")
                            xbmc.log(f"OptiKlean: Processing addon {addon_id}", xbmc.LOGINFO)
                            
                            if addon_id in critical_cache_addons:
                                skip_msg = f"[SKIPPED] Critical addon: {addon_id}"
                                if not has_skips:
                                    log_content = log_content.rstrip() + "\n\n"
                                    has_skips = True
                                log_content += skip_msg + "\n"
                                last_was_skip = True
                                xbmc.log(f"OptiKlean: {skip_msg}", xbmc.LOGINFO)
                                continue
                            
                            last_was_skip = False
                            
                            for temp_folder in ['temp', 'tmp']:
                                temp_path = xbmcvfs.makeLegalFilename(f"{addon_data_path}/{addon_id}/{temp_folder}/")
                                xbmc.log(f"OptiKlean: Checking for {temp_folder} at {temp_path}", xbmc.LOGINFO)
                                
                                if xbmcvfs.exists(temp_path):
                                    try:
                                        _, files = xbmcvfs.listdir(temp_path)
                                        xbmc.log(f"OptiKlean: Found {len(files)} files in {temp_folder}", xbmc.LOGINFO)
                                        
                                        deleted = []
                                        protected = []
                                        errors = []
                                        addon_size_freed = 0
                                        
                                        for file_name in files:
                                            if progress.iscanceled():
                                                break
                                                
                                            file_path = xbmcvfs.makeLegalFilename(f"{temp_path}/{file_name}")
                                            xbmc.log(f"OptiKlean: Processing file {file_path}", xbmc.LOGINFO)
                                            
                                            file_size = get_file_size(file_path) or 0
                                            
                                            if is_safe_to_delete(file_path, addon_id=addon_id, 
                                                              critical_cache_addons=critical_cache_addons):
                                                status, error = delete_file(file_path)
                                                if status == DELETE_SUCCESS:
                                                    if xbmcvfs.exists(file_path):
                                                        error_msg = f"File still exists after deletion: {file_path}"
                                                        xbmc.log(f"OptiKlean: {error_msg}", xbmc.LOGWARNING)
                                                        errors.append(f"Verify failed: {file_name}")
                                                    else:
                                                        xbmc.log(f"OptiKlean: Successfully deleted {file_path} ({file_size} bytes)", xbmc.LOGINFO)
                                                        deleted.append((file_name, file_size))
                                                        addon_size_freed += file_size
                                                        total_size_freed += file_size
                                                        option2_size_freed += file_size
                                                elif status == DELETE_LOCKED:
                                                    error_msg = f"Failed to delete {file_path} (locked)"
                                                    xbmc.log(f"OptiKlean: {error_msg}", xbmc.LOGWARNING)
                                                    errors.append(f"Locked: {file_name}")
                                                else:
                                                    error_msg = f"Failed to delete {file_path} ({error})"
                                                    xbmc.log(f"OptiKlean: {error_msg}", xbmc.LOGERROR)
                                                    errors.append(f"Error: {file_name} ({error})")
                                            else:
                                                xbmc.log(f"OptiKlean: Protected file {file_path}", xbmc.LOGINFO)
                                                protected.append(file_name)
                                        
                                        if has_skips and not last_was_skip and (deleted or protected or errors):
                                            log_content += "\n"
                                        
                                        if deleted or protected or errors:
                                            log_content += f"{addon_id} ({temp_folder}):\n"
                                            
                                            if deleted:
                                                size_kb = addon_size_freed / 1024
                                                log_content += f"  Deleted {len(deleted)} files ({size_kb:.2f} KB freed):\n"
                                                for file_name, file_size in deleted:
                                                    size_str = f"{file_size/1024:.2f}KB" if file_size >= 1024 else f"{file_size}B"
                                                    log_content += f"    - {file_name} ({size_str})\n"
                                            
                                            if protected:
                                                log_content += f"  Protected files ({len(protected)}):\n"
                                                for file_name in protected:
                                                    log_content += f"    - {file_name}\n"
                                            
                                            if errors:
                                                log_content += f"  Errors ({len(errors)}):\n"
                                                for error in errors:
                                                    log_content += f"    - {error}\n"
                                            
                                            log_content += "\n"
                                    
                                    except Exception as e:
                                        error_msg = f"Error processing {addon_id} {temp_folder}: {str(e)}"
                                        log_content += f"{addon_id} {temp_folder} ERROR: {error_msg}\n"
                                        xbmc.log(f"OptiKlean: {error_msg}", xbmc.LOGERROR)
                                else:
                                    xbmc.log(f"OptiKlean: No {temp_folder} folder found for {addon_id}", xbmc.LOGINFO)
                    
                    # Move total space freed to the end of the log
                    if total_size_freed > 0:
                        size_mb = total_size_freed / (1024 * 1024)
                        log_content += f"Total space freed: {size_mb:.2f} MB\n\n"
                        
                        total_freed_all_options += option2_size_freed

                except Exception as e:
                    error_msg = f"Error listing addon_data folder: {str(e)}"
                    log_content += error_msg + "\n"
                    xbmc.log(f"OptiKlean: {error_msg}", xbmc.LOGERROR)

            execution_time = round(time.perf_counter() - start_time, 2)
            log_content += f"Running time: {execution_time}s\n"
            write_log("clear_temp_folders_from_addon_data", log_content.rstrip() + "\n")

        # Opzione 3: Clear temp folder from addons
        if selected and 3 in selected and not progress.iscanceled():
            start_time = time.perf_counter()
            progress.update(0, "Preparing to clear addons temp folder...")
            option3_size_freed = 0
            
            log_content = "Addons temp folder cleaning results:\n\n"
            xbmc.log("OptiKlean DEBUG: Starting clear addons temp folder", xbmc.LOGINFO)
            
            addons_temp_path = ensure_path_format(xbmcvfs.translatePath("special://home/addons/temp/"))
            xbmc.log(f"OptiKlean DEBUG: Using addons temp path: {addons_temp_path}", xbmc.LOGINFO)
            
            if not xbmcvfs.exists(addons_temp_path):
                error_msg = f"Addons temp folder does not exist: {addons_temp_path}"
                xbmc.log(f"OptiKlean DEBUG: {error_msg}", xbmc.LOGERROR)
                log_content += error_msg + "\n"
            else:
                # First map the directory structure
                progress.update(10, "Mapping addons temp folder structure...")
                folder_structure = map_directory_structure(addons_temp_path)
                
                if not folder_structure:
                    error_msg = f"Could not access addons temp folder: {addons_temp_path}"
                    xbmc.log(f"OptiKlean DEBUG: {error_msg}", xbmc.LOGERROR)
                    log_content += error_msg + "\n"
                else:
                    xbmc.log(f"OptiKlean DEBUG: Found {len(folder_structure['files'])} files and {len(folder_structure['subfolders'])} subfolders in addons temp", xbmc.LOGINFO)
                    
                    results = {
                        "deleted": [],
                        "locked": [],
                        "errors": [],
                        "protected": [],
                        "total_size": 0
                    }
                    
                    def process_folder(folder, parent_results):
                        nonlocal option3_size_freed
                        full_path = folder['path']
                        xbmc.log(f"OptiKlean DEBUG: Processing folder: {full_path}", xbmc.LOGINFO)
                        
                        # Process files in this folder
                        for file_name in folder['files']:
                            if progress.iscanceled():
                                return False
                                
                            file_path = os.path.join(full_path, file_name)
                            xbmc.log(f"OptiKlean DEBUG: Processing file: {file_path}", xbmc.LOGINFO)
                            
                            if not is_safe_to_delete(file_path, addons_temp_path):
                                xbmc.log(f"OptiKlean DEBUG: Protected file skipped: {file_path}", xbmc.LOGINFO)
                                parent_results["protected"].append(file_path)
                                continue
                            
                            file_size = get_file_size(file_path) or 0
                            status, error = delete_file(file_path, progress_dialog=progress)

                            if status == DELETE_SUCCESS:
                                parent_results["deleted"].append((file_path, file_size))
                                parent_results["total_size"] += file_size
                                option3_size_freed += file_size
                                xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {file_path} (size: {file_size} bytes)", xbmc.LOGINFO)
                            elif status == DELETE_LOCKED:
                                parent_results["locked"].append(file_path)
                                xbmc.log(f"OptiKlean DEBUG: File is locked: {file_path}", xbmc.LOGINFO)
                            else:
                                parent_results["errors"].append(f"{file_path} ({error})")
                                xbmc.log(f"OptiKlean DEBUG: Error deleting file: {file_path} - {error}", xbmc.LOGERROR)
                        
                        # Process all subfolders recursively
                        for subfolder in folder['subfolders']:
                            process_folder(subfolder, parent_results)
                        
                        return True
                    
                    # Process all top-level folders
                    for folder in folder_structure['subfolders']:
                        if progress.iscanceled():
                            break
                        process_folder(folder, results)
                    
                    # Process files in root folder
                    for file_name in folder_structure['files']:
                        if progress.iscanceled():
                            break
                            
                        file_path = os.path.join(addons_temp_path, file_name)
                        xbmc.log(f"OptiKlean DEBUG: Processing root file: {file_path}", xbmc.LOGINFO)
                        
                        if not is_safe_to_delete(file_path, addons_temp_path):
                            xbmc.log(f"OptiKlean DEBUG: Protected file skipped: {file_path}", xbmc.LOGINFO)
                            results["protected"].append(file_path)
                            continue

                        # Get size BEFORE deletion
                        file_size = get_file_size(file_path) or 0
                        status, error = delete_file(file_path, progress_dialog=progress)
                            
                        if status == DELETE_SUCCESS:
                            results["deleted"].append((file_path, file_size))  # Store as tuple with size
                            results["total_size"] += file_size
                            option3_size_freed += file_size
                            xbmc.log(f"OptiKlean DEBUG: Successfully deleted file: {file_path} (size: {file_size} bytes)", xbmc.LOGINFO)
                        elif status == DELETE_LOCKED:
                            results["locked"].append(file_path)
                            xbmc.log(f"OptiKlean DEBUG: File is locked: {file_path}", xbmc.LOGINFO)
                        else:
                            results["errors"].append(f"{file_path} ({error})")
                            xbmc.log(f"OptiKlean DEBUG: Error deleting file: {file_path} - {error}", xbmc.LOGERROR)
                    
                    # Generate log content
                    if results["deleted"]:
                        size_mb = results["total_size"] / (1024 * 1024)
                        total_freed_all_options += option3_size_freed
                        log_content += f"Successfully deleted ({len(results['deleted'])} items, {size_mb:.2f} MB freed):\n"
                        for item in results["deleted"]:
                            if isinstance(item, tuple):
                                file_path, file_size = item
                                filename = os.path.basename(file_path)
                                size_str = f"{file_size/1024:.2f}KB" if file_size >= 1024 else f"{file_size}B"
                                log_content += f"- {filename} ({size_str})\n"
                            else:
                                # Handle folder deletion messages
                                if "Deleted folder:" in item:
                                    folder_name = item.split(":")[1].strip().split('/')[-1]
                                    log_content += f"- [Folder] {folder_name}\n"
                                else:
                                    log_content += f"- {item}\n"
                        log_content += "\n"

                    if results["locked"]:
                        log_content += f"Locked items ({len(results['locked'])}):\n"
                        for item in results["locked"]:
                            log_content += f"- {os.path.basename(item)}\n"
                        log_content += "\n"

                    if results["errors"]:
                        log_content += f"Errors ({len(results['errors'])}):\n"
                        for error in results["errors"]:
                            # Try to extract filename from error messages
                            if "Error in" in error:
                                path_part = error.split(':')[0].strip()
                                filename = os.path.basename(path_part)
                                log_content += f"- {filename}: {error.split(':', 1)[1].strip()}\n"
                            else:
                                log_content += f"- {error}\n"
                        log_content += "\n"

                    if results["protected"]:
                        log_content += f"Protected items ({len(results['protected'])}):\n"
                        for item in results["protected"]:
                            log_content += f"- {os.path.basename(item)}\n"
                        log_content += "\n"
                    
                    xbmc.log(f"OptiKlean DEBUG: Addons temp cleanup completed. Deleted: {len(results['deleted'])}, Locked: {len(results['locked'])}, Errors: {len(results['errors'])}, Protected: {len(results['protected'])}", xbmc.LOGINFO)
                        
            execution_time = round(time.perf_counter() - start_time, 2)
            log_content += f"\nRunning time: {execution_time}s\n"
            write_log("clear_temp_folder_from_addons", log_content.rstrip() + "\n")
            
        # Show notification if any option was selected and completed
        if selected:
            total_mb = total_freed_all_options / (1024 * 1024)
            notification_msg = f"Clear cache and temp completed! ({total_mb:.2f} MB freed)"
            xbmcgui.Dialog().notification("OptiKlean", notification_msg, xbmcgui.NOTIFICATION_INFO, 3000)

            # Aggiorna i log delle impostazioni automatiche solo se:
            # 1. Non è in modalità automatica
            # 2. Almeno una pulizia è stata completata con successo
            # 3. La pulizia automatica è abilitata nelle impostazioni
            if not auto_mode and addon.getSettingBool("clear_cache_and_temp_enable"):
                try:
                    update_last_run("clear_cache_and_temp")
                    update_automatic_settings_log()
                    xbmc.log("OptiKlean: Updated automatic cleaning logs after manual execution", xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"OptiKlean: Error updating automatic logs: {str(e)}", xbmc.LOGERROR)
        
    except Exception as e:
        error_msg = f"Unexpected error during cleanup: {str(e)}"
        xbmc.log(error_msg, xbmc.LOGERROR)
        xbmcgui.Dialog().notification("OptiKlean", "Error during cleanup, see log", xbmcgui.NOTIFICATION_ERROR, 5000)
                
    finally:
        progress.close()


# Funzione per trovare il database delle texture
def find_texture_database(db_path):
    """
    Trova il database delle texture più recente in modo dinamico, compatibile con tutte le versioni di Kodi.
    """
    xbmc.log(f"OptiKlean DEBUG: Entering find_texture_database with path: {db_path}", xbmc.LOGINFO)
    
    # Ensure proper path format (no double slashes)
    db_path = db_path.replace('//', '/')
    
    if not xbmcvfs.exists(db_path):
        xbmc.log(f"OptiKlean DEBUG: Database path does not exist: {db_path}", xbmc.LOGINFO)
        return None

    # Pattern per identificare i database delle texture
    texture_pattern = "Textures*.db"
    xbmc.log(f"OptiKlean DEBUG: Looking for files matching pattern: {texture_pattern}", xbmc.LOGINFO)

    # Cerca tutti i file nella directory database
    _, files = xbmcvfs.listdir(db_path)
    xbmc.log(f"OptiKlean DEBUG: All files in database directory: {files}", xbmc.LOGINFO)
    
    matching_files = [f for f in files if fnmatch.fnmatch(f, texture_pattern)]
    xbmc.log(f"OptiKlean DEBUG: Matching texture database files: {matching_files}", xbmc.LOGINFO)

    if not matching_files:
        xbmc.log("OptiKlean DEBUG: No texture database files found", xbmc.LOGINFO)
        return None  # Nessun database texture trovato

    # Converti i nomi dei file in numeri e ordina per versione (Textures13.db, Textures14.db, ...)
    def extract_version(filename):
        match = re.search(r"Textures(\d+)\.db", filename)
        version = int(match.group(1)) if match else 0
        xbmc.log(f"OptiKlean DEBUG: Extracted version {version} from file {filename}", xbmc.LOGINFO)
        return version

    matching_files.sort(key=extract_version, reverse=True)
    xbmc.log(f"OptiKlean DEBUG: Sorted texture database files: {matching_files}", xbmc.LOGINFO)

    # Restituisce il database più recente - Fix path to avoid double slashes
    latest_db = matching_files[0]
    full_path = xbmcvfs.translatePath(f"{db_path}{latest_db}")
    full_path = full_path.replace('//', '/')  # Ensure no double slashes
    xbmc.log(f"OptiKlean DEBUG: Selected latest texture database: {full_path}", xbmc.LOGINFO)
    return full_path


# Funzione per cancellare le thumbnails non più utilizzate
def clear_unused_thumbnails(auto_mode=False):
    xbmc.log("OptiKlean DEBUG: Starting clear_unused_thumbnails", xbmc.LOGINFO)
    start_time = time.perf_counter()
    progress = xbmcgui.DialogProgress()
    progress.create("OptiKlean", "Preparing unused thumbnails cleanup...")
    log_content = "Unused thumbnails cleaning results:\n\n"

    db_path = ensure_path_format(xbmcvfs.translatePath("special://database/"))
    standard_thumb_path = ensure_path_format(xbmcvfs.translatePath("special://userdata/Thumbnails/"))
    alt_thumb_path = ensure_path_format(xbmcvfs.translatePath("special://thumbnails/"))

    skin_base = ensure_path_format(xbmcvfs.translatePath("special://skin/"))
    skin_subfolders = ["thumbnails/", "media/Thumbnails/", "extras/Thumbnails/"]
    skin_thumb_paths = [ensure_path_format(os.path.join(skin_base, sub)) for sub in skin_subfolders]

    thumb_paths = [p for p in [standard_thumb_path, alt_thumb_path] if xbmcvfs.exists(p)] + [
        p for p in skin_thumb_paths if xbmcvfs.exists(p)
    ]

    for p in thumb_paths:
        xbmc.log(f"OptiKlean DEBUG: Thumbnail path added: {p}", xbmc.LOGINFO)

    if not thumb_paths:
        xbmc.log("OptiKlean DEBUG: No valid thumbnail paths found", xbmc.LOGERROR)
        progress.update(100, "Thumbnails folder not found.")
        log_content += "Thumbnails folder not found.\n"
        execution_time = round(time.perf_counter() - start_time, 2)
        log_content += f"\nRunning time: {execution_time}s\n"
        write_log("clear_unused_thumbnails", log_content)
        xbmcgui.Dialog().notification("OptiKlean", "Thumbnails folder not found.", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    texture_db = find_texture_database(db_path)
    xbmc.log(f"OptiKlean DEBUG: Texture database path: {texture_db}", xbmc.LOGINFO)

    if not texture_db:
        xbmc.log("OptiKlean DEBUG: Texture database not found.", xbmc.LOGERROR)
        progress.update(100, "Texture database not found.")
        log_content += "Texture database not found.\n"
        execution_time = round(time.perf_counter() - start_time, 2)
        log_content += f"\nRunning time: {execution_time}s\n"
        write_log("clear_unused_thumbnails", log_content)
        xbmcgui.Dialog().notification("OptiKlean", "Texture database not found.", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    try:
        progress.update(10, "Reading texture database...")
        conn = sqlite3.connect(texture_db)
        cursor = conn.cursor()
        cursor.execute("SELECT cachedurl FROM texture")
        rows = cursor.fetchall()
        conn.close()

        valid_thumbs = set()
        missing_thumbs = 0

        for row in rows:
            full_path = row[0]
            found = False
            for base_path in thumb_paths:
                thumb_path_item = xbmcvfs.makeLegalFilename(f"{base_path}{full_path}")
                if xbmcvfs.exists(thumb_path_item):
                    valid_thumbs.add(thumb_path_item)
                    found = True
                    break
            if not found:
                missing_thumbs += 1
                xbmc.log(f"OptiKlean DEBUG: Missing thumbnail: {full_path}", xbmc.LOGDEBUG)

        progress.update(20, "Counting thumbnails...")

        def count_files(path):
            total = 0
            try:
                dirs, files = xbmcvfs.listdir(path)
                total += len(files)
                for d in dirs:
                    sub_path = xbmcvfs.makeLegalFilename(f"{path}/{d}")
                    total += count_files(sub_path)
            except Exception as e:
                xbmc.log(f"OptiKlean DEBUG: Error counting files in {path}: {str(e)}", xbmc.LOGERROR)
            return total

        total_files = sum(count_files(p) for p in thumb_paths)

        progress.update(30, "Deleting unused thumbnails...")
        deleted, locked, errors, processed_files, total_size_freed = [], [], [], 0, 0
        current_index = 0

        def recursive_thumbnail_cleanup(thumb_path, valid_thumbs, progress_dialog, total_files, processed_files):
            xbmc.log(f"OptiKlean DEBUG: Entering recursive_thumbnail_cleanup for path: {thumb_path}", xbmc.LOGINFO)
            deleted = []
            locked = []
            errors = []
            size_freed = 0
            
            try:
                dirs, files = xbmcvfs.listdir(thumb_path)
                
                for file in files:
                    if progress_dialog and progress_dialog.iscanceled():
                        return deleted, locked, errors, processed_files, size_freed

                    file_path = xbmcvfs.makeLegalFilename(f"{thumb_path}/{file}")
                    processed_files += 1
                    percent = 30 + int((processed_files / total_files) * 70) if total_files > 0 else 100
                    progress_dialog.update(percent, f"Checking: {file[:20]}...")
                    
                    if file_path not in valid_thumbs:
                        # Get file size BEFORE deletion
                        file_size = get_file_size(file_path) or 0
                        status, error = delete_file(file_path)
                        if status == DELETE_SUCCESS:
                            deleted.append((file_path, file_size))
                            size_freed += file_size
                            xbmc.log(f"OptiKlean DEBUG: Deleted {file_path} (size: {file_size} bytes)", xbmc.LOGINFO)
                        elif status == DELETE_LOCKED:
                            locked.append(file_path)
                            xbmc.log(f"OptiKlean DEBUG: File locked: {file_path}", xbmc.LOGINFO)
                        else:
                            errors.append(f"{file_path} ({error})")
                            xbmc.log(f"OptiKlean DEBUG: Error deleting {file_path}: {error}", xbmc.LOGERROR)

                for dir_name in dirs:
                    sub_path = xbmcvfs.makeLegalFilename(f"{thumb_path}/{dir_name}")
                    sub_deleted, sub_locked, sub_errors, processed_files, sub_size = recursive_thumbnail_cleanup(
                        sub_path, valid_thumbs, progress_dialog, total_files, processed_files
                    )
                    deleted.extend(sub_deleted)
                    locked.extend(sub_locked)
                    errors.extend(sub_errors)
                    size_freed += sub_size

            except Exception as e:
                xbmc.log(f"OptiKlean DEBUG: Exception in recursive_thumbnail_cleanup: {str(e)}", xbmc.LOGERROR)
                errors.append(f"Error in {thumb_path}: {str(e)}")

            return deleted, locked, errors, processed_files, size_freed

        for path in thumb_paths:
            del_, lock_, err_, proc_, size_ = recursive_thumbnail_cleanup(
                path, valid_thumbs, progress, total_files, current_index
            )
            deleted.extend(del_)
            locked.extend(lock_)
            errors.extend(err_)
            processed_files += proc_
            total_size_freed += size_
            current_index = processed_files

        progress.update(100, "Finishing...")
        
        # Calculate total size freed in MB
        total_mb = total_size_freed / (1024 * 1024)
        
        log_content += f"Deleted: {len(deleted)} ({total_mb:.2f} MB freed)\n"
        log_content += f"Locked: {len(locked)}\n"
        log_content += f"Errors: {len(errors)}\n\n"
        xbmc.log(f"Valid thumbs in DB: {len(valid_thumbs)}", level=xbmc.LOGINFO)
        xbmc.log(f"Missing thumbs: {missing_thumbs}", level=xbmc.LOGINFO)

        if deleted:
            log_content += "Deleted files:\n"
            for file_path, file_size in deleted:
                # Extract just the filename
                filename = os.path.basename(file_path)
                # Format size appropriately
                if file_size >= 1024 * 1024:  # If >= 1MB
                    size_str = f"{file_size/(1024*1024):.2f}MB"
                elif file_size >= 1024:  # If >= 1KB
                    size_str = f"{file_size/1024:.2f}KB"
                else:
                    size_str = f"{file_size}B"
                log_content += f"    - {filename} ({size_str})\n"
            log_content += "\n"

        if locked:
            log_content += "Locked files (not deleted):\n"
            for file_path in locked:
                log_content += f"    - {os.path.basename(file_path)}\n"
            log_content += "\n"

        if errors:
            log_content += "Errors:\n"
            for error in errors:
                # Try to extract filename from error messages if possible
                if "Error in" in error:
                    # For path errors, show just the last part
                    parts = error.split(':')
                    if len(parts) > 1:
                        path_part = parts[0].strip()
                        filename = os.path.basename(path_part)
                        log_content += f"    - {filename}: {':'.join(parts[1:]).strip()}\n"
                    else:
                        log_content += f"    - {error}\n"
                else:
                    log_content += f"    - {error}\n"
            log_content += "\n"

        xbmc.log(f"OptiKlean DEBUG: Thumbnail cleanup completed. Freed {total_mb:.2f} MB", xbmc.LOGINFO)
        
        # Aggiorna i log delle impostazioni automatiche solo se:
        # 1. Non è in modalità automatica
        # 2. La pulizia automatica è abilitata nelle impostazioni
        if not auto_mode and addon.getSettingBool("clear_unused_thumbnails_enable"):
            try:
                update_last_run("clear_unused_thumbnails")
                update_automatic_settings_log()
                xbmc.log("OptiKlean: Updated automatic cleaning logs after manual execution", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"OptiKlean: Error updating automatic logs: {str(e)}", xbmc.LOGERROR)

    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Critical error in clear_unused_thumbnails: {str(e)}", xbmc.LOGERROR)
        log_content += f"Critical error: {str(e)}"

    finally:
        progress.close()
        execution_time = round(time.perf_counter() - start_time, 2)
        log_content += f"\nRunning time: {execution_time}s\n"
        write_log("clear_unused_thumbnails", log_content)
        xbmc.log("OptiKlean DEBUG: Finished clear_unused_thumbnails function", xbmc.LOGINFO)
        xbmcgui.Dialog().notification(
            "OptiKlean",
            f"Deleted {len(deleted)} unused thumbnails ({total_mb:.2f} MB freed)",
            xbmcgui.NOTIFICATION_INFO,
            5000
        )


def delete_folder(folder_path, progress_dialog=None):
    """
    Delete a folder and all its contents using hybrid xbmcvfs + os approach.
    Returns tuple: (status, locked_files, error_message)
    status can be: DELETE_SUCCESS, DELETE_LOCKED, or DELETE_ERROR
    """
    # Normalize path for all platforms
    folder_path = os.path.normpath(folder_path)
    if not folder_path.endswith(os.sep):
        folder_path += os.sep
    
    xbmc.log(f"OptiKlean DEBUG: Attempting to delete folder: {folder_path}", xbmc.LOGINFO)
    
    # Hybrid existence check
    def path_exists(path):
        # First try xbmcvfs
        if xbmcvfs.exists(path):
            return True
        # Fallback to os.path
        return os.path.exists(path)
    
    if not path_exists(folder_path):
        xbmc.log(f"OptiKlean DEBUG: Folder does not exist: {folder_path}", xbmc.LOGINFO)
        return DELETE_SUCCESS, [], "Folder does not exist"

    locked_files = []
    
    try:
        # Get list of contents using best available method
        def list_contents(path):
            try:
                # First try xbmcvfs
                dirs, files = xbmcvfs.listdir(path)
                return dirs, files
            except Exception as e:
                xbmc.log(f"OptiKlean DEBUG: xbmcvfs.listdir failed: {str(e)}", xbmc.LOGERROR)
                # Fallback to os.listdir
                try:
                    all_items = os.listdir(path)
                    dirs = [d for d in all_items if os.path.isdir(os.path.join(path, d))]
                    files = [f for f in all_items if not os.path.isdir(os.path.join(path, f))]
                    return dirs, files
                except Exception as e:
                    xbmc.log(f"OptiKlean DEBUG: Error listing contents: {str(e)}", xbmc.LOGERROR)
                    raise

        # Delete files first
        dirs, files = list_contents(folder_path)
        xbmc.log(f"OptiKlean DEBUG: Found {len(files)} files and {len(dirs)} subdirectories", xbmc.LOGINFO)
        
        for file in files:
            if progress_dialog and progress_dialog.iscanceled():
                return DELETE_ERROR, [], "Operation cancelled by user"
                
            file_path = os.path.join(folder_path, file)
            if progress_dialog:
                try:
                    percent = progress_dialog.getPercentage()
                    progress_dialog.update(percent, f"Deleting file: {file}")
                except AttributeError:
                    pass
            
            # Hybrid delete approach
            status = DELETE_ERROR
            error_msg = ""
            
            # First try xbmcvfs
            try:
                if xbmcvfs.delete(file_path):
                    status = DELETE_SUCCESS
                else:
                    # Fallback to os.remove
                    try:
                        os.remove(file_path)
                        status = DELETE_SUCCESS
                    except Exception as e:
                        error_msg = str(e)
                        if getattr(e, 'errno', None) in (errno.EACCES, errno.EPERM, errno.EBUSY):
                            status = DELETE_LOCKED
            except Exception as e:
                error_msg = str(e)
                if getattr(e, 'errno', None) in (errno.EACCES, errno.EPERM, errno.EBUSY):
                    status = DELETE_LOCKED
            
            if status == DELETE_LOCKED:
                locked_files.append(file_path)
                xbmc.log(f"OptiKlean DEBUG: File is locked: {file_path}", xbmc.LOGINFO)
            elif status == DELETE_ERROR:
                xbmc.log(f"OptiKlean DEBUG: Error deleting file: {file_path} - {error_msg}", xbmc.LOGERROR)
        
        # Then delete subdirectories recursively
        for folder in dirs:
            if progress_dialog and progress_dialog.iscanceled():
                return DELETE_ERROR, [], "Operation cancelled by user"
                
            subfolder_path = os.path.join(folder_path, folder)
            if progress_dialog:
                try:
                    percent = progress_dialog.getPercentage()
                    progress_dialog.update(percent, f"Processing subfolder: {folder}")
                except AttributeError:
                    pass
            
            sub_status, sub_locked, sub_error = delete_folder(subfolder_path, progress_dialog)
            if sub_status == DELETE_LOCKED:
                locked_files.extend(sub_locked)
            elif sub_status == DELETE_ERROR:
                xbmc.log(f"OptiKlean DEBUG: Error deleting subfolder: {subfolder_path} - {sub_error}", xbmc.LOGERROR)
        
        # Finally delete the folder itself
        if locked_files:
            return DELETE_LOCKED, locked_files, "Folder contains locked files"
            
        # Hybrid folder deletion
        deleted = False
        try:
            # First try xbmcvfs
            if xbmcvfs.rmdir(folder_path):
                deleted = True
            else:
                # Fallback to os.rmdir
                try:
                    os.rmdir(folder_path)
                    deleted = True
                except OSError as e:
                    if e.errno == errno.ENOTEMPTY:
                        # Folder not empty - try to list contents to verify
                        try:
                            remaining_dirs, remaining_files = list_contents(folder_path)
                            xbmc.log(f"OptiKlean DEBUG: Folder not empty, contains {len(remaining_files)} files and {len(remaining_dirs)} subfolders", xbmc.LOGINFO)
                        except Exception:
                            pass
                    error_msg = str(e)
        except Exception as e:
            error_msg = str(e)
        
        if deleted:
            xbmc.log(f"OptiKlean DEBUG: Successfully deleted folder: {folder_path}", xbmc.LOGINFO)
            return DELETE_SUCCESS, [], ""
        else:
            xbmc.log(f"OptiKlean DEBUG: Failed to delete folder: {folder_path} - {error_msg}", xbmc.LOGERROR)
            return DELETE_ERROR, [], error_msg
    
    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Exception in delete_folder: {str(e)}", xbmc.LOGERROR)
        return DELETE_ERROR, [], str(e)


# Funzione per pulire i residui degli addon (addon disabilitati e residui di addon disinstallati)
def clear_addon_leftovers(auto_mode=False):
    start_time = time.perf_counter()
    progress = xbmcgui.DialogProgress()
    progress.create("OptiKlean", "Reading addon information...")
    log_content = "Disabled and leftovers addons cleaning results:\n\n"
    xbmc.log("OptiKlean DEBUG: Starting clear_addon_leftovers", xbmc.LOGINFO)

    # Get enabled addons
    progress.update(20, "Reading enabled addons list...")
    enabled_addons = []
    try:
        json_response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Addons.GetAddons", "params":{"enabled":true}, "id":1}')
        response = json.loads(json_response)
        if 'result' in response and 'addons' in response['result']:
            enabled_addons = [addon['addonid'] for addon in response['result']['addons']]
            xbmc.log(f"OptiKlean DEBUG: Found {len(enabled_addons)} enabled addons", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Error getting enabled addons: {str(e)}", xbmc.LOGERROR)

    # Get disabled addons
    progress.update(30, "Reading disabled addons list...")
    disabled_addons = []
    try:
        json_response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Addons.GetAddons", "params":{"enabled":false}, "id":1}')
        response = json.loads(json_response)
        if 'result' in response and 'addons' in response['result']:
            disabled_addons = [addon['addonid'] for addon in response['result']['addons']]
            xbmc.log(f"OptiKlean DEBUG: Found {len(disabled_addons)} disabled addons", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Error getting disabled addons: {str(e)}", xbmc.LOGERROR)

    all_installed_addons = set(enabled_addons + disabled_addons)
    disabled_addons_set = set(disabled_addons)
    xbmc.log(f"OptiKlean DEBUG: Total installed addons: {len(all_installed_addons)}", xbmc.LOGINFO)

    # Check addons folder
    addon_dir = xbmcvfs.translatePath("special://home/addons/")
    progress.update(40, "Finding addon folders...")
    existing_addon_folders = set(xbmcvfs.listdir(addon_dir)[0]) if xbmcvfs.exists(addon_dir) else set()
    xbmc.log(f"OptiKlean DEBUG: Found {len(existing_addon_folders)} addon folders on disk", xbmc.LOGINFO)

    # Check addon_data folder
    addon_data_dir = xbmcvfs.translatePath("special://home/userdata/addon_data/")
    progress.update(50, "Checking addon data folders...")
    existing_addon_data_folders = set(xbmcvfs.listdir(addon_data_dir)[0]) if xbmcvfs.exists(addon_data_dir) else set()
    xbmc.log(f"OptiKlean DEBUG: Found {len(existing_addon_data_folders)} addon_data folders on disk", xbmc.LOGINFO)

    # Identify leftovers
    orphaned_folders = [folder for folder in existing_addon_folders if folder not in all_installed_addons]
    disabled_folders = [folder for folder in existing_addon_folders if folder in disabled_addons_set]
    orphaned_addon_data = [folder for folder in existing_addon_data_folders if folder not in all_installed_addons]
    disabled_addon_data = [folder for folder in existing_addon_data_folders if folder in disabled_addons_set]
    xbmc.log(f"OptiKlean DEBUG: Found {len(orphaned_folders)} orphaned folders, {len(disabled_folders)} disabled folders, {len(orphaned_addon_data)} orphaned addon_data, {len(disabled_addon_data)} disabled addon_data", xbmc.LOGINFO)

    # Create selection list
    display_list = []
    folder_map = {}
    xbmc.log("OptiKlean DEBUG: Building selection list", xbmc.LOGINFO)

    # Disabled addon folders (in addons)
    for folder in disabled_folders:
        if folder != "packages":  # Skip packages folder
            display_name = f"[Disabled] {folder} (addons)"
            display_list.append(display_name)
            folder_map[display_name] = xbmcvfs.translatePath(os.path.normpath(os.path.join(addon_dir, folder)))
            xbmc.log(f"OptiKlean DEBUG: Added disabled addon folder: {folder}", xbmc.LOGINFO)

    # Disabled addon_data folders
    for folder in disabled_addon_data:
        if folder != "packages":  # Skip packages folder
            display_name = f"[Disabled] {folder} (addon_data)"
            display_list.append(display_name)
            folder_map[display_name] = xbmcvfs.translatePath(os.path.normpath(os.path.join(addon_data_dir, folder)))
            xbmc.log(f"OptiKlean DEBUG: Added disabled addon_data folder: {folder}", xbmc.LOGINFO)

    # Orphaned addon folders
    for folder in orphaned_folders:
        if folder != "packages" and folder != "temp":  # Skip packages and temp folders
            display_name = f"[Leftover] {folder} (addons)"
            display_list.append(display_name)
            folder_map[display_name] = xbmcvfs.translatePath(os.path.normpath(os.path.join(addon_dir, folder)))
            xbmc.log(f"OptiKlean DEBUG: Added orphaned addon folder: {folder}", xbmc.LOGINFO)

    # Orphaned addon_data folders
    for folder in orphaned_addon_data:
        if folder != "packages":  # Skip packages folder
            display_name = f"[Leftover] {folder} (addon_data)"
            display_list.append(display_name)
            folder_map[display_name] = xbmcvfs.translatePath(os.path.normpath(os.path.join(addon_data_dir, folder)))
            xbmc.log(f"OptiKlean DEBUG: Added orphaned addon_data folder: {folder}", xbmc.LOGINFO)

    progress.close()

    if not display_list:
        xbmc.log("OptiKlean DEBUG: No leftover or disabled addons found", xbmc.LOGINFO)
        progress.close()
        log_content += "No leftover or disabled addon folders found.\n"
        write_log("clear_addon_leftovers", log_content)
        
        # Aggiorna i log delle impostazioni automatiche anche se non ci sono addon da eliminare
        xbmc.log(f"OptiKlean DEBUG: auto_mode={auto_mode}, clear_addon_leftovers_enable={addon.getSettingBool('clear_addon_leftovers_enable')}", xbmc.LOGINFO)
        if not auto_mode and addon.getSettingBool("clear_addon_leftovers_enable"):
            try:
                update_last_run("clear_addon_leftovers")
                update_automatic_settings_log()
                xbmc.log("OptiKlean: Updated automatic cleaning logs after manual execution", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"OptiKlean: Error updating automatic logs: {str(e)}", xbmc.LOGERROR)

        # Mostra la finestra di dialogo solo se non è in modalità automatica
        if not auto_mode:
            xbmcgui.Dialog().ok("OptiKlean", "No leftover or disabled addons found.")
        return

    # User selection
    message = "Select folders to remove:"
    if not auto_mode:
        selected = xbmcgui.Dialog().multiselect(message, display_list)
        xbmc.log(f"OptiKlean DEBUG: User selected {len(selected) if selected else 0} items", xbmc.LOGINFO)

        if not selected:
            xbmc.log("OptiKlean DEBUG: No items selected for deletion", xbmc.LOGINFO)
            write_log("clear_addon_leftovers", log_content)
            return

        selected_display_names = [display_list[i] for i in selected]
    else:
        selected_display_names = display_list

    def get_folder_size(folder_path):
        """Calculate total size of a folder in bytes"""
        total_size = 0
        try:
            # First try xbmcvfs method
            dirs, files = xbmcvfs.listdir(folder_path)
            for file in files:
                file_path = xbmcvfs.makeLegalFilename(os.path.join(folder_path, file))
                file_size = get_file_size(file_path)
                total_size += file_size
                xbmc.log(f"OptiKlean DEBUG: File {file_path} size: {file_size} bytes", xbmc.LOGDEBUG)
            
            for dir_name in dirs:
                dir_path = xbmcvfs.makeLegalFilename(os.path.join(folder_path, dir_name))
                total_size += get_folder_size(dir_path)
                
        except Exception as e:
            xbmc.log(f"OptiKlean DEBUG: Error calculating folder size for {folder_path}: {str(e)}", xbmc.LOGERROR)
            # Fallback to os.walk if xbmcvfs fails
            try:
                for root, dirs, files in os.walk(folder_path):
                    for f in files:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
            except Exception as e:
                xbmc.log(f"OptiKlean DEBUG: Fallback size calculation failed for {folder_path}: {str(e)}", xbmc.LOGERROR)
        
        return total_size

    # Deletion process
    progress = xbmcgui.DialogProgress()
    progress.create("OptiKlean", "Removing selected addons...")
    total_selected = len(selected_display_names)
    deleted_folders = []
    locked_folders = []
    locked_files = []
    error_folders = []
    total_size_freed = 0  # Track total size of deleted files

    for index, display_name in enumerate(selected_display_names):
        if progress.iscanceled():
            xbmc.log("OptiKlean DEBUG: Operation canceled by user", xbmc.LOGINFO)
            break

        folder_path = folder_map[display_name]
        xbmc.log(f"OptiKlean DEBUG: Processing folder {folder_path} ({index+1}/{total_selected})", xbmc.LOGINFO)
        percent = int((index / total_selected) * 100) if total_selected > 0 else 0
        progress.update(percent, f"Removing addon ({index+1}/{total_selected}): {folder_path}")

        # Get folder size before deletion
        folder_size = get_folder_size(folder_path)
        xbmc.log(f"OptiKlean DEBUG: Folder size before deletion: {folder_size} bytes", xbmc.LOGINFO)
        
        status, locked_file_list, error_msg = delete_folder(folder_path, progress_dialog=progress)
        if status == DELETE_SUCCESS:
            xbmc.log(f"OptiKlean DEBUG: Successfully deleted folder {folder_path}", xbmc.LOGINFO)
            deleted_folders.append((folder_path, folder_size))
            total_size_freed += folder_size
        elif status == DELETE_LOCKED:
            xbmc.log(f"OptiKlean DEBUG: Folder locked {folder_path}", xbmc.LOGINFO)
            locked_folders.append(folder_path)
            locked_files.extend(locked_file_list)
        else:
            xbmc.log(f"OptiKlean DEBUG: Error deleting folder {folder_path}: {error_msg}", xbmc.LOGERROR)
            error_folders.append(f"{folder_path} ({error_msg})")

    progress.close()

    # Calculate total MB freed
    total_size_freed = sum(size for _, size in deleted_folders)  # Calculate from deleted_folders
    total_mb = total_size_freed / (1024 * 1024) if total_size_freed > 0 else 0  # Initialize here

    # Final log
    xbmc.log(f"OptiKlean DEBUG: Deletion complete. Deleted: {len(deleted_folders)}, Freed: {total_mb:.2f} MB", xbmc.LOGINFO)
    
    # Organize deleted folders by type using existing variables
    deleted_addons = [(f.replace(addon_dir, ""), s) for f, s in deleted_folders if addon_dir in f]
    deleted_addon_data = [(f.replace(addon_data_dir, ""), s) for f, s in deleted_folders if addon_data_dir in f]
    
    if deleted_folders:
        log_content += "Successfully deleted addon folders:\n"
        if deleted_addons:
            log_content += "  [Addons]:\n"
            for folder, size in deleted_addons:
                size_mb = size / (1024 * 1024)
                log_content += f"    - {folder} ({size_mb:.2f} MB)\n"
        if deleted_addon_data:
            log_content += "  [Addon Data]:\n"
            for folder, size in deleted_addon_data:
                size_mb = size / (1024 * 1024)
                log_content += f"    - {folder} ({size_mb:.2f} MB)\n"
        log_content += f"\n  Total space freed: {total_mb:.2f} MB\n\n"
    
    if locked_folders:
        cleaned_locked = [f.replace(addon_dir, "").replace(addon_data_dir, "") for f in locked_folders]
        log_content += "Addon folders with locked files:\n  " + "\n  ".join(cleaned_locked) + "\n\n"
        if locked_files:
            cleaned_locked_files = [os.path.basename(f) for f in locked_files]
            log_content += "Locked files:\n  " + "\n  ".join(cleaned_locked_files) + "\n\n"
    if error_folders:
        cleaned_errors = []
        for error in error_folders:
            path, msg = error.split(" (", 1)
            cleaned_path = path.replace(addon_dir, "").replace(addon_data_dir, "")
            cleaned_errors.append(f"{cleaned_path} ({msg}")
        log_content += "Errors:\n  " + "\n  ".join(cleaned_errors) + "\n\n"

    execution_time = round(time.perf_counter() - start_time, 2)
    log_content += f"Running time: {execution_time}s\n"
    
    write_log("clear_addon_leftovers", log_content)
    xbmcgui.Dialog().notification(
        "OptiKlean",
        f"Cleared {len(deleted_folders)} addon folders ({total_mb:.2f} MB freed)",
        xbmcgui.NOTIFICATION_INFO,
        3000
    )

    # Aggiorna i log delle impostazioni automatiche solo se:
    # 1. Non è in modalità automatica
    # 2. La pulizia automatica è abilitata nelle impostazioni
    xbmc.log(f"OptiKlean DEBUG: auto_mode={auto_mode}, clear_addon_leftovers_enable={addon.getSettingBool('clear_addon_leftovers_enable')}", xbmc.LOGINFO)
    if not auto_mode and addon.getSettingBool("clear_addon_leftovers_enable"):
        try:
            update_last_run("clear_addon_leftovers")
            update_automatic_settings_log()
            xbmc.log("OptiKlean: Updated automatic cleaning logs after manual execution", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"OptiKlean: Error updating automatic logs: {str(e)}", xbmc.LOGERROR)

# Funzione per pulire i pacchetti (packages)
def clear_kodi_packages(auto_mode=False):
    start_time = time.perf_counter()
    progress = xbmcgui.DialogProgress()
    progress.create("OptiKlean", "Preparing to clear packages...")
    
    packages_path = xbmcvfs.translatePath("special://home/addons/packages")
    xbmc.log(f"OptiKlean DEBUG: Using packages path: {packages_path}", xbmc.LOGINFO)
    log_content = "Kodi packages cleaning results:\n\n"
    
    # Track results
    deleted_items = []
    locked_items = []
    error_items = []
    total_size_freed = 0  # Track total size of deleted packages
    
    xbmc.log(f"OptiKlean DEBUG: Starting package cleanup at path: {packages_path}", xbmc.LOGINFO)
    
    def path_exists(path):
        path = xbmcvfs.translatePath(os.path.normpath(path))
        if xbmcvfs.exists(path):
            xbmc.log(f"OptiKlean DEBUG: Path exists (xbmcvfs): {path}", xbmc.LOGINFO)
            return True
        if os.path.exists(path):
            xbmc.log(f"OptiKlean DEBUG: Path exists (os.path): {path}", xbmc.LOGINFO)
            return True
        xbmc.log(f"OptiKlean DEBUG: Path does not exist: {path}", xbmc.LOGINFO)
        return False
    
    if not path_exists(packages_path):
        error_msg = f"Packages folder does not exist: {packages_path}"
        xbmc.log(f"OptiKlean DEBUG: {error_msg}", xbmc.LOGERROR)
        log_content += error_msg + "\n"
        progress.close()
        write_log("clear_kodi_packages", log_content)
        xbmcgui.Dialog().notification("OptiKlean", "Packages folder not found", xbmcgui.NOTIFICATION_ERROR, 3000)
        return
    
    # Hybrid file listing with robust path handling
    def list_package_files(path):
        norm_path = xbmcvfs.translatePath(os.path.normpath(path))
        try:
            xbmc.log(f"OptiKlean DEBUG: Attempting xbmcvfs.listdir for: {norm_path}", xbmc.LOGINFO)
            dirs, files = xbmcvfs.listdir(norm_path)
            zip_files = [f for f in files if f.lower().endswith('.zip')]
            xbmc.log(f"OptiKlean DEBUG: Found {len(zip_files)} zip files via xbmcvfs", xbmc.LOGINFO)
            return zip_files
        except Exception as e:
            xbmc.log(f"OptiKlean DEBUG: xbmcvfs.listdir failed, falling back to os.listdir: {str(e)}", xbmc.LOGWARNING)
            try:
                zip_files = [f for f in os.listdir(norm_path) if f.lower().endswith('.zip') and os.path.isfile(
                    xbmcvfs.translatePath(os.path.normpath(os.path.join(norm_path, f))))]
                xbmc.log(f"OptiKlean DEBUG: Found {len(zip_files)} zip files via os.listdir", xbmc.LOGINFO)
                return zip_files
            except Exception as e:
                xbmc.log(f"OptiKlean DEBUG: Failed to list directory contents: {str(e)}", xbmc.LOGERROR)
                return []
    
    package_files = list_package_files(packages_path)
    total_files = len(package_files)
    
    xbmc.log(f"OptiKlean DEBUG: Found {total_files} package files to process", xbmc.LOGINFO)
    
    if total_files == 0:
        progress.close()
        log_content += "No package files found to delete.\n"
        write_log("clear_kodi_packages", log_content)
        xbmcgui.Dialog().notification("OptiKlean", "No packages found", xbmcgui.NOTIFICATION_INFO, 3000)
        # Aggiorna i log delle impostazioni automatiche anche se non ci sono pacchetti
        xbmc.log(f"OptiKlean DEBUG: auto_mode={auto_mode}, clear_kodi_packages_enable={addon.getSettingBool('clear_kodi_packages_enable')}", xbmc.LOGINFO)
        if not auto_mode and addon.getSettingBool("clear_kodi_packages_enable"):
            try:
                update_last_run("clear_kodi_packages")
                update_automatic_settings_log()
                xbmc.log("OptiKlean: Updated automatic cleaning logs after manual execution", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"OptiKlean: Error updating automatic logs: {str(e)}", xbmc.LOGERROR)
        return
    
    def delete_package_file(file_path):
        norm_path = xbmcvfs.translatePath(os.path.normpath(file_path))
        xbmc.log(f"OptiKlean DEBUG: Attempting to delete: {norm_path}", xbmc.LOGINFO)

        # Get file size before deletion (spostato all'inizio)
        try:
            file_size = get_file_size(norm_path)
        except Exception:
            file_size = 0  # Default se non riesci a ottenere la dimensione

        # First try xbmcvfs
        try:
            if xbmcvfs.delete(norm_path):
                xbmc.log(f"OptiKlean DEBUG: Successfully deleted via xbmcvfs: {norm_path}", xbmc.LOGINFO)
                return DELETE_SUCCESS, file_size  # Restituisci la dimensione invece di ""
            xbmc.log(f"OptiKlean DEBUG: xbmcvfs.delete returned False for: {norm_path}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"OptiKlean DEBUG: xbmcvfs.delete exception: {str(e)}", xbmc.LOGWARNING)
        
        # Fallback to os.remove with verification
        try:
            if os.path.exists(norm_path):
                os.remove(norm_path)
                if not os.path.exists(norm_path):
                    xbmc.log(f"OptiKlean DEBUG: Successfully deleted via os.remove: {norm_path}", xbmc.LOGINFO)
                    return DELETE_SUCCESS, file_size
                xbmc.log(f"OptiKlean DEBUG: File still exists after os.remove: {norm_path}", xbmc.LOGERROR)
                return DELETE_ERROR, "File removal failed"
            xbmc.log(f"OptiKlean DEBUG: File disappeared before os.remove: {norm_path}", xbmc.LOGINFO)
            return DELETE_SUCCESS, 0
        except OSError as e:
            if e.errno in (errno.EACCES, errno.EPERM, errno.EBUSY):
                xbmc.log(f"OptiKlean DEBUG: File locked: {norm_path}", xbmc.LOGINFO)
                return DELETE_LOCKED, str(e)
            xbmc.log(f"OptiKlean DEBUG: OS error deleting file: {norm_path} - {str(e)}", xbmc.LOGERROR)
            return DELETE_ERROR, str(e)
        except Exception as e:
            xbmc.log(f"OptiKlean DEBUG: Unexpected error deleting file: {norm_path} - {str(e)}", xbmc.LOGERROR)
            return DELETE_ERROR, str(e)
    
    for index, package_file in enumerate(package_files):
        if progress.iscanceled():
            xbmc.log("OptiKlean DEBUG: Operation canceled by user", xbmc.LOGINFO)
            log_content += "\nOperation cancelled by user.\n"
            break
            
        percent = int((index / total_files) * 100) if total_files > 0 else 0
        file_path = xbmcvfs.translatePath(os.path.normpath(os.path.join(packages_path, package_file)))
        progress.update(percent, f"Deleting package ({index+1}/{total_files}): {package_file}")
        
        xbmc.log(f"OptiKlean DEBUG: Processing package file {index+1}/{total_files}: {file_path}", xbmc.LOGINFO)
        
        status, result = delete_package_file(file_path)
        if status == DELETE_SUCCESS:
            if isinstance(result, int):  # If we got a file size
                deleted_items.append((file_path, result))
                total_size_freed += result
            else:
                deleted_items.append((file_path, 0))  # Default to 0 if size unknown
        elif status == DELETE_LOCKED:
            locked_items.append(f"{file_path} ({result})")
        else:
            error_items.append(f"{file_path} ({result})")
    
    progress.close()
    
    # Format results
    if deleted_items:
        total_mb = total_size_freed / (1024 * 1024)
        log_content += f"Successfully deleted {len(deleted_items)} packages ({total_mb:.2f} MB freed):\n"
        for file_path, size in deleted_items:
            filename = os.path.basename(file_path)  # Extract just the filename
            size_kb = size / 1024
            size_mb = size / (1024 * 1024)
            # Show size in appropriate unit (KB or MB)
            if size_mb >= 1:
                log_content += f"  - {filename} ({size_mb:.2f} MB)\n"
            else:
                log_content += f"  - {filename} ({size_kb:.2f} KB)\n"
        log_content += "\n"
    
    if locked_items:
        log_content += "Packages in use (locked):\n"
        for item in locked_items:
            path, reason = item.split(" (", 1) if " (" in item else (item, "")
            filename = os.path.basename(path)
            log_content += f"  - {filename} ({reason}\n"
        log_content += "\n"
    
    if error_items:
        log_content += "Errors while deleting packages:\n"
        for item in error_items:
            path, reason = item.split(" (", 1) if " (" in item else (item, "")
            filename = os.path.basename(path)
            log_content += f"  - {filename} ({reason}\n"
        log_content += "\n"

    execution_time = round(time.perf_counter() - start_time, 2)
    log_content += f"\nRunning time: {execution_time}s\n"
    write_log("clear_kodi_packages", log_content)
    
    # Show summary notification
    if deleted_items:
        total_mb = total_size_freed / (1024 * 1024)
        summary = f"Deleted {len(deleted_items)} packages ({total_mb:.2f} MB freed)"
    else:
        summary = "No packages deleted"
    if locked_items:
        summary += f" ({len(locked_items)} locked)"
    xbmcgui.Dialog().notification("OptiKlean", summary, xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.log(f"OptiKlean DEBUG: Package cleanup completed. {summary}", xbmc.LOGINFO)

    # Aggiorna i log delle impostazioni automatiche solo se:
    # 1. Non è in modalità automatica
    # 2. La pulizia automatica è abilitata nelle impostazioni
    xbmc.log(f"OptiKlean DEBUG: auto_mode={auto_mode}, clear_kodi_packages_enable={addon.getSettingBool('clear_kodi_packages_enable')}", xbmc.LOGINFO)
    if not auto_mode and addon.getSettingBool("clear_kodi_packages_enable"):
        try:
            update_last_run("clear_kodi_packages")
            update_automatic_settings_log()
            xbmc.log("OptiKlean: Updated automatic cleaning logs after manual execution", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"OptiKlean: Error updating automatic logs: {str(e)}", xbmc.LOGERROR)

# Funzione per ottimizzare i database di Kodi e degli addons
def optimize_databases(auto_mode=False):
    start_time = time.perf_counter()
    # Percorsi base
    std_db_path = xbmcvfs.translatePath("special://database/")
    backup_path = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('profile')), 'db_backups')
    xbmc.log(f"OptiKlean DEBUG: Using backup path: {backup_path}", xbmc.LOGINFO)
    addon_data_path = xbmcvfs.translatePath("special://userdata/addon_data/").rstrip('/') + '/'

    # Inizializza log (senza debug)
    log_content = "Database optimization results:\n\n"
    
    # Risultati
    optimized_dbs = []
    locked_dbs = []
    error_dbs = []
    backup_dbs = []
    backup_failed = []

    # Funzione debug solo per console (non per file log)
    def debug_log(message):
        xbmc.log(f"OptiKlean Debug: {message}", xbmc.LOGINFO)
        return ""  # Restituisce stringa vuota invece del messaggio

    # Progress dialog
    progress = xbmcgui.DialogProgress()
    progress.create("OptiKlean", "Preparing database optimization...")
    
    # Create backup directory if it doesn't exist
    try:
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
            xbmc.log(f"OptiKlean DEBUG: Created backup directory: {backup_path}", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"OptiKlean DEBUG: Error creating backup directory: {str(e)}", xbmc.LOGERROR)
        return
    
    def check_directory_exists(dir_path):
        if xbmcvfs.exists(dir_path):
            return True
        test_file = xbmcvfs.makeLegalFilename(dir_path + "/.temp_test")
        try:
            f = xbmcvfs.File(test_file, 'w')
            f.write("test")
            f.close()
            xbmcvfs.delete(test_file)
            return True
        except Exception:
            try:
                xbmcvfs.delete(test_file)
            except Exception:
                pass
            return False
    
    def process_databases(directory, source_type="standard"):
        db_files = []
        try:
            _, files = xbmcvfs.listdir(directory)
            for file in files:
                if file.lower().endswith((".db", ".sqlite")):
                    # commentata perché inutilizzata
                    # full_path = xbmcvfs.makeLegalFilename(directory + '/' + file)
                    db_files.append((directory, file, source_type))
        except Exception:
            pass
        return db_files
    
    # Raccolta database
    all_db_files = []
    all_db_files.extend(process_databases(std_db_path, "standard"))
    
    if check_directory_exists(addon_data_path):
        addon_dirs, _ = xbmcvfs.listdir(addon_data_path)
        for addon_dir in addon_dirs:
            addon_path = xbmcvfs.makeLegalFilename(addon_data_path + addon_dir)
            if check_directory_exists(addon_path):
                all_db_files.extend(process_databases(addon_path, f"addon:{addon_dir}"))
                try:
                    subdirs, _ = xbmcvfs.listdir(addon_path)
                    for subdir in subdirs:
                        subdir_path = xbmcvfs.makeLegalFilename(addon_path + '/' + subdir)
                        if check_directory_exists(subdir_path):
                            all_db_files.extend(process_databases(subdir_path, f"addon:{addon_dir}:{subdir}"))
                except Exception:
                    pass
    
    # Elaborazione
    total_files = len(all_db_files)
    if total_files == 0:
        progress.close()
        log_content += "No databases found to process.\n"
        write_log("optimize_databases", log_content)
        xbmcgui.Dialog().notification("OptiKlean", "No databases found", xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for index, (dir_path, file, source_type) in enumerate(all_db_files):
        if progress.iscanceled():
            log_content += "\nOperation cancelled by user.\n"
            break
            
        percent = int((index / total_files) * 100)
        progress.update(percent, f"Processing: {file}")

        db_file_path = xbmcvfs.makeLegalFilename(dir_path + '/' + file)
        backup_type_path = xbmcvfs.makeLegalFilename(backup_path + '/' + source_type.replace(":", "_"))
        
        if not xbmcvfs.exists(backup_type_path):
            xbmcvfs.mkdirs(backup_type_path)
        
        backup_file_path = xbmcvfs.makeLegalFilename(backup_type_path + '/' + file + ".bak")
        
        # Backup
        try:
            if xbmcvfs.copy(db_file_path, backup_file_path):
                backup_dbs.append(f"{source_type}:{file}")
            else:
                backup_failed.append(f"{source_type}:{file}")
        except Exception:
            backup_failed.append(f"{source_type}:{file}")
        
        # Ottimizzazione
        try:
            conn = sqlite3.connect(db_file_path, timeout=1)
            conn.execute("PRAGMA quick_check;")
            conn.execute("VACUUM;")
            conn.close()
            optimized_dbs.append(f"{source_type}:{file}")
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                locked_dbs.append(f"{source_type}:{file}")
            else:
                error_dbs.append(f"{source_type}:{file}")
        except Exception:
            error_dbs.append(f"{source_type}:{file}")
    
    progress.close()
    
    # Costruzione log pulito
    log_content += f"Total databases processed: {total_files}\n\n"
    
    if backup_dbs:
        log_content += "SUCCESSFUL BACKUPS:\n" + "\n".join(f"• {db}" for db in backup_dbs) + "\n\n"
    if optimized_dbs:
        log_content += "OPTIMIZED DATABASES:\n" + "\n".join(f"• {db}" for db in optimized_dbs) + "\n\n"
    if locked_dbs:
        log_content += "LOCKED DATABASES (not optimized):\n" + "\n".join(f"• {db}" for db in locked_dbs) + "\n\n"
    if backup_failed:
        log_content += "BACKUP FAILED:\n" + "\n".join(f"• {db}" for db in backup_failed) + "\n"
    if error_dbs:
        log_content += "OPTIMIZATION ERRORS:\n" + "\n".join(f"• {db}" for db in error_dbs)

    execution_time = round(time.perf_counter() - start_time, 2)
    log_content += f"\nRunning time: {execution_time}s\n"    
    write_log("optimize_databases", log_content)
    xbmcgui.Dialog().notification(
        "OptiKlean", 
        f"Optimized {len(optimized_dbs)}/{total_files} databases", 
        xbmcgui.NOTIFICATION_INFO, 
        3000
    )

    # Aggiorna i log delle impostazioni automatiche solo se:
    # 1. Non è in modalità automatica
    # 2. La pulizia automatica è abilitata nelle impostazioni
    if not auto_mode and addon.getSettingBool("optimize_databases_enable"):
        try:
            update_last_run("optimize_databases")
            update_automatic_settings_log()
            xbmc.log("OptiKlean: Updated automatic cleaning logs after manual execution", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"OptiKlean: Error updating automatic logs: {str(e)}", xbmc.LOGERROR)

def show_support():
    dialog = xbmcgui.Dialog()
    
    dialog.ok(
        heading="Support",
        message="Telegram: @ItalianSpaghettiGeeks",
    )


# Funzione per visualizzare i log
def view_logs():
    log_reports = [
        ("Clear Kodi temp folder log", "clear_kodi_temp_folder.log"),
        ("Clear cache files from addon data log", "clear_cache_files_from_addon_data.log"),
        ("Clear temp folders from addon data log", "clear_temp_folders_from_addon_data.log"),
        ("Clear temp folder from addons log", "clear_temp_folder_from_addons.log"),
        ("Clear unused thumbnails log", "clear_unused_thumbnails.log"),
        ("Clear addon leftovers log", "clear_addon_leftovers.log"),
        ("Clear Kodi packages log", "clear_kodi_packages.log"),
        ("Optimize databases log", "optimize_databases.log"),
        ("Automatic cleaning settings log", "automatic_cleaning_settings.log")
    ]

    # Create a list of user-friendly names
    display_names = [name for name, _ in log_reports]
    selected = xbmcgui.Dialog().select("Select log to view", display_names)

    if selected != -1:
        _, filename = log_reports[selected]
        log_file = os.path.join(addon_data_folder, filename)

        try:
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if not content.strip():
                    content = "Empty content"
            else:
                content = "Log file not found."
        except Exception as e:
            content = "Error reading log file: " + str(e)

        xbmcgui.Dialog().textviewer("Log: " + display_names[selected], content)


def run_automatic_maintenance():
    """Esegue la manutenzione automatica quando chiamato da autoexec.py"""
    xbmc.log("OptiKlean: Avvio manutenzione automatica", xbmc.LOGINFO)
    
    actions_executed = []
    addon = xbmcaddon.Addon()
    
    # Ensure data folder exists
    if not xbmcvfs.exists(addon_data_folder):
        xbmcvfs.mkdirs(addon_data_folder)
        xbmc.log("OptiKlean: Created addon data folder", xbmc.LOGINFO)
    
    def should_run_cleaning(cleaning_type):
        """Determina se una determinata pulizia deve essere eseguita in base allo switch e all'intervallo"""
        try:
            # Verifica se è abilitata nelle impostazioni
            if not addon.getSettingBool(f"{cleaning_type}_enable"):
                xbmc.log(f"OptiKlean: {cleaning_type} non eseguita perché disabilitata", xbmc.LOGDEBUG)
                return False

            interval = addon.getSettingInt(f"{cleaning_type}_interval")
            last_run_file = os.path.join(addon_data_folder, f"last_{cleaning_type}.json")

            if not xbmcvfs.exists(last_run_file):
                return True  # prima esecuzione

            with open(last_run_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_run = data.get("timestamp", 0)

            if last_run == 0:
                return True

            next_run = last_run + (interval * 86400)
            now = int(time.time())
            return now >= next_run

        except Exception as e:
            xbmc.log(f"OptiKlean: Errore in should_run_cleaning: {str(e)}", xbmc.LOGERROR)
            return False


    def run_cleaning(cleaning_name, function, success_message):
        """Esegue una pulizia se è attiva e dovrebbe essere eseguita"""
        try:
            enabled = addon.getSettingBool(f"{cleaning_name}_enable")
            if not enabled:
                xbmc.log(f"OptiKlean: {cleaning_name} è disabilitato, salto pulizia", xbmc.LOGINFO)
                return False

            if should_run_cleaning(cleaning_name):
                xbmc.log(f"OptiKlean: Starting {cleaning_name} cleaning", xbmc.LOGINFO)

                if 'auto_mode' in function.__code__.co_varnames:
                    function(auto_mode=True)
                else:
                    function()

                update_last_run(cleaning_name)
                actions_executed.append(success_message)

                xbmc.log(f"OptiKlean: Completed {cleaning_name} cleaning", xbmc.LOGINFO)
                return True
            else:
                xbmc.log(f"OptiKlean: {cleaning_name} non necessario al momento", xbmc.LOGINFO)
                return False

        except Exception as e:
            xbmc.log(f"OptiKlean: Error during {cleaning_name}: {str(e)}", xbmc.LOGERROR)
            return False
    
    # Execute cleanings
    run_cleaning("clear_cache_and_temp", clear_cache_and_temp, "Cache/temp")
    run_cleaning("clear_unused_thumbnails", clear_unused_thumbnails, "Thumbnails")
    run_cleaning("clear_addon_leftovers", clear_addon_leftovers, "Addon leftovers")
    run_cleaning("clear_kodi_packages", clear_kodi_packages, "Packages")
    run_cleaning("optimize_databases", optimize_databases, "Databases")

    # Show notification if any action was executed
    if actions_executed:
        msg = "Auto-clean: " + ", ".join(actions_executed)
        xbmc.executebuiltin(f'Notification(OptiKlean, {msg}, 4000)')
        xbmc.log(f"OptiKlean: Completed cleanings - {msg}", xbmc.LOGINFO)
        
        # Aggiorna il log delle impostazioni dopo le pulizie
        try:
            update_automatic_settings_log()
        except Exception as e:
            xbmc.log(f"OptiKlean: Error updating settings log: {str(e)}", xbmc.LOGERROR)
    else:
        xbmc.log("OptiKlean: No cleanings required at this time", xbmc.LOGINFO)


# Gestione dei parametri per eseguire l'azione selezionata
if __name__ == '__main__':
    # Controlla per il parametro "autorun" da service.py (fallback)
    if len(sys.argv) > 1 and sys.argv[1] == 'autorun':
        xbmc.log("OptiKlean: Rilevato parametro autorun", xbmc.LOGINFO)
        run_automatic_maintenance()
    else:
        # Elaborazione normale dei parametri del menu
        params = {}
        if len(sys.argv) > 2 and sys.argv[2].startswith('?'):
            params = dict(pair.split('=') for pair in sys.argv[2][1:].split('&') if '=' in pair)
        action = params.get("action")
        
        if action == "clear_cache_and_temp":
            clear_cache_and_temp()
        elif action == "clear_unused_thumbnails":
            clear_unused_thumbnails()
        elif action == "clear_addon_leftovers":
            clear_addon_leftovers()
        elif action == "clear_kodi_packages":
            clear_kodi_packages()
        elif action == "optimize_databases":
            optimize_databases()
        elif action == "view_logs":
            view_logs()
        elif action == "show_support":
            show_support()
        else:
            show_menu()
