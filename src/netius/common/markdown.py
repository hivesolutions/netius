#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import re

from netius.common import parser

class MarkdownParser(parser.Parser):
    """
    Parser object for the md (markdown) format, should be able to
    parse the normalized standard definition of markdown.

    The parser is based on the original specification published
    under the daring fireball blog, supporting the typical readability
    language features emphasized in the specification.

    This implementation is a heavily simplified version of a good and
    some of the features may not be completely implemented and the
    actual performance of the parser may be low.

    @see: http://daringfireball.net/projects/markdown/syntax
    """

    def __init__(self, owner):
        parser.Parser.__init__(self, owner)

        self.build()

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        parser.Parser.build(self)

        newline = r"(?P<newline>(\n\n)|(\r\n\r\n))"
        header = r"(?P<header>^(?P<header_index>#+) (?P<header_value>.+)$)"
        list = r"(?P<list>^(?P<list_index>\s*)[\*\+\-](?P<list_value>.+)$)"
        image = r"(?P<image>\!(?P<image_label>\[.+?\])(?P<image_value>\(.+?\)))"
        link = r"(?P<link>(?P<link_label>\[.+?\])(?P<link_value>\([^ ]+\)))"
        bold = r"(?P<bold>\*\*(?P<bold_value>[^\0]+?)\*\*)"
        italic = r"(?P<italic>\*(?P<italic_value>[^\0]+?)\*)"
        code = r"(?P<code>```(?P<code_name>.*)(?P<code_value>[^\0]+?)```)"
        code_single =  r"(?P<code_single>`(?P<code_single_value>[^`]+)`)"

        self.master = re.compile(
            "|".join([
                newline,
                header,
                list,
                image,
                link,
                bold,
                italic,
                code,
                code_single
            ]),
            re.MULTILINE | re.UNICODE
        )
        self.simple = re.compile(
            "|".join([
                image,
                link,
                bold,
                italic,
                code_single
            ]),
            re.MULTILINE | re.UNICODE
        )

    def parse(self, data, regex = None):
        regex = regex or self.master

        nodes = []
        matches = regex.finditer(data)

        current = 0

        for match in matches:
            name = match.lastgroup
            parts = match.groupdict()

            start, end = match.span()
            if start > current:
                value = data[current:start]
                value = value.replace("\r", "")
                value = value.replace("\n", " ")
                if value: nodes.append(value)

            method = getattr(self, "parse_" + name)
            node = method(parts)
            nodes.append(node)

            current = end

        remaining = data[current:]
        remaining = remaining.replace("\r", "")
        remaining = remaining.replace("\n", " ")
        if remaining: nodes.append(remaining)

        return nodes

    def parse_newline(self, parts):
        node = dict(type = "newline")
        return node

    def parse_header(self, parts):
        index = parts["header_index"]
        value = parts["header_value"]

        if value.endswith(" " + index): value = value.rstrip(" #")
        value = self.parse(value, regex = self.simple)

        node = dict(
            type = "header",
            level = len(index),
            value = value
        )
        return node

    def parse_list(self, parts):
        index = parts["list_index"]
        value = parts["list_value"]
        value = self.parse(value, regex = self.simple)

        node = dict(
            type = "list",
            level = len(index) + 1,
            value = value
        )
        return node

    def parse_image(self, parts):
        label = parts["image_label"]
        value = parts["image_value"]

        label = label[1:-1]
        value = value[1:-1]

        node = dict(
            type = "image",
            label = label,
            value = value
        )
        return node

    def parse_link(self, parts):
        label = parts["link_label"]
        value = parts["link_value"]

        original = label + value
        reversed = original[::-1]
        last = reversed.index("(")

        label = original[1:(last + 2) * -1]
        value = original[last * -1:-1]

        label = self.parse(label, regex = self.simple)

        node = dict(
            type = "link",
            label = label,
            value = value
        )
        return node

    def parse_bold(self, parts):
        value = parts["bold_value"]
        value = self.parse(value, regex = self.simple)

        node = dict(
            type = "bold",
            value = value
        )
        return node

    def parse_italic(self, parts):
        value = parts["italic_value"]
        value = self.parse(value, regex = self.simple)

        node = dict(
            type = "italic",
            value = value
        )
        return node

    def parse_code(self, parts):
        name = parts["code_name"]
        value = parts["code_value"]

        node = dict(
            type = "code",
            name = name,
            value = value,
            multiline = True
        )
        return node

    def parse_code_single(self, parts):
        value = parts["code_single_value"]

        node = dict(
            type = "code",
            value = value,
            multiline = False
        )
        return node

    def parse_normal(self, parts):
        return parts["value"]

