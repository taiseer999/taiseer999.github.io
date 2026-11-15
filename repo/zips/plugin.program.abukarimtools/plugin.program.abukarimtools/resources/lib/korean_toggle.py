# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools, see LICENSE.txt
"""Korean Media tab on/off – thin wrapper around tab_toggle."""
from resources.lib import tab_toggle


def run():
    tab_toggle.run(key='korean', slot='1103', label='Korean Media')
