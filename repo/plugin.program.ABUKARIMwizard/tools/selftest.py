# -*- coding: utf-8 -*-
"""Pre-package self-test for plugin.program.ABUKARIMwizard.

Run from the addon root BEFORE zipping:   python3 tools/selftest.py
Exit code 0 = OK to ship, 1 = at least one FAIL.

Checks:
  * xbmc.service extension present (commented out in 3.9.41 -> no update popup)
  * every .py compiles, with SyntaxWarning (bad escapes) treated as an error
  * every .xml parses (a bare '&' is only a warning - Kodi tolerates it)
  * en_gb / ar_sa strings.po have the same ids, no empty Arabic msgstr
  * every local_string(id) used in code exists in strings.po
  * changelog.txt has the addon.xml version, <news> <= 1500 chars
"""
import os
import re
import sys
import warnings
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
NEWS_LIMIT = 1500
SKIP_DIRS = {'__pycache__', '.git'}

fails, warns = [], []


def walk(ext):
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f.endswith(ext):
                yield os.path.join(d, f)


def rel(p):
    return os.path.relpath(p, ROOT)


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


# ── addon.xml / changelog ────────────────────────────────────────────────────
version = '?'
try:
    root = ET.parse(os.path.join(ROOT, 'addon.xml')).getroot()   # drops comments
    version = root.get('version')
    points = [e.get('point') for e in root.findall('extension')]
    if 'xbmc.service' not in points:
        fails.append('addon.xml: xbmc.service extension missing or commented out '
                     '(no startup update check / notify)')
    if 'xbmc.python.pluginsource' not in points:
        fails.append('addon.xml: xbmc.python.pluginsource extension missing')
    news = root.find('extension/news')
    if news is not None and news.text and len(news.text) > NEWS_LIMIT:
        fails.append('addon.xml: <news> is %d chars (limit %d)'
                     % (len(news.text), NEWS_LIMIT))
    if not re.search(r'^v%s\b' % re.escape(version),
                     read(os.path.join(ROOT, 'changelog.txt')), re.M):
        fails.append('changelog.txt has no "v%s" entry' % version)
except Exception as e:
    fails.append('addon.xml / changelog.txt: %s' % e)

# ── Python: compile with SyntaxWarning as error ──────────────────────────────
py_files = list(walk('.py'))
for p in py_files:
    with warnings.catch_warnings():
        warnings.simplefilter('error', SyntaxWarning)
        try:
            compile(read(p), p, 'exec')
        except (SyntaxError, SyntaxWarning) as e:
            fails.append('python: %s: %s' % (rel(p), e))

# ── XML ──────────────────────────────────────────────────────────────────────
for p in walk('.xml'):
    try:
        ET.parse(p)
    except Exception as e:
        try:
            ET.fromstring(re.sub(r'&(?!#?\w+;)', '&amp;', read(p)))
            warns.append('xml: %s: bare "&" (Kodi tolerates it)' % rel(p))
        except Exception:
            fails.append('xml: %s: %s' % (rel(p), e))

# ── strings.po ───────────────────────────────────────────────────────────────
po_ids = {}
for lang in ('en_gb', 'ar_sa'):
    p = os.path.join(ROOT, 'resources', 'language',
                     'resource.language.%s' % lang, 'strings.po')
    try:
        txt = read(p)
        ids = re.findall(r'msgctxt "#(\d+)"', txt)
        if len(ids) != len(set(ids)):
            fails.append('%s strings.po has duplicate ids' % lang)
        po_ids[lang] = set(int(i) for i in ids)
        if lang == 'ar_sa':
            empty = re.findall(r'msgctxt "#(\d+)"\nmsgid "[^"\n]+"\nmsgstr ""\n', txt)
            if empty:
                fails.append('ar_sa strings.po: %d empty msgstr (%s...)'
                             % (len(empty), ', '.join(empty[:5])))
    except Exception as e:
        fails.append('%s strings.po: %s' % (lang, e))
if len(po_ids) == 2 and po_ids['en_gb'] != po_ids['ar_sa']:
    fails.append('strings.po en_gb / ar_sa ids differ: %s'
                 % sorted(po_ids['en_gb'] ^ po_ids['ar_sa'])[:10])
used = set()
for p in py_files:
    used |= set(int(i) for i in re.findall(
        r'(?:local_string|getLocalizedString)\((3\d{4})\)', read(p)))
missing = sorted(used - po_ids.get('en_gb', used))
if missing:
    fails.append('string id used in code but not in strings.po: %s' % missing)

# ── report ───────────────────────────────────────────────────────────────────
print('ABUKARIMwizard %s: %d .py checked, %d string ids used'
      % (version, len(py_files), len(used)))
for w in warns:
    print('WARN  ' + w)
for f in fails:
    print('FAIL  ' + f)
print('RESULT: %s' % ('FAIL (%d)' % len(fails) if fails else 'OK'))
sys.exit(1 if fails else 0)
