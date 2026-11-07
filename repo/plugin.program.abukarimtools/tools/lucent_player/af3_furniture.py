# -*- coding: utf-8 -*-
"""4.7.29: Lucent format pills for AF3's furniture codec logos.

Run after port.py / af3_layout.py:
    python3 tools/lucent_player/af3_furniture.py resources/lucent_player/Includes_ABK_LucentPlayer.xml

Adds include ABK_LP_FlagsRow: the Lucent pills (4K, Dolby Vision, HEVC, Atmos,
DD+, 5.1...) for any item, not only the playing video. The flag variables
(ABK_LP_NuvioFlagImg_*) read VideoPlayer.*, and a variable takes no params, so
every value becomes its own image with a mutually exclusive condition, and
VideoPlayer.X / Player.Filename[AndPath] become $PARAM[...]. patcher.py puts
the include into AF3's Furniture_Codecs (home widgets, info, OSD).
Idempotent.
"""
import re
import sys

from lxml import etree

NAME = 'ABK_LP_FlagsRow'
SLOTS = ('res', 'hdr', 'vcodec', 'atmos', 'acodec', 'ch')
PARAMS = (('videoresolution', 'VideoPlayer.VideoResolution'), ('hdrtype', 'VideoPlayer.HdrType'),
          ('videocodec', 'VideoPlayer.VideoCodec'), ('audiocodec', 'VideoPlayer.AudioCodec'),
          ('audiochannels', 'VideoPlayer.AudioChannels'), ('filename', 'Player.Filename'),
          ('filenameandpath', 'Player.FilenameAndPath'))


def _p(cond):
    cond = cond.replace('Player.FilenameAndPath', '$PARAM[il_filenameandpath]') \
               .replace('Player.Filename', '$PARAM[il_filename]')
    for name, label in PARAMS[:5]:
        cond = cond.replace(label, '$PARAM[il_%s]' % name)
    return cond


def main(path):
    tree = etree.parse(path)
    root = tree.getroot()
    if root.find('include[@name="%s"]' % NAME) is not None:
        print('already there')
        return
    exprs = {e.get('name'): e.text for e in root.findall('expression')}
    inc = etree.SubElement(root, 'include', name=NAME)
    for name, label in PARAMS:
        etree.SubElement(inc, 'param', name='il_' + name).text = label
    etree.SubElement(inc, 'param', name='visible').text = 'true'
    etree.SubElement(inc, 'param', name='align').text = 'center'
    etree.SubElement(inc, 'param', name='height').text = '51'
    etree.SubElement(inc, 'param', name='width').text = '132'
    etree.SubElement(inc, 'param', name='itemgap').text = '12'
    d = etree.SubElement(inc, 'definition')
    gl = etree.SubElement(d, 'control', type='grouplist')
    etree.SubElement(gl, 'visible').text = '$PARAM[visible]'
    for tag, val in (('orientation', 'horizontal'), ('align', '$PARAM[align]'), ('itemgap', '$PARAM[itemgap]'),
                     ('height', '$PARAM[height]'), ('usecontrolcoords', 'false')):
        etree.SubElement(gl, tag).text = val
    n = 0
    for slot in SLOTS:
        var = root.find('variable[@name="ABK_LP_NuvioFlagImg_%s"]' % slot)
        before = []
        for v in var.findall('value'):
            cond = v.get('condition') or ''
            if 'Skin.String(abk.lp.flag.' in cond:          # Lucent's own-flag override, not ported
                continue
            if 'LucentDV2Named' in cond:                     # its [dv2] text breaks the negated conditions
                continue
            cond = re.sub(r'\$EXP\[([^\]]+)\]', lambda m: '[%s]' % exprs[m.group(1)], cond)
            full = '[%s]' % _p(cond)
            if before:
                full += ' + !' + ' + !'.join(before)
            before.append('[%s]' % _p(cond))
            img = etree.SubElement(gl, 'control', type='image')
            etree.SubElement(img, 'width').text = '$PARAM[width]'
            etree.SubElement(img, 'height').text = '$PARAM[height]'
            etree.SubElement(img, 'centertop').text = '50%'
            etree.SubElement(img, 'aspectratio').text = 'keep'
            etree.SubElement(img, 'texture', background='true').text = v.text
            etree.SubElement(img, 'visible').text = full
            n += 1
    etree.indent(inc, space='    ', level=1)
    inc.tail = '\n'
    inc.addprevious(etree.Comment(' 4.7.29: Lucent pills for AF3 Furniture_Codecs (af3_furniture.py) '))
    tree.write(path, encoding='UTF-8', xml_declaration=True)
    print('%s: %d pill images' % (NAME, n))


if __name__ == '__main__':
    main(sys.argv[1])
