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
    3. Runs the Binary Installer silently (resources/lib/binary_installer.py).
    4. Shows a popup: Restore Backup / Skip.
         - Restore -> backup_manager.py restore flow
    5. Opens the Skin Installer last (resources/lib/skin_installer.py).
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

# How long (seconds) to wait for Kodi/wizard to settle before starting.
STARTUP_TIMEOUT = 240


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools FirstRun] %s' % msg, level)


# --------------------------------------------------------------------------
# Readiness helpers
# --------------------------------------------------------------------------
def _home_ready(monitor, stable_secs=3):
    """True once the Home window has been visible AND no modal dialog is up
    for `stable_secs` consecutive seconds.

    This is the reliable 'the boot wizards are done and we're sitting on the
    home screen' signal: while the CoreELEC/LibreELEC first-boot wizard (or any
    other startup dialog) is on screen, Home is not the active visible window,
    so we simply wait for Home to be stably visible and clear.
    """
    clear = 0
    while not monitor.abortRequested() and clear < stable_secs:
        home = xbmc.getCondVisibility('Window.IsVisible(home)')
        modal = xbmc.getCondVisibility('System.HasModalDialog')
        if home and not modal:
            clear += 1
        else:
            clear = 0
        if monitor.waitForAbort(1):
            return False
    return not monitor.abortRequested()


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
    """Wait until we're sitting on a clear Home screen with the ABUKARIM wizard
    finished.

    Returns:
        'ready'    -> safe to run now
        'abort'    -> Kodi is shutting down
        'timeout'  -> waited the maximum but never reached a clear home screen
    """
    waited = 0
    while not monitor.abortRequested() and waited < STARTUP_TIMEOUT:
        if xbmc.getCondVisibility('Window.IsVisible(home)') \
                and not xbmc.getCondVisibility('System.HasModalDialog') \
                and _wizard_first_run_done():
            # Confirm it stays clear for a few seconds (wizard fully gone),
            # then a short settle so any closing animation / notification ends.
            if _home_ready(monitor, stable_secs=3):
                if monitor.waitForAbort(3):
                    return 'abort'
                return 'ready'
        if monitor.waitForAbort(2):
            return 'abort'
        waited += 2
    if monitor.abortRequested():
        return 'abort'
    return 'timeout'


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
        _log('Running Binary Installer (auto, no prompt)…')
        # auto=True: installs inputstream.adaptive / vfs.libarchive silently —
        # progress bar + finishing notification only, no confirmation dialog.
        binary_installer.run(auto=True)
        return True
    except Exception:
        _log('Binary Installer failed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'Binary installer failed — run it from ABUKARIM TOOLS',
                                      xbmcgui.NOTIFICATION_ERROR, 6000)
        return False


def _step_restore():
    """Run the restore flow. Returns True only after restore fully finishes."""
    try:
        from resources.lib import backup_manager
        _log('Opening Backup Manager (restore)…')
        bm     = backup_manager.BackupManager()
        dialog = xbmcgui.Dialog()
        include_skin = bm._ask_skin_addons(dialog)
        bm._do_restore(dialog, include_skin)
        _log('Backup Manager restore flow returned.')
        return True
    except Exception:
        _log('Restore failed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME,
                            'Restore could not be started.\n'
                            'You can run it later from ABUKARIM TOOLS → Backup/Restore.')
        return False


def _final_choice(monitor):
    """Popup: Restore Backup / Skip. Returns True if a restore was performed."""
    choice = False
    for attempt in (1, 2, 3):
        _wait_no_modal(monitor)
        started = time.time()
        choice = xbmcgui.Dialog().yesno(
            ADDON_NAME,
            'Setup is almost complete.\n\n'
            'Would you like to restore a previous backup?',
            yeslabel='Restore Backup',
            nolabel='Skip',
        )
        # An answer in under 1.5 s almost certainly means our dialog was
        # swallowed by another addon's popup — wait for the screen to clear
        # and ask again.
        if time.time() - started > 1.5:
            break
        _log('Restore popup was dismissed instantly — retrying.')
    if choice:
        return _step_restore()
    _log('User skipped the restore step.')
    return False


# --------------------------------------------------------------------------
def run_first_run_sequence(monitor):
    status = _wait_until_ready(monitor)
    if status == 'abort':
        _log('Kodi shutting down before sequence could start — flag kept '
             'so it will run on next boot.')
        return
    if status == 'timeout':
        # Never reached a clean home screen within the wait window. Proceed
        # anyway (the modal-aware waits inside each step will still avoid
        # fighting other dialogs) rather than deferring forever.
        _log('Home screen not confirmed clear after %ss — proceeding anyway.'
             % STARTUP_TIMEOUT)

    # Remove the flag *before* running so the sequence is strictly one-shot
    # even if the user aborts Kodi half-way through.
    try:
        os.remove(FLAG_FILE)
    except OSError:
        pass

    _log('Starting first-run sequence.')

    _log('Step 1 — Binary Installer.')
    _step_binary_installer(monitor)
    # Binary installer runs its own progress dialog; make sure it and any
    # Kodi install prompts are fully gone before we move on.
    _wait_no_modal(monitor, stable=3)

    _log('Step 2 — Restore popup.')
    restored = _final_choice(monitor)

    # Critical: the Skin Installer must NEVER open until the restore step has
    # completely finished. Restore opens file-browse + confirm dialogs and
    # writes files; opening the skin portal on top of that corrupts both
    # flows. Wait for the screen to be clear and stable, with a longer settle
    # when a restore actually ran.
    if restored:
        _log('Restore performed — waiting for it to settle before skin step.')
        _wait_no_modal(monitor, stable=4)
        # extra fixed settle for disk writes / addon refresh to finish
        if not monitor.waitForAbort(5):
            pass
    else:
        _wait_no_modal(monitor, stable=3)

    _log('Step 3 — Skin Installer (last).')
    _wait_no_modal(monitor, stable=3)
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
