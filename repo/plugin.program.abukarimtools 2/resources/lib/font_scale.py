# -*- coding: utf-8 -*-
"""
font_scale.py - ABUKARIM TOOLS (3.4.6)

Toggles entry "Font Size": four modes for EVERY font of the active skin.

    original   - the skin's own sizes
    smaller    - every size -5%
    smaller10  - every size -10%
    smaller15  - every size -15%
    smaller20  - every size -20%  (3.4.9)

(3.4.8: the +5% "larger" mode was dropped; a box still saved on it goes
back to original on the next sweep. A change from the menu now force-restarts
Kodi instead of ReloadSkin.)

What is scaled (text edit, no XML rewrite - same style as the PPI fonts):
    * every literal <size>N</size> inside a <font> block
    * every <param name="size_*">N</param> (AF3 passes the sizes of all its
      fontsets into Font_Default this way; $PARAM[...] sizes follow them)
in Font.xml and every other XML of the skin's <res> folders whose file name
contains "font" (AF3: Font.xml + Includes_Font.xml).

Kodi reads <size> with XMLUtils::GetInt, so sizes stay integers. Each scaled
value keeps its ORIGINAL right beside it as a comment:

    <size>22</size><!--abk-fs:21-->

so the edit is stateless and exactly reversible: a mode change always scales
from the stored original, "original" puts it back and drops the comment, and
a font block added later (skin update, another patch) has no comment yet and
is scaled from its own value on the next pass. A skin update brings the stock
files back, which simply look "original" and get scaled again by reconcile()
(called from patcher.apply_set on every sweep / skin-update watchdog run).

The mode lives in addon_data/plugin.program.abukarimtools/font_scale.json and
applies to whichever skin is active. Font.xml is read at skin load, so a change
needs ReloadSkin().

3.4.7 - NEVER scale the font entries TinyPPI owns. TinyPPI's fonts.py checks
every <fontset> for its required (name, filename, SIZE) triples - font23_narrow
/ font32 on special://xbmc/media/Fonts/arial.ttf at 21 / 32, plus abk_ppi_ar21
/ abk_ppi_ar32 on some builds - and on every skin load inserts fresh copies of
any it cannot match exactly. Scaling them made TinyPPI insert 21/32 copies,
which the next sweep scaled, which TinyPPI re-inserted: a ReloadSkin loop every
~1.3 s that also piled duplicate blocks into Font.xml (kodi.log 2026-10-15).
Those blocks are recognised by name + an absolute special:// file path (the
skin's own fonts use bare file names), restored to their original size if an
older pass scaled them, and exact duplicates of them inside a fontset are
dropped (first one kept - it is the one Kodi uses). A write guard also stops
the reconcile for the session if anything keeps undoing it.
"""
import json
import os
import re

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T
from resources.lib import paths as _paths

TITLE = 'ABUKARIM TOOLS'
STATE_FILE = os.path.join(_paths.PROFILE, 'font_scale.json')

# (mode, factor, label id) - menu order
MODES = (
    ('original',  1.00, 30741),
    ('smaller',   0.95, 30743),
    ('smaller10', 0.90, 30742),
    ('smaller15', 0.85, 30746),
    ('smaller20', 0.80, 30747),
)
_FACTOR = dict((m, f) for m, f, _l in MODES)

_NUM = r'([0-9]+(?:\.[0-9]+)?)'
_TAG = r'(?:<!--abk-fs:([0-9]+(?:\.[0-9]+)?)-->)?'
_FONT_BLOCK_RE = re.compile(r'<font>.*?</font>', re.S)
_NAME_RE = re.compile(r'<name>\s*(.*?)\s*</name>', re.S)
_FILE_RE = re.compile(r'<filename>\s*(.*?)\s*</filename>', re.S)
_FONTSET_RE = re.compile(r'(<fontset\b[^>]*>)(.*?)(</fontset>)', re.S)
# a whole <font> element with its indent and line break (TinyPPI's own rule)
_FONT_LINE_RE = re.compile(r'[ \t]*<font>.*?</font>(?:<!--abk-fs:[0-9.]+-->)?[ \t]*\r?\n?', re.S)
# font names other add-ons look up by exact size (TinyPPI fonts.py)
_PROTECTED_NAMES = ('font23_narrow', 'font32', 'abk_ppi_ar21', 'abk_ppi_ar32')

