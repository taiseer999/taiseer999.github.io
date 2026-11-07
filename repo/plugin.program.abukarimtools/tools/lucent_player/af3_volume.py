# -*- coding: utf-8 -*-
"""4.7.32: Lucent's passthrough note on AF3's volume dialog.

Run after port.py / af3_layout.py / af3_furniture.py:
    python3 tools/lucent_player/af3_volume.py resources/lucent_player/Includes_ABK_LucentPlayer.xml

Adds include ABK_LP_VolumePassthrough: Lucent 1.33.6 DialogVolumeBar.xml
(djdirty60, GPL-2.0-or-later) - a glass bar shown while the sound goes
straight to the amplifier (Player.Passthrough), where Kodi's volume does
nothing. Only the note is taken; AF3 keeps its own volume bar. patcher.py
puts the include into AF3's DialogVolumeBar.xml (skin bool abk.lucentplayer).
Strings 32100 / 32101 (strings_map.py). Idempotent.
"""
import sys

from lxml import etree

NAME = 'ABK_LP_VolumePassthrough'
XML = """<include name="%s">
        <param name="left">560</param>
        <param name="top">40</param>
        <definition>
            <control type="group">
                <left>$PARAM[left]</left>
                <top>$PARAM[top]</top>
                <width>800</width>
                <height>70</height>
                <visible>Skin.HasSetting(abk.lucentplayer) + Player.Passthrough</visible>
                <animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>
                <animation effect="fade" start="100" end="0" time="300">WindowClose</animation>
                <control type="image"><left>0</left><top>0</top><width>800</width><height>70</height><texture border="24">abk_lp/pinfo/rr22.png</texture><colordiffuse>EB0E121C</colordiffuse></control>
                <control type="image"><left>0</left><top>0</top><width>800</width><height>70</height><texture border="28">abk_lp/pinfo/rr28_edge.png</texture><colordiffuse>1AFFFFFF</colordiffuse></control>
                <control type="grouplist"><left>30</left><top>0</top><width>740</width><height>70</height><orientation>horizontal</orientation><itemgap>10</itemgap>
                    <control type="label"><width>auto</width><height>70</height><font>abk_lp_font_caps</font><textcolor>FF5FE0E0</textcolor><aligny>center</aligny><label>$ADDON[plugin.program.abukarimtools 32100]</label></control>
                    <control type="label"><width>auto</width><height>70</height><font>abk_lp_font10</font><textcolor>BFFFFFFF</textcolor><aligny>center</aligny><label>·  $ADDON[plugin.program.abukarimtools 32101]</label></control>
                </control>
            </control>
        </definition>
    </include>""" % NAME


def main(path):
    tree = etree.parse(path)
    root = tree.getroot()
    if root.find('include[@name="%s"]' % NAME) is not None:
        print('already there')
        return
    el = etree.fromstring(XML)
    el.tail = '\n'
    root.append(el)
    tree.write(path, encoding='UTF-8', xml_declaration=True)
    print('added', NAME)


if __name__ == '__main__':
    main(sys.argv[1])
