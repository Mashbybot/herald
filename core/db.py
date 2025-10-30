# core/db.py - Simplified for async PostgreSQL and sync SQLite

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
        init_sqlite_db()

async def run_postgresql_migrations():
    """Run database migrations for PostgreSQL"""
    async with get_async_db() as conn:
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
                experience_total INTEGER DEFAULT 0,
                experience_spent INTEGER DEFAULT 0,
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
async def get_async_db():
    """Get async database connection for PostgreSQL"""
    if not USE_POSTGRESQL:
        raise RuntimeError("Async connection only available for PostgreSQL. Use get_db_connection() for SQLite.")
    
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Make sure init_database() was called.")
    
    async with _pool.acquire() as conn:
        yield conn

def get_db_connection():
    """Get synchronous database connection - FOR SQLITE ONLY"""
    if USE_POSTGRESQL:
        raise RuntimeError("PostgreSQL requires async operations. Use 'async with get_async_db() as conn' instead.")
    else:
        # SQLite for development
        return get_sqlite_connection()

def get_sqlite_connection():
    """Get SQLite connection (for development)"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_sqlite_db():
    """Initialize SQLite database (for development)"""
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    # Create characters table
    cursor.execute("""
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
            experience_total INTEGER DEFAULT 0,
            experience_spent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        );
    """)
    
    # Create skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            character_name TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            dots INTEGER DEFAULT 0 CHECK(dots >= 0 AND dots <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, character_name, skill_name),
            FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
        );
    """)
    
    # Create equipment table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            character_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
        );
    """)
    
    # Create notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            character_name TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
        );
    """)
    
    # Create specialties table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS specialties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            character_name TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            specialty_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, character_name, skill_name, specialty_name),
            FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
        );
    """)
    
    # Create XP log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            character_name TEXT NOT NULL,
            action TEXT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
        );
    """)
    
    conn.commit()
    conn.close()
    logger.info("📁 SQLite database initialized")
