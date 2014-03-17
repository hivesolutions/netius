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

import uuid
import types
import struct
import hashlib

import netius.common
import netius.clients

#@todo must change this from here
def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

class TorrentTask(object):
    """
    Describes a task (operation) that is going to be performed
    using the peer to peer mesh network of the torrent protocol.

    Each of the download operations should be able to be described
    by this task object (for latter reference).
    """

    def __init__(self, owner, file_path = None, info_hash = None):
        self.owner = owner
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.peers = []
        if file_path: info = self.load_info(file_path)
        else: info = dict(info_hash = info_hash)
        self.peers_tracker(info)
        print self.peers

    def load_info(self, file_path):
        file = open(file_path, "rb")
        try: data = file.read()
        finally: file.close()
        struct = netius.common.bdecode(data)
        struct["info_hash"] = netius.common.info_hash(struct)
        return struct

    def peers_tracker(self, info):
        announce = info.get("announce", None)
        announce_list = info.get("announce-list", [[announce]])

        for tracker in announce_list:
            tracker_url = tracker[0]
            result = netius.clients.HTTPClient.get_s(
                tracker_url,
                params = dict(
                    info_hash = info["info_hash"],
                    peer_id = self.owner.peer_id,
                    port = "1000",
                    uploaded = self.uploaded,
                    downloaded = self.downloaded,
                    left = self.left,
                    compact = "0"
                ),
                async = False
            )

            data = result["data"]
            if not data: continue

            response = netius.common.bdecode(data)
            peers = response["peers"]

            if type(peers) == types.DictType:
                self.peers = peers
                continue

            peers = [peer for peer in chunks(peers, 6)]
            for peer in peers:
                address, port = struct.unpack("!LH", peer)
                ip = netius.common.addr_to_ip4(address)
                peer = dict(
                    ip = ip,
                    port = port
                )
                self.peers.append(peer)

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
        self.peer_id = self._generate_id()

    def download(self, file_path = None, info_hash = None):
        """
        Starts the "downloading" process of a torrent associated file
        using the defined peer to peer torrent strategy suing either
        the provided torrent path as reference or just the info hash
        of the file that is going to be downloaded.

        Note that if only the info hash is provided a DHT bases strategy
        is going to be used to retrieve the peers list.

        @type file_path: String
        @param file_path: The path to the file that contains the torrent
        information that is going to be used for file processing.
        @type info_hash: String
        @param info_hash: The info hash value of the file that is going
        to be downloaded, may be used for magnet torrents (DHT).
        """

        task = TorrentTask(
            self,
            file_path = file_path,
            info_hash = info_hash
        )

    def _generate_id(self):
        random = str(uuid.uuid4())
        hash = hashlib.sha1(random)
        digest = hash.hexdigest()
        id = "-NE1000-%s" % digest[:12]
        return id

if __name__ == "__main__":
    torrent_client = TorrentClient()
    torrent_client.download("C:\ubuntu.torrent")
