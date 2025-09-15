# core/db.py - Fixed for PostgreSQL with proper sync wrapper - Version 2

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
    async with get_async_connection() as conn:
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
async def get_async_connection():
    """Get async database connection (PostgreSQL or SQLite)"""
    if USE_POSTGRESQL:
        # PostgreSQL connection from pool
        async with _pool.acquire() as conn:
            yield conn
    else:
        # For SQLite, we'd need aiosqlite, but for now just raise an error
        raise RuntimeError("Async SQLite connections not implemented. Use get_db_connection() for sync SQLite.")

def get_db_connection():
    """
    Get synchronous database connection.
    This is the main function that should be used by all cogs.
    Returns a connection that works like SQLite for compatibility.
    """
    if USE_POSTGRESQL:
        # For PostgreSQL in production, we need to wrap async calls
        return PostgreSQLSyncWrapper()
    else:
        # SQLite for development
        return get_sqlite_connection()

class PostgreSQLSyncWrapper:
    """
    Wrapper to make PostgreSQL work with sync code patterns.
    This allows existing SQLite-style code to work with PostgreSQL.
    """
    
    def __init__(self):
        self._connection = None
        self._should_release = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _get_connection_sync(self):
        """Get connection synchronously"""
        if self._connection is None:
            if _pool is None:
                raise RuntimeError("Database pool not initialized. Make sure init_database() was called.")
            
            # Get the current event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, but we need sync behavior
                # Create a new event loop in a thread
                import concurrent.futures
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(_pool.acquire())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    self._connection = future.result()
                    
            except RuntimeError:
                # No event loop running, we can use asyncio.run
                async def acquire():
                    return await _pool.acquire()
                
                self._connection = asyncio.run(acquire())
            
            self._should_release = True
        
        return self._connection
    
    def cursor(self):
        """Return a cursor-like object for PostgreSQL"""
        conn = self._get_connection_sync()
        return PostgreSQLCursorWrapper(conn)
    
    def commit(self):
        """Commit transaction (no-op for PostgreSQL autocommit)"""
        pass
    
    def rollback(self):
        """Rollback transaction"""
        pass
    
    def close(self):
        """Close connection"""
        if self._connection and self._should_release:
            if _pool:
                # Release connection back to pool
                try:
                    loop = asyncio.get_running_loop()
                    # Create task to release later
                    loop.create_task(_pool.release(self._connection))
                except RuntimeError:
                    # No loop running, use asyncio.run
                    async def release():
                        await _pool.release(self._connection)
                    asyncio.run(release())
            
            self._connection = None
            self._should_release = False

class PostgreSQLCursorWrapper:
    """
    Cursor wrapper to make PostgreSQL work with SQLite-style cursor code.
    """
    
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 0
        self._last_result = None
    
    def execute(self, query, params=None):
        """Execute query synchronously"""
        try:
            # Convert SQLite ? placeholders to PostgreSQL $1, $2, etc.
            pg_query = self._convert_query(query)
            query_lower = query.lower().strip()
            
            # Run the query synchronously
            if query_lower.startswith(('insert', 'update', 'delete')):
                # For modification queries, use execute
                result = self._run_sync_query(self.connection.execute, pg_query, params)
                self._last_result = []
                # Parse the result to get rowcount
                if isinstance(result, str) and result.startswith(('INSERT', 'UPDATE', 'DELETE')):
                    # PostgreSQL returns strings like "INSERT 0 1" or "UPDATE 3"
                    parts = result.split()
                    if len(parts) >= 2:
                        try:
                            self.rowcount = int(parts[-1])
                        except ValueError:
                            self.rowcount = 1 if result else 0
                    else:
                        self.rowcount = 1 if result else 0
                else:
                    self.rowcount = 1 if result else 0
            else:
                # For select queries, use fetch
                self._last_result = self._run_sync_query(self.connection.fetch, pg_query, params)
                self.rowcount = len(self._last_result) if self._last_result else 0
                    
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            logger.error(f"Original query: {query}")
            logger.error(f"Converted query: {pg_query}")
            logger.error(f"Params: {params}")
            raise
    
    def _run_sync_query(self, coro_func, query, params):
        """Run an async query synchronously"""
        async def run_query():
            if params:
                return await coro_func(query, *params)
            else:
                return await coro_func(query)
        
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, use a thread
            import concurrent.futures
            
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(run_query())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()
                
        except RuntimeError:
            # No event loop running
            return asyncio.run(run_query())
    
    def fetchone(self):
        """Fetch one row"""
        if self._last_result and len(self._last_result) > 0:
            row = self._last_result[0]
            # Convert asyncpg Record to dict for SQLite compatibility
            return dict(row)
        return None
    
    def fetchall(self):
        """Fetch all rows"""
        if self._last_result:
            # Convert asyncpg Records to dicts
            return [dict(row) for row in self._last_result]
        return []
    
    def _convert_query(self, query):
        """Convert SQLite ? placeholders to PostgreSQL $1, $2, etc."""
        if '?' not in query:
            return query
            
        parts = query.split('?')
        if len(parts) == 1:
            return query
        
        result = parts[0]
        for i in range(1, len(parts)):
            result += f"${i}" + parts[i]
        
        return result

def get_sqlite_connection():
    """Get SQLite connection (for development)"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_sqlite_db():
    """Initialize SQLite database (existing function for development)"""
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
        
    finally:
        sqlite_conn.close()
        await pool.close()
    
    logger.info("🎉 Migration completed successfully!")
