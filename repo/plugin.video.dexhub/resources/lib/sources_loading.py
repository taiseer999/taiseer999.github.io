# -*- coding: utf-8 -*-
"""Loading window shown while Dex Hub gathers sources from providers.

Provides a cancellable, POV/SALTS-style "Searching..." overlay with live
provider progress. The window is a `WindowXMLDialog` so it renders above
Kodi's main window (including over the catalog listing).

Usage:

    from .sources_loading import SourcesLoadingDialog

    with SourcesLoadingDialog(title='Killers of the Flower Moon (2023)',
                              provider_count=5) as loader:
        for idx, provider in enumerate(providers, 1):
            if loader.is_cancelled():
                break
            loader.update(provider_name=provider['name'], index=idx,
                          results_so_far=len(found))
            # fetch...
            loader.add_results(n=len(new_results))

The dialog auto-closes when the `with` block exits. If `is_cancelled()`
returns True, the caller should abort its fetch loop.
"""
import os

import xbmc
import xbmcgui
import xbmcaddon

from .i18n import tr

ADDON = xbmcaddon.Addon()

_SKIN_FILE = 'sources_loading.xml'
_SKIN_RES = 'Default'
_SKIN_DIMS = '1080i'


def _addon_path():
    return ADDON.getAddonInfo('path')


class _LoadingWindow(xbmcgui.WindowXMLDialog):
    """Internal dialog. Prefer SourcesLoadingDialog context manager."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cancelled = False

    def onInit(self):
        # Make the cancel button keyboard-accessible.
        try:
            self.setFocusId(9000)
        except Exception:
            pass

    def onAction(self, action):
        # Back / ESC cancel the fetch.
        action_id = action.getId()
        if action_id in (10, 92, 216, 247, 257, 275):  # ACTION_PREVIOUS_MENU / BACK
            self._cancelled = True
            self.close()
        else:
            super().onAction(action)

    def onClick(self, control_id):
        if control_id == 9000:
            self._cancelled = True
            self.close()

    def is_cancelled(self):
        return self._cancelled


class SourcesLoadingDialog(object):
    """Context-managed wrapper around the loading WindowXMLDialog.

    Safe to use even if the XML is missing — falls back to a no-op so the
    caller never crashes. All setter methods silently no-op when the
    window isn't actually showing.
    """

    def __init__(self, title='', subtitle='', fanart='', provider_count=0):
        self._title = title
        self._subtitle = subtitle
        self._fanart = fanart
        self._provider_count = max(0, int(provider_count or 0))
        self._results_so_far = 0
        self._win = None
        self._opened = False

    def __enter__(self):
        try:
            self._win = _LoadingWindow(_SKIN_FILE, _addon_path(), _SKIN_RES, _SKIN_DIMS)
        except Exception:
            self._win = None
            return self
        self._apply_initial_props()
        try:
            self._win.show()
            self._opened = True
        except Exception:
            self._win = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._win is not None:
                self._win.close()
        except Exception:
            pass
        self._win = None
        self._opened = False
        return False  # don't suppress exceptions

    def _apply_initial_props(self):
        if self._win is None:
            return
        self._set('title', self._title)
        self._set('subtitle', self._subtitle)
        self._set('fanart', self._fanart)
        self._set('status', tr('جار البحث عن المصادر...'))
        self._set('sub_status', '')
        self._set('progress_pct', '0')
        self._set('results_line', '')
        self._set('cancel_label', tr('إلغاء') or 'Cancel')
        if self._provider_count:
            self._set('providers_line',
                      '%s 0 / %d' % (tr('المصادر'), self._provider_count))
        else:
            self._set('providers_line', '')

    def _set(self, key, value):
        if self._win is None:
            return
        try:
            self._win.setProperty(key, str(value or ''))
        except Exception:
            pass

    def is_cancelled(self):
        if self._win is None:
            return False
        try:
            return bool(self._win.is_cancelled())
        except Exception:
            return False

    def update(self, provider_name='', index=0, status=None, sub_status=None):
        """Update the window while the caller makes progress."""
        if self._win is None:
            return
        if status is not None:
            self._set('status', status)
        if sub_status is not None:
            self._set('sub_status', sub_status)
        if index and self._provider_count:
            pct = max(0, min(100, int(round(100.0 * index / self._provider_count))))
            self._set('progress_pct', str(pct))
            line = '%s %d / %d' % (tr('المصادر'), index, self._provider_count)
            if provider_name:
                line = '%s  •  %s' % (line, provider_name)
            self._set('providers_line', line)

    def add_results(self, n=0):
        self._results_so_far += max(0, int(n or 0))
        if self._results_so_far:
            noun = 'sources found' if tr('نعم') == 'Yes' else tr('مصدر')
            self._set('results_line', '%d %s' % (self._results_so_far, noun))

    def set_finalizing(self, msg=None):
        """Switch to a final "organizing results..." state."""
        self._set('status', msg or (tr('جار جلب نتائج إضافية...')))
        self._set('progress_pct', '100')
