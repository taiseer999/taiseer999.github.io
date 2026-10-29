# -*- coding: utf-8 -*-
"""Pre-package self-test for plugin.program.abukarimtools.

Run from the addon root BEFORE zipping:   python3 tools/selftest.py
Exit code 0 = OK to ship, 1 = at least one FAIL.

Catches the regressions that have shipped before:
  * xbmc.service extension commented out (v1.9.1, v2.3, 3.1.0.27, 3.1.7, 3.3.3)
  * a .py / .xml that does not parse
  * en_gb / ar_sa strings.po out of step, or a T(id) with no string
  * a patch sentinel that is not a substring of what the patch writes
    (the RedLight busy-player bug: it re-runs and fails on every sweep)
  * a patch pointing at a toggle id that is not in TOGGLE_GROUPS
  * addon.xml version missing from changelog.txt, oversized <news>
"""
import ast
import os
import re
import sys
import types
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
NEWS_LIMIT = 1500
SKIP_DIRS = {'vendor', '__pycache__', '.git'}

fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def walk(ext):
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f.endswith(ext):
                yield os.path.join(d, f)


def rel(p):
    return os.path.relpath(p, ROOT)


# ── addon.xml ────────────────────────────────────────────────────────────────
addon_xml = os.path.join(ROOT, 'addon.xml')
try:
    tree = ET.parse(addon_xml)            # comments are dropped by the parser
    root = tree.getroot()
    version = root.get('version')
    points = [e.get('point') for e in root.findall('extension')]
    if 'xbmc.service' not in points:
        fail('addon.xml: xbmc.service extension is missing or commented out '
             '(no boot sweep / watchdog / repo linking)')
    if 'xbmc.python.pluginsource' not in points:
        fail('addon.xml: xbmc.python.pluginsource extension missing')
    news = root.find('extension/news')
    if news is not None and news.text and len(news.text) > NEWS_LIMIT:
        fail('addon.xml: <news> is %d chars (limit %d) - move history to '
             'changelog.txt' % (len(news.text), NEWS_LIMIT))
    with open(os.path.join(ROOT, 'changelog.txt'), encoding='utf-8') as f:
        cl = f.read()
    if not re.search(r'^v%s\b' % re.escape(version), cl, re.M):
        fail('changelog.txt has no "v%s" entry' % version)
except Exception as e:
    fail('addon.xml / changelog.txt: %s' % e)
    version = '?'

# ── Python syntax ────────────────────────────────────────────────────────────
py_files = list(walk('.py'))
for p in py_files:
    try:
        with open(p, encoding='utf-8') as f:
            ast.parse(f.read(), p)
    except Exception as e:
        fail('python: %s: %s' % (rel(p), e))

# ── XML well-formedness ──────────────────────────────────────────────────────
for p in walk('.xml'):
    try:
        ET.parse(p)
    except Exception as e:
        # Kodi's TinyXML accepts a bare '&' (upstream AF3 files have them);
        # only warn when that is the sole problem.
        try:
            with open(p, encoding='utf-8') as f:
                ET.fromstring(re.sub(r'&(?!#?\w+;)', '&amp;', f.read()))
            warn('xml: %s: bare "&" (Kodi tolerates it)' % rel(p))
        except Exception:
            fail('xml: %s: %s' % (rel(p), e))

# ── strings.po parity + T(id) coverage ───────────────────────────────────────
po_ids = {}
for lang in ('en_gb', 'ar_sa'):
    p = os.path.join(ROOT, 'resources', 'language',
                     'resource.language.%s' % lang, 'strings.po')
    try:
        with open(p, encoding='utf-8') as f:
            txt = f.read()
        ids = re.findall(r'msgctxt "#(\d+)"', txt)
        if len(ids) != len(set(ids)):
            fail('%s strings.po has duplicate msgctxt ids' % lang)
        po_ids[lang] = set(int(i) for i in ids)
        if lang == 'ar_sa':
            empty = re.findall(r'msgctxt "#(\d+)"\nmsgid "[^"\n]+"\nmsgstr ""\n', txt)
            if empty:
                fail('ar_sa strings.po: %d empty msgstr (%s...)'
                     % (len(empty), ', '.join(empty[:5])))
    except Exception as e:
        fail('%s strings.po: %s' % (lang, e))
