from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from .retrieve import HandlerBase

import errno
import six
import logging
import numpy as np
import uuid
import os
import os.path as op
import datetime

import filestore.commands as fsc

logger = logging.getLogger(__name__)


class NpyWriter(HandlerBase):
    """
    Class to handle writing a numpy array out to disk and registering
    that write with FileStore.

    This class is only good for one call to add_data.

    Parameters
    ----------
    fpath : str
        Path (including filename) of where to save the file

    custom : dict, optional
        Saved in the custom field of the fileBase document.  Valid
        keys are {mmap_mode, }
    """

    SPEC_NAME = 'npy'

    def __init__(self, fpath, custom=None):
        if op.exists(fpath):
            raise IOError("the requested file {fpath} already exist")
        self._fpath = fpath
        if custom is None:
            custom = dict()
        for k in custom.keys():
            if k != 'mmap_mode':
                raise ValueError("The only valid custom key is 'mmaped_mode' "
                                 "you passed in {}".format(k))
        self._f_custom = dict(custom)

        self._writable = True

    def add_data(self, data, uid=None, custom=None):
        """
        Parameters
        ----------
        data : ndarray
            The data to save

        uid : str, optional
            The uid to be used for this entry,
            if not given use uuid1 to generate one

        custom : None, optional
            Currently raises if not 'falsy' and is ignored.

        Returns
        -------
        uid : str
            The uid used to register this data with filestore, can
            be used to retrieve it
        """
        if not self._writable:
            raise RuntimeError("This writer can only write one data entry "
                               "and has already been used")

        if custom:
            raise ValueError("This writer does not support custom")

        if op.exists(self._fpath):
            raise IOError("the requested file {fpath} "
                          "already exist".format(fpath=self._fpath))

        if uid is None:
            uid = str(uuid.uuid1())

        np.save(self._fpath, np.asanyarray(data))
        self._writable = False
        fb = fsc.insert_resource(self.SPEC_NAME, self._fpath, self._f_custom)
        evl = fsc.insert_nugget(fb, uid)

        return evl.event_id


def save_ndarray(data, base_path=None):
    """
    Helper method to mindlessly save a numpy array to disk.

    Defaults to saving files in :path:`~/.fs_cache/YYYY-MM-DD`


    Parameters
    ----------
    data : ndarray
        The data to be saved

    base_path : str, optional
        The base-path to use for saving files.  If not given
        default to `~/.fs_cache`.  Will add a sub-directory for
        each day in this path.
    """
    if base_path is None:
        base_path = op.join(op.expanduser('~'), '.fs_cache',
                            str(datetime.date.today()))
    _make_sure_path_exists(base_path)
    fpath = op.join(base_path, str(uuid.uuid4()) + '.npy')
    with NpyWriter(fpath) as fout:
        eid = fout.add_data(data)

    return eid


if six.PY2:
    # http://stackoverflow.com/a/5032238/380231
    def _make_sure_path_exists(path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
else:
    # technically, this won't work with py3.1, but no one uses that
    def _make_sure_path_exists(path):
        return os.makedirs(path, exist_ok=True)
