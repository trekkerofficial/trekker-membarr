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


conn = create_connection(DB_URL)

def create_main_tables():
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
    conn.commit()

def create_accessory_tables():
    conn.execute(
        f'''CREATE TABLE IF NOT EXISTS "{JELLYFIN_TABLE}_libraries" (
            "role"          TEXT NOT NULL,
            "library_name"	TEXT NOT NULL,
            FOREIGN KEY("role") REFERENCES roles("role") ON DELETE CASCADE,
            PRIMARY KEY("role", "library_name")
        );
        '''
    )
    conn.execute(
        f'''CREATE TABLE IF NOT EXISTS "{JELLYFIN_TABLE}_users" (
            "server_url"	TEXT NOT NULL,
            "discord_userid"       TEXT NOT NULL,
            "jellyfin_username"      TEXT NOT NULL,
            FOREIGN KEY ("server_url") REFERENCES {JELLYFIN_TABLE}("server_url") ON DELETE CASCADE,
            FOREIGN KEY ("discord_userid") REFERENCES clients("discord_userid") ON DELETE CASCADE,
            PRIMARY KEY ("server_url", "discord_userid")
        );
        '''
    )
    conn.commit()

def save_jellyfin_server(server_url, api_key, external_url=None, enabled=True):
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

def add_user(server_url, discord_userid, jellyfin_username):
    if not server_url or not discord_userid or not jellyfin_username:
        print("Error: server_url, discord_userid or jellyfin_username is empty")
        return False
    conn.execute(f'''
        INSERT OR REPLACE INTO "{JELLYFIN_TABLE}_users" (
            "server_url", "discord_userid", "jellyfin_username"
        ) VALUES (
            "{server_url}", "{discord_userid}", "{jellyfin_username}"
        );
    ''')
    conn.commit()
    print("Jellyfin user added to db")
    return True


def add_role(server_url, role):
    if not server_url or not role:
        print("Error: server_url or role is empty")
        return False
    conn.execute(f'''
        INSERT OR REPLACE INTO "roles" (
            "jellyfin_server_url", "role"
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
        DELETE FROM "roles" WHERE "jellyfin_server_url" = "{server_url}" AND "role" = "{role}";
    ''')
    conn.commit()
    print("Jellyfin role removed from db")
    return True


def set_jellyfin_libraries(role, libraries):
    # First remove all existing libraries
    conn.execute(f'''
        DELETE FROM "{JELLYFIN_TABLE}_libraries" WHERE "role" = "{role}";
    ''')

    # handle if libraries is none
    if not libraries:
        libraries = []

    # Then add new libraries
    for library in libraries:
        conn.execute(f'''
            INSERT OR REPLACE INTO "{JELLYFIN_TABLE}_libraries" (
                "role", "library_name"
            ) VALUES (
                "{role}", "{library}"
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

def get_jellyfin_server(server_url):
    return conn.execute(f'''
        SELECT * FROM "{JELLYFIN_TABLE}" WHERE "server_url" = "{server_url}";
    ''').fetchone()


def get_jellyfin_libraries(role):
    return set(map(
        lambda row: row[0],
        conn.execute(f'''
        SELECT library_name FROM "{JELLYFIN_TABLE}_libraries" WHERE "role" = "{role}";
    ''').fetchall()))


def get_jellyfin_roles(server_url=None) -> set:
    return set(map(
        lambda row: row[0] if server_url else (row[0], row[1]),
        conn.execute(
            f'SELECT role{", jellyfin_server_url" if not server_url else ""} FROM "roles" ' +
            f'WHERE "jellyfin_server_url"' +
            (f' = "{server_url}"' if server_url else ' IS NOT NULL') +
            f';'
            ).fetchall()))


def get_jellyfin_roles_raw(server_url, guild) -> set:
    return set(map(lambda row: discord.utils.get(guild.roles, name=row), get_jellyfin_roles(server_url)))

def get_user(server_url, discord_userid):
    return conn.execute(f'''
        SELECT *
        FROM "{JELLYFIN_TABLE}_users"
        WHERE "server_url" = "{server_url}"
        AND "discord_userid" = "{discord_userid}";
    ''').fetchone()

def enable_server(server_url: bool, enable: bool = True):
    conn.execute(
        f'''
        UPDATE {JELLYFIN_TABLE}
        SET enabled = {"TRUE" if enable else "FALSE"}
        WHERE server_url = '{server_url}'
        '''
    )
    conn.commit()
