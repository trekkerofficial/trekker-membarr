import configparser
import sqlite3
import app.bot.helper.db.jellyfin_table as jellyfin_table

CURRENT_VERSION = 'Membarr V1.1'

# Lookup for what previous versions of the users table looked like
table_history = {
    # Original table format as of fork frmo Invitarr
    'Invitarr V1.0': [
        (0, 'id', 'INTEGER', 1, None, 1),
        (1, 'discord_username', 'TEXT', 1, None, 0),
        (2, 'email', 'TEXT', 1, None, 0)
    ],
    'Membarr V1.1': [
        (0, 'id', 'INTEGER', 1, None, 1),
        (1, 'discord_username', 'TEXT', 1, None, 0),
        (2, 'email', 'TEXT', 0, None, 0),
        (3, 'jellyfin_username', 'TEXT', 0, None, 0)
    ]
}

CONFIG_PATH = 'app/config/config.ini'
BOT_SECTION = 'bot_envs'
DB_URL = 'app/config/app.db'
USER_TABLE = 'clients'
JELLYFIN_TABLE = 'jellyfin_servers'
PLEX_TABLE = 'plex_servers'

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
            return 

conn = create_connection(DB_URL)
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

def check_table_version(conn, tablename):
    dbcur = conn.cursor()
    dbcur.execute(f"PRAGMA table_info({tablename})")
    table_format = dbcur.fetchall()
    for app_version in table_history:
        if table_history[app_version] == table_format:
            return app_version
    raise ValueError("Could not identify database table version.")

def migrate_jellyfin_config():
    if config.has_section(BOT_SECTION):
        if config.has_option(BOT_SECTION, 'jellyfin_server_url'):
            jellyfin_server_url = config.get(BOT_SECTION, 'jellyfin_server_url')
        if config.has_option(BOT_SECTION, 'jellyfin_api_key'):
            jellyfin_api_key = config.get(BOT_SECTION, 'jellyfin_api_key')
        if config.has_option(BOT_SECTION, 'jellyfin_enabled'):
            jellyfin_enabled = config.get(BOT_SECTION, 'jellyfin_enabled')
        if config.has_option(BOT_SECTION, 'jellyfin_external_url'):
            jellyfin_external_url = config.get(BOT_SECTION, 'jellyfin_external_url')
        else: jellyfin_external_url = None

        if jellyfin_server_url and jellyfin_api_key:
            print("Jellyfin config detected, migrating to database")
            jellyfin_table.save_jellyfin_server(jellyfin_server_url, jellyfin_api_key, jellyfin_enabled, jellyfin_external_url)
        
        if config.has_option(BOT_SECTION, 'plex_server_url'):
            

def update_user_table():
    tablename = USER_TABLE
    version = check_table_version(conn, tablename)
    print('------')
    print(f'DB table version: {version}')
    if version == CURRENT_VERSION:
        print('DB table up to date!')
        print('------')
        return

    # Table NOT up to date.
    # Update to Membarr V1.1 table
    if version == 'Invitarr V1.0':
        print("Upgrading DB table from Invitarr v1.0 to Membarr V1.1")
        # Create temp table
        conn.execute(
        '''CREATE TABLE "membarr_temp_upgrade_table" (
        "id"	INTEGER NOT NULL UNIQUE,
        "discord_username"	TEXT NOT NULL UNIQUE,
        "email"	TEXT,
        "jellyfin_username" TEXT,
        PRIMARY KEY("id" AUTOINCREMENT)
        );''')
        conn.execute(f'''
        INSERT INTO membarr_temp_upgrade_table(id, discord_username, email)
        SELECT id, discord_username, email
        FROM {tablename};
        ''')
        conn.execute(f'''
        DROP TABLE {tablename};
        ''')
        conn.execute(f'''
        ALTER TABLE membarr_temp_upgrade_table RENAME TO {tablename}
        ''')
        conn.commit()
        version = 'Membarr V1.1'

    print('------')

def update_data():
    update_user_table()