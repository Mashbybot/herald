import sqlite3
import logging
from config.settings import DATABASE_PATH

logger = logging.getLogger('Herald.Database')

def get_db_connection():
    """Get a database connection with Row factory for dictionary-like access"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_schema_version():
    """Get the current database schema version"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_info ORDER BY version DESC LIMIT 1")
        result = cur.fetchone()
        conn.close()
        return result['version'] if result else 0
    except sqlite3.OperationalError:
        # schema_info table doesn't exist yet
        return 0

def set_schema_version(version: int):
    """Set the database schema version"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO schema_info (version, updated_at) VALUES (?, datetime('now'))")
    cur.execute("INSERT OR REPLACE INTO schema_info (version, updated_at) VALUES (?, datetime('now'))", (version,))
    conn.commit()
    conn.close()

def init_db():
    """Initialize database with proper schema and migrations"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create schema versioning table first
        cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_info (
            version INTEGER PRIMARY KEY,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        current_version = get_schema_version()
        logger.info(f"Current database schema version: {current_version}")
        
        # Run migrations
        if current_version < 1:
            logger.info("Running migration to version 1...")
            migrate_to_v1(cur)
            
        if current_version < 2:
            logger.info("Running migration to version 2...")
            migrate_to_v2(cur)
            
        if current_version < 3:
            logger.info("Running migration to version 3...")
            migrate_to_v3(cur)
            
        # Set current version to 3
        cur.execute("INSERT OR REPLACE INTO schema_info (version, updated_at) VALUES (?, datetime('now'))", (3,))
        
        conn.commit()
        logger.info("Database initialization complete")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def migrate_to_v1(cur):
    """Migration to version 1: Initial schema"""
    
    # Character sheet schema matching Hunter v5 attributes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        strength INTEGER DEFAULT 1 CHECK(strength >= 1 AND strength <= 5),
        dexterity INTEGER DEFAULT 1 CHECK(dexterity >= 1 AND dexterity <= 5),
        stamina INTEGER DEFAULT 1 CHECK(stamina >= 1 AND stamina <= 5),
        charisma INTEGER DEFAULT 1 CHECK(charisma >= 1 AND charisma <= 5),
        manipulation INTEGER DEFAULT 1 CHECK(manipulation >= 1 AND manipulation <= 5),
        composure INTEGER DEFAULT 1 CHECK(composure >= 1 AND composure <= 5),
        intelligence INTEGER DEFAULT 1 CHECK(intelligence >= 1 AND intelligence <= 5),
        wits INTEGER DEFAULT 1 CHECK(wits >= 1 AND wits <= 5),
        resolve INTEGER DEFAULT 1 CHECK(resolve >= 1 AND resolve <= 5),
        health INTEGER DEFAULT 0,
        willpower INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, name)
    );
    """)
    
    # Skills table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        character_name TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        dots INTEGER DEFAULT 0 CHECK(dots >= 0 AND dots <= 5),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, character_name, skill_name),
        FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
    );
    """)
    
    # Create indexes for common queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_characters_user_id ON characters(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_characters_user_name ON characters(user_id, name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_skills_user_char ON skills(user_id, character_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_skills_user_char_skill ON skills(user_id, character_name, skill_name);")

def migrate_to_v2(cur):
    """Migration to version 2: Add damage tracking"""
    
    # Check if damage columns already exist
    cur.execute("PRAGMA table_info(characters)")
    columns = [row[1] for row in cur.fetchall()]
    
    damage_columns = ['health_sup', 'health_agg', 'willpower_sup', 'willpower_agg']
    
    for column in damage_columns:
        if column not in columns:
            logger.info(f"Adding {column} column to characters table")
            cur.execute(f"""
            ALTER TABLE characters 
            ADD COLUMN {column} INTEGER DEFAULT 0 CHECK({column} >= 0);
            """)
    
    # Add trigger to update updated_at timestamp
    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS update_characters_timestamp 
    AFTER UPDATE ON characters
    BEGIN
        UPDATE characters SET updated_at = datetime('now') WHERE id = NEW.id;
    END;
    """)
    
    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS update_skills_timestamp 
    AFTER UPDATE ON skills
    BEGIN
        UPDATE skills SET updated_at = datetime('now') WHERE id = NEW.id;
    END;
    """)

def migrate_to_v3(cur):
    """Migration to version 3: Add H5E mechanics (Desperation, Edge, Creed)"""
    
    # Check if H5E columns already exist
    cur.execute("PRAGMA table_info(characters)")
    columns = [row[1] for row in cur.fetchall()]
    
    h5e_columns = {
        'desperation': 'INTEGER DEFAULT 0 CHECK(desperation >= 0 AND desperation <= 10)',
        'edge': 'INTEGER DEFAULT 0 CHECK(edge >= 0 AND edge <= 5)', 
        'creed': 'TEXT DEFAULT NULL'
    }
    
    for column, definition in h5e_columns.items():
        if column not in columns:
            logger.info(f"Adding {column} column to characters table")
            cur.execute(f"""
            ALTER TABLE characters 
            ADD COLUMN {column} {definition};
            """)

def backup_database(backup_path: str = None):
    """Create a backup of the database"""
    if not backup_path:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{DATABASE_PATH}.backup_{timestamp}"
    
    try:
        source = get_db_connection()
        backup = sqlite3.connect(backup_path)
        source.backup(backup)
        backup.close()
        source.close()
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        raise

def get_database_stats():
    """Get database statistics for monitoring"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    stats = {}
    
    # Character count
    cur.execute("SELECT COUNT(*) as count FROM characters")
    stats['characters'] = cur.fetchone()['count']
    
    # Skills count  
    cur.execute("SELECT COUNT(*) as count FROM skills")
    stats['skills'] = cur.fetchone()['count']
    
    # User count
    cur.execute("SELECT COUNT(DISTINCT user_id) as count FROM characters")
    stats['users'] = cur.fetchone()['count']
    
    # Database size
    cur.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    stats['size_bytes'] = cur.fetchone()['size']
    
    conn.close()
    return stats

def cleanup_orphaned_skills():
    """Clean up skills that don't have corresponding characters"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
    DELETE FROM skills 
    WHERE NOT EXISTS (
        SELECT 1 FROM characters 
        WHERE characters.user_id = skills.user_id 
        AND characters.name = skills.character_name
    )
    """)
    
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} orphaned skill records")
    
    return deleted

def vacuum_database():
    """Optimize database by running VACUUM"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)  # Don't use Row factory for VACUUM
        conn.execute("VACUUM")
        conn.close()
        logger.info("Database vacuumed successfully")
    except Exception as e:
        logger.error(f"Database vacuum failed: {e}")
        raise
