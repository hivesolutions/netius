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

import json
import time

import netius.common
import netius.clients

from . import smtp_r


class ActivityRelaySMTPServer(smtp_r.RelaySMTPServer):
    """
    Relay SMTP server with activity tracking middleware that
    posts delivery status information to an external HTTP
    endpoint after each relay operation completes.

    The activity tracking is optional and only enabled when
    the `SMTP_ACTIVITY_URL` environment variable is set.
    """

    def __init__(self, activity_url=None, activity_secret=None, *args, **kwargs):
        smtp_r.RelaySMTPServer.__init__(self, *args, **kwargs)
        self.activity_url = activity_url
        self.activity_secret = activity_secret

    def on_serve(self):
        smtp_r.RelaySMTPServer.on_serve(self)
        self.activity_url = self.get_env("SMTP_ACTIVITY_URL", self.activity_url)
        self.activity_secret = self.get_env(
            "SMTP_ACTIVITY_SECRET", self.activity_secret
        )
        if self.activity_url:
            self.info(
                "Activity tracking enabled, posting to '%s' ...", self.activity_url
            )

    def on_relay_smtp(self, smtp_client, connection, froms, tos, contents):
        self._post_activity(connection, froms, tos, contents, "delivered")
        smtp_r.RelaySMTPServer.on_relay_smtp(
            self, smtp_client, connection, froms, tos, contents
        )

    def on_relay_error_smtp(
        self,
        smtp_client,
        connection,
        froms,
        tos,
        contents,
        reply_to,
        context,
        exception,
    ):
        self._post_activity(
            connection, froms, tos, contents, "failed", error=str(exception)
        )
        smtp_r.RelaySMTPServer.on_relay_error_smtp(
            self,
            smtp_client,
            connection,
            froms,
            tos,
            contents,
            reply_to,
            context,
            exception,
        )

    def _post_activity(self, connection, froms, tos, contents, status, error=None):
        # in case no activity URL is defined the tracking is
        # disabled and the method returns immediately
        if not self.activity_url:
            return

        # verifies if the activity has already been posted for this
        # relay operation, if that's the case skips the post to avoid
        # duplicate webhook calls (the SMTP client may call both
        # on_close and on_exception for the same relay operation in
        # certain error scenarios)
        has_post = getattr(connection, "_activity_post", False)
        if has_post:
            return
        connection._activity_post = True

        # parses the message headers to extract the subject and
        # message id values for the activity payload, note that
        # byte keys are used as rfc822_parse returns byte pairs
        headers, _body = netius.common.rfc822_parse(contents)
        subject = headers.get(b"Subject", b"")
        message_id = headers.get(b"Message-ID", b"")
        message_id = headers.get(b"Message-Id", message_id)
        subject = netius.legacy.str(subject)
        message_id = netius.legacy.str(message_id)
        username = getattr(connection, "username", None)

        # converts the headers list of byte pairs into a dictionary
        # of string key-value pairs for JSON serialization and also
        # decodes the full contents as a string value
        headers_d = dict(
            (netius.legacy.str(key), netius.legacy.str(value)) for key, value in headers
        )
        contents_s = netius.legacy.str(contents)

        # builds the activity payload using the extracted values
        # and the relay context information
        payload = dict(
            timestamp=time.time(),
            sender=froms[0] if froms else None,
            recipients=list(tos),
            headers=headers_d,
            contents=contents_s,
            subject=subject,
            message_id=message_id,
            status=status,
            server=self.host,
            username=username,
        )
        if error:
            payload["error"] = error

        # serializes the payload as JSON and builds the headers
        # for the HTTP request including the content type and
        # the shared secret for authentication (if defined)
        data = json.dumps(payload)
        data = netius.legacy.bytes(data)
        headers = {"Content-Type": "application/json"}
        if self.activity_secret:
            headers["X-Activity-Secret"] = self.activity_secret

        # posts the activity payload to the external endpoint
        # using a non-blocking HTTP client request, in case of
        # failure a warning is logged and the error is ignored
        try:
            netius.clients.HTTPClient.method_s(
                "POST",
                self.activity_url,
                headers=headers,
                data=data,
            )
        except Exception as exception:
            self.info(
                "Failed to post activity to '%s' (%s)",
                self.activity_url,
                str(exception),
            )


if __name__ == "__main__":
    import logging

    server = ActivityRelaySMTPServer(level=logging.DEBUG)
    server.serve(env=True)
else:
    __path__ = []
