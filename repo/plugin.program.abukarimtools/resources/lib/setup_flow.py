# -*- coding: utf-8 -*-
"""
setup_flow.py - Installation Wizard core (4.7.0).

Three parts, all driven from service._run_steps_inner():

1. PREFLIGHT - before anything on the box changes: clock, internet to the
   ABUKARIM repo, free space, Kodi version. A box whose clock is still at
   its factory date fails every HTTPS download with a certificate error that
   looks like a random install failure, so the clock gets up to 90 s to sync
   first. All good = nothing is shown.

2. QUESTIONS - every question of the wizard is asked up front, with nothing
   applied and no skin reload in between: restore (the newest backup found on
   the box is offered first), preset + Add-on Portal ticks, Widgets Layout,
   My Lists. A summary page follows: Start setup / Change answers. The
   answers are written to setup_state.json.

3. APPLY - the steps run one after another with no further questions (the
   only exception is My Lists "Custom"/"Anime": its Trakt link and list
   pickers need TMDb Helper, which may only be installed in this phase).
   Patch toggles are NOT asked: the saved choice applies silently, as in the
   phone setup; they stay editable in Apply Patches.

   Every step's status is written to setup_state.json before and after it
   runs, so the wizard can RESUME: a crash or power cut continues at the
   step that did not finish, without asking anything again. A step found
   "running" at resume time was interrupted; after MAX_ATTEMPTS it is marked
   failed and skipped, so a step that crashes Kodi cannot loop the box.
   At the end setup_report.json is written and shown once after the reboot;
   failed steps can be retried from the AB Tools menu.

Nothing in here is allowed to stop setup: every step is fenced.
"""

import json
import os
import shutil
import ssl
import time
import traceback
import zipfile

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T
from resources.lib import paths as _paths

PROFILE = _paths.PROFILE
STATE_FILE = os.path.join(PROFILE, 'setup_state.json')
REPORT_FILE = os.path.join(PROFILE, 'setup_report.json')
SCHEMA = 1

MAX_ATTEMPTS = 2            # a step interrupted twice is marked failed
MAX_RESUMES = 3             # automatic resumes at boot per setup
RESUME_WINDOW = 24 * 3600   # an older unfinished setup is not resumed at boot

MIN_FREE_MB = 400
WARN_FREE_MB = 1024
CLOCK_MIN_YEAR = 2026
CLOCK_WAIT_S = 90

CHECK_URLS = (
    'https://raw.githubusercontent.com/taiseer999/taiseer999.github.io/main/'
    'repo/zips/addons.xml.md5',
)

# key, report label id, overlay step id, reloads the skin
STEPS = (
    ('binaries',     30945, 30775, False),
    ('tinyppi',      30946, 30775, False),
    ('bootstrap',    30947, 30775, False),
    ('hw_tuning',    30948, 30775, False),
    ('restore',      30949, 30058, True),
    ('addons',       30950, 30021, True),
    ('layout',       30951, 30630, True),
    ('lists',        30952, 30660, True),
    ('patches',      30953, 30005, True),
    ('webserver',    30954, 30776, False),
    ('lists_ensure', 30955, 30660, True),
    ('language',     30956, 30776, True),
)
STEP_KEYS = tuple(s[0] for s in STEPS)

OK, FAILED, SKIPPED, PENDING, RUNNING = 'ok', 'failed', 'skipped', 'pending', 'running'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools Setup] %s' % msg, level)


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------

def load():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            st = json.load(f)
        if isinstance(st, dict) and st.get('schema') == SCHEMA:
            return st
    except Exception:
        pass
    return None


def save(st):
    st['updated'] = int(time.time())
    try:
        os.makedirs(PROFILE, exist_ok=True)
        tmp = STATE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
        os.replace(tmp, STATE_FILE)     # atomic: a power cut never leaves half a file
    except Exception as e:
        _log('could not save state: %s' % e, xbmc.LOGWARNING)


