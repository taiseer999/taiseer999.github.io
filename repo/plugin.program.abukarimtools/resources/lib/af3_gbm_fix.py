# -*- coding: utf-8 -*-
"""
af3_gbm_fix.py  –  ABUKARIM TOOLS
UGOOS AM6B CoreELEC Fix: Arctic Fuse 3 GBM poster edge flicker workaround.

Applies bordersize=5 to Layout_Poster artwork so texture edges never touch the
atlas boundary — same approach as Aeon Nox Silvo commit 43bb68e. Fixes the
poster edge flicker/"tearing" seen after CoreELEC's fbdev→GBM switch
(nightly 20260623+) on Amlogic devices.

Standalone apply/revert tool — verified against AF3 5.4.1.1.
"""

import base64
import os
from xml.dom import minidom

import xbmc
import xbmcgui
import xbmcvfs

ADDON_NAME = 'ABUKARIM TOOLS'
SKIN_ID    = 'skin.arctic.fuse.3'
HOME       = xbmcvfs.translatePath('special://home/')
SKIN_DIR   = os.path.join(HOME, 'addons', SKIN_ID)
DIALOG     = xbmcgui.Dialog()

# ── AF3 GBM poster flicker fix blobs (verified 1:1 vs pristine AF3 5.4.1.1) ──
_OBJ_RECT_HEAD_OLD_B64 = 'ICAgIDxpbmNsdWRlIG5hbWU9Ik9iamVjdF9MYXlvdXRfSW1hZ2VfUmVjdGFuZ2xlIj4KICAgICAgICA8cGFyYW0gbmFtZT0iYXNwZWN0cmF0aW8iPmtlZXA8L3BhcmFtPgogICAgICAgIDxwYXJhbSBuYW1lPSJzZWxlY3RlZCI+ZmFsc2U8L3BhcmFtPgogICAgICAgIDxkZWZpbml0aW9uPgogICAgICAgICAgICA8Y29udHJvbCB0eXBlPSJpbWFnZSI+CiAgICAgICAgICAgICAgICA8dGV4dHVyZSBiYWNrZ3JvdW5kPSJ0cnVlIiBkaWZmdXNlPSIkUEFSQU1bZGlmZnVzZV0iPiRQQVJBTVtpY29uXTwvdGV4dHVyZT4KICAgICAgICAgICAgICAgIDxhc3BlY3RyYXRpbyBzY2FsZWRpZmZ1c2U9ImZhbHNlIj4kUEFSQU1bYXNwZWN0cmF0aW9dPC9hc3BlY3RyYXRpbz4='
_OBJ_RECT_HEAD_NEW_B64 = 'ICAgIDxpbmNsdWRlIG5hbWU9Ik9iamVjdF9MYXlvdXRfSW1hZ2VfUmVjdGFuZ2xlIj4KICAgICAgICA8cGFyYW0gbmFtZT0iYXNwZWN0cmF0aW8iPmtlZXA8L3BhcmFtPgogICAgICAgIDxwYXJhbSBuYW1lPSJzZWxlY3RlZCI+ZmFsc2U8L3BhcmFtPgogICAgICAgIDxwYXJhbSBuYW1lPSJib3JkZXJzaXplIj4wPC9wYXJhbT4KICAgICAgICA8ZGVmaW5pdGlvbj4KICAgICAgICAgICAgPGNvbnRyb2wgdHlwZT0iaW1hZ2UiPgogICAgICAgICAgICAgICAgPHRleHR1cmUgYmFja2dyb3VuZD0idHJ1ZSIgZGlmZnVzZT0iJFBBUkFNW2RpZmZ1c2VdIj4kUEFSQU1baWNvbl08L3RleHR1cmU+CiAgICAgICAgICAgICAgICA8Ym9yZGVyc2l6ZT4kUEFSQU1bYm9yZGVyc2l6ZV08L2JvcmRlcnNpemU+CiAgICAgICAgICAgICAgICA8YXNwZWN0cmF0aW8gc2NhbGVkaWZmdXNlPSJmYWxzZSI+JFBBUkFNW2FzcGVjdHJhdGlvXTwvYXNwZWN0cmF0aW8+'
_OBJ_RECT_ICON_OLD_B64 = 'ICAgICAgICAgICAgICAgIDxjb2xvcmRpZmZ1c2U+bWFpbl9mZ18xMDA8L2NvbG9yZGlmZnVzZT4KICAgICAgICAgICAgICAgIDx0ZXh0dXJlIGJhY2tncm91bmQ9InRydWUiIGRpZmZ1c2U9IiRQQVJBTVtkaWZmdXNlXSI+JFBBUkFNW2ljb25dPC90ZXh0dXJlPgogICAgICAgICAgICAgICAgPGFzcGVjdHJhdGlvIHNjYWxlZGlmZnVzZT0iZmFsc2UiPiRQQVJBTVthc3BlY3RyYXRpb108L2FzcGVjdHJhdGlvPgogICAgICAgICAgICAgICAgPHZpc2libGU+U3RyaW5nLlN0YXJ0c1dpdGgoJFBBUkFNW2xpc3RpdGVtXS5JY29uLERlZmF1bHQp'
_OBJ_RECT_ICON_NEW_B64 = 'ICAgICAgICAgICAgICAgIDxjb2xvcmRpZmZ1c2U+bWFpbl9mZ18xMDA8L2NvbG9yZGlmZnVzZT4KICAgICAgICAgICAgICAgIDx0ZXh0dXJlIGJhY2tncm91bmQ9InRydWUiIGRpZmZ1c2U9IiRQQVJBTVtkaWZmdXNlXSI+JFBBUkFNW2ljb25dPC90ZXh0dXJlPgogICAgICAgICAgICAgICAgPGJvcmRlcnNpemU+JFBBUkFNW2JvcmRlcnNpemVdPC9ib3JkZXJzaXplPgogICAgICAgICAgICAgICAgPGFzcGVjdHJhdGlvIHNjYWxlZGlmZnVzZT0iZmFsc2UiPiRQQVJBTVthc3BlY3RyYXRpb108L2FzcGVjdHJhdGlvPgogICAgICAgICAgICAgICAgPHZpc2libGU+U3RyaW5nLlN0YXJ0c1dpdGgoJFBBUkFNW2xpc3RpdGVtXS5JY29uLERlZmF1bHQp'
_OBJ_ICON_PARAM_OLD_B64 = 'ICAgIDxpbmNsdWRlIG5hbWU9Ik9iamVjdF9MYXlvdXRfSW1hZ2VfSWNvbiI+CiAgICAgICAgPHBhcmFtIG5hbWU9ImdlbnJlX2JvcmRlcnNpemUiPjUwPC9wYXJhbT4KICAgICAgICA8cGFyYW0gbmFtZT0ib3RoZXJfYm9yZGVyc2l6ZSI+MjA8L3BhcmFtPg=='
_OBJ_ICON_PARAM_NEW_B64 = 'ICAgIDxpbmNsdWRlIG5hbWU9Ik9iamVjdF9MYXlvdXRfSW1hZ2VfSWNvbiI+CiAgICAgICAgPHBhcmFtIG5hbWU9ImdlbnJlX2JvcmRlcnNpemUiPjUwPC9wYXJhbT4KICAgICAgICA8cGFyYW0gbmFtZT0ib3RoZXJfYm9yZGVyc2l6ZSI+MjA8L3BhcmFtPgogICAgICAgIDxwYXJhbSBuYW1lPSJib3JkZXJzaXplIj4wPC9wYXJhbT4='
_OBJ_ICON_FWD_OLD_B64 = 'ICAgICAgICAgICAgICAgIDxpbmNsdWRlIGNvbnRlbnQ9Ik9iamVjdF9MYXlvdXRfSW1hZ2VfUmVjdGFuZ2xlIiBjb25kaXRpb249IiFbJFBBUkFNW2luY2x1ZGVfZGlzY2FydF1dIj4KICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iZGlmZnVzZSI+JFBBUkFNW2RpZmZ1c2VdPC9wYXJhbT4KICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iaWNvbiI+JFBBUkFNW2ljb25dPC9wYXJhbT4KICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0ibGlzdGl0ZW0iPiRQQVJBTVtsaXN0aXRlbV08L3BhcmFtPgogICAgICAgICAgICAgICAgICAgIDxwYXJhbSBuYW1lPSJhc3BlY3RyYXRpbyI+JFBBUkFNW2FzcGVjdHJhdGlvXTwvcGFyYW0+CiAgICAgICAgICAgICAgICAgICAgPHBhcmFtIG5hbWU9InNlbGVjdGVkIj4kUEFSQU1bc2VsZWN0ZWRdPC9wYXJhbT4KICAgICAgICAgICAgICAgIDwvaW5jbHVkZT4='
_OBJ_ICON_FWD_NEW_B64 = 'ICAgICAgICAgICAgICAgIDxpbmNsdWRlIGNvbnRlbnQ9Ik9iamVjdF9MYXlvdXRfSW1hZ2VfUmVjdGFuZ2xlIiBjb25kaXRpb249IiFbJFBBUkFNW2luY2x1ZGVfZGlzY2FydF1dIj4KICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iZGlmZnVzZSI+JFBBUkFNW2RpZmZ1c2VdPC9wYXJhbT4KICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iaWNvbiI+JFBBUkFNW2ljb25dPC9wYXJhbT4KICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0ibGlzdGl0ZW0iPiRQQVJBTVtsaXN0aXRlbV08L3BhcmFtPgogICAgICAgICAgICAgICAgICAgIDxwYXJhbSBuYW1lPSJhc3BlY3RyYXRpbyI+JFBBUkFNW2FzcGVjdHJhdGlvXTwvcGFyYW0+CiAgICAgICAgICAgICAgICAgICAgPHBhcmFtIG5hbWU9InNlbGVjdGVkIj4kUEFSQU1bc2VsZWN0ZWRdPC9wYXJhbT4KICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iYm9yZGVyc2l6ZSI+JFBBUkFNW2JvcmRlcnNpemVdPC9wYXJhbT4KICAgICAgICAgICAgICAgIDwvaW5jbHVkZT4='
_LAY_POSTER_OLD_B64 = 'ICAgICAgICAgICAgICAgICAgICA8aW5jbHVkZSBjb250ZW50PSJPYmplY3RfTGF5b3V0X0ltYWdlX0ljb24iPgogICAgICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iZGlmZnVzZSI+JFBBUkFNW2RpZmZ1c2VdPC9wYXJhbT4KICAgICAgICAgICAgICAgICAgICAgICAgPHBhcmFtIG5hbWU9Imljb24iPiRQQVJBTVtpY29uXTwvcGFyYW0+CiAgICAgICAgICAgICAgICAgICAgICAgIDxwYXJhbSBuYW1lPSJsaXN0aXRlbSI+JFBBUkFNW2xpc3RpdGVtXTwvcGFyYW0+CiAgICAgICAgICAgICAgICAgICAgICAgIDxwYXJhbSBuYW1lPSJhc3BlY3RyYXRpbyI+c2NhbGU8L3BhcmFtPgogICAgICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0ic2VsZWN0ZWQiPiRQQVJBTVtzZWxlY3RlZF08L3BhcmFtPgogICAgICAgICAgICAgICAgICAgIDwvaW5jbHVkZT4='
_LAY_POSTER_NEW_B64 = 'ICAgICAgICAgICAgICAgICAgICA8aW5jbHVkZSBjb250ZW50PSJPYmplY3RfTGF5b3V0X0ltYWdlX0ljb24iPgogICAgICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iZGlmZnVzZSI+JFBBUkFNW2RpZmZ1c2VdPC9wYXJhbT4KICAgICAgICAgICAgICAgICAgICAgICAgPHBhcmFtIG5hbWU9Imljb24iPiRQQVJBTVtpY29uXTwvcGFyYW0+CiAgICAgICAgICAgICAgICAgICAgICAgIDxwYXJhbSBuYW1lPSJsaXN0aXRlbSI+JFBBUkFNW2xpc3RpdGVtXTwvcGFyYW0+CiAgICAgICAgICAgICAgICAgICAgICAgIDxwYXJhbSBuYW1lPSJhc3BlY3RyYXRpbyI+c2NhbGU8L3BhcmFtPgogICAgICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0ic2VsZWN0ZWQiPiRQQVJBTVtzZWxlY3RlZF08L3BhcmFtPgogICAgICAgICAgICAgICAgICAgICAgICA8cGFyYW0gbmFtZT0iYm9yZGVyc2l6ZSI+NTwvcGFyYW0+CiAgICAgICAgICAgICAgICAgICAgPC9pbmNsdWRlPg=='


