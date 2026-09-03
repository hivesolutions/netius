#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import shutil
import tempfile
import unittest

import netius
import netius.extra
import netius.common

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class FileServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base_path = tempfile.mkdtemp()
        self.hello_path = os.path.join(self.base_path, "hello.txt")
        self._write(self.hello_path, b"Hello World")
        self.large_path = os.path.join(self.base_path, "large.bin")
        self._write(self.large_path, b"L" * (netius.extra.file.BUFFER_SIZE + 1))
        os.mkdir(os.path.join(self.base_path, "sub"))
        os.mkdir(os.path.join(self.base_path, "indexed"))
        self._write(
            os.path.join(self.base_path, "indexed", "index.html"), b"<p>index</p>"
        )
        self.server = netius.extra.FileServer(base_path=self.base_path)
        self.server.on_serve()
        self.connections = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self._close_files()
        self.server.cleanup()
        shutil.rmtree(self.base_path)

    def test_init(self):
        server = netius.extra.FileServer()

        try:
            self.assertEqual(server.base_path, "")
            self.assertEqual(server.style_urls, [])
            self.assertEqual(server.index_files, [])
            self.assertEqual(server.path_regex, [])
            self.assertEqual(server.list_dirs, True)
            self.assertEqual(server.list_engine, "base")
            self.assertEqual(server.cors, False)
            self.assertEqual(server.cache, 0)
            self.assertEqual(server.follow_links, False)
        finally:
            server.cleanup()

    def test_init_values(self):
        server = netius.extra.FileServer(
            base_path="/tmp",
            style_urls=["/style.css"],
            index_files=["index.html"],
            path_regex=[("^legacy/.*", "index.html")],
            list_dirs=False,
            list_engine="apache",
            cors=True,
            cache=60,
            follow_links=True,
        )

        try:
            self.assertEqual(server.base_path, "/tmp")
            self.assertEqual(server.style_urls, ["/style.css"])
            self.assertEqual(server.index_files, ["index.html"])
            self.assertEqual(server.path_regex, [("^legacy/.*", "index.html")])
            self.assertEqual(server.list_dirs, False)
            self.assertEqual(server.list_engine, "apache")
            self.assertEqual(server.cors, True)
            self.assertEqual(server.cache, 60)
            self.assertEqual(server.follow_links, True)
        finally:
            server.cleanup()

    def test_sorter_build(self):
        items = self._make_items()

        items.sort(key=netius.extra.FileServer._sorter_build())

        # with no explicit criteria the directories are grouped before the
        # files and the parent link is always kept as the very first item
        self.assertEqual(self._names(items), ["..", "z-dir", "a.txt", "b.bin"])

    def test_sorter_build_name(self):
        items = self._make_items()

        items.sort(key=netius.extra.FileServer._sorter_build(name="name"))

        # sorting by name ignores the directory grouping, so a file may
        # be placed before a directory, the parent link still comes first
        self.assertEqual(self._names(items), ["..", "a.txt", "b.bin", "z-dir"])

    def test_sorter_build_modified(self):
        items = self._make_items()

        items.sort(key=netius.extra.FileServer._sorter_build(name="modified"))

        self.assertEqual(self._names(items), ["..", "z-dir", "b.bin", "a.txt"])

    def test_sorter_build_size(self):
        items = self._make_items()

        items.sort(key=netius.extra.FileServer._sorter_build(name="size"))

        self.assertEqual(self._names(items), ["..", "z-dir", "b.bin", "a.txt"])

    def test_sorter_build_type(self):
        items = self._make_items()

        items.sort(key=netius.extra.FileServer._sorter_build(name="type"))

        self.assertEqual(self._names(items), ["..", "z-dir", "b.bin", "a.txt"])

    def test_sorter_build_reverse(self):
        items = self._make_items()

        items.sort(key=netius.extra.FileServer._sorter_build(name="name"), reverse=True)

        # the parent link owes its position to a sorting value and not to a
        # special case, so a descending sort moves it to the very last row
        self.assertEqual(self._names(items), ["z-dir", "b.bin", "a.txt", ".."])

    def test_items_normalize(self):
        items = netius.extra.FileServer._items_normalize(
            ["hello.txt", "sub"], self.base_path
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["name"], "hello.txt")
        self.assertEqual(items[0]["is_dir"], False)
        self.assertEqual(items[0]["size"], 11)
        self.assertEqual(items[0]["size_s"], "11 B")
        self.assertEqual(items[0]["type_s"], "text/plain")
        self.assertEqual(items[0]["icon"], netius.extra.file.FILE_SVG)
        self.assertEqual(items[1]["name"], "sub")
        self.assertEqual(items[1]["is_dir"], True)
        self.assertEqual(items[1]["size"], 0)
        self.assertEqual(items[1]["size_s"], "-")
        self.assertEqual(items[1]["type_s"], "Directory")
        self.assertEqual(items[1]["icon"], netius.extra.file.FOLDER_SVG)

    def test_items_normalize_missing(self):
        items = netius.extra.FileServer._items_normalize(
            ["hello.txt", "missing.txt"], self.base_path
        )

        # an item that no longer exists in the file system is silently
        # dropped, as the listing may be built from a stale directory read
        self.assertEqual(self._names(items), ["hello.txt"])

    def test_items_normalize_pad(self):
        items = netius.extra.FileServer._items_normalize(
            ["sub"], self.base_path, pad=True
        )

        self.assertEqual(items[0]["name"], "sub")
        self.assertEqual(items[0]["name_s"], "sub/")

    def test_items_normalize_quote(self):
        self._write(os.path.join(self.base_path, "with space.txt"), b"data")

        items = netius.extra.FileServer._items_normalize(
            ["with space.txt"], self.base_path
        )

        self.assertEqual(items[0]["name_q"], "with%20space.txt")

    def test_gen_dir(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(netius.extra.FileServer, "_gen_dir_apache") as gen_dir:
            netius.extra.FileServer._gen_dir("apache", self.base_path, "/", {})

        # the engine name selects the generator method by name, so that a
        # new engine only requires an extra method to be defined
        self.assertEqual(gen_dir.call_count, 1)
        self.assertEqual(gen_dir.call_args[0][0], self.base_path)

    def test_gen_dir_base(self):
        data = self._gen_dir("base", "/")

        self.assertEqual('<a href="hello.txt">hello.txt</a>' in data, True)
        self.assertEqual('<a href="sub">sub</a>' in data, True)
        self.assertEqual("<title>Index of /</title>" in data, True)
        self.assertEqual(netius.extra.file.FOLDER_SVG in data, True)

        # the root of the served tree has no parent to climb to, so the
        # listing must not offer the relative parent entry
        self.assertEqual('<a href="..">..</a>' in data, False)

    def test_gen_dir_base_parent(self):
        data = self._gen_dir("base", "/sub/")

        self.assertEqual('<a href="..">..</a>' in data, True)

    def test_gen_dir_base_nested(self):
        path = os.path.join(self.base_path, "sub", "deep")
        os.mkdir(path)

        data = self._gen_dir("base", "/sub/deep/", path=path)

        # every element of the path is rendered as its own link, so that
        # any of the parent directories may be reached from the listing
        self.assertEqual('<a href="/">/</a>' in data, True)
        self.assertEqual('<a href="/sub/">sub</a>' in data, True)
        self.assertEqual("<span>/</span>" in data, True)
        self.assertEqual("<span>deep</span>" in data, True)

    def test_gen_dir_base_sort(self):
        data = self._gen_dir("base", "/", query_m=dict(sort=["size"]))

        # the column that is currently sorting the listing is marked as
        # selected and the link of every column flips the direction
        self.assertEqual('class="selected">Size' in data, True)
        self.assertEqual("?sort=size&direction=desc" in data, True)

    def test_gen_dir_base_no_style(self):
        data = self._gen_dir("base", "/", style=False)

        # without style there's no icon to tell a directory apart, so the
        # name of the directory is padded with the separator instead
        self.assertEqual(netius.extra.file.FOLDER_SVG in data, False)
        self.assertEqual('<a href="sub/">sub/</a>' in data, True)

    def test_gen_dir_apache(self):
        data = self._gen_dir("apache", "/")

        self.assertEqual('<a href="hello.txt">hello.txt</a>' in data, True)
        self.assertEqual("<title>Index of /</title>" in data, True)

        # the apache engine always offers the parent entry, even for the
        # root of the served tree, and names it the way apache does
        self.assertEqual('<a href="../">Parent Directory</a>' in data, True)
        self.assertEqual('alt="[PARENTDIR]"' in data, True)

    def test_gen_dir_legacy(self):
        data = self._gen_dir("legacy", "/")

        self.assertEqual('<a href="hello.txt">hello.txt</a>' in data, True)
        self.assertEqual("<title>Index of /</title>" in data, True)

    def test_on_connection_d(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        file = mock.MagicMock()
        connection.file = file

        self.server.on_connection_d(connection)

        # the file descriptor of an interrupted download must be released
        # together with the connection, otherwise it would be leaked
        self.assertEqual(file.close.call_count, 1)
        self.assertEqual(connection.file, None)
        self.assertEqual(connection.range, None)
        self.assertEqual(connection.bytes_p, None)
        self.assertEqual(connection.queue, None)

    def test_on_connection_d_no_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.file = None

        self.server.on_connection_d(connection)

        self.assertEqual(connection.file, None)

    def test_on_stream_d(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        stream = mock.MagicMock()
        file = mock.MagicMock()
        stream.file = file

        self.server.on_stream_d(stream)

        self.assertEqual(file.close.call_count, 1)
        self.assertEqual(stream.file, None)
        self.assertEqual(stream.range, None)
        self.assertEqual(stream.bytes_p, None)
        self.assertEqual(stream.queue, None)

    def test_on_stream_d_no_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        stream = mock.MagicMock()
        stream.file = None

        self.server.on_stream_d(stream)

        self.assertEqual(stream.file, None)

    def test_on_serve(self):
        server = netius.extra.FileServer(base_path=".", cache=30)

        try:
            server.on_serve()

            # the base path is made absolute so that the containment check
            # of every request may be a simple prefix comparison
            self.assertEqual(server.base_path, os.path.abspath("."))
            self.assertEqual(server.cache_d.seconds, 30)
            self.assertEqual(server.path_regex, [])
        finally:
            server.cleanup()

    def test_on_serve_env(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.FileServer()
        server.env = True
        values = dict(
            BASE_PATH=self.base_path,
            STYLE_URLS=["/style.css"],
            INDEX_FILES=["index.html"],
            PATH_REGEX=[("^legacy/.*", "index.html")],
            LIST_DIRS=False,
            LIST_ENGINE="apache",
            CORS=True,
            CACHE=60,
            FOLLOW_LINKS=True,
        )

        try:
            with mock.patch.object(
                server,
                "get_env",
                side_effect=lambda name, default, **kwargs: values.get(name, default),
            ):
                server.on_serve()

            self.assertEqual(server.base_path, self.base_path)
            self.assertEqual(server.style_urls, ["/style.css"])
            self.assertEqual(server.index_files, ["index.html"])
            self.assertEqual(server.list_dirs, False)
            self.assertEqual(server.list_engine, "apache")
            self.assertEqual(server.cors, True)
            self.assertEqual(server.cache, 60)
            self.assertEqual(server.follow_links, True)
        finally:
            server.cleanup()

    def test_on_serve_env_regex(self):
        server = netius.extra.FileServer(base_path=self.base_path)
        server.env = True

        try:
            with netius.conf_override("PATH_REGEX", "^legacy/.*:index.html"):
                server.on_serve()

            # the environment carries the rules as a single string, each rule
            # separated by a semicolon and each pair separated by a colon
            self.assertEqual(len(server.path_regex), 1)
            self.assertEqual(server.path_regex[0][1], "index.html")
            self.assertEqual(server._resolve("legacy/deep/page"), "index.html")
        finally:
            server.cleanup()

    def test_on_data_http(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/hello.txt"))

        kwargs = connection.send_response.call_args[1]

        self.assertEqual(kwargs["code"], 200)
        self.assertEqual(kwargs["headers"]["content-length"], "11")
        self.assertEqual(kwargs["headers"]["content-type"], "text/plain")

    def test_on_data_http_dir(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/sub/"))

        kwargs = connection.send_response.call_args[1]

        self.assertEqual(kwargs["code"], 200)
        self.assertEqual(kwargs["headers"]["content-type"], "text/html")

    def test_on_data_http_no_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/missing.txt"))

        self.assertEqual(connection.send_response.call_args[1]["code"], 404)

    def test_on_data_http_escape(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        # the path is handed over already denormalized so that the guard of
        # the server itself is exercised and not the one of the parser
        self.server.on_data_http(connection, self._make_parser("/../../etc/passwd"))

        # a path that climbs out of the base path may never be served, the
        # security error is reported as an internal server error instead
        self.assertEqual(connection.send_response.call_args[1]["code"], 500)

    def test_on_data_http_sibling(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        parent = os.path.dirname(self.base_path)
        sibling = os.path.basename(self.base_path) + "-backup"
        os.mkdir(os.path.join(parent, sibling))
        self._write(os.path.join(parent, sibling, "secret.txt"), b"secret")

        connection = self._make_connection()

        try:
            self.server.on_data_http(
                connection, self._make_parser("/../%s/secret.txt" % sibling)
            )

            # a directory whose name only starts like the base path is not
            # under it, so reaching into it may never be served either
            self.assertEqual(connection.send_response.call_args[1]["code"], 500)
        finally:
            shutil.rmtree(os.path.join(parent, sibling))

    def test_on_data_http_link(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        outside = tempfile.mkdtemp()

        try:
            self._write(os.path.join(outside, "secret.txt"), b"secret")
            self._link(
                os.path.join(outside, "secret.txt"),
                os.path.join(self.base_path, "link.txt"),
            )

            connection = self._make_connection()

            self.server.on_data_http(connection, self._make_parser("/link.txt"))

            # a link that sits under the base path but points out of it is a
            # way around the containment, so the target of it is what counts
            self.assertEqual(connection.send_response.call_args[1]["code"], 500)

            # the operator may have published through the link on purpose, in
            # which case the server is told to follow it
            self.server.follow_links = True
            connection = self._make_connection()
            self.server.on_data_http(connection, self._make_parser("/link.txt"))

            self.assertEqual(connection.send_response.call_args[1]["code"], 200)
        finally:
            self.server.follow_links = False
            self._close_files()
            shutil.rmtree(outside)

    def test_on_data_http_link_inside(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self._link(self.hello_path, os.path.join(self.base_path, "link.txt"))

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/link.txt"))

        # a link whose target stays under the base path leads nowhere it
        # should not, so it is served as the file that it names
        self.assertEqual(connection.send_response.call_args[1]["code"], 200)
        self.assertEqual(
            connection.send_response.call_args[1]["headers"]["content-length"], "11"
        )

    def test_on_data_http_queue(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.file = mock.MagicMock()
        del connection.queue
        parser = self._make_parser("/hello.txt")

        self.server.on_data_http(connection, parser)

        # a request that arrives while a file is still being sent must be
        # queued, as the connection is not able to multiplex both responses
        self.assertEqual(connection.send_response.call_count, 0)
        self.assertEqual(connection.queue, [parser.get_state.return_value])

    def test_on_data_http_queue_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.file = mock.MagicMock()
        connection.queue = ["pending"]
        parser = self._make_parser("/hello.txt")

        self.server.on_data_http(connection, parser)

        # the queue is kept in order, so that the responses reach the client
        # in the very same sequence as the requests arrived
        self.assertEqual(connection.queue, ["pending", parser.get_state.return_value])

    def test_on_dir_file_redirect(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/sub"))

        kwargs = connection.send_response.call_args[1]

        # a directory is only listed under a path that ends with the
        # separator, otherwise the relative links would be broken
        self.assertEqual(kwargs["code"], 301)
        self.assertEqual(kwargs["headers"]["location"], "/sub/")

    def test_on_dir_file_index(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.index_files = ["index.html"]
        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/indexed/"))

        kwargs = connection.send_response.call_args[1]

        # the index file of the directory replaces the listing, and it's
        # served as a normal file, meaning its own type is used
        self.assertEqual(kwargs["code"], 200)
        self.assertEqual(kwargs["headers"]["content-type"], "text/html")
        self.assertEqual(kwargs["headers"]["content-length"], "12")

    def test_on_dir_file_index_missing(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.index_files = ["missing.html", "index.html"]
        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/indexed/"))

        # the index files are candidates and not requirements, so the first
        # one that exists in the directory is the one to be served
        self.assertEqual(connection.send_response.call_args[1]["code"], 200)
        self.assertEqual(
            connection.send_response.call_args[1]["headers"]["content-length"], "12"
        )

    def test_on_dir_file_index_link(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        outside = tempfile.mkdtemp()

        try:
            self._write(os.path.join(outside, "secret.html"), b"<p>secret</p>")
            self._link(
                os.path.join(outside, "secret.html"),
                os.path.join(self.base_path, "sub", "index.html"),
            )
            self.server.index_files = ["index.html"]

            connection = self._make_connection()

            self.server.on_data_http(connection, self._make_parser("/sub/"))

            # the index file is the one that is opened, so one that is a link
            # out of the base path is refused as the directory itself would be
            self.assertEqual(connection.send_response.call_args[1]["code"], 500)

            # the operator may have published through the link on purpose, in
            # which case the server is told to follow it
            self.server.follow_links = True
            connection = self._make_connection()
            self.server.on_data_http(connection, self._make_parser("/sub/"))

            self.assertEqual(connection.send_response.call_args[1]["code"], 200)
            self.assertEqual(
                connection.send_response.call_args[1]["headers"]["content-length"],
                "13",
            )
        finally:
            self.server.follow_links = False
            self._close_files()
            shutil.rmtree(outside)

    def test_on_dir_file_index_link_inside(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self._link(self.hello_path, os.path.join(self.base_path, "sub", "index.html"))
        self.server.index_files = ["index.html"]

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/sub/"))

        # an index file that links to a file under the base path leads nowhere
        # it should not, so it is served as the file that it names
        self.assertEqual(connection.send_response.call_args[1]["code"], 200)
        self.assertEqual(
            connection.send_response.call_args[1]["headers"]["content-length"], "11"
        )

    def test_on_dir_file_no_list(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.list_dirs = False
        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/sub/"))

        # with the listing disabled a directory is indistinguishable from
        # a resource that does not exist at all
        self.assertEqual(connection.send_response.call_args[1]["code"], 404)

    def test_on_normal_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/hello.txt"))

        kwargs = connection.send_response.call_args[1]

        self.assertEqual(kwargs["code"], 200)
        self.assertEqual(kwargs["headers"]["accept-ranges"], "bytes")
        self.assertEqual(kwargs["final"], False)
        self.assertEqual(kwargs["callback"], self.server._file_send)
        self.assertEqual(connection.range, (0, 10))
        self.assertEqual(connection.bytes_p, 11)

    def test_on_normal_file_partial(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        parser = self._make_parser("/hello.txt", headers=dict(range="bytes=2-5"))

        self.server.on_data_http(connection, parser)

        kwargs = connection.send_response.call_args[1]

        self.assertEqual(kwargs["code"], 206)
        self.assertEqual(kwargs["headers"]["content-range"], "bytes 2-5/11")
        self.assertEqual(kwargs["headers"]["content-length"], "4")
        self.assertEqual(connection.range, (2, 5))
        self.assertEqual(connection.bytes_p, 4)

        # a partial response describes the range that it carries and so it
        # must not advertise the range support header
        self.assertEqual("accept-ranges" in kwargs["headers"], False)

    def test_on_normal_file_partial_open(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        parser = self._make_parser("/hello.txt", headers=dict(range="bytes=4-"))

        self.server.on_data_http(connection, parser)

        # an open ended range runs until the last byte of the file, the
        # very same applying to a range with no start position
        self.assertEqual(connection.range, (4, 10))
        self.assertEqual(connection.bytes_p, 7)

    def test_on_normal_file_cors(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.cors = True
        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/hello.txt"))

        headers = connection.send_response.call_args[1]["headers"]

        self.assertEqual(headers["access-control-allow-origin"], "*")

    def test_on_normal_file_cache(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.FileServer(base_path=self.base_path, cache=60)
        server.on_serve()
        connection = self._make_connection()

        try:
            server.on_data_http(connection, self._make_parser("/hello.txt"))
        finally:
            server.cleanup()

        headers = connection.send_response.call_args[1]["headers"]

        self.assertEqual(headers["cache-control"], "public, max-age=60")
        self.assertEqual(headers["expires"].endswith("GMT"), True)

    def test_on_normal_file_etag(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_data_http(connection, self._make_parser("/hello.txt"))

        etag = connection.send_response.call_args[1]["headers"]["etag"]

        self.assertEqual(etag.startswith("netius-"), True)

    def test_on_no_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_no_file(connection)

        kwargs = connection.send_response.call_args[1]

        self.assertEqual(kwargs["code"], 404)
        self.assertEqual(kwargs["headers"], dict(connection="close"))
        self.assertEqual(kwargs["callback"], self.server._file_close)

    def test_on_exception_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        self.server.on_exception_file(connection, netius.SecurityError("Invalid path"))

        kwargs = connection.send_response.call_args[1]

        self.assertEqual(kwargs["code"], 500)
        self.assertEqual(b"Invalid path" in kwargs["data"], True)
        self.assertEqual(kwargs["callback"], self.server._file_close)

    def test_on_not_modified(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        etag = "netius-%.2f" % os.path.getmtime(self.hello_path)
        parser = self._make_parser("/hello.txt", headers={"if-none-match": etag})

        self.server.on_data_http(connection, parser)

        kwargs = connection.send_response.call_args[1]

        # an unchanged resource is answered with an empty body, the encoding
        # must be reset so that no compression is applied to it
        self.assertEqual(kwargs["code"], 304)
        self.assertEqual(kwargs["data"], "")
        self.assertEqual(
            connection.set_encoding.call_args[0], (netius.common.PLAIN_ENCODING,)
        )

    def test_next_queue(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.queue = ["first", "second"]

        with mock.patch.object(netius.common.HTTPParser, "mock") as parser:
            with mock.patch.object(self.server, "on_data_http") as on_data_http:
                self.server._next_queue(connection)

        # only the head of the queue is processed, the remaining requests
        # wait for the current one to release the connection again
        self.assertEqual(connection.queue, ["second"])
        self.assertEqual(parser.call_args[0][1], "first")
        self.assertEqual(on_data_http.call_count, 1)

    def test_next_queue_empty(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.queue = []

        with mock.patch.object(self.server, "on_data_http") as on_data_http:
            self.server._next_queue(connection)

        self.assertEqual(on_data_http.call_count, 0)

    def test_next_queue_unset(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        del connection.queue

        with mock.patch.object(self.server, "on_data_http") as on_data_http:
            self.server._next_queue(connection)

        self.assertEqual(on_data_http.call_count, 0)

    def test_file_send(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (0, 10))

        self.server._file_send(connection)

        args, kwargs = connection.send_part.call_args

        # the whole file fits a single buffer and so the sending is final,
        # the finish callback releases the file and flushes the connection
        self.assertEqual(args[0], b"Hello World")
        self.assertEqual(kwargs["callback"], self.server._file_finish)
        self.assertEqual(connection.bytes_p, 0)

    def test_file_send_partial(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (2, 5))

        self.server._file_send(connection)

        # only the bytes of the requested range are read from the file, the
        # remaining contents are never sent to the client
        self.assertEqual(connection.send_part.call_args[0][0], b"llo ")

    def test_file_send_buffer(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        size = netius.extra.file.BUFFER_SIZE + 1
        connection = self._make_file_connection(self.large_path, (0, size - 1))

        self.server._file_send(connection)

        args, kwargs = connection.send_part.call_args

        # a file larger than the buffer is sent in multiple parts, each one
        # scheduling the next one through the very same callback
        self.assertEqual(len(args[0]), netius.extra.file.BUFFER_SIZE)
        self.assertEqual(kwargs["callback"], self.server._file_send)
        self.assertEqual(connection.bytes_p, 1)

        self.server._file_send(connection)

        args, kwargs = connection.send_part.call_args

        self.assertEqual(len(args[0]), 1)
        self.assertEqual(kwargs["callback"], self.server._file_finish)
        self.assertEqual(connection.bytes_p, 0)

    def test_file_finish(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (0, 10))
        connection.parser.keep_alive = True

        self.server._file_finish(connection)

        # the file state of the connection is released so that a following
        # request is not mistaken for a download still in progress
        self.assertEqual(connection.file, None)
        self.assertEqual(connection.range, None)
        self.assertEqual(connection.bytes_p, None)
        self.assertEqual(connection.flush_s.call_args[1]["callback"], None)

    def test_file_finish_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (0, 10))
        connection.parser.keep_alive = False

        self.server._file_finish(connection)

        # a connection that is not kept alive is closed right after the
        # contents of the file reach the client
        self.assertEqual(
            connection.flush_s.call_args[1]["callback"], self.server._file_close
        )

    def test_file_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()

        self.server._file_close(connection)

        self.assertEqual(connection.close.call_args[1], dict(flush=True))

    def test_file_check_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.parser.keep_alive = False

        self.server._file_check_close(connection)

        self.assertEqual(connection.close.call_count, 1)

    def test_file_check_close_keep_alive(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.parser.keep_alive = True

        self.server._file_check_close(connection)

        self.assertEqual(connection.close.call_count, 0)

    def test_resolve(self):
        self.server.path_regex = [("^legacy/.*", "index.html")]
        self.server._build_regex()

        self.assertEqual(self.server._resolve("legacy/deep/page"), "index.html")
        self.assertEqual(self.server._resolve("assets/logo.png"), "assets/logo.png")

    def test_build_regex(self):
        self.server.path_regex = [("^legacy/.*", "index.html")]

        self.server._build_regex()

        # the rules are compiled once at boot time, as they are evaluated
        # for every single request that reaches the server
        self.assertEqual(len(self.server.path_regex), 1)
        self.assertEqual(self.server.path_regex[0][0].pattern, "^legacy/.*")
        self.assertEqual(self.server.path_regex[0][1], "index.html")

    def test_resolve_regex(self):
        self.server.path_regex = [("^legacy/.*", "index.html")]
        self.server._build_regex()

        self.assertEqual(
            self.server._resolve_regex("legacy/deep/page"), ("index.html", True)
        )
        self.assertEqual(
            self.server._resolve_regex("assets/logo.png"), ("assets/logo.png", False)
        )

    def test_is_sub(self):
        # the base path itself and anything under it are contained, while
        # the parent and a sibling whose name only starts like it are not
        self.assertEqual(self.server._is_sub(self.server.base_path), True)
        self.assertEqual(self.server._is_sub(self.hello_path), True)
        self.assertEqual(
            self.server._is_sub(os.path.dirname(self.server.base_path)), False
        )
        self.assertEqual(self.server._is_sub(self.server.base_path + "-backup"), False)

    def test_is_sub_link(self):
        outside = tempfile.mkdtemp()

        try:
            self._write(os.path.join(outside, "secret.txt"), b"secret")
            self._link(
                os.path.join(outside, "secret.txt"),
                os.path.join(self.base_path, "link.txt"),
            )

            # a link is judged by the target of it, unless the server is told
            # to follow it, in which case the name under the base path is enough
            self.assertEqual(
                self.server._is_sub(os.path.join(self.base_path, "link.txt")), False
            )

            self.server.follow_links = True

            self.assertEqual(
                self.server._is_sub(os.path.join(self.base_path, "link.txt")), True
            )
        finally:
            self.server.follow_links = False
            shutil.rmtree(outside)

    def _make_items(self):
        return [
            dict(
                name="a.txt",
                is_dir=False,
                modified="2022-01-01 00:00",
                size=30,
                type="text/plain",
            ),
            dict(
                name="z-dir",
                is_dir=True,
                modified="2020-01-01 00:00",
                size=0,
                type="Directory",
            ),
            dict(
                name="..",
                is_dir=True,
                modified="2019-01-01 00:00",
                size=0,
                type="Directory",
            ),
            dict(
                name="b.bin",
                is_dir=False,
                modified="2021-01-01 00:00",
                size=10,
                type="application/octet-stream",
            ),
        ]

    def _link(self, source, target):
        # the creation of a link is reserved to a privileged user under
        # some systems, in which case the case has nothing to run
        try:
            os.symlink(source, target)
        except (AttributeError, NotImplementedError, OSError):
            self.skipTest("Skipping test: symbolic links unavailable")

    def _make_connection(self):
        connection = mock.MagicMock()
        # removes the dynamic attributes that the server checks through
        # hasattr, otherwise they would always be reported as present
        del connection.file
        del connection.queue
        self.connections.append(connection)
        return connection

    def _make_file_connection(self, path, range):
        connection = self._make_connection()
        connection.file = open(path, "rb")
        connection.file.seek(range[0])
        connection.range = range
        connection.bytes_p = range[1] - range[0] + 1
        return connection

    def _make_parser(self, path="/", headers=None):
        parser = mock.MagicMock()
        parser.get_path.return_value = path
        parser.get_query.return_value = ""
        parser.headers = {} if headers == None else headers
        parser.keep_alive = False
        return parser

    def _gen_dir(self, engine, path_v, query_m=None, style=True, path=None):
        path = self.base_path if path == None else path
        query_m = {} if query_m == None else query_m
        return "".join(
            netius.extra.FileServer._gen_dir(engine, path, path_v, query_m, style=style)
        )

    def _names(self, items):
        return [item["name"] for item in items]

    def _close_files(self):
        # the file of a connection is only released once the sending of the
        # response is finished, so an interrupted one has to be closed by
        # hand, otherwise the removal of the directory fails under Windows
        for connection in self.connections:
            file = getattr(connection, "file", None)
            if not file:
                continue
            file.close()

    def _write(self, path, data):
        file = open(path, "wb")
        try:
            file.write(data)
        finally:
            file.close()
