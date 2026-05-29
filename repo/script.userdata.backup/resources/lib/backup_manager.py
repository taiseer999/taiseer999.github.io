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
#  Fully excluded addons (entire folder skipped):
EXCLUDED_ADDONS = {
    'script.skinshortcuts',
    'script.skinvariables',
}

#  Partial exclusion: for these addons only specific files are KEPT;
#  everything else inside their folder is skipped.
#  Format:  { addon_id: set_of_filenames_to_keep }
PARTIAL_ADDONS = {
    'plugin.video.themoviedb.helper': {'settings.xml'},
}
# ─────────────────────────────────────────────────────────────────────────────


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[script.userdata.backup] %s' % msg, level)


class BackupManager:

    def __init__(self):
        self.addon_data_path = xbmcvfs.translatePath('special://userdata/addon_data/')
        self.home_path       = xbmcvfs.translatePath('special://home/')

    # ------------------------------------------------------------------ UI ---

    def run(self):
        choices = ['Backup addon_data', 'Restore addon_data', 'Cancel']
        dialog  = xbmcgui.Dialog()
        idx     = dialog.select('%s – Main Menu' % ADDON_NAME, choices)

        if idx == 0:
            self._do_backup(dialog)
        elif idx == 1:
            self._do_restore(dialog)

    # --------------------------------------------------------------- Backup --

    def _do_backup(self, dialog):
        # Ask where to save
        dest_folder = dialog.browse(
            3, 'Choose backup destination folder', 'files', '', False, False,
            self.home_path
        )
        if not dest_folder:
            return

        timestamp   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_name    = 'kodi_addon_data_backup_%s.zip' % timestamp
        zip_path    = os.path.join(dest_folder, zip_name)

        pbar = xbmcgui.DialogProgress()
        pbar.create(ADDON_NAME, 'Collecting files…')

        try:
            file_list = self._collect_files()
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

        except Exception as e:
            pbar.close()
            _log('Backup error: %s' % e, xbmc.LOGERROR)
            dialog.ok(ADDON_NAME, 'Backup failed!\n%s' % e)

    # -------------------------------------------------------------- Restore --

    def _do_restore(self, dialog):
        zip_path = dialog.browse(
            1, 'Select backup ZIP to restore', 'files', '*.zip', False, False,
            self.home_path
        )
        if not zip_path or not zip_path.lower().endswith('.zip'):
            return

        if not dialog.yesno(
            ADDON_NAME,
            'This will overwrite existing addon_data files.\n\n'
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
                    pct = int((i + 1) / total * 100)
                    pbar.update(pct, 'Restoring… (%d / %d)\n%s' % (i + 1, total, member))

                    dest = os.path.join(self.addon_data_path, member)
                    dest_dir = os.path.dirname(dest)

                    if not xbmcvfs.exists(dest_dir):
                        xbmcvfs.mkdirs(dest_dir)

                    try:
                        data = zf.read(member)
                        with xbmcvfs.File(dest, 'w') as fh:
                            fh.write(bytes(data))
                    except Exception as e:
                        _log('Could not restore %s: %s' % (member, e),
                             xbmc.LOGWARNING)

            pbar.close()

            if pbar.iscanceled():
                dialog.ok(ADDON_NAME, 'Restore cancelled (partial restore may have occurred).')
            else:
                _log('Restore completed from: %s' % zip_path)
                dialog.ok(ADDON_NAME, 'Restore complete!\n\n%d files restored.' % total)

        except Exception as e:
            pbar.close()
            _log('Restore error: %s' % e, xbmc.LOGERROR)
            dialog.ok(ADDON_NAME, 'Restore failed!\n%s' % e)

    # -------------------------------------------------------- File collection -

    def _collect_files(self):
        """
        Walk addon_data and return list of (absolute_path, archive_name) tuples
        applying the exclusion rules at the top of this file.
        """
        collected = []

        if not os.path.isdir(self.addon_data_path):
            _log('addon_data path not found: %s' % self.addon_data_path,
                 xbmc.LOGWARNING)
            return collected

        for addon_id in os.listdir(self.addon_data_path):
            addon_dir = os.path.join(self.addon_data_path, addon_id)

            if not os.path.isdir(addon_dir):
                continue

            # ── Fully excluded addons ──────────────────────────────────────
            if addon_id in EXCLUDED_ADDONS:
                _log('Skipping (fully excluded): %s' % addon_id)
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
                                                       self.addon_data_path)
                            collected.append((abs_path, arc_name))
                continue

            # ── Normal addon – include everything ─────────────────────────
            for root, dirs, files in os.walk(addon_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    arc_name = os.path.relpath(abs_path, self.addon_data_path)
                    collected.append((abs_path, arc_name))

        _log('Collected %d files for backup.' % len(collected))
        return collected
