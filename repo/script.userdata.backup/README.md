# script.userdata.backup — Kodi Addon

## What it does

Backs up and restores everything inside **userdata/addon_data** with the
following exclusion rules:

| Addon | Action |
|---|---|
| `script.skinshortcuts` | **Fully excluded** – nothing backed up |
| `script.skinvariables` | **Fully excluded** – nothing backed up |
| `plugin.video.themoviedb.helper` | **Partially included** – only `settings.xml` is backed up; all other files are skipped |
| Everything else | **Fully included** |

Backups are written as a single `.zip` file with the structure mirroring
`addon_data/` so restores drop files back exactly where they came from.

---

## Installation

1. Copy the `script.userdata.backup` folder into your Kodi add-ons directory:
   - **Windows:** `%APPDATA%\Kodi\addons\`
   - **Linux / macOS:** `~/.kodi/addons/`
   - **Android:** `/sdcard/Android/data/org.xbmc.kodi/files/.kodi/addons/`
   - **LibreELEC / CoreELEC:** `/storage/.kodi/addons/`

2. In Kodi go to **Settings → Add-ons → My add-ons → Program add-ons** and
   enable **Userdata Backup & Restore**.

3. Run the addon from **Program Add-ons**.

---

## Usage

### Backup
1. Launch the addon → choose **Backup addon_data**.
2. Browse to the folder where you want to save the ZIP.
3. A timestamped ZIP (e.g. `kodi_addon_data_backup_20260529_143000.zip`) is
   created there.

### Restore
1. Launch the addon → choose **Restore addon_data**.
2. Browse to and select the previously created ZIP file.
3. Confirm the prompt.  Files are extracted back into `addon_data/`.

---

## Customising exclusions

Open `resources/lib/backup_manager.py` and edit the two dictionaries near the
top of the file:

```python
# Fully skip these addon folders
EXCLUDED_ADDONS = {
    'script.skinshortcuts',
    'script.skinvariables',
}

# Keep only specific filenames from these addons
PARTIAL_ADDONS = {
    'plugin.video.themoviedb.helper': {'settings.xml'},
}
```

Add or remove entries as needed — no other code changes required.
