# -*- coding: utf-8 -*-
"""Generate the Lucent window XMLs for Fen Light, Red Light, POV and Umbrella.

Dev tool (not used at runtime). Output: resources/lucent/xml/<profile>/<file>.xml

Look and textures: "Lucent" theme for Seren by djdirty60
(https://github.com/djdirty60/Seren-Thema). Every window here reads the shared
lucent.* properties written by resources/lucent/lucent_theme.py, plus the
add-on's own control ids / properties that its Python code depends on.

Run:  python3 tools/gen_lucent.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'resources', 'lucent', 'xml')
BADGES_SHOWN = 7

BG = '0B1119'


def esc(text):
    return text.replace('&', '&amp;')


# ───────────────────────── shared building blocks ─────────────────────────

def backdrop(fanart):
    return '''
        <!-- ============ Cinematic backdrop ============ -->
        <control type="group">
            <control type="image">
                <texture>lucent/white.png</texture>
                <colordiffuse>FF%(bg)s</colordiffuse>
            </control>
            <control type="image">
                <animation effect="fade" start="0" end="100" time="500">WindowOpen</animation>
                <aspectratio>scale</aspectratio>
                <texture background="true">%(fanart)s</texture>
            </control>
            <control type="image">
                <width>1500</width>
                <texture>lucent/grad_left.png</texture>
                <colordiffuse>F5%(bg)s</colordiffuse>
            </control>
            <control type="image">
                <top>440</top>
                <height>640</height>
                <texture>lucent/grad_bottom.png</texture>
                <colordiffuse>FF%(bg)s</colordiffuse>
            </control>
            <control type="image">
                <height>260</height>
                <texture>lucent/grad_top.png</texture>
                <colordiffuse>99%(bg)s</colordiffuse>
            </control>
            <control type="image">
                <texture>lucent/vignette.png</texture>
                <colordiffuse>99000000</colordiffuse>
            </control>
        </control>
''' % {'bg': BG, 'fanart': fanart}


def pill(label, visible, edge=False, bright=False):
    tex = 'lucent/pill44_edge.png' if edge else 'lucent/pill44.png'
    diffuse = '2EFFFFFF' if bright else '1AFFFFFF'
    color = 'FFFFFFFF' if bright else 'FFDCE2E7'
    return '''
                <control type="button">
                    <width>auto</width>
                    <height>44</height>
                    <font>font12</font>
                    <textoffsetx>20</textoffsetx>
                    <aligny>center</aligny>
                    <textcolor>%(c)s</textcolor>
                    <disabledcolor>%(c)s</disabledcolor>
                    <texturenofocus border="22" colordiffuse="%(d)s">%(t)s</texturenofocus>
                    <texturefocus border="22" colordiffuse="%(d)s">%(t)s</texturefocus>
                    <enable>false</enable>
                    <label>%(l)s</label>
                    <visible>%(v)s</visible>
                </control>''' % {'c': color, 'd': diffuse, 't': tex, 'l': label, 'v': visible}


def title_block(fade_cond=None, extra_anim=''):
    """Logo / title, meta pills and episode title (top of the left column)."""
    W = 'Window.Property(lucent.%s)'
    hide = ''
    if fade_cond:
        hide = '\n            <animation effect="fade" end="0" time="200" condition="%s">Conditional</animation>' % fade_cond
    return '''
        <!-- ============ Left column: logo / title / meta ============ -->
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="100">WindowOpen</animation>
            <animation effect="slide" start="-60,0" end="0,0" time="350" delay="100" tween="cubic" easing="out">WindowOpen</animation>
            <animation effect="fade" end="0" time="250">WindowClose</animation>%(extra)s
            <left>96</left>
            <top>96</top>
            <width>720</width>
            <control type="image">
                <width>560</width>
                <height>220</height>
                <aspectratio align="left" aligny="bottom">keep</aspectratio>
                <texture>$INFO[%(logo)s]</texture>
                <visible>!String.IsEmpty(%(logo)s)</visible>
            </control>
            <control type="textbox">
                <top>60</top>
                <width>720</width>
                <height>160</height>
                <font>font37</font>
                <textcolor>FFFFFFFF</textcolor>
                <aligny>bottom</aligny>
                <label>[B]$INFO[%(show)s][/B]</label>
                <visible>String.IsEmpty(%(logo)s)</visible>
            </control>
            <control type="grouplist">
                <top>252</top>
                <height>44</height>
                <width>720</width>
                <orientation>horizontal</orientation>
                <itemgap>12</itemgap>
                <usecontrolcoords>true</usecontrolcoords>%(pills)s
            </control>
            <control type="label">
                <top>320</top>
                <width>720</width>
                <height>44</height>
                <font>font27</font>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]$INFO[%(ept)s][/B]</label>
                <visible>!String.IsEmpty(%(ept)s)</visible>
            </control>
        </control>
''' % {
        'extra': hide + extra_anim,
        'logo': W % 'clearlogo', 'show': W % 'show_title', 'ept': W % 'ep_title',
        'pills': ''.join([
            pill('[B]$INFO[%s][/B]' % (W % 'ep_code'), '!String.IsEmpty(%s)' % (W % 'ep_code'), bright=True),
            pill('$INFO[%s]' % (W % 'year'), '!String.IsEmpty(%s)' % (W % 'year')),
            pill('★ $INFO[%s]' % (W % 'rating'), '!String.IsEmpty(%s)' % (W % 'rating')),
            pill('$INFO[%s]' % (W % 'mpaa'), '!String.IsEmpty(%s)' % (W % 'mpaa'), edge=True),
            pill('$INFO[%s]' % (W % 'genre'), '!String.IsEmpty(%s) + String.IsEmpty(%s)' % (W % 'genre', W % 'ep_code')),
        ])}


def plot_block(label, top=476, height=330, fade_cond=None, visible=None):
    hide = ''
    if fade_cond:
        hide = '\n            <animation effect="fade" end="0" time="200" condition="%s">Conditional</animation>' % fade_cond
    vis = '\n            <visible>%s</visible>' % visible if visible else ''
    return '''
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="150">WindowOpen</animation>
            <animation effect="fade" end="0" time="250">WindowClose</animation>%(hide)s%(vis)s
            <left>96</left>
            <top>%(top)d</top>
            <control type="textbox">
                <width>700</width>
                <height>%(h)d</height>
                <font>font12</font>
                <textcolor>FFBDC8D1</textcolor>
                <label>%(l)s</label>
                <autoscroll delay="6000" time="2500" repeat="8000">true</autoscroll>
            </control>
        </control>
''' % {'hide': hide, 'vis': vis, 'top': top, 'h': height, 'l': label}


def glass(left, top, width, height):
    """Shadow + glass body + hairline edge, sized to the enclosing group."""
    return '''
            <control type="image">
                <left>-40</left>
                <top>-40</top>
                <width>%(w)d</width>
                <height>%(h)d</height>
                <texture border="88">lucent/panel_shadow.png</texture>
                <colordiffuse>99000000</colordiffuse>
            </control>
            <control type="image">
                <width>%(iw)d</width>
                <height>%(ih)d</height>
                <texture border="48">lucent/panel.png</texture>
                <colordiffuse>E0162532</colordiffuse>
            </control>
            <control type="image">
                <width>%(iw)d</width>
                <height>%(ih)d</height>
                <texture border="48">lucent/panel_edge.png</texture>
                <colordiffuse>2EFFFFFF</colordiffuse>
            </control>''' % {'w': width + 80, 'h': height + 80, 'iw': width, 'ih': height}


def action_button(cid, label, visible=None, nav=''):
    vis = '\n                    <visible>%s</visible>' % visible if visible else ''
    return '''
                <control type="button" id="%(id)s">
                    <width>auto</width>
                    <height>64</height>
                    <font>font12</font>
                    <textoffsetx>30</textoffsetx>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FF%(bg)s</focusedcolor>
                    <texturefocus border="32" colordiffuse="FFFFFFFF">lucent/pill64.png</texturefocus>
                    <texturenofocus border="32" colordiffuse="24FFFFFF">lucent/pill64.png</texturenofocus>
                    <pulseonselect>false</pulseonselect>
                    <label>[B]%(l)s[/B]</label>%(nav)s%(vis)s
                </control>''' % {'id': cid, 'bg': BG, 'l': label, 'vis': vis, 'nav': nav}


def segmented_bar(prop, width=760, segments=40, top=0, left=0, visible=None):
    seg = width // segments
    vis = '\n                <visible>%s</visible>' % visible if visible else ''
    out = [('''
            <control type="group">
                <left>%d</left>
                <top>%d</top>
                <width>%d</width>
                <height>6</height>''' + vis + '''
                <control type="image">
                    <width>%d</width>
                    <height>6</height>
                    <texture border="3">lucent/pill6.png</texture>
                    <colordiffuse>1FFFFFFF</colordiffuse>
                </control>''') % (left, top, width, seg * segments)]
    for n in range(segments):
        threshold = max(1, int(round((n + 1) * 100.0 / segments)) - 1)
        out.append('''
                <control type="image">
                    <left>%d</left>
                    <width>%d</width>
                    <height>6</height>
                    <texture>lucent/white.png</texture>
                    <colordiffuse>FFFFFFFF</colordiffuse>
                    <visible>Integer.IsGreaterOrEqual(%s,%d)</visible>
                </control>''' % (n * seg, seg, prop, threshold))
    out.append('\n            </control>')
    return ''.join(out)


def native_progress(cid, top, left=40, width=760):
    return '''
            <control type="progress" id="%(id)s">
                <left>%(l)d</left>
                <top>%(t)d</top>
                <width>%(w)d</width>
                <height>6</height>
                <reveal>true</reveal>
                <texturebg border="3" colordiffuse="1FFFFFFF">lucent/pill6.png</texturebg>
                <lefttexture />
                <midtexture border="3" colordiffuse="FFFFFFFF">lucent/pill6.png</midtexture>
                <righttexture />
                <overlaytexture />
            </control>''' % {'id': cid, 't': top, 'l': left, 'w': width}


def spinner(visible, left, top):
    return '''
            <control type="image">
                <left>%d</left>
                <top>%d</top>
                <width>16</width>
                <height>16</height>
                <texture>lucent/dot.png</texture>
                <colordiffuse>FFFFFFFF</colordiffuse>
                <animation effect="fade" start="100" end="25" time="600" pulse="true" condition="true">Conditional</animation>
                <visible>%s</visible>
            </control>''' % (left, top, visible)


# ───────────────────────── stream cards ─────────────────────────

def badge_row(diffuse):
    out = []
    for n in range(1, BADGES_SHOWN + 1):
        out.append('''
                            <control type="image">
                                <left>%d</left>
                                <width>88</width>
                                <height>34</height>
                                <aspectratio>keep</aspectratio>
                                <texture>lucent/flags/$INFO[ListItem.Property(lucent.badge_%d)].png</texture>
                                <colordiffuse>%s</colordiffuse>
                                <visible>!String.IsEmpty(ListItem.Property(lucent.badge_%d))</visible>
                            </control>''' % ((n - 1) * 96, n, diffuse, n))
    return ''.join(out)


def card(state, profile):
    """state: 'idle' (itemlayout), 'dim' (focused item, list not focused), 'active'."""
    full = profile['full_prop']
    active = state == 'active'
    if state == 'idle':
        body = '''
                        <control type="image">
                            <texture border="32">lucent/card.png</texture>
                            <colordiffuse>0FFFFFFF</colordiffuse>
                        </control>'''
    elif state == 'dim':
        body = '''
                        <control type="image">
                            <texture border="32">lucent/card.png</texture>
                            <colordiffuse>24FFFFFF</colordiffuse>
                        </control>
                        <control type="image">
                            <texture border="32">lucent/card_edge.png</texture>
                            <colordiffuse>40FFFFFF</colordiffuse>
                        </control>'''
    else:
        body = '''
                        <control type="image">
                            <left>-24</left>
                            <top>-24</top>
                            <width>952</width>
                            <height>172</height>
                            <texture border="56">lucent/card_glow.png</texture>
                            <colordiffuse>66D6F0FF</colordiffuse>
                        </control>
                        <control type="image">
                            <texture border="32">lucent/card.png</texture>
                            <colordiffuse>FF2C3E4C</colordiffuse>
                        </control>
                        <control type="image">
                            <texture border="32">lucent/card_edge.png</texture>
                            <colordiffuse>F2FFFFFF</colordiffuse>
                        </control>'''
    zoom = ('\n                    <animation effect="zoom" start="98" end="100" center="auto" time="180" '
            'tween="cubic" easing="out">Focus</animation>') if active else ''
    pill_diffuse = 'FFFFFFFF' if active else '1AFFFFFF'
    pill_text = 'FF%s' % BG if active else 'FFDCE2E7'
    title_color = 'FFFFFFFF' if active else 'CCFFFFFF'
    meta_color = 'FFDCE2E7' if active else 'FF8F9BA6'
    badge_diffuse = 'E6FFFFFF' if active else '99FFFFFF'
    title_label = '[B]$INFO[ListItem.Property(lucent.title)][/B]' if active else '$INFO[ListItem.Property(lucent.title)]'
    scroll = ''
    full_label = profile['full_label']
    return '''
                <control type="group">
                    <left>16</left>
                    <top>12</top>
                    <width>904</width>
                    <height>124</height>%(zoom)s%(body)s
                    <!-- Stream -->
                    <control type="group">
                        <visible>String.IsEmpty(ListItem.Property(%(full)s))</visible>
                        <control type="image">
                            <left>20</left>
                            <top>20</top>
                            <width>124</width>
                            <height>42</height>
                            <texture border="21">lucent/pill42.png</texture>
                            <colordiffuse>%(pd)s</colordiffuse>
                            <visible>String.IsEmpty(ListItem.Property(lucent.lowq)) + String.IsEmpty(ListItem.Property(lucent.res))</visible>
                        </control>
                        <control type="image">
                            <left>20</left>
                            <top>20</top>
                            <width>124</width>
                            <height>42</height>
                            <texture border="21">lucent/pill42.png</texture>
                            <colordiffuse>FFD9434B</colordiffuse>
                            <visible>!String.IsEmpty(ListItem.Property(lucent.lowq))</visible>
                        </control>
                        <control type="label">
                            <left>20</left>
                            <top>20</top>
                            <width>124</width>
                            <height>42</height>
                            <font>font12</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>%(pt)s</textcolor>
                            <label>[B]$INFO[ListItem.Property(lucent.quality)][/B]</label>
                            <visible>String.IsEmpty(ListItem.Property(lucent.lowq)) + String.IsEmpty(ListItem.Property(lucent.res))</visible>
                        </control>
                        <!-- Resolution flag (Arctic Fuse 3 colour flags) -->
                        <control type="image">
                            <left>20</left>
                            <top>14</top>
                            <width>124</width>
                            <height>46</height>
                            <aspectratio>keep</aspectratio>
                            <texture>lucent/res/$INFO[ListItem.Property(lucent.res)].png</texture>
                            <colordiffuse>%(resd)s</colordiffuse>
                            <visible>!String.IsEmpty(ListItem.Property(lucent.res))</visible>
                        </control>
                        <control type="label">
                            <left>20</left>
                            <top>20</top>
                            <width>124</width>
                            <height>42</height>
                            <font>font12</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>[B]$INFO[ListItem.Property(lucent.quality)][/B]</label>
                            <visible>!String.IsEmpty(ListItem.Property(lucent.lowq))</visible>
                        </control>
                        <!-- Debrid / service icon (AB Wizard account manager artwork) -->
                        <control type="image">
                            <left>58</left>
                            <top>66</top>
                            <width>48</width>
                            <height>48</height>
                            <aspectratio>keep</aspectratio>
                            <texture>$INFO[ListItem.Property(lucent.icon)]</texture>
                            <colordiffuse>%(icon)s</colordiffuse>
                            <visible>!String.IsEmpty(ListItem.Property(lucent.icon))</visible>
                        </control>
                        <control type="label">
                            <left>168</left>
                            <top>12</top>
                            <width>712</width>
                            <height>40</height>
                            <font>font12</font>
                            <textcolor>%(tc)s</textcolor>%(scroll)s
                            <label>%(tl)s</label>
                        </control>
                        <control type="label">
                            <left>168</left>
                            <top>46</top>
                            <width>712</width>
                            <height>34</height>
                            <font>font12</font>
                            <textcolor>%(mc)s</textcolor>
                            <label>[UPPERCASE]$INFO[ListItem.Property(lucent.meta)][/UPPERCASE]</label>
                        </control>
                        <control type="group">
                            <left>168</left>
                            <top>84</top>
                            <width>712</width>
                            <height>34</height>%(badges)s
                        </control>
                    </control>
                    <!-- Full search -->
                    <control type="label">
                        <left>40</left>
                        <width>824</width>
                        <height>124</height>
                        <font>font12</font>
                        <align>center</align>
                        <aligny>center</aligny>
                        <textcolor>%(tc)s</textcolor>
                        <label>[B][UPPERCASE]%(fl)s[/UPPERCASE][/B]</label>
                        <visible>!String.IsEmpty(ListItem.Property(%(full)s))</visible>
                    </control>
                </control>''' % {
        'zoom': zoom, 'body': body, 'full': full, 'pd': pill_diffuse, 'pt': pill_text,
        'icon': 'FFFFFFFF' if active else 'D9FFFFFF', 'resd': 'FFFFFFFF' if active else 'D9FFFFFF', 'tc': title_color, 'mc': meta_color,
        'scroll': scroll, 'tl': title_label, 'badges': badge_row(badge_diffuse), 'fl': full_label}


def stream_list(lid, visible, profile, scroll_id):
    vis = '\n                <visible>%s</visible>' % visible if visible else ''
    nav = profile['list_nav']
    return '''
            <!-- Stream list %(id)s -->
            <control type="scrollbar" id="%(sid)s">
                <left>962</left>
                <top>124</top>
                <width>6</width>
                <height>800</height>
                <onleft>%(id)s</onleft>
                <showonepage>false</showonepage>
                <orientation>vertical</orientation>
                <texturesliderbackground colordiffuse="14FFFFFF" border="3">lucent/pill6.png</texturesliderbackground>
                <texturesliderbar colordiffuse="4DFFFFFF" border="3">lucent/pill6.png</texturesliderbar>
                <texturesliderbarfocus colordiffuse="FFFFFFFF" border="3">lucent/pill6.png</texturesliderbarfocus>%(vis)s
            </control>
            <control type="label">
                <right>40</right>
                <top>30</top>
                <width>300</width>
                <height>50</height>
                <font>font12</font>
                <align>right</align>
                <textcolor>FFBDC8D1</textcolor>
                <label>$INFO[Container(%(id)s).CurrentItem]$INFO[Container(%(id)s).NumItems, / ,]</label>%(vis)s
            </control>
            <control type="list" id="%(id)s">
                <left>24</left>
                <top>116</top>
                <width>936</width>
                <height>836</height>
                <orientation>vertical</orientation>
                <pagecontrol>%(sid)s</pagecontrol>
                <scrolltime tween="cubic" easing="out">250</scrolltime>
                <focusposition>1</focusposition>
                <movement>3</movement>%(nav)s
                <onright>%(right)s</onright>%(vis)s
                <itemlayout height="148" width="936">%(idle)s
                </itemlayout>
                <focusedlayout height="148" width="936" condition="!Control.HasFocus(%(id)s)">%(dim)s
                </focusedlayout>
                <focusedlayout height="148" width="936" condition="Control.HasFocus(%(id)s)">%(active)s
                </focusedlayout>
            </control>
''' % {'id': lid, 'sid': scroll_id, 'vis': vis, 'nav': nav, 'right': profile.get('onright', lid),
           'idle': card('idle', profile), 'dim': card('dim', profile), 'active': card('active', profile)}


def results_window(profile):
    lists = ''.join(stream_list(lid, vis, profile, sid) for lid, vis, sid in profile['lists'])
    left_extra = profile.get('left_extra', '')
    fade_cond = profile.get('plot_fade_cond')
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!-- LUCENT for %(name)s - source results. Generated by AB Tools (tools/gen_lucent.py). -->
<!-- Look and textures: Lucent theme for Seren by djdirty60 (github.com/djdirty60/Seren-Thema). -->
<window type="dialog">
    <coordinates>
        <left>0</left>
        <top>0</top>
        <width>1920</width>
        <height>1080</height>
    </coordinates>
    <defaultcontrol always="true">%(default)s</defaultcontrol>
    <controls>%(bg)s%(title)s%(plot)s%(left_extra)s
        <!-- ============ Right: glass stream panel ============ -->
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="150">WindowOpen</animation>
            <animation effect="slide" start="120,0" end="0,0" time="400" delay="150" tween="cubic" easing="out">WindowOpen</animation>
            <animation effect="slide" end="200,0" time="300" tween="cubic" easing="in">WindowClose</animation>
            <animation effect="fade" end="0" time="300">WindowClose</animation>
            <left>880</left>
            <top>56</top>
            <width>984</width>
            <height>968</height>%(glass)s
            <control type="label">
                <left>40</left>
                <top>30</top>
                <width>600</width>
                <height>50</height>
                <font>font27</font>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]Streams[/B]</label>
            </control>
            <control type="label">
                <left>40</left>
                <top>72</top>
                <width>900</width>
                <height>26</height>
                <font>font12</font>
                <textcolor>FF8F9BA6</textcolor>
                <label>%(subhead)s</label>
            </control>
            <control type="image">
                <left>40</left>
                <top>106</top>
                <width>904</width>
                <height>1</height>
                <texture>lucent/white.png</texture>
                <colordiffuse>1AFFFFFF</colordiffuse>
            </control>%(lists)s
        </control>%(hidden)s
    </controls>
</window>
''' % {'name': profile['name'], 'default': profile['lists'][0][0],
           'bg': backdrop('$INFO[Window.Property(lucent.fanart)]'),
           'title': title_block(),
           'plot': plot_block('$INFO[Window.Property(lucent.plot)]', fade_cond=fade_cond),
           'left_extra': left_extra, 'glass': glass(0, 0, 984, 968),
           'subhead': profile['subhead'], 'lists': lists, 'hidden': profile.get('hidden', '')}


# ───────────────────────── progress windows ─────────────────────────

def progress_card(inner, height=344, visible=None):
    vis = '\n            <visible>%s</visible>' % visible if visible else ''
    return '''
        <!-- ============ Glass progress card ============ -->
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="100">WindowOpen</animation>
            <animation effect="slide" start="0,60" end="0,0" time="400" delay="100" tween="cubic" easing="out">WindowOpen</animation>
            <animation effect="fade" end="0" time="250">WindowClose</animation>%(vis)s
            <left>96</left>
            <top>%(top)d</top>
            <width>840</width>
            <height>%(h)d</height>%(glass)s%(inner)s
        </control>
''' % {'vis': vis, 'top': 1080 - 96 - height, 'h': height, 'glass': glass(0, 0, 840, height), 'inner': inner}


def header(label, visible=None, right=None):
    vis = '\n                <visible>%s</visible>' % visible if visible else ''
    out = '''
            <control type="label">
                <left>40</left>
                <top>28</top>
                <width>600</width>
                <height>44</height>
                <font>font27</font>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]%s[/B]</label>%s
            </control>''' % (label, vis)
    if right:
        out += '''
            <control type="label">
                <right>40</right>
                <top>28</top>
                <width>200</width>
                <height>44</height>
                <font>font27</font>
                <align>right</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]%s[/B]</label>%s
            </control>''' % (right, vis)
    return out


def counts_row(values, top, visible=None):
    vis = '\n                <visible>%s</visible>' % visible if visible else ''
    cells = []
    for n, (label, value) in enumerate(values):
        cells.append('''
                <control type="group">
                    <left>%d</left>
                    <width>176</width>
                    <height>84</height>
                    <control type="image">
                        <width>176</width>
                        <height>84</height>
                        <texture border="32">lucent/card.png</texture>
                        <colordiffuse>14FFFFFF</colordiffuse>
                    </control>
                    <control type="label">
                        <top>8</top>
                        <width>176</width>
                        <height>40</height>
                        <font>font27</font>
                        <align>center</align>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>[B]$INFO[%s][/B]</label>
                    </control>
                    <control type="label">
                        <top>46</top>
                        <width>176</width>
                        <height>30</height>
                        <font>font12</font>
                        <align>center</align>
                        <textcolor>FF8F9BA6</textcolor>
                        <label>%s</label>
                    </control>
                </control>''' % (n * 190, value, label))
    return '''
            <control type="group">
                <left>40</left>
                <top>%d</top>%s%s
            </control>''' % (top, vis, ''.join(cells))


def textbox(cid, top, height, label='', visible=None, color='FF8F9BA6'):
    vis = '\n                <visible>%s</visible>' % visible if visible else ''
    idattr = ' id="%s"' % cid if cid else ''
    lab = '\n                <label>%s</label>' % label if label else ''
    return '''
            <control type="textbox"%s>
                <left>40</left>
                <top>%d</top>
                <width>760</width>
                <height>%d</height>
                <font>font12</font>
                <textcolor>%s</textcolor>%s%s
            </control>''' % (idattr, top, height, color, lab, vis)


def button_row(buttons, top, visible=None, gid=None):
    vis = '\n                <visible>%s</visible>' % visible if visible else ''
    idattr = ' id="%s"' % gid if gid else ''
    return '''
            <control type="grouplist"%s>
                <left>40</left>
                <top>%d</top>
                <width>760</width>
                <height>64</height>
                <orientation>horizontal</orientation>
                <itemgap>16</itemgap>%s%s
            </control>''' % (idattr, top, vis, ''.join(buttons))


def window_shell(name, what, body, default=None):
    dc = '\n    <defaultcontrol always="true">%s</defaultcontrol>' % default if default else ''
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!-- LUCENT for %s - %s. Generated by AB Tools (tools/gen_lucent.py). -->
<!-- Look and textures: Lucent theme for Seren by djdirty60 (github.com/djdirty60/Seren-Thema). -->
<window type="dialog">
    <coordinates>
        <left>0</left>
        <top>0</top>
        <width>1920</width>
        <height>1080</height>
    </coordinates>%s
    <controls>%s
    </controls>
</window>
''' % (name, what, dc, body)


def fen_playback(name, counts, percent_expr, resume_percent_expr, resume_buttons):
    """Fen Light / Red Light sources_playback.xml (scraper, resolver and resume modes)."""
    mode = 'String.IsEqual(Window.Property(window_mode),%s)'
    scraper, resolver, resume = mode % 'scraper', mode % 'resolver', mode % 'resume'
    busy = 'String.IsEqual(Window.Property(enable_busy_spinner),true)'
    inner = ''.join([
        header('Searching for streams', scraper, right='$INFO[%s]' % counts[-1][1]),
        header('Opening stream', resolver),
        header('Resume playback?', resume),
        spinner(busy, 620, 42),
        segmented_bar(percent_expr, top=96, left=40, visible='!' + resume if resume_percent_expr != percent_expr else None),
        counts_row(counts[:-1], 128, scraper),
        textbox('2001', 232, 84, visible=scraper),
        textbox('2002', 128, 188, visible=resolver, color='FFDCE2E7'),
        segmented_bar(resume_percent_expr, top=96, left=40, visible=resume) if resume_percent_expr != percent_expr else '',
        resume_buttons,
    ])
    body = ''.join([
        backdrop('$INFO[Window.Property(lucent.fanart)]'),
        title_block(),
        plot_block('$INFO[Window.Property(lucent.plot)]', top=476, height=130, visible='!' + resolver),
        plot_block('$INFO[Window.Property(text)]', top=476, height=130, visible=resolver),
        progress_card(inner),
    ])
    return window_shell(name, 'scraping / resolving', body)


# ───────────────────────── profiles ─────────────────────────

def fen_results_profile(name):
    fmt = 'String.IsEqual(Window.Property(window_format),%s)'
    filter_list = '''
        <!-- ============ Filters (left of the stream list) ============ -->
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="150">WindowOpen</animation>
            <animation effect="fade" end="0" time="250">WindowClose</animation>
            <left>96</left>
            <top>476</top>
            <control type="group">
                <animation effect="fade" end="0" time="200" condition="!Control.HasFocus(2100)">Conditional</animation>
                <control type="label">
                    <width>700</width>
                    <height>40</height>
                    <font>font27</font>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>[B]Filter[/B]</label>
                </control>
            </control>
            <control type="fixedlist" id="2100">
                <animation effect="fade" end="0" time="200" condition="!Control.HasFocus(2100)">Conditional</animation>
                <top>52</top>
                <width>700</width>
                <height>380</height>
                <onup>2100</onup>
                <ondown>2100</ondown>
                <orientation>vertical</orientation>
                <focusposition>2</focusposition>
                <movement>2</movement>
                <scrolltime tween="cubic" easing="out">200</scrolltime>
                <itemlayout height="76" width="700">
                    <control type="label">
                        <left>28</left>
                        <width>640</width>
                        <height>64</height>
                        <font>font12</font>
                        <aligny>center</aligny>
                        <textcolor>FFDCE2E7</textcolor>
                        <label>$INFO[ListItem.Property(label)]</label>
                    </control>
                </itemlayout>
                <focusedlayout height="76" width="700">
                    <control type="image">
                        <width>700</width>
                        <height>64</height>
                        <texture border="32">lucent/pill64.png</texture>
                        <colordiffuse>FFFFFFFF</colordiffuse>
                    </control>
                    <control type="label">
                        <left>28</left>
                        <width>640</width>
                        <height>64</height>
                        <font>font12</font>
                        <aligny>center</aligny>
                        <textcolor>FF%(bg)s</textcolor>
                        <label>[B]$INFO[ListItem.Property(label)][/B]</label>
                    </control>
                </focusedlayout>
            </control>
            <control type="label">
                <top>424</top>
                <width>700</width>
                <height>40</height>
                <font>font12</font>
                <textcolor>FF8F9BA6</textcolor>
                <label>▶  Press RIGHT to filter</label>
                <visible>!Control.HasFocus(2100) + !String.IsEqual(Window.Property(filter_applied),true)</visible>
            </control>
            <control type="label">
                <top>424</top>
                <width>700</width>
                <height>40</height>
                <font>font12</font>
                <textcolor>FFDCE2E7</textcolor>
                <label>Filter active  ·  press BACK to clear</label>
                <visible>!Control.HasFocus(2100) + String.IsEqual(Window.Property(filter_applied),true)</visible>
            </control>
        </control>
''' % {'bg': BG}
    return {
        'name': name,
        'lists': [('2000', fmt % 'list', '2060'), ('2001', fmt % 'rows', '2063'), ('2002', fmt % 'widelist', '2064')],
        'list_nav': '\n                <onleft>2100</onleft>',
        'full_prop': 'perform_full_search', 'full_label': 'Perform Full Search',
        'subhead': '[UPPERCASE]$INFO[Window.Property(total_results)] Results $INFO[Window.Property(filters_ignored)] $INFO[Window.Property(filter_info)][/UPPERCASE]',
        'left_extra': filter_list, 'plot_fade_cond': 'Control.HasFocus(2100)',
        # set_poster() writes the poster into image 200 - keep the control, unseen.
        'hidden': '''
        <control type="image" id="200">
            <width>1</width>
            <height>1</height>
            <visible>false</visible>
        </control>''',
    }


def pov_results_profile():
    fmt = 'String.StartsWith(Window.Property(tikiskins.window_style),%s)'
    return {
        'name': 'POV',
        'lists': [('2000', fmt % 'list', '2060'), ('2001', fmt % 'infolist', '2061'), ('2002', fmt % 'widelist', '2062')],
        'list_nav': '',
        'full_prop': 'tikiskins.perform_full_search',
        'full_label': '$INFO[ListItem.Property(tikiskins.start_full_scrape)]',
        'subhead': '[UPPERCASE]$INFO[Window.Property(tikiskins.total_results)] Results$INFO[Window.Property(tikiskins.scrape_time),  ·  ,s] $INFO[Window.Property(tikiskins.filters_ignored)][/UPPERCASE]',
        'left_extra': '''
        <control type="label">
            <left>96</left>
            <top>936</top>
            <width>720</width>
            <height>40</height>
            <font>font12</font>
            <textcolor>FF8F9BA6</textcolor>
            <label>RIGHT to filter  ·  MENU for options  ·  INFO for details</label>
        </control>''',
    }


def umbrella_results_profile(list_id, what, buttons=True):
    extra = ''
    nav = ''
    if buttons:
        nav = '\n                <onleft>2090</onleft>'
        extra = '''
        <!-- ============ Action pills ============ -->
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="150">WindowOpen</animation>
            <animation effect="fade" end="0" time="250">WindowClose</animation>
            <left>96</left>
            <top>880</top>%s
        </control>''' % button_row([
            action_button('2051', 'Back', 'String.IsEqual(Window().Property(umbrella.sourcebackbutton),1)'),
            action_button('2001', '$ADDON[plugin.video.umbrella 32639]'),
        ], 0, gid='2090').replace('<left>40</left>', '<left>0</left>', 1).replace(
            '<itemgap>16</itemgap>', '<itemgap>16</itemgap>\n                <onright>%s</onright>\n                <onup>%s</onup>' % (list_id, list_id))
    return {
        'name': 'Umbrella (%s)' % what,
        'lists': [(list_id, None, '5060')],
        'list_nav': nav,
        'full_prop': 'lucent.never_set', 'full_label': '',
        'subhead': '[UPPERCASE]$INFO[Window().Property(umbrella.total_results)] Results$INFO[Window.Property(lucent.filter_info),  ·  Filter: ,  ·  BACK to clear][/UPPERCASE]',
        'left_extra': extra + '''
        <control type="label">
            <left>96</left>
            <top>%d</top>
            <width>720</width>
            <height>40</height>
            <font>font12</font>
            <textcolor>FF8F9BA6</textcolor>
            <label>RIGHT to filter  ·  MENU for options  ·  INFO for details</label>
        </control>''' % (960 if buttons else 936),
    }


LC = 'Window.Property(lucent.%s)'
COUNTS_ON = 'String.IsEqual(Window.Property(lucent.counts),true)'
PARSED_TILES = [('4K', LC % 'c_4k'), ('1080P', LC % 'c_1080p'), ('720P', LC % 'c_720p'), ('SD', LC % 'c_sd')]
SHIFT = '\n                <animation effect="slide" end="0,104" time="0" condition="%s">Conditional</animation>' % COUNTS_ON


def shifted_textbox(cid, top, height, color='FFDCE2E7'):
    return textbox(cid, top, height, color=color).replace('<font>font12</font>', '<font>font12</font>' + SHIFT, 1)


def pov_progress():
    p = 'Window.Property(tikiskins.source_progress.%s)'
    buttons_on = 'String.IsEqual(%s,true)' % (p % 'buttons')
    has_heading = '!String.IsEmpty(%s)' % (LC % 'heading')
    inner = ''.join([
        header('$INFO[%s]' % (LC % 'heading'), has_heading, right='$INFO[%s]' % (LC % 'c_total')),
        header('$INFO[%s]' % (LC % 'show_title'), '!' + has_heading),
        native_progress('5000', 96),
        counts_row(PARSED_TILES, 128, COUNTS_ON),
        shifted_textbox('2000', 128, 104),
        button_row([
            action_button('10', '$INFO[%s]' % (p % 'true_button'), nav='\n                    <onright>11</onright>\n                    <onleft>11</onleft>'),
            action_button('11', '$INFO[%s]' % (p % 'false_button'), nav='\n                    <onright>10</onright>\n                    <onleft>10</onleft>'),
        ], 256, visible=buttons_on),
    ])
    body = ''.join([
        backdrop('$INFO[%s]' % (p % 'fanart')),
        title_block(),
        plot_block('$INFO[Window.Property(lucent.plot)]', top=476, height=110),
        progress_card(inner, height=364),
    ])
    return window_shell('POV', 'progress', body)


def umbrella_progress():
    shown = '!String.IsEqual(Window.Property(umbrella.icononly),true) + !String.IsEqual(Window.Property(umbrella.isHidden),true)'
    icon_only = 'String.IsEqual(Window.Property(umbrella.icononly),true) + !String.IsEqual(Window.Property(umbrella.isHidden),true)'
    inner = ''.join([
        header('$INFO[%s]' % (LC % 'heading'), '!String.IsEmpty(%s)' % (LC % 'heading'),
               right='$INFO[Window().Property(percent)]%'),
        header('Searching for streams', 'String.IsEmpty(%s)' % (LC % 'heading'),
               right='$INFO[Window().Property(percent)]%'),
        segmented_bar('Window().Property(percent)', top=96, left=40),
        counts_row(PARSED_TILES, 128, COUNTS_ON),
        shifted_textbox('2001', 128, 104),
        '''
            <control type="label">
                <left>40</left>
                <top>336</top>
                <width>760</width>
                <height>30</height>
                <font>font12</font>
                <textcolor>FF8F9BA6</textcolor>
                <label>[UPPERCASE]$ADDON[plugin.video.umbrella 40337][/UPPERCASE]</label>
            </control>''',
    ])
    body = '''
        <control type="group">
            <visible>%(shown)s</visible>%(bg)s%(title)s%(plot)s%(card)s
        </control>
        <!-- Icon-only mode: small glass pill top right -->
        <control type="group">
            <visible>%(icon)s</visible>
            <right>48</right>
            <top>36</top>
            <width>220</width>
            <height>56</height>
            <control type="image">
                <texture border="28">lucent/pill60.png</texture>
                <colordiffuse>E0162532</colordiffuse>
            </control>%(spin)s
            <control type="label">
                <left>56</left>
                <width>150</width>
                <height>56</height>
                <font>font12</font>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]$INFO[Window().Property(percent)]%%[/B]</label>
            </control>
        </control>''' % {
        'shown': shown, 'icon': icon_only,
        'bg': backdrop('$INFO[Window.Property(umbrella.fanart)]').replace('\n', '\n    '),
        'title': title_block().replace('\n', '\n    '),
        'plot': plot_block('$INFO[Window.Property(lucent.plot)]', top=476, height=90).replace('\n', '\n    '),
        'card': progress_card(inner, height=384).replace('\n', '\n    '),
        'spin': spinner('true', 24, 20)}
    return window_shell('Umbrella', 'progress', body)


def pov_contextmenu():
    """POV options dialog (long-press / MENU on a stream; also POV's image viewer).
    Contract: list 2020, ListItem.Property(tikiskins.context.label)."""
    label = '$INFO[ListItem.Property(tikiskins.context.label)]'
    body = '''
        <control type="image">
            <texture>lucent/white.png</texture>
            <colordiffuse>B3000000</colordiffuse>
            <animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>
            <animation effect="fade" end="0" time="150">WindowClose</animation>
        </control>
        <control type="group">
            <animation effect="fade" start="0" end="100" time="220">WindowOpen</animation>
            <animation effect="zoom" start="94" end="100" center="auto" time="220" tween="cubic" easing="out">WindowOpen</animation>
            <animation effect="fade" end="0" time="150">WindowClose</animation>
            <centerleft>50%%</centerleft>
            <centertop>50%%</centertop>
            <width>640</width>
            <height max="760">auto</height>
            <control type="image">
                <texture border="48">lucent/panel.png</texture>
                <colordiffuse>F2162532</colordiffuse>
            </control>
            <control type="image">
                <texture border="48">lucent/panel_edge.png</texture>
                <colordiffuse>2EFFFFFF</colordiffuse>
            </control>
            <control type="image">
                <left>32</left>
                <top>28</top>
                <width>48</width>
                <height>48</height>
                <aspectratio>keep</aspectratio>
                <texture>$INFO[Window.Property(tikiskins.pov.icon)]</texture>
            </control>
            <control type="label">
                <left>96</left>
                <top>28</top>
                <width>500</width>
                <height>48</height>
                <font>font27</font>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]Options[/B]</label>
            </control>
            <control type="image">
                <left>32</left>
                <top>100</top>
                <width>576</width>
                <height>1</height>
                <texture>lucent/white.png</texture>
                <colordiffuse>1AFFFFFF</colordiffuse>
            </control>
            <control type="list" id="2020">
                <left>24</left>
                <top>116</top>
                <width>592</width>
                <height max="616">auto</height>
                <onup>2020</onup>
                <ondown>2020</ondown>
                <orientation>vertical</orientation>
                <scrolltime tween="cubic" easing="out">200</scrolltime>
                <itemlayout height="77" width="592">
                    <control type="label">
                        <left>32</left>
                        <width>528</width>
                        <height>64</height>
                        <font>font12</font>
                        <aligny>center</aligny>
                        <textcolor>FFDCE2E7</textcolor>
                        <label>%(label)s</label>
                    </control>
                </itemlayout>
                <focusedlayout height="77" width="592">
                    <control type="image">
                        <width>592</width>
                        <height>64</height>
                        <texture border="32">lucent/pill64.png</texture>
                        <colordiffuse>FFFFFFFF</colordiffuse>
                        <animation effect="zoom" start="97" end="100" center="auto" time="160" tween="cubic" easing="out">Focus</animation>
                    </control>
                    <control type="label">
                        <left>32</left>
                        <width>528</width>
                        <height>64</height>
                        <font>font12</font>
                        <aligny>center</aligny>
                        <textcolor>FF%(bg)s</textcolor>
                        <label>[B]%(label)s[/B]</label>
                    </control>
                </focusedlayout>
            </control>
        </control>''' % {'label': label, 'bg': BG}
    return window_shell('POV', 'options menu', body)


def resume_buttons_fen():
    resume = 'String.IsEqual(Window.Property(window_mode),resume)'
    return button_row([
        action_button('10', 'Resume $INFO[Window.Property(resume_percent)]%', nav='\n                    <onleft>12</onleft>\n                    <onright>11</onright>'),
        action_button('11', 'Start Over', nav='\n                    <onleft>10</onleft>\n                    <onright>12</onright>'),
        action_button('12', 'Cancel', nav='\n                    <onleft>11</onleft>\n                    <onright>10</onright>'),
    ], 160, visible=resume)


def resume_buttons_redlight():
    vis = 'String.IsEqual(Window.Property(window_mode),resume) + String.IsEqual(Window.Property(resume_ready),true)'
    return button_row([
        action_button('3010', '$INFO[Window.Property(resume_btn_label)]', nav='\n                    <onleft>3012</onleft>\n                    <onright>3011</onright>'),
        action_button('3011', '$INFO[Window.Property(startover_btn_label)]', nav='\n                    <onleft>3010</onleft>\n                    <onright>3012</onright>'),
        action_button('3012', '$INFO[Window.Property(cancel_btn_label)]', nav='\n                    <onleft>3011</onleft>\n                    <onright>3010</onright>'),
    ], 160, visible=vis, gid='3001')



SEL_W, SEL_ROW, SEL_HEAD, SEL_PAD, SEL_MAX = 900, 76, 148, 24, 8


def _sel_h(n):
    return SEL_HEAD + SEL_ROW * n + SEL_PAD


def lucent_select():
    """Themed select / multi-select used by the helper's filter menus
    (Fen Light / Red Light RIGHT, Umbrella filter). Contract (lucent_theme.py):
    list 5000; Window props lucent.heading, lucent.subtitle, lucent.multi,
    lucent.rows (1..8); ListItem label / label2 (count), props lucent.checked,
    lucent.kind=apply (first row of a multi-select)."""
    L = SEL_W
    left = (1920 - L) // 2
    top8 = (1080 - _sel_h(SEL_MAX)) // 2
    rows = 'Window.Property(lucent.rows)'
    multi = 'String.IsEqual(Window.Property(lucent.multi),true)'
    panels, shifts = [], []
    for n in range(1, SEL_MAX + 1):
        h = _sel_h(n)
        t = (1080 - h) // 2
        cond = 'String.IsEqual(%s,%d)' % (rows, n)
        panels.append("""
            <control type="group">
                <top>%(t)d</top>
                <visible>%(c)s</visible>
                <control type="image">
                    <left>-40</left>
                    <top>-40</top>
                    <width>%(sw)d</width>
                    <height>%(sh)d</height>
                    <texture border="88">lucent/panel_shadow.png</texture>
                    <colordiffuse>B3000000</colordiffuse>
                </control>
                <control type="image">
                    <width>%(w)d</width>
                    <height>%(h)d</height>
                    <texture border="48">lucent/panel.png</texture>
                    <colordiffuse>F5162532</colordiffuse>
                </control>
                <control type="image">
                    <width>%(w)d</width>
                    <height>%(h)d</height>
                    <texture border="48">lucent/panel_edge.png</texture>
                    <colordiffuse>2EFFFFFF</colordiffuse>
                </control>
            </control>""" % {'t': t, 'c': cond, 'w': L, 'h': h, 'sw': L + 80, 'sh': h + 80})
        if n < SEL_MAX:
            shifts.append('\n            <animation effect="slide" end="0,%d" time="0" condition="%s">Conditional</animation>'
                          % (t - top8, cond))

    def row(focused):
        pill = ''
        if focused:
            pill = """
                        <control type="image">
                            <width>%d</width>
                            <height>64</height>
                            <texture border="32">lucent/pill64.png</texture>
                            <colordiffuse>FFFFFFFF</colordiffuse>
                        </control>""" % (L - 40)
        txt = 'FF%s' % BG if focused else 'FFDCE2E7'
        cnt_bg = '1F%s' % BG if focused else '1AFFFFFF'
        cnt_txt = 'FF%s' % BG if focused else 'FFBDC8D1'
        circle_off = '66%s' % BG if focused else '40FFFFFF'
        circle_on = 'FF%s' % BG if focused else 'FFFFFFFF'
        dot_on = 'FFFFFFFF' if focused else 'FF%s' % BG
        bold = '[B]%s[/B]' if focused else '%s'
        not_apply = 'String.IsEmpty(ListItem.Property(lucent.kind))'
        return """
                    <control type="group">%(pill)s
                        <!-- multi-select check circle -->
                        <control type="group">
                            <visible>%(multi)s + %(na)s</visible>
                            <control type="image">
                                <left>28</left>
                                <top>15</top>
                                <width>34</width>
                                <height>34</height>
                                <texture border="17">lucent/pill42.png</texture>
                                <colordiffuse>%(coff)s</colordiffuse>
                                <visible>String.IsEmpty(ListItem.Property(lucent.checked))</visible>
                            </control>
                            <control type="image">
                                <left>28</left>
                                <top>15</top>
                                <width>34</width>
                                <height>34</height>
                                <texture border="17">lucent/pill42.png</texture>
                                <colordiffuse>%(con)s</colordiffuse>
                                <visible>!String.IsEmpty(ListItem.Property(lucent.checked))</visible>
                            </control>
                            <control type="image">
                                <left>38</left>
                                <top>25</top>
                                <width>14</width>
                                <height>14</height>
                                <texture>lucent/dot.png</texture>
                                <colordiffuse>%(don)s</colordiffuse>
                                <visible>!String.IsEmpty(ListItem.Property(lucent.checked))</visible>
                            </control>
                        </control>
                        <!-- label: plain list -->
                        <control type="label">
                            <left>36</left>
                            <width>%(lw)d</width>
                            <height>64</height>
                            <font>font12</font>
                            <aligny>center</aligny>
                            <textcolor>%(txt)s</textcolor>
                            <label>%(lab)s</label>
                            <visible>!%(multi)s + !%(icons)s</visible>
                        </control>
                        <!-- icon rows (totals screen): resolution badge + service icon + label -->
                        <control type="group">
                            <visible>!%(multi)s + %(icons)s</visible>
                            <control type="image">
                                <left>24</left>
                                <top>9</top>
                                <width>110</width>
                                <height>46</height>
                                <aspectratio>keep</aspectratio>
                                <texture>$INFO[ListItem.Art(icon)]</texture>
                                <visible>!String.IsEmpty(ListItem.Art(icon))</visible>
                            </control>
                            <control type="image">
                                <left>146</left>
                                <top>10</top>
                                <width>44</width>
                                <height>44</height>
                                <aspectratio>keep</aspectratio>
                                <texture>$INFO[ListItem.Art(thumb)]</texture>
                                <visible>!String.IsEmpty(ListItem.Art(thumb))</visible>
                            </control>
                            <control type="label">
                                <left>206</left>
                                <width>%(lw3)d</width>
                                <height>64</height>
                                <font>font12</font>
                                <aligny>center</aligny>
                                <textcolor>%(txt)s</textcolor>
                                <label>%(lab)s</label>
                            </control>
                        </control>
                        <!-- label: multi-select rows -->
                        <control type="label">
                            <left>84</left>
                            <width>%(lw2)d</width>
                            <height>64</height>
                            <font>font12</font>
                            <aligny>center</aligny>
                            <textcolor>%(txt)s</textcolor>
                            <label>%(lab)s</label>
                            <visible>%(multi)s + %(na)s</visible>
                        </control>
                        <!-- label: Apply row -->
                        <control type="label">
                            <left>36</left>
                            <width>%(lw)d</width>
                            <height>64</height>
                            <font>font12</font>
                            <aligny>center</aligny>
                            <textcolor>%(apc)s</textcolor>
                            <label>[B]✓  $INFO[ListItem.Label][/B]</label>
                            <visible>!%(na)s</visible>
                        </control>
                        <!-- count pill -->
                        <control type="group">
                            <left>%(cl)d</left>
                            <top>11</top>
                            <visible>!String.IsEmpty(ListItem.Label2)</visible>
                            <control type="image">
                                <width>150</width>
                                <height>42</height>
                                <texture border="21">lucent/pill42.png</texture>
                                <colordiffuse>%(cbg)s</colordiffuse>
                            </control>
                            <control type="label">
                                <width>150</width>
                                <height>42</height>
                                <font>font12</font>
                                <align>center</align>
                                <aligny>center</aligny>
                                <textcolor>%(ctx)s</textcolor>
                                <label>[B]$INFO[ListItem.Label2][/B]</label>
                            </control>
                        </control>
                    </control>""" % {
            'pill': pill, 'multi': multi, 'na': not_apply, 'coff': circle_off, 'con': circle_on, 'don': dot_on,
            'lw': L - 40 - 36 - 190, 'lw2': L - 40 - 84 - 190, 'lw3': L - 40 - 206 - 190, 'txt': txt,
            'icons': 'String.IsEqual(Window.Property(lucent.icons),true)',
            'lab': bold % '$INFO[ListItem.Label]', 'apc': txt if focused else 'FFD6F0FF',
            'cl': L - 40 - 150 - 22, 'cbg': cnt_bg, 'ctx': cnt_txt}

    body = """
        <control type="image">
            <texture>lucent/white.png</texture>
            <colordiffuse>C0000000</colordiffuse>
            <animation effect="fade" start="0" end="100" time="200">WindowOpen</animation>
            <animation effect="fade" end="0" time="150">WindowClose</animation>
        </control>
        <control type="group">
            <animation effect="fade" start="0" end="100" time="220">WindowOpen</animation>
            <animation effect="zoom" start="95" end="100" center="960,540" time="240" tween="cubic" easing="out">WindowOpen</animation>
            <animation effect="fade" end="0" time="150">WindowClose</animation>
            <left>%(left)d</left>
            <width>%(w)d</width>%(panels)s
            <control type="group">
                <top>%(top8)d</top>%(shifts)s
                <control type="label">
                    <left>40</left>
                    <top>32</top>
                    <width>%(tw)d</width>
                    <height>48</height>
                    <font>font27</font>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>[B]$INFO[Window.Property(lucent.heading)][/B]</label>
                </control>
                <control type="label">
                    <left>40</left>
                    <top>80</top>
                    <width>%(tw)d</width>
                    <height>30</height>
                    <font>font12</font>
                    <textcolor>FF8F9BA6</textcolor>
                    <label>[UPPERCASE]$INFO[Window.Property(lucent.subtitle)][/UPPERCASE]</label>
                </control>
                <control type="label">
                    <right>40</right>
                    <top>36</top>
                    <width>200</width>
                    <height>40</height>
                    <font>font12</font>
                    <align>right</align>
                    <textcolor>FFBDC8D1</textcolor>
                    <label>$INFO[Container(5000).CurrentItem]$INFO[Container(5000).NumItems, / ,]</label>
                </control>
                <control type="image">
                    <left>40</left>
                    <top>124</top>
                    <width>%(tw)d</width>
                    <height>1</height>
                    <texture>lucent/white.png</texture>
                    <colordiffuse>1AFFFFFF</colordiffuse>
                </control>
                <control type="list" id="5000">
                    <left>20</left>
                    <top>%(lt)d</top>
                    <width>%(lw)d</width>
                    <height>%(lh)d</height>
                    <onup>5000</onup>
                    <ondown>5000</ondown>
                    <onleft>5000</onleft>
                    <onright>5000</onright>
                    <orientation>vertical</orientation>
                    <scrolltime tween="cubic" easing="out">200</scrolltime>
                    <itemlayout height="%(rh)d" width="%(lw)d">%(idle)s
                    </itemlayout>
                    <focusedlayout height="%(rh)d" width="%(lw)d">
                        <control type="group">
                            <animation effect="zoom" start="98" end="100" center="auto" time="160" tween="cubic" easing="out">Focus</animation>%(foc)s
                        </control>
                    </focusedlayout>
                </control>
            </control>
        </control>""" % {
        'left': left, 'w': L, 'panels': ''.join(panels), 'top8': top8, 'shifts': ''.join(shifts),
        'tw': L - 80, 'lt': SEL_HEAD - 8, 'lw': L - 40, 'lh': SEL_ROW * SEL_MAX, 'rh': SEL_ROW,
        'idle': row(False), 'foc': row(True)}
    return window_shell('Fen Light / Red Light / Umbrella', 'filter menu', body, default='5000')


# ───────────────────────── AB Tools "Search All" window ─────────────────────────
# Lives in AB Tools' own skin folder; textures are read straight from
# resources/lucent/media (absolute special:// paths, no second copy).

AB_MEDIA = 'special://home/addons/plugin.program.abukarimtools/resources/lucent/media/'
AB_ADDONS = (('rl', 'FFE5484D'), ('fl', 'FF3E9BFF'), ('umb', 'FF9B6BFF'), ('pov', 'FF2BC48A'))
AB_TAGS = 4
AB_TAG_W = 64


def _ab_tags(active):
    """Up to 4 add-on tags at the right end of the meta line (slot 1 rightmost);
    the meta text is fitted shorter in Python to leave room for them."""
    out = []
    for n in range(1, AB_TAGS + 1):
        left = 904 - 20 - n * (AB_TAG_W + 6) + 6
        for key, color in AB_ADDONS:
            out.append('''
                        <control type="image">
                            <left>%d</left>
                            <top>49</top>
                            <width>%d</width>
                            <height>28</height>
                            <texture border="14">lucent/pill42.png</texture>
                            <colordiffuse>%s</colordiffuse>
                            <visible>String.IsEqual(ListItem.Property(abs.tag_%d),%s)</visible>
                        </control>''' % (left, AB_TAG_W, color if active else 'A6' + color[2:], n, key))
        out.append('''
                        <control type="label">
                            <left>%d</left>
                            <top>49</top>
                            <width>%d</width>
                            <height>28</height>
                            <font>font12</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>[B]$INFO[ListItem.Property(abs.tagtxt_%d)][/B]</label>
                        </control>''' % (left, AB_TAG_W, n))
    return ''.join(out)


def ab_card(state):
    """Glass stream card (same as the add-ons' windows) + add-on tags."""
    xml = card(state, {'full_prop': 'abs.never', 'full_label': ''})
    marker = '\n                    <!-- Full search -->'
    assert marker in xml
    return xml.replace(marker, _ab_tags(state == 'active') + marker, 1)


def ab_chip(focused):
    if focused:
        bg = '''
                    <control type="image">
                        <width>226</width>
                        <height>52</height>
                        <texture border="26">lucent/pill60.png</texture>
                        <colordiffuse>FFFFFFFF</colordiffuse>
                    </control>'''
        tc, cc = 'FF%s' % BG, 'FF%s' % BG
    else:
        bg = '''
                    <control type="image">
                        <width>226</width>
                        <height>52</height>
                        <texture border="26">lucent/pill60.png</texture>
                        <colordiffuse>1AFFFFFF</colordiffuse>
                        <visible>String.IsEmpty(ListItem.Property(abs.active))</visible>
                    </control>
                    <control type="image">
                        <width>226</width>
                        <height>52</height>
                        <texture border="26">lucent/pill60.png</texture>
                        <colordiffuse>66D6F0FF</colordiffuse>
                        <visible>!String.IsEmpty(ListItem.Property(abs.active))</visible>
                    </control>'''
        tc, cc = 'FFFFFFFF', 'FFBDC8D1'
    dots = ''.join('''
                    <control type="image">
                        <left>16</left>
                        <top>19</top>
                        <width>14</width>
                        <height>14</height>
                        <texture>lucent/dot.png</texture>
                        <colordiffuse>%s</colordiffuse>
                        <visible>String.IsEqual(ListItem.Property(abs.key),%s) + String.IsEmpty(ListItem.Property(abs.loading))</visible>
                    </control>''' % (color, key) for key, color in AB_ADDONS)
    return '''%(bg)s%(dots)s
                    <control type="image">
                        <left>16</left>
                        <top>19</top>
                        <width>14</width>
                        <height>14</height>
                        <texture>lucent/dot.png</texture>
                        <colordiffuse>%(cc)s</colordiffuse>
                        <animation effect="fade" start="100" end="15" time="500" pulse="true" condition="true">Conditional</animation>
                        <visible>!String.IsEmpty(ListItem.Property(abs.loading))</visible>
                    </control>
                    <control type="label">
                        <left>30</left>
                        <width>190</width>
                        <height>52</height>
                        <font>font12</font>
                        <align>center</align>
                        <aligny>center</aligny>
                        <textcolor>%(tc)s</textcolor>
                        <label>[B]$INFO[ListItem.Label][/B]$INFO[ListItem.Label2,  ,]</label>
                    </control>''' % {'bg': bg, 'dots': dots, 'tc': tc, 'cc': cc}


def ab_search_window():
    W = 'Window.Property(abs.%s)'
    slots = []
    for n in range(1, 5):
        top = (n - 1) * 54
        dots = ''.join('''
                <control type="image">
                    <left>0</left>
                    <top>%(t)d</top>
                    <width>16</width>
                    <height>16</height>
                    <texture>lucent/dot.png</texture>
                    <colordiffuse>%(c)s</colordiffuse>
                    <animation effect="fade" start="100" end="15" time="500" pulse="true" condition="String.IsEqual(Window.Property(abs.s%(n)d.state),searching)">Conditional</animation>
                    <visible>String.IsEqual(Window.Property(abs.s%(n)d.key),%(k)s)</visible>
                </control>''' % {'t': top + 17, 'c': color, 'n': n, 'k': key} for key, color in AB_ADDONS)
        slots.append('''%(dots)s
                <control type="label">
                    <left>32</left>
                    <top>%(t)d</top>
                    <width>360</width>
                    <height>50</height>
                    <font>font12</font>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>[B]$INFO[Window.Property(abs.s%(n)d.name)][/B]</label>
                </control>
                <control type="label">
                    <left>392</left>
                    <top>%(t)d</top>
                    <width>308</width>
                    <height>50</height>
                    <font>font12</font>
                    <align>right</align>
                    <aligny>center</aligny>
                    <textcolor>FFBDC8D1</textcolor>
                    <label>$INFO[Window.Property(abs.s%(n)d.status)]</label>
                </control>''' % {'dots': dots, 't': top, 'n': n})
    status = '''
        <!-- ============ Left: one line per add-on (searching / N streams) ============ -->
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="200">WindowOpen</animation>
            <animation effect="fade" end="0" time="250">WindowClose</animation>
            <left>96</left>
            <top>736</top>
            <width>700</width>
            <control type="label">
                <width>700</width>
                <height>40</height>
                <font>font12</font>
                <textcolor>FF8F9BA6</textcolor>
                <label>[B][UPPERCASE]$INFO[%(heading)s][/UPPERCASE][/B]</label>
            </control>
            <control type="image">
                <top>44</top>
                <width>700</width>
                <height>1</height>
                <texture>lucent/white.png</texture>
                <colordiffuse>1AFFFFFF</colordiffuse>
            </control>
            <control type="group">
                <top>56</top>%(slots)s
            </control>
        </control>''' % {'heading': W % 'addons_heading', 'slots': ''.join(slots)}
    body = '''
        <!-- ============ Right: glass stream panel ============ -->
        <control type="group">
            <animation effect="fade" start="0" end="100" time="350" delay="150">WindowOpen</animation>
            <animation effect="slide" start="120,0" end="0,0" time="400" delay="150" tween="cubic" easing="out">WindowOpen</animation>
            <animation effect="slide" end="200,0" time="300" tween="cubic" easing="in">WindowClose</animation>
            <animation effect="fade" end="0" time="300">WindowClose</animation>
            <left>880</left>
            <top>56</top>
            <width>984</width>
            <height>968</height>%(glass)s
            <control type="label">
                <left>40</left>
                <top>26</top>
                <width>600</width>
                <height>50</height>
                <font>font27</font>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]$INFO[%(head)s][/B]</label>
            </control>
            <control type="label">
                <left>624</left>
                <top>26</top>
                <width>320</width>
                <height>50</height>
                <font>font12</font>
                <align>right</align>
                <aligny>center</aligny>
                <textcolor>FFBDC8D1</textcolor>
                <label>$INFO[Container(2000).CurrentItem]$INFO[Container(2000).NumItems, / ,]</label>
                <visible>Integer.IsGreater(Container(2000).NumItems,0)</visible>
            </control>
            <control type="label">
                <left>40</left>
                <top>70</top>
                <width>904</width>
                <height>26</height>
                <font>font12</font>
                <textcolor>FF8F9BA6</textcolor>
                <label>$INFO[%(sub)s]</label>
            </control>
            <!-- Filter chips: All, each add-on, each quality -->
            <control type="list" id="2300">
                <left>40</left>
                <top>110</top>
                <width>904</width>
                <height>52</height>
                <orientation>horizontal</orientation>
                <scrolltime tween="cubic" easing="out">200</scrolltime>
                <ondown>2000</ondown>
                <itemlayout height="52" width="238">%(chip)s
                </itemlayout>
                <focusedlayout height="52" width="238" condition="!Control.HasFocus(2300)">%(chip)s
                </focusedlayout>
                <focusedlayout height="52" width="238" condition="Control.HasFocus(2300)">%(chipf)s
                </focusedlayout>
            </control>
            <control type="image">
                <left>40</left>
                <top>178</top>
                <width>904</width>
                <height>1</height>
                <texture>lucent/white.png</texture>
                <colordiffuse>1AFFFFFF</colordiffuse>
            </control>
            <control type="scrollbar" id="2001">
                <left>962</left>
                <top>196</top>
                <width>6</width>
                <height>740</height>
                <onleft>2000</onleft>
                <showonepage>false</showonepage>
                <orientation>vertical</orientation>
                <texturesliderbackground colordiffuse="14FFFFFF" border="3">lucent/pill6.png</texturesliderbackground>
                <texturesliderbar colordiffuse="4DFFFFFF" border="3">lucent/pill6.png</texturesliderbar>
                <texturesliderbarfocus colordiffuse="FFFFFFFF" border="3">lucent/pill6.png</texturesliderbarfocus>
            </control>
            <control type="list" id="2000">
                <left>24</left>
                <top>184</top>
                <width>936</width>
                <height>768</height>
                <orientation>vertical</orientation>
                <pagecontrol>2001</pagecontrol>
                <scrolltime tween="cubic" easing="out">250</scrolltime>
                <focusposition>1</focusposition>
                <movement>2</movement>
                <onup>2300</onup>
                <itemlayout height="148" width="936">%(idle)s
                </itemlayout>
                <focusedlayout height="148" width="936" condition="!Control.HasFocus(2000)">%(dim)s
                </focusedlayout>
                <focusedlayout height="148" width="936" condition="Control.HasFocus(2000)">%(active)s
                </focusedlayout>
            </control>
            <!-- Still searching / nothing found -->
            <control type="group">
                <top>420</top>
                <visible>!Integer.IsGreater(Container(2000).NumItems,0)</visible>
                <control type="image">
                    <left>476</left>
                    <width>32</width>
                    <height>32</height>
                    <texture>lucent/dot.png</texture>
                    <colordiffuse>FFFFFFFF</colordiffuse>
                    <animation effect="fade" start="100" end="15" time="500" pulse="true" condition="true">Conditional</animation>
                    <visible>String.IsEmpty(%(empty)s)</visible>
                </control>
                <control type="label">
                    <left>40</left>
                    <top>56</top>
                    <width>904</width>
                    <height>50</height>
                    <font>font27</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFDCE2E7</textcolor>
                    <label>$INFO[%(waitmsg)s]</label>
                </control>
            </control>
        </control>''' % {'glass': glass(0, 0, 984, 968), 'head': W % 'heading', 'sub': W % 'subhead',
                          'chip': ab_chip(False), 'chipf': ab_chip(True), 'empty': W % 'empty', 'waitmsg': W % 'waitmsg',
                          'idle': ab_card('idle'), 'dim': ab_card('dim'), 'active': ab_card('active')}
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<!-- AB Tools - Search All (streams from every add-on). Generated by tools/gen_lucent.py. -->
<!-- Look and textures: Lucent theme for Seren by djdirty60 (github.com/djdirty60/Seren-Thema). -->
<window type="dialog">
    <coordinates>
        <left>0</left>
        <top>0</top>
        <width>1920</width>
        <height>1080</height>
    </coordinates>
    <defaultcontrol always="true">2300</defaultcontrol>
    <controls>%(bg)s%(title)s%(plot)s%(status)s%(body)s
    </controls>
</window>
''' % {'bg': backdrop('$INFO[Window.Property(lucent.fanart)]'), 'title': title_block(),
       'plot': plot_block('$INFO[Window.Property(lucent.plot)]', height=220),
       'status': status, 'body': body}
    import re as _re
    return _re.sub(r'(<texture[a-z]*(?: [^>]*)?>)lucent/', lambda m: m.group(1) + AB_MEDIA + 'lucent/', xml)


def build():
    files = {}
    fen_counts = [('4K', 'Window.Property(results_4k)'), ('1080P', 'Window.Property(results_1080p)'),
                  ('720P', 'Window.Property(results_720p)'), ('SD', 'Window.Property(results_sd)'),
                  ('TOTAL', 'Window.Property(results_total)')]
    rl = 'Window(10000).Property(redlight.scrape.%s)'
    rl_counts = [('4K', rl % 'results_4k'), ('1080P', rl % 'results_1080p'), ('720P', rl % 'results_720p'),
                 ('SD', rl % 'results_sd'), ('TOTAL', rl % 'results_total')]
    files['fenlight/sources_results.xml'] = results_window(fen_results_profile('Fen Light'))
    files['fenlight/sources_playback.xml'] = fen_playback('Fen Light', fen_counts, 'Window.Property(percent)',
                                                          'Window.Property(percent)', resume_buttons_fen())
    files['redlight/sources_results.xml'] = results_window(fen_results_profile('Red Light'))
    files['redlight/sources_playback.xml'] = fen_playback(
        'Red Light', rl_counts, rl % 'percent', 'Window.Property(resume_timeout_percent)', resume_buttons_redlight())
    files['pov/sources_results.xml'] = results_window(pov_results_profile())
    files['pov/progress_media.xml'] = pov_progress()
    files['pov/contextmenu.xml'] = pov_contextmenu()
    files['shared/lucent_select.xml'] = lucent_select()
    files['umbrella/source_results.xml'] = results_window(umbrella_results_profile('2000', 'results'))
    files['umbrella/uncached_results.xml'] = results_window(umbrella_results_profile('2001', 'uncached', buttons=False))
    files['umbrella/source_progress.xml'] = umbrella_progress()
    ab_path = os.path.join(ROOT, 'resources', 'skins', 'Default', '1080i', 'ab_search.xml')
    with open(ab_path, 'w', encoding='utf-8') as f:
        f.write(ab_search_window())
    for rel, xml in files.items():
        path = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(xml)
    return files


if __name__ == '__main__':
    for rel in sorted(build()):
        print(rel)
