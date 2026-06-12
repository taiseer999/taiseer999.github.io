# -*- coding: utf-8 -*-
"""
service.py – ABUKARIM TOOLS first-run automation.

Runs as a Kodi service on every start. It only does something when the
one-shot flag file (shipped inside the build's userdata) is present:

    special://profile/addon_data/plugin.program.abukarimtools/first_run.flag

The flag is extracted together with the build, so it exists exactly once:
on the first Kodi start after a fresh build install. The service then:

    1. Waits for Kodi's home window and for the ABUKARIM wizard to finish
       its own first-run work (enable_addons / backup_gui_skin).
    2. Deletes the flag (guarantees the sequence never repeats).
    3. Opens the Skin Installer (resources/lib/skin_installer.py).
    4. Opens the Binary Installer (resources/lib/binary_installer.py).
    5. Shows a popup: Restore Backup / Auth Addons / Skip.
         - Restore     -> backup_manager.py restore flow
         - Auth Addons -> RunScript(script.module.acctmgr)
"""

import os
import time
import traceback

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON       = xbmcaddon.Addon()
ADDON_NAME  = 'ABUKARIM TOOLS'
PROFILE     = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
FLAG_FILE   = os.path.join(PROFILE, 'first_run.flag')

WIZARD_ID   = 'plugin.program.ABUKARIMwizard'
ACCTMGR_ID  = 'script.module.acctmgr'

# How long (seconds) to wait for Kodi/wizard to settle before starting.
STARTUP_TIMEOUT = 180


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools FirstRun] %s' % msg, level)


# --------------------------------------------------------------------------
# Readiness helpers
# --------------------------------------------------------------------------
def _wizard_first_run_done():
    """
    True when the ABUKARIM wizard has finished (or will not run) its own
    first-run routine, so our dialogs won't fight with its dialogs.
    """
    try:
        wiz = xbmcaddon.Addon(WIZARD_ID)
        return wiz.getSetting('firstrun') != 'true'
    except Exception:
        # Wizard not installed / not enabled -> nothing to wait for
        return True


def _addon_enabled(addon_id):
    return xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % addon_id)


def _wait_until_ready(monitor):
    """Wait for home window + wizard first-run completion (with timeout)."""
    waited = 0
    while not monitor.abortRequested() and waited < STARTUP_TIMEOUT:
        home_visible = xbmc.getCondVisibility('Window.IsVisible(home)')
        if home_visible and _wizard_first_run_done():
            # extra settle time so the wizard's notifications clear
            if monitor.waitForAbort(5):
                return False
            return True
        if monitor.waitForAbort(2):
            return False
        waited += 2
    # Timeout: continue anyway unless Kodi is shutting down
    return not monitor.abortRequested()


# --------------------------------------------------------------------------
# Sequence steps
# --------------------------------------------------------------------------
def _step_skin_installer():
    try:
        from resources.lib import skin_installer
        _log('Opening Skin Installer…')
        # first_run=True: the portal closes itself after a successful
        # install and the skin is applied after the modal is gone, so the
        # sequence continues automatically instead of waiting for the user
        # to press Back.
        skin_installer.run(first_run=True)
        return True
    except Exception:
        _log('Skin Installer failed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME,
                            'Skin Installer could not be started.\n'
                            'You can run it later from ABUKARIM TOOLS.')
        return False


def _wait_skin_settle(monitor, seconds=8):
    """Give ReloadSkin time to finish before opening the next dialog."""
    waited = 0
    while waited < seconds:
        if monitor.waitForAbort(1):
            return False
        waited += 1
        if not xbmc.getCondVisibility('Window.IsActive(busydialog)') and waited >= 4:
            break
    return True


def _wait_no_modal(monitor, timeout=600, stable=2):
    """
    Wait until NO modal dialog is on screen for `stable` consecutive
    seconds. After a skin is applied, other addons (e.g. TMDb Helper)
    may pop their own dialogs; opening ours on top of theirs gets ours
    instantly dismissed. So we politely wait for the screen to be clear
    (up to `timeout` seconds — the user may need time to answer them).
    """
    waited = 0
    clear = 0
    while not monitor.abortRequested() and waited < timeout:
        if xbmc.getCondVisibility('System.HasModalDialog'):
            if clear:
                _log('Waiting for foreign dialog to close before continuing…')
            clear = 0
        else:
            clear += 1
            if clear >= stable:
                return True
        if monitor.waitForAbort(1):
            return False
        waited += 1
    return not monitor.abortRequested()


