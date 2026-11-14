"""Last step after port.py / af3_layout.py / af3_furniture.py (4.8.69):
route every Lucent pill texture (abk_lp/flags/X.png) through ABK_LP_FlagDir so
"AF3: OSD Flags Style" can swap the Lucent Player's pills for another badge set
(resource.images.af3.frbadges/<style>/lucent_player/X.png, same file names).
Skin.String(abk.flagstyle) empty = the Lucent pills (Automatic / Lucent).
4.8.74: the player rows also get the AF3 "OSD extras" flags the Lucent
Player hid (AF3's DialogSeekBar group, ExtraOSD included, is off while the
Lucent Player is on): source (from the file name), aspect ratio, audio
language, subtitle language - drawn from ABK_LP_ExtraDir in the classic
folder layout of the chosen style.
Idempotent.  Usage: python3 af3_flagstyle.py .../Includes_ABK_LucentPlayer.xml
"""
import sys

VAR = '''<!-- 4.8.69: AF3 OSD Flags Style (af3_flagstyle.py) -->
    <variable name="ABK_LP_FlagDir">
        <value condition="!String.IsEmpty(Skin.String(abk.flagstyle)) + System.AddonIsEnabled(resource.images.af3.frbadges)">resource://resource.images.af3.frbadges/$INFO[Skin.String(abk.flagstyle)]/lucent_player</value>
        <value>abk_lp/flags</value>
    </variable>
'''


EXTRA_VARS = '''<!-- 4.8.74: OSD extras in the Lucent Player rows (af3_flagstyle.py) -->
    <variable name="ABK_LP_ExtraDir">
        <value condition="String.IsEqual(Skin.String(abk.flagstyle),colorful) + System.AddonIsEnabled(resource.images.af3.classicflags)">resource://resource.images.af3.classicflags/colorful</value>
        <value condition="!String.IsEmpty(Skin.String(abk.flagstyle)) + System.AddonIsEnabled(resource.images.af3.frbadges)">resource://resource.images.af3.frbadges/$INFO[Skin.String(abk.flagstyle)]</value>
        <value condition="System.AddonIsEnabled(resource.images.af3.frbadges)">resource://resource.images.af3.frbadges/lucent</value>
        <value condition="System.AddonIsEnabled(resource.images.af3.classicflags)">resource://resource.images.af3.classicflags/colorful</value>
        <value>flags/colorful</value>
    </variable>
    <variable name="ABK_LP_ExtraSource">
        <value condition="[String.Contains(Player.Filename,bluray) | String.Contains(Player.Filename,blu-ray) | String.Contains(Player.Filename,remux) | String.Contains(Player.Filename,bdrip) | String.Contains(Player.Filename,brrip)] + [String.Contains(Player.Filename,2160p) | String.Contains(Player.Filename,uhd)]">other/4k_bluray</value>
        <value condition="String.Contains(Player.Filename,bluray) | String.Contains(Player.Filename,blu-ray) | String.Contains(Player.Filename,remux) | String.Contains(Player.Filename,bdrip) | String.Contains(Player.Filename,brrip)">other/bluray</value>
        <value condition="String.Contains(Player.Filename,web-dl) | String.Contains(Player.Filename,webdl) | String.Contains(Player.Filename,webrip) | String.Contains(Player.Filename,.web.)">other/web-dl</value>
        <value condition="String.Contains(Player.Filename,hdtv)">other/hdtv</value>
        <value condition="String.Contains(Player.Filename,dvd)">other/dvd</value>
    </variable>
'''

EXTRA_MARK = '<!-- ABK_LP_EXTRAS -->'


def _img(w, texture, visible, fallback=''):
    fb = ' fallback="%s"' % fallback if fallback else ''
    return ('''                <control type="image">
                    <width>%d</width>
                    <height>51</height>
                    <aspectratio>keep</aspectratio>
                    <texture background="true"%s>%s</texture>
                    <visible>%s</visible>
                </control>
''' % (w, fb, texture, visible))


EXTRAS = (EXTRA_MARK + '\n'
          + _img(132, '$VAR[ABK_LP_ExtraDir]/$VAR[ABK_LP_ExtraSource].png', '!String.IsEmpty($VAR[ABK_LP_ExtraSource])')
          + _img(110, '$VAR[ABK_LP_ExtraDir]/aspectratio/$INFO[VideoPlayer.VideoAspect].png', '!String.IsEmpty(VideoPlayer.VideoAspect)')
          + _img(160, '$VAR[ABK_LP_ExtraDir]/other/language/$INFO[VideoPlayer.AudioLanguage].png', '!String.IsEmpty(VideoPlayer.AudioLanguage)',
                 '$VAR[ABK_LP_ExtraDir]/other/language/fallback.png')
          + _img(160, '$VAR[ABK_LP_ExtraDir]/other/language/$INFO[VideoPlayer.SubtitlesLanguage].png',
                 'VideoPlayer.SubtitlesEnabled + !String.IsEmpty(VideoPlayer.SubtitlesLanguage)',
                 '$VAR[ABK_LP_ExtraDir]/other/language/fallback.png'))


def _add_extras(s):
    """After the channels image of each player flag row; widen the row."""
    import re
    if EXTRA_MARK in s:
        return s
    ch = re.compile(r'(<control type="image"[^>]*>\s*<width>132</width>\s*<height>51</height>\s*<aspectratio>keep</aspectratio>\s*'
                    r'<texture>\$VAR\[ABK_LP_NuvioFlagImg_ch\]</texture>[\s\S]*?</control>\n)')
    s, n = ch.subn(lambda m: m.group(1) + EXTRAS, s)
    assert n == 3, n
    s = s.replace('<top>772</top><left>96</left><width>1100</width>', '<top>772</top><left>96</left><width>1728</width>')
    s = s.replace('<control type="grouplist" id="14600">\n                    <width>1100</width>',
                  '<control type="grouplist" id="14600">\n                    <width>1640</width>')
    # the info panel column (left 140) holds that row - a grouplist clips its children
    s = re.sub(r'(<control type="grouplist" id="14500">\s*<left>140</left>[\s\S]{0,80}?<width>)1100(</width>)', r'\g<1>1640\g<2>', s)
    return s


def main(path):
    s = open(path, encoding='utf-8').read()
    s = s.replace('abk_lp/flags/', '$VAR[ABK_LP_FlagDir]/')
    if 'name="ABK_LP_FlagDir"' not in s:
        i = s.index('<includes>') + len('<includes>')
        s = s[:i] + '\n    ' + VAR + s[i:]
    if 'name="ABK_LP_ExtraDir"' not in s:
        i = s.index('<includes>') + len('<includes>')
        s = s[:i] + '\n    ' + EXTRA_VARS + s[i:]
    s = _add_extras(s)
    open(path, 'w', encoding='utf-8').write(s)


if __name__ == '__main__':
    main(sys.argv[1])
