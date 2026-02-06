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

import unittest
import collections

import netius.extra

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ConsulProxyServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.extra.ConsulProxyServer(
            consul_url="http://localhost:8500",
            consul_tag="proxy.enable=true",
            consul_poll_interval=30.0,
            hosts=dict(),
            auth=dict(),
            redirect=dict(),
            error_urls=dict(),
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_config(self):
        self.assertEqual(self.server.consul_url, "http://localhost:8500")
        self.assertEqual(self.server.consul_tag, "proxy.enable=true")
        self.assertEqual(self.server.consul_poll_interval, 30.0)
        self.assertEqual(self.server.consul_token, None)
        self.assertEqual(self.server.host_suffixes, [])

    def test_config_custom(self):
        server = netius.extra.ConsulProxyServer(
            consul_url="http://consul.local:8500",
            consul_token="my-token",
            consul_tag="web.proxy=true",
            consul_poll_interval=60.0,
            host_suffixes=["example.com"],
            hosts=dict(),
            auth=dict(),
            redirect=dict(),
            error_urls=dict(),
        )
        self.assertEqual(server.consul_url, "http://consul.local:8500")
        self.assertEqual(server.consul_token, "my-token")
        self.assertEqual(server.consul_tag, "web.proxy=true")
        self.assertEqual(server.consul_poll_interval, 60.0)
        self.assertEqual(server.host_suffixes, ["example.com"])
        server.cleanup()

    def test_resolve_domain(self):
        tags = ["proxy.enable=true", "proxy.domain=myapp.local"]
        result = self.server._resolve_domain("myapp", tags)
        self.assertEqual(result, "myapp.local")

    def test_resolve_domain_default(self):
        tags = ["proxy.enable=true"]
        result = self.server._resolve_domain("MyApp", tags)
        self.assertEqual(result, "myapp")

    def test_resolve_domain_empty(self):
        tags = ["proxy.enable=true", "proxy.domain="]
        result = self.server._resolve_domain("MyApp", tags)
        self.assertEqual(result, "myapp")

    def test_resolve_domain_name(self):
        tags = ["proxy.enable=true", "proxy.name=webapp"]
        result = self.server._resolve_domain("myapp", tags)
        self.assertEqual(result, "webapp")

    def test_resolve_domain_name_priority(self):
        tags = ["proxy.enable=true", "proxy.name=webapp", "proxy.domain=other"]
        result = self.server._resolve_domain("myapp", tags)
        self.assertEqual(result, "webapp")

    def test_resolve_domain_name_empty(self):
        tags = ["proxy.enable=true", "proxy.name="]
        result = self.server._resolve_domain("MyApp", tags)
        self.assertEqual(result, "myapp")

    def test_build_urls(self):
        instances = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]
        result = self.server._build_urls(instances)
        self.assertEqual(result, ["http://10.0.0.1:8080"])

    def test_build_urls_multiple(self):
        instances = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            },
            {
                "Service": {"Address": "10.0.0.2", "Port": 8080},
                "Node": {"Address": "10.0.0.101"},
            },
        ]
        result = self.server._build_urls(instances)
        self.assertEqual(result, ["http://10.0.0.1:8080", "http://10.0.0.2:8080"])

    def test_build_urls_node_fallback(self):
        instances = [
            {
                "Service": {"Address": "", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]
        result = self.server._build_urls(instances)
        self.assertEqual(result, ["http://10.0.0.100:8080"])

    def test_build_urls_no_address(self):
        instances = [
            {
                "Service": {"Address": "", "Port": 8080},
                "Node": {"Address": ""},
            }
        ]
        result = self.server._build_urls(instances)
        self.assertEqual(result, [])

    def test_build_urls_no_port(self):
        instances = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 0},
                "Node": {"Address": "10.0.0.100"},
            }
        ]
        result = self.server._build_urls(instances)
        self.assertEqual(result, [])

    def test_build_urls_empty(self):
        result = self.server._build_urls([])
        self.assertEqual(result, [])

    def test_build_hosts(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {
            "myapp": ["proxy.enable=true"],
            "redis": ["database"],
        }
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.hosts.get("myapp"), "http://10.0.0.1:8080")
        self.assertTrue("redis" not in self.server.hosts)

    def test_build_hosts_multiple(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            },
            {
                "Service": {"Address": "10.0.0.2", "Port": 8080},
                "Node": {"Address": "10.0.0.101"},
            },
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(
            self.server.hosts.get("myapp"),
            ("http://10.0.0.1:8080", "http://10.0.0.2:8080"),
        )

    def test_build_hosts_custom_domain(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.domain=app.local"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.hosts.get("app.local"), "http://10.0.0.1:8080")
        self.assertTrue("myapp" not in self.server.hosts)

    def test_build_hosts_custom_name(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.name=webapp"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.hosts.get("webapp"), "http://10.0.0.1:8080")
        self.assertTrue("myapp" not in self.server.hosts)

    def test_build_hosts_cleanup(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.hosts.get("myapp"), "http://10.0.0.1:8080")

        # simulates second rebuild with the service removed from
        # consul, the host entry should be properly cleaned up
        with mock.patch.object(self.server, "_consul_services", return_value=dict()):
            self.server._build_hosts()

        self.assertTrue("myapp" not in self.server.hosts)

    def test_build_hosts_empty(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server, "_consul_services", return_value=dict()):
            self.server._build_hosts()

        self.assertEqual(len(self.server._consul_hosts), 0)

    def test_build_hosts_no_healthy(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true"]}

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=[]):
            self.server._build_hosts()

        self.assertTrue("myapp" not in self.server.hosts)

    def test_host_rules(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="myapp"))
        result = self.server.rules_host(None, parser)
        self.assertEqual(result, ("http://10.0.0.1:8080", None))

    def test_resolve_ports(self):
        tags = ["proxy.enable=true", "proxy.port=8080"]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, {8080})

    def test_resolve_ports_multiple(self):
        tags = ["proxy.enable=true", "proxy.port=8080,9090"]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, {8080, 9090})

    def test_resolve_ports_alias(self):
        tags = ["proxy.enable=true", "proxy.ports=8080,9090"]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, {8080, 9090})

    def test_resolve_ports_none(self):
        tags = ["proxy.enable=true"]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, None)

    def test_resolve_ports_empty(self):
        tags = ["proxy.enable=true", "proxy.port="]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, None)

    def test_resolve_ports_priority(self):
        tags = ["proxy.enable=true", "proxy.port=8080", "proxy.ports=9090"]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, {8080})

    def test_resolve_ports_spaces(self):
        tags = ["proxy.enable=true", "proxy.port=8080 , 9090"]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, {8080, 9090})

    def test_resolve_ports_invalid(self):
        tags = ["proxy.enable=true", "proxy.port=abc"]
        result = self.server._resolve_ports(tags)
        self.assertEqual(result, None)

    def test_build_urls_port_filter(self):
        instances = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            },
            {
                "Service": {"Address": "10.0.0.2", "Port": 9090},
                "Node": {"Address": "10.0.0.101"},
            },
        ]
        result = self.server._build_urls(instances, ports={8080})
        self.assertEqual(result, ["http://10.0.0.1:8080"])

    def test_build_urls_port_filter_none(self):
        instances = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            },
            {
                "Service": {"Address": "10.0.0.2", "Port": 9090},
                "Node": {"Address": "10.0.0.101"},
            },
        ]
        result = self.server._build_urls(instances, ports=None)
        self.assertEqual(result, ["http://10.0.0.1:8080", "http://10.0.0.2:9090"])

    def test_build_hosts_port_filter(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.port=8080"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            },
            {
                "Service": {"Address": "10.0.0.2", "Port": 9090},
                "Node": {"Address": "10.0.0.101"},
            },
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.hosts.get("myapp"), "http://10.0.0.1:8080")

    def test_build_hosts_port_filter_multiple(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.port=8080,9090"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            },
            {
                "Service": {"Address": "10.0.0.2", "Port": 9090},
                "Node": {"Address": "10.0.0.101"},
            },
            {
                "Service": {"Address": "10.0.0.3", "Port": 3000},
                "Node": {"Address": "10.0.0.102"},
            },
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(
            self.server.hosts.get("myapp"),
            ("http://10.0.0.1:8080", "http://10.0.0.2:9090"),
        )

    def test_apply_tags_password(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.password=secret123"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertTrue("myapp" in self.server.auth)
        self.assertEqual(self.server.auth["myapp"].password, "secret123")

    def test_apply_tags_password_empty(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.password="]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertTrue("myapp" not in self.server.auth)

    def test_apply_tags_error_url(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {
            "myapp": ["proxy.enable=true", "proxy.error-url=http://errors.local/50x"]
        }
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.error_urls.get("myapp"), "http://errors.local/50x")

    def test_apply_tags_error_url_empty(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.error-url="]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertTrue("myapp" not in self.server.error_urls)

    def test_apply_tags_redirect_ssl(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {"myapp": ["proxy.enable=true", "proxy.redirect-ssl=true"]}
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.redirect.get("myapp"), ("myapp", "https"))

    def test_apply_tags_redirect_ssl_custom_name(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {
            "myapp": [
                "proxy.enable=true",
                "proxy.name=webapp",
                "proxy.redirect-ssl=true",
            ]
        }
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.redirect.get("webapp"), ("webapp", "https"))
        self.assertTrue("myapp" not in self.server.redirect)

    def test_apply_tags_combined(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {
            "myapp": [
                "proxy.enable=true",
                "proxy.password=secret",
                "proxy.error-url=http://errors.local/50x",
                "proxy.redirect-ssl=true",
            ]
        }
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertEqual(self.server.hosts.get("myapp"), "http://10.0.0.1:8080")
        self.assertEqual(self.server.auth["myapp"].password, "secret")
        self.assertEqual(self.server.error_urls.get("myapp"), "http://errors.local/50x")
        self.assertEqual(self.server.redirect.get("myapp"), ("myapp", "https"))

    def test_apply_tags_cleanup(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        services = {
            "myapp": [
                "proxy.enable=true",
                "proxy.password=secret",
                "proxy.error-url=http://errors.local/50x",
                "proxy.redirect-ssl=true",
            ]
        }
        health = [
            {
                "Service": {"Address": "10.0.0.1", "Port": 8080},
                "Node": {"Address": "10.0.0.100"},
            }
        ]

        with mock.patch.object(
            self.server, "_consul_services", return_value=services
        ), mock.patch.object(self.server, "_consul_health", return_value=health):
            self.server._build_hosts()

        self.assertTrue("myapp" in self.server.auth)
        self.assertTrue("myapp" in self.server.error_urls)
        self.assertTrue("myapp" in self.server.redirect)

        # simulates second rebuild with the service removed from
        # consul, all entries should be properly cleaned up
        with mock.patch.object(self.server, "_consul_services", return_value=dict()):
            self.server._build_hosts()

        self.assertTrue("myapp" not in self.server.hosts)
        self.assertTrue("myapp" not in self.server.auth)
        self.assertTrue("myapp" not in self.server.error_urls)
        self.assertTrue("myapp" not in self.server.redirect)