def _step_binary_installer(monitor):
    try:
        from resources.lib import binary_installer
        for attempt in (1, 2):
            _wait_no_modal(monitor)
            _log('Opening Binary Installer… (attempt %d)' % attempt)
            started = time.time()
            binary_installer.run()   # shows its own confirm + progress + summary
            # If it came back almost instantly, our confirm dialog was most
            # likely swallowed by another addon's popup — wait and retry once.
            if time.time() - started > 2 or attempt == 2:
                break
            _log('Binary Installer dialog was dismissed instantly — retrying.')
        return True
    except Exception:
        _log('Binary Installer failed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME,
                            'Binary Installer could not be started.\n'
                            'You can run it later from ABUKARIM TOOLS.')
        return False


def _step_restore():
    try:
        from resources.lib import backup_manager
        _log('Opening Backup Manager (restore)…')
        bm     = backup_manager.BackupManager()
        dialog = xbmcgui.Dialog()
        include_skin = bm._ask_skin_addons(dialog)
        bm._do_restore(dialog, include_skin)
    except Exception:
        _log('Restore failed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME,
                            'Restore could not be started.\n'
                            'You can run it later from ABUKARIM TOOLS → Backup/Restore.')


def _step_auth_addons():
    _log('Launching Account Manager…')
    if not _addon_enabled(ACCTMGR_ID):
        # try to enable it first (it ships with the build but may be disabled)
        xbmc.executebuiltin('EnableAddon(%s)' % ACCTMGR_ID)
        xbmc.sleep(2000)
    xbmc.executebuiltin('RunScript(%s)' % ACCTMGR_ID)
    # RunScript is asynchronous — give the Account Manager a few seconds to
    # open its window so the next step's no-modal wait holds until the user
    # is done with it.
    xbmc.sleep(5000)


def _final_choice(monitor):
    """Popup: Restore Backup / Auth Addons / Skip."""
    # yesnocustom returns: 1 = yes, 0 = no, 2 = custom, -1 = back/cancel
    choice = -1
    for attempt in (1, 2, 3):
        _wait_no_modal(monitor)
        started = time.time()
        choice = xbmcgui.Dialog().yesnocustom(
            ADDON_NAME,
            'Setup is almost complete.\n\n'
            'Would you like to restore a previous backup, '
            'or authorize your accounts (Trakt / Debrid)?',
            customlabel='Skip',
            nolabel='Auth Addons',
            yeslabel='Restore Backup',
            defaultbutton=xbmcgui.DLG_YESNO_YES_BTN,
        )
        # An answer in under 1.5 s almost certainly means our dialog was
        # swallowed by another addon's popup — wait for the screen to clear
        # and ask again.
        if time.time() - started > 1.5:
            break
        _log('Restore/Auth popup was dismissed instantly — retrying.')
    if choice == 1:
        _step_restore()
    elif choice == 0:
        _step_auth_addons()
    else:
        _log('User skipped restore/auth step.')


# --------------------------------------------------------------------------
def run_first_run_sequence(monitor):
    if not _wait_until_ready(monitor):
        _log('Kodi shutting down before sequence could start — flag kept '
             'so it will run on next boot.')
        return

    # Remove the flag *before* running so the sequence is strictly one-shot
    # even if the user aborts Kodi half-way through.
    try:
        os.remove(FLAG_FILE)
    except OSError:
        pass

    _log('Starting first-run sequence.')

    _log('Step 1 — Binary Installer.')
    _step_binary_installer(monitor)

    _log('Step 2 — Restore/Auth popup.')
    _final_choice(monitor)

    _log('Step 3 — Skin Installer (last).')
    _wait_no_modal(monitor)
    _step_skin_installer()

    _log('First-run sequence finished.')


def main():
    monitor = xbmc.Monitor()

    if not os.path.exists(FLAG_FILE):
        return                       # normal boot — nothing to do

    _log('First-run flag detected: %s' % FLAG_FILE)
    run_first_run_sequence(monitor)


if __name__ == '__main__':
    main()
