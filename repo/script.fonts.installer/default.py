import os
import shutil

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_icon = xbmcvfs.translatePath(addon.getAddonInfo('icon'))
addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))

# Folder name is case-sensitive on CoreELEC/Linux: it must match the zip exactly.
font_source = os.path.join(addon_path, 'resources', 'Fonts')
# The only folder Kodi scans for user subtitle fonts (FONTPATH::USER).
font_dest = xbmcvfs.translatePath('special://home/media/Fonts/')
fontcache_dest = os.path.join(font_dest, 'fontcache.xml')

FONT_EXTS = ('.ttf', '.otf', '.ttc')

# Files shipped by older versions that are no longer bundled.
# Removed on uninstall only if they are still byte-identical sizes we shipped.
LEGACY_FILES = {
    'Droid.Arabic.Naskh_.Regular_DownloadSoftware.iR_.ttf': 91340,
}

LOG_TAG = '[script.fonts.installer]'


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('%s %s' % (LOG_TAG, msg), level)


def bundled_fonts():
    """The font files shipped in resources/Fonts (the install manifest)."""
    try:
        names = os.listdir(font_source)
    except OSError as e:
        log('Font source folder missing: %s (%s)' % (font_source, e), xbmc.LOGERROR)
        return []
    return sorted(n for n in names if n.lower().endswith(FONT_EXTS))


def same_file(a, b):
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, 'rb') as fa, open(b, 'rb') as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def reset_fontcache():
    # Kodi trusts fontcache.xml by FILENAME, so a stale entry can hide or
    # mislabel a font. Deleting it makes Kodi rescan every file at next start.
    if os.path.exists(fontcache_dest):
        try:
            os.remove(fontcache_dest)
        except OSError as e:
            log('Could not remove fontcache.xml: %s' % e, xbmc.LOGWARNING)


def install_fonts(fonts):
    if not os.path.isdir(font_dest):
        os.makedirs(font_dest)
    copied, failed = 0, []
    for name in fonts:
        src = os.path.join(font_source, name)
        dest = os.path.join(font_dest, name)
        if same_file(src, dest):
            continue
        try:
            shutil.copyfile(src, dest)
            copied += 1
        except Exception as e:
            failed.append(name)
            log('Copy failed for %s: %s' % (name, e), xbmc.LOGERROR)
    reset_fontcache()
    log('Installed %d font(s) to %s, %d failed' % (copied, font_dest, len(failed)))
    return failed


def uninstall_fonts(fonts):
    removed = 0
    for name in fonts:
        dest = os.path.join(font_dest, name)
        # Only delete files that are ours (never a user's same-named font).
        if same_file(os.path.join(font_source, name), dest):
            try:
                os.remove(dest)
                removed += 1
            except OSError as e:
                log('Remove failed for %s: %s' % (name, e), xbmc.LOGERROR)
    for name, size in LEGACY_FILES.items():
        dest = os.path.join(font_dest, name)
        try:
            if os.path.getsize(dest) == size:
                os.remove(dest)
                removed += 1
        except OSError:
            pass
    reset_fontcache()
    log('Removed %d font(s) from %s' % (removed, font_dest))


def fonts_exist(fonts):
    return bool(fonts) and all(
        os.path.exists(os.path.join(font_dest, n)) for n in fonts)


def offer_restart(message):
    # Kodi builds the subtitle font list only once, at startup
    # (GUIFontManager::Initialize). ReloadSkin() does not refresh it.
    dialog = xbmcgui.Dialog()
    if not dialog.yesno(addon_name, message + '[CR][CR]'
                        'Kodi must restart for the subtitle font list to update. Restart now?'):
        return
    if xbmc.getCondVisibility('System.Platform.OSX'):
        dialog.ok(addon_name, 'Kodi will now quit. Open it again to see the new fonts.')
        xbmc.executebuiltin('Quit')
    else:
        xbmc.executebuiltin('RestartApp')


if __name__ == '__main__':
    fonts = bundled_fonts()
    if not fonts:
        xbmcgui.Dialog().ok(addon_name, 'No fonts found in the add-on package.')
    elif fonts_exist(fonts):
        uninstall_fonts(fonts)
        offer_restart('Fonts removed.')
    else:
        failed = install_fonts(fonts)
        if failed:
            xbmcgui.Dialog().ok(addon_name, 'Some fonts failed to copy:[CR]' + '[CR]'.join(failed))
        offer_restart('%d fonts installed.' % (len(fonts) - len(failed)))
