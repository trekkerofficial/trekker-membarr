import sqlite3


DB_URL = 'app/config/app.db'
JELLYFIN_TABLE = 'jellyfin_servers'

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
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

if checkTableExists(conn, JELLYFIN_TABLE):
    print('Jellyfin table exists.')
else:
    conn.execute(
        f'''CREATE TABLE "{JELLYFIN_TABLE}" (
            "server_url"	TEXT NOT NULL UNIQUE,
            "api_key"	    TEXT NOT NULL,
            "enabled"       BOOLEAN NOT NULL,
            "external_url"  TEXT,
            PRIMARY KEY("server_url")
        );
        '''
    )
    conn.execute(
        f'''CREATE TABLE "{JELLYFIN_TABLE}_libraries" (
            "server_url"	TEXT NOT NULL,
            "library_name"	TEXT NOT NULL,
            PRIMARY KEY("server_url", "library_name")
        );
        '''
    )
    conn.execute(
        f'''CREATE TABLE "{JELLYFIN_TABLE}_roles" (
            "server_url"	TEXT NOT NULL,
            "role"          TEXT NOT NULL,
            FOREIGN KEY("server_url") REFERENCES {JELLYFIN_TABLE}("server_url")
            PRIMARY KEY("server_url", "role")
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
    print("Jellyfin role added to db")
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

def set_jellyfin_libraries(server_url, libraries):
    if not server_url:
        print("Error: server_url is empty")
        return False
    
    # First remove all existing libraries
    conn.execute(f'''
        DELETE FROM "{JELLYFIN_TABLE}_libraries" WHERE "server_url" = "{server_url}";
    ''')

    # Then add new libraries
    for library in libraries:
        conn.execute(f'''
            INSERT OR REPLACE INTO "{JELLYFIN_TABLE}_libraries" (
                "server_url", "library_name"
            ) VALUES (
                "{server_url}", "{library}"
            );
        ''')
    conn.commit()
    print("Jellyfin libraries added to db")
    return True

def get_enabled_jellyfin_servers():
    conn.execute(f'''
        SELECT * FROM "{JELLYFIN_TABLE}" WHERE "enabled" = true;
    ''')
    return conn.fetchall()

def get_jellyfin_libraries(server_url):
    conn.execute(f'''
        SELECT * FROM "{JELLYFIN_TABLE}_libraries" WHERE "server_url" = "{server_url}";
    ''')
    return conn.fetchall()

def get_jellyfin_roles(server_url):
    conn.execute(f'''
        SELECT * FROM "{JELLYFIN_TABLE}_roles" WHERE "server_url" = "{server_url}";
    ''')
    return conn.fetchall()