class MarkdownGenerator(object):

    def __init__(self, file = None):
        self.file = file
        self.reset()

    def reset(self):
        pass

    def flush(self):
        pass

    def generate(self, nodes):
        self.reset()
        self._generate(nodes)
        self.flush()

    def emit(self, value):
        if not self.file: return
        self.file.write(value)

    def _generate(self, nodes):
        for node in nodes:
            is_map = type(node) == dict
            _type = node["type"] if is_map else "normal"
            method = getattr(self, "generate_" + _type)
            method(node)

class MarkdownHTML(MarkdownGenerator):

    def reset(self):
        MarkdownGenerator.reset(self)
        self.paragraph = False
        self.list_item = False
        self.open = False
        self.list_level = 0

    def flush(self):
        MarkdownGenerator.flush(self)
        self._close_all()

    def generate_newline(self, node):
        self._close_all()
        self.emit("<p>")
        self.open = True
        self.paragraph = True

    def generate_header(self, node):
        level = node["level"]
        value = node["value"]
        self._close_all()
        self.emit("<h%d>" % level)
        self._generate(value, open = True)
        self.emit("</h%d>" % level)

    def generate_list(self, node):
        level = node["level"]
        value = node["value"]
        if self.list_item: self.emit("</li>")
        self._ensure_list(level = level)
        self.emit("<li>")
        self.list_item = True
        self._generate(value, open = True)

    def generate_image(self, node):
        label = node["label"]
        value = node["value"]
        self.emit("<img src=\"%s\" alt=\"%s\" />" % (value, label))

    def generate_link(self, node):
        label = node["label"]
        value = node["value"]
        self.emit("<a href=\"%s\">" % value)
        self._generate(label, open = True)
        self.emit("</a>")

    def generate_bold(self, node):
        value = node["value"]
        self.emit("<strong>")
        self._generate(value, open = True)
        self.emit("</strong>")

    def generate_italic(self, node):
        value = node["value"]
        self.emit("<em>")
        self._generate(value, open = True)
        self.emit("</em>")

    def generate_code(self, node):
        value = node["value"]
        multiline = node.get("multiline", False)
        tag = "pre" if multiline else "code"
        self.emit("<%s>" % tag)
        self.emit(value)
        self.emit("</%s>" % tag)

    def generate_normal(self, node):
        if self.open: self.emit(node)
        else: self.generate_newline(node); self.emit(node.lstrip())

    def _generate(self, nodes, open = False):
        _open = self.open
        if open: self.open = True
        MarkdownGenerator._generate(self, nodes)
        if open: self.open = _open

    def _ensure_list(self, level = 1):
        if self.list_level == level: return
        self._close_paragraph()
        delta = level - self.list_level
        if delta < 0: self._close_list(delta * -1); return
        for _index in range(delta): self.emit("<ul>")
        self.list_level = level
        self.open = True

    def _close_all(self):
        self._close_paragraph()
        self._close_list()
        self.open = False

    def _close_paragraph(self):
        if not self.paragraph: return
        self.emit("</p>")
        self.paragraph = False

    def _close_list(self, count = None):
        if self.list_item: self.emit("</li>")
        if not count: count = self.list_level
        for _index in range(count): self.emit("</ul>")
        self.list_level -= count
        self.list_item = False