def new_state(answers, build_id=''):
    now = int(time.time())
    return {'schema': SCHEMA, 'build': build_id, 'version': _version(),
            'phase': 'apply', 'started': now, 'updated': now, 'resumes': 0,
            'answers': answers,
            'steps': {k: {'status': PENDING, 'attempts': 0} for k in STEP_KEYS}}


def _version():
    try:
        return _paths.version()
    except Exception:
        return '?'


def unfinished(st):
    """First step that is not ok/skipped/failed, or None."""
    for k in STEP_KEYS:
        if (st.get('steps', {}).get(k) or {}).get('status') in (PENDING, RUNNING):
            return k
    return None


def failed_steps(st):
    return [k for k in STEP_KEYS
            if (st.get('steps', {}).get(k) or {}).get('status') == FAILED]


def step_label(key):
    for k, lab, _o, _r in STEPS:
        if k == key:
            return T(lab)
    return key


def should_auto_resume():
    """Boot: an apply phase that was cut short (crash / power) recently."""
    st = load()
    if not st or st.get('phase') != 'apply' or not unfinished(st):
        return False
    if time.time() - st.get('updated', 0) > RESUME_WINDOW:
        _log('unfinished setup is older than %dh - not resumed at boot'
             % (RESUME_WINDOW // 3600))
        return False
    if st.get('resumes', 0) >= MAX_RESUMES:
        _log('setup already resumed %d times - not resumed again at boot'
             % st.get('resumes', 0), xbmc.LOGWARNING)
        return False
    return True


# ---------------------------------------------------------------------------
# entry choice (menu)
# ---------------------------------------------------------------------------

RESUME, RETRY, FRESH = 'resume', 'retry', 'fresh'


def entry_choice(auto=False):
    """What to run. auto=True (boot resume) never asks. None = cancel."""
    st = load()
    if not st:
        return FRESH
    nxt = unfinished(st) if st.get('phase') == 'apply' else None
    fails = failed_steps(st) if st.get('phase') == 'done' else []
    if auto:
        return RESUME if nxt else FRESH
    if not nxt and not fails:
        return FRESH
    opts, keys = [], []
    if nxt:
        opts.append(T(30934)); keys.append(RESUME)
        heading = T(30933) % step_label(nxt)
    else:
        opts.append(T(30936) % ', '.join(step_label(k) for k in fails)); keys.append(RETRY)
        heading = T(30937)
    opts.append(T(30935)); keys.append(FRESH)
    from resources.lib import dialog_guard
    idx = dialog_guard.select(heading, opts)
    return keys[idx] if idx >= 0 else None


def prepare_retry(st):
    """Failed steps back to pending; an add-on step retries only what failed."""
    for k in failed_steps(st):
        s = st['steps'][k]
        s.update(status=PENDING, attempts=0, error='')
        if k == 'addons' and s.get('failed_ids'):
            st['answers']['addons'] = list(s['failed_ids'])
    st['phase'] = 'apply'
    st['resumes'] = 0
    save(st)
    return st


# ---------------------------------------------------------------------------
# 1. preflight
# ---------------------------------------------------------------------------

def _https(url, timeout=8):
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ABUKARIM-Tools'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(64)
        return True, ''
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, ssl.SSLCertVerificationError) or \
                'CERTIFICATE_VERIFY_FAILED' in str(reason) or 'not yet valid' in str(reason):
            return False, 'certificate'
        return False, str(reason)[:80]
    except Exception as e:
        return False, str(e)[:80]


def _free_mb():
    try:
        home = xbmcvfs.translatePath('special://home/')
        return shutil.disk_usage(home).free // (1024 * 1024)
    except Exception:
        return None


def _kodi_major():
    try:
        return int((xbmc.getInfoLabel('System.BuildVersion') or '0').split('.')[0])
    except ValueError:
        return 0


def _clock_ok():
    return time.localtime().tm_year >= CLOCK_MIN_YEAR


def _wait_clock(monitor):
    """Give NTP time after boot (CoreELEC boxes have no RTC battery)."""
    if _clock_ok():
        return True
    _log('clock reads %s - waiting up to %ds for time sync'
         % (time.strftime('%Y-%m-%d %H:%M'), CLOCK_WAIT_S))
    bg = xbmcgui.DialogProgressBG()
    bg.create(T(30911), T(30919))
    try:
        for i in range(CLOCK_WAIT_S):
            if _clock_ok():
                _log('clock synced: %s' % time.strftime('%Y-%m-%d %H:%M'))
                return True
            bg.update(int(i * 100 / CLOCK_WAIT_S))
            if monitor.waitForAbort(1):
                return False
    finally:
        bg.close()
    return _clock_ok()


def checks(monitor):
    """Returns (problems, warnings) as lists of display strings."""
    problems, warnings = [], []
    clock = _wait_clock(monitor)
    if not clock:
        problems.append(T(30912) % time.strftime('%Y-%m-%d'))
    for url in CHECK_URLS:
        ok, why = _https(url)
        if not ok:
            if why == 'certificate' and clock:
                problems.append(T(30912) % time.strftime('%Y-%m-%d'))
            elif why != 'certificate':
                problems.append(T(30913) % why)
            break
    free = _free_mb()
    if free is not None:
        if free < MIN_FREE_MB:
            problems.append(T(30914) % ('%d MB' % free, '%d MB' % MIN_FREE_MB))
        elif free < WARN_FREE_MB:
            warnings.append(T(30914) % ('%d MB' % free, '%d MB' % WARN_FREE_MB))
    major = _kodi_major()
    if major and major < 21:
        warnings.append(T(30915) % xbmc.getInfoLabel('System.BuildVersion'))
    # dedupe, keep order
    seen = set()
    problems = [p for p in problems if not (p in seen or seen.add(p))]
    _log('preflight: clock=%s free=%sMB kodi=%s problems=%d warnings=%d'
         % (time.strftime('%Y-%m-%d %H:%M'), free, major, len(problems), len(warnings)))
    return problems, warnings


def preflight(monitor):
    """True = go on, False = the user cancelled setup."""
    while not monitor.abortRequested():
        try:
            problems, warnings = checks(monitor)
        except Exception:
            _log('preflight crashed (setup continues):\n%s' % traceback.format_exc(),
                 xbmc.LOGERROR)
            return True
        if not problems and not warnings:
            return True
        if not problems:
            for w in warnings:
                _log('preflight warning: %s' % w, xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(T(30911), warnings[0],
                                          xbmcgui.NOTIFICATION_WARNING, 6000)
            return True
        text = '[CR]'.join('- ' + p for p in problems + warnings)
        from resources.lib import dialog_guard
        idx = dialog_guard.select('%s: %s' % (T(30911), text.replace('[CR]', '  ')),
                                  [T(30916), T(30917), T(30918)])
        if idx == 0:
            continue
        if idx == 1:
            _log('preflight problems ignored by the user: %s' % problems, xbmc.LOGWARNING)
            return True
        _log('setup cancelled at preflight: %s' % problems, xbmc.LOGWARNING)
        return False
    return False


# ---------------------------------------------------------------------------
# 2. questions
# ---------------------------------------------------------------------------

BACKUP_PATTERNS = ('kodi_userdata_backup_', 'abk_backup_')


def _backup_dirs():
    dirs = [xbmcvfs.translatePath('special://home/'),
            xbmcvfs.translatePath('special://home/backup/'),
            xbmcvfs.translatePath('special://profile/addon_data/'
                                  'plugin.program.abukarimtools/'),
            '/storage', '/storage/backup', '/storage/downloads',
            os.path.expanduser('~/Downloads'), os.path.expanduser('~/Desktop')]
    for root in ('/var/media', '/media', '/mnt'):
        try:
            for name in os.listdir(root):
                p = os.path.join(root, name)
                if os.path.isdir(p):
                    dirs += [p, os.path.join(p, 'backup')]
        except OSError:
            pass
    return dirs


def find_backups(limit=5):
    """Backups made by AB Tools that are on this box or a USB stick, newest first."""
    found, seen = [], set()
    for d in _backup_dirs():
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            if not n.lower().endswith('.zip') or not n.startswith(BACKUP_PATTERNS):
                continue
            p = os.path.realpath(os.path.join(d, n))
            if p in seen:
                continue
            seen.add(p)
            try:
                if zipfile.is_zipfile(p):
                    found.append((os.path.getmtime(p), os.path.getsize(p), p))
            except OSError:
                pass
    found.sort(reverse=True)
    return found[:limit]


def _human(size):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return ('%d %s' if unit in ('B', 'KB') else '%.1f %s') % (size, unit)
        size /= 1024.0


def ask_restore(prev=None):
    """Path of the backup to restore, or '' for none."""
    from resources.lib import dialog_guard
    while True:
        cands = find_backups()
        items, paths_ = [], []
        for mtime, size, p in cands:
            li = xbmcgui.ListItem(T(30920) % os.path.basename(p),
                                  '%s  ·  %s  ·  %s' % (
                                      time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime)),
                                      _human(size), os.path.dirname(p)))
            items.append(li); paths_.append(p)
        items.append(xbmcgui.ListItem(T(30921))); paths_.append('browse')
        items.append(xbmcgui.ListItem(T(30922))); paths_.append('')
        pre = 0
        if prev is not None:
            pre = paths_.index(prev) if prev in paths_ else len(paths_) - 1
        idx = dialog_guard.select(T(30923), items, useDetails=True, preselect=pre)
        choice = paths_[idx] if idx >= 0 else ''
        if choice == 'browse':
            p = xbmcgui.Dialog().browse(1, T(30225), 'files', '.zip', False, False,
                                        xbmcvfs.translatePath('special://home/'))
            if p and p.lower().endswith('.zip'):
                return p
            continue
        if not choice:
            from resources.lib import skip_guard
            if idx >= 0 or skip_guard.confirm(T(30058)):
                return ''
            continue
        return choice