def _pairs():
    """(rel_path, [(old, new), ...], sentinel) per target file."""
    return [
        (
            os.path.join('1080i', 'Includes_Objects.xml'),
            [
                (base64.b64decode(_OBJ_RECT_HEAD_OLD_B64).decode('utf-8'),
                 base64.b64decode(_OBJ_RECT_HEAD_NEW_B64).decode('utf-8')),
                (base64.b64decode(_OBJ_RECT_ICON_OLD_B64).decode('utf-8'),
                 base64.b64decode(_OBJ_RECT_ICON_NEW_B64).decode('utf-8')),
                (base64.b64decode(_OBJ_ICON_PARAM_OLD_B64).decode('utf-8'),
                 base64.b64decode(_OBJ_ICON_PARAM_NEW_B64).decode('utf-8')),
                (base64.b64decode(_OBJ_ICON_FWD_OLD_B64).decode('utf-8'),
                 base64.b64decode(_OBJ_ICON_FWD_NEW_B64).decode('utf-8')),
            ],
            '<param name="bordersize">0</param>\n        <definition>\n            <control type="image">',
        ),
        (
            os.path.join('1080i', 'Includes_Layouts.xml'),
            [
                (base64.b64decode(_LAY_POSTER_OLD_B64).decode('utf-8'),
                 base64.b64decode(_LAY_POSTER_NEW_B64).decode('utf-8')),
            ],
            '<param name="selected">$PARAM[selected]</param>\n                        <param name="bordersize">5</param>',
        ),
    ]


