# -*- coding: utf-8 -*-
"""
af3_flagstyle.py - ABUKARIM TOOLS (4.8.68, Lucent + samples 4.8.69, Black & White replaces Neon 4.8.73)

Toggles entry "AF3: OSD Flags Style" - a selection dialog with a sample
picture of every option (resources/flagstyle_samples/<style>.png):

    auto        (default) follows "AF3: Lucent Look": Lucent badges while the
                Lucent Look is on, the classic colour badges otherwise
    colorful    the classic colour badges (resource.images.af3.classicflags)
    lucent      white glass pills like the Lucent info pills  \
    glass       FR-Badges Glass          \
    blackwhite  FR-Badges Black & White   |  resource.images.af3.frbadges
    whiteblack  FR-Badges White & Black   |  (MIT, farizmohd70/FR-Badges,
    minimal     FR-Badges Minimal         |   mapped onto the classic layout:
    light       FR-Badges Light          /    audio/ channels/ source/ ...)

The Piers AF3 reads every OSD / footer badge through the skin variable
Flags_Badge_Directory (Includes_Colors.xml), which already holds full
resource:// paths. reconcile() puts ONE marked <value> line first in that
variable for the chosen FR style, gated on the add-on being enabled:

  <value condition="System.AddonIsEnabled(resource.images.af3.frbadges)">
      resource://resource.images.af3.frbadges/<style></value>  <!-- ABUKARIM: flag style -->

so with the add-on missing or disabled the skin falls straight back to the
classic colourful / monochrome lines below it. "Classic" removes the line.
patcher.apply_set runs reconcile() after every patch pass, so an AF3 update
gets the chosen style back. The skin still gates the OSD extras row and the
footer codec row on resource.images.af3.classicflags (AF3: Classic OSD
Flags), so picking an FR style also switches that toggle on.

4.8.69 - the AF3 Lucent Player draws its own pills (media/abk_lp/flags) in
the OSD, the pause card and the footer row. Those now go through the skin
variable ABK_LP_FlagDir (Includes_ABK_LucentPlayer.xml,
tools/lucent_player/af3_flagstyle.py), which reads Skin.String(abk.flagstyle):
empty = the Lucent pills (Automatic / Lucent), otherwise
resource://resource.images.af3.frbadges/<style>/lucent_player/ (same file
names as the Lucent pills). sync_skin_string() keeps that string in step.

Any explicit pick (Classic included) overrides the Lucent Look: only "auto"
lets the Lucent Look choose. resource.images.af3.frbadges is a hard
requirement of AB Tools (4.8.69), and start_boot_ensure() puts it back when
it is missing or disabled whatever the style.

The choice is saved in addon_data (af3_flagstyle.json).
"""
import json
import os
import re
import threading

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
RES_ID = 'resource.images.af3.frbadges'
TITLE = 'ABUKARIM TOOLS'
DEFAULT = 'auto'
CLASSIC = 'colorful'
# (style, label id, description id shown under the label in the picker)
STYLES = (('auto', 32242, 32243), ('colorful', 32231, 32244), ('lucent', 32241, 32245),
          ('glass', 32232, 32246), ('whiteblack', 32234, 32248), ('blackwhite', 32233, 32247),
          ('minimal', 32235, 32249), ('light', 32236, 32250))
_LABEL = {k: l for k, l, _d in STYLES}
_SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        'resources', 'flagstyle_samples')
MARK = '<!-- ABUKARIM: flag style -->'
_VAR_RE = re.compile(r'(<variable name="Flags_Badge_Directory">)(.*?)(</variable>)', re.S)
_MARK_LINE_RE = re.compile(r'\n[ \t]*<value[^\n]*' + re.escape(MARK) + r'[^\n]*')
_STATE = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/'),
                      'plugin.program.abukarimtools', 'af3_flagstyle.json')
_ADDONS = xbmcvfs.translatePath('special://home/addons/')
_LOCK = threading.Lock()


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools FlagStyle] %s' % msg, level)


def get_style():
    try:
        with open(_STATE, 'r', encoding='utf-8') as f:
            st = json.load(f).get('style')
        return st if st in _LABEL else DEFAULT
    except Exception:
        return DEFAULT


def set_style(style):
    try:
        os.makedirs(os.path.dirname(_STATE), exist_ok=True)
        with open(_STATE, 'w', encoding='utf-8') as f:
            json.dump({'style': style}, f)
    except Exception as e:
        _log('state not saved: %s' % e, xbmc.LOGWARNING)


