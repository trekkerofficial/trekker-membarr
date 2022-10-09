import sqlite3
from app.bot.helper.database.JellyfinTable import JELLYFIN_TABLE
from app.bot.helper.database.PlexTable import PLEX_TABLE

DB_URL = 'app/config/app.db'

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA foreign_keys = ON")
        print("Connected to db")
    except Exception as e:
        print("error in connecting to db")
    finally:
        if conn:
            return conn


def create_table():
    conn = create_connection(DB_URL)
    conn.execute(
        f'''CREATE TABLE IF NOT EXISTS "roles" (
            "role"                  TEXT NOT NULL UNIQUE,
            "jellyfin_server_url"	TEXT,
            "plex_server_url"	    TEXT,
            FOREIGN KEY("jellyfin_server_url") REFERENCES {JELLYFIN_TABLE}("server_url") ON DELETE CASCADE,
            FOREIGN KEY("plex_server_url") REFERENCES {PLEX_TABLE}("server_url") ON DELETE CASCADE,
            PRIMARY KEY("role")
            CHECK(
                (jellyfin_server_url IS NULL OR plex_server_url IS NULL) AND 
                (jellyfin_server_url IS NOT NULL OR plex_server_url IS NOT NULL)
            )
        );
        '''
    )