# -*- coding: utf-8 -*-
import os
import shutil
import zipfile
import datetime
import posixpath

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

# guisettings.xml cannot be reliably swapped from inside a running Kodi:
# Kodi holds it in memory and flushes it to disk on exit, clobbering anything
# written mid-session. The only safe time to replace it is while Kodi is NOT
# running. We therefore use a per-platform strategy:
#
#   • *ELEC (CoreELEC/LibreELEC): inject an autostart.sh block that copies the
#     staged file into userdata *before* Kodi starts. Fully automatic.
#   • macOS / Windows / Linux desktop: stage the file and write a one-click
#     helper script (.command/.bat/.sh) to the user's home/Desktop. The user
#     quits Kodi, runs it, and it copies the file in and relaunches Kodi.
#   • Android: no reliable external hook -> guisettings.xml is skipped and the
#     user is told. Everything else still restores.
#
# The staged file lives inside our addon profile so the path resolves on
# every platform.
_PROFILE_DIR        = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
GUISETTINGS_STAGING = os.path.join(_PROFILE_DIR, 'guisettings_pending.xml')
USERDATA_GUISETTINGS = xbmcvfs.translatePath('special://userdata/guisettings.xml')

# On *ELEC (CoreELEC / LibreELEC) the autostart.sh trick applies the staged
# file before Kodi starts.
AUTOSTART_PATH      = '/storage/.config/autostart.sh'
AUTOSTART_MARKER    = '# [abukarimtools] guisettings restore'


def _is_elec():
    """True only on CoreELEC / LibreELEC, where /storage + autostart.sh exist."""
    return os.path.isdir('/storage/.config') or os.path.isdir('/storage/.kodi')


def _is_android():
    """True on Android / Android TV builds of Kodi."""
    return xbmc.getCondVisibility('System.Platform.Android')


def _is_windows():
    return xbmc.getCondVisibility('System.Platform.Windows')


def _is_osx():
    return xbmc.getCondVisibility('System.Platform.OSX')


def _helper_dir():
    """
    Pick a user-visible folder to drop the helper script in. Prefer Desktop;
    fall back to home.
    """
    home = os.path.expanduser('~')
    desktop = os.path.join(home, 'Desktop')
    return desktop if os.path.isdir(desktop) else home

# ─── Exclusion rules ──────────────────────────────────────────────────────────
#
#  Addons that are excluded by default but can be opted-in per run via the
#  "Include skin data?" prompt shown before each backup / restore:
SKIN_ADDONS = [
    'script.skinshortcuts',
    'script.skinvariables',
]

#  Partial exclusion: for these addons only specific files are KEPT;
#  everything else inside their folder is skipped.
#  Format:  { addon_id: set_of_filenames_to_keep }
PARTIAL_ADDONS = {
    'plugin.video.themoviedb.helper': {'settings.xml'},
}

