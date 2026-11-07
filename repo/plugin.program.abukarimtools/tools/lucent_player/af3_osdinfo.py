# -*- coding: utf-8 -*-
"""4.7.33: info under the year / genre line of the Lucent Player OSD, and the DV2 test.

Run after port.py / af3_layout.py / af3_furniture.py / af3_volume.py:
    python3 tools/lucent_player/af3_osdinfo.py resources/lucent_player/Includes_ABK_LucentPlayer.xml

1. Lucent's OSD has only the logo and "year  genre" (top-left of the screen).
   Moved down under the AF3 badges (af3_layout.py) it left an empty band
   above the format pills, and AF3's own quick-info overlay is hidden while
   Lucent Player is on. Two controls are added to the title group, under the
   year / genre line: rating / runtime / certificate, and the plot (4 lines,
   scrolls when longer). Each hides when Kodi has nothing for it.
2. ABK_LP_LucentDV2Named (Lucent 1.34.1) tests String.Contains(...,[dv2]):
   Kodi reads the "[" as a group bracket, logs "Misplaced [" / "Error parsing
   boolean expression" and the whole expression never parses, so the DV2
   badge never showed. Those two [dv2] clauses go; ".dv2." etc. still match.
Idempotent.
"""
import re
import sys

MARK = '<!-- ABK_LP_OSDINFO -->'
SUBTITLE = '<label>$VAR[ABK_LP_PlayerSubtitle]</label>'
ADD = ('\n            ' + MARK + '\n'
       '            <control type="label">\n'
       '                <left>0</left>\n'
       '                <top>206</top>\n'
       '                <width>1100</width>\n'
       '                <height>36</height>\n'
       '                <font>abk_lp_font12</font>\n'
       '                <textcolor>B3FFFFFF</textcolor>\n'
       '                <shadowcolor>00FFFFFF</shadowcolor>\n'
       '                <aligny>center</aligny>\n'
       '                <label>$INFO[VideoPlayer.Rating,★ ,]$INFO[VideoPlayer.Duration,   ,]$INFO[VideoPlayer.mpaa,   ,]</label>\n'
       '                <visible>!String.IsEmpty(VideoPlayer.Rating) | !String.IsEmpty(VideoPlayer.Duration) | !String.IsEmpty(VideoPlayer.mpaa)</visible>\n'
       '            </control>\n'
       '            <control type="textbox">\n'
       '                <left>0</left>\n'
       '                <top>250</top>\n'
       '                <width>1000</width>\n'
       '                <height>124</height>\n'
       '                <font>abk_lp_font_body</font>\n'
       '                <textcolor>CCFFFFFF</textcolor>\n'
       '                <shadowcolor>00FFFFFF</shadowcolor>\n'
       '                <label>$INFO[VideoPlayer.Plot]</label>\n'
       '                <autoscroll delay="6000" time="3000" repeat="8000">true</autoscroll>\n'
       '                <visible>!String.IsEmpty(VideoPlayer.Plot)</visible>\n'
       '            </control>')


def main(path):
    txt = open(path, encoding='utf-8').read()
    done = []
    if MARK not in txt:
        # the subtitle label of the title group (the first one; the pause card has its own)
        i = txt.find(SUBTITLE)
        if i < 0:
            sys.exit('subtitle label not found')
        end = txt.find('</control>', i) + len('</control>')
        txt = txt[:end] + ADD + txt[end:]
        done.append('osd info')
    n = 0
    for il in ('Player.Filename', 'Player.FilenameAndPath'):
        txt, k = re.subn(r' \| String\.Contains\(%s,\[dv2\]\)' % re.escape(il), '', txt)
        n += k
    if n:
        done.append('dv2 test (%d clauses)' % n)
    if '[dv2]' in txt:
        sys.exit('[dv2] still present')
    open(path, 'w', encoding='utf-8').write(txt)
    print(', '.join(done) or 'already there')


if __name__ == '__main__':
    main(sys.argv[1])