def _log(msg):
    xbmc.log('[AbukarimTools AM6B-Fix] %s' % msg, xbmc.LOGINFO)


def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _validate_xml(content, rel_path):
    try:
        minidom.parseString(content.encode('utf-8'))
        return True
    except Exception as exc:  # pylint: disable=broad-except
        _log('XML validation failed for %s: %r' % (rel_path, exc))
        return False


def _status():
    """Returns 'missing', 'pristine', 'patched', or 'partial'."""
    if not os.path.isdir(SKIN_DIR):
        return 'missing'
    states = []
    for rel_path, _replacements, sentinel in _pairs():
        target = os.path.join(SKIN_DIR, rel_path)
        if not os.path.isfile(target):
            return 'missing'
        states.append(sentinel in _read(target))
    if all(states):
        return 'patched'
    if any(states):
        return 'partial'
    return 'pristine'


def _apply(direction):
    """direction: 'apply' (old->new) or 'revert' (new->old)."""
    results = []
    for rel_path, replacements, sentinel in _pairs():
        target = os.path.join(SKIN_DIR, rel_path)
        content = _read(target)

        if direction == 'apply' and sentinel in content:
            results.append((True, '%s already patched – skipping.' % rel_path))
            continue
        if direction == 'revert' and sentinel not in content:
            results.append((True, '%s not patched – skipping.' % rel_path))
            continue

        patched = content
        ok = True
        for old, new in replacements:
            find, repl = (old, new) if direction == 'apply' else (new, old)
            if patched.count(find) != 1:
                results.append((False, '%s: anchor not found – skin version mismatch '
                                       '(fix is for AF3 5.4.1.1).' % rel_path))
                ok = False
                break
            patched = patched.replace(find, repl, 1)
        if not ok:
            continue

        if not _validate_xml(patched, rel_path):
            results.append((False, '%s: result failed XML validation – not written.' % rel_path))
            continue

        _write(target, patched)
        results.append((True, '%s %s OK.' % (rel_path,
                        'patched' if direction == 'apply' else 'reverted')))
    return results


