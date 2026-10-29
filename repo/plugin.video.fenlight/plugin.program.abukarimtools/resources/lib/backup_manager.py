import os
import re
import shutil
import zipfile

from resources.lib.i18n import T
import datetime

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon('plugin.program.abukarimtools')
ADDON_NAME = ADDON.getAddonInfo('name')

# guisettings.xml cannot be overwritten while Kodi is running — Kodi holds it
# in memory and flushes it on exit, clobbering anything we write mid-session.
# oe_settings.xml (CoreELEC's own settings service) behaves the same way —
# service.coreelec.settings periodically re-syncs its own remembered values
# (e.g. audiooutput.audiodevice) back over guisettings.xml, so restoring
# guisettings.xml alone doesn't stick if oe_settings.xml still holds the old
# value; it gets pushed straight back on the next sync.
# Instead we stage both files here; autostart.sh copies them into place
# before Kodi/CoreELEC's settings service starts on the next boot.
GUISETTINGS_STAGING  = '/storage/.guisettings_pending.xml'
OE_SETTINGS_STAGING  = '/storage/.oe_settings_pending.xml'
OE_SETTINGS_DEST     = ('/storage/.kodi/userdata/addon_data/'
                         'service.coreelec.settings/oe_settings.xml')
OE_SETTINGS_MEMBER   = 'addon_data/service.coreelec.settings/oe_settings.xml'
AUTOSTART_PATH      = '/storage/.config/autostart.sh'
AUTOSTART_MARKER    = '# [abukarimtools] guisettings restore'

# ─── Exclusion rules ──────────────────────────────────────────────────────────
#
#  Addons that are excluded by default but can be opted-in per run via the
#  "Include skin data?" prompt shown before each backup / restore:
SKIN_ADDONS = [
    'script.skinshortcuts',
    'script.skinvariables',
]

#  Addons whose addon_data is ALWAYS excluded from backups/restores.
#  These hold machine-/build-specific state that should not travel between
#  installs (e.g. the ABUKARIM build wizard's firstrun flag). ABUKARIM TOOLS'
#  own folder is excluded whole since 3.1.0.16 - first-run lifecycle files,
#  patch toggles, sentinels and everything else stay with the box.
EXCLUDED_ADDONS = [
    'plugin.program.ABUKARIMwizard',
    'plugin.program.abukarimtools',
]

#  Partial exclusion: for these addons only specific files are KEPT;
#  everything else inside their folder is skipped.
#  Format:  { addon_id: set_of_filenames_to_keep }
PARTIAL_ADDONS = {
    'plugin.video.themoviedb.helper': {'settings.xml'},
}

#  Partial SKIP: for these addons EVERYTHING is kept EXCEPT these filenames.
#  Format:  { addon_id: set_of_filenames_to_skip }
#  (plugin.program.abukarimtools used to be here for its first-run files; it is
#  now fully excluded via EXCLUDED_ADDONS, which covers those files too.)
SKIP_FILES = {}
# ─────────────────────────────────────────────────────────────────────────────


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[plugin.program.abukarim] %s' % msg, level)


