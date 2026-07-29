# -*- coding: utf-8 -*-
"""
patch_watchdog.py – ABUKARIM TOOLS

Keeps the patcher's work alive automatically.

A Kodi add-on update replaces the add-on folder wholesale, so every patch we
applied to that add-on is gone the moment it updates — until now the user had
to remember to open ABUKARIM TOOLS → Apply Patches by hand.

Kodi exposes no Python-visible "add-on was updated" event (xbmc.Monitor only
forwards the JSON-RPC notification set, which has no add-on install/update
member), so this is a cheap poller instead:

    * every POLL_SECONDS, stat() addon.xml of each add-on that PATCHES targets
      and read its version — that is 6 stat() calls, no file reads at all
    * when a signature changes, wait for the folder to stop changing (an
      update is still unpacking for a second or two), then re-run ONLY that
      add-on's patch entries, silently
    * every FULL_VERIFY_SECONDS, run the whole default patch set anyway as a
      belt-and-braces sweep — every entry is idempotent (already_patched_check)
      so a verify pass that finds nothing wrong writes nothing

State lives in addon_data/plugin.program.abukarimtools/patch_state.json. If it
is missing or unreadable the first pass simply treats everything as changed,
which is harmless: patching is idempotent.

Only the DEFAULT (ungrouped) patch set is auto-applied. Optional groups such
as 'redlight' stay manual by design — they are a user choice, not a fix, and
silently re-applying an opt-in patch after an update would be a surprise.
"""

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.i18n import T
import xbmcvfs

from resources.lib import patcher

ADDON       = xbmcaddon.Addon()
ADDON_NAME  = 'ABUKARIM TOOLS'
ADDON_ICON  = xbmcvfs.translatePath(ADDON.getAddonInfo('icon'))
PROFILE     = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
STATE_FILE  = os.path.join(PROFILE, 'patch_state.json')
ADDONS_DIR  = os.path.join(xbmcvfs.translatePath('special://home/'), 'addons')

# Kill switch: create this file to stop auto-patching without uninstalling.
DISABLE_FILE = os.path.join(PROFILE, 'autopatch.off')

POLL_SECONDS        = 30      # signature check — stat() only
SETTLE_SECONDS      = 5       # gap between stability probes after a change
SETTLE_MAX_SECONDS  = 120     # give up waiting for a folder to go quiet
FULL_VERIFY_SECONDS = 1800    # 30 min belt-and-braces sweep
BOOT_DELAY_SECONDS  = 60      # let Kodi's own startup add-on updates finish


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools AutoPatch] %s' % msg, level)


def _notify(message, seconds=6000):
    try:
        xbmcgui.Dialog().notification(ADDON_NAME, message, ADDON_ICON, seconds)
    except Exception:
        pass


# ---------------------------------------------------------------------------
_MISSING_ADDONS = set()   # ids Kodi has already told us it does not know


def _addon_path(addon_id):
    """Resolve an add-on's folder, preferring Kodi's own registry.

    Ordering matters for the log, not just for speed.  xbmcaddon.Addon() on an
    id Kodi does not know writes "EXCEPTION: Unknown addon id '<x>'" into
    kodi.log from the C++ side *before* the Python exception reaches our
    except: clause, so catching it is not enough to keep the log clean.  With a
    30s poll and two uninstalled targets that was ~2 lines every sweep, which
    buries real errors.

    So: try the standard folder first (cheap, silent, and the answer in almost
    every case), and only consult the registry when it is absent - that still
    covers portable installs and non-default addon directories.  Once Kodi has
    disowned an id, remember it and stop asking, so a genuinely missing add-on
    costs one log line per session instead of one per sweep.
    """
    local = os.path.join(ADDONS_DIR, addon_id)
    if os.path.isdir(local):
        return local
    if addon_id in _MISSING_ADDONS:
        return None
    try:
        path = xbmcaddon.Addon(addon_id).getAddonInfo('path')
        path = xbmcvfs.translatePath(path)
        if path and os.path.isdir(path):
            return path
    except Exception:
        pass
    _MISSING_ADDONS.add(addon_id)
    return None


def _signature(addon_id):
    """Cheap fingerprint of an installed add-on.

    version + addon.xml size/mtime. An update, a downgrade and a same-version
    reinstall all rewrite addon.xml, so all three are caught; nothing else
    touches it, so idle boxes never trigger a pass.

    Returns None when the add-on is not installed (or is mid-uninstall) — a
    missing target is not an error, the patch entry for it just no-ops.
    """
    path = _addon_path(addon_id)
    if not path:
        return None

    version = ''
    try:
        version = xbmcaddon.Addon(addon_id).getAddonInfo('version') or ''
    except Exception:
        version = ''

    try:
        st = os.stat(os.path.join(path, 'addon.xml'))
    except OSError:
        return None

    return '%s|%d|%d' % (version, st.st_size, st.st_mtime_ns)