def ask_addons(prev=None):
    """Ticked add-on ids. Preset question first (as before), then the portal."""
    from resources.lib import addon_portal
    preselect = set(prev or ())
    if prev is None:
        try:
            from resources.lib import presets
            from resources.lib import skip_guard
            while True:
                preset = presets.choose()
                if preset is not None or skip_guard.confirm(T(30764)):
                    break
            preselect = presets.addon_selection(preset)
        except Exception:
            _log('preset question failed (portal opens unticked):\n%s'
                 % traceback.format_exc(), xbmc.LOGWARNING)
    while True:
        selection = addon_portal._open_portal(preselect)
        if selection:
            return [a for a, _n, _r in selection]
        from resources.lib import skip_guard
        if skip_guard.confirm(T(30021)):
            return []


def ask_layout(ctx, monitor):
    from resources.lib import af3_shortcuts
    return af3_shortcuts.choose(wait_clear=lambda: ctx._wait_no_modal(monitor),
                                settle=lambda s: ctx._settle(monitor, s))


def ask_lists(ctx, monitor):
    from resources.lib import trakt_hubs
    return trakt_hubs.choose(wait_clear=lambda: ctx._wait_no_modal(monitor),
                             settle=lambda s: ctx._settle(monitor, s))


def _mode_label(kind, mode):
    try:
        if kind == 'layout':
            from resources.lib import af3_shortcuts as m
            ids = {m.LIGHT: 30631, m.MODERATE: 30633, m.FULL: 30635}
        else:
            from resources.lib import trakt_hubs as m
            ids = {m.ORIGINAL: 30661, m.CUSTOM: 30663, m.ANIME: 30709}
        return T(ids[mode]) if mode in ids else str(mode)
    except Exception:
        return str(mode)


