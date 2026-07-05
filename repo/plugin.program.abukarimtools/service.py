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
ADDON_PATH  = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFILE     = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
FLAG_FILE   = os.path.join(PROFILE, 'first_run.flag')

WELCOME_IMAGE = os.path.join(ADDON_PATH, 'resources', 'media', 'welcome.jpg')
# Kodi-native VFS path form — more reliable for ControlImage than an absolute
# OS path that may contain spaces (e.g. macOS "Application Support").
WELCOME_IMAGE_VFS = 'special://home/addons/%s/resources/media/welcome.jpg' % (
    ADDON.getAddonInfo('id'),)
WELCOME_SECONDS = 7

# Marker written once first-run has completed, so it can never repeat (this is
# what stops the skin's startup from re-triggering the whole sequence in a
# loop). A separate lock guards against two launches overlapping.
DONE_FILE = os.path.join(PROFILE, 'first_run.done')
LOCK_FILE = os.path.join(PROFILE, 'first_run.lock')

# Self-trigger: a new build apply replaces the addons/ folder wholesale, so a
# version string shipped INSIDE the addon is always fresh after an install.
# We compare it against a copy stored in addon_data; if they differ (or the
# addon_data copy is missing — e.g. wiped by the build's restore), a new build
# was applied and we (re)create the first-run flag. The wipe can only REMOVE
# LAST_BUILD_FILE, which makes first-run more likely to fire, never less, so the
# trigger is immune to the addon_data wipe.
BUILD_ID_FILE   = os.path.join(ADDON_PATH, 'resources', 'build.id')   # shipped
LAST_BUILD_FILE = os.path.join(PROFILE, 'last_build.id')              # addon_data

WIZARD_ID   = 'plugin.program.ABUKARIMwizard'

# How long (seconds) to wait for Kodi/wizard to settle before starting.
STARTUP_TIMEOUT = 180
# If the Home window still isn't visible after this many seconds (e.g. the
# CoreELEC first-boot wizard is on screen), start anyway instead of waiting
# the full STARTUP_TIMEOUT. macOS/normal boots start the moment Home appears,
# so this only affects the *ELEC 'takes forever' case.
STARTUP_GRACE = 30

# A LOCK_FILE older than this is treated as abandoned rather than "another
# run in progress". Nothing in _run_steps legitimately runs anywhere close to
# this long even counting the _wait_no_modal(timeout=600) worst case, so a
# lock still present past this ceiling means the process that wrote it died
# without reaching the finally block that clears it — a Kodi crash, kernel
# panic, or hard power-cycle mid-sequence, all of which this box is prone to.
# Without this, one interrupted run wedges every future automatic AND manual
# attempt forever, silently (see [AbukarimTools FirstRun] "lock present"
# repeating in the log with no user-visible symptom at all).
STALE_LOCK_SECONDS = 1800  # 30 minutes


def _lock_is_stale():
    """True if LOCK_FILE exists but is old enough to be an abandoned lock
    from an interrupted run rather than one that's genuinely still active."""
    try:
        age = time.time() - os.path.getmtime(LOCK_FILE)
    except OSError:
        return False  # doesn't exist -> not stale, just absent
    return age > STALE_LOCK_SECONDS


def _clear_stale_lock(context):
    """If LOCK_FILE is stale, remove it and log why. Returns True if a lock
    remains (still fresh, a run is genuinely in progress)."""
    if not os.path.exists(LOCK_FILE):
        return False
    if _lock_is_stale():
        age = time.time() - os.path.getmtime(LOCK_FILE)
        _log('%s: stale lock (%.0fs old) found — a previous run was likely '
             'interrupted (crash/reboot) before it could finish. Clearing '
             'it and proceeding.' % (context, age), xbmc.LOGWARNING)
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass
        return False
    return True


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

    # Already completed (e.g. skin reload re-fired the service) → stop.
    if os.path.exists(DONE_FILE):
        _log('First-run already completed (done marker present) — skipping.')
        try:
            os.remove(FLAG_FILE)
        except OSError:
            pass
        return
    if _clear_stale_lock('Automatic first-run'):
        _log('First-run already running (lock present) — skipping duplicate.')
        return

    try:
        with open(LOCK_FILE, 'w') as f:
            f.write('running')
    except OSError:
        pass

    # Remove the flag *before* running so the sequence is strictly one-shot
    # even if the user aborts Kodi half-way through.
    try:
        os.remove(FLAG_FILE)
    except OSError:
        pass

    try:
        _run_steps(monitor)
    finally:
        _mark_done()
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass

    # Reboot prompt LAST — only after the done marker is safely on disk, so a
    # user-approved reboot can never cut the completion record short and
    # re-trigger the sequence on the next boot.
    _prompt_reboot_if_coreelec(monitor)


