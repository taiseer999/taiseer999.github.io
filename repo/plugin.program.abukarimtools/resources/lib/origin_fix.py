# -*- coding: utf-8 -*-
"""
Origin Fix – repairs the 'origin' column in Kodi's Addons database.

Add-ons installed by staged extraction (skin portal / wizard builds) or from a
zip file are registered with an EMPTY origin. Kodi 19+ only auto-updates an
add-on from the repository recorded as its origin, so an empty origin means
the add-on never receives updates and never shows as repo-installed.

This tool looks each such add-on up in the cached repository listings inside
the same database (repo / addonlinkrepo / addons tables) and, when a repo is
found that carries it, writes that repo's id into installed.origin.

Safety rules:
  * only add-ons physically present under special://home/addons are touched
    (system/binary add-ons that live in the read-only OS image are skipped,
    so CoreELEC binaries can never be pointed at repository.xbmc.org)
  * only rows whose origin is currently empty are modified
  * nothing is ever deleted; the change is a single UPDATE per add-on

Note: Kodi keeps origins in memory, so a restart is needed before the new
origins take effect for update checks. The interactive runner offers one.
"""

import os
import re
import sqlite3

import xbmc
import xbmcgui
import xbmcvfs

TITLE = 'ABUKARIM – Origin Fix'

ADDONS_PATH   = xbmcvfs.translatePath('special://home/addons/')
DATABASE_PATH = xbmcvfs.translatePath('special://database/')

# When several repos carry the same add-on id, prefer these (compared
# case-insensitively, first match wins), otherwise fall back to the
# alphabetically-first candidate so the result is deterministic.
PREFERRED_REPOS = [
    'repository.taiseerkodi22',   # Piers / Kodi 22 repo
    'repository.taiseerce',       # CoreELEC NG repo
    'repository.taiseer',         # Kodi 21 repo
]

# Never rewrite the origin of these ids even if a repo carries them.
SKIP_IDS = set()


def _log(msg):
    xbmc.log('[AbukarimTools OriginFix] %s' % msg, xbmc.LOGINFO)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _find_addons_db():
    """Return the path of the newest AddonsNN.db, or None."""
    best_ver, best_path = -1, None
    try:
        for name in os.listdir(DATABASE_PATH):
            m = re.fullmatch(r'Addons(\d+)\.db', name)
            if m and int(m.group(1)) > best_ver:
                best_ver = int(m.group(1))
                best_path = os.path.join(DATABASE_PATH, name)
    except OSError as e:
        _log('cannot list Database dir: %s' % e)
    return best_path


def _connect(db_path):
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.execute('PRAGMA busy_timeout=5000')
    return conn


