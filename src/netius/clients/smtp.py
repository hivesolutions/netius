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

import time
import base64
import datetime

import email.parser

import netius.common

from . import dns

HELO_STATE = 1

EHLO_STATE = 2

CAPA_STATE = 3

STLS_STATE = 4

UPGRADE_STATE = 5

AUTH_STATE = 6

USERNAME_STATE = 7

PASSWORD_STATE = 8

FROM_STATE = 9

TO_STATE = 10

DATA_STATE = 11

CONTENTS_STATE = 12

QUIT_STATE = 13

FINAL_STATE = 14


class SMTPConnection(netius.Connection):

    AUTH_METHODS = ("plain", "login")
    """ The sequence that defined the multiple allowed
    methods for this SMTP protocol implementation """

    def __init__(self, host="smtp.localhost", *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.host = host
        self.froms = None
        self.tos = None
        self.contents = None
        self.username = None
        self.password = None
        self.expected = None
        self.to_index = 0
        self.state = HELO_STATE
        self.next = None
        self.sindex = 0
        self.sequence = ()
        self.capabilities = ()
        self.messages = []
        self.greeting = None
        self.queue_response = None
        self.tls_version = None
        self.tls_cipher = None
        self.start_time = None
        self.transcript = []
        self.transcript_max = 50

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        if not self.is_open():
            return
        self.start_time = time.time()
        self.parser = netius.common.SMTPParser(self)
        self.parser.bind("on_line", self.on_line)
        self.build()

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if not self.is_closed():
            return
        if self.parser:
            self.parser.destroy()
        self.destroy()

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        netius.Connection.build(self)
        self.states = (
            self.helo_t,
            self.ehlo_t,
            self.capa_t,
            self.stls_t,
            self.upgrade_t,
            self.auth_t,
            self.username_t,
            self.password_t,
            self.mail_t,
            self.rcpt_t,
            self.data_t,
            self.contents_t,
            self.quit_t,
            self.close_t,
        )
        self.state_l = len(self.states)

    def destroy(self):
        """
        Destroys the current structure for the stats meaning that
        it's restored to the original values, this method should only
        be called on situation where no more client usage is required.
        """

        netius.Connection.destroy(self)
        self.states = ()
        self.state_l = 0

    def set_smtp(self, froms, tos, contents, username=None, password=None):
        self.froms = froms
        self.tos = tos
        self.contents = contents
        self.username = username
        self.password = password

    def set_sequence(self, sequence, safe=True):
        if safe and self.sequence == sequence:
            return
        self.sindex = 0
        self.sequence = sequence
        self.state = sequence[0]

    def set_message_seq(self, ehlo=True):
        sequence = (
            EHLO_STATE if ehlo else HELO_STATE,
            CAPA_STATE,
            AUTH_STATE,
            USERNAME_STATE,
            PASSWORD_STATE,
            FROM_STATE,
            TO_STATE,
            DATA_STATE,
            CONTENTS_STATE,
            QUIT_STATE,
            FINAL_STATE,
        )
        self.set_sequence(sequence)

    def set_message_stls_seq(self, ehlo=True):
        sequence = (
            EHLO_STATE if ehlo else HELO_STATE,
            CAPA_STATE,
            STLS_STATE,
            UPGRADE_STATE,
            EHLO_STATE if ehlo else HELO_STATE,
            CAPA_STATE,
            AUTH_STATE,
            USERNAME_STATE,
            PASSWORD_STATE,
            FROM_STATE,
            TO_STATE,
            DATA_STATE,
            CONTENTS_STATE,
            QUIT_STATE,
            FINAL_STATE,
        )
        self.set_sequence(sequence)

    def set_capabilities(self, capabilities, force=True):
        if not force and self.capabilities:
            return
        capabilities = [value.strip().lower() for value in capabilities]
        self.capabilities = capabilities

    def next_sequence(self):
        self.sindex += 1
        self.sindex = self.sequence.index(self.next) if self.next else self.sindex
        self.state = self.next if self.next else self.sequence[self.sindex]
        self.next = None

    def parse(self, data):
        return self.parser.parse(data)

    def send_smtp(self, code, message="", delay=True, callback=None):
        base = "%s %s" % (code, message)
        data = base + "\r\n"
        count = self.send(data, delay=delay, callback=callback)
        self.debug(base)
        self._transcript_add("send", base)
        return count

    def on_line(self, code, message, is_final=True):
        # creates the base string from the provided code value and the
        # message associated with it, then logs the values into the
        # current debug logger support (for traceability)
        base = "%s %s" % (code, message)
        self.debug(base)
        self._transcript_add("recv", base)

        # adds the message part of the line to the buffer that holds the
        # various messages "pending" for the current response, these values
        # may latter be used for the processing of the response
        self.messages.append(message)

        # in case the currently parsed line is not a final one must return
        # immediately to continue the processing of information for the
        # current response, the various message should be accumulated under
        # the message buffer to avoid any problem
        if not is_final:
            return

        # runs the code based assertion so that if there's an expected
        # value set for the current connection it's correctly validated
        self.assert_c(code)

        # verifies that the current state valid represents a valid state
        # according to the ones that have "generate" handling methods, otherwise
        # raises a parser error indicating the problem
        if self.state > self.state_l:
            raise netius.ParserError("Invalid state", details=self.messages)

        # runs the calling of the next state based method according to the
        # currently defined state, this is the increments in calling
        self.call()

        # erases the message buffer as it's not longer going to be used in
        # the handling (as it is finished) nothing remaining
        del self.messages[:]

    def call(self):
        # tries to retrieve the method for the current state in iteration
        # and then calls the retrieve method with no arguments (handler method)
        method = self.states[self.state - 1]
        method()

    def skip(self):
        self.next_sequence()
        self.call()

    def helo_t(self):
        if self.greeting == None:
            self.greeting = self.messages[0] if self.messages else None
        self.helo(self.host)
        self.next_sequence()

    def ehlo_t(self):
        if self.greeting == None:
            self.greeting = self.messages[0] if self.messages else None
        self.ehlo(self.host)
        self.next_sequence()

    def capa_t(self):
        capabilities = self.messages[1:]
        self.set_capabilities(capabilities)
        if "starttls" in self.capabilities:
            self.set_message_stls_seq()
        self.next_sequence()
        self.call()

    def stls_t(self):
        self.starttls()
        self.next_sequence()

    def upgrade_t(self):
        def callback(connection):
            connection.upgrade(server=False)

        self.next_sequence()
        callback(self)

    def auth_t(self):
        is_valid = self.username and self.password
        if not is_valid:
            self.next = FROM_STATE
            self.skip()
            return

        method = self.best_auth()
        self.auth(self.username, self.password, method=method)
        self.next_sequence()

    def username_t(self):
        self.login_username(self.username)
        self.next_sequence()

    def password_t(self):
        self.login_password(self.password)
        self.next_sequence()

    def mail_t(self):
        self.mail(self.froms[0])
        self.next_sequence()

    def rcpt_t(self):
        is_final = self.to_index == len(self.tos) - 1
        self.rcpt(self.tos[self.to_index])
        self.to_index += 1
        if is_final:
            self.next_sequence()

    def data_t(self):
        self.data()
        self.next_sequence()

    def contents_t(self):
        self.assert_s(CONTENTS_STATE)
        self.send(self.contents)
        self.send("\r\n.\r\n")
        self.set_expected(250)
        self.next_sequence()

    def quit_t(self):
        self.queue_response = self.messages[0] if self.messages else None

        # captures TLS information that can be later used for
        # diagnostics purposes and critical security analysis
        try:
            self.tls_version = self.socket.version() if self.socket else None
            self.tls_cipher = self.socket.cipher() if self.socket else None
        except Exception:
            self.tls_version = None
            self.tls_cipher = None

        self.quit()
        self.next_sequence()

    def close_t(self):
        self.close(flush=True)

    def pass_t(self):
        pass

    def helo(self, host):
        self.assert_s(HELO_STATE)
        message = host
        self.send_smtp("helo", message)
        self.set_expected(250)

    def ehlo(self, host):
        self.assert_s(EHLO_STATE)
        message = host
        self.send_smtp("ehlo", message)
        self.set_expected(250)

    def starttls(self):
        self.assert_s(STLS_STATE)
        self.send_smtp("starttls")
        self.set_expected(220)

    def auth(self, username, password, method="plain"):
        self.assert_s(AUTH_STATE)
        method_name = "auth_%s" % method
        has_method = hasattr(self, method_name)
        if not has_method:
            raise netius.NotImplemented("Method not implemented")
        method = getattr(self, method_name)
        method(username, password)

    def auth_plain(self, username, password):
        auth_value = "\0%s\0%s" % (username, password)
        auth_value = netius.legacy.bytes(auth_value)
        auth_value = base64.b64encode(auth_value)
        auth_value = netius.legacy.str(auth_value)
        message = "%s %s" % ("plain", auth_value)
        self.send_smtp("auth", message)
        self.set_expected(235)
        self.next = FROM_STATE

    def auth_login(self, username, password):
        message = "login"
        self.send_smtp("auth", message)
        self.set_expected(334)

    def login_username(self, username):
        username = netius.legacy.bytes(username)
        username = base64.b64encode(username)
        username = netius.legacy.str(username)
        self.send_smtp(username)
        self.set_expected(334)

    def login_password(self, password):
        password = netius.legacy.bytes(password)
        password = base64.b64encode(password)
        password = netius.legacy.str(password)
        self.send_smtp(password)
        self.set_expected(235)

    def mail(self, value):
        self.assert_s(FROM_STATE)
        message = "FROM:<%s>" % value
        self.send_smtp("mail", message)
        self.set_expected(250)

    def rcpt(self, value):
        self.assert_s(TO_STATE)
        message = "TO:<%s>" % value
        self.send_smtp("rcpt", message)
        self.set_expected(250)

    def data(self):
        self.assert_s(DATA_STATE)
        self.send_smtp("data")
        self.set_expected(354)

    def quit(self):
        self.assert_s(QUIT_STATE)
        self.send_smtp("quit")
        self.set_expected(221)

    def set_expected(self, expected):
        self.expected = expected

    def assert_c(self, code):
        if not self.expected:
            return
        expected = self.expected
        code_i = int(code)
        self.expected = None
        valid = expected == code_i
        if valid:
            return
        raise netius.ParserError(
            "Invalid response code expected '%d' received '%d'" % (expected, code_i),
            details=self.messages,
        )

    def assert_s(self, expected):
        if self.state == expected:
            return
        raise netius.ParserError("Invalid state", details=self.messages)

    def best_auth(self):
        cls = self.__class__
        methods = []
        for capability in self.capabilities:
            is_auth = capability.startswith("auth ")
            if not is_auth:
                continue
            parts = capability.split(" ")
            parts = [part.strip() for part in parts]
            methods.extend(parts[1:])
        usable = [method for method in methods if method in cls.AUTH_METHODS]
        return usable[0] if usable else "plain"

    def _transcript_add(self, direction, message):
        if not self.owner or not getattr(self.owner, "capture_transcript", False):
            return
        if len(self.transcript) >= self.transcript_max:
            return
        self.transcript.append(
            dict(direction=direction, message=message, timestamp=time.time())
        )


class SMTPClient(netius.StreamClient):

    def __init__(
        self, host=None, auto_close=False, capture_transcript=False, *args, **kwargs
    ):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.host = host if host else "[" + netius.common.host() + "]"
        self.auto_close = auto_close
        self.capture_transcript = capture_transcript

    @classmethod
    def message_s(
        cls, froms, tos, contents, daemon=True, host=None, mark=True, callback=None
    ):
        smtp_client = cls.get_client_s(thread=True, daemon=daemon, host=host)
        smtp_client.message(froms, tos, contents, mark=mark, callback=callback)

    def message(
        self,
        froms,
        tos,
        contents,
        message_id=None,
        host=None,
        port=25,
        username=None,
        password=None,
        ehlo=True,
        stls=False,
        mark=True,
        comply=False,
        ensure_loop=True,
        sequential=True,
        mx_dedup=False,
        callback=None,
        callback_error=None,
    ):
        """
        Sends an email message to the provided recipients, establishing
        one or more SMTP connections as needed based on the target hosts.

        This method operates in two distinct modes depending on whether
        the host parameter is provided:

        **Direct host mode** (host is set): connects directly to the
        specified host and sends the message to all recipients through
        that single connection. This is the typical mode for relay
        operations where a smart host or specific SMTP server is used.
        The method returns the connection object synchronously.

        **MX resolution mode** (host is None): resolves MX records for
        each unique recipient domain via DNS, groups recipients by
        resolved MX host, and opens one connection per unique MX server.
        This avoids opening multiple connections to the same server when
        different domains share the same MX (eg. multiple Google Workspace
        domains), which could cause the remote to drop extra connections.
        The method returns None as connections are established
        asynchronously through DNS callbacks.

        In both modes the callback is invoked once all SMTP sessions
        have completed (not per-connection), receiving the client instance
        and a context dictionary containing deliverability information
        accumulated across all sessions. The callback_error on the other
        hand fires per-connection whenever an exception occurs during
        an individual SMTP session.

        STARTTLS is auto-negotiated based on server capabilities
        regardless of the stls parameter. When the remote server
        advertises starttls in its EHLO capabilities the connection
        is automatically upgraded. The stls parameter controls the
        initial connection sequence: when True the sequence assumes
        STARTTLS from the start, when False (default) the sequence
        starts plain and upgrades dynamically if supported.

        :type froms: List
        :param froms: The list of sender email addresses, typically
        a single-element list. Only the first element is used as the
        MAIL FROM address in the SMTP envelope.
        :type tos: List
        :param tos: The list of recipient email addresses. In MX
        resolution mode these are grouped by domain and then by
        resolved MX host for connection deduplication.
        :type contents: String
        :param contents: The raw email message contents including
        headers and body in RFC 2822 format.
        :type message_id: String
        :param message_id: Optional message identifier to be set in
        the headers when the comply flag is enabled.
        :type host: String
        :param host: The target SMTP host to connect to directly,
        bypassing MX resolution. When set the method operates in
        direct host mode, when None it operates in MX resolution mode.
        :type port: int
        :param port: The target SMTP port, defaults to 25.
        :type username: String
        :param username: Optional username for SMTP authentication
        on the target server.
        :type password: String
        :param password: Optional password for SMTP authentication
        on the target server.
        :type ehlo: bool
        :param ehlo: If True uses EHLO for the greeting (default),
        if False uses the legacy HELO command instead.
        :type stls: bool
        :param stls: If True the initial connection sequence includes
        STARTTLS negotiation before sending. Note that STARTTLS is
        auto-negotiated from server capabilities regardless of this
        flag, so this primarily controls the initial sequence setup.
        :type mark: bool
        :param mark: If True (default) the contents are marked with
        the client's user agent and date headers. Should be set to
        False when relaying messages to preserve original headers.
        :type comply: bool
        :param comply: If True ensures that mandatory RFC headers
        (From, To, Message-ID) are present in the contents, adding
        them if missing.
        :type ensure_loop: bool
        :param ensure_loop: If True (default) ensures the event loop
        thread is started before initiating DNS queries. This is
        required for standalone usage where no event loop is running
        yet. Should be disabled when the client is already running
        within an active event loop.
        :type sequential: bool
        :param sequential: If True the SMTP connections to different
        MX hosts are established one at a time, waiting for each
        session to complete before starting the next. This reduces
        pressure on remote servers that may drop concurrent connections
        from the same source IP. Defaults to True (sequential).
        :type mx_dedup: bool
        :param mx_dedup: If True recipients on different email domains
        that resolve to the same MX host are grouped into a single
        SMTP connection. Should be disabled when the remote server
        rejects multiple destination domains per transaction (eg.
        Google returns 451 4.3.0). Defaults to False.
        :type callback: Callable
        :param callback: Optional callback invoked once all SMTP
        sessions for this message have completed. Called with
        (smtp_client, context) where context is a dictionary
        containing froms, tos, contents, and a sessions list with
        per-connection deliverability information (greeting, queue
        response, TLS details, transcript, duration, etc).
        :type callback_error: Callable
        :param callback_error: Optional callback invoked per-connection
        when an exception occurs during an SMTP session. Called with
        (smtp_client, context, exception). Unlike callback this may
        fire multiple times if multiple connections encounter errors.
        :rtype: SMTPConnection/None
        :return: The connection object in direct host mode, or None
        in MX resolution mode where connections are established
        asynchronously.
        """

        # in case the comply flag is set then ensure that a series
        # of mandatory fields are present in the contents
        if comply:
            contents = self.comply(
                contents, froms=froms, tos=tos, message_id=message_id
            )

        # in case the mark flag is set the contents data is modified
        # and "marked" with the pre-defined header values of the client
        # this should provide some extra information on the agent
        if mark:
            contents = self.mark(contents)

        # creates the shared sessions list that will accumulate
        # deliverability information across all domain handlers
        # for the current message relay operation
        sessions = []

        # creates the method that is able to generate handler for a
        # certain sequence of to based (email) addresses
        def build_handler(tos, domain=None, tos_map=None):

            # creates the context object that will be used to pass
            # contextual information to the callbacks, the sessions
            # list is shared across all handlers for the same message
            # and accumulates deliverability info per domain session
            context = dict(
                froms=froms,
                tos=tos,
                contents=contents,
                mark=mark,
                comply=comply,
                ensure_loop=ensure_loop,
                domain=domain,
                tos_map=tos_map,
                sessions=sessions,
            )

            def capture_session(connection):
                """
                Captures the deliverability information from the SMTP
                session into the shared sessions list, including the
                remote server greeting, queue response, TLS details,
                session duration, recipients and transcript. Skips
                if already captured to avoid duplicates when both
                `on_exception` and `on_close` fire for the same
                connection.

                :type connection: SMTPConnection
                :param connection: The SMTP connection to capture
                session information from, or None if not available.
                """

                if not connection:
                    return
                if getattr(connection, "_session_captured", False):
                    return
                connection._session_captured = True
                end_time = time.time()
                duration = (
                    end_time - connection.start_time
                    if not connection.start_time == None
                    else None
                )
                session = dict(
                    domain=domain,
                    host=(
                        netius.legacy.str(connection.address[0])
                        if connection.address
                        else None
                    ),
                    port=connection.address[1] if connection.address else None,
                    mx_host=(
                        netius.legacy.str(connection.mx_host)
                        if getattr(connection, "mx_host", None)
                        else None
                    ),
                    greeting=connection.greeting,
                    queue_response=connection.queue_response,
                    capabilities=list(connection.capabilities),
                    starttls=not connection.tls_version == None,
                    tls_version=connection.tls_version,
                    tls_cipher=connection.tls_cipher,
                    start_time=connection.start_time,
                    end_time=end_time,
                    duration=duration,
                    recipients=list(tos),
                    error=getattr(connection, "_session_error", None),
                    transcript=connection.transcript,
                )
                context["sessions"].append(session)

            def on_close(connection=None):
                # ensures the session deliverability information is
                # persisted before the completion tracking runs
                capture_session(connection)

                # verifies if the current handler has been built with a
                # domain based closure and if that's the case removes the
                # reference of it from the map of tos, then verifies if the
                # map is still valid and if that's the case returns and this
                # is not considered the last remaining SMTP session for the
                # current send operation (still some open)
                if domain:
                    del tos_map[domain]
                if tos_map:
                    return

                # verifies if the callback method is defined and if that's
                # the case calls the callback indicating the end of the send
                # operation (note that this may represent multiple SMTP sessions)
                if callback:
                    callback(self, context)

            def on_exception(connection=None, exception=None):
                if connection:
                    connection._session_error = str(exception) if exception else None

                # captures session before calling `callback_error` so
                # that the error report includes all session data
                capture_session(connection)

                if callback_error:
                    callback_error(self, context, exception)

            def connect_mx(address, _tos=None):
                """
                Establishes an SMTP connection to the provided MX address
                and configures it for message delivery. Binds the `on_close`
                and `on_exception` handlers from the enclosing `build_handler`
                context for session completion tracking.

                :type address: String
                :param address: The resolved MX host address to connect to.
                :type _tos: List
                :param _tos: Optional override for the recipient list, used
                when multiple domains have been merged into a single
                connection after MX deduplication.
                :rtype: SMTPConnection
                :return: The established SMTP connection.
                """

                # sets the proper address (host) and port values that are
                # going to be used to establish the connection, notice that
                # in case the values provided as parameter to the message
                # method are valid they are used instead of the "resolved"
                _host = host or address
                _port = port or 25
                _tos = _tos or tos

                # prints a debug message about the connection that is now
                # going to be established (helps with debugging purposes)
                self.debug("Establishing SMTP connection on %s:%d ...", _host, _port)

                # establishes the connection to the target host and port,
                # using the provided key and certificate files and then
                # sets the SMTP information in the current connection, after
                # the connections is completed the SMTP session should start
                connection = self.connect(_host, _port)
                connection.mx_host = address if not address == host else None
                if stls:
                    connection.set_message_stls_seq(ehlo=ehlo)
                else:
                    connection.set_message_seq(ehlo=ehlo)
                connection.set_smtp(
                    froms, _tos, contents, username=username, password=password
                )
                connection.bind("close", on_close)
                connection.bind("exception", on_exception)
                return connection

            # returns the connect method bound to the current
            # handler context, ready to be used for connection
            return connect_mx

        # in case the host address has been provided by argument the
        # handler method is called immediately to trigger the processing
        # of the SMTP connection using the current host and port
        if host:
            connect_mx = build_handler(tos)
            connection = connect_mx(host)
            return connection

        # ensures that the proper main loop is started so that the current
        # SMTP client does not become orphan as no connection has been
        # established as of this moment (as expected) and the DNS client
        # is going to be run as a daemon (avoids process exit)
        if ensure_loop:
            self.ensure_loop()

        # creates the map that is going to be used to associate each of
        # the domains with the proper to (email) addresses, this is going
        # to allow aggregated based SMTP sessions (performance wise)
        domains_map = dict()
        for to in tos:
            _name, domain = to.split("@", 1)
            _tos = domains_map.get(domain, [])
            _tos.append(to)
            domains_map[domain] = _tos

        # creates the structures used to collect the DNS MX resolutions
        # before initiating any connections, this ensures that domains
        # resolving to the same MX host are grouped into a single
        # connection avoiding drops from the remote server
        mx_resolved = dict()
        domains_pending = list(domains_map.keys())

        def on_mx_resolved(domain, response):
            """
            Callback for MX DNS resolution that collects the resolved
            address and once all domains are resolved triggers the
            connection initiation phase via `initiate_mx`.

            :type domain: String
            :param domain: The email domain that was resolved.
            :type response: DNSResponse
            :param response: The DNS response containing the MX
            records for the domain, or None if resolution failed.
            """

            # stores the resolved MX address for the domain or none
            # in case the resolution has failed
            if response and response.answers:
                first = response.answers[0]
                extra = first[4]
                mx_resolved[domain] = extra[1]
            else:
                mx_resolved[domain] = None

            # removes the current domain from the pending list, in
            # case there are still pending domains returns immediately
            # waiting for all resolutions to complete
            domains_pending.remove(domain)
            if domains_pending:
                return

            # all domains have been resolved, triggers the connection
            # initiation phase that groups recipients by MX host
            initiate_mx()

        def initiate_mx():
            """
            Groups recipients by resolved MX host and initiates one
            SMTP connection per unique server. Domains that failed MX
            resolution are reported via `callback_error` and tracked
            for completion. Called once all DNS resolutions complete.
            """

            # groups the recipients by resolved MX host so that a
            # single connection is used per unique MX server address,
            # when `mx_dedup` is disabled each domain gets its own
            # connection even if they share the same MX host, domains
            # that failed resolution are tracked separately
            mx_map = dict()
            mx_failed = []
            for domain, tos in netius.legacy.items(domains_map):
                mx_host = mx_resolved.get(domain)
                if mx_host == None:
                    mx_failed.append(domain)
                    continue
                mx_host_s = netius.legacy.str(mx_host).rstrip(".").lower()
                if mx_dedup:
                    mx_key = mx_host_s
                else:
                    mx_key = domain
                existing = mx_map.get(mx_key, ([], [], mx_host_s))
                existing[0].extend(tos)
                existing[1].append(domain)
                mx_map[mx_key] = existing

            # creates the tos map keyed by MX host for the completion
            # tracking of the send operation, failed domains are also
            # included so that the on close fallback fires properly
            tos_map = dict(
                (mx_key, value[0]) for mx_key, value in netius.legacy.items(mx_map)
            )
            for domain in mx_failed:
                tos_map[domain] = domains_map[domain]

            # handles any domains that failed MX resolution by
            # raising the proper error and triggering the on close
            # handler for completion tracking
            for domain in mx_failed:
                _tos = domains_map[domain]
                connect_mx = build_handler(_tos, domain=domain, tos_map=tos_map)
                exception = netius.NetiusError(
                    "Not possible to resolve MX for '%s'" % domain
                )
                if callback_error:
                    callback_error(
                        self,
                        dict(
                            froms=froms,
                            tos=_tos,
                            contents=contents,
                            mark=mark,
                            comply=comply,
                            ensure_loop=ensure_loop,
                            domain=domain,
                            tos_map=tos_map,
                            sessions=sessions,
                        ),
                        exception,
                    )
                del tos_map[domain]
                if not tos_map:
                    if callback:
                        callback(
                            self,
                            dict(
                                froms=froms,
                                tos=list(tos),
                                contents=contents,
                                mark=mark,
                                comply=comply,
                                ensure_loop=ensure_loop,
                                domain=None,
                                tos_map=tos_map,
                                sessions=sessions,
                            ),
                        )
                    return

            # retrieves the list of MX entries to be processed, in
            # sequential mode these are processed one at a time with
            # each connection starting only after the previous completes
            mx_entries = netius.legacy.items(mx_map)

            # in sequential mode the connections are established one
            # at a time, each starting only after the previous one
            # completes, reducing pressure on remote MX servers that
            # may drop concurrent connections from the same source,
            # in parallel mode all connections are started immediately
            if sequential:
                _connect_next_mx(mx_entries, tos_map)
            else:
                for mx_key, (tos, _domains, mx_host_s) in mx_entries:
                    connect_mx = build_handler(tos, domain=mx_key, tos_map=tos_map)
                    connect_mx(mx_host_s, _tos=tos)

        def _connect_next_mx(pending, tos_map):
            # in case there are no more pending MX entries returns
            # immediately as all connections have been processed
            if not pending:
                return

            # retrieves the next MX entry from the pending list
            # and establishes the connection for it
            mx_key, (tos, _domains, mx_host_s) = pending[0]
            remaining = pending[1:]
            connect_mx = build_handler(tos, domain=mx_key, tos_map=tos_map)
            connection = connect_mx(mx_host_s, _tos=tos)

            # binds an additional close handler that triggers the
            # next connection once the current one completes
            connection.bind(
                "close",
                lambda connection=None: _connect_next_mx(remaining, tos_map),
            )

        # iterates over the complete set of domains to run the MX
        # based query operation collecting the results
        for domain in domains_map:
            self.debug("Resolving MX domain for '%s' ...", domain)

            def build_mx_callback(_domain):
                return lambda response: on_mx_resolved(_domain, response)

            dns.DNSClient.query_s(domain, type="mx", callback=build_mx_callback(domain))

    def on_connect(self, connection):
        netius.StreamClient.on_connect(self, connection)

    def on_upgrade(self, connection):
        netius.StreamClient.on_upgrade(self, connection)
        connection.call()

    def on_data(self, connection, data):
        netius.StreamClient.on_data(self, connection, data)
        connection.parse(data)

    def on_connection_d(self, connection):
        netius.StreamClient.on_connection_d(self, connection)
        if not self.auto_close:
            return
        if self.connections:
            return
        self.close()

    def build_connection(self, socket, address, ssl=False):
        return SMTPConnection(
            owner=self, socket=socket, address=address, ssl=ssl, host=self.host
        )

    def comply(self, contents, froms=None, tos=None, message_id=None):
        parser = email.parser.Parser()
        message = parser.parsestr(contents)
        if froms:
            self.from_(message, froms[0])
        if tos:
            self.to(message, ",".join(tos))
        if message_id:
            self.message_id(message, message_id)
        return message.as_string()

    def mark(self, contents):
        parser = email.parser.Parser()
        message = parser.parsestr(contents)
        self.date(message)
        self.user_agent(message)
        return message.as_string()

    def from_(self, message, value):
        from_ = message.get("From", None)
        if from_:
            return
        message["From"] = value

    def to(self, message, value):
        to = message.get("To", None)
        if to:
            return
        message["To"] = value

    def message_id(self, message, value):
        message_id = message.get("Message-Id", None)
        message_id = message.get("Message-ID", message_id)
        if message_id:
            return
        message["Message-ID"] = value

    def date(self, message):
        date = message.get("Date", None)
        if date:
            return
        date_time = datetime.datetime.utcnow()
        message["Date"] = date_time.strftime("%a, %d %b %Y %H:%M:%S +0000")

    def user_agent(self, message):
        user_agent = message.get("User-Agent", None)
        if user_agent:
            return
        message["User-Agent"] = netius.IDENTIFIER


if __name__ == "__main__":
    import email.mime.text

    sender = netius.conf("SMTP_SENDER", "hello@bemisc.com")
    receiver = netius.conf("SMTP_RECEIVER", "hello@bemisc.com")
    host = netius.conf("SMTP_HOST", None)
    port = netius.conf("SMTP_PORT", 25, cast=int)
    username = netius.conf("SMTP_USER", None)
    password = netius.conf("SMTP_PASSWORD", None)
    stls = netius.conf("SMTP_STARTTLS", False, cast=bool)

    mime = email.mime.text.MIMEText("Hello World")
    mime["Subject"] = "Hello World"
    mime["From"] = sender
    mime["To"] = receiver
    contents = mime.as_string()

    client = SMTPClient(auto_close=True)
    client.message(
        [sender],
        [receiver],
        contents,
        host=host,
        port=port,
        username=username,
        password=password,
        stls=stls,
    )
else:
    __path__ = []