def summary_text(answers):
    from resources.lib import addon_portal
    phone = set(answers.get('phone') or ())
    names = {c[0]: c[1] for c in addon_portal._catalog()}

    def part(key, value):
        return T(30932) if key in phone else value

    r = answers.get('restore')
    lines = [
        T(30925) % part('restore', os.path.basename(r) if r else T(30931)),
        T(30926) % part('addons', ', '.join(names.get(a, a) for a in answers.get('addons') or [])
                        or T(30931)),
        T(30927) % part('layout', _mode_label('layout', answers.get('layout'))),
        T(30928) % part('lists', _mode_label('lists', answers.get('lists'))),
        T(30942),
    ]
    return '[CR]'.join(lines)


def confirm_summary(answers):
    """True = start, False = change answers. A dialog torn down faster than a
    person can answer is shown again (it is never read as "change")."""
    for _ in range(4):
        started = time.time()
        yes = xbmcgui.Dialog().yesno(T(30924), summary_text(answers),
                                     yeslabel=T(30929), nolabel=T(30930))
        if yes:
            return True
        if time.time() - started >= 1.0:
            return False
        xbmc.sleep(1500)
    return True


def ask_all(ctx, monitor, phone):
    """Phase A. Returns the answers dict (never applies anything)."""
    answers = {'phone': sorted(phone)}
    first = True
    while not monitor.abortRequested():
        if 'restore' not in phone:
            ctx._overlay('step', 30058)
            answers['restore'] = ask_restore(None if first else answers.get('restore'))
        if 'addons' not in phone:
            ctx._overlay('step', 30021)
            answers['addons'] = ask_addons(None if first else answers.get('addons'))
        if 'layout' not in phone:
            ctx._overlay('step', 30630)
            answers['layout'] = ask_layout(ctx, monitor)
        if 'lists' not in phone and 'anime' not in phone:
            ctx._overlay('step', 30660)
            answers['lists'] = ask_lists(ctx, monitor)
        _log('answers: %s' % json.dumps(answers, ensure_ascii=False))
        if confirm_summary(answers):
            return answers
        first = False
        _log('user changes the answers')
    return answers