def _tables(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def _repo_candidates(cur, addon_id):
    """All repository ids whose cached listing carries addon_id."""
    cur.execute(
        'SELECT DISTINCT r.addonID '
        'FROM repo r '
        'JOIN addonlinkrepo l ON l.idRepo = r.id '
        'JOIN addons a       ON a.id     = l.idAddon '
        'WHERE a.addonID = ?', (addon_id,))
    return sorted(row[0] for row in cur.fetchall() if row[0])


def _pick_repo(candidates):
    if not candidates:
        return None
    lower = {c.lower(): c for c in candidates}
    for pref in PREFERRED_REPOS:
        if pref in lower:
            return lower[pref]
    return candidates[0]


def _locally_installed(addon_id):
    """True when the add-on physically lives in the writable addons dir."""
    return os.path.isdir(os.path.join(ADDONS_PATH, addon_id))


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def fix_addons(addon_ids=None):
    """Repair empty origins.

    addon_ids: iterable of ids to fix, or None to scan every installed row
    with an empty origin.

    Returns a dict:
        {'fixed': {addonID: repoID, ...},
         'unmatched': [addonID, ...],   # empty origin but not in any repo
         'error': str or None}
    """
    result = {'fixed': {}, 'unmatched': [], 'error': None}

    db_path = _find_addons_db()
    if not db_path:
        result['error'] = 'No Addons database found.'
        _log(result['error'])
        return result
    _log('using database: %s' % db_path)

    conn = None
    try:
        conn = _connect(db_path)
        cur = conn.cursor()

        need = {'installed', 'repo', 'addonlinkrepo', 'addons'}
        missing = need - _tables(cur)
        if missing:
            result['error'] = ('Database schema unexpected '
                               '(missing: %s)' % ', '.join(sorted(missing)))
            _log(result['error'])
            return result

        if addon_ids is None:
            cur.execute("SELECT addonID FROM installed "
                        "WHERE origin IS NULL OR origin = ''")
            targets = [row[0] for row in cur.fetchall()]
        else:
            targets = list(addon_ids)

        updates = []
        for addon_id in targets:
            if not addon_id or addon_id in SKIP_IDS:
                continue
            if not _locally_installed(addon_id):
                continue  # bundled/system add-on – never touch

            cur.execute('SELECT origin FROM installed WHERE addonID = ?',
                        (addon_id,))
            row = cur.fetchone()
            if row is None or (row[0] or '') != '':
                continue  # not registered yet, or already has an origin

            repo_id = _pick_repo(_repo_candidates(cur, addon_id))
            if repo_id:
                updates.append((repo_id, addon_id))
            else:
                result['unmatched'].append(addon_id)

        for repo_id, addon_id in updates:
            cur.execute('UPDATE installed SET origin = ? '
                        "WHERE addonID = ? AND (origin IS NULL OR origin = '')",
                        (repo_id, addon_id))
            if cur.rowcount:
                result['fixed'][addon_id] = repo_id
                _log('origin set: %s -> %s' % (addon_id, repo_id))
        conn.commit()

    except sqlite3.DatabaseError as e:
        result['error'] = 'Database error: %s' % e
        _log(result['error'])
        try:
            if conn:
                conn.rollback()
        except sqlite3.Error:
            pass
    finally:
        try:
            if conn:
                conn.close()
        except sqlite3.Error:
            pass

    return result


def fix_addons_silent(addon_ids):
    """Targeted, exception-proof variant for use right after an install.
    A best-effort helper: failures are logged, never raised."""
    try:
        res = fix_addons(addon_ids)
        if res['error']:
            _log('silent fix skipped: %s' % res['error'])
        return res
    except Exception as e:  # noqa: BLE001 – must never break an install
        _log('silent fix crashed: %s' % e)
        return {'fixed': {}, 'unmatched': list(addon_ids), 'error': str(e)}


# ---------------------------------------------------------------------------
# Interactive runner (menu entry)
# ---------------------------------------------------------------------------

def _is_coreelec():
    if os.path.isdir('/etc/coreelec'):
        return True
    try:
        with open('/etc/os-release') as f:
            return any('coreelec' in line.lower() for line in f)
    except OSError:
        return False


def _restart_kodi():
    if _is_coreelec():
        _log('Restarting Kodi via systemctl (CoreELEC).')
        os.system('systemctl restart kodi &')
    else:
        _log('Restarting Kodi via RestartApp builtin.')
        xbmc.executebuiltin('RestartApp')


def run():
    dialog = xbmcgui.Dialog()
    if not dialog.yesno(
            TITLE,
            'Scan for add-ons installed without a repository origin\n'
            '(zip / portal installs) and link them back to their repo\n'
            'so they show as installed and receive updates again?',
            yeslabel='Scan && fix', nolabel='Cancel'):
        return

    res = fix_addons(None)

    if res['error']:
        dialog.ok(TITLE,
                  'Could not complete the fix:\n%s\n\n'
                  'If the database is corrupt, rebuild it first '
                  '(stop Kodi, delete Addons*.db, restart).' % res['error'])
        return

    fixed, unmatched = res['fixed'], res['unmatched']

    if not fixed and not unmatched:
        dialog.ok(TITLE, 'Nothing to fix – every locally installed add-on '
                         'already has a repository origin.')
        return

    lines = []
    if fixed:
        lines.append('[B]Linked to a repository (%d):[/B]' % len(fixed))
        lines += ['%s  →  %s' % (a, r) for a, r in sorted(fixed.items())]
    if unmatched:
        lines.append('')
        lines.append('[B]No repository carries these (%d) – left as-is:[/B]'
                     % len(unmatched))
        lines += sorted(unmatched)
    dialog.textviewer(TITLE, '\n'.join(lines))

    if fixed and dialog.yesno(
            TITLE,
            'Kodi must restart before the new origins are used for\n'
            'update checks. Restart now?',
            yeslabel='Restart', nolabel='Later'):
        xbmc.sleep(500)
        _restart_kodi()