def run_now(monitor=None, remove_flag=True, force=False):
    """Run the first-run steps immediately, skipping the boot-time wait.

    Guards against the loop where the skin's startup re-launches first-run on
    every skin load:
      • If first-run already completed (DONE_FILE exists) we refuse to run
        again unless force=True (the menu item passes force=True so the user
        can deliberately re-run setup).
      • A LOCK_FILE prevents two launches from overlapping.
    """
    if monitor is None:
        monitor = xbmc.Monitor()

    # Already completed → do nothing (this breaks the skin-startup loop).
    if not force and os.path.exists(DONE_FILE):
        _log('First-run already completed (done marker present) — skipping.')
        return

    # Another run in progress → do nothing, unless the caller is explicitly
    # forcing a retry (the menu item passes force=True) — in that case a
    # stuck lock is exactly the thing the user is trying to override, so
    # clear it unconditionally instead of deferring to it. Without force,
    # still honor a genuinely fresh lock but drop a stale/abandoned one.
    if force:
        if os.path.exists(LOCK_FILE):
            _log('Manual run forced — clearing existing lock '
                 '(stale or not) before proceeding.', xbmc.LOGWARNING)
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass
    elif _clear_stale_lock('Manual first-run'):
        _log('First-run already running (lock present) — skipping duplicate.')
        return

    try:
        with open(LOCK_FILE, 'w') as f:
            f.write('running')
    except OSError:
        pass

    if remove_flag:
        try:
            os.remove(FLAG_FILE)
        except OSError:
            pass

    _log('Manual run requested.')
    try:
        _run_steps(monitor)
    finally:
        # Mark complete (with the shipped build id) and release the lock.
        _mark_done()
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass

    # Same ordering rule as the automatic path: done marker first, reboot
    # prompt second.
    _prompt_reboot_if_coreelec(monitor)


class _WelcomeWindow(xbmcgui.WindowDialog):
    """Fullscreen welcome image shown at the start of first-run.

    Closes automatically after WELCOME_SECONDS, or immediately on any key /
    click so the user is never stuck waiting on it.
    """
    def __init__(self, image_path):
        super(_WelcomeWindow, self).__init__()
        # Fullscreen image (coordinates are in Kodi's 1280x720 skin space).
        img = xbmcgui.ControlImage(0, 0, 1280, 720, image_path,
                                   aspectRatio=0)
        self.addControl(img)

    def onAction(self, action):
        # Any Back/Select/nav key closes the splash early.
        self.close()


def _show_welcome(monitor):
    """Show the welcome image for WELCOME_SECONDS, then continue."""
    if monitor is None:
        monitor = xbmc.Monitor()

    _log('Welcome splash: preparing (image=%s).' % WELCOME_IMAGE)
    if not os.path.exists(WELCOME_IMAGE):
        _log('Welcome image not found, skipping splash: %s' % WELCOME_IMAGE)
        return

    win = None
    try:
        win = _WelcomeWindow(WELCOME_IMAGE_VFS)
        win.show()
        # Give Kodi a moment to actually draw the window before we start the
        # countdown — without this the dialog can open and close in the same
        # frame on slower / first-boot systems and never become visible.
        xbmc.sleep(300)
        _log('Welcome splash shown — holding for %ss.' % WELCOME_SECONDS)

        # Keep it up for the requested duration (abort early if Kodi quits).
        waited = 0
        while waited < WELCOME_SECONDS * 1000:
            if monitor.abortRequested():
                break
            xbmc.sleep(200)
            waited += 200
    except Exception:
        _log('Welcome splash failed:\n%s' % traceback.format_exc(), xbmc.LOGERROR)
    finally:
        try:
            if win is not None:
                win.close()
                del win
        except Exception:
            pass
        _log('Welcome splash closed.')


