# -*- coding: utf-8 -*-
"""Background service:
 - Auto-downloads the best Arabic subtitle when a video starts without one.
 - Runs queued Gemini proofreading jobs and swaps in the improved subtitle.
"""
import json
import os
import threading
import time

import xbmc
import xbmcgui

from resources.lib.common import ADDON_NAME, JOBS_DIR, log, notify, setting_bool, set_status
from resources.lib import media, providers, pipeline


MONITOR = [None]
NO_KEY_TOLD = [False]


class Player(xbmc.Player):
    def _offer_embedded(self, video, path):
        """No Arabic subtitle found: offer to translate the one inside the video."""
        try:
            from resources.lib import llm
            if not setting_bool('embedded_ask', True) or not setting_bool('embedded_ai', True) \
                    or not llm.any_available():
                return False
            lang = pipeline.embedded_text_info(video)
            if not lang or not self.isPlayingVideo() or self.getPlayingFile() != path:
                return False
            msg = ('لم يُعثر على ترجمة عربية لهذا العمل.[CR]'
                   'لكن الفيديو يحتوي على ترجمة %s مدمجة، فهل تريد ترجمتها إلى العربية بالذكاء الاصطناعي؟' % lang)
            try:
                yes = xbmcgui.Dialog().yesno(ADDON_NAME, msg, nolabel='لا', yeslabel='نعم، ترجم',
                                             autoclose=20000, defaultbutton=xbmcgui.DLG_YESNO_YES_BTN)
            except (TypeError, AttributeError):          # Kodi 19/20
                yes = xbmcgui.Dialog().yesno(ADDON_NAME, msg, nolabel='لا', yeslabel='نعم، ترجم',
                                             autoclose=20000)
            if not yes or not self.isPlayingVideo() or self.getPlayingFile() != path:
                set_status('')
                return True
            bar = xbmcgui.DialogProgressBG()
            bar.create(ADDON_NAME, 'جارٍ استخراج الترجمة المدمجة وترجمتها...')

            def pos():
                try:
                    return self.getTime() * 1000
                except Exception:
                    return 0
            try:
                sub_path, summary = pipeline.embedded_translate(
                    video, progress=lambda p, m: bar.update(int(p), ADDON_NAME, m),
                    abort=lambda: not self.isPlayingVideo(), position=pos)
            finally:
                bar.close()
            if self.isPlayingVideo() and self.getPlayingFile() == path:
                self.setSubtitles(sub_path)
                self.showSubtitles(True)
                set_status(summary[0] if summary else 'الترجمة تعمل ✓', 'busy' if os.listdir(JOBS_DIR) else 'ok')
                notify(' | '.join(summary), seconds=6)
            return True
        except Exception as e:
            log('embedded offer failed: %s' % e, xbmc.LOGERROR)
            set_status('فشل استخراج الترجمة المدمجة', 'err')
            notify(str(e).split('\n')[-1][:80], seconds=6)
            return True

    def __init__(self):
        xbmc.Player.__init__(self)
        self.last_path = None

    def setSubtitles(self, path):
        # Piers edition: a subtitle Najd sets is not an outside one to time
        from resources.lib import extwatch
        extwatch.najd_set()
        xbmc.Player.setSubtitles(self, path)

    def onPlayBackStopped(self):
        set_status('')
        if getattr(self, 'live', None):
            self.live.stop = True
        self._after(False)

    def onPlayBackEnded(self):
        set_status('')
        self._after(True)

    def _watch(self, token):
        """Remember how far the viewer got (for the timing question at the end)."""
        while getattr(self, 'fb', None) and self.fb.get('token') == token:
            try:
                if self.isPlayingVideo():
                    self.fb['pos'] = self.getTime()
                    self.fb['total'] = self.getTotalTime() or self.fb.get('total', 0)
            except Exception:
                pass
            if MONITOR[0].waitForAbort(5):
                return

    def _after(self, ended):
        fb, self.fb = getattr(self, 'fb', None), None
        if not fb or not setting_bool('ask_timing', True):
            return
        if not ended and (not fb.get('total') or fb.get('pos', 0) < 0.6 * fb['total']):
            return
        threading.Thread(target=self._ask_timing, args=(fb['video'],), daemon=True).start()

    def _ask_timing(self, video):
        try:
            from resources.lib import trace
            if not trace.has_sync(video):
                return
            if MONITOR[0].waitForAbort(3) or self.isPlayingVideo():
                return          # next episode already started: don't interrupt
            opts = ['مضبوط', 'تظهر قبل الكلام (متقدمة)', 'تظهر بعد الكلام (متأخرة)',
                    'جزء منها فقط غير مضبوط', 'لم أنتبه']
            codes = ['ok', 'early', 'late', 'part', 'skip']
            k = xbmcgui.Dialog().select('ترجمة نجد — كيف كان توقيت الترجمة؟', opts, autoclose=25000)
            if k < 0:
                return
            ans = codes[k]
            if ans == 'part':
                w = xbmcgui.Dialog().select('أين تقريباً؟', ['البداية', 'المنتصف', 'النهاية', 'لا أدري'],
                                            autoclose=20000)
                ans += ':' + ['start', 'middle', 'end', '?'][w] if w >= 0 else ''
            trace.feedback(video, ans)
            if ans != 'skip':
                notify('شكراً، حُفظ في التقرير ✓', seconds=3)
        except Exception as e:
            log('timing question failed: %s' % e)

    def onAVStarted(self):
        set_status('')
        try:
            token = time.time()
            self.fb = {'token': token, 'video': media.current(), 'pos': 0, 'total': 0}
            threading.Thread(target=self._watch, args=(token,), daemon=True).start()
        except Exception as e:
            log('watch not started: %s' % e)
        try:
            if getattr(self, 'live', None):
                self.live.stop = True
            from resources.lib import live
            self.live = live.start(self, MONITOR[0], self.getPlayingFile())
        except Exception as e:
            log('live check not started: %s' % e)
        threading.Thread(target=self._auto, daemon=True).start()
        try:
            # Piers edition: time any subtitle another add-on or file puts on
            from resources.lib import extwatch
            extwatch.start(self, self.getPlayingFile())
        except Exception as e:
            log('external sync watch not started: %s' % e)

    def _auto(self):
        try:
            # let the player / streaming add-on finish starting before doing anything
            for _ in range(10):
                xbmc.sleep(1000)
                if not self.isPlayingVideo():
                    return
            if xbmc.getCondVisibility('Player.Paused') or \
                    xbmc.getCondVisibility('Window.IsActive(subtitlesearch)'):
                return
            path = self.getPlayingFile()
            if path == self.last_path:
                return
            self.last_path = path
            if self.getTotalTime() < 600:          # skip trailers / clips
                return
            try:
                cur = media.current()
                r = pipeline.final_resume(cur) or pipeline.embedded_resume(cur) or pipeline.reference_resume(cur)
            except Exception as e:
                log('embedded resume failed: %s' % e)
                r = None
            if r:
                sub_path, pct = r
                self.setSubtitles(sub_path)
                self.showSubtitles(True)
                if pct < 100:
                    set_status('الترجمة جاهزة بنسبة %d٪، ويكتمل الباقي في الخلفية...' % pct, 'busy')
                    notify('عدت إلى الفيلم: الترجمة جاهزة بنسبة %d٪ ويكتمل الباقي تلقائياً' % pct, seconds=5)
                else:
                    set_status('الترجمة المحفوظة تعمل ✓', 'ok')
                    notify('شُغّلت الترجمة المحفوظة لهذا العمل (دون إعادة تنزيل أو تعديل)', seconds=4)
                return
            if not setting_bool('auto_download', True):
                return
            if media.is_dexhub_item(self) and not media.subtitle_streams_have_arabic():
                # Piers edition: Dex Hub loads its own subtitle after the start;
                # give it the first go so the subtitle is not swapped twice.
                set_status('بانتظار ترجمة Dex Hub...')
                for _ in range(30):
                    xbmc.sleep(1000)
                    if not self.isPlayingVideo() or self.getPlayingFile() != path:
                        set_status('')
                        return
                    if media.subtitle_streams_have_arabic():
                        break
                set_status('')
            if media.subtitle_streams_have_arabic():
                # Piers edition: turn the video's own Arabic subtitle on
                # instead of only reporting that it is there
                if media.enable_arabic_stream() == 'switched':
                    set_status('تم تفعيل الترجمة العربية المدمجة ✓', 'ok')
                    notify('تم تفعيل الترجمة العربية الموجودة في الفيديو', seconds=4)
                else:
                    set_status('الفيديو يحتوي على ترجمة عربية ✓', 'ok')
                return
            # the same list the search below really uses: only sites with a key (the subtitle
            # add-ons installed in Kodi are never called in the background)
            enabled = tuple(n for n in ('najdindex', 'subdl', 'subsource', 'opensubtitles') if providers.PROVIDERS[n].available())
            if not enabled:
                if not self._offer_embedded(media.current(), path):
                    msg = 'التنزيل التلقائي يحتاج إلى مفتاح موقع ترجمة؛ افتح قائمة الترجمة واختر بنفسك'
                    set_status(msg, 'err')
                    notify(msg, seconds=7)
                return
            set_status('جارٍ البحث عن ترجمة عربية...')
            video = media.current()
            results = [r for r in providers.search_all(video, ['ar'], enabled=enabled)
                       if r['lang'] == 'ar']
            if not results:
                msg = 'تعذر الاتصال بمواقع الترجمة' if providers.all_failed() \
                    else 'لم يُعثر على ترجمة عربية لهذا العمل'
                if enabled == ('najdindex',):       # no site keys: the old advice still holds
                    msg = 'التنزيل التلقائي يحتاج إلى مفتاح موقع ترجمة؛ افتح قائمة الترجمة واختر بنفسك'
                set_status(msg, 'err')
                if not self._offer_embedded(video, path):
                    notify(msg)
                return
            set_status('عُثر على ترجمة، جارٍ تجهيزها...')
            notify('عُثر على ترجمة، جارٍ التجهيز...', seconds=3)
            for item in results[:3]:
                try:
                    sub_path, summary = pipeline.process(item, video)
                except Exception as e:
                    log('auto: candidate failed: %s' % e)
                    continue
                if self.isPlayingVideo() and self.getPlayingFile() == path:
                    if media.subtitle_streams_have_arabic():
                        return          # user (or Kodi) already loaded an Arabic subtitle meanwhile
                    self.setSubtitles(sub_path)
                    self.showSubtitles(True)
                    set_status('الترجمة تعمل، وجارٍ ضبطها مع الصوت...' if os.listdir(JOBS_DIR)
                               else 'الترجمة تعمل ✓', 'busy' if os.listdir(JOBS_DIR) else 'ok')
                    notify('تمت إضافة الترجمة%s' % (' | ' + ' | '.join(summary) if summary else ''),
                           seconds=7)
                return
            set_status('تعذر تجهيز الترجمة', 'err')
        except Exception as e:
            set_status('')
            log('auto download error: %s' % e, xbmc.LOGERROR)