if len(po_ids) == 2 and po_ids['en_gb'] != po_ids['ar_sa']:
    fail('strings.po en_gb / ar_sa ids differ: %s'
         % sorted(po_ids['en_gb'] ^ po_ids['ar_sa'])[:10])
used = set()
for p in py_files:
    with open(p, encoding='utf-8') as f:
        used |= set(int(i) for i in re.findall(r'\bT\((3\d{4})\)', f.read()))
missing = sorted(used - po_ids.get('en_gb', used))
if missing:
    fail('T(id) used in code but not in strings.po: %s' % missing)

# ── patcher: sentinels + toggles (mocked Kodi) ───────────────────────────────
def _mock_kodi():
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGDEBUG, xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 0, 1, 2, 3
    xbmc.log = lambda *a, **k: None
    xbmc.executebuiltin = lambda *a, **k: None
    xbmc.getCondVisibility = lambda *a, **k: False
    xbmc.getInfoLabel = lambda *a, **k: ''
    xbmc.sleep = lambda *a, **k: None
    xbmc.Monitor = type('Monitor', (), {'abortRequested': lambda s: False,
                                        'waitForAbort': lambda s, t=0: False})
    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: '/tmp/abk_selftest/' + p.split('://', 1)[-1]
    xbmcvfs.exists = lambda p: os.path.exists(p)
    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.Dialog = type('Dialog', (), {})
    xbmcgui.Window = lambda *a, **k: types.SimpleNamespace(
        getProperty=lambda *a: '', setProperty=lambda *a: None,
        clearProperty=lambda *a: None)
    xbmcaddon = types.ModuleType('xbmcaddon')

    class _Addon(object):
        def __init__(self, *a, **k):
            pass

        def getAddonInfo(self, k):
            return {'id': 'plugin.program.abukarimtools', 'path': ROOT,
                    'version': version, 'profile': '/tmp/abk_selftest/'}.get(k, '')

        def getLocalizedString(self, i):
            return 'S%d' % i

        def getSetting(self, *a):
            return ''

    xbmcaddon.Addon = _Addon
    for m in (xbmc, xbmcvfs, xbmcgui, xbmcaddon):
        sys.modules[m.__name__] = m


try:
    _mock_kodi()
    sys.path.insert(0, ROOT)
    from resources.lib import patcher
    known = {t for t, _l in patcher.TOGGLE_GROUPS}
    if len(known) != len(patcher.TOGGLE_GROUPS):
        fail('patcher: duplicate toggle id in TOGGLE_GROUPS')
    always_on = 0
    for e in patcher.PATCHES:
        name = '%s/%s' % (e['addon_id'], e.get('rel_path'))
        tid = patcher._toggle_of(e)
        if tid is None:
            always_on += 1
        elif tid not in known and not e.get('feature'):
            fail('patcher: %s uses toggle "%s" not in TOGGLE_GROUPS' % (name, tid))
        s = e.get('already_patched_check')
        written = e.get('new') or ''
        if not written and isinstance(e.get('fallback_repl'), str):
            written = e['fallback_repl']
        if s and written and s not in written and '\\g<' not in s:
            fail('patcher: sentinel not in output for %s' % name)
        pair = e.get('revert_when_off')
        if pair and (len(pair) != 2 or pair[0] not in written):
            fail('patcher: revert_when_off[0] is not what %s writes' % name)
    print('patcher: %d entries, %d toggles, %d always-on'
          % (len(patcher.PATCHES), len(known), always_on))
except Exception as e:
    fail('patcher import under mocked Kodi failed: %r' % e)

# ── report ───────────────────────────────────────────────────────────────────
print('abukarimtools %s: %d .py checked' % (version, len(py_files)))
for w in warns:
    print('WARN  ' + w)
for f_ in fails:
    print('FAIL  ' + f_)
print('RESULT: %s' % ('FAIL (%d)' % len(fails) if fails else 'OK'))
sys.exit(1 if fails else 0)
