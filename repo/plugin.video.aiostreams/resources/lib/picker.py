# -*- coding: utf-8 -*-
"""Full-screen stream picker (fanart, poster, plot, colour-coded FEL/MEL list).
Ported from FEL Cinema; falls back to Kodi's select dialog on any error."""
import xbmc
import xbmcgui

from . import kodi, streams as st

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_STOP = 13
LIST_ID = 30002


def header_from_listitem(title=''):
    """Art/plot of the item that launched playback (our lists, TMDbHelper, widgets)."""
    def info(label):
        return xbmc.getInfoLabel(label) or ''
    return {
        'title': title or info('ListItem.Title') or info('ListItem.Label'),
        'poster': info('ListItem.Art(poster)') or info('ListItem.Art(tvshow.poster)') or info('ListItem.Art(thumb)'),
        'fanart': info('ListItem.Art(fanart)'),
        'plot': info('ListItem.Plot'),
        'year': info('ListItem.Year'),
        'rating': info('ListItem.Rating'),
        'genre': info('ListItem.Genre'),
        'duration': info('ListItem.Duration'),
    }


class StreamPicker(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super(StreamPicker, self).__init__(*args)
        self.header = kwargs.get('header') or {}
        self.streams = kwargs.get('streams') or []
        self.selected = None

    def onInit(self):
        h = self.header
        for key in ('fanart', 'poster', 'title', 'plot'):
            self.setProperty(key, h.get(key) or '')
        rating = h.get('rating') or ''
        meta = [h.get('year') or '', ('IMDb %s' % rating) if rating and rating not in ('0', '0.0') else '',
                h.get('duration') or '', h.get('genre') or '']
        self.setProperty('subtitle', '  •  '.join(x for x in meta if x))

        infos = [st.classify(s) for s in self.streams]
        fel = sum(1 for c in infos if c['dv_type'] == 'FEL')
        mel = sum(1 for c in infos if c['dv_type'] == 'MEL')
        ch71 = sum(1 for c in infos if c['channels'] == '7.1')
        self.setProperty('counts', '[B]%s[/B]   [COLOR %s]● %d FEL[/COLOR]   [COLOR %s]● %d MEL[/COLOR]   [COLOR %s]● %d 7.1[/COLOR]' % (
            kodi.s(30043) % len(self.streams), st.COLOR_FEL, fel, st.COLOR_MEL, mel, st.COLOR_71, ch71))

        ctrl = self.getControl(LIST_ID)
        ctrl.reset()
        lis = []
        for idx, (stream, c) in enumerate(zip(self.streams, infos)):
            col = c['color']
            flags = '  |  '.join(x for x in (c['badge'], c['quality'], c['group'], c['visual'], c['audio']) if x)
            if not stream.get('streamData'):
                # no parsed data: show the formatter's own name line
                flags = st.clean(stream.get('name') or '').replace('\n', ' ') or flags
            li = xbmcgui.ListItem(c['filename'], offscreen=True)
            li.setProperty('idx', str(idx))
            li.setProperty('accent', col if c['tier'] < 4 else 'FFFFA500')
            li.setProperty('res', '[COLOR %s][B]%s[/B][/COLOR]' % (col, c['resolution'] or '—'))
            li.setProperty('flags', '[COLOR %s]%s[/COLOR]' % (col, flags))
            li.setProperty('filename', '[COLOR %s]%s[/COLOR]' % (col, c['filename']))
            li.setProperty('size', '[COLOR %s][B]%s[/B][/COLOR]' % (col, c['size_label'] or ''))
            debrid = c['debrid']
            li.setProperty('debrid', '[COLOR FF4ADE80][B]%s[/B][/COLOR]' % debrid if c['cached'] else debrid)
            li.setProperty('addon', c['addon'])
            lis.append(li)
        ctrl.addItems(lis)
        self.setFocusId(LIST_ID)

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_STOP):
            self.selected = None
            self.close()

    def onClick(self, control_id):
        if control_id == LIST_ID:
            item = self.getControl(LIST_ID).getSelectedItem()
            if item is not None:
                try:
                    self.selected = int(item.getProperty('idx'))
                except ValueError:
                    self.selected = None
            self.close()


def pick(playable, header):
    """Return the chosen index, None when cancelled, or raise to request the
    plain select dialog."""
    dlg = StreamPicker('AIOStreamsPicker.xml', kodi.ADDON_PATH, 'Default', '1080i',
                       header=header, streams=playable)
    dlg.doModal()
    idx = dlg.selected
    del dlg
    return idx
