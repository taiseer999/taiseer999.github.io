# -*- coding: utf-8 -*-
"""4.7.26: fit the ported Lucent OSD around Arctic Fuse 3's own OSD.

Run after port.py:  python3 tools/lucent_player/af3_layout.py resources/lucent_player/Includes_ABK_LucentPlayer.xml

- AF3 keeps its own OSD buttons (and its new Statistics button, patcher.py),
  so Lucent's button row (grouplist 7100) and its focused-button name go.
- The logo / title block moves down to where AF3's info-on-controls block
  (window 1153) puts its logo, and steps aside while 1153 is shown.
- The format flags of the pause card (4K, Dolby Vision, HEVC, Atmos, DD+, 5.1)
  are added to the OSD, in the band above the progress bar.
Idempotent: a second run changes nothing.
"""
import copy
import sys

from lxml import etree

MARK = 'ABK_LP_AF3_LAYOUT'
LOGO_TOP = '340'
FLAGS_TOP = '772'


def main(path):
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(path, parser)
    root = tree.getroot()
    if any(MARK in (c.text or '') for c in root.iter(etree.Comment)):
        print('already laid out')
        return
    osd = root.find('.//include[@name="ABK_LP_VideoOSD"]')
    seek = root.find('.//include[@name="ABK_LP_SeekBar"]')
    assert osd is not None and seek is not None

    # 1. Lucent buttons and the focused-button name
    gl = osd.find('.//control[@id="7100"]')
    gl.getparent().remove(gl)
    for lab in osd.iter('control'):
        if lab.get('type') == 'label' and (lab.findtext('label') or '') == '$VAR[ABK_LP_OSDButtonLabel]':
            lab.getparent().remove(lab)
            break
    btn = osd.find('.//control[@id="7087"]')
    btn.find('ondown').text = '6091'          # AF3 buttons

    # 2. logo / title block
    logo = None
    for g in osd.iter('control'):
        if g.get('type') == 'group' and g.find('control/texture') is not None \
                and g.find('control/texture').text == '$VAR[ABK_LP_PlayerLogo]':
            logo = g
            break
    assert logo is not None
    logo.find('top').text = LOGO_TOP
    vis = etree.SubElement(logo, 'visible')
    vis.text = '!Window.IsVisible(1153)'
    logo.insert(0, etree.Comment(' %s: below the AF3 badges, hidden while AF3 shows its own info block (1153) ' % MARK))
    logo.remove(vis)
    logo.insert(1, vis)

    # 3. the pause card flags, copied into the OSD
    flags = copy.deepcopy(seek.find('.//control[@id="14600"]'))
    for c in flags.iter('control'):
        c.attrib.pop('id', None)
    for tag, val in (('left', '96'), ('top', FLAGS_TOP)):
        e = flags.find(tag)
        if e is None:
            e = etree.Element(tag)
            flags.insert(0, e)
        e.text = val
    host = logo.getparent()
    host.insert(host.index(logo) + 1, flags)
    flags.addprevious(etree.Comment(' %s: format flags (Lucent pause card) ' % MARK))

    tree.write(path, encoding='UTF-8', xml_declaration=True)
    print('laid out', path)


if __name__ == '__main__':
    main(sys.argv[1])