def _run_steps(monitor):
    _log('Starting first-run sequence.')

    # Welcome splash first — shown for a few seconds before setup begins.
    _show_welcome(monitor)

    _log('Step 1 — Binary Installer.')
    _step_binary_installer(monitor)

    _log('Step 2 — Restore popup.')
    _final_choice(monitor)

    _log('Step 3 — Apply Patches.')
    _wait_no_modal(monitor)
    _step_patcher(monitor)

    _log('Step 4 — Skin Installer (last).')
    _wait_no_modal(monitor)
    _step_skin_installer()

    _log('First-run sequence finished.')

    # NOTE: the CoreELEC reboot prompt is deliberately NOT here any more.
    # It is issued by the callers AFTER the done marker has been written —
    # the Reboot builtin races the finally block, and if the system went
    # down before DONE_FILE landed, the (now DONE-keyed) trigger would
    # re-run the whole sequence on the next boot.


def _is_coreelec():
    """True on a CoreELEC installation (same check the binary installer uses)."""
    if os.path.isdir('/etc/coreelec'):
        return True
    try:
        with open('/etc/os-release') as f:
            return any('coreelec' in line.lower() for line in f)
    except OSError:
        return False


def _prompt_reboot_if_coreelec(monitor):
    if not _is_coreelec():
        _log('Reboot prompt skipped (not CoreELEC).')
        return
    # Let the freshly-loaded skin settle before showing the dialog.
    if monitor.waitForAbort(10):
        return  # Kodi is shutting down anyway
    # Make sure no modal is in the way.
    _wait_no_modal(monitor)
    try:
        yes = xbmcgui.Dialog().yesno(
            ADDON_NAME,
            'تم إكمال الإعداد.\n'
            'يُنصح بإعادة التشغيل لإكمال تطبيق البناء.\n'
            'هل تريد إعادة التشغيل الآن؟\n\n'
            'Setup is complete. A reboot is recommended to finish '
            'applying your build. Reboot now?',
            nolabel='لاحقاً / Later', yeslabel='إعادة التشغيل / Reboot')
    except Exception as e:
        _log('Reboot dialog failed: %s' % e)
        return
    if yes:
        _log('User chose reboot — rebooting system.')
        xbmc.executebuiltin('Reboot')
    else:
        _log('User postponed reboot.')


def _read_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''


def _first_run_pending():
    """True if first-run has NOT completed for the currently shipped build.

    Returns (pending: bool, build_id: str). If no build.id ships with the
    addon we return (False, '') so behaviour is unchanged for builds that
    don't use this mechanism.

    The check is keyed off DONE_FILE, which stores the build id of the last
    COMPLETED first-run (written only after _run_steps finishes). This is what
    makes the trigger crash-resilient: the old code compared build.id against
    LAST_BUILD_FILE, which was recorded at ARM time — so a kernel panic /
    power-cycle mid-sequence (FLAG already consumed, DONE never written) left
    changed=False on every subsequent boot and first-run silently never ran
    again. Now an interrupted run simply re-arms on the next boot until a run
    actually completes.

    Legacy migration: pre-1.7.3.2 installs wrote the literal string 'done'
    into DONE_FILE and the build id into LAST_BUILD_FILE. If both match the
    old completed state, migrate DONE_FILE to the new format instead of
    re-running first-run on devices that already finished it.
    """
    build_id = _read_text(BUILD_ID_FILE)
    if not build_id:
        return False, ''
    done = _read_text(DONE_FILE)
    if done == build_id:
        return False, build_id
    if done == 'done' and _read_text(LAST_BUILD_FILE) == build_id:
        # Old-format completion for this same build — migrate, don't re-run.
        _mark_done(build_id)
        _log('Migrated legacy done marker for build %s.' % build_id)
        return False, build_id
    return True, build_id


def _mark_done(build_id=None):
    """Write DONE_FILE with the completed build id (repeat guard)."""
    if build_id is None:
        build_id = _read_text(BUILD_ID_FILE) or 'done'
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(DONE_FILE, 'w', encoding='utf-8') as f:
            f.write(build_id)
    except OSError as e:
        _log('Could not write done marker (%s) — first-run may re-arm on '
             'next boot.' % e, xbmc.LOGWARNING)