#  Hard exclusion: these addons are ALWAYS skipped during both backup and
#  restore. Unlike SKIN_ADDONS there is no opt-in — their data is never
#  collected and never written back. (Currently empty.)
EXCLUDE_ADDONS = [
]
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

        if idx == 0:
            include_skin = self._ask_skin_addons(dialog)
            self._do_backup(dialog, include_skin)
        elif idx == 1:
            include_skin = self._ask_skin_addons(dialog)
            self._do_restore(dialog, include_skin)

    def _ask_skin_addons(self, dialog):
        """
        Ask the user whether to include skin customisations.
        Returns a set of addon_ids to include (may be empty), or None if cancelled.
        """
        labels = [
            'My AF2/ AF3 widgets-تعديلاتي وترتيباتي الشخصية في السكن',
            'My AH2/ others widgets- تعديلاتي وترتيباتي الشخصية في السكن',
        ]
        selected = dialog.multiselect(
            'Include my customisations?',
            labels,
            preselect=[]
        )
        # multiselect returns None on Back/cancel or [] when confirmed with nothing ticked
        # either way treat as empty selection — skin addons will be skipped
        if not selected:
            return set()
        return {SKIN_ADDONS[i] for i in selected}

    # --------------------------------------------------------------- Backup --

    def _android_guisettings_heads_up(self, dialog):
        """
        On Android, warn up front that display/system settings (guisettings.xml)
        are excluded from backup and restore, because there's no reliable way to
        apply them on Android. Returns False if the user cancels.
        Non-Android platforms: no-op, returns True.
        """
        if not _is_android():
            return True
        return dialog.yesno(
            ADDON_NAME,
            'Android note: display/system settings (guisettings.xml) are '
            'excluded from backup and restore. Everything else is included.\n'
            'ملاحظة أندرويد: إعدادات العرض (guisettings.xml) مستثناة من '
            'النسخ والاستعادة. كل ما عداها مشمول.\n\nContinue? / متابعة؟',
            yeslabel='Continue / متابعة',
            nolabel='Cancel / إلغاء',
        )

    def _do_backup(self, dialog, include_skin):
        if not self._android_guisettings_heads_up(dialog):
            return
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
        pbar.create(ADDON_NAME, 'Collecting files…')

        try:
            file_list = self._collect_files(include_skin)
            total     = len(file_list)

            if total == 0:
                pbar.close()
                dialog.ok(ADDON_NAME, 'No files found to back up.')
                return

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
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
                dialog.ok(ADDON_NAME, 'Backup cancelled.')
            else:
                _log('Backup written to: %s' % zip_path)
                dialog.ok(ADDON_NAME,
                          'Backup complete!\n\n%d files saved to:\n%s'
                          % (total, zip_path))
                if (SKIN_ADDONS[0] in include_skin
                        and SKIN_ADDONS[1] in include_skin):
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
            dialog.ok(ADDON_NAME, 'Backup failed!\n%s' % e)

    # -------------------------------------------------------------- Restore --

    def _do_restore(self, dialog, include_skin):
        if not self._android_guisettings_heads_up(dialog):
            return
        zip_path = dialog.browse(
            1, 'Select backup ZIP to restore', 'files', '*.zip', False, False,
            self.home_path
        )
        if not zip_path or not zip_path.lower().endswith('.zip'):
            return

        # guisettings.xml is only overwritten where it can be applied
        # (not on Android).
        gs_line = ('' if _is_android()
                   else 'guisettings.xml, ')
        if not dialog.yesno(
            ADDON_NAME,
            'This will overwrite existing addon_data files, %skeymaps, '
            'sources.xml and favourites.xml.\n\n'
            'Continue with restore?' % gs_line
        ):
            return

        pbar = xbmcgui.DialogProgress()
        pbar.create(ADDON_NAME, 'Restoring…')

        # Tracks what happened with guisettings.xml so we can show the right
        # finishing instructions. Values: None (no guisettings in backup),
        # 'elec', ('helper', path|None), 'android_skip', 'error'.
        guisettings_outcome = None

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                members = zf.namelist()
                total   = len(members)

                for i, member in enumerate(members):
                    if pbar.iscanceled():
                        break

                    # Skip pure directory entries
                    if member.endswith('/'):
                        continue

                    # Normalise separators so Windows-created zips work on Linux
                    norm_member = member.replace('\\', '/').lstrip('/')

                    # Skip hard-excluded addon data entirely
                    member_parts = norm_member.split('/')
                    if (len(member_parts) >= 2
                            and member_parts[0] == 'addon_data'
                            and member_parts[1] in EXCLUDE_ADDONS):
                        continue

                    # Skip skin addon data unless the user opted in
                    member_parts = norm_member.split('/')
                    if (len(member_parts) >= 2
                            and member_parts[0] == 'addon_data'
                            and member_parts[1] in SKIN_ADDONS
                            and member_parts[1] not in include_skin):
                        continue

                    # guisettings.xml needs platform-specific handling because
                    # Kodi flushes its in-memory copy on exit. We stage it and
                    # apply it while Kodi is not running (see header notes).
                    if norm_member == 'guisettings.xml':
                        # Android: no reliable external hook — skip it.
                        if _is_android():
                            guisettings_outcome = 'android_skip'
                            _log('Android detected — skipping guisettings.xml '
                                 '(cannot be applied reliably).',
                                 xbmc.LOGWARNING)
                            continue
                        try:
                            data = zf.read(member)
                            os.makedirs(os.path.dirname(GUISETTINGS_STAGING),
                                        exist_ok=True)
                            with open(GUISETTINGS_STAGING, 'wb') as fh:
                                fh.write(data)

                            if _is_elec():
                                # Applied automatically before next Kodi start.
                                self._inject_autostart_restore()
                                guisettings_outcome = 'elec'
                            else:
                                # Desktop: drop a one-click helper script.
                                helper = self._write_desktop_helper()
                                guisettings_outcome = ('helper', helper)
                            _log('guisettings.xml staged at %s'
                                 % GUISETTINGS_STAGING)
                        except Exception as e:
                            guisettings_outcome = 'error'
                            _log('Could not stage guisettings.xml: %s' % e,
                                 xbmc.LOGWARNING)
                        continue

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

            pbar.close()

            if pbar.iscanceled():
                dialog.ok(ADDON_NAME,
                          'Restore cancelled.\nتم إلغاء الاستعادة.')
            else:
                _log('Restore completed from: %s' % zip_path)

                base = ('تمت الاستعادة! %d ملف.\n'
                        'Done! %d files restored.' % (total, total))
                tail = ''

                if guisettings_outcome == 'elec':
                    tail = ('\n\nقم بعمل اعادة تشغيل للجهاز - ريبوت.\n'
                            'Reboot now to apply settings.')
                elif (isinstance(guisettings_outcome, tuple)
                        and guisettings_outcome[0] == 'helper'):
                    helper = guisettings_outcome[1]
                    if helper:
                        fname = os.path.basename(helper)
                        _log('Helper script written to: %s' % helper)
                        tail = ('\n\nأغلق كودي ثم شغّل هذا الملف من سطح المكتب:\n'
                                'Quit Kodi, then run this file from the Desktop:\n'
                                '%s' % fname)
                    else:
                        tail = ('\n\nتم تخطّي إعدادات العرض.\n'
                                'Display settings skipped.')
                elif guisettings_outcome == 'android_skip':
                    tail = ('\n\nتم تخطّي إعدادات العرض على أندرويد، '
                            'وتمت استعادة الباقي.\n'
                            'Display settings skipped on Android; '
                            'rest restored.')
                elif guisettings_outcome == 'error':
                    tail = ('\n\nفشلت إعدادات العرض (راجع السجل)، '
                            'وتمت استعادة الباقي.\n'
                            'Display settings failed (see log); rest restored.')

                dialog.ok(ADDON_NAME, base + tail)
                if (SKIN_ADDONS[0] in include_skin
                        and SKIN_ADDONS[1] in include_skin):
                    _log('Both skin addons restored – running rebuild_shortcuts.')
                    xbmc.executebuiltin(
                        'RunScript(script.skinvariables,'
                        'run_executebuiltin=special://skin/shortcuts/'
                        'skinvariables-build-templates.json,use_rules)'
                    )

        except Exception as e:
            pbar.close()
            _log('Restore error: %s' % e, xbmc.LOGERROR)
            dialog.ok(ADDON_NAME, 'Restore failed!\nفشلت الاستعادة!\n%s' % e)

    # ------------------------------------------------- autostart.sh injection -

    def _inject_autostart_restore(self):
        """
        Append a self-removing block to autostart.sh that copies the staged
        guisettings.xml into userdata before Kodi starts, then deletes itself.
        Does nothing if the block is already present.
        """
        block = (
            '\n%(marker)s\n'
            'if [ -f "%(staging)s" ]; then\n'
            '    cp "%(staging)s" /storage/.kodi/userdata/guisettings.xml\n'
            '    rm -f "%(staging)s"\n'
            '    # Remove this block from autostart.sh\n'
            '    sed -i "/%(marker)s/,/^fi$/d" "%(autostart)s"\n'
            'fi\n'
        ) % {
            'marker':   AUTOSTART_MARKER,
            'staging':  GUISETTINGS_STAGING,
            'autostart': AUTOSTART_PATH,
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
        # Ensure a shebang is present if the file was freshly created.
        if not content.lstrip().startswith('#!'):
            content = '#!/bin/sh\n' + content
        with open(AUTOSTART_PATH, 'w') as f:
            f.write(content.rstrip('\n') + block)

        # CRITICAL: CoreELEC/LibreELEC silently ignore autostart.sh unless it
        # is executable. Without this the restore block never runs.
        try:
            os.chmod(AUTOSTART_PATH, 0o755)
        except OSError as e:
            _log('Could not chmod autostart.sh: %s' % e, xbmc.LOGWARNING)

        _log('Injected guisettings restore block into %s (chmod 755)'
             % AUTOSTART_PATH)

    # ------------------------------------------- desktop helper-script writer -

    def _write_desktop_helper(self):
        """
        Write a one-click helper script that, run while Kodi is CLOSED, copies
        the staged guisettings.xml into userdata and relaunches Kodi. Returns
        the path to the script written, or None on failure.

        macOS  -> .command (double-clickable in Finder)
        Windows-> .bat
        Linux  -> .sh (chmod +x)
        """
        staging  = GUISETTINGS_STAGING
        target   = USERDATA_GUISETTINGS
        out_dir  = _helper_dir()

        try:
            if _is_windows():
                path = os.path.join(out_dir, 'ABUKARIM_apply_guisettings.bat')
                body = (
                    '@echo off\r\n'
                    'echo Applying restored Kodi display/system settings...\r\n'
                    'taskkill /IM kodi.exe /F >nul 2>&1\r\n'
                    'timeout /t 2 /nobreak >nul\r\n'
                    'copy /Y "%(staging)s" "%(target)s"\r\n'
                    'del /Q "%(staging)s" >nul 2>&1\r\n'
                    'echo Done. You can reopen Kodi now.\r\n'
                    'pause\r\n'
                ) % {'staging': staging, 'target': target}
                with open(path, 'w', newline='') as fh:
                    fh.write(body)
                return path

            # macOS / Linux share a POSIX shell script; only the relaunch
            # command differs.
            if _is_osx():
                relaunch = 'open -a Kodi'
                ext = '.command'
            else:
                relaunch = 'kodi &'
                ext = '.sh'

            path = os.path.join(out_dir, 'ABUKARIM_apply_guisettings' + ext)
            body = (
                '#!/bin/sh\n'
                'echo "Applying restored Kodi display/system settings..."\n'
                '# Make sure Kodi is fully closed first.\n'
                'pkill -x Kodi 2>/dev/null\n'
                'pkill -x kodi.bin 2>/dev/null\n'
                'sleep 2\n'
                'cp "%(staging)s" "%(target)s"\n'
                'rm -f "%(staging)s"\n'
                'echo "Done. Relaunching Kodi..."\n'
                '%(relaunch)s\n'
            ) % {'staging': staging, 'target': target, 'relaunch': relaunch}

            with open(path, 'w') as fh:
                fh.write(body)
            os.chmod(path, 0o755)
            return path

        except Exception as e:
            _log('Could not write desktop helper script: %s' % e,
                 xbmc.LOGWARNING)
            return None

    # -------------------------------------------------------- File collection -

    def _collect_files(self, include_skin):
        """
        Walk userdata and return list of (absolute_path, archive_name) tuples.

        Included:
          • userdata/addon_data/**  – with per-addon exclusion rules
          • userdata/guisettings.xml
          • userdata/sources.xml
          • userdata/favourites.xml
          • userdata/keymaps/**

        All archive names are relative to userdata/ so restore can place
        every file back at the correct path under special://userdata/.
        """
        collected = []

        # ── guisettings.xml ───────────────────────────────────────────────────
        # Excluded on Android, where it can't be applied on restore anyway.
        guisettings = os.path.join(self.userdata_path, 'guisettings.xml')
        if _is_android():
            _log('Android — excluding guisettings.xml from backup.')
        elif os.path.isfile(guisettings):
            arc_name = 'guisettings.xml'
            collected.append((guisettings, arc_name))
            _log('Including guisettings.xml')
        else:
            _log('guisettings.xml not found, skipping.', xbmc.LOGWARNING)

        # ── sources.xml & favourites.xml ──────────────────────────────────────
        # Plain top-level userdata files. Unlike guisettings.xml these are not
        # held/flushed by Kodi the same way, so on restore they are written
        # directly (handled by the generic restore path) with no staging.
        for top_file in ('sources.xml', 'favourites.xml'):
            abs_path = os.path.join(self.userdata_path, top_file)
            if os.path.isfile(abs_path):
                collected.append((abs_path, top_file))
                _log('Including %s' % top_file)
            else:
                _log('%s not found, skipping.' % top_file, xbmc.LOGWARNING)

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

            # ── Hard-excluded addons – never backed up ────────────────────
            if addon_id in EXCLUDE_ADDONS:
                _log('Skipping (hard-excluded): %s' % addon_id)
                continue

            # ── Skin addons – include only if user opted in ───────────────
            if addon_id in SKIN_ADDONS and addon_id not in include_skin:
                _log('Skipping (skin addon, not opted in): %s' % addon_id)
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

            # ── Normal addon – include everything ─────────────────────────
            for root, dirs, files in os.walk(addon_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    rel      = os.path.relpath(abs_path, self.userdata_path)
                    arc_name = rel.replace('\\', '/')
                    collected.append((abs_path, arc_name))

        _log('Collected %d files for backup.' % len(collected))
        return collected