# ---------------------------------------------------------------------------
# 3. apply
# ---------------------------------------------------------------------------

def _s_binaries(ctx, monitor, st):
    return OK if ctx._step_binary_installer(monitor) else FAILED


def _s_tinyppi(ctx, monitor, st):
    from resources.lib import addon_portal
    addon_portal.ensure_tinyppi(force=True)
    return OK


def _s_bootstrap(ctx, monitor, st):
    from resources.lib import bootstrap
    bootstrap.run()
    return OK


def _s_hw_tuning(ctx, monitor, st):
    from resources.lib import hw_tuning
    hw_tuning.auto()
    return OK


def _s_restore(ctx, monitor, st):
    path = st['answers'].get('restore')
    if not path:
        return SKIPPED
    if not os.path.exists(path):
        st['steps']['restore']['error'] = 'not found: %s' % path
        return FAILED
    from resources.lib import backup_manager
    pbar = xbmcgui.DialogProgress()
    pbar.create(T(30949), os.path.basename(path))

    def prog(i, n, name):
        if pbar.iscanceled():
            return False
        pbar.update(int((i + 1) * 100 / max(n, 1)), name)
        return True
    try:
        total, cancelled, after = backup_manager.restore_backup(path, prog)
    finally:
        pbar.close()
    st['steps']['restore']['detail'] = '%s files' % total
    if after.get('failed'):
        st['steps']['restore']['error'] = 'not reinstalled: %s' % ', '.join(after['failed'])
    return SKIPPED if cancelled else OK


