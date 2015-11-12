#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2015 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by the Apache
# Foundation, either version 2.0 of the License, or (at your option) any
# later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Apache License for more details.
#
# You should have received a copy of the Apache License along with
# Hive Netius System. If not, see <http://www.apache.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2015 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import copy
import math
import uuid
import time
import struct
import hashlib

import netius.common
import netius.clients

REFRESH_TIME = 30.0
""" The default time in between refresh call in the torrent task
each refresh operation should perform some operations (eg: DHT
refresh, tracker re-retrieval, etc) """

ID_STRING = "NE1000"
""" Text value that is going to be used to identify the agent
of torrent against the other peers, should be a join of both
the abbreviation of the agent name and version """

BLOCK_SIZE = 16384
""" The typical size of block that is going to be retrieved
using the current torrent infra-structure, this value conditions
most of the torrent operations and should be defined carefully """

THRESHOLD_END = 10485760
""" The threshold value from which the task is considered to be
under the ending stage, from this stage on a new strategy for the
download may apply as it is more difficult to get blocks """

class Pieces(netius.Observable):
    """
    Class that represents the logical structure of a file that is
    divided into pieces and blocks as a hierarchy, this class is
    responsible for the management of the data structures of such
    data storage model.

    A piece is considered to be the basic unit of a torrent file
    and each piece is composed by multiple blocks, note that the
    number of blocks is fixed for all the pieces of a file.
    """

    def __init__(self, number_pieces, number_blocks):
        netius.Observable.__init__(self)

        self.number_pieces = number_pieces
        self.number_blocks = number_blocks
        self.bitfield = [True for _index in range(number_pieces)]
        self.mask = [True for _index in range(number_pieces * number_blocks)]

    def piece(self, index):
        return self.bitfield[index]

    def block(self, index, begin):
        base = index * self.number_blocks
        block_index = begin // BLOCK_SIZE
        return self.mask[base + block_index]

    def pop_block(self, bitfield, mark = True):
        index = 0
        result = self._and(bitfield, self.bitfield)
        for bit in result:
            if bit == True: break
            index += 1

        if index == len(result): return None

        begin = self.update_block(index, mark = mark)
        return (index, begin)

    def push_block(self, index, begin):
        self.mark_block(index, begin, value = True)

    def mark_block(self, index, begin, value = False):
        base = index * self.number_blocks
        block_index = begin // BLOCK_SIZE
        self.mask[base + block_index] = value
        self.trigger("block", self, index, begin)
        self.update_piece(index)

    def update_block(self, index, mark = True):
        base = index * self.number_blocks

        for block_index in range(self.number_blocks):
            state = self.mask[base + block_index]
            if state == True: break

        begin = block_index * BLOCK_SIZE
        if mark: self.mark_block(index, begin)
        return begin

    def update_piece(self, index):
        base = index * self.number_blocks
        piece_state = False

        for block_index in range(self.number_blocks):
            state = self.mask[base + block_index]
            if state == False: continue
            piece_state = True
            break

        self.bitfield[index] = piece_state
        if piece_state == True: return

        self.trigger("piece", self, index)

        for bit in self.bitfield:
            if bit == True: return

        self.trigger("complete", self)

    def _and(self, first, second):
        result = []
        for _first, _second in zip(first, second):
            if _first and _second: value = True
            else: value = False
            result.append(value)
        return result