def _record_build(build_id):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(LAST_BUILD_FILE, 'w', encoding='utf-8') as f:
            f.write(build_id)
        _log('Recorded build id: %s' % build_id)
    except Exception as e:
        _log('Could not record build id: %s' % e)



# autostart.sh restore cleanup:
#
# backup_manager.py writes a one-shot block into /storage/.config/autostart.sh
# to restore guisettings.xml/oe_settings.xml on the next boot (Kodi can't
# write those itself mid-session — Kodi and CoreELEC's settings service both
# hold their own copies in memory and flush them back over any external edit).
#
# autostart.sh used to try to remove that block from itself via `sed -i`
# once it had run. That is unsafe: autostart.sh runs as a shell script, and
# rewriting the very file a shell is still reading from, from inside that
# same running script, is undefined territory on BusyBox ash (the shell used
# by CoreELEC) — it corrupted/deleted the file outright in practice.
#
# The safe fix: autostart.sh no longer touches itself at all. Cleanup happens
# here instead, in a completely different, later-starting process. By the
# time this Python code runs, autostart.sh (a boot-time init script) has
# already executed to completion and exited — it is not "the same running
# script" from Kodi's point of view, so deleting it here carries none of that
# risk. If it's present when Kodi starts, its one-shot job for this boot is
# already done, so it's always safe and correct to remove it now.
AUTOSTART_PATH   = '/storage/.config/autostart.sh'
AUTOSTART_MARKER = '# [abukarimtools] guisettings restore'


def _cleanup_stale_autostart():
    if not os.path.exists(AUTOSTART_PATH):
        return
    try:
        # errors='replace': the pre-1.7.3 sed self-edit bug could leave
        # autostart.sh with corrupted (non-UTF-8) bytes. A strict read then
        # raises UnicodeDecodeError — which is NOT an OSError — and before
        # this fix that exception escaped, killed the whole service process,
        # and the build.id first-run trigger further down in main() never
        # ran at all ("first run sometimes does not auto start").
        with open(AUTOSTART_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        _log('Could not read %s for cleanup: %s' % (AUTOSTART_PATH, e))
        return

    if AUTOSTART_MARKER not in content:
        # Present but not ours — leave it alone.
        return

    try:
        os.remove(AUTOSTART_PATH)
        _log('Removed one-shot %s after restore (safe: this runs from a '
             'separate process, after the script itself already finished '
             'executing).' % AUTOSTART_PATH)
    except OSError as e:
        _log('Could not remove %s: %s' % (AUTOSTART_PATH, e),
             xbmc.LOGWARNING)


def main():
    monitor = xbmc.Monitor()

    # The boot chore below is strictly best-effort: it is not allowed to
    # prevent the first-run trigger further down from being evaluated. It is
    # fenced so an unexpected exception is logged and skipped rather than
    # killing the service process.

    # Runs on every boot, unconditionally: autostart.sh's job (if it ran at
    # all this boot) is already finished by the time Kodi is up.
    try:
        _cleanup_stale_autostart()
    except Exception:
        _log('autostart cleanup crashed (ignored):\n%s'
             % traceback.format_exc(), xbmc.LOGERROR)

    # Self-trigger: arm first-run whenever the shipped build.id has no
    # matching COMPLETED marker (DONE_FILE). This covers both a fresh build
    # apply and a previous run that was interrupted (crash / power-cycle)
    # before it could finish — the old last_build.id comparison covered only
    # the former. Manual first_run.flag still works as before.
    pending, build_id = _first_run_pending()
    if pending:
        _log('First-run pending for build %s — arming.' % build_id)
        for stale in (DONE_FILE, LOCK_FILE):
            try:
                if os.path.exists(stale):
                    os.remove(stale)
            except Exception as e:
                _log('Could not clear %s: %s' % (stale, e))
        try:
            os.makedirs(PROFILE, exist_ok=True)
            open(FLAG_FILE, 'w').close()
        except Exception as e:
            _log('Could not create first-run flag: %s' % e)
        # Kept for logging/diagnostics only — completion is tracked in
        # DONE_FILE now, not here.
        _record_build(build_id)

    if not os.path.exists(FLAG_FILE):
        return                       # normal boot — nothing to do

    _log('First-run flag detected: %s' % FLAG_FILE)
    run_first_run_sequence(monitor)


if __name__ == '__main__':
    main()
