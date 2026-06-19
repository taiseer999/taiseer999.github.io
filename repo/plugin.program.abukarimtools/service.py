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
STARTUP_TIMEOUT = 180
# If the Home window still isn't visible after this many seconds (e.g. the
# CoreELEC first-boot wizard is on screen), start anyway instead of waiting
# the full STARTUP_TIMEOUT. macOS/normal boots start the moment Home appears,
# so this only affects the *ELEC 'takes forever' case.
STARTUP_GRACE = 30


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
    """Decide when it's safe to start the first-run sequence.

    Fast path (macOS / normal boot): start as soon as the Home window is
    visible and the ABUKARIM wizard has finished — usually only a few seconds.

    CoreELEC/LibreELEC: on a fresh box the *ELEC first-boot wizard owns the
    screen, so Home never reports visible for a long time and the old code sat
    here for the full STARTUP_TIMEOUT (that's the 'takes forever to start').
    To avoid that, we also start after a short GRACE period even if Home isn't
    detected — the sequence's own per-step modal waits keep it from colliding
    with anything still on screen.
    """
    waited = 0
    _log('Waiting for system to settle before first-run (grace=%ss, '
         'max=%ss)…' % (STARTUP_GRACE, STARTUP_TIMEOUT))
    while not monitor.abortRequested() and waited < STARTUP_TIMEOUT:
        home_visible = xbmc.getCondVisibility('Window.IsVisible(home)')
        if home_visible and _wizard_first_run_done():
            # Fast path (macOS / normal boot): wizard already done and we're on
            # the home screen — start right away after a short settle.
            _log('Home screen ready — starting first-run now.')
            if monitor.waitForAbort(5):
                return False
            return True
        # Fallback for CoreELEC/LibreELEC: the ABUKARIM build wizard can run a
        # long first-boot routine, and Home stays hidden behind it, so neither
        # condition above becomes true for a long time. After the grace period,
        # start anyway. We no longer require the wizard to report 'done' here —
        # the sequence's own per-step modal waits keep it from colliding with
        # any wizard dialog still on screen, and it stops the skin step from
        # being blocked indefinitely.
        if waited >= STARTUP_GRACE:
            _log('Grace period (%ss) elapsed without a clear home screen — '
                 'starting the first-run sequence anyway.' % STARTUP_GRACE)
            if monitor.waitForAbort(2):
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
def _step_patcher(monitor):
    try:
        from resources.lib import patcher
        _log('Applying patches…')
        patcher.run()
        return True
    except Exception:
        _log('Patcher failed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            'Apply Patches failed — run it from ABUKARIM TOOLS',
            xbmcgui.NOTIFICATION_ERROR, 6000)
        return False


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


def _final_choice(monitor):
    """Popup: Restore Backup / Skip."""
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
        _step_restore()
    else:
        _log('User skipped the restore step.')


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

    _run_steps(monitor)


def run_now(monitor=None, remove_flag=True):
    """Run the first-run steps immediately, skipping the boot-time wait.

    This is what the manual shortcut (run.py) calls. It does NOT wait for the
    home screen / wizard — the user has chosen to run it on purpose — and by
    default it also clears the one-shot flag so a later boot won't repeat it.
    """
    if monitor is None:
        monitor = xbmc.Monitor()
    if remove_flag:
        try:
            os.remove(FLAG_FILE)
        except OSError:
            pass
    _log('Manual run requested.')
    _run_steps(monitor)


def _run_steps(monitor):
    _log('Starting first-run sequence.')

    _log('Step 1 — Binary Installer.')
    _step_binary_installer(monitor)

    _log('Step 2 — Restore popup.')
    _final_choice(monitor)

    _log('Step 3 — Apply Patches.')
    _wait_no_modal(monitor)
    _step_patcher(monitor)

    _log('First-run sequence finished.')


def main():
    monitor = xbmc.Monitor()

    if not os.path.exists(FLAG_FILE):
        return                       # normal boot — nothing to do

    _log('First-run flag detected: %s' % FLAG_FILE)
    run_first_run_sequence(monitor)


if __name__ == '__main__':
    main()