def _s_addons(ctx, monitor, st):
    ids = st['answers'].get('addons') or []
    if not ids:
        return SKIPPED
    from resources.lib import addon_portal
    cat = {c[0]: c for c in addon_portal._catalog()}
    entries = [(i, cat[i][1], cat[i][2]) for i in ids if i in cat]
    if not entries:
        return SKIPPED
    by_name = {e[1]: e[0] for e in entries}
    results = addon_portal._install_selection(entries)
    bad = [by_name.get(n, n) for n, good, _note in results if not good]
    notes = ['%s: %s' % (n, note) for n, good, note in results if not good and note]
    try:
        from resources.lib import menu_reconcile
        menu_reconcile.run(rebuild=True)
    except Exception as e:
        _log('menu reconcile failed: %s' % e, xbmc.LOGWARNING)
    st['steps']['addons']['detail'] = '%d/%d' % (len(results) - len(bad), len(results))
    if bad:
        st['steps']['addons']['failed_ids'] = bad
        st['steps']['addons']['error'] = '; '.join(notes) or ', '.join(bad)
        return FAILED
    return OK


def _s_layout(ctx, monitor, st):
    mode = st['answers'].get('layout')
    if not mode:
        return SKIPPED
    from resources.lib import af3_shortcuts
    return OK if af3_shortcuts.apply(mode) else FAILED


def _s_lists(ctx, monitor, st):
    mode = st['answers'].get('lists')
    if not mode:
        return SKIPPED
    from resources.lib import trakt_hubs
    ok = trakt_hubs.apply(mode)
    trakt_hubs.wait_rebuild()
    return OK if ok else FAILED


def _s_patches(ctx, monitor, st):
    from resources.lib import patcher, patch_watchdog
    ids = [a for a in patcher.target_addon_ids() if patch_watchdog._addon_path(a)]
    ok_n, fail_n, written, _r = patcher.apply_set(addon_ids=ids)
    patcher.reload_skin_if_pending()
    st['steps']['patches']['detail'] = '%d ok, %d failed, %d written' % (ok_n, fail_n, written)
    return OK if fail_n == 0 else FAILED


def _s_webserver(ctx, monitor, st):
    from resources.lib import webserver_secure
    webserver_secure.first_run()
    return OK


def _s_lists_ensure(ctx, monitor, st):
    from resources.lib import trakt_hubs
    trakt_hubs.ensure()
    return OK


def _s_language(ctx, monitor, st):
    if not st['answers'].get('arabic', True):
        return SKIPPED
    from resources.lib import set_language
    set_language.force_arabic()
    return OK


RUNNERS = {
    'binaries': _s_binaries, 'tinyppi': _s_tinyppi, 'bootstrap': _s_bootstrap,
    'hw_tuning': _s_hw_tuning, 'restore': _s_restore, 'addons': _s_addons,
    'layout': _s_layout, 'lists': _s_lists, 'patches': _s_patches,
    'webserver': _s_webserver, 'lists_ensure': _s_lists_ensure,
    'language': _s_language,
}


def _skip_from_phone(st):
    """Sections finished on the phone are not run again on the TV."""
    phone = set(st['answers'].get('phone') or ())
    mapping = {'restore': 'restore', 'addons': 'addons', 'layout': 'layout',
               'lists': 'lists', 'anime': 'lists'}
    for section, key in mapping.items():
        s = st['steps'].get(key)
        if section in phone and s and s['status'] == PENDING:
            s.update(status=SKIPPED, detail='phone')


