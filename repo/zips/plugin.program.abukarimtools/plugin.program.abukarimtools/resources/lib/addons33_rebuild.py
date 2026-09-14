# -*- coding: utf-8 -*-
"""
addons33_rebuild.py – ABUKARIM TOOLS

Guided rebuild of Kodi's add-on database (Addons33.db).

Why this exists
---------------
On this build Addons33.db keeps coming up at boot as
    "Can't update database Addons33 from version 0 - it's too old"
A corrupt/too-old add-on DB at boot can stop Kodi registering and auto-starting
services — including this add-on's own xbmc.service, which is where the
background auto-patch watchdog lives. When the service never starts, patches
only re-apply when ABUKARIM TOOLS is opened by hand (the menu self-heal), i.e.
"no autopatching".

Deleting the corrupt DB lets Kodi build a clean one. The catch the user flagged:
a fresh rebuild can leave add-ons disabled until they are re-enabled. So this
module automates the whole cycle rather than leaving the box half-configured:

    Phase 1  (user taps "Rebuild Add-on Database"):
        confirm  ->  delete Addons33.db (+ -wal/-shm)  ->  mark step=2  ->  reboot

    Phase 2  (next boot: Kodi has already rebuilt a fresh Addons33.db):
        continue_if_pending() runs from the service AND, as a fallback, when the
        menu is opened  ->  enable every installed add-on (JSON-RPC)  ->  clear
        the marker  ->  reboot once more so the freshly-registered services
        (this add-on's watchdog included) start clean.

Worst case: if the rebuild leaves THIS add-on disabled too, neither its service
nor its menu can run, so phase 2 cannot self-continue. The user then only has to
re-enable ABUKARIM TOOLS once (My add-ons) — opening it, or the next boot,
finishes the rest automatically. That is documented in the confirm dialog.
"""

import json
import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

ADDON       = xbmcaddon.Addon('plugin.program.abukarimtools')
ADDON_NAME  = 'ABUKARIM TOOLS'
ADDON_ICON  = xbmcvfs.translatePath(ADDON.getAddonInfo('icon'))
PROFILE     = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
MARKER      = os.path.join(PROFILE, 'addons33_rebuild.step')

# CoreELEC one-shot: the DB must be deleted BEFORE Kodi starts, because Kodi
# holds Addons33.db open for the whole session and rewrites it during shutdown
# — deleting it from inside a running Kodi does not reliably survive the
# reboot. autostart.sh runs before Kodi, so the delete there always sticks.
#
# The block does NOT remove itself: rewriting a running shell script's own file
# mid-read is unsafe on BusyBox ash and has corrupted autostart.sh here before
# (see backup_manager._inject_autostart_restore). Instead it is guarded by a
# TRIGGER FILE and deletes only that, so a block left behind for any reason is
# inert on every later boot. The block text itself is removed from Python in
# phase 2, from a separate process, long after the script has exited.
AUTOSTART_PATH   = '/storage/.config/autostart.sh'
AUTOSTART_MARKER = '# [abukarimtools] addons33 rebuild'
TRIGGER_FILE     = '/storage/.addons33_rebuild_pending'

# Set once per Kodi session so a phase-2 continuation can never run twice (e.g.
# the service starts it and the user also opens the menu before the reboot).
_CONTINUE_STARTED = False


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Addons33] %s' % msg, level)


def _notify(message, seconds=6000):
    try:
        xbmcgui.Dialog().notification(ADDON_NAME, message, ADDON_ICON, seconds)
    except Exception:
        pass


# ---------------------------------------------------------------------------
def _is_coreelec():
    """True on a *ELEC box (reboots the OS) vs a desktop dev install (quits)."""
    if os.path.isdir('/storage/.kodi'):
        return True
    try:
        return xbmcvfs.translatePath('special://home/').startswith('/storage/')
    except Exception:
        return False


def _restart():
    """Restart the box (CoreELEC) or quit Kodi (desktop)."""
    if _is_coreelec():
        xbmc.executebuiltin('Reboot')
    else:
        xbmc.executebuiltin('Quit')


def _db_dir():
    return xbmcvfs.translatePath('special://database/')


def _addons33_files():
    """All Addons33.* files (the DB plus any -wal/-shm sidecars)."""
    out = []
    d = _db_dir()
    try:
        for name in os.listdir(d):
            low = name.lower()
            if low.startswith('addons33') and (
                    low.endswith('.db') or low.endswith('.db-wal')
                    or low.endswith('.db-shm')):
                out.append(os.path.join(d, name))
    except Exception as e:
        _log('Could not list database dir %s: %s' % (d, e), xbmc.LOGWARNING)
    return out


