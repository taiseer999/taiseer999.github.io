AF3: Lucent Player (ABUKARIM TOOLS 4.7.25)

The OSD, seek bar / pause card, buffering spinner and Statistics window are
ported from the Lucent skin by djdirty60 - https://github.com/djdirty60/Lucent
(commit 39ba04a, version 1.34.11). Lucent is licensed GPL-2.0-or-later; these
derived files (Includes_ABK_LucentPlayer.xml, ABK_LucentPlayerInfo.xml,
media/, resources/lib/lucent_playerinfo.py, resources/lib/lucent_sleep.py)
are distributed under the same licence. Regenerate them from a Lucent
checkout with tools/lucent_player/port.py.

4.8.69: after port.py, af3_layout.py and af3_furniture.py, run
tools/lucent_player/af3_flagstyle.py on Includes_ABK_LucentPlayer.xml so the
pills follow "AF3: OSD Flags Style" (ABK_LP_FlagDir).
