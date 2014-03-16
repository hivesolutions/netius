#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import netius.common

class TorrentClient(netius.StreamClient):
    """
    Implementation of the torrent protocol, able to download
    and seed files across a peer to peer mesh network.

    The client provides a series of top level methods that
    provide the main interface with the system.

    The current implementation support both a torrent file
    (using trackers) strategy and also a DHT (distributed
    has table) strategy for completely decentralized usage.
    """

    def __init__(self, auto_close = False, *args, **kwargs):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.auto_close = auto_close

    def download(self, file_path = None, info_hash = None):
        """
        Starts the "downloading" process of a torrent associated file
        using the defined peer to peer torrent strategy suing either
        the provided torrent path as reference or just the info hash
        of the file that is going to be downloaded.

        Note that if only the info hash is provided a DHT bases strategy
        is going to be used to retrieve the peers list.
        """

        if file_path: info = self.load_info(file_path)
        else: info = dict(info_hash = info_hash)

        import pprint
        pprint.pprint(info)

    def load_info(self, file_path):
        file = open(file_path, "rb")
        try: data = file.read()
        finally: file.close()
        struct = netius.common.bdecode(data)
        struct["info_hash"] = netius.common.info_hash(struct)
        return struct

if __name__ == "__main__":
    torrent_client = TorrentClient()
    torrent_client.download("C:\Users\joamag\Downloads\ubuntu-12.04.4-alternate-amd64.iso.torrent")
