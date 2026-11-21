# SPDX-License-Identifier: GPL-3.0-or-later
# Kodi helper module, kept only for resources/lib/modules/speedtest.py (a separate script run with RunScript).
# GPL-3.0-or-later, see resources/licenses/GPL-3.0.txt. Not covered by the AB Tools licence.

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    # noinspection PyUnresolvedReferences
    import __builtin__
    # noinspection PyShadowingBuiltins
    unichr = __builtin__.unichr
    # noinspection PyShadowingBuiltins
    unicode = __builtin__.unicode
    # noinspection PyShadowingBuiltins
    basestring = __builtin__.basestring
else:
    # noinspection PyShadowingBuiltins
    unichr = chr
    # noinspection PyShadowingBuiltins
    unicode = str
    # noinspection PyShadowingBuiltins
    basestring = str