def mode_label(style=None):
    return T(_LABEL[style or get_style()])


def _is_local(addon_id):
    return os.path.isfile(os.path.join(_ADDONS, addon_id, 'addon.xml'))


def res_ready():
    return bool(xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % RES_ID))


def _repo_id():
    try:
        from resources.lib import origin_fix
        return origin_fix.AF3_REPO
    except Exception:
        return 'repository.taiseer'


def ensure():
    """Install + enable resource.images.af3.frbadges from AF3's repository
    (same path as AF3: Classic OSD Flags). Silent, never raises."""
    if res_ready():
        return True
    if not _LOCK.acquire(False):
        return False
    repo = _repo_id()
    try:
        from resources.lib import addon_portal as ap
        if _is_local(RES_ID):
            return ap._enable(RES_ID)
        try:
            from resources.lib import origin_fix
            origin_fix.ensure_repo_installed(repo)
        except Exception as e:
            _log('repo check failed: %s' % e, xbmc.LOGWARNING)
        ok = False
        if _is_local(repo):
            zip_url, ver = ap._resolve_zip_in_repo(repo, RES_ID)
            if zip_url:
                _log('%s %s <- %s' % (RES_ID, ver, zip_url))
                ok = ap._install_zip(zip_url, RES_ID)
        if not ok:
            _log('%s: falling back to InstallAddon' % RES_ID, xbmc.LOGWARNING)
            ok = ap._kodi_install(RES_ID)
        if not ok:
            _log('%s could not be installed' % RES_ID, xbmc.LOGWARNING)
            return False
        enabled = ap._enable(RES_ID)
        ap._force_origin(RES_ID, repo)
        _log('%s installed from %s (enabled=%s)' % (RES_ID, repo, enabled))
        return enabled
    except Exception as e:
        _log('install failed: %s' % e, xbmc.LOGWARNING)
        return False
    finally:
        _LOCK.release()


def _skin_dir():
    try:
        from resources.lib import patcher
        d = patcher._resolve_addon_dir(SKIN_ID)
        if d:
            return d
    except Exception:
        pass
    d = xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID)
    return d if os.path.isdir(d) else None


def apply_to_text(content, style):
    """Pure text step (unit-testable). Returns (new_content, status) where
    status is 'ok', 'novar' (variable missing) or 'oldskin' (folder-name
    layout from before 50.11.68 - FR styles need the resource:// layout)."""
    m = _VAR_RE.search(content)
    if not m:
        return content, 'novar'
    body = _MARK_LINE_RE.sub('', m.group(2))
    if style != CLASSIC:
        if 'resource://' not in body:
            return content[:m.start(2)] + body + content[m.end(2):], 'oldskin'
        indent = re.search(r'\n([ \t]*)<value', body)
        indent = indent.group(1) if indent else ' ' * 8
        if style == DEFAULT:          # follow the Lucent Look
            cond, folder = 'Skin.HasSetting(abk.lucent) + System.AddonIsEnabled(%s)' % RES_ID, 'lucent'
        else:                         # explicit pick: wins over the Lucent Look
            cond, folder = 'System.AddonIsEnabled(%s)' % RES_ID, style
        line = ('\n%s<value condition="%s">resource://%s/%s</value>  %s'
                % (indent, cond, RES_ID, folder, MARK))
        body = line + body
    return content[:m.start(2)] + body + content[m.end(2):], 'ok'


def lp_style(style=None):
    """Value of Skin.String(abk.flagstyle) for the Lucent Player pills."""
    style = style or get_style()
    return '' if style in (DEFAULT, 'lucent') else style


def sync_skin_string(style=None):
    """Skin strings belong to the active skin: only while AF3 is active.
    Returns True when the value changed."""
    if xbmc.getSkinDir() != SKIN_ID:
        return False
    want = lp_style(style)
    if xbmc.getInfoLabel('Skin.String(abk.flagstyle)') == want:
        return False
    if want:
        xbmc.executebuiltin('Skin.SetString(abk.flagstyle,%s)' % want)
    else:
        xbmc.executebuiltin('Skin.Reset(abk.flagstyle)')
    _log('Skin.String(abk.flagstyle) -> %r' % want)
    return True