class TorrentTask(netius.Observable):
    """
    Describes a task (operation) that is going to be performed
    using the peer to peer mesh network of the torrent protocol.

    Each of the download operations should be able to be described
    by this task object (for latter reference).

    This should be considered the main interface to interact from
    a developer point of view, as such the methods should represent
    a proper easily described interface.
    """

    def __init__(self, owner, target_path, torrent_path = None, info_hash = None):
        netius.Observable.__init__(self)

        self.owner = owner
        self.target_path = target_path
        self.torrent_path = torrent_path
        self.info_hash = info_hash
        self.start = time.time()
        self.uploaded = 0
        self.downloaded = 0
        self.unchoked = 0
        self.next_refresh = self.start + REFRESH_TIME
        self.connections = []
        self.peers = []
        self.peers_m = {}

    def load(self):
        if self.torrent_path: self.info = self.load_info(self.torrent_path)
        else: self.info = dict(info_hash = self.info_hash)

        self.pieces_tracker()
        self.peers_dht()
        self.peers_tracker()

        self.load_file()
        self.load_pieces()

    def unload(self):
        self.owner = None
        self.unload_file()
        self.unload_pieces()
        self.disconnect_peers()

    def on_close(self, connection):
        is_unchoked = connection.choked == netius.clients.UNCHOKED
        self.connections.remove(connection)
        self.unchoked -= 1 if is_unchoked else 0

    def ticks(self):
        if time.time() < self.next_refresh: return
        self.refresh()

    def refresh(self):
        self.peers_dht()
        self.peers_tracker()
        self.connect_peers()
        self.next_refresh = time.time() + REFRESH_TIME
        self.trigger("refresh", self)

    def on_choked(self, connection):
        self.unchoked -= 1

    def on_unchoked(self, connection):
        self.unchoked += 1

    def on_block(self, pieces, index, begin):
        self.trigger("block", self, index, begin)

    def on_piece(self, pieces, index):
        self.verify_piece(index)
        self.trigger("piece", self, index)

    def on_complete(self, pieces):
        self.trigger("complete", self)

    def on_dht(self, response):
        # verifies if the response is valid and in case it's not
        # returns immediately to avoid any erroneous parsing
        if not response: return

        # retrieves the payload for the response and then uses it
        # to retrieves the nodes part of the response for parsing
        # of the peers that are going to be added (to the task)
        payload = response.get_payload()
        nodes = payload.get("nodes", "")

        # creates the list that will hold the final set of peers
        # parsed from the nodes string, this is going to be used
        # to extend the list of peers in the task
        peers = []

        # splits the current nodes list into a set of chunks of
        # a pre-defined size and then iterates over all of them
        # creating the proper peer dictionary for each of them
        chunks = [chunk for chunk in netius.common.chunks(nodes, 26)]
        for chunk in chunks:
            chunk = netius.legacy.bytes(chunk)
            peer_id, address, port = struct.unpack("!20sLH", chunk)
            ip = netius.common.addr_to_ip4(address)
            peer = dict(id = peer_id, ip = ip, port = port)
            peers.append(peer)

        # in case no valid peers have been parsed there's no need
        # to continue with the processing, nothing to be done
        if not peers: return

        # extends the currently defined peers list in the current
        # torrent task with the ones that have been discovered
        self.extend_peers(peers)

        # retrieves the reference to the host id from the request
        # that originated the current response and then converts it
        # into the proper string representation to be used in logging
        request = response.request
        host = request.host

        # prints a debug message about the peer loading that has just occurred, this
        # may be used for the purpose of development (and traceability)
        self.owner.debug("Received %d peers from DHT peer '%s'" % (len(peers), host))

    def on_tracker(self, client, parser, result):
        # extracts the data (string) contents of the http response and in case
        # there're none of them continues the loop as there's nothing to be
        # processed from this tracker response (invalid response)
        data = result["data"]
        if not data: return

        # tries to decode the provided data from the tracker using the bencoder
        # and extracts the peers part of the message to be processed
        response = netius.common.bdecode(data)
        peers = response["peers"]

        # verifies if the provided peers part is not compact (already a dictionary)
        # if that's the case there's nothing remaining to be done, otherwise extra
        # processing must be done to
        if type(peers) == dict: self.extend_peers(peers)

        # need to normalize the peer structure by decoding the peers string into a
        # set of address port sub strings (as defined in torrent specification)
        else:
            peers = [peer for peer in netius.common.chunks(peers, 6)]
            for peer in peers:
                peer = netius.legacy.bytes(peer)
                address, port = struct.unpack("!LH", peer)
                ip = netius.common.addr_to_ip4(address)
                peer = dict(ip = ip, port = port)
                self.add_peer(peer)

        # prints a debug message about the peer loading that has just occurred, this
        # may be used for the purpose of development (and traceability)
        self.owner.debug("Received %d peers from '%s'" % (len(peers), parser.owner.base))

        # refreshes the connection with the peers because new peers have been added
        # to the current task and there may be new connections pending
        self.connect_peers()

    def load_info(self, torrent_path):
        file = open(torrent_path, "rb")
        try: data = file.read()
        finally: file.close()

        struct = netius.common.bdecode(data)
        struct["info_hash"] = self.info_hash = netius.common.info_hash(struct)
        return struct

    def load_file(self):
        size = self.info["length"]
        name = self.info["info"]["name"]
        is_dir = os.path.isdir(self.target_path)
        if is_dir: self.target_path = os.path.join(self.target_path, name)
        self.file = open(self.target_path, "wb")
        self.file.seek(size - 1)
        self.file.write(b"\0")
        self.file.flush()

    def unload_file(self):
        if not self.file: return
        self.file.close()
        self.file = None

    def load_pieces(self):
        number_pieces = self.info["number_pieces"]
        number_blocks = self.info["number_blocks"]
        self.requested = Pieces(number_pieces, number_blocks)
        self.stored = Pieces(number_pieces, number_blocks)
        self.stored.bind("block", self.on_block)
        self.stored.bind("piece", self.on_piece)
        self.stored.bind("complete", self.on_complete)

    def unload_pieces(self):
        if self.requested: self.requested.destroy()
        if self.stored: self.stored.destroy()
        self.requested = None
        self.stored = None

    def pieces_tracker(self):
        info = self.info.get("info", {})
        pieces = info.get("pieces", "")
        length = info.get("length", None)
        piece_length = info.get("piece length", 1)
        number_blocks = math.ceil(float(piece_length) / float(BLOCK_SIZE))
        number_blocks = int(number_blocks)
        pieces_l = [piece for piece in netius.common.chunks(pieces, 20)]
        pieces_count = len(pieces_l)
        self.info["pieces"] = pieces_l
        self.info["length"] = length or pieces_count * piece_length
        self.info["number_pieces"] = pieces_count
        self.info["number_blocks"] = number_blocks

    def set_data(self, data, index, begin):
        # retrieves the current status of the block in the stored
        # pieces structure and in case it's already stored returns
        # immediately as this is a duplicated block setting, possible
        # in the last part of the file retrieval (end game)
        block = self.stored.block(index, begin)
        if not block: return

        # retrieves the size of a piece and uses that value together
        # with the block begin offset value to seek the proper file position
        # and then writes the received data under that position, flushing
        # the file contents afterwards to avoid file corruption
        piece_length = self.info["info"]["piece length"]
        self.file.seek(index * piece_length + begin)
        self.file.write(data)
        self.file.flush()

        # increments the amount of downloaded bytes for the task and then
        # marks the current block as stored so that no other equivalent
        # operation is performed (avoiding duplicated operations)
        self.downloaded += len(data)
        self.stored.mark_block(index, begin)

    def set_dht(self, peer_t, port):
        # tries to retrieve the peer associated with the provided peer tuple
        # and in case it succeeds sets the proper DHT (port) value in the peer
        # so that it may latter be used for DHT based operations
        peer = self.peers_m.get(peer_t, None)
        if not peer: return
        peer["dht"] = port

    def peers_dht(self):
        if not self.info_hash: return
        for peer in self.peers:
            port = peer.get("dht", None)
            if not port: continue
            host = peer["ip"]
            self.owner.dht_client.get_peers(
                host = host,
                port = port,
                peer_id = self.owner.peer_id,
                info_hash = self.info_hash,
                callback = self.on_dht
            )
            self.owner.debug("Requested peers from DHT peer '%s'" % host)

    def peers_tracker(self):
        """
        Tries to retrieve as much information as possible about the
        peers from the currently loaded tracker information.

        It's possible that no tracker information exits for the current
        task and for such situations no state change will occur.
        """

        # retrieves both the announce and the announce list structure from
        # the current info dictionary and uses both of them to create the
        # final list containing the various addresses of trackers, then
        # iterates over each of the trackers to retrieve the information
        # about the various peers associated with the torrent file
        announce = self.info.get("announce", None)
        announce_list = self.info.get("announce-list", [[announce]])
        for tracker in announce_list:
            # retrieves the first element of the tracker structure as the
            # url of it and then verifies that it references an http based
            # tracker (as that's the only one supported)
            tracker_url = tracker[0]
            is_http = tracker_url.startswith(("http://", "https://"))
            if not is_http: continue

            # runs the get http retrieval call (blocking call) so that it's
            # possible to retrieve the contents for the announce of the tracker
            # this is an asynchronous call and the on tracker callback will be
            # called at the end of the process with the message
            self.owner.http_client.get(
                tracker_url,
                params = dict(
                    info_hash = self.info_hash,
                    peer_id = self.owner.peer_id,
                    port = 6881,
                    uploaded = self.uploaded,
                    downloaded = self.downloaded,
                    left = self.left(),
                    compact = 1,
                    no_peer_id = 0,
                    event = "started",
                    numwant = 50
                ),
                on_result = self.on_tracker
            )

            # prints a debug message about the request for peer that was just
            # performed in order to provide some debugging information
            self.owner.debug("Requested peers using '%s'" % tracker_url)

    def connect_peers(self):
        for peer in self.peers: self.connect_peer(peer)

    def disconnect_peers(self):
        connections = copy.copy(self.connections)
        for connection in connections: connection.close(flush = True)

    def connect_peer(self, peer):
        if not peer["new"]: return
        peer["new"] = False
        connection = self.owner.client.peer(self, peer["ip"], peer["port"])
        self.connections.append(connection)
        connection.bind("close", self.on_close)
        connection.bind("choked", self.on_choked)
        connection.bind("unchoked", self.on_unchoked)

    def info_string(self):
        return "==== STATUS ====\n" +\
            "peers       := %d\n" % len(self.peers) +\
            "connections := %d\n" % len(self.connections) +\
            "choked      := %d\n" % (len(self.connections) - self.unchoked) +\
            "unchoked    := %d\n" % self.unchoked +\
            "percent     := %.2f % %\n" % self.percent() +\
            "speed       := %s/s" % self.speed_s()

    def left(self):
        size = self.info["length"]
        return size - self.downloaded

    def speed(self):
        """
        Retrieves a float number representing the global speed
        of the task in bytes per second, this value is computed
        using the original creation time of the task and so it
        may not represent the most accurate speedup.

        @rtype: float
        @return: The current speed of download, defined as bytes
        per second from the original task creation time.
        """

        current = time.time()
        delta = current - self.start
        bytes_second = self.downloaded / delta
        return bytes_second

    def speed_s(self):
        return netius.common.size_round_unit(
            self.speed(),
            space = True,
            reduce = False
        )

    def percent(self):
        size = self.info["length"]
        return float(self.downloaded) / float(size) * 100.0

    def pop_block(self, bitfield):
        left = self.left()
        is_end = left < THRESHOLD_END
        structure = self.stored if is_end else self.requested
        if not structure: return None
        return structure.pop_block(bitfield, mark = not is_end)

    def push_block(self, index, begin):
        if not self.requested: return
        self.requested.push_block(index, begin)

    def verify_piece(self, index):
        file = open(self.target_path, "rb")
        try: self._verify_piece(index, file)
        finally: file.close()

    def extend_peers(self, peers):
        for peer in peers: self.add_peer(peer)

    def add_peer(self, peer):
        peer_t = (peer["ip"], peer["port"])
        if peer_t in self.peers_m: return
        peer["time"] = time.time()
        peer["new"] = True
        self.peers_m[peer_t] = peer
        self.peers.append(peer)

    def remove_peer(self, peer):
        peer_t = (peer["ip"], peer["port"])
        if not peer_t in self.peers_m: return
        del self.peers_m[peer_t]
        self.peers.remove(peer)

    def _verify_piece(self, index, file):
        piece = self.info["pieces"][index]
        piece_length = self.info["info"]["piece length"]
        file = open(self.target_path, "rb")
        file.seek(index * piece_length)
        pending = piece_length
        hash = hashlib.sha1()
        while True:
            if pending == 0: break
            count = BLOCK_SIZE if pending > BLOCK_SIZE else pending
            data = file.read(count)
            hash.update(data)
            pending -= count
        digest = hash.digest()
        piece = netius.legacy.bytes(piece)
        if digest == piece: return
        raise netius.DataError("Verifying piece index '%d'" % index)

