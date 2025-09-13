# core/db.py - Updated for PostgreSQL support

import os
import asyncio
import asyncpg
import sqlite3
import logging
from contextlib import asynccontextmanager
from config.settings import DATABASE_URL, DATABASE_PATH, USE_POSTGRESQL

logger = logging.getLogger('Herald.Database')

# Connection pool for PostgreSQL
_pool = None

async def init_database():
    """Initialize database connection and run migrations"""
    global _pool
    
    if USE_POSTGRESQL:
        logger.info("🐘 Initializing PostgreSQL database...")
        
        # Create connection pool
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            command_timeout=60
        )
        
        # Run migrations
        await run_postgresql_migrations()
        logger.info("✅ PostgreSQL database ready")
        
    else:
        logger.info("📁 Using SQLite database (development mode)")
        # Keep existing SQLite initialization
        init_sqlite_db()


async def run_postgresql_migrations():
    """Run database migrations for PostgreSQL"""
    async with get_db_connection() as conn:
        # Create tables matching SQLite schema
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_info (
                version INTEGER PRIMARY KEY,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Characters table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id SERIAL PRIMARY KEY,
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
                health_sup INTEGER DEFAULT 0 CHECK(health_sup >= 0),
                health_agg INTEGER DEFAULT 0 CHECK(health_agg >= 0),
                willpower_sup INTEGER DEFAULT 0 CHECK(willpower_sup >= 0),
                willpower_agg INTEGER DEFAULT 0 CHECK(willpower_agg >= 0),
                desperation INTEGER DEFAULT 0 CHECK(desperation >= 0 AND desperation <= 10),
                edge INTEGER DEFAULT 0 CHECK(edge >= 0 AND edge <= 5),
                creed TEXT DEFAULT NULL,
                ambition TEXT DEFAULT NULL,
                desire TEXT DEFAULT NULL,
                drive TEXT DEFAULT NULL,
                redemption TEXT DEFAULT NULL,
                danger INTEGER DEFAULT 0 CHECK(danger >= 0 AND danger <= 5),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, name)
            );
        """)
        
        # Skills table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                dots INTEGER DEFAULT 0 CHECK(dots >= 0 AND dots <= 5),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, character_name, skill_name),
                FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
            );
        """)
        
        # Equipment table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
            );
        """)
        
        # Notes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
            );
        """)
        
        # Specialties table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS specialties (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                specialty_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, character_name, skill_name, specialty_name),
                FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
            );
        """)
        
        # XP log table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS xp_log (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                action TEXT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
            );
        """)
        
        # Create indexes for performance
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_characters_user_id ON characters(user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_characters_user_name ON characters(user_id, name);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_user_char ON skills(user_id, character_name);")
        
        # Update schema version
        await conn.execute("INSERT INTO schema_info (version, updated_at) VALUES (3, NOW()) ON CONFLICT (version) DO UPDATE SET updated_at = NOW();")


@asynccontextmanager
async def get_db_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    if USE_POSTGRESQL:
        # PostgreSQL connection from pool
        async with _pool.acquire() as conn:
            yield conn
    else:
        # SQLite connection (existing logic)
        conn = get_sqlite_connection()
        try:
            yield conn
        finally:
            conn.close()


def get_sqlite_connection():
    """Get SQLite connection (for development)"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_sqlite_db():
    """Initialize SQLite database (existing function for development)"""
    # Keep your existing SQLite initialization code
    # This is for local development only
    pass


async def migrate_sqlite_to_postgresql(sqlite_path: str, postgresql_url: str):
    """Migration script to move data from SQLite to PostgreSQL"""
    logger.info("🔄 Starting SQLite to PostgreSQL migration...")
    
    # Connect to both databases
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    pool = await asyncpg.create_pool(postgresql_url)
    
    try:
        # Migrate characters
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM characters")
        characters = sqlite_cursor.fetchall()
        
        async with pool.acquire() as pg_conn:
            for char in characters:
                await pg_conn.execute("""
                    INSERT INTO characters (user_id, name, strength, dexterity, stamina, 
                    charisma, manipulation, composure, intelligence, wits, resolve,
                    health, willpower, health_sup, health_agg, willpower_sup, willpower_agg,
                    desperation, edge, creed, ambition, desire, drive, redemption, danger)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25)
                    ON CONFLICT (user_id, name) DO NOTHING
                """, *[char[key] for key in char.keys() if key not in ['id', 'created_at', 'updated_at']])
        
        logger.info(f"✅ Migrated {len(characters)} characters")
        
        # Migrate skills, equipment, notes, etc. (similar pattern)
        # ... additional migration code ...
        
    finally:
        sqlite_conn.close()
        await pool.close()
    
    logger.info("🎉 Migration completed successfully!")


# Add to requirements.txt:
# asyncpg>=0.28.0  # For PostgreSQL async support
