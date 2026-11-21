# -*- coding: utf-8 -*-
"""Piers edition: the player's «sync» button (AF3 OSD / AB Tools subtitle
window) - time the subtitle that is on screen now, whoever put it there.

 - a subtitle Najd set (its own download, or an outside one it timed):
   on the video's embedded timeline at once, else a background job
   (English reference by meaning, Whisper, the sound);
 - an outside subtitle file (any add-on, the subtitle window, a file beside
   the video): the same, via pipeline.sync_external;
 - the video's own embedded track: it is already the film's timing.
"""
import os
import time

import xbmc

from .common import log, notify, set_status, setting, setting_bool
from . import extwatch, media, pipeline


def _job_steps(video):
    """The same choice as the menu's «re-time» (service.resync), with Whisper
    after the free listening when Groq is linked."""
    from . import llm
    if setting('sync_method', 'smart') in ('smart', 'auto') and llm.any_available() and \
            pipeline.has_reference(video):
        return ['semantic']
    if pipeline.embedded_reference(video):
        return ['emb_alt']             # the video's own subtitle: look again, part by part
    whisper_ok = False
    try:
        from . import whisper
        whisper_ok = setting_bool('whisper_sync', True) and whisper.available()
    except Exception as e:
        log('osd sync: whisper check: %s' % e)
    if not pipeline.is_stream(video) and pipeline.audio_possible(video):
        return ['audio']
    if pipeline.is_stream(video) and pipeline.finetune_possible(video):
        return ['finetune', 'whisper'] if whisper_ok else ['finetune']
    if pipeline.audio_possible(video):
        return ['audio']
    return []


def _apply(player, vpath, r):
    new_path, mode, lines = r
    if mode == 'now' and player.isPlayingVideo() and player.getPlayingFile() == vpath:
        player.setSubtitles(new_path)
        player.showSubtitles(True)
        set_status('الترجمة مضبوطة ✓', 'ok')
        notify(' | '.join(lines) if lines else 'الترجمة مضبوطة ✓', seconds=6)
    elif mode == 'same':
        set_status('الترجمة مضبوطة ✓', 'ok')
        notify('الترجمة مضبوطة أصلاً ✓', seconds=4)
    else:
        set_status(lines[0] if lines else 'جارٍ ضبط الترجمة...')
        notify('جارٍ ضبط التوقيت... وستُستبدل الترجمة تلقائياً عند الانتهاء', seconds=5)


def run():
    player = xbmc.Player()
    if not player.isPlayingVideo():
        notify('شغّل الفيديو أولاً ثم زامن الترجمة')
        return
    vpath = player.getPlayingFile()
    video = media.current()
    st = extwatch._state()
    if not st['enabled'] or st['index'] < 0:
        notify('لا توجد ترجمة معروضة الآن')
        return
    external = st['external'] is True or 'external' in st['name'].lower()
    last = pipeline.last_for(video)
    if not external and not last:
        notify('هذه الترجمة مدمجة في الفيديو، وتوقيتها مضبوط على الفيلم أصلاً', seconds=5)
        return
    set_status('جارٍ ضبط توقيت الترجمة...')
    notify('جارٍ ضبط توقيت الترجمة...', seconds=3)
    try:
        path = extwatch.find_file(st, vpath, time.time() - 600) if external else ''
        if path:                                   # an outside subtitle file
            src = extwatch._local_copy(path)
            r = pipeline.sync_external(src, video) if src else None
            log('osd sync: outside file %s -> %s' % (path, r and r[1]))
            if r:
                _apply(player, vpath, r)
                return
        elif last:                                 # Najd's own subtitle
            steps = _job_steps(video)
            if steps:
                pipeline.queue_job(last['path'], video, last.get('item') or {}, steps, resync=True)
                log('osd sync: own subtitle queued %s' % steps)
                set_status('جارٍ ضبط الترجمة...')
                notify('جارٍ ضبط التوقيت... وستُستبدل الترجمة تلقائياً عند الانتهاء', seconds=5)
                return
        else:
            set_status('')
            notify('لم يُعثر على ملف الترجمة الحالية. اخترها من قائمة الترجمة ثم أعد المحاولة', seconds=6)
            return
    except Exception as e:
        log('osd sync failed: %s' % e, xbmc.LOGERROR)
    set_status('')
    notify('تعذر ضبط هذه الترجمة: لا مرجع لتوقيت الفيلم ولا يمكن الاستماع إلى صوته', seconds=6)
