import os
import sys

import aiosqlite

from BotInfo.config import DB_PATH


async def init_db():
    """
    Generates a SQLite database if it doesn't exist already
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            role TEXT,
            password TEXT
        );
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            telegram_id INTEGER,
            full_name TEXT,
            title TEXT,
            event_status TEXT,
            cert_url TEXT,
            cert_file_id TEXT,
            cert_file_link TEXT,
            curator_full_name TEXT,
            confirmed INTEGER DEFAULT 0
        );
        """)
        await db.commit()


async def query(sql: str, args: tuple = (), one: bool = False):
    """
    Completes SELECT request to SQLite database
    :param sql: SQL SELECT statement to execute
    :param args: Tuple of parameters to substitute into the SQL query
    :param one: If True, return only the first row; if False, return all rows (default - False)
    :return: If `one` is False, returns a list of rows; if `one` is True, returns a single row or None if no rows found
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, args)
        rows = await cur.fetchall()
        return rows and (rows[0] if one else rows)


async def execute(sql: str, args: tuple = ()):
    """
    Executes an INSERT, UPDATE or DELETE query against the SQLite database and commits changes

    :param sql: SQL statement to execute (INSERT, UPDATE, DELETEююю)
    :param args: Tuple of parameters to substitute into the SQL statement
    :return: The `lastrowid` of the cursor, indicating the row ID of the last inserted row
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, args)
        await db.commit()
        return cur.lastrowid