class BackupManager:

    def __init__(self):
        self.userdata_path   = xbmcvfs.translatePath('special://userdata/')
        self.addon_data_path = xbmcvfs.translatePath('special://userdata/addon_data/')
        self.home_path       = xbmcvfs.translatePath('special://home/')

    # ------------------------------------------------------------------ UI ---

    def run(self):
        choices = ['Backup', 'Restore', 'Cancel']
        dialog  = xbmcgui.Dialog()
        idx     = dialog.select('%s – Main Menu' % ADDON_NAME, choices)

        # 3.2.9: no "Include my customisations?" question any more - menus and
        # widgets (skinshortcuts + skinvariables) are always part of a backup
        # and always restored when the backup contains them.
        include_skin = set(SKIN_ADDONS)
        if idx == 0:
            self._do_backup(dialog, include_skin)
        elif idx == 1:
            self._do_restore(dialog, include_skin)

    # --------------------------------------------------------------- Backup --

    def _do_backup(self, dialog, include_skin):
        # Ask where to save
        dest_folder = dialog.browse(
            3, 'Choose backup destination folder', 'files', '', False, False,
            self.home_path
        )
        if not dest_folder:
            return

        timestamp   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_name    = 'kodi_userdata_backup_%s.zip' % timestamp
        zip_path    = os.path.join(dest_folder, zip_name)

        pbar = xbmcgui.DialogProgress()
        pbar.create(ADDON_NAME, T(30220))

        try:
            file_list = self._collect_files(include_skin)
            total     = len(file_list)

            if total == 0:
                pbar.close()
                dialog.ok(ADDON_NAME, T(30221))
                return

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                _write_addon_manifest(zf)            # 3.4.0: add-ons + skin
                for i, (abs_path, arc_name) in enumerate(file_list):
                    if pbar.iscanceled():
                        break
                    pct = int((i + 1) / total * 100)
                    pbar.update(pct, 'Backing up… (%d / %d)\n%s' % (i + 1, total, arc_name))
                    try:
                        with open(abs_path, 'rb') as f:
                            zf.writestr(arc_name, f.read())
                    except Exception as e:
                        _log('Could not add %s: %s' % (abs_path, e),
                             xbmc.LOGWARNING)

            pbar.close()

            if pbar.iscanceled():
                # Remove incomplete zip
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
                dialog.ok(ADDON_NAME, T(30222))
            else:
                _log('Backup written to: %s' % zip_path)
                dialog.ok(ADDON_NAME, T(30223) % (total, zip_path))
                if (SKIN_ADDONS[0] in include_skin
                        and SKIN_ADDONS[1] in include_skin
                        and xbmcvfs.exists('special://skin/shortcuts/'
                                           'skinvariables-build-templates.json')):
                    _log('Both skin addons included – triggering rebuild_shortcuts.')
                    xbmc.executebuiltin(
                        'AlarmClock(rebuild_shortcuts,'
                        'RunScript(script.skinvariables,'
                        'run_executebuiltin=special://skin/shortcuts/'
                        'skinvariables-build-templates.json,use_rules),'
                        '00:01,silent)'
                    )

        except Exception as e:
            pbar.close()
            _log('Backup error: %s' % e, xbmc.LOGERROR)
            dialog.ok(ADDON_NAME, T(30224) % e)

    # -------------------------------------------------------------- Restore --

    @staticmethod
    def _push_active_skin_settings(data):
        """3.2.64: the Installation Wizard now applies the skin FIRST, so a
        restore can carry settings for the skin that is already running.
        Kodi keeps the active skin's settings in memory and writes them back
        on the next change or exit, which would silently undo the restored
        file - so the restored values are also pushed into Kodi itself."""
        text = data.decode('utf-8', 'replace')
        n = 0
        for m in re.finditer(r'<setting\s+([^>]*?)(?:/>|>(.*?)</setting>)',
                             text, re.S):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            sid = attrs.get('id')
            if not sid or sid.startswith('script-skinvariables-generator'):
                continue                      # build hashes: let it rebuild
            val = (m.group(2) or '').strip()
            val = (val.replace('&lt;', '<').replace('&gt;', '>')
                      .replace('&quot;', '"').replace('&apos;', "'")
                      .replace('&amp;', '&'))
            if attrs.get('type') == 'bool':
                if val.lower() == 'true':
                    xbmc.executebuiltin('Skin.SetBool(%s)' % sid)
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % sid)
            else:
                if val:
                    xbmc.executebuiltin('Skin.SetString(%s,"%s")'
                                        % (sid, val.replace('"', '\\"')))
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % sid)
            n += 1
        _log('Active skin settings pushed into Kodi: %d' % n)
        return n

    def _restore_members(self, zf, include_skin, progress=None):
        """3.3.7: the restore loop on its own, shared by the TV restore and
        the phone setup (phone_setup.py). progress(i, total, name) returning
        False cancels. Returns (members, cancelled)."""
        members = zf.namelist()
        total = len(members)
        self._guisettings = None
        self._manifest = None
        self._repos_added = []
        self._zip_addon_data = set()
        for i, member in enumerate(members):
            if progress and progress(i, total, member) is False:
                return total, True
            # Skip pure directory entries
            if member.endswith('/'):
                continue

            # Normalise separators so Windows-created zips work on Linux
            norm_member = member.replace('\\', '/').lstrip('/')

            # 3.4.0: the add-on manifest and the repository add-ons
            if norm_member == MANIFEST_NAME:
                try:
                    import json as _json
                    self._manifest = _json.loads(zf.read(member).decode('utf-8'))
                except Exception as e:
                    _log('manifest unreadable: %s' % e, xbmc.LOGWARNING)
                continue
            if norm_member.startswith('addons/'):
                parts = norm_member.split('/')
                if (len(parts) >= 3 and parts[1].startswith('repository.')
                        and '..' not in parts
                        and not os.path.isfile(os.path.join(ADDONS_HOME, parts[1], 'addon.xml'))
                        or (len(parts) >= 3 and parts[1] in self._repos_added)):
                    try:
                        dest = os.path.join(ADDONS_HOME, *parts[1:])
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with open(dest, 'wb') as fh:
                            fh.write(zf.read(member))
                        if parts[1] not in self._repos_added:
                            self._repos_added.append(parts[1])
                    except Exception as e:
                        _log('repository %s not restored: %s' % (parts[1], e),
                             xbmc.LOGWARNING)
                continue
            _p = norm_member.split('/')
            if len(_p) >= 3 and _p[0] == 'addon_data':
                self._zip_addon_data.add(_p[1])

            # Skip skin addon data unless the user opted in
            member_parts = norm_member.split('/')
            if (len(member_parts) >= 2
                    and member_parts[0] == 'addon_data'
                    and member_parts[1] in SKIN_ADDONS
                    and member_parts[1] not in include_skin):
                continue

            # Skip always-excluded addons (e.g. the ABUKARIM wizard's
            # first-run state) even if an older backup still contains
            # them, so machine-specific setup data isn't carried over.
            if (len(member_parts) >= 2
                    and member_parts[0] == 'addon_data'
                    and member_parts[1] in EXCLUDED_ADDONS):
                continue

            # Skip machine-/build-specific first-run lifecycle files
            # but keep the rest of the addon's data (e.g. patch
            # toggles). Restoring these re-imports another box's setup
            # state and makes first-run re-fire on the next boot after
            # a restore.
            if (len(member_parts) >= 3
                    and member_parts[0] == 'addon_data'
                    and member_parts[1] in SKIP_FILES
                    and member_parts[-1] in SKIP_FILES[member_parts[1]]):
                _log('Skipping first-run state file: %s' % norm_member)
                continue

            # guisettings.xml must be staged — writing it while Kodi
            # is running has no effect because Kodi overwrites it on exit.
            if norm_member == 'guisettings.xml':
                try:
                    data = zf.read(member)
                    self._guisettings = data          # 3.3.8: skin + live apply
                    if not _can_stage():
                        _log('guisettings.xml: no /storage (not CoreELEC) - '
                             'applied live after the restore')
                        continue
                    with open(GUISETTINGS_STAGING, 'wb') as fh:
                        fh.write(data)
                    self._inject_autostart_restore()
                    _log('guisettings.xml staged at %s' % GUISETTINGS_STAGING)
                except Exception as e:
                    _log('Could not stage guisettings.xml: %s' % e,
                         xbmc.LOGWARNING)
                continue

            # Same reasoning as guisettings.xml above — CoreELEC's own
            # settings service re-syncs this file's values back over
            # guisettings.xml during the session, so it needs the same
            # stage-and-restore-on-boot treatment or the fix doesn't stick.
            if norm_member == OE_SETTINGS_MEMBER:
                try:
                    data = zf.read(member)
                    with open(OE_SETTINGS_STAGING, 'wb') as fh:
                        fh.write(data)
                    self._inject_autostart_restore()
                    _log('oe_settings.xml staged at %s' % OE_SETTINGS_STAGING)
                except Exception as e:
                    _log('Could not stage oe_settings.xml: %s' % e,
                         xbmc.LOGWARNING)
                continue

            # the running skin's own settings: also push into Kodi
            if norm_member == 'addon_data/%s/settings.xml' % xbmc.getSkinDir():
                try:
                    self._push_active_skin_settings(zf.read(member))
                except Exception as e:
                    _log('Could not push active skin settings: %s' % e,
                         xbmc.LOGWARNING)

            dest     = os.path.join(self.userdata_path,
                                    *norm_member.split('/'))
            dest_dir = os.path.dirname(dest)

            try:
                os.makedirs(dest_dir, exist_ok=True)
                data = zf.read(member)
                with open(dest, 'wb') as fh:
                    fh.write(data)
            except Exception as e:
                _log('Could not restore %s: %s' % (member, e),
                     xbmc.LOGWARNING)

        return total, False

    def _do_restore(self, dialog, include_skin):
        zip_path = dialog.browse(
            1, T(30225), 'files', '*.zip', False, False,
            self.home_path
        )
        if not zip_path or not zip_path.lower().endswith('.zip'):
            return

        if not dialog.yesno(ADDON_NAME, T(30231)):
            return

        pbar = xbmcgui.DialogProgress()
        pbar.create(ADDON_NAME, T(30226))

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                def _prog(i, n, name):
                    if pbar.iscanceled():
                        return False
                    pbar.update(int((i + 1) / max(n, 1) * 100),
                                'Restoring… (%d / %d)\n%s' % (i + 1, n, name))
                    return True
                total, _cancel = self._restore_members(zf, include_skin, _prog)

            pbar.close()

            if pbar.iscanceled():
                dialog.ok(ADDON_NAME, T(30227))
            else:
                _log('Restore completed from: %s' % zip_path)
                after = _after_restore(self._guisettings, self)
                dialog.ok(ADDON_NAME, T(30228) % total)
                if after.get('restart'):
                    if dialog.yesno(ADDON_NAME, T(30737)):
                        _restart_kodi()

        except Exception as e:
            pbar.close()
            _log('Restore error: %s' % e, xbmc.LOGERROR)
            dialog.ok(ADDON_NAME, T(30229) % e)

    # ------------------------------------------------- autostart.sh injection -

    def _inject_autostart_restore(self):
        """
        Append a one-shot restore block to autostart.sh that copies staged
        guisettings.xml / oe_settings.xml into place before Kodi and
        CoreELEC's settings service start on the next boot.

        This block does NOT remove itself. An earlier version tried to via
        `sed -i` on autostart.sh from inside autostart.sh while it was still
        executing — rewriting a running shell script's own file mid-read is
        unsafe on BusyBox ash and corrupted/deleted the file in practice.
        Cleanup instead happens from service.py, in a separate process that
        only runs after this script has already finished and exited — see
        _cleanup_stale_autostart() there for the reasoning.

        Does nothing if the block is already present (idempotent — may be
        called once for guisettings.xml and again for oe_settings.xml in the
        same restore; the `if [ -f ... ]` guards make re-running harmless
        even so).
        """
        block = (
            '\n%(marker)s\n'
            'if [ -f "%(gui_staging)s" ]; then\n'
            '    cp "%(gui_staging)s" /storage/.kodi/userdata/guisettings.xml\n'
            '    rm -f "%(gui_staging)s"\n'
            'fi\n'
            'if [ -f "%(oe_staging)s" ]; then\n'
            '    cp "%(oe_staging)s" "%(oe_dest)s"\n'
            '    rm -f "%(oe_staging)s"\n'
            'fi\n'
        ) % {
            'marker':      AUTOSTART_MARKER,
            'gui_staging': GUISETTINGS_STAGING,
            'oe_staging':  OE_SETTINGS_STAGING,
            'oe_dest':     OE_SETTINGS_DEST,
        }

        # Read existing content (file may not exist yet)
        try:
            with open(AUTOSTART_PATH, 'r') as f:
                content = f.read()
        except IOError:
            content = '#!/bin/sh\n'

        if AUTOSTART_MARKER in content:
            _log('autostart.sh already contains restore block, skipping inject.')
            return

        os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
        with open(AUTOSTART_PATH, 'w') as f:
            f.write(content.rstrip('\n') + block)

        _log('Injected guisettings/oe_settings restore block into %s' % AUTOSTART_PATH)

    # -------------------------------------------------------- File collection -

    def _collect_files(self, include_skin):
        """
        Walk userdata and return list of (absolute_path, archive_name) tuples.

        Included:
          • userdata/addon_data/**  – with per-addon exclusion rules
          • userdata/guisettings.xml
          • userdata/keymaps/**

        All archive names are relative to userdata/ so restore can place
        every file back at the correct path under special://userdata/.
        """
        collected = []

        # ── guisettings.xml ───────────────────────────────────────────────────
        guisettings = os.path.join(self.userdata_path, 'guisettings.xml')
        if os.path.isfile(guisettings):
            arc_name = 'guisettings.xml'
            collected.append((guisettings, arc_name))
            _log('Including guisettings.xml')
        else:
            _log('guisettings.xml not found, skipping.', xbmc.LOGWARNING)

        # ── keymaps/ ──────────────────────────────────────────────────────────
        keymaps_dir = os.path.join(self.userdata_path, 'keymaps')
        if os.path.isdir(keymaps_dir):
            for root, dirs, files in os.walk(keymaps_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    rel      = os.path.relpath(abs_path, self.userdata_path)
                    arc_name = rel.replace('\\', '/')
                    collected.append((abs_path, arc_name))
            _log('Included keymaps/ directory.')
        else:
            _log('keymaps/ directory not found, skipping.', xbmc.LOGWARNING)

        # ── addon_data/ ───────────────────────────────────────────────────────
        if not os.path.isdir(self.addon_data_path):
            _log('addon_data path not found: %s' % self.addon_data_path,
                 xbmc.LOGWARNING)
            _log('Collected %d files for backup.' % len(collected))
            return collected

        for addon_id in os.listdir(self.addon_data_path):
            addon_dir = os.path.join(self.addon_data_path, addon_id)

            if not os.path.isdir(addon_dir):
                continue

            # ── Skin addons – include only if user opted in ───────────────
            if addon_id in SKIN_ADDONS and addon_id not in include_skin:
                _log('Skipping (skin addon, not opted in): %s' % addon_id)
                continue

            # ── Always-excluded addons ────────────────────────────────────
            if addon_id in EXCLUDED_ADDONS:
                _log('Skipping (always excluded): %s' % addon_id)
                continue

            # ── Partially excluded addons ─────────────────────────────────
            if addon_id in PARTIAL_ADDONS:
                allowed = PARTIAL_ADDONS[addon_id]
                _log('Partially including %s (keeping: %s)'
                     % (addon_id, ', '.join(allowed)))
                for root, dirs, files in os.walk(addon_dir):
                    for fname in files:
                        if fname in allowed:
                            abs_path = os.path.join(root, fname)
                            rel      = os.path.relpath(abs_path, self.userdata_path)
                            arc_name = rel.replace('\\', '/')
                            collected.append((abs_path, arc_name))
                continue

            # ── Skip-list addons – include everything EXCEPT named files ───
            if addon_id in SKIP_FILES:
                skip = SKIP_FILES[addon_id]
                _log('Including %s (skipping first-run state: %s)'
                     % (addon_id, ', '.join(sorted(skip))))
                for root, dirs, files in os.walk(addon_dir):
                    for fname in files:
                        if fname in skip:
                            continue
                        abs_path = os.path.join(root, fname)
                        rel      = os.path.relpath(abs_path, self.userdata_path)
                        arc_name = rel.replace('\\', '/')
                        collected.append((abs_path, arc_name))
                continue

            # ── Normal addon – include everything ─────────────────────────
            for root, dirs, files in os.walk(addon_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    rel      = os.path.relpath(abs_path, self.userdata_path)
                    arc_name = rel.replace('\\', '/')
                    collected.append((abs_path, arc_name))

        _log('Collected %d files for backup.' % len(collected))
        return collected


# ─── headless API (3.3.7: phone setup) ───────────────────────────────────────

def write_backup(zip_path, progress=None):
    """Full backup (menus and widgets included, like the TV backup) into
    zip_path without any dialog. progress(i, total, name) -> False cancels.
    Returns the number of files written (0 = nothing / cancelled)."""
    bm = BackupManager()
    files = bm._collect_files(set(SKIN_ADDONS))
    total = len(files)
    if not total:
        return 0
    n = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        _write_addon_manifest(zf)                    # 3.4.0: add-ons + skin
        for i, (abs_path, arc_name) in enumerate(files):
            if progress and progress(i, total, arc_name) is False:
                break
            try:
                with open(abs_path, 'rb') as f:
                    zf.writestr(arc_name, f.read())
                n += 1
            except Exception as e:
                _log('Could not add %s: %s' % (abs_path, e), xbmc.LOGWARNING)
        else:
            _log('Backup written to: %s (%d files)' % (zip_path, n))
            return n
    try:
        os.remove(zip_path)
    except OSError:
        pass
    return 0


def restore_backup(zip_path, progress=None):
    """Restore zip_path (a backup made by this add-on) without any dialog.
    Returns (files in the zip, cancelled). Raises on a broken zip."""
    bm = BackupManager()
    with zipfile.ZipFile(zip_path, 'r') as zf:
        total, cancelled = bm._restore_members(zf, set(SKIN_ADDONS), progress)
    after = {}
    if not cancelled:
        _log('Restore completed from: %s' % zip_path)
        after = _after_restore(bm._guisettings, bm, progress)
    return total, cancelled, after


# ─── add-ons and skin in the backup (3.4.0) ──────────────────────────────────
# A backup used to hold userdata only, so a restore onto a fresh box brought
# back the SETTINGS of the video add-ons and the skin but not the add-ons
# themselves (user report 2026-10-14). Now every backup carries
# abk_manifest.json - each installed add-on/skin with its version and the
# repository it updates from - plus the repository add-ons themselves
# (addons/repository.*/..., a few KB each). A restore puts missing
# repositories back, then installs every missing add-on from its own
# repository with the Add-on Portal installer, then switches the skin.

ADDONS_HOME = xbmcvfs.translatePath('special://home/addons/')
MANIFEST_NAME = 'abk_manifest.json'
_NO_MANIFEST = ('script.module.', 'resource.', 'xbmc.', 'kodi.', 'metadata.',
                'inputstream.', 'audioencoder.', 'audiodecoder.', 'imagedecoder.',
                'peripheral.', 'game.', 'vfs.', 'visualization.', 'screensaver.')
_NO_MANIFEST_IDS = {'plugin.program.abukarimtools'}
_REPO_MAX_FILE = 2 * 1024 * 1024


def _addon_xml(addon_dir):
    import xml.etree.ElementTree as ET
    try:
        return ET.parse(os.path.join(addon_dir, 'addon.xml')).getroot()
    except Exception:
        return None


def scan_addons():
    """Installed (non-system, non-library) add-ons: [{id, name, version,
    kind: skin|repo|addon, origin}]."""
    try:
        from resources.lib import origin_fix
        origins = origin_fix.snapshot_origins()
    except Exception:
        origins = {}
    out = []
    try:
        names = sorted(os.listdir(ADDONS_HOME))
    except OSError:
        return out
    for d in names:
        if d in ('packages', 'temp') or d.startswith(_NO_MANIFEST) or d in _NO_MANIFEST_IDS:
            continue
        root = _addon_xml(os.path.join(ADDONS_HOME, d))
        if root is None or root.get('id') != d:
            continue
        points = {e.get('point') for e in root.findall('extension')}
        if 'xbmc.python.module' in points:
            continue
        kind = ('skin' if 'xbmc.gui.skin' in points else
                'repo' if 'xbmc.addon.repository' in points else 'addon')
        out.append({'id': d, 'name': root.get('name') or d,
                    'version': root.get('version') or '', 'kind': kind,
                    'origin': origins.get(d, '')})
    return out


def _write_addon_manifest(zf):
    """abk_manifest.json + the repository add-ons, into an open ZipFile."""
    import json as _json
    try:
        addons = scan_addons()
        manifest = {'version': 1, 'skin': xbmc.getSkinDir(), 'addons': addons}
        zf.writestr(MANIFEST_NAME, _json.dumps(manifest, ensure_ascii=False, indent=1))
        n = 0
        for a in addons:
            if a['kind'] != 'repo':
                continue
            base = os.path.join(ADDONS_HOME, a['id'])
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    fp = os.path.join(root, fname)
                    try:
                        if os.path.getsize(fp) > _REPO_MAX_FILE:
                            continue
                        rel = os.path.relpath(fp, ADDONS_HOME).replace('\\', '/')
                        with open(fp, 'rb') as f:
                            zf.writestr('addons/' + rel, f.read())
                        n += 1
                    except Exception:
                        pass
        _log('manifest: %d add-on(s), skin %s, %d repository file(s)'
             % (len(addons), manifest['skin'], n))
    except Exception as e:
        _log('manifest not written: %s' % e, xbmc.LOGWARNING)


def _db_repo_for(addon_id):
    """Repository whose cached listing carries addon_id (old backups)."""
    try:
        from resources.lib import origin_fix
        db = origin_fix._find_addons_db()
        if not db:
            return ''
        conn = origin_fix._connect(db)
        try:
            return origin_fix._pick_repo(origin_fix._repo_candidates(conn.cursor(), addon_id)) or ''
        finally:
            conn.close()
    except Exception:
        return ''


def reinstall_missing(manifest, repos_added, zip_addon_data, progress=None):
    """Install what the backup had and this box lacks. Returns
    (installed count, [failed names])."""
    from resources.lib import addon_portal as ap
    if manifest and isinstance(manifest.get('addons'), list):
        wanted = [a for a in manifest['addons']
                  if isinstance(a, dict) and a.get('id') and a.get('kind') != 'repo']
    else:
        # backups from before 3.4.0: the add-ons whose settings are in the zip
        wanted = [{'id': i, 'name': i, 'origin': ''} for i in sorted(zip_addon_data)
                  if i.startswith(('plugin.video.', 'plugin.program.', 'skin.'))
                  and i not in _NO_MANIFEST_IDS]
    system = xbmcvfs.translatePath('special://xbmc/addons/')
    missing = [a for a in wanted if not ap._is_local(a['id'])
               and not os.path.isdir(os.path.join(system, a['id']))     # Kodi's own (Estuary)
               and a['id'] != 'skin.estuary']
    if not missing and not repos_added:
        return 0, []
    if repos_added:
        _log('repositories restored from the backup: %s' % ', '.join(repos_added))
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(3000)
        for rid in repos_added:
            ap._enable(rid)
            ap._force_origin(rid, rid)
        xbmc.executebuiltin('UpdateAddonRepos')
        ap._wait_repo_listings(repos_added)
    if not missing:
        return 0, []
    if progress:
        try:                                   # restore-style: (i, total, name)
            progress(96, 100, 'add-ons')
        except Exception:
            pass
    entries, kodi_only = [], []
    for a in missing:
        rid = a.get('origin') or _db_repo_for(a['id'])
        if rid and not rid.startswith('b6a50484'):           # not ORIGIN_SYSTEM
            entries.append((a['id'], a.get('name') or a['id'], rid))
        else:
            kodi_only.append(a)
    _log('restore: installing %d missing add-on(s): %s'
         % (len(missing), ', '.join(a['id'] for a in missing)))
    installed, failed = 0, []
    if entries:
        for name, ok, _note in ap._install_selection(entries):
            if ok:
                installed += 1
            else:
                failed.append(name)
    for a in kodi_only:
        if ap._kodi_install(a['id'], timeout_ms=30000):
            ap._enable(a['id'])
            installed += 1
        else:
            failed.append(a.get('name') or a['id'])
    _log('restore: %d add-on(s) installed, %d failed%s'
         % (installed, len(failed), (' (%s)' % ', '.join(failed)) if failed else ''))
    return installed, failed


# ─── after a restore (3.3.8) ─────────────────────────────────────────────────
# kodi.log 2026-10-14 09:53: a phone restore on the Mac "did nothing" -
# guisettings.xml could not be staged (/storage only exists on *ELEC), the
# box was on Estuary so the restored Arctic Fuse 3 menus / settings were not
# visible, and the skinvariables rebuild crashed on a skin without
# shortcuts/skinvariables-build-templates.json.

# never applied live: hardware / network / the skin itself (switched apart)
_LIVE_SKIP = ('lookandfeel.skin', 'audiooutput.', 'videoscreen.', 'network.',
              'services.webserver', 'services.esallinterfaces', 'services.zeroconf',
              'services.airplay', 'services.upnp', 'debug.', 'system.',
              'coreelec.', 'smb.', 'videoplayer.hqscalers', 'locale.timezone')


def _can_stage():
    return os.path.isdir('/storage')


def _rpc(method, params=None):
    import json
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except Exception:
        return {}


def _gs_values(data):
    """{id: text} of the NON-default settings in a guisettings.xml."""
    text = data.decode('utf-8', 'replace') if isinstance(data, bytes) else data
    out = {}
    for m in re.finditer(r'<setting\s+([^>]*?)(?:/>|>(.*?)</setting>)', text, re.S):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if not attrs.get('id') or attrs.get('default') == 'true':
            continue
        val = (m.group(2) or '')
        val = (val.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
                  .replace('&apos;', "'").replace('&amp;', '&'))
        out[attrs['id']] = val
    return out


def apply_guisettings_live(data):
    """Desktop / non-*ELEC: push the backup's Kodi settings through JSON-RPC
    (Kodi would overwrite a written guisettings.xml on exit). Only settings
    whose type is known and whose value differs; hardware, network and the
    skin are left out. Returns the number applied."""
    want = _gs_values(data)
    cur = (_rpc('Settings.GetSettings', {'level': 'expert'}).get('result') or {}).get('settings') or []
    types = {c.get('id'): (c.get('type'), c.get('value')) for c in cur if isinstance(c, dict)}
    n = 0
    for sid, raw in want.items():
        if sid.startswith(_LIVE_SKIP) or sid not in types:
            continue
        typ, now = types[sid]
        try:
            if typ == 'boolean':
                val = raw.strip().lower() == 'true'
            elif typ == 'integer':
                val = int(raw)
            elif typ == 'number':
                val = float(raw)
            elif typ == 'string':
                val = raw
            else:
                continue
        except ValueError:
            continue
        if val == now:
            continue
        res = _rpc('Settings.SetSettingValue', {'setting': sid, 'value': val})
        if res.get('result') is True:
            n += 1
    _log('Kodi settings applied live from the backup: %d' % n)
    return n


def _backup_skin(data):
    m = re.search(r'<setting id="lookandfeel\.skin"[^>]*>([^<]+)</setting>',
                  data.decode('utf-8', 'replace') if isinstance(data, bytes) else data)
    return m.group(1).strip() if m else ''


def _rebuild_shortcuts():
    tpl = 'special://skin/shortcuts/skinvariables-build-templates.json'
    if not xbmcvfs.exists(tpl):
        _log('%s has no skinvariables build template - no rebuild' % xbmc.getSkinDir())
        return False
    xbmc.executebuiltin('RunScript(script.skinvariables,run_executebuiltin=%s,use_rules)' % tpl)
    return True


def _after_restore(guisettings, bm=None, progress=None):
    """Make a restore visible now: missing add-ons + skin reinstalled from
    their repositories (3.4.0), Kodi settings live (non-*ELEC), back to the
    skin the backup was made on, menus rebuilt.
    Returns {'settings', 'skin', 'installed', 'failed', 'restart'}."""
    out = {'settings': 0, 'skin': '', 'installed': 0, 'failed': [], 'restart': True}
    if bm is not None:
        try:
            out['installed'], out['failed'] = reinstall_missing(
                getattr(bm, '_manifest', None), getattr(bm, '_repos_added', []),
                getattr(bm, '_zip_addon_data', set()), progress)
        except Exception as e:
            _log('add-on reinstall failed: %s' % e, xbmc.LOGWARNING)
    if guisettings and not _can_stage():
        try:
            out['settings'] = apply_guisettings_live(guisettings)
        except Exception as e:
            _log('live settings failed: %s' % e, xbmc.LOGWARNING)
    manifest = getattr(bm, '_manifest', None) if bm is not None else None
    skin = (_backup_skin(guisettings) if guisettings else '') or \
        ((manifest or {}).get('skin') if isinstance(manifest, dict) else '') or ''
    if skin in ('', 'skin.estuary') and not isinstance(manifest, dict) and bm is not None:
        # backups from before 3.4.0 (kodi.log 2026-10-14 10:17): guisettings
        # said Estuary although the box's own skin settings are in the zip -
        # when exactly one other installed skin has settings there, use it.
        skins = sorted(i for i in getattr(bm, '_zip_addon_data', set())
                       if i.startswith('skin.') and i != 'skin.estuary'
                       and xbmc.getCondVisibility('System.HasAddon(%s)' % i))
        if len(skins) == 1:
            _log('old backup: guisettings says %s, using %s (its settings are in the zip)'
                 % (skin or 'nothing', skins[0]))
            skin = skins[0]
    if (skin and skin != xbmc.getSkinDir()
            and xbmc.getCondVisibility('System.HasAddon(%s)' % skin)):
        try:
            from resources.lib import skin_switcher
            _log('switching to the backup skin: %s' % skin)
            skin_switcher._swap_skin(skin)
            out['skin'] = skin
            xbmc.sleep(1500)
        except Exception as e:
            _log('skin switch failed: %s' % e, xbmc.LOGWARNING)
    try:
        _rebuild_shortcuts()
    except Exception as e:                      # never fail a finished restore
        _log('menu rebuild skipped: %s' % e, xbmc.LOGWARNING)
    return out


def _restart_kodi():
    if _can_stage():
        xbmc.executebuiltin('Reboot')
    else:
        xbmc.executebuiltin('RestartApp')