def _signatures(addon_ids):
    return {a: _signature(a) for a in addon_ids}


def _load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        tmp = STATE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, sort_keys=True)
        os.replace(tmp, STATE_FILE)          # atomic: never a half-written state
    except Exception as e:
        _log('Could not write state file: %s' % e, xbmc.LOGWARNING)


def _wait_until_settled(monitor, addon_ids):
    """Block until the given add-ons' signatures stop moving.

    Kodi unpacks an update into the live folder, so the instant we notice a
    change the files may still be arriving. Patching mid-unpack would either
    fail to find the target string or be overwritten a second later.
    """
    waited = 0
    previous = _signatures(addon_ids)
    while waited < SETTLE_MAX_SECONDS:
        if monitor.waitForAbort(SETTLE_SECONDS):
            return None
        waited += SETTLE_SECONDS
        current = _signatures(addon_ids)
        if current == previous:
            return current
        previous = current
    _log('Folder still changing after %ds — patching anyway.' % SETTLE_MAX_SECONDS,
         xbmc.LOGWARNING)
    return previous


# ---------------------------------------------------------------------------
def _installed(addon_ids):
    """Filter to the add-ons actually present — an absent target is not a
    failure, and reporting it as one every sweep would bury real ones."""
    return [a for a in addon_ids if _addon_path(a)]


def _run_pass(addon_ids=None, reason=''):
    """Apply the default patch set (optionally narrowed) and report."""
    addon_ids = _installed(addon_ids or patcher.target_addon_ids())
    if not addon_ids:
        return 0, 0
    try:
        ok, failed, changed, _results = patcher.apply_set(addon_ids=addon_ids)
    except Exception as e:
        _log('Patch pass crashed (%s): %s' % (reason, e), xbmc.LOGERROR)
        return 0, 0

    if changed:
        _log('%s: re-applied %d patch(es), %d failed.' % (reason, changed, failed))
        _notify(T(30290))
    elif failed:
        _log('%s: %d patch(es) FAILED, %d OK.' % (reason, failed, ok),
             xbmc.LOGWARNING)
    return changed, failed


def watch(monitor):
    """Main loop. Returns when Kodi asks the service to abort."""
    if monitor.waitForAbort(BOOT_DELAY_SECONDS):
        return

    targets = patcher.target_addon_ids()
    _log('Watching %d add-on(s): %s' % (len(targets), ', '.join(targets)))

    state       = _load_state()
    last_verify = 0.0

    # Boot sweep: catches updates that happened while Kodi was closed, and
    # any patch that went missing for a reason we never saw.
    if not os.path.exists(DISABLE_FILE):
        _run_pass(reason='boot sweep')
        state = _signatures(targets)
        _save_state(state)
        last_verify = time.time()

    while not monitor.abortRequested():
        if monitor.waitForAbort(POLL_SECONDS):
            break

        if os.path.exists(DISABLE_FILE):
            continue                        # kill switch engaged

        try:
            current = _signatures(targets)
        except Exception as e:
            _log('Signature scan failed (ignored): %s' % e, xbmc.LOGWARNING)
            continue

        changed_ids = [a for a in targets if current.get(a) != state.get(a)]

        if changed_ids:
            _log('Change detected: %s' % ', '.join(changed_ids))
            settled = _wait_until_settled(monitor, changed_ids)
            if settled is None:
                break                       # aborting
            # Re-patch only the add-ons that moved.
            _run_pass(addon_ids=changed_ids, reason='update of %s'
                      % ', '.join(changed_ids))
            state.update(_signatures(targets))
            _save_state(state)
            last_verify = time.time()
            continue

        if time.time() - last_verify >= FULL_VERIFY_SECONDS:
            _run_pass(reason='periodic verify')
            state = _signatures(targets)
            _save_state(state)
            last_verify = time.time()

    _log('Watchdog stopped.')


# ---------------------------------------------------------------------------
def is_enabled():
    return not os.path.exists(DISABLE_FILE)


def toggle():
    """Menu entry: flip the auto-patch kill switch."""
    if is_enabled():
        try:
            os.makedirs(PROFILE, exist_ok=True)
            open(DISABLE_FILE, 'w').close()
        except Exception as e:
            _log('Could not write kill switch: %s' % e, xbmc.LOGWARNING)
        state = 'OFF'
        body  = T(30292)
    else:
        try:
            os.remove(DISABLE_FILE)
        except Exception:
            pass
        state = 'ON'
        body  = T(30291)
    _log('Auto-patch toggled %s by user.' % state)
    xbmcgui.Dialog().ok(ADDON_NAME, body)


def run():
    toggle()
