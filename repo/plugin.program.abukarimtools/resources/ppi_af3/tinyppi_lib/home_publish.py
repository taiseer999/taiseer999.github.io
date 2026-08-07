"""Approach A helper (by ABUKARIM TOOLS): publish TinyPPI's player data onto the
Home window (10000) so a native skin dialog — Arctic Fuse 3's
DialogPlayerProcessInfo — can read it via $INFO[Window(10000).Property(*Var)]
even when TinyPPI's own overlay window is closed.

This module deliberately does NOT edit properties.py. TinyPPI's own
``update_properties(window)`` already writes every *Var onto whatever window it
is handed; we simply hand it a thin proxy for the Home window. That keeps this
version-agnostic: it works against whatever TinyPPI build is installed, with no
dependency on that build's internal structure (no whole-file replacement, so no
version-drift breakage such as a missing ``coded_frame`` import).

Started by the service (monitor.py) on a background thread while video plays.
"""

import os
import threading

import xbmc
import xbmcgui

_HOME_ID = 10000
_ADDON_ID = "script.tinyppi"

# Absolute media root for the channel-layout graphics, so a FOREIGN skin dialog
# (whose own media folder lacks TinyPPI's "channels/…" files) can still draw the
# speaker diagram. TinyPPI's own window keeps using the relative paths.
_MEDIA_ROOT = ("special://home/addons/%s/resources/skins/Default/media/"
               % _ADDON_ID)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("TinyPPI-PPIAF3: %s" % msg, level)


class _HomeProxy:
    """Quacks like an xbmcgui.Window for TinyPPI's update_properties():

    * setProperty / getProperty / clearProperty forward to the real Home window,
      so every *Var TinyPPI computes lands on Window(10000).
    * getControl returns a dummy whose setPercent is a no-op — Home has no
      progress controls (the overlay used control id 9100), and the skin dialog
      binds its <progress> to infolabels / a published property instead.
    """

    class _NullControl:
        def setPercent(self, _value):
            pass

        def setLabel(self, *_a, **_k):
            pass

        def setVisible(self, *_a, **_k):
            pass

    def __init__(self):
        self._home = xbmcgui.Window(_HOME_ID)
        self._null = self._NullControl()

    def setProperty(self, key, value):
        self._home.setProperty(key, value)

    def getProperty(self, key):
        return self._home.getProperty(key)

    def clearProperty(self, key):
        self._home.clearProperty(key)

    def getControl(self, _control_id):
        return self._null


def _publish_absolute_channel_paths(home):
    """Add absolute special:// twins of the two relative channel-image props so a
    foreign skin dialog can render them. Empty stays empty."""
    for rel_name, abs_name in (("ChannelLayerVar", "ChannelLayerAbsVar"),
                               ("ChannelIconVar", "ChannelIconAbsVar")):
        rel = home.getProperty(rel_name)
        home.setProperty(abs_name, (_MEDIA_ROOT + rel) if rel else "")


def _publish_cpu_temp_progress(home):
    """Publish the 0-100 CPU-temperature progress as a Home property so the skin
    dialog can bind a <progress> to it (the overlay used a control id instead)."""
    try:
        from info.properties import get_CpuTemperatureProgressVar
        home.setProperty("TinyPPI.CpuTempProgress",
                         str(get_CpuTemperatureProgressVar()))
    except Exception:
        pass


def publish_once():
    """Compute TinyPPI's player properties straight onto Home (10000)."""
    from info import properties  # the installed build's own module

    proxy = _HomeProxy()
    properties.update_properties(proxy)

    home = xbmcgui.Window(_HOME_ID)
    _publish_absolute_channel_paths(home)
    _publish_cpu_temp_progress(home)


def _enabled():
    """Opt-out via a settings flag; default ON."""
    try:
        import xbmcaddon
        return xbmcaddon.Addon().getSetting("home_publish") != "false"
    except Exception:
        return True


class HomePublisher(threading.Thread):
    """Keeps Home (10000) fresh with TinyPPI data while video plays, so the AF3
    dialog shows live values without TinyPPI's own overlay being open."""

    _INTERVAL = 1.0

    def __init__(self, monitor):
        super().__init__(name="TinyPPI-PPIAF3-HomePublisher", daemon=True)
        self._monitor = monitor
        self._player = xbmc.Player()

    def run(self):
        _log("Home publisher started")
        while not self._monitor.abortRequested():
            try:
                playing = (self._player.isPlaying()
                           and xbmc.getCondVisibility("Player.HasVideo"))
            except Exception:
                playing = False

            if not (playing and _enabled()):
                if self._monitor.waitForAbort(2.0):
                    break
                continue

            try:
                publish_once()
            except Exception as exc:
                _log("publish failed: %s" % exc, xbmc.LOGERROR)

            if self._monitor.waitForAbort(self._INTERVAL):
                break
        _log("Home publisher stopped")


def start(monitor):
    """Start the background publisher; safe to call once from the service."""
    try:
        HomePublisher(monitor).start()
    except Exception as exc:  # pragma: no cover
        _log("failed to start: %s" % exc, xbmc.LOGWARNING)
