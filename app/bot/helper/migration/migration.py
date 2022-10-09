import configparser
import sqlite3
import app.bot.helper.database.JellyfinTable as JellyfinTable

CURRENT_VERSION = 'Membarr V2.0'

# Lookup for what previous versions of the users table looked like
user_table_history = {
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
    ],
    'Membarr V2.0': [
        (0, 'discord_userid', 'TEXT', 1, None, 1)
    ]
}

CONFIG_PATH = 'app/config/config.ini'
BOT_SECTION = 'bot_envs'
DB_URL = 'app/config/app.db'
USER_TABLE = 'clients'      # I HATE THAT THIS IS CALLED CLIENTS ARGH


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Connected to db")
    except Exception as e:
        print("error in connecting to db")
    finally:
        return conn


conn = create_connection(DB_URL)
config = configparser.ConfigParser()
config.read(CONFIG_PATH)


def check_table_version(conn, tablename):
    dbcur = conn.cursor()
    dbcur.execute(f"PRAGMA table_info({tablename})")
    table_format = dbcur.fetchall()
    for app_version in user_table_history:
        if user_table_history[app_version] == table_format:
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
        else:
            jellyfin_external_url = None
        if config.has_option(BOT_SECTION, 'jellyfin_roles'):
            jellyfin_roles = config.get(BOT_SECTION, 'jellyfin_roles').split(',');
        if config.has_option(BOT_SECTION, 'jellyfin_libs'):
            jellyfin_libraries = config.get(BOT_SECTION, 'jellyfin_libs').split(',')
        else:
            jellyfin_libraries = []

        if jellyfin_server_url and jellyfin_api_key:
            print("Jellyfin config detected, migrating to database")
            JellyfinTable.save_jellyfin_server(jellyfin_server_url, jellyfin_api_key, jellyfin_external_url,
                                               jellyfin_enabled)

            if jellyfin_roles:
                for role in jellyfin_roles:
                    JellyfinTable.add_jellyfin_role(jellyfin_server_url, role)
                    JellyfinTable.set_jellyfin_libraries(role, jellyfin_libraries)


def migrate_plex_config():
    if config.has_section(BOT_SECTION):
        if config.has_option(BOT_SECTION, 'plex_server_url'):
            plex_server_url = config.get(BOT_SECTION, 'plex_server_url')


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

    if version == 'Membarr V1.1':
        print("Upgrading DB table from Membarr V1.1 to Membarr V2.0")
        # Create temp table
        conn.execute(
        '''CREATE TABLE "membarr_temp_upgrade_table" (
        "discord_userid"	TEXT NOT NULL UNIQUE,
        PRIMARY KEY("discord_userid")
        );''')
        conn.execute(f'''
        INSERT INTO membarr_temp_upgrade_table(discord_userid)
        SELECT discord_username
        FROM {tablename};
        ''')
        conn.execute(f'''
        DROP TABLE {tablename};
        ''')
        conn.execute(f'''
        ALTER TABLE membarr_temp_upgrade_table RENAME TO {tablename}
        ''')
        conn.commit()
        version = 'Membarr V2.0'

    print('------')


def upgrade_db():
    update_user_table()
    JellyfinTable.create_tables()
    migrate_jellyfin_config()
