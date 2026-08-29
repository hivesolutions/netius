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
import gzip
import shutil
import tempfile
import unittest

import netius.common

from netius.common import geo


class GeoResolverTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()
        self.downloads = []
        self.original = geo.GeoResolver.__dict__["_download_db"]
        self.original_try = geo.GeoResolver.__dict__["_try_db"]
        self.db = geo.GeoResolver._db

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        geo.GeoResolver._download_db = self.original
        geo.GeoResolver._try_db = self.original_try
        geo.GeoResolver._db = self.db
        shutil.rmtree(self.base)

    def test_resolve(self):
        geo.GeoResolver._db = dict(a=dict(city=dict(names=dict(en="Lisbon"))))

        # the resolution is delegated to the database, the simplified mode
        # flattening the names of the entry into a single one
        result = geo.GeoResolver.resolve("a")
        self.assertEqual(result["city"]["name"], "Lisbon")

    def test_resolve_no_db(self):
        geo.GeoResolver._db = None
        self._patch_download()

        # with no database available at all the resolution reports no value
        # rather than raising, as the feature is an optional one
        self.assertEqual(geo.GeoResolver.resolve("a"), None)

    def test_resolve_full(self):
        geo.GeoResolver._db = dict(a=dict(city=dict(names=dict(en="Lisbon"))))

        # the complete result is served when the simplification is not asked
        # for, so that a caller may read the values that it would drop
        result = geo.GeoResolver.resolve("a", simplified=False)
        self.assertEqual(result["city"]["names"]["en"], "Lisbon")

    def test__get_db_cached(self):
        geo.GeoResolver._db = "database"

        # a database that has already been opened is served from the cache,
        # so that the search for the file of it happens only once
        self.assertEqual(geo.GeoResolver._get_db(), "database")

    def test__try_all(self):
        tried = self._patch_try(found=False)

        self.assertEqual(geo.GeoResolver._try_all(), None)

        # the prefixes are walked in the order that they are declared and the
        # download is only attempted once none of them holds the database
        expected = [
            (prefix + geo.GeoResolver.DB_NAME, False)
            for prefix in geo.GeoResolver.PREFIXES
        ]
        expected.append((geo.GeoResolver.DB_NAME, True))
        self.assertEqual(tried, expected)

    def test__try_all_found(self):
        tried = self._patch_try(found=True)

        # the first prefix that holds the database ends the search, so that
        # no further prefix is looked at and no download is attempted
        self.assertEqual(geo.GeoResolver._try_all(), geo.GeoResolver.DB_NAME)
        self.assertEqual(len(tried), 1)

    def test__simplify(self):
        result = geo.GeoResolver._simplify(
            dict(
                city=dict(names=dict(en="Lisbon", pt="Lisboa")),
                postal=dict(code="1000"),
            )
        )

        # only the names that the model considers valid are kept, and the
        # localized names of each of them collapse into a single one
        self.assertEqual(result["city"]["name"], "Lisbon")
        self.assertEqual("names" in result["city"], False)
        self.assertEqual("postal" in result, False)

    def test__simplify_empty(self):
        # a result that carries no value is returned as it is, so that the
        # absence of a resolution is not confused with an empty one
        self.assertEqual(geo.GeoResolver._simplify(None), None)

    def test__try_db(self):
        path = os.path.join(self.base, "db.mmdb")
        self._store(path, b"database")

        # a database that is already in place is used as it is, with no
        # download being attempted for it
        self._patch_download()
        self.assertEqual(geo.GeoResolver._try_db(path=path), path)
        self.assertEqual(self.downloads, [])

    def test__try_db_missing(self):
        path = os.path.join(self.base, "missing.mmdb")
        self._patch_download()

        # a database that is absent is not downloaded unless the download is
        # asked for, the absence being reported instead
        self.assertEqual(geo.GeoResolver._try_db(path=path), None)
        self.assertEqual(self.downloads, [])

    def test__try_db_download(self):
        path = os.path.join(self.base, "downloaded.mmdb")
        self._patch_download(contents=b"database")

        # a download that produces the file names the path of it, which the
        # caller needs in order to open the database that was fetched
        self.assertEqual(geo.GeoResolver._try_db(path=path, download=True), path)
        self.assertEqual(self.downloads, [path])

    def test__try_db_download_failed(self):
        path = os.path.join(self.base, "failed.mmdb")
        self._patch_download()

        # a download that produces no file reports the absence, instead of
        # naming a path that nothing is able to open
        self.assertEqual(geo.GeoResolver._try_db(path=path, download=True), None)
        self.assertEqual(self.downloads, [path])

    def test__store_db(self):
        path = os.path.join(self.base, "stored.mmdb")
        contents = self._compress(b"database")

        result = geo.GeoResolver._store_db(contents, path=path)

        # the payload is decompressed into the target path and the archive
        # that carried it is removed, leaving only the database behind
        self.assertEqual(result, path)
        self.assertEqual(self._read(path), b"database")
        self.assertEqual(os.path.exists(path + ".gz"), False)

    def _patch_download(self, contents=None):
        # replaces the download by one that records the path that it was
        # asked for, writing the provided contents when there are any
        def _download_db(cls, path=geo.GeoResolver.DB_NAME):
            self.downloads.append(path)
            if contents == None:
                return
            self._store(path, contents)

        geo.GeoResolver._download_db = classmethod(_download_db)

    def _patch_try(self, found=False):
        # replaces the lookup of a database by one that records the paths
        # that it was asked for, reporting them as found or as absent
        tried = []

        def _try_db(cls, path=geo.GeoResolver.DB_NAME, download=False):
            tried.append((path, download))
            return path if found else None

        geo.GeoResolver._try_db = classmethod(_try_db)
        return tried

    def _compress(self, contents):
        path = os.path.join(self.base, "source.gz")
        file = gzip.open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
        return self._read(path)

    def _store(self, path, contents):
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()

    def _read(self, path):
        file = open(path, "rb")
        try:
            return file.read()
        finally:
            file.close()
