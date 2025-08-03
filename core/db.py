import sqlite3
from config.settings import DATABASE_PATH

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Character sheet schema matching Hunter v5 attributes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        strength INTEGER DEFAULT 1,
        dexterity INTEGER DEFAULT 1,
        stamina INTEGER DEFAULT 1,
        charisma INTEGER DEFAULT 1,
        manipulation INTEGER DEFAULT 1,
        composure INTEGER DEFAULT 1,
        intelligence INTEGER DEFAULT 1,
        wits INTEGER DEFAULT 1,
        resolve INTEGER DEFAULT 1,
        health INTEGER DEFAULT 0,
        willpower INTEGER DEFAULT 0
    );
    """)

    # Skills table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        character_name TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        dots INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()
