import os
import shutil
import zipfile
import datetime

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

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
        zip_path = dialog.browse(
            1, 'Select backup ZIP to restore', 'files', '*.zip', False, False,
            self.home_path
        )
        if not zip_path or not zip_path.lower().endswith('.zip'):
            return

        if not dialog.yesno(
            ADDON_NAME,
            'This will overwrite existing addon_data files, '
            'guisettings.xml, and keymaps.\n\n'
            'Continue with restore?'
        ):
            return

        pbar = xbmcgui.DialogProgress()
        pbar.create(ADDON_NAME, 'Restoring…')

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

                    # Skip skin addon data unless the user opted in
                    member_parts = member.replace('\\', '/').split('/')
                    if (len(member_parts) >= 2
                            and member_parts[0] == 'addon_data'
                            and member_parts[1] in SKIN_ADDONS
                            and member_parts[1] not in include_skin):
                        continue

                    pct = int((i + 1) / total * 100)
                    pbar.update(pct, 'Restoring… (%d / %d)\n%s' % (i + 1, total, member))

                    dest     = os.path.join(self.userdata_path, member)
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
                dialog.ok(ADDON_NAME, 'Restore cancelled (partial restore may have occurred).')
            else:
                _log('Restore completed from: %s' % zip_path)
                dialog.ok(ADDON_NAME,
                          'Restore complete! %d files restored.\n\n'
                          'Please restart Kodi manually for the changes to take effect.' % total)
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
            dialog.ok(ADDON_NAME, 'Restore failed!\n%s' % e)

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
            arc_name = os.path.relpath(guisettings, self.userdata_path)
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
                    arc_name = os.path.relpath(abs_path, self.userdata_path)
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

            # ── Partially excluded addons ─────────────────────────────────
            if addon_id in PARTIAL_ADDONS:
                allowed = PARTIAL_ADDONS[addon_id]
                _log('Partially including %s (keeping: %s)'
                     % (addon_id, ', '.join(allowed)))
                for root, dirs, files in os.walk(addon_dir):
                    for fname in files:
                        if fname in allowed:
                            abs_path = os.path.join(root, fname)
                            arc_name = os.path.relpath(abs_path,
                                                       self.userdata_path)
                            collected.append((abs_path, arc_name))
                continue

            # ── Normal addon – include everything ─────────────────────────
            for root, dirs, files in os.walk(addon_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    arc_name = os.path.relpath(abs_path, self.userdata_path)
                    collected.append((abs_path, arc_name))

        _log('Collected %d files for backup.' % len(collected))
        return collected
