# -*- coding: utf-8 -*-
"""
settings_downgrade.py - Maintenance > "Fix Add-on Settings Version".

4.6.31: a settings.xml in addon_data that was saved by a newer Kodi carries
<settings version="5">. A Kodi whose settings manager is at version 4
(e.g. 22.0-RC1 21.90.901) rejects the WHOLE file:

    CSettingsManager: unable to read setting values from version 5 (current version: 4)
    CAddon[script.module.acctmgr]: failed to load user settings

so the add-on runs on defaults (Account Manager / POV / Umbrella / ResolveURL
look unauthorised) and the next setSetting() can overwrite the stored tokens.

This is NOT a patch and never runs by itself: it is a Maintenance entry that
is only listed on a box where Kodi itself logged that error AND at least one
addon_data/*/settings.xml is still newer than what Kodi reads. The supported
version is taken from Kodi's own log line ("current version: N"), never
guessed. Only the version number in the root tag is changed - values are left
as they are - and each file is backed up once as settings.xml.v<M>.bak.
Kodi is restarted straight away (force close, nothing flushed) so no add-on
can write its in-memory defaults over the converted file.
"""

import os
import re

import xbmc
import xbmcgui
import xbmcvfs

_ERR_RE = re.compile(r'unable to read setting values from version (\d+) '
                     r'\(current version: (\d+)\)')
_HDR_RE = re.compile(r'(<settings\b[^>]*?\bversion\s*=\s*["\'])(\d+)(["\'])')
_LOG_SCAN_LIMIT = 8 * 1024 * 1024     # bytes; the error is logged at boot


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SettingsVersion] %s' % msg, level)


def supported_version():
    """The settings version this Kodi reads, from its own log; None if Kodi
    never complained this session (or the session before)."""
    logdir = xbmcvfs.translatePath('special://logpath/')
    for name in ('kodi.log', 'kodi.old.log'):
        path = os.path.join(logdir, name)
        current = None
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                read = 0
                for line in fh:
                    read += len(line)
                    if 'unable to read setting values' in line:
                        m = _ERR_RE.search(line)
                        if m:
                            current = int(m.group(2))
                            break
                    if read > _LOG_SCAN_LIMIT:
                        break
        except OSError:
            continue
        if current is not None:
            return current
    return None


def _addon_data():
    return xbmcvfs.translatePath('special://profile/addon_data/')


def _file_version(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            head = fh.read(512)
    except OSError:
        return None
    m = _HDR_RE.search(head)
    return int(m.group(2)) if m else None


def affected(target):
    """[(addon_id, version)] whose settings.xml is newer than target."""
    out = []
    root = _addon_data()
    try:
        ids = sorted(os.listdir(root))
    except OSError:
        return out
    for addon_id in ids:
        path = os.path.join(root, addon_id, 'settings.xml')
        if not os.path.isfile(path):
            continue
        ver = _file_version(path)
        if ver is not None and ver > target:
            out.append((addon_id, ver))
    return out


def applicable():
    """Show the Maintenance entry only when this box needs it."""
    try:
        target = supported_version()
        return target is not None and bool(affected(target))
    except Exception as e:
        _log('applicable() failed: %s' % e, xbmc.LOGWARNING)
        return False


def _convert(path, target):
    with open(path, 'r', encoding='utf-8') as fh:
        data = fh.read()
    m = _HDR_RE.search(data[:512])
    if not m or int(m.group(2)) <= target:
        return False
    ver = int(m.group(2))
    bak = '%s.v%d.bak' % (path, ver)
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as fh:
            fh.write(data)
    new = data[:m.start()] + m.group(1) + str(target) + m.group(3) + data[m.end():]
    tmp = path + '.abk.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(new)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    return True


def run():
    from resources.lib.i18n import T
    dlg = xbmcgui.Dialog()
    target = supported_version()
    items = affected(target) if target is not None else []
    if not items:
        dlg.ok('ABUKARIM TOOLS', T(30902))
        return
    newest = max(v for _a, v in items)
    names = ', '.join(a for a, _v in items)
    if not dlg.yesno('ABUKARIM TOOLS', T(30901) % (len(items), newest, target, names)):
        return
    done, failed = [], []
    root = _addon_data()
    for addon_id, ver in items:
        path = os.path.join(root, addon_id, 'settings.xml')
        try:
            if _convert(path, target):
                done.append(addon_id)
                _log('%s: settings version %d -> %d' % (addon_id, ver, target))
        except Exception as e:
            failed.append(addon_id)
            _log('%s: convert failed: %s' % (addon_id, e), xbmc.LOGERROR)
    _log('target %d: converted %d, failed %d' % (target, len(done), len(failed)))
    if failed:
        dlg.ok('ABUKARIM TOOLS', T(30904) % (len(done), len(failed), ', '.join(failed)))
    else:
        dlg.ok('ABUKARIM TOOLS', T(30903) % len(done))
    if done:
        from resources.lib import origin_fix
        origin_fix.force_restart('add-on settings version')