def process_jobs(player, monitor):
    for name in sorted(os.listdir(JOBS_DIR)):
        if not name.endswith('.json'):
            continue             # still being written
        full = os.path.join(JOBS_DIR, name)
        try:
            with open(full, encoding='utf-8') as f:
                job = json.load(f)
        except Exception:
            os.remove(full)
            continue
        os.remove(full)
        if time.time() - job.get('time', 0) > 6 * 3600 or not os.path.exists(job['path']):
            continue
        vpath = (job.get('video') or {}).get('path', '')

        def still_playing():
            try:
                return player.isPlayingVideo() and (not vpath or player.getPlayingFile() == vpath)
            except Exception:
                return False

        if vpath and not still_playing():
            continue
        bar = xbmcgui.DialogProgressBG()
        bar.create(ADDON_NAME, 'جارٍ الاستماع إلى الفيلم...' if 'audio' in job['steps']
                   else 'جارٍ ترجمة باقي الفيلم...' if 'reference_more' in job['steps']
                   else 'جارٍ استخراج باقي الترجمة وترجمته...' if 'embedded_more' in job['steps']
                   else 'جارٍ التصحيح بالذكاء الاصطناعي...')
        current = [job['path']]

        def replaced():
            """The viewer picked another subtitle meanwhile (a new job is waiting, or the
            subtitle on screen is not one of this job's versions): stop, free the queue."""
            if 'embedded_more' not in job['steps'] and 'reference_more' not in job['steps']:
                return False
            try:
                if any(n.endswith('.json') for n in os.listdir(JOBS_DIR)):
                    return True
                last = pipeline.last_for(job.get('video') or {})
                return bool(last) and last.get('path') != current[0] and \
                    (last.get('lineage') or last.get('path')) not in (job['path'], current[0]) and \
                    (last.get('item') or {}).get('provider') not in ('embedded', 'reference')
            except Exception:
                return False

        def swap(path, msg_lines):
            last = pipeline.last_for(job.get('video') or {})
            if last and last.get('path') != current[0] and \
                    (last.get('lineage') or last.get('path')) not in (job['path'], current[0]):
                return False          # user picked another subtitle meanwhile
            if still_playing():
                player.setSubtitles(path)
                player.showSubtitles(True)
                pipeline.remember_last(path, job.get('video') or {}, job.get('item') or {},
                                       lineage=job['path'])
                current[0] = path
                return True
            return False

        def early(path, msg_lines):
            try:
                ok = swap(path, msg_lines)
            except Exception as e:
                log('early swap failed: %s' % e, xbmc.LOGERROR)
                ok = False
            if ok and any('جاهز' in l for l in msg_lines):
                set_status(msg_lines[0] + '، ويكتمل الباقي...', 'busy')
            elif ok:
                partial = 'التالية' in ' '.join(msg_lines)
                set_status('صُحّحت الأسطر التالية ✓، ويكتمل الباقي...' if partial
                           else 'صُحّح النص ✓، وجارٍ ضبط التوقيت...')
                notify(' | '.join(msg_lines), seconds=5)

        try:
            def pos():
                try:
                    return player.getTime() * 1000 if still_playing() else 0
                except Exception:
                    return 0
            new_path, lines = pipeline.run_job(
                job, on_update=early, position=pos,
                progress=lambda p, m: (bar.update(p, ADDON_NAME, m),
                                       set_status('%s %d%%' % (m.rstrip('.').rstrip(), p)))
                if still_playing() else None,
                abort=lambda: monitor.abortRequested() or not still_playing() or replaced())
        except Exception as e:
            import traceback
            log('job failed: %s\n%s' % (e, traceback.format_exc()), xbmc.LOGERROR)
            new_path, lines = None, ['تعذر إكمال المعالجة (%s)' % type(e).__name__]
        finally:
            bar.close()
        if not still_playing():
            set_status('')            # playback ended: nothing to report on screen
            continue
        if not new_path:
            bad = [l for l in lines if any(x in l for x in ('تعذر', 'لم ', 'لا يطابق', 'غير'))]
            if bad:
                set_status(bad[0].split(':')[0][:45], 'err')
            else:
                set_status('الترجمة تعمل ✓', 'ok')
        if new_path or (lines and not any(x in ' '.join(lines) for x in
                                          ('نفد', 'تعذر', 'لم ', 'توقف', 'غير', 'لا يطابق', 'مشغول', 'خطأ'))):
            # finished (not stopped halfway by an error or a used-up AI allowance): keep it,
            # so the next time this film plays nothing is redone
            try:
                pipeline.keep_final(job.get('video') or {}, new_path or current[0], job.get('item') or {})
            except Exception as e:
                log('keep_final: %s' % e)
        if new_path:
            if swap(new_path, lines):
                set_status('الترجمة مضبوطة ✓' if 'audio' in job['steps'] or 'understand' in job['steps']
                           else 'الترجمة كاملة ✓' if ('embedded_more' in job['steps'] or 'reference_more' in job['steps'])
                           else 'صُحّح النص ✓', 'ok')
            else:
                log('a newer subtitle was chosen meanwhile (or playback ended); not swapping')
                continue
        if lines:
            notify(' | '.join(lines), seconds=8)