def apply_all(ctx, monitor, st):
    """Phase B. Runs every unfinished step; returns the state."""
    _skip_from_phone(st)
    save(st)
    for key, _lab, overlay_id, reloads in STEPS:
        if monitor.abortRequested():
            _log('Kodi is stopping - setup will resume at %s' % key)
            return st
        s = st['steps'].setdefault(key, {'status': PENDING, 'attempts': 0})
        if s['status'] in (OK, SKIPPED, FAILED):
            continue
        if s['status'] == RUNNING:
            _log('step %s was interrupted (attempt %d)' % (key, s.get('attempts', 0)),
                 xbmc.LOGWARNING)
        if s.get('attempts', 0) >= MAX_ATTEMPTS:
            s.update(status=FAILED, error=s.get('error') or 'interrupted %d times' % s['attempts'])
            _log('step %s gave up after %d interrupted attempts' % (key, s['attempts']),
                 xbmc.LOGERROR)
            save(st)
            continue
        ctx._overlay('step', overlay_id)
        if reloads:
            ctx._overlay('pause', '%s can reload the skin' % key)
        ctx._wait_no_modal(monitor)
        if key in ('patches', 'lists', 'lists_ensure'):
            ctx._wait_skin_build(monitor)
        s.update(status=RUNNING, attempts=s.get('attempts', 0) + 1,
                 started=int(time.time()), error='')
        save(st)
        _log('step %s: start (attempt %d)' % (key, s['attempts']))
        t0 = time.time()
        try:
            status = RUNNERS[key](ctx, monitor, st) or OK
        except Exception:
            status = FAILED
            s['error'] = traceback.format_exc().strip().splitlines()[-1][:200]
            _log('step %s crashed:\n%s' % (key, traceback.format_exc()), xbmc.LOGERROR)
        s.update(status=status, seconds=round(time.time() - t0, 1), ended=int(time.time()))
        save(st)
        _log('step %s: %s in %.1fs%s' % (key, status, s['seconds'],
                                         (' - ' + s['error']) if s.get('error') else ''))
        if reloads:
            ctx._wait_skin_settle(monitor)
            ctx._overlay('ensure')
    if not unfinished(st):
        st['phase'] = 'done'
        st['finished'] = int(time.time())
        st['report_pending'] = True
        save(st)
        write_report(st)
    return st


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def write_report(st):
    rep = {'version': st.get('version'), 'build': st.get('build'),
           'started': st.get('started'), 'finished': st.get('finished'),
           'duration_s': (st.get('finished') or 0) - (st.get('started') or 0),
           'resumes': st.get('resumes', 0), 'answers': st.get('answers'),
           'steps': [dict(key=k, **(st['steps'].get(k) or {})) for k in STEP_KEYS]}
    try:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
    except Exception as e:
        _log('could not write report: %s' % e, xbmc.LOGWARNING)
    counts = {s: 0 for s in (OK, FAILED, SKIPPED)}
    for k in STEP_KEYS:
        counts[st['steps'].get(k, {}).get('status', SKIPPED)] = \
            counts.get(st['steps'].get(k, {}).get('status', SKIPPED), 0) + 1
    _log('REPORT: %d ok, %d failed, %d skipped in %ds (resumes %d)'
         % (counts[OK], counts[FAILED], counts[SKIPPED], rep['duration_s'], rep['resumes']))
    return rep


def report_text(st):
    marks = {OK: '[COLOR FF33D17A]✔[/COLOR]', FAILED: '[COLOR FFFF5555]✘[/COLOR]',
             SKIPPED: '[COLOR FF888888]–[/COLOR]'}
    counts = {OK: 0, FAILED: 0, SKIPPED: 0}
    lines = []
    for k in STEP_KEYS:
        s = st['steps'].get(k) or {}
        status = s.get('status', SKIPPED)
        counts[status] = counts.get(status, 0) + 1
        extra = s.get('error') or s.get('detail') or ''
        secs = ' (%ss)' % s['seconds'] if s.get('seconds') else ''
        lines.append('%s  %s%s%s' % (marks.get(status, '?'), step_label(k), secs,
                                     ('  -  ' + extra) if extra else ''))
    head = T(30939) % (counts[OK], counts[FAILED], counts[SKIPPED])
    tail = ('[CR][CR]' + T(30940)) if counts[FAILED] else ''
    return head + '[CR][CR]' + '[CR]'.join(lines) + tail


def show_pending_report(monitor):
    """Once, after the reboot that ends setup."""
    st = load()
    if not st or st.get('phase') != 'done' or not st.get('report_pending'):
        return
    for _ in range(90):                      # home screen, nothing on top
        if xbmc.getCondVisibility('Window.IsVisible(home)') and \
                not xbmc.getCondVisibility('System.HasModalDialog'):
            break
        if monitor.waitForAbort(2):
            return
    if monitor.waitForAbort(6):
        return
    st['report_pending'] = False
    save(st)
    xbmcgui.Dialog().textviewer(T(30938), report_text(st))
