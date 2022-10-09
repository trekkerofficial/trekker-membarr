import sqlite3

DB_URL = 'app/config/app.db'
DB_TABLE = 'clients'    # user table (honestly should be called users but whatever, it's not important)

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

# Checking if table exists
if checkTableExists(conn, DB_TABLE):
	print('User Table exists.')
else:
    conn.execute(
    f'''CREATE TABLE "{DB_TABLE}" (
        "id"	INTEGER NOT NULL UNIQUE,
        "discord_username"	TEXT NOT NULL UNIQUE,
        "email"	TEXT,
        "jellyfin_username" TEXT,
        PRIMARY KEY("id" AUTOINCREMENT)
    );''')

def save_user_email(username, email):
    if username and email:
        conn.execute(f"""
            INSERT OR REPLACE INTO clients(discord_username, email)
            VALUES('{username}', '{email}')
        """)
        conn.commit()
        print("User added to db.")
    else:
        return "Username and email cannot be empty"

def save_user(userid):
    userid = str(userid)
    if userid:
        conn.execute("INSERT OR IGNORE INTO clients (discord_userid) VALUES ('" + userid + "')")
        conn.commit()
        print("User added to db.")
    else:
        return "Username cannot be empty"


def delete_user(userid):
    if userid:
        try:
            conn.execute('DELETE from clients where discord_userid="{}";'.format(userid))
            conn.commit()
            return True
        except:
            return False
    else:
        return "username cannot be empty"

def read_all():
    cur = conn.cursor()
    cur.execute("SELECT * FROM clients")
    rows = cur.fetchall()
    all = []
    for row in rows:
        all.append(row)
    return all

