#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Temporary harness used to reproduce the intermittent failure of the
deferred compression test under macOS, it replicates the fixture of the
test and loops over the request that fails, dumping the diagnostics of
the closed connections whenever the failure is observed."""

import os
import sys
import time
import json
import zlib
import logging
import threading

# the diagnostics must be active before netius is imported, as that's what
# selects the connection class that keeps the closing metadata
os.environ["DIAG"] = "1"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import netius
import netius.extra
import netius.servers

import importlib

import http.client as http_client

common = importlib.import_module("netius.base.common")

# records the sequence of the relevant proxy events so that the ordering
# that leads to the loss of the payload may be observed
EVENTS = []

_partial = netius.extra.ReverseProxyServer._on_prx_partial
_message = netius.extra.ReverseProxyServer._on_prx_message
_release = netius.extra.ReverseProxyServer._prx_release


def _on_prx_partial(self, client, parser, data):
    connection = self.conn_map.get(parser.owner, None)
    buffer = connection and getattr(connection, "encoding_b", None)
    EVENTS.append(
        "partial len=%d buffered=%s" % (
            len(data), buffer["length"] if buffer else None)
    )
    return _partial(self, client, parser, data)


def _on_prx_message(self, client, parser, message):
    connection = self.conn_map.get(parser.owner, None)
    buffer = connection and getattr(connection, "encoding_b", None)
    EVENTS.append(
        "message len=%d buffered=%s" % (
            len(message or b""), buffer["length"] if buffer else None)
    )
    return _message(self, client, parser, message)


def _prx_release(self, connection, codec=None, length=None):
    buffer = getattr(connection, "encoding_b", None)
    EVENTS.append(
        "release codec=%s length=%s buffered=%s" % (
            bool(codec), length, buffer["length"] if buffer else None)
    )
    return _release(self, connection, codec=codec, length=length)


netius.extra.ReverseProxyServer._on_prx_partial = _on_prx_partial
netius.extra.ReverseProxyServer._on_prx_message = _on_prx_message
netius.extra.ReverseProxyServer._prx_release = _prx_release

BIG = b"netius " * 900

COUNT = int(os.environ.get("COUNT", 300))


def app(environ, start_response):
    path = environ["PATH_INFO"]
    if path == "/stream":
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [BIG[:3000], BIG[3000:]]
    if path == "/trickle":
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"tiny"]
    start_response(
        "200 OK",
        [("Content-Type", "text/plain"), ("Content-Length", str(len(BIG)))],
    )
    return [BIG]


def wait(port):
    for _index in range(50):
        time.sleep(0.1)
        try:
            probe = __import__("socket").create_connection(("127.0.0.1", port), 1)
            probe.close()
            return
        except Exception:
            continue


def dump(reason):
    print("=" * 70)
    print("FAILURE: %s" % reason)
    print("=" * 70)
    print("--- events ---")
    for event in EVENTS[-14:]:
        print("  %s" % event)
    print("--- closed connections ---")
    records = common.AbstractBase._DIAG_CLOSED
    print("closed connections recorded: %d" % len(records))
    for info in list(records)[-12:]:
        print(
            json.dumps(
                dict(
                    id=info.get("id"),
                    owner=info.get("owner"),
                    close_reason=info.get("close_reason"),
                    close_error=info.get("close_error"),
                    close_paired=info.get("close_paired"),
                    duration=info.get("duration"),
                    in_bytes=info.get("in_bytes"),
                    out_bytes=info.get("out_bytes"),
                    recvs=info.get("recvs"),
                    sends=info.get("sends"),
                ),
                sort_keys=True,
            )
        )
    sys.stdout.flush()


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

backend = netius.servers.WSGIServer(app=app, env=False, level=logging.DEBUG)
backend.serve(host="127.0.0.1", port=0, start=False)
backend_port = backend.port
threading.Thread(target=backend.start, daemon=True).start()
wait(backend_port)

proxy = netius.extra.ReverseProxyServer(
    hosts={"default": "http://127.0.0.1:%d" % backend_port},
    encoding="auto",
    env=False,
    resolve=False,
    level=logging.DEBUG,
)
proxy.serve(host="127.0.0.1", port=0, start=False)
proxy_port = proxy.port
threading.Thread(target=proxy.start, daemon=True).start()
wait(proxy_port)

print("backend=%d proxy=%d count=%d" % (backend_port, proxy_port, COUNT))
sys.stdout.flush()

failures = 0

for index in range(COUNT):
    del EVENTS[:]
    connection = http_client.HTTPConnection("127.0.0.1", proxy_port, timeout=30)
    try:
        connection.request(
            "GET",
            "/stream",
            headers={
                "Host": "compress.example.com",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        response = connection.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        if not headers.get("Content-Encoding") == "gzip":
            failures += 1
            dump("iteration %d, encoding %r" % (index, headers.get("Content-Encoding")))
            break
        decoded = zlib.decompress(body, zlib.MAX_WBITS | 16)
        if not decoded == BIG:
            failures += 1
            dump("iteration %d, body %d bytes (expected %d)" % (
                index, len(decoded), len(BIG)))
            break
    except Exception as exception:
        failures += 1
        dump("iteration %d, %s: %s" % (index, type(exception).__name__, exception))
        break
    finally:
        connection.close()

print("finished, iterations=%d failures=%d" % (index + 1, failures))
sys.exit(1 if failures else 0)
