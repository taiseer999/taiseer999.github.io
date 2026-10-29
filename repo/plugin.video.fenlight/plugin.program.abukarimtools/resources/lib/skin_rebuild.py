# -*- coding: utf-8 -*-
"""
skin_rebuild.py - make a skinvariables skin (Arctic Fuse 2/3) really rebuild
its home menus / widgets after its nodes were changed on disk.

Why (3.2.43~beta8, from a kodi.log where "rebuild queued" did nothing):
the skin's skinvariables-build-templates.json runs

    route=action=buildtemplate&lastbuildtime={Skin.String(Shortcuts.RebuildDateTime)}

and script.skinvariables only regenerates when the hash of (those arguments +
the generator template + profile name) differs from the stored
Skin.String(script-skinvariables-generator-hash). The NODE FILES ARE NOT PART
OF THAT HASH, so after replacing them a plain RunScript(...build-templates...)
sees "already up to date" and returns silently. The skin's own editor and the
ABUKARIM Wizard's Patch GUI bump Shortcuts.RebuildDateTime first - so do we.

  * active skin   -> Skin.SetString(Shortcuts.RebuildDateTime,<now>) and run
                     the build (skinvariables regenerates and reloads the skin)
  * other skin    -> Kodi only keeps the ACTIVE skin's settings in memory, so
                     its addon_data/<skin>/settings.xml is edited directly:
                     new RebuildDateTime, generator hash(es) emptied. The menus
                     are rebuilt the next time that skin loads.
"""

import os
import re
import time

import xbmc
import xbmcvfs

ADDON_DATA = xbmcvfs.translatePath('special://profile/addon_data/')
STAMP_ID = 'Shortcuts.RebuildDateTime'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SkinRebuild] %s' % msg, level)


def _stamp():
    return time.strftime('%Y-%m-%d_%H:%M:%S')


def _templates_exist(skin_id):
    p = xbmcvfs.translatePath('special://home/addons/%s/shortcuts/'
                              'skinvariables-build-templates.json' % skin_id)
    return os.path.isfile(p)


def _mark_settings_file(skin_id, stamp):
    """Bump the stamp and empty the generator hashes in a non-active skin."""
    path = os.path.join(ADDON_DATA, skin_id, 'settings.xml')
    if not os.path.isfile(path):
        _log('%s: no settings.xml - it builds from scratch on first load' % skin_id)
        return False
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    new = re.sub(
        r'(<setting id="script-skinvariables-generator[^"]*-hash"[^>]*?)'
        r'(?:/>|>[^<]*</setting>)',
        r'\1></setting>', text)
    stamp_re = re.compile(r'(<setting id="%s"[^>]*?)(?:/>|>[^<]*</setting>)'
                          % re.escape(STAMP_ID))
    if stamp_re.search(new):
        new = stamp_re.sub(lambda m: '%s>%s</setting>' % (m.group(1), stamp), new)
    else:
        new = new.replace('</settings>',
                          '    <setting id="%s" type="string">%s</setting>\n'
                          '</settings>' % (STAMP_ID, stamp), 1)
    if new == text:
        return False
    tmp = path + '.abk.part'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(new)
    os.replace(tmp, path)
    _log('%s: rebuild armed in settings.xml (stamp %s)' % (skin_id, stamp))
    return True


# ---------------------------------------------------------------------------
# skinvariables activity (3.2.47) - lets the patcher hold its ReloadSkin() until
# a skinvariables build has finished. skinvariables sets no "busy" property; the
# only evidence is: a build we started, its progress window, and the
# script-skinvariables-*.xml files it writes into the skin right before it
# calls ReloadSkin() itself.
# ---------------------------------------------------------------------------
BUILD_MARKER = os.path.join(ADDON_DATA, 'plugin.program.abukarimtools',
                            'skinvariables_build.started')
SV_START_GRACE = 30     # s: a build we started counts as running until it writes
SV_QUIET       = 10     # s: generated files must be still this long = finished


def _note_build_started():
    try:
        os.makedirs(os.path.dirname(BUILD_MARKER), exist_ok=True)
        with open(BUILD_MARKER, 'w') as f:
            f.write(str(time.time()))
    except Exception as e:
        _log('could not note build start: %s' % e, xbmc.LOGWARNING)


def last_generated_write():
    """mtime of the newest script-skinvariables-*.xml in the active skin (0 if none)."""
    newest = 0.0
    try:
        root = xbmcvfs.translatePath('special://skin/')
        for d in os.listdir(root):
            full = os.path.join(root, d)
            if not os.path.isdir(full):
                continue
            for f in os.listdir(full):
                if f.startswith('script-skinvariables') and f.endswith('.xml'):
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(full, f)))
                    except OSError:
                        pass
    except Exception:
        pass
    return newest


def busy():
    """Return a reason string while skinvariables is (probably) still building,
    else ''. Never raises."""
    try:
        now = time.time()
        last = last_generated_write()
        if last and now - last < SV_QUIET:
            return 'skin files written %ds ago' % int(now - last)
        if xbmc.getCondVisibility('Window.IsActive(progressdialog) | '
                                  'Window.IsActive(extendedprogressdialog)'):
            return 'progress window open'
        if os.path.exists(BUILD_MARKER):
            started = os.path.getmtime(BUILD_MARKER)
            if last >= started:
                os.remove(BUILD_MARKER)          # the build we started finished
            elif now - started < SV_START_GRACE:
                return 'build started %ds ago' % int(now - started)
            else:
                os.remove(BUILD_MARKER)          # nothing to rebuild (hash equal)
    except Exception as e:
        _log('busy check failed: %s' % e, xbmc.LOGWARNING)
    return ''


def force(skin_id):
    """Rebuild skin_id's skinvariables menus now (active) or on next load."""
    stamp = _stamp()
    if skin_id == xbmc.getSkinDir():
        if not _templates_exist(skin_id):
            return False
        _note_build_started()
        xbmc.executebuiltin('Skin.SetString(%s,%s)' % (STAMP_ID, stamp))
        xbmc.executebuiltin('RunScript(script.skinvariables,run_executebuiltin='
                            'special://skin/shortcuts/skinvariables-build-templates.json,'
                            'use_rules)')
        _log('%s: rebuild started (active skin, stamp %s)' % (skin_id, stamp))
        return True
    try:
        return _mark_settings_file(skin_id, stamp)
    except Exception as e:
        _log('%s: could not arm rebuild: %s' % (skin_id, e), xbmc.LOGWARNING)
        return False
