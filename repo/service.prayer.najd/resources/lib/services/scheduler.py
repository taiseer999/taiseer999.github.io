# -*- coding: utf-8 -*-
import os
import threading
from datetime import datetime, timedelta
from resources.lib.core.prayer_engine import calculate, NAMES, as_datetime, name_of
from resources.lib.core import cities
from resources.lib.storage.database import Database

class Scheduler(object):
    def __init__(self, addon, profile, xbmc, xbmcgui, addon_path=''):
        self.addon=addon; self.xbmc=xbmc; self.xbmcgui=xbmcgui; self.addon_path=addon_path
        self.db=Database(profile.rstrip('/\\') + '/najd_prayer.sqlite')
        self._last_day=None; self._today=None
    def _s(self,key,default=''):
        v=self.addon.getSetting(key)
        return v if v not in (None,'') else default
    def _location(self):
        return cities.resolve(self._s('city','0'), self._s('latitude','24.7136'),
                              self._s('longitude','46.6753'), self._s('utc_offset','3'))
    def _city_name(self):
        return cities.name_of(self._s('city','0'), self._s('city_name','الرياض'))
    def _times(self, day):
        methods=['UmmAlQura','MWL','Egypt','Karachi','ISNA']; schools=['standard','hanafi']
        mi=int(self._s('calculation_method','0') or 0); si=int(self._s('asr_school','0') or 0)
        la,lo,tz=self._location()
        signature='|'.join([str(la),str(lo),str(tz),str(mi),str(si),self._s('isha_interval','90')]+[self._s('adjust_'+k,'0') for k in ('fajr','sunrise','dhuhr','asr','maghrib','isha')])
        key=day.isoformat()+':'+signature
        cached=self.db.get_day(key)
        if cached: return cached
        adj={k:int(self._s('adjust_'+k,'0') or 0) for k in ('fajr','sunrise','dhuhr','asr','maghrib','isha')}
        data=calculate(day,la,lo,tz,methods[max(0,min(mi,4))],schools[max(0,min(si,1))],adj,float(self._s('isha_interval','90')))
        self.db.put_day(key,data); return data
    def current(self, now=None):
        now=now or datetime.now(); data=self._times(now.date())
        ordered=[]
        for k in ('fajr','sunrise','dhuhr','asr','maghrib','isha'):
            dt=as_datetime(now.date(),data.get(k))
            if dt: ordered.append((k,dt))
        upcoming=next(((k,dt) for k,dt in ordered if dt>now),None)
        if not upcoming:
            tomorrow=now.date()+timedelta(days=1); td=self._times(tomorrow)
            upcoming=next(((k,as_datetime(tomorrow,td[k])) for k in ('fajr','sunrise','dhuhr','asr','maghrib','isha') if td.get(k)),None)
        return data,upcoming
    def next_salah(self, now=None):
        """Next of the five prayers (sunrise excluded) as (key, datetime)."""
        now=now or datetime.now()
        for day in (now.date(), now.date()+timedelta(days=1)):
            data=self._times(day)
            for k in ('fajr','dhuhr','asr','maghrib','isha'):
                dt=as_datetime(day,data.get(k))
                if dt and dt>now: return k,dt
        return None
    def tick(self):
        now=datetime.now(); data=self._times(now.date())
        if self._last_day != now.date(): self._last_day=now.date(); self._today=data
        self._publish_properties(now, data)
        # Fire only within 75 seconds of the scheduled minute; never replay stale events after restart.
        if self._s('notifications','true') == 'true':
            for key in ('fajr','dhuhr','asr','maghrib','isha'):
                dt=as_datetime(now.date(),data.get(key))
                if not dt: continue
                delta=(now-dt).total_seconds()
                if 0 <= delta < 75:
                    event_key=now.date().isoformat()+':'+key
                    if self.db.mark_fired(event_key): self._dispatch(key,False)
                reminder=int(self._s('reminder_minutes','0') or 0)
                if reminder > 0:
                    target=dt-timedelta(minutes=reminder)
                    if 0 <= (now-target).total_seconds() < 75:
                        event_key=now.date().isoformat()+':'+key+':pre'
                        if self.db.mark_fired(event_key): self._dispatch(key,True)
        return data
    def _publish_properties(self, now, data):
        """Expose the next prayer to the Home window so skins can show it next to the
        Kodi clock. Not every skin reads these, so the feature is best-effort."""
        if self._s('show_clock_widget','true') != 'true':
            return
        win=self.xbmcgui.Window(10000)  # Home
        upcoming=None
        for k in ('fajr','sunrise','dhuhr','asr','maghrib','isha'):
            dt=as_datetime(now.date(),data.get(k))
            if dt and dt>now: upcoming=(k,dt); break
        if not upcoming:
            tomorrow=now.date()+timedelta(days=1); td=self._times(tomorrow)
            for k in ('fajr','sunrise','dhuhr','asr','maghrib','isha'):
                dt=as_datetime(tomorrow,td.get(k))
                if dt: upcoming=(k,dt); break
        if upcoming:
            key,dt=upcoming; mins=max(0,int((dt-now).total_seconds()//60))
            win.setProperty('NajdPrayer.Next','%s %s'%(name_of(key,dt),dt.strftime('%H:%M')))
            win.setProperty('NajdPrayer.NextName',name_of(key,dt))
            win.setProperty('NajdPrayer.NextTime',dt.strftime('%H:%M'))
            win.setProperty('NajdPrayer.Remaining','%02d:%02d'%(mins//60,mins%60))

    def _adhan_time_str(self, key):
        try:
            return self._times(datetime.now().date()).get(key) or ''
        except Exception:
            return ''
    # ---- what to do at adhan while a video plays (setting video_adhan_action) ----
    NOTIFY_ONLY, PAUSE_ONLY, ADHAN_RESUME, ASK = 0, 1, 2, 3

    def _adhan_path(self, key):
        """Per-prayer file > general file > bundled 20-second adhan."""
        custom=self._s('adhan_'+key,'') or self._s('adhan_file','')
        if custom: return custom
        if self.addon_path:
            bundled=os.path.join(self.addon_path,'resources','media','adhan.mp3')
            if os.path.exists(bundled): return bundled
        return ''
    def _paused(self):
        try: return bool(self.xbmc.getCondVisibility('Player.Paused'))
        except Exception: return False
    def _pause_video(self):
        try:
            if not self._paused(): self.xbmc.Player().pause()
        except Exception as exc:
            self.xbmc.log('[NajdPrayer] pause error: %s' % exc,self.xbmc.LOGERROR)
    def _unpause_video(self):
        try:
            if self._paused(): self.xbmc.Player().pause()
        except Exception as exc:
            self.xbmc.log('[NajdPrayer] resume error: %s' % exc,self.xbmc.LOGERROR)
    def _play_adhan(self, path):
        try: self.xbmc.Player().play(path)
        except Exception as exc: self.xbmc.log('[NajdPrayer] audio error: %s' % exc,self.xbmc.LOGERROR)

    def _play_adhan_then_resume(self, path):
        """Remember the film + position, play the adhan, then resume the film
        from the same spot once the adhan ends (or the user stops it)."""
        player=self.xbmc.Player()
        try:
            saved=player.getPlayingFile(); pos=player.getTime()
        except Exception:
            saved=None; pos=0
        # Keep the film's full item (title, year, IMDb/TMDb, art...). Replaying the
        # bare URL loses it, and then subtitle add-ons cannot find the subtitle.
        try:
            item=player.getPlayingItem()
        except Exception:
            item=None
        self._play_adhan(path)
        if not saved:
            return
        t=threading.Thread(target=self._resume_after_adhan, args=(saved, pos, item))
        t.daemon=True; t.start()

    def _resume_after_adhan(self, saved, pos, item=None):
        mon=self.xbmc.Monitor(); player=self.xbmc.Player()
        # wait for the adhan to start (up to ~15 s)
        for _ in range(30):
            if player.isPlayingAudio(): break
            if mon.waitForAbort(0.5): return
        else:
            return
        # wait for the adhan to finish (max ~15 min); bail out if the user starts a video
        for _ in range(1800):
            if not player.isPlaying(): break
            if player.isPlayingVideo(): return
            if mon.waitForAbort(0.5): return
        if mon.waitForAbort(1.0) or player.isPlaying():
            return  # user started something else meanwhile
        start=max(0.0, pos-3.0)
        li=None
        if item is not None:
            try:
                item.setPath(saved); li=item
            except Exception:
                li=None
        if li is None:
            li=self.xbmcgui.ListItem(path=saved)
        li.setProperty('StartOffset', '%.1f' % start)
        player.play(saved, li)
        # fallback: some sources ignore StartOffset — seek manually once playing
        for _ in range(40):
            if player.isPlayingVideo(): break
            if mon.waitForAbort(0.5): return
        try:
            if player.isPlayingVideo() and player.getTime() < start-15:
                player.seekTime(start)
        except Exception:
            pass

    def _ask_at_adhan(self, title):
        """Video is already paused. Returns 'adhan', 'resume' or 'stay'."""
        try:
            args=('حان الآن وقت صلاة %s' % title,
                  'تم إيقاف الفيلم مؤقتاً.\nهل تريد تشغيل الأذان ثم إكمال الفيلم من نفس المكان؟',
                  'إبقاء الفيلم متوقفاً', 'متابعة الفيلم', 'تشغيل الأذان', 600000)
            yes_btn=getattr(self.xbmcgui,'DLG_YESNO_YES_BTN',None)
            try:
                r=self.xbmcgui.Dialog().yesnocustom(*args, defaultbutton=yes_btn) if yes_btn is not None \
                    else self.xbmcgui.Dialog().yesnocustom(*args)
            except TypeError:  # older Kodi without defaultbutton
                r=self.xbmcgui.Dialog().yesnocustom(*args)
        except Exception as exc:
            self.xbmc.log('[NajdPrayer] ask dialog error: %s' % exc,self.xbmc.LOGERROR)
            return 'stay'
        # 1=yes (adhan), 0=no (resume), 2=custom (stay), -1=timeout/cancel (stay: user may be praying)
        return {1:'adhan', 0:'resume'}.get(r,'stay')

    def _dispatch(self, key, pre=False):
        title=name_of(key); mode={'0':'full','1':'notify','2':'configurable'}.get(self._s('alert_mode','2'),'configurable')
        playing=self.xbmc.Player().isPlayingVideo()
        path=self._adhan_path(key)
        can_play=mode in ('full','configurable') and bool(path)
        try: action=int(self._s('video_adhan_action','3') or 3)
        except ValueError: action=self.ASK
        if playing and action in (self.ADHAN_RESUME, self.ASK) and not can_play:
            action=self.PAUSE_ONLY  # nothing to play -> just pause
        asking=playing and not pre and action==self.ASK
        message=('باقي %s دقيقة على صلاة %s' % (self._s('reminder_minutes','0'),title)) if pre else ('حان الآن وقت '+title)
        # The ask dialog replaces the notification + popup (no clutter over the film).
        if not asking:
            if self._s('notify_on_screen','true') == 'true' or not playing:
                self.xbmcgui.Dialog().notification('مواقيت نجد للصلاة', message, self.xbmcgui.NOTIFICATION_INFO, 7000)
            if self._s('popup_alert','true') == 'true' and self.addon_path and (not playing or self._s('notify_on_screen','true') == 'true'):
                try:
                    from resources.lib.gui.alert import show_alert
                    lead=('تذكير — بعد %s دقيقة' % self._s('reminder_minutes','0')) if pre else 'حان الآن وقت صلاة'
                    secs=int(self._s('popup_seconds','20') or 20)
                    show_alert(self.addon_path, lead, title, self._adhan_time_str(key), self._city_name(), secs,
                               'jumuah' if title == 'الجمعة' else key)
                except Exception as exc:
                    self.xbmc.log('[NajdPrayer] popup error: %s' % exc,self.xbmc.LOGERROR)
        if pre: return
        if not playing:
            if can_play: self._play_adhan(path)
            return
        if action==self.NOTIFY_ONLY:
            return
        self._pause_video()
        if action==self.PAUSE_ONLY:
            return
        if action==self.ASK:
            choice=self._ask_at_adhan(title)
            if choice=='resume': self._unpause_video(); return
            if choice=='stay': return
        self._play_adhan_then_resume(path)
