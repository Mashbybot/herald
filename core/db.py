import sqlite3
from config.settings import DATABASE_PATH

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Basic character sheet structure — expand as needed
    cur.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        attributes TEXT,  -- JSON string for now
        skills TEXT,
        edges TEXT
    );
    """)
    conn.commit()
    conn.close()
