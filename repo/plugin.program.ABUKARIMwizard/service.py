from resources.lib.modules._service import Startup


def _release_kodi_objects():
    """3.9.52: modules keep Addon / Dialog / DialogProgress objects as globals
    (addonvar.dialog, addonvar.dp, whitelist.dialog, quick_log.text_view ...).
    Still alive when the service ends, Kodi logs "has left several classes in
    memory that we couldn't clean up". Drop them before the interpreter exits."""
    import sys
    import xbmcaddon
    import xbmcgui
    kinds = (xbmcaddon.Addon, xbmcgui.Dialog, xbmcgui.DialogProgress)
    for name, mod in list(sys.modules.items()):
        if not name.startswith('resources.') or mod is None:
            continue
        for attr, val in list(vars(mod).items()):
            owner = getattr(val, '__self__', None)
            if isinstance(val, kinds) or isinstance(owner, kinds):
                try:
                    delattr(mod, attr)
                except Exception:
                    pass


if __name__ == '__main__':
    s = Startup()
    try:
        s.run_startup()
    finally:
        del s
        try:
            _release_kodi_objects()
        except Exception:
            pass
