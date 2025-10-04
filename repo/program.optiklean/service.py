import os
import sys

import xbmc
import xbmcaddon
import xbmcvfs

try:
    from autoupdater import AutoUpdater
except ImportError as e:
    xbmc.log(f"OptiKlean: Fallita importazione autoupdater: {str(e)}", xbmc.LOGERROR)
    AutoUpdater = None

try:
    from default import run_automatic_maintenance, monitor_settings_changes
except ImportError as e:
    xbmc.log(f"OptiKlean: Errore nell'importare da default.py: {str(e)}", xbmc.LOGERROR)
    run_automatic_maintenance = None
    monitor_settings_changes = None

# Ottieni il percorso dell'addon e aggiungilo ai percorsi di sistema
addon = xbmcaddon.Addon()
addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
sys.path.append(addon_path)

# Path to addon_data for storing logs
addon_data_folder = xbmcvfs.translatePath(f"special://profile/addon_data/{addon.getAddonInfo('id')}/")


class OptiKleanMonitor(xbmc.Monitor):
    def __init__(self):
        super(OptiKleanMonitor, self).__init__()
        self.addon = xbmcaddon.Addon()
        self.startup_complete = False
        self.maintenance_executed = False
        self.updater = AutoUpdater() if AutoUpdater else None
        self.check_first_run()

    def check_first_run(self):
        """Controlla se qualsiasi opzione attiva non ha file JSON e attiva la manutenzione automatica se necessaria"""
        try:
            if run_automatic_maintenance is None:
                return

            cleaning_types = [
                "clear_cache_and_temp",
                "clear_unused_thumbnails",
                "clear_addon_leftovers",
                "clear_kodi_packages",
                "optimize_databases"
            ]

            needs_first_run = False

            for cleaning in cleaning_types:
                enabled = self.addon.getSettingBool(f"{cleaning}_enable")
                if not enabled:
                    continue

                last_run_file = os.path.join(
                    xbmcvfs.translatePath(self.addon.getAddonInfo('profile')),
                    f"last_{cleaning}.json"
                )

                if not xbmcvfs.exists(last_run_file):
                    xbmc.log(f"OptiKlean: Primo avvio rilevato per '{cleaning}' abilitato ma senza file JSON", xbmc.LOGINFO)
                    needs_first_run = True
                    break

            if needs_first_run:
                xbmc.log("OptiKlean: rilevato primo avvio per le opzioni abilitate", xbmc.LOGINFO)
                while not self.abortRequested() and not self.startup_complete:
                    if self.waitForAbort(5):
                        return

                if not self.abortRequested():
                    xbmc.log("OptiKlean: avvio prima manutenzione automatica", xbmc.LOGINFO)
                    run_automatic_maintenance()

        except Exception as e:
            xbmc.log(f"OptiKlean: Errore in check_first_run: {str(e)}", xbmc.LOGERROR)


    def onSettingsChanged(self):
        """Gestisci cambio impostazioni"""
        try:
            xbmc.log("OptiKlean: impostazioni cambiate", xbmc.LOGINFO)
            
            # Assicurati che la cartella del profilo esista
            if not xbmcvfs.exists(addon_data_folder):
                xbmcvfs.mkdirs(addon_data_folder)

            # Aggiorna subito lo stato delle impostazioni automatiche
            monitor_settings_changes()

            # Check if first run needed for newly enabled cleanings
            self.check_first_run()
            
        except Exception as e:
            xbmc.log(f"OptiKlean: Errore gestione impostazioni cambiate: {str(e)}", xbmc.LOGERROR)
    
    def onNotification(self, sender, method, data):
        xbmc.log(f"OptiKlean: Notifica ricevuta - {method}", xbmc.LOGDEBUG)
        
        if method == "GUI.OnScreensaverDeactivated" or method == "Player.OnPlay":
            self.startup_complete = True
            xbmc.log("OptiKlean: Avvio di Kodi completato", xbmc.LOGINFO)
        
        if method in ["VideoLibrary.OnScanFinished", "AudioLibrary.OnScanFinished"]:
            self.startup_complete = True
            xbmc.log("OptiKlean: Scansione libreria completata, Kodi è pronto", xbmc.LOGINFO)
            
        if method.startswith("VideoLibrary") or method.startswith("AudioLibrary"):
            self.startup_complete = True
            xbmc.log("OptiKlean: Attività database rilevata, Kodi è attivo", xbmc.LOGINFO)
            
        if method.startswith("Input") or method.startswith("GUI"):
            self.startup_complete = True
            xbmc.log("OptiKlean: Interazione utente rilevata", xbmc.LOGDEBUG)

def check_and_run_update(monitor):
    if (
        monitor.maintenance_executed
        and monitor.updater
        and monitor.updater._is_auto_update_enabled()
    ):
        xbmc.sleep(3000)
        if monitor.updater.check_and_update():
            xbmc.log("OptiKlean: Aggiornamento completato", xbmc.LOGINFO)

# Funzione principale del servizio
if __name__ == '__main__':
    xbmc.log("OptiKlean: Servizio avviato", xbmc.LOGINFO)
    
    monitor = OptiKleanMonitor()
    xbmc.sleep(5000)  # 5 secondi di attesa iniziale
    
    wait_time = 3
    idle_counter = 0
    
    while not monitor.abortRequested():
        xbmc.log(f"OptiKlean: Avvio completo: {monitor.startup_complete}, Manutenzione automatica eseguita: {monitor.maintenance_executed}", xbmc.LOGDEBUG)
        if monitor.waitForAbort(wait_time):
            break
        
        if not monitor.maintenance_executed:
            try:
                xbmc.sleep(2000)
                
                if not xbmc.Player().isPlaying():
                    xbmc.log("OptiKlean: Kodi è pronto, avvio della manutenzione automatica", xbmc.LOGINFO)
                    
                    if run_automatic_maintenance:
                        run_automatic_maintenance()
                    else:
                        xbmc.executebuiltin('RunScript(program.optiklean, autorun)')
                    
                    monitor.maintenance_executed = True
                    wait_time = 60
                    
                    check_and_run_update(monitor)

                else:
                    xbmc.log("OptiKlean: Riproduzione in corso, riprogrammo la pulizia", xbmc.LOGINFO)
                    idle_counter += 1
                    if idle_counter > 10:
                        xbmc.log("OptiKlean: Timeout attesa inattività, eseguo comunque", xbmc.LOGINFO)
                        if run_automatic_maintenance:
                            run_automatic_maintenance()
                        else:
                            xbmc.executebuiltin('RunScript(program.optiklean, autorun)')
                        monitor.maintenance_executed = True
                        wait_time = 60
                        
                        check_and_run_update(monitor)

            except Exception as e:
                xbmc.log(f"OptiKlean: Errore durante la manutenzione automatica: {str(e)}", xbmc.LOGERROR)
                monitor.maintenance_executed = True
                wait_time = 60

    xbmc.log("OptiKlean: Servizio terminato", xbmc.LOGINFO)
