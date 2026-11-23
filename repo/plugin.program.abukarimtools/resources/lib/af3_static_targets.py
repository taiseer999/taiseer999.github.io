# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
af3_static_targets.py - 4.12.22: finish the 4.12.18 GUI-freeze fix.

The deadlock (Kodi core, CDirectoryProvider, still in xbmc master):
  job worker : OnJobComplete() holds the provider lock -> StartDirectoryJob()
               -> <content target> GetLabel -> Window.Property / Container.*
               -> GUIINFO::GetWindow -> needs the GUI lock
  render loop: holds the GUI lock -> Container(x).IsUpdating -> provider lock
Any <content target="$INFO[...]"> whose info goes through the GUI windows can
hang Kodi. A plain-text target is never evaluated, so it never blocks.

4.12.18 fixed it with two fixed-path regex entries in patcher.py. Crashlog
2026-11-22 20:28 (on 4.12.21, boot sweep "0 written") hung the same way,
JobWorker in StartDirectoryJob -> CGUIControlsGUIInfo::GetLabel ->
GUIINFO::GetWindow, so a dynamic target was still loaded. Gaps closed here:
  * every generated file, not only "...-includes-.xml": a skin user
    (SkinVariables.SkinUser) loads script-skinvariables-generator-includes-
    <user>.xml through script-skinvariables-skinusers.xml;
  * any GUI-window info in a target, not only WidgetMeta.*.Target;
  * a menu rebuild after the sweep (skinvariables rewrites the file mid-
    session) is caught by poll() from the watchdog loop, not at next boot.
Each dynamic target found is logged with its file and value, so the next
log proves what was loaded. Value written: "videos" (Piers is a video build;
the skin itself sets WidgetMeta.*.Target to videos for every non-music item).
"""

import os
import re

import xbmc
import xbmcvfs

SKIN_ID = 'skin.arctic.fuse.3'
STATIC = 'videos'
_TAG = '[AbukarimTools StaticTargets]'

# Info that Kodi resolves through the GUI window list (CGUIControlsGUIInfo /
# GUIINFO::GetWindow): Window.Property, Window(x).Property, Container.*,
# Container(n).*, Control.*, System.CurrentWindow/Control.
_GUI_INFO = r'\$(?:ESC)?INFO\[\s*(?:Window|Container|Control|System\.Current)[^\]]*\]'
# <content ... target="...$INFO[..]...">  (attribute anywhere in the tag)
_ATTR_RE = re.compile(r'(<content\b[^>]*?\btarget=")([^"]*' + _GUI_INFO + r'[^"]*)(")')
# <param name="categorytarget">...</param> / <param name="target">...</param>
_PARAM_RE = re.compile(r'(<param name="(?:category)?target">)([^<]*' + _GUI_INFO + r'[^<]*)(</param>)')

_mtimes = {}


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('%s %s' % (_TAG, msg), level)


def _skin_root():
    p = xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID)
    return p if os.path.isdir(p) else None


def _generated_files(root):
    out = []
    for res in ('1080i', '720p', '2160i'):
        d = os.path.join(root, res)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.startswith('script-skinvariables-generator') and name.endswith('.xml'):
                out.append(os.path.join(d, name))
    return out


def _fix_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
    except (IOError, OSError, UnicodeDecodeError):
        return 0
    found = []

    def _sub(m):
        found.append(m.group(2))
        return m.group(1) + STATIC + m.group(3)

    new = _ATTR_RE.sub(_sub, src)
    new = _PARAM_RE.sub(_sub, new)
    if not found or new == src:
        return 0
    tmp = path + '.abk_tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(new)
    os.replace(tmp, path)
    for v in sorted(set(found)):
        _log('%s: dynamic target %s -> %s (%d)'
             % (os.path.basename(path), v, STATIC, found.count(v)))
    return len(found)


def apply():
    """Fix every generated include file. Returns (ok, msg, wrote) like the
    other apply_set helpers. Idempotent, never raises."""
    try:
        root = _skin_root()
        if not root:
            return True, '[%s] not installed - static targets skipped.' % SKIN_ID, False
        total = 0
        files = _generated_files(root)
        for path in files:
            total += _fix_file(path)
            try:
                _mtimes[path] = os.path.getmtime(path)
            except OSError:
                pass
        if total:
            return True, ('[%s] Patched OK: static widget targets (%d in %d file(s))'
                          % (SKIN_ID, total, len(files))), True
        return True, ('[%s] Static widget targets already in place (%d file(s)).'
                      % (SKIN_ID, len(files))), False
    except Exception as e:
        return False, '[%s] static targets failed: %s' % (SKIN_ID, e), False


def poll():
    """Cheap check from the watchdog loop: re-fix a generated file that
    skinvariables rewrote since the last look. True if something was written."""
    try:
        root = _skin_root()
        if not root:
            return False
        wrote = False
        for path in _generated_files(root):
            try:
                mt = os.path.getmtime(path)
            except OSError:
                continue
            if _mtimes.get(path) == mt:
                continue
            if _fix_file(path):
                wrote = True
            try:
                _mtimes[path] = os.path.getmtime(path)
            except OSError:
                pass
        return wrote
    except Exception as e:
        _log('poll failed (ignored): %s' % e, xbmc.LOGWARNING)
        return False