def reconcile(skin_dir=None):
    """Put the chosen style on Flags_Badge_Directory. Returns (ok, msg, wrote)."""
    skin_dir = skin_dir or _skin_dir()
    if not skin_dir:
        return True, '[flag style] AF3 not installed - skipping.', False
    path = os.path.join(skin_dir, '1080i', 'Includes_Colors.xml')
    if not os.path.isfile(path):
        return True, '[flag style] Includes_Colors.xml not found - skipping.', False
    style = get_style()
    try:
        sync_skin_string(style)
    except Exception as e:
        _log('skin string: %s' % e, xbmc.LOGWARNING)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        new, status = apply_to_text(content, style)
        if status == 'novar':
            return True, '[flag style] Flags_Badge_Directory not in this AF3 - skipping.', False
        wrote = new != content
        if wrote:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new)
        if status == 'oldskin':
            return True, '[flag style] %s: this AF3 has no resource:// flags (pre-50.11.68) - classic kept.' % style, wrote
        return True, ('[flag style] Patched OK: %s.' if wrote else '[flag style] %s - nothing to change.') % style, wrote
    except Exception as e:
        return False, '[flag style] %s' % e, False


def _reload_af3():
    if xbmc.getSkinDir() != SKIN_ID:
        xbmc.executebuiltin('Container.Refresh')
        return
    try:
        from resources.lib import patcher
        if os.path.exists(patcher._SKIN_RELOAD_MARKER):
            os.remove(patcher._SKIN_RELOAD_MARKER)
    except Exception:
        pass
    xbmc.sleep(300)
    from resources.lib.settings_engine import safe_reload_skin   # 4.8.72: never under the page
    safe_reload_skin()


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    current = get_style()
    keys = [k for k, _l, _d in STYLES]
    items = []
    for k, l, d in STYLES:
        li = xbmcgui.ListItem(T(l), T(d))
        img = os.path.join(_SAMPLES, '%s.png' % k)
        li.setArt({'icon': img, 'thumb': img})
        items.append(li)
    pick = xbmcgui.Dialog().select(T(32230), items, preselect=keys.index(current), useDetails=True)
    if pick < 0:
        return
    style = keys[pick]
    # every style needs the add-on now (Classic too: its Lucent Player copy)
    if not res_ready():
        xbmcgui.Dialog().notification(TITLE, T(32130), xbmcgui.NOTIFICATION_INFO, 6000)  # installing...
    if not ensure():
        xbmcgui.Dialog().ok(TITLE, T(32238))
        return
    # the OSD extras row and footer codec row are gated on the classic add-on
    try:
        from resources.lib import af3_classicflags_toggle as cf
        if not (cf.toggle_on() and cf.res_ready()):
            cf._save_toggle(True)
            cf.ensure()
    except Exception as e:
        _log('classic flags switch-on failed: %s' % e, xbmc.LOGWARNING)
    set_style(style)
    before = xbmc.getInfoLabel('Skin.String(abk.flagstyle)')
    ok, msg, wrote = reconcile()
    changed = wrote or (xbmc.getSkinDir() == SKIN_ID and before != lp_style(style))
    _log('%s -> %s' % (style, msg))
    if not ok or 'pre-50.11.68' in msg:
        xbmcgui.Dialog().ok(TITLE, T(32239))
        xbmc.executebuiltin('Container.Refresh')
        return
    xbmcgui.Dialog().notification(TITLE, T(32237) % mode_label(style), xbmcgui.NOTIFICATION_INFO, 3000)
    if changed:
        _reload_af3()
    else:
        xbmc.executebuiltin('Container.Refresh')


def start_boot_ensure(monitor, delay=110):
    """Once per boot: the add-on is a must (4.8.69) - put it back in the
    background when it is missing or disabled, whatever the style."""
    if res_ready():
        return
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        return

    def _run():
        if monitor.waitForAbort(delay):
            return
        try:
            from resources.lib import patcher
            lock = patcher._FIRST_RUN_LOCK_FILE
        except Exception:
            patcher, lock = None, ''
        for _ in range(60):
            if not ((lock and os.path.exists(lock)) or xbmc.getCondVisibility('Player.HasMedia')):
                break
            if monitor.waitForAbort(30):
                return
        if res_ready():
            return
        _log('boot: %s missing for style %s - installing' % (RES_ID, get_style()))
        if ensure() and patcher and xbmc.getSkinDir() == SKIN_ID:
            patcher._mark_skin_reload()
            patcher.reload_skin_if_pending()

    t = threading.Thread(target=_run, name='abk-flagstyle-ensure')
    t.daemon = True
    t.start()