# write guard: more than _GUARD_MAX writes of the font files inside
# _GUARD_WINDOW seconds means something keeps undoing them - stop fighting
GUARD_FILE = os.path.join(_paths.PROFILE, 'font_scale_guard.json')
_GUARD_WINDOW = 300
_GUARD_MAX = 4
_SIZE_RE = re.compile(r'<size>\s*' + _NUM + r'\s*</size>' + _TAG)
_PARAM_RE = re.compile(r'(<param\s+name\s*=\s*"size_[^"]*"\s*>)\s*' + _NUM
                       + r'\s*(</param>)' + _TAG)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools FontScale] %s' % msg, level)


# ---------------------------------------------------------------- state
def get_mode():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            mode = json.load(f).get('mode', 'original')
        return mode if mode in _FACTOR else 'original'
    except Exception:
        return 'original'


def set_mode(mode):
    if mode not in _FACTOR:
        mode = 'original'
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'mode': mode}, f)
    except Exception as e:
        _log('cannot save mode: %s' % e, xbmc.LOGWARNING)


def mode_label(mode=None):
    mode = mode or get_mode()
    for m, _f, lid in MODES:
        if m == mode:
            return T(lid)
    return T(30741)


# ---------------------------------------------------------------- scaling
def _scaled(orig, factor):
    v = float(orig) * factor
    if '.' in orig:
        return ('%.2f' % v).rstrip('0').rstrip('.')
    return str(max(1, int(v + 0.5)))


def _protected(block):
    """A font entry another add-on owns and matches by exact size."""
    n = _NAME_RE.search(block)
    f = _FILE_RE.search(block)
    return bool(n and f and n.group(1) in _PROTECTED_NAMES
                and '://' in f.group(1))


def _dedupe_protected(text):
    """Drop exact repeats of a protected font block inside each fontset."""
    def _norm(block):
        block = re.sub(r'<!--abk-fs:[0-9.]+-->', '', block)
        return re.sub(r'\s+', '', block)

    def _fontset(m):
        seen = set()

        def _one(b):
            blk = b.group(0)
            if not _protected(blk):
                return blk
            key = _norm(blk)
            if key in seen:
                return ''
            seen.add(key)
            return blk
        return m.group(1) + _FONT_LINE_RE.sub(_one, m.group(2)) + m.group(3)

    return _FONTSET_RE.sub(_fontset, text)


def scale_text(text, factor):
    """Return text with every font size set to original*factor (1.0 = undo).
    Protected (TinyPPI) entries always go back to / stay at their original."""
    def _size(m):
        orig = m.group(2) or m.group(1)
        if factor == 1.0:
            return '<size>%s</size>' % orig
        return '<size>%s</size><!--abk-fs:%s-->' % (_scaled(orig, factor), orig)

    def _restore(m):
        return '<size>%s</size>' % (m.group(2) or m.group(1))

    def _block(m):
        if _protected(m.group(0)):
            return _SIZE_RE.sub(_restore, m.group(0))
        return _SIZE_RE.sub(_size, m.group(0))

    def _param(m):
        orig = m.group(4) or m.group(2)
        if factor == 1.0:
            return '%s%s%s' % (m.group(1), orig, m.group(3))
        return '%s%s%s<!--abk-fs:%s-->' % (m.group(1), _scaled(orig, factor),
                                           m.group(3), orig)

    text = _FONT_BLOCK_RE.sub(_block, text)
    text = _PARAM_RE.sub(_param, text)
    return _dedupe_protected(text)


def _skin_font_files(skin_dir):
    """Font.xml + every '*font*.xml' in the skin's <res> folders."""
    found = []
    try:
        with open(os.path.join(skin_dir, 'addon.xml'), 'rb') as f:
            ax = re.sub(r'<!--.*?-->', '', f.read().decode('utf-8', 'replace'), flags=re.S)
        folders = []
        for tag in re.findall(r'<res\b[^>]*>', ax, re.I):
            m = re.search(r"""\bfolder\s*=\s*(["'])(.*?)\1""", tag)
            if m and m.group(2).strip():
                folders.append(m.group(2).strip())
        for sub in folders or ['1080i', '720p', '16x9', 'xml']:
            folder = os.path.normpath(os.path.join(skin_dir, sub))
            if (os.path.commonpath((skin_dir, folder)) != skin_dir
                    or not os.path.isdir(folder)):
                continue
            for name in sorted(os.listdir(folder)):
                low = name.lower()
                path = os.path.join(folder, name)
                if (low.endswith('.xml') and 'font' in low
                        and os.path.isfile(path) and path not in found):
                    found.append(path)
    except Exception as e:
        _log('cannot list font files: %s' % e, xbmc.LOGWARNING)
    return found


