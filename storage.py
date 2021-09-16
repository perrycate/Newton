#!/usr/bin/env python3
import io
import pickle
import sqlite3
from dataclasses import dataclass
from typing import Optional, Tuple

import discord


@dataclass
class File:
    name: str
    data: bytes


def _discord_file_to_bytes(f: discord.File) -> bytes:
    return pickle.dumps(File(f.filename, f.fp.read()))


def _bytes_to_discord_file(b: bytes) -> discord.File:
    f = pickle.loads(b)
    # If the filename does not end with a image format, discord will not preview the image.
    # It doesn't actually matter if the image is a .png or not, discord will still preview it lol.
    return discord.File(io.BytesIO(f.data), filename=f.name)


class CmdStore:
    def __init__(self, sqlite3_db_name):
        self._conn = sqlite3.connect(sqlite3_db_name)
        self._cursor = self._conn.cursor()
        self._exec(
            '''CREATE TABLE IF NOT EXISTS commands (key INTEGER PRIMARY KEY, date REAL, user TEXT, trigger TEXT, content TEXT, enabled INTEGER, image BLOB);'''
        )

    def save(self, username, command, content, image=None):
        if image is not None:
            image = _discord_file_to_bytes(image)
        self._exec(
            '''INSERT INTO commands (date, user, trigger, content, enabled, image) VALUES(strftime('%s.%f', 'now'), ?, ?, ?, 1, ?)''',
            username, command, content, image)

    def get(self, command) -> Tuple[str, Optional[discord.File]]:
        rows = self._read(
            '''SELECT content, image FROM commands where trigger=? AND enabled=1 ORDER BY RANDOM() LIMIT 1;''',
            command)
        if len(rows) == 0:
            return "", None

        # Convert image into discord's format, if it is present.
        image = rows[0][1]
        if image is not None:
            image = _bytes_to_discord_file(image)
        return rows[0][0], image

    def list_commands(self):
        return self._read(
            '''SELECT trigger, user, (strftime('%s.%f')-date) FROM commands WHERE enabled=1 GROUP BY trigger ORDER BY trigger;'''
        )

    def count(self, command):
        rows = self._read(
            '''SELECT COUNT(*) FROM commands where trigger=? AND enabled=1;''',
            command)
        if len(rows) == 0:
            return 0
        return int(rows[0][0])

    def delete(self, command):
        self._exec('''UPDATE commands SET enabled=0 WHERE trigger=?''',
                   command)

    def _exec(self, sql_str, *args):
        self._cursor.execute(sql_str, args)
        self._conn.commit()

    def _read(self, sql, *args):
        self._cursor.execute(sql, args)
        return self._cursor.fetchall()

    def __del__(self):
        self._conn.close()
