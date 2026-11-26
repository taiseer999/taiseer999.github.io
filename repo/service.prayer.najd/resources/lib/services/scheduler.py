# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from resources.lib.core.prayer_engine import calculate, NAMES, as_datetime
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
            win.setProperty('NajdPrayer.Next','%s %s'%(NAMES[key],dt.strftime('%H:%M')))
            win.setProperty('NajdPrayer.NextName',NAMES[key])
            win.setProperty('NajdPrayer.NextTime',dt.strftime('%H:%M'))
            win.setProperty('NajdPrayer.Remaining','%02d:%02d'%(mins//60,mins%60))

    def _adhan_time_str(self, key):
        try:
            return self._times(datetime.now().date()).get(key) or ''
        except Exception:
            return ''
    def _dispatch(self, key, pre=False):
        title=NAMES[key]; mode={'0':'full','1':'notify','2':'configurable'}.get(self._s('alert_mode','2'),'configurable')
        playing=self.xbmc.Player().isPlayingVideo()
        message=('باقي %s دقيقة على صلاة %s' % (self._s('reminder_minutes','0'),title)) if pre else ('حان الآن وقت '+title)
        # On-screen notification (bottom of the screen, also over video) unless disabled.
        if self._s('notify_on_screen','true') == 'true' or not playing:
            self.xbmcgui.Dialog().notification('مواقيت نجد للصلاة', message, self.xbmcgui.NOTIFICATION_INFO, 7000)
        # Rich popup alert window (non-blocking), unless disabled or suppressed over video.
        if self._s('popup_alert','true') == 'true' and self.addon_path and (not playing or self._s('notify_on_screen','true') == 'true'):
            try:
                from resources.lib.gui.alert import show_alert
                lead=('تذكير — بعد %s دقيقة' % self._s('reminder_minutes','0')) if pre else 'حان الآن وقت صلاة'
                secs=int(self._s('popup_seconds','20') or 20)
                show_alert(self.addon_path, lead, title, self._adhan_time_str(key), self._city_name(), secs)
            except Exception as exc:
                self.xbmc.log('[NajdPrayer] popup error: %s' % exc,self.xbmc.LOGERROR)
        if pre: return
        # Optionally pause the running video at adhan time so the user doesn't miss it.
        if playing and self._s('pause_video_at_adhan','false') == 'true':
            try:
                if not self.xbmc.getCondVisibility('Player.Paused'):
                    self.xbmc.Player().pause()
            except Exception as exc:
                self.xbmc.log('[NajdPrayer] pause error: %s' % exc,self.xbmc.LOGERROR)
        # Respect video playback unless user explicitly selected full adhan during video.
        allow_video=self._s('adhan_during_video','false') == 'true'
        path=self._s('adhan_'+key,'') or self._s('adhan_file','')
        if mode in ('full','configurable') and path and (not playing or allow_video):
            try: self.xbmc.Player().play(path)
            except Exception as exc: self.xbmc.log('[NajdPrayer] audio error: %s' % exc,self.xbmc.LOGERROR)