if __name__ == '__main__':
    monitor = xbmc.Monitor()
    MONITOR[0] = monitor
    player = Player()
    log('service started')
    try:
        from resources.lib import health
        health.start(monitor)
    except Exception as e:
        log('health record: %s' % e)
    set_status('')
    try:
        from resources.lib.badge import Badge
        Badge(monitor).start()
    except Exception as e:
        log('badge disabled: %s' % e)
    try:
        pipeline.forget_old_offsets()
    except Exception as e:
        log('offset cleanup: %s' % e)
    first_run = not setting_bool('wizard_done', False)
    try:
        from resources.lib import whatsnew
        threading.Thread(target=whatsnew.maybe_show, args=(monitor, first_run), daemon=True).start()
    except Exception as e:
        log('what\'s new failed: %s' % e)
    def ask_dexhub_key():
        """Piers edition (advice of Dex Hub's author): Dex Hub's AI key is
        used only after the user says yes - it spends that account's tokens.
        Asked once, on the home screen, when Najd has no AI key of its own."""
        from resources.lib import llm
        from resources.lib.common import ADDON, PROFILE, abtools_setup_busy
        flag = os.path.join(PROFILE, 'dexhub_key_asked')
        try:
            if os.path.exists(flag) or setting_bool('use_dexhub_key', False) or llm.configured() \
                    or not llm.dexhub_has_key():
                return
        except Exception as e:
            log('dexhub key check: %s' % e)
            return
        for _ in range(600):
            if monitor.waitForAbort(5):
                return
            if xbmc.getCondVisibility('Window.IsActive(home)') and \
                    not xbmc.getCondVisibility('Player.HasMedia') and \
                    not xbmc.getCondVisibility('System.HasActiveModalDialog') and not abtools_setup_busy():
                break
        else:
            return
        yes = xbmcgui.Dialog().yesno(
            ADDON_NAME, 'يوجد مفتاح ذكاء اصطناعي محفوظ في Dex Hub.[CR]'
            'هل تسمح لنجد باستعماله لتصحيح الترجمات وترجمتها؟[CR]'
            '[COLOR gold]سيُستهلك من رصيد ذلك المفتاح.[/COLOR] يمكنك تغيير ذلك لاحقاً من إعدادات نجد.',
            nolabel='لا', yeslabel='نعم، اسمح')
        try:
            open(flag, 'w').close()
        except OSError:
            pass
        ADDON.setSetting('use_dexhub_key', 'true' if yes else 'false')
        log('Dex Hub AI key: %s by the user' % ('allowed' if yes else 'declined'))

    if not first_run:
        threading.Thread(target=ask_dexhub_key, daemon=True).start()
    if first_run:
        # first run: open the setup wizard once Kodi's home screen is up.
        # Piers edition: in its own thread (the job loop below starts at once)
        # and never over AB Tools' first-run setup or a playing video.
        def first_run_wizard():
            from resources.lib.common import ADDON, abtools_setup_busy
            for _ in range(60):
                if monitor.waitForAbort(2) or xbmc.getCondVisibility('Window.IsActive(home)'):
                    break
            while not monitor.abortRequested() and (
                    abtools_setup_busy() or xbmc.getCondVisibility('Player.HasMedia') or
                    not xbmc.getCondVisibility('Window.IsActive(home)')):
                if monitor.waitForAbort(5):
                    return
            if not monitor.abortRequested():
                ADDON.setSetting('wizard_done', 'true')
                xbmc.executebuiltin('RunScript(service.subtitles.najdsmart,wizard)')
        threading.Thread(target=first_run_wizard, daemon=True).start()
    busy = threading.Lock()

    def worker():
        with busy:
            process_jobs(player, monitor)

    from resources.lib.common import ensure_dirs
    while not monitor.abortRequested():
        ensure_dirs()
        if any(n.endswith('.json') for n in os.listdir(JOBS_DIR)) and not busy.locked():
            threading.Thread(target=worker, daemon=True).start()
        if monitor.waitForAbort(2):
            break
    try:
        health.stop()
    except Exception:
        pass
    log('service stopped')
