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
    the SMTP_ACTIVITY_URL environment variable is set.
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

    def relay(self, connection, froms, tos, contents):
        # verifies that the current connection has an authenticated user
        # and if not raises an exception as the authentication is mandatory
        # for the relaying of message under the "default" policy
        if not hasattr(connection, "username") or not connection.username:
            raise netius.SecurityError("User is not authenticated")

        # using the auth meta information retrieves the list of allowed
        # froms for the current user and verifies that the current froms
        # are all contained in the list of allowed froms, otherwise raises
        # an exception indicating that the user is not allowed to relay
        auth_meta = getattr(connection, "auth_meta", {})
        allowed_froms = auth_meta.get("allowed_froms", [])
        allowed = not allowed_froms or all(value in allowed_froms for value in froms)
        if not allowed:
            raise netius.SecurityError("User is not allowed to relay from")

        # retrieves the current date value formatted according to
        # the SMTP based specification string value, this value
        # is going to be used for the replacement of the header
        date = self.date()

        # retrieves the first email from the froms list as this is
        # the one that is going to be used for message id generation
        # and then generates a new "temporary" message id
        first = froms[0]
        message_id = self.message_id(connection=connection, email=first)

        # the default reply to value is the first from value and it
        # should serve as a way to reply with errors in case they
        # exist - this way we can notify the sender (postmaster)
        reply_to = first

        # parses the provided contents as mime text and then appends
        # the various extra fields so that the relay operation is
        # considered valid and then re-joins the message as a string
        headers, body = netius.common.rfc822_parse(contents)
        received = connection.received_s()

        # extracts the subject from the headers before they are
        # modified, this value is going to be used for the activity
        # tracking operation (if enabled)
        subject = headers.get("Subject", "")

        message_id = headers.pop("Message-Id", message_id)
        message_id = headers.pop("Message-ID", message_id)
        headers.set("Date", date)
        headers.set("Received", received)
        headers.set("Message-ID", message_id)
        contents = netius.common.rfc822_join(headers, body)

        # tries to sign the message using DKIM, the server is going to
        # search the current registry, trying to find a registry for the
        # domain of the sender and if it finds one signs the message using
        # the information provided by the registry
        contents = self.dkim_contents(contents, email=first)

        # builds the activity context dictionary that will be
        # captured by the callback closures for later posting
        username = getattr(connection, "username", None)
        activity_ctx = dict(
            froms=froms,
            tos=tos,
            subject=subject,
            message_id=message_id,
            username=username,
        )

        # creates the callback that will close the client once the message
        # is sent to all the recipients (better auto close support) and
        # also posts the activity information to the external endpoint
        callback = lambda smtp_client: (
            self._post_activity(activity_ctx, "delivered"),
            smtp_client.close(),
        )

        # creates the callback to the error as a function that sends a
        # postmaster email to the reply to address found in the message,
        # note that this is only performed in case there's a valid email
        # address defined as postmaster for this SMTP server, the activity
        # information is also posted with the error details
        callback_error = lambda smtp_client, context, exception: (
            self._post_activity(activity_ctx, "failed", error=str(exception)),
            self.relay_postmaster(reply_to, context, exception),
        )

        # generates a new SMTP client for the sending of the message,
        # uses the current host for identification and then triggers
        # the message event to send the message to the target host
        smtp_client = netius.clients.SMTPClient(host=self.host)
        smtp_client.message(
            froms,
            tos,
            contents,
            mark=False,
            callback=callback,
            callback_error=callback_error,
        )

    def _post_activity(self, context, status, error=None):
        # in case no activity URL is defined the tracking is
        # disabled and the method returns immediately
        if not self.activity_url:
            return

        # builds the activity payload using the context information
        # that was previously extracted from the message headers
        payload = dict(
            timestamp=time.time(),
            sender=context.get("froms", [None])[0],
            recipients=context.get("tos", []),
            subject=context.get("subject", ""),
            status=status,
            message_id=context.get("message_id", ""),
            server=self.host,
            username=context.get("username", None),
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
