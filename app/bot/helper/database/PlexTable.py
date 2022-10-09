import sqlite3


DB_URL = 'app/config/app.db'
PLEX_TABLE = 'plex_servers'

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
    dbcur.execute("""SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{0}';""".format(tablename.replace('\'', '\'\'')))
    if dbcur.fetchone()[0] == 1:
        dbcur.close()
        return True
    dbcur.close()
    return False

conn = create_connection(DB_URL)

def create_main_tables():
    conn.execute(
        f'''CREATE TABLE IF NOT EXISTS "{PLEX_TABLE}" (
            "server_url"	TEXT NOT NULL UNIQUE,
            "token"	        TEXT NOT NULL,
            "enabled"       BOOLEAN NOT NULL,
            PRIMARY KEY("server_url")
        );''')
    conn.commit()

def create_accessory_tables():
    conn.execute(
        f'''CREATE TABLE IF NOT EXISTS "{PLEX_TABLE}_libraries" (
            "role"          TEXT NOT NULL,
            "library_name"	TEXT NOT NULL,
            FOREIGN KEY("role") REFERENCES roles("role") ON DELETE CASCADE,
            PRIMARY KEY("role", "library_name")
        );
        '''
    )
    conn.execute(
        f'''CREATE TABLE IF NOT EXISTS "{PLEX_TABLE}_users" (
            "server_url"	    TEXT NOT NULL,
            "discord_userid"	TEXT NOT NULL,
            "plex_email"	    TEXT NOT NULL,
            FOREIGN KEY("server_url") REFERENCES {PLEX_TABLE}("server_url") ON DELETE CASCADE,
            FOREIGN KEY("discord_userid") REFERENCES clients("discord_userid") ON DELETE CASCADE,
            PRIMARY KEY("server_url", "discord_userid")
        );
        '''
    )
    conn.commit()

def save_plex_server(server_url, token, enabled=True):
    if not server_url or not token:
        print("Error: server_url or token is empty")
        return False
    conn.execute(f'''
        INSERT OR REPLACE INTO "{PLEX_TABLE}" (
            "server_url", "token", "enabled"
        ) VALUES (
            "{server_url}", "{token}", "{enabled}"
        );
    ''')
    conn.commit()
    print("Plex server added to db")
    return True

def delete_plex_server(server_url):
    if not server_url:
        print("Error: server_url is empty")
        return False
    conn.execute(f'''
        DELETE FROM "{PLEX_TABLE}" WHERE "server_url" = "{server_url}"
    ''')
    conn.commit()
    print("Plex server removed from db")
    return True

def add_plex_role(server_url, role):
    if not server_url or not role:
        print("Error: server_url or role is empty")
        return False
    conn.execute(f'''
        INSERT OR REPLACE INTO "{PLEX_TABLE}_roles" (
            "server_url",
            "role"
        ) VALUES (
            "{server_url}",
            "{role}"
        );
    ''')
    conn.commit()
    print("Plex role added to db")
    return True

def remove_plex_role(server_url, role):
    if not server_url or not role:
        print("Error: server_url or role is empty")
        return False
    conn.execute(f'''
        DELETE FROM "{PLEX_TABLE}_roles" WHERE "server_url" = "{server_url}" AND "role" = "{role}"
    ''')
    conn.commit()
    print("Plex role removed from db")
    return True

def set_plex_libraries(server_url, libraries):
    if not server_url:
        print("Error: server_url is empty")
        return False
    # First remove all existing libraries
    conn.execute(f'''
        DELETE FROM "{PLEX_TABLE}_libraries" WHERE "server_url" = "{server_url}"
    ''')

    # Then add back the new ones
    for library in libraries:
        conn.execute(f'''
            INSERT OR REPLACE INTO "{PLEX_TABLE}_libraries" (
                "server_url",
                "library_name"
            ) VALUES (
                "{server_url}",
                "{library}"
            );
        ''')
    conn.commit()
    print("Plex libraries set")

