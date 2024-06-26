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

import asyncio
import aiofiles
import aiohttp

import netius

BASE_URL = "http://stats.nba.com/stats"
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/45.0.2454.101 Safari/537.36"
    ),
    "connection": ("keep-alive"),
}


async def get_players(player_args, season="2016-17"):
    endpoint = "/commonallplayers"

    params = dict(season=season, leagueid="00", isonlycurrentseason="1")
    url = BASE_URL + endpoint

    print("Getting all players for season %s ..." % season)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            data = await resp.json()

    player_args.extend([(item[0], item[2]) for item in data["resultSets"][0]["rowSet"]])


async def get_player(player_id, player_name):
    endpoint = "/commonplayerinfo"
    params = dict(playerid=player_id)
    url = BASE_URL + endpoint

    print("Getting player %s" % player_name)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            data = await resp.text()
            print(data)

    async with aiofiles.open(
        "players/%s.json" % player_name.replace(" ", "_"), "w"
    ) as file:
        await file.write(data)


loop = netius.get_loop(_compat=True)

os.makedirs("players", exist_ok=True)

player_args = []
loop.run_until_complete(get_players(player_args))
loop.run_until_complete(asyncio.gather(*(get_player(*args) for args in player_args)))
loop.close()
