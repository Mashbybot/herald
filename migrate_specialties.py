# migrate_specialties.py
import sys
import os

# Add the project directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_specialties_table():
    """Create the specialties table if it doesn't exist"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create specialties table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS specialties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                specialty_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE,
                UNIQUE(user_id, character_name, skill_name, specialty_name)
            )
        """)
        
        # Create index for faster lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_specialties_character 
            ON specialties(user_id, character_name)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Specialties table created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating specialties table: {e}")

if __name__ == "__main__":
    print("Creating specialties table...")
    create_specialties_table()
    print("Migration complete!")