def _inject_autostart_delete():
    """Append the one-shot Addons33 delete block to autostart.sh (CoreELEC).

    Returns True when the block is in place (already present counts as
    success). The real database directory is resolved now and baked into the
    script so a non-default userdata path still works.
    """
    db_glob = os.path.join(_db_dir(), 'Addons33.db')
    block = (
        '\n%(marker)s\n'
        'if [ -f "%(trigger)s" ]; then\n'
        '    rm -f "%(db)s" "%(db)s-wal" "%(db)s-shm"\n'
        '    rm -f "%(trigger)s"\n'
        'fi\n'
    ) % {'marker': AUTOSTART_MARKER, 'trigger': TRIGGER_FILE, 'db': db_glob}

    try:
        with open(AUTOSTART_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except IOError:
        content = '#!/bin/sh\n'
    except Exception as e:
        _log('Could not read %s: %s' % (AUTOSTART_PATH, e), xbmc.LOGWARNING)
        return False

    try:
        if AUTOSTART_MARKER not in content:
            os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
            with open(AUTOSTART_PATH, 'w', encoding='utf-8') as f:
                f.write(content.rstrip('\n') + block)
            _log('Injected Addons33 delete block into %s' % AUTOSTART_PATH)
        else:
            _log('Addons33 delete block already present in %s' % AUTOSTART_PATH)
        try:
            os.chmod(AUTOSTART_PATH, 0o755)
        except Exception:
            pass
        # Arm the trigger: without it the block is a no-op.
        with open(TRIGGER_FILE, 'w', encoding='utf-8') as f:
            f.write('addons33\n')
        return True
    except Exception as e:
        _log('Could not write autostart block: %s' % e, xbmc.LOGERROR)
        return False


def cleanup_autostart_block():
    """Remove our one-shot block from autostart.sh, leaving anything else.

    Safe to call any time: this runs from Python, in a separate process, after
    autostart.sh has already finished executing for this boot. If our block is
    the only content left, the file is removed entirely.
    """
    if not os.path.exists(AUTOSTART_PATH):
        return
    try:
        with open(AUTOSTART_PATH, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        _log('Could not read %s for cleanup: %s' % (AUTOSTART_PATH, e),
             xbmc.LOGWARNING)
        return

    if AUTOSTART_MARKER not in content:
        return

    # Drop from our marker up to the closing 'fi' of our block.
    head, _, tail = content.partition(AUTOSTART_MARKER)
    _, _, after = tail.partition('\nfi\n')
    remainder = (head.rstrip('\n') + '\n' + after.lstrip('\n')).strip()

    try:
        if remainder in ('', '#!/bin/sh'):
            os.remove(AUTOSTART_PATH)
            _log('Removed %s (our block was its only content).' % AUTOSTART_PATH)
        else:
            with open(AUTOSTART_PATH, 'w', encoding='utf-8') as f:
                f.write(remainder + '\n')
            _log('Removed Addons33 delete block from %s' % AUTOSTART_PATH)
    except Exception as e:
        _log('Could not clean %s: %s' % (AUTOSTART_PATH, e), xbmc.LOGWARNING)

    try:
        if os.path.exists(TRIGGER_FILE):
            os.remove(TRIGGER_FILE)
    except Exception:
        pass


def _run_origin_fix():
    """Repair empty add-on origin fields after the rebuild.

    A freshly built Addons33.db loses the origin column for locally installed
    add-ons, which is exactly what origin_fix repairs. Best-effort: never
    allowed to break the rebuild.
    """
    try:
        from resources.lib import origin_fix
        res = origin_fix.fix_addons()
        if res.get('error'):
            _log('Origin fix reported: %s' % res['error'], xbmc.LOGWARNING)
        else:
            _log('Origin fix: %d origin(s) repaired, %d unmatched.'
                 % (len(res.get('fixed') or {}), len(res.get('unmatched') or [])))
        return res
    except Exception as e:
        _log('Origin fix crashed (ignored): %s' % e, xbmc.LOGERROR)
        return None


def _read_step():
    try:
        with open(MARKER, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''


def _write_step(step):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(MARKER, 'w', encoding='utf-8') as f:
            f.write(step)
        return True
    except Exception as e:
        _log('Could not write marker: %s' % e, xbmc.LOGWARNING)
        return False


def _clear_step():
    try:
        if os.path.exists(MARKER):
            os.remove(MARKER)
    except Exception:
        pass


def _settle(monitor, seconds):
    """Sleep that respects an abort request when a Monitor is available."""
    if monitor is not None:
        monitor.waitForAbort(seconds)
    else:
        xbmc.sleep(int(seconds * 1000))


def _enable_all_addons():
    """Enable every installed-but-disabled add-on via JSON-RPC.

    Two passes: enabling an add-on whose dependency is still disabled can fail
    the first time, so a second sweep mops those up. Returns (enabled, failed).
    """
    enabled = failed = 0
    for _pass in range(2):
        try:
            req = {'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.GetAddons',
                   'params': {'enabled': False, 'properties': ['name']}}
            res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
            addons = res.get('result', {}).get('addons', []) or []
        except Exception as e:
            _log('GetAddons failed: %s' % e, xbmc.LOGWARNING)
            break
        if not addons:
            break
        for a in addons:
            aid = a.get('addonid')
            if not aid:
                continue
            try:
                er = {'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled',
                      'params': {'addonid': aid, 'enabled': True}}
                r = json.loads(xbmc.executeJSONRPC(json.dumps(er)))
                if 'error' in r:
                    failed += 1
                else:
                    enabled += 1
            except Exception:
                failed += 1
    return enabled, failed


# ---------------------------------------------------------------------------
def run():
    """Phase 1: schedule the rebuild, then restart into it.

    On CoreELEC the delete is handed to autostart.sh so it happens BEFORE Kodi
    opens the database. Elsewhere (macOS dev box) there is no autostart.sh, so
    fall back to deleting in-process and tell the user to reopen Kodi — Kodi
    does not relaunch itself there.
    """
    dlg = xbmcgui.Dialog()
    if not dlg.yesno(ADDON_NAME, T(30330), yeslabel=T(30051), nolabel=T(30052)):
        return

    if _is_coreelec():
        if not _inject_autostart_delete():
            dlg.ok(ADDON_NAME, T(30335))
            return
        _write_step('2')
        _log('Phase 1: delete scheduled via autostart.sh. Rebooting.')
        dlg.ok(ADDON_NAME, T(30331))
        _restart()
        return

    # --- non-CoreELEC fallback (dev machines) ---
    files = _addons33_files()
    if not files:
        if dlg.yesno(ADDON_NAME, T(30334), yeslabel=T(30051), nolabel=T(30052)):
            _write_step('2')
            _notify_manual_restart(dlg)
        return

    removed = 0
    for f in files:
        try:
            os.remove(f)
            removed += 1
            _log('Deleted %s' % f)
        except Exception as e:
            _log('Could not delete %s: %s' % (f, e), xbmc.LOGWARNING)

    if not removed:
        dlg.ok(ADDON_NAME, T(30335))
        return

    _write_step('2')
    _log('Phase 1 (fallback): deleted %d Addons33 file(s).' % removed)
    _notify_manual_restart(dlg)


def _notify_manual_restart(dlg):
    """Kodi cannot relaunch itself off CoreELEC — say so before quitting.

    Previously this path called Quit silently, so Kodi just disappeared and the
    rebuild looked broken even when the delete had worked.
    """
    dlg.ok(ADDON_NAME, T(30336))
    xbmc.executebuiltin('Quit')


def continue_if_pending(monitor=None):
    """Phase 2: after the rebuild reboot, enable all add-ons, repair origins,
    clean up the one-shot, then restart.

    Safe to call from the service on boot and from the menu on open; runs at
    most once per session and no-ops unless a rebuild is mid-flight.
    """
    global _CONTINUE_STARTED
    if _CONTINUE_STARTED:
        return False
    if _read_step() != '2':
        return False
    _CONTINUE_STARTED = True

    _log('Phase 2: Addons33 rebuilt - re-enabling all add-ons.')
    _notify(T(30332))
    # Give Kodi time to finish rebuilding the DB and scanning add-ons.
    _settle(monitor, 20)

    enabled, failed = _enable_all_addons()
    _log('Phase 2: enabled %d add-on(s), %d could not be enabled.'
         % (enabled, failed))

    # Let the enable writes land before touching the DB directly.
    _settle(monitor, 3)

    # A fresh Addons33.db has empty origin fields, so updates would not resolve
    # back to their repo. Repair them now, while we still have a restart coming
    # anyway (origin_fix writes to the DB; Kodi picks it up on the next start).
    _run_origin_fix()

    _clear_step()
    cleanup_autostart_block()
    _settle(monitor, 2)
    _log('Phase 2 complete - restarting into the clean database.')
    _restart()
    return True