def _show_results(title, results):
    lines = []
    for ok, msg in results:
        icon = '[COLOR lime]✔[/COLOR]' if ok else '[COLOR red]✘[/COLOR]'
        lines.append('%s  %s' % (icon, msg))
    failed = sum(1 for ok, _ in results if not ok)
    summary = '[B]%s[/B][CR][CR]' % title + '[CR]'.join(lines)
    summary += '[CR][CR]%d succeeded,  %d failed.' % (len(results) - failed, failed)
    DIALOG.ok(ADDON_NAME, summary)
    return failed == 0


def _reload_skin_if_active():
    try:
        if xbmc.getSkinDir() == SKIN_ID:
            if DIALOG.yesno(ADDON_NAME,
                            'Arctic Fuse 3 is the active skin.\n'
                            'Reload the skin now to apply the change?',
                            yeslabel='Reload', nolabel='Later'):
                xbmc.executebuiltin('ReloadSkin()')
    except Exception:  # pylint: disable=broad-except
        pass


def run():
    """Entry point called from default.py router."""
    _log('AM6B CoreELEC Fix started.')
    status = _status()

    if status == 'missing':
        DIALOG.ok(ADDON_NAME,
                  'Arctic Fuse 3 (%s) is not installed — nothing to fix.' % SKIN_ID)
        return

    if status in ('pristine', 'partial'):
        if not DIALOG.yesno(
                ADDON_NAME,
                '[B]AM6B CoreELEC Fix — AF3 GBM Poster Flicker[/B]\n\n'
                'Fixes poster edge flicker/tearing while navigating widgets on '
                'CoreELEC GBM builds (nightly 20260623+).\n'
                'Adds a 5px artwork inset to Layout_Poster (same fix as Aeon Nox Silvo).\n\n'
                'Apply to %s now?' % SKIN_ID,
                yeslabel='Apply fix', nolabel='Cancel'):
            return
        results = _apply('apply')
        if _show_results('AM6B GBM Flicker Fix — Applied', results):
            _reload_skin_if_active()
        _log('Apply finished.')
        return

    # status == 'patched' → offer revert
    choice = DIALOG.yesno(
        ADDON_NAME,
        'The GBM flicker fix is already applied to %s.\n\n'
        'Do you want to remove it (restore original files)?' % SKIN_ID,
        yeslabel='Remove fix', nolabel='Keep it')
    if not choice:
        return
    results = _apply('revert')
    if _show_results('AM6B GBM Flicker Fix — Removed', results):
        _reload_skin_if_active()
    _log('Revert finished.')