class TorrentServer(netius.ContainerServer):

    def __init__(self, *args, **kwargs):
        netius.ContainerServer.__init__(self, *args, **kwargs)
        self.peer_id = self._generate_id()
        self.client = netius.clients.TorrentClient(
            thread = False,
            *args,
            **kwargs
        )
        self.http_client = netius.clients.HTTPClient(
            thread = False,
            *args,
            **kwargs
        )
        self.dht_client = netius.clients.DHTClient(
            thread = False,
            *args,
            **kwargs
        )
        self.tasks = []
        self.add_base(self.client)
        self.add_base(self.http_client)
        self.add_base(self.dht_client)

    def cleanup(self):
        netius.ContainerServer.cleanup(self)
        self.cleanup_tasks()
        self.client.destroy()

    def ticks(self):
        netius.ContainerServer.ticks(self)
        for task in self.tasks: task.ticks()

    def download(self, target_path, torrent_path = None, info_hash = None, close = False):
        """
        Starts the "downloading" process of a torrent associated file
        using the defined peer to peer torrent strategy suing either
        the provided torrent path as reference or just the info hash
        of the file that is going to be downloaded.

        Note that if only the info hash is provided a DHT bases strategy
        is going to be used to retrieve the peers list.

        The returned value is the task entity representing the newly created
        task for the downloading of the requested file, this object may be
        used for the operations and listening of events.

        @type target_path: String
        @param target_path: The path to the file that will be used to store
        the binary information resulting from the download, this file may also
        be used to store some temporary information on state of download.
        @type torrent_path: String
        @param torrent_path: The path to the file that contains the torrent
        information that is going to be used for file processing.
        @type info_hash: String
        @param info_hash: The info hash value of the file that is going
        to be downloaded, may be used for magnet torrents (DHT).
        @type close: bool
        @param close: If the server infra-structure should be close (process ends)
        at the end of the download, this is not the default behavior (multiple download).
        @rtype: TorrentTask
        @return: The torrent task object that represents the task that has been
        created for downloading of the requested file.
        """

        def on_complete(task):
            owner = task.owner
            self.remove_task(task)
            if close: owner.close()

        task = TorrentTask(
            self,
            target_path,
            torrent_path = torrent_path,
            info_hash = info_hash
        )
        task.load()
        task.connect_peers()
        task.bind("complete", on_complete)
        self.tasks.append(task)
        return task

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        task.unload()
        self.tasks.remove(task)

    def cleanup_tasks(self):
        tasks = copy.copy(self.tasks)
        for task in tasks: self.remove_task(task)

    def _generate_id(self):
        random = str(uuid.uuid4())
        random = netius.legacy.bytes(random)
        hash = hashlib.sha1(random)
        digest = hash.hexdigest()
        id = "-%s-%s" % (ID_STRING, digest[:12])
        return id

if __name__ == "__main__":
    import logging

    def on_start(server):
        task = server.download("C:/", "C:/ubuntu.torrent", close = True)
        task.bind("piece", on_piece)
        task.bind("complete", on_complete)

    def on_piece(task, index):
        percent = task.percent()
        speed_s = task.speed_s()
        left = task.left()
        percent = int(percent)
        print(task.info_string())
        print("[%d%%] - %d bytes (%s/s)" % (percent, left, speed_s))

    def on_complete(task):
        print("Download completed")

    server = TorrentServer(level = logging.DEBUG)
    server.bind("start", on_start)
    server.serve(env = True)
