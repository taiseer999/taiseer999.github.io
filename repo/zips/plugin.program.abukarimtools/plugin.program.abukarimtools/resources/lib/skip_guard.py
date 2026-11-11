# -*- coding: utf-8 -*-
"""
skip_guard.py - "Skip this step?" confirmation for the Installation Wizard.

3.4.21: every way of skipping a wizard step (a Skip button, Back on a picker,
closing the Add-on Portal / Skin Installer without choosing) now asks first:

    Skip this step?   [Yes, skip]   [Back to the step]

confirm() returns True only when the user really chose "Yes, skip". Back (or
"Back to the step") returns False and the caller shows the step again.

A dialog answered faster than a human can (swallowed by a skin reload or an
add-on rescan - same family as dialog_guard / the restore popup) is shown
again. If it is swallowed every time, the skip goes through as before, so the
wizard can never loop forever.
"""

import time

import xbmc
import xbmcgui

from resources.lib.i18n import T

MIN_HUMAN_S = 1.0
ATTEMPTS = 4


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools SkipGuard] %s' % msg, level)


def _settle(mon, seconds=2.0):
    waited = 0.0
    while waited < 8 and not mon.abortRequested():
        if not xbmc.getCondVisibility('System.HasModalDialog') and waited >= seconds:
            return
        xbmc.sleep(250)
        waited += 0.25


def confirm(step_name):
    """Ask before skipping `step_name`. True = skip, False = back to the step."""
    mon = xbmc.Monitor()
    if mon.abortRequested():
        return True
    for attempt in range(1, ATTEMPTS + 1):
        _settle(mon, 0.5 if attempt == 1 else 2.0)
        if mon.abortRequested():
            return True
        started = time.time()
        yes = xbmcgui.Dialog().yesno(T(30760), T(30761) % step_name,
                                     yeslabel=T(30762), nolabel=T(30763))
        if yes:
            _log('skip confirmed: %s' % step_name)
            return True
        if time.time() - started >= MIN_HUMAN_S:
            _log('skip cancelled - back to the step: %s' % step_name)
            return False
        _log('confirmation dismissed instantly (attempt %d) - asking again'
             % attempt)
    _log('confirmation swallowed %d times - skipping %s'
         % (ATTEMPTS, step_name), xbmc.LOGWARNING)
    return True
