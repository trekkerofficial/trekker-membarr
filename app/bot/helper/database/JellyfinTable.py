import sqlite3
import discord

DB_URL = 'app/config/app.db'
JELLYFIN_TABLE = 'jellyfin_servers'


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


def checkTableExists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("""SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{0}';""".format(
        tablename.replace('\'', '\'\'')))
    if dbcur.fetchone()[0] == 1:
        dbcur.close()
        return True
    dbcur.close()
    return False


conn = create_connection(DB_URL)

conn.execute(
    f'''CREATE TABLE IF NOT EXISTS "{JELLYFIN_TABLE}" (
        "server_url"	TEXT NOT NULL UNIQUE,
        "api_key"	    TEXT NOT NULL,
        "enabled"       BOOLEAN NOT NULL,
        "external_url"  TEXT,
        PRIMARY KEY("server_url")
    );
    '''
)
conn.execute(
    f'''CREATE TABLE IF NOT EXISTS "{JELLYFIN_TABLE}_roles" (
        "server_url"	TEXT NOT NULL,
        "role"          TEXT NOT NULL,
        FOREIGN KEY("server_url") REFERENCES {JELLYFIN_TABLE}("server_url") ON DELETE CASCADE,
        PRIMARY KEY("server_url", "role")
    );
    '''
)
conn.execute(
    f'''CREATE TABLE IF NOT EXISTS "{JELLYFIN_TABLE}_libraries" (
        "server_url"	TEXT NOT NULL,
        "role"          TEXT NOT NULL,
        "library_name"	TEXT NOT NULL,
        FOREIGN KEY("server_url", "role") REFERENCES {JELLYFIN_TABLE}_roles("server_url", "role") ON DELETE CASCADE,
        PRIMARY KEY("server_url", "role", "library_name")
    );
    '''
)


def save_jellyfin_server(server_url, api_key, enabled=True, external_url=None):
    if not server_url or not api_key:
        print("Error: server_url or api_key is empty")
        return False
    if external_url is None:
        external_url = server_url
    conn.execute(f'''
        INSERT OR REPLACE INTO "{JELLYFIN_TABLE}" (
            "server_url", "api_key", "enabled", "external_url"
        ) VALUES (
            "{server_url}", "{api_key}", "{enabled}", "{external_url}"
        );
    ''')
    conn.commit()
    print("Jellyfin server added to db")
    return True


def delete_jellyfin_server(server_url):
    conn.execute(f'''
        DELETE FROM "{JELLYFIN_TABLE}" WHERE "server_url" = "{server_url}";
    ''')
    conn.commit()
    print("Jellyfin server deleted from db")
    return True


def add_jellyfin_role(server_url, role):
    if not server_url or not role:
        print("Error: server_url or role is empty")
        return False
    conn.execute(f'''
        INSERT OR REPLACE INTO "{JELLYFIN_TABLE}_roles" (
            "server_url", "role"
        ) VALUES (
            "{server_url}", "{role}"
        );
    ''')
    conn.commit()
    print(f"Jellyfin role {role} added to db")
    return True


def remove_jellyfin_role(server_url, role):
    if not server_url or not role:
        print("Error: server_url or role is empty")
        return False
    conn.execute(f'''
        DELETE FROM "{JELLYFIN_TABLE}_roles" WHERE "server_url" = "{server_url}" AND "role" = "{role}";
    ''')
    conn.commit()
    print("Jellyfin role removed from db")
    return True


def set_jellyfin_libraries(server_url, role, libraries):
    if not server_url:
        print("Error: server_url is empty")
        return False

    # First remove all existing libraries
    conn.execute(f'''
        DELETE FROM "{JELLYFIN_TABLE}_libraries" WHERE "server_url" = "{server_url}" and "role" = "{role}";
    ''')

    # handle if libraries is none
    if not libraries:
        libraries = []

    # Then add new libraries
    for library in libraries:
        conn.execute(f'''
            INSERT OR REPLACE INTO "{JELLYFIN_TABLE}_libraries" (
                "server_url", "role", "library_name"
            ) VALUES (
                "{server_url}", "{role}", "{library}"
            );
        ''')
    conn.commit()
    print(f"Jellyfin libraries {libraries} added to db")
    return True


def get_enabled_jellyfin_servers():
    return list(map(
        lambda row: row[0],
        conn.execute(f'''
        SELECT server_url FROM "{JELLYFIN_TABLE}" WHERE "enabled" = true;
    ''').fetchall()))


def get_all_jellyfin_servers(raw: bool=False):
    return set(map(
        lambda row: (row[0], row[1], row[2], row[3]) if raw else row[0],
        conn.execute(f'''
            SELECT {"*" if raw else "server_url"} FROM "{JELLYFIN_TABLE}";
        ''').fetchall()))


def get_jellyfin_libraries(server_url, role):
    return set(map(
        lambda row: row[0],
        conn.execute(f'''
        SELECT library_name FROM "{JELLYFIN_TABLE}_libraries" WHERE "server_url" = "{server_url}" and "role" = "{role}";
    ''').fetchall()))


def get_jellyfin_roles(server_url) -> set:
    return set(map(
        lambda row: row[0],
        conn.execute(f'''
        SELECT role FROM "{JELLYFIN_TABLE}_roles" WHERE "server_url" = "{server_url}";
    ''').fetchall()))


def get_jellyfin_roles_raw(server_url, guild) -> set:
    return set(map(lambda row: discord.utils.get(guild.roles, name=row), get_jellyfin_roles(server_url)))


def enable_server(server_url: bool, enable: bool = True):
    conn.execute(
        f'''
        UPDATE {JELLYFIN_TABLE}
        SET enabled = {"TRUE" if enable else "FALSE"}
        WHERE server_url = '{server_url}'
        '''
    )
    conn.commit()
