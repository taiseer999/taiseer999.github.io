# -*- coding: utf-8 -*-
"""

    Copyright (C) 2020 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import json
import os
import tempfile
from copy import deepcopy

import xbmc  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

from .common import CONFIG
from .logger import Logger

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass

LOG = Logger('json_store')


class JSONStore:

    def __init__(self, filename):
        self.base_path = xbmc.translatePath(CONFIG['addon'].getAddonInfo('profile'))
        self.filename = os.path.join(self.base_path, filename)

        self._data = None
        self.load()
        self.set_defaults()

    def set_defaults(self):
        raise NotImplementedError

    def save(self, data):
        if data != self._data:
            self._data = deepcopy(data)
            if not xbmcvfs.exists(self.base_path):
                if not self.make_dirs(self.base_path):
                    LOG.debug('JSONStore Save |{filename}| failed to create directories.'
                              .format(filename=self.filename.encode('utf-8')))
                    return

            file_handle = None
            temp_name = None
            try:
                file_handle = tempfile.NamedTemporaryFile(
                    'w',
                    dir=self.base_path,
                    delete=False,
                    encoding='utf-8'
                )
                temp_name = file_handle.name
                LOG.debug('JSONStore Save |{filename}|'
                          .format(filename=self.filename.encode('utf-8')))
                json.dump(self._data, file_handle, indent=4, sort_keys=True)
                file_handle.flush()
                os.fsync(file_handle.fileno())
                file_handle.close()
                file_handle = None
                os.replace(temp_name, self.filename)
            except (OSError, ValueError, TypeError):
                LOG.debug('JSONStore Save failed |{filename}|'
                          .format(filename=self.filename.encode('utf-8')))

                if file_handle is not None:
                    try:
                        file_handle.close()
                    except OSError:
                        pass
                if temp_name:
                    try:
                        os.remove(temp_name)
                    except OSError:
                        pass

    def load(self):
        if xbmcvfs.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as jsonfile:
                    data = json.load(jsonfile)
                if not isinstance(data, dict):
                    raise ValueError('JSONStore data must be a dictionary')
                self._data = data
                LOG.debug('JSONStore Load |{filename}|'
                          .format(filename=self.filename.encode('utf-8')))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                LOG.debug('JSONStore Load failed, using defaults |{filename}|'
                          .format(filename=self.filename.encode('utf-8')))
                self._data = {}
        else:
            self._data = {}

    def get_data(self):
        return deepcopy(self._data)

    @staticmethod
    def make_dirs(path):
        if not path.endswith('/'):
            path = ''.join([path, '/'])
        path = xbmc.translatePath(path)
        if not xbmcvfs.exists(path):
            try:
                _ = xbmcvfs.mkdirs(path)
            except OSError:
                pass
            if not xbmcvfs.exists(path):
                try:
                    os.makedirs(path)
                except OSError:
                    pass
            return xbmcvfs.exists(path)

        return True