def apply(skin_dir, mode):
    """Bring every font file of skin_dir to `mode`.
    Returns (files_written, errors)."""
    factor = _FACTOR.get(mode, 1.0)
    written, errors = 0, []
    for path in _skin_font_files(skin_dir):
        try:
            with open(path, 'rb') as f:
                raw = f.read()
            text = raw.decode('utf-8')
        except Exception as e:
            errors.append('%s: %s' % (os.path.basename(path), e))
            continue
        new = scale_text(text, factor)
        if new == text:
            continue
        try:
            tmp = path + '.abk_tmp'
            with open(tmp, 'wb') as f:
                f.write(new.encode('utf-8'))
            os.replace(tmp, path)
            written += 1
            _log('%s -> %s' % (path, mode))
        except Exception as e:
            errors.append('%s: %s' % (os.path.basename(path), e))
            try:
                os.remove(path + '.abk_tmp')
            except OSError:
                pass
    return written, errors


def _guard_load():
    try:
        with open(GUARD_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _guard_save(data):
    try:
        os.makedirs(os.path.dirname(GUARD_FILE), exist_ok=True)
        with open(GUARD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass


def _guard_blocked(now):
    g = _guard_load()
    return bool(g.get('blocked')) and now - g.get('blocked', 0) < 6 * 3600


def _guard_note_write(now):
    """Record a background write; True if this one trips the guard."""
    g = _guard_load()
    times = [t for t in g.get('writes', []) if now - t < _GUARD_WINDOW] + [now]
    g['writes'] = times
    tripped = len(times) > _GUARD_MAX
    if tripped:
        g['blocked'] = now
    _guard_save(g)
    return tripped


def guard_reset():
    _guard_save({})


def _active_skin_dir():
    try:
        d = os.path.normpath(xbmcvfs.translatePath('special://skin/'))
        return d if os.path.isdir(d) else None
    except Exception:
        return None


def reconcile():
    """Keep the active skin at the saved mode. Called from patcher.apply_set.
    Returns (ok, msg, wrote). Never raises."""
    try:
        skin_dir = _active_skin_dir()
        if not skin_dir:
            return True, '[font size] no active skin folder - skipping.', False
        import time
        now = time.time()
        if _guard_blocked(now):
            return True, ('[font size] paused - the font files kept being changed '
                          'back by something else; choose a mode again to retry.'), False
        mode = get_mode()
        written, errors = apply(skin_dir, mode)
        if written and _guard_note_write(now):
            _log('font files rewritten %d+ times in %ds - another add-on keeps '
                 'changing them; font size reconcile paused.'
                 % (_GUARD_MAX + 1, _GUARD_WINDOW), xbmc.LOGWARNING)
        skin = os.path.basename(skin_dir)
        if errors:
            return False, '[%s] font size (%s) failed: %s' % (
                skin, mode, '; '.join(errors)), written > 0
        if written:
            return True, '[%s] Patched OK: font size set to %s (%d file(s)).' % (
                skin, mode, written), True
        return True, '[%s] Font size already %s.' % (skin, mode), False
    except Exception as e:
        return False, '[font size] reconcile failed: %s' % e, False


# ---------------------------------------------------------------- menu
def run():
    cur = get_mode()
    lis, pre = [], 0
    for i, (mode, _f, lid) in enumerate(MODES):
        label = T(lid)
        if mode == cur:
            label = '[B]%s[/B]  ✓' % label
            pre = i
        lis.append(xbmcgui.ListItem(label, offscreen=True))
    choice = xbmcgui.Dialog().select(T(30740), lis, preselect=pre)
    if choice < 0:
        return
    mode = MODES[choice][0]
    set_mode(mode)
    guard_reset()
    skin_dir = _active_skin_dir()
    written, errors = apply(skin_dir, mode) if skin_dir else (0, ['no skin'])
    if errors:
        _log('apply failed: %s' % '; '.join(errors), xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(TITLE, T(30745))
        return
    if not written:
        # already at this mode - nothing changed, nothing to restart
        xbmc.executebuiltin('Container.Refresh')
        return
    # 3.4.8: always a full Kodi restart on change (fonts load cleanly at
    # boot); the add-on's one restart path = Wizard Force Close / os._exit
    _log('mode -> %s: forcing Kodi restart' % mode)
    xbmcgui.Dialog().notification(TITLE, T(30744) % mode_label(mode),
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    from resources.lib import origin_fix
    origin_fix.force_restart('font size %s' % mode)
