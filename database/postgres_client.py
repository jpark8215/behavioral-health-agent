"""
Simple PostgreSQL client for behavioral health app
"""
import os
import logging
import asyncpg
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class PostgresClient:
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self.database = os.getenv("POSTGRES_DB", "postgres")
        
        if not self.password:
            raise ValueError("POSTGRES_PASSWORD must be set")
        
        self.pool = None
        logger.info(f"PostgreSQL client configured for {self.host}:{self.port}")
    
    async def connect(self):
        """Initialize connection pool"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    min_size=1,
                    max_size=10
                )
                await self._create_tables()
                logger.info("PostgreSQL connection pool created")
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL pool: {e}")
                raise
    
    async def _create_tables(self):
        """Create necessary tables if they don't exist"""
        create_sessions_table = """
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            summary TEXT,
            diagnosis TEXT,
            content_hash VARCHAR(64),
            audio_file_path TEXT,
            transcript TEXT,
            metadata JSONB DEFAULT '{}'::jsonb
        );
        """
        
        create_index = """
        CREATE INDEX IF NOT EXISTS idx_sessions_content_hash ON sessions(content_hash);
        CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_sessions_table)
            await conn.execute(create_index)
            logger.info("Database tables created/verified")
    
    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session"""
        if self.pool is None:
            await self.connect()
        
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Prepare metadata with key_points and treatment_plan
        metadata = session_data.get("metadata", {}).copy()
        if "key_points" in session_data:
            metadata["key_points"] = session_data["key_points"]
        if "treatment_plan" in session_data:
            metadata["treatment_plan"] = session_data["treatment_plan"]
        
        query = """
        INSERT INTO sessions (id, created_at, updated_at, summary, diagnosis, content_hash, audio_file_path, transcript, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *;
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                session_id,
                now,
                now,
                session_data.get("summary"),
                session_data.get("diagnosis"),
                session_data.get("content_hash"),
                session_data.get("audio_file_path"),
                session_data.get("transcript"),
                json.dumps(metadata)
            )
            
            result = dict(row)
            
            # Convert UUID to string for JSON serialization
            if "id" in result:
                result["id"] = str(result["id"])
            
            # Convert datetime to ISO format
            if "created_at" in result and result["created_at"]:
                result["created_at"] = result["created_at"].isoformat()
            if "updated_at" in result and result["updated_at"]:
                result["updated_at"] = result["updated_at"].isoformat()
            
            result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else {}
            
            # Extract key_points and treatment_plan from metadata for backward compatibility
            if "key_points" in result["metadata"]:
                result["key_points"] = result["metadata"]["key_points"]
            if "treatment_plan" in result["metadata"]:
                result["treatment_plan"] = result["metadata"]["treatment_plan"]
            
            logger.info(f"Session created: {session_id}")
            return result
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID"""
        if self.pool is None:
            await self.connect()
        
        query = "SELECT * FROM sessions WHERE id = $1;"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, session_id)
            if row:
                result = dict(row)
                
                # Convert UUID to string for JSON serialization
                if "id" in result:
                    result["id"] = str(result["id"])
                
                # Convert datetime to ISO format
                if "created_at" in result and result["created_at"]:
                    result["created_at"] = result["created_at"].isoformat()
                if "updated_at" in result and result["updated_at"]:
                    result["updated_at"] = result["updated_at"].isoformat()
                
                result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else {}
                
                # Extract key_points and treatment_plan from metadata for backward compatibility
                if "key_points" in result["metadata"]:
                    result["key_points"] = result["metadata"]["key_points"]
                if "treatment_plan" in result["metadata"]:
                    result["treatment_plan"] = result["metadata"]["treatment_plan"]
                
                return result
            return None
    
    async def list_sessions(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """List sessions with pagination"""
        if self.pool is None:
            await self.connect()
        
        count_query = "SELECT COUNT(*) FROM sessions;"
        list_query = """
        SELECT id, created_at, updated_at, summary, diagnosis, content_hash
        FROM sessions 
        ORDER BY created_at DESC 
        LIMIT $1 OFFSET $2;
        """
        
        async with self.pool.acquire() as conn:
            total = await conn.fetchval(count_query)
            rows = await conn.fetch(list_query, limit, skip)
            
            sessions = []
            for row in rows:
                session = dict(row)
                # Convert UUID to string
                if "id" in session:
                    session["id"] = str(session["id"])
                # Convert datetime to ISO format
                if "created_at" in session and session["created_at"]:
                    session["created_at"] = session["created_at"].isoformat()
                if "updated_at" in session and session["updated_at"]:
                    session["updated_at"] = session["updated_at"].isoformat()
                sessions.append(session)
            
            return {
                "sessions": sessions,
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total
            }
    
    async def check_duplicate_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Check if a session with the same content hash exists"""
        if self.pool is None:
            await self.connect()
        
        query = """
        SELECT * FROM sessions 
        WHERE content_hash = $1 
        ORDER BY created_at DESC 
        LIMIT 1;
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, content_hash)
            if row:
                result = dict(row)
                
                # Convert UUID to string for JSON serialization
                if "id" in result:
                    result["id"] = str(result["id"])
                
                # Convert datetime to ISO format
                if "created_at" in result and result["created_at"]:
                    result["created_at"] = result["created_at"].isoformat()
                if "updated_at" in result and result["updated_at"]:
                    result["updated_at"] = result["updated_at"].isoformat()
                
                result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else {}
                
                # Extract key_points and treatment_plan from metadata for backward compatibility
                if "key_points" in result["metadata"]:
                    result["key_points"] = result["metadata"]["key_points"]
                if "treatment_plan" in result["metadata"]:
                    result["treatment_plan"] = result["metadata"]["treatment_plan"]
                
                return result
            return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a session"""
        if self.pool is None:
            await self.connect()
        
        # Build dynamic update query
        set_clauses = ["updated_at = $1"]
        values = [datetime.utcnow()]
        param_count = 2
        
        for key, value in updates.items():
            if key in ["summary", "diagnosis", "content_hash", "audio_file_path", "transcript"]:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
            elif key == "metadata":
                set_clauses.append(f"metadata = ${param_count}")
                values.append(json.dumps(value))
                param_count += 1
        
        values.append(session_id)
        
        query = f"""
        UPDATE sessions 
        SET {', '.join(set_clauses)}
        WHERE id = ${param_count}
        RETURNING *;
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            if row:
                result = dict(row)
                
                # Convert UUID to string for JSON serialization
                if "id" in result:
                    result["id"] = str(result["id"])
                
                # Convert datetime to ISO format
                if "created_at" in result and result["created_at"]:
                    result["created_at"] = result["created_at"].isoformat()
                if "updated_at" in result and result["updated_at"]:
                    result["updated_at"] = result["updated_at"].isoformat()
                
                result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else {}
                
                # Extract key_points and treatment_plan from metadata
                if "key_points" in result["metadata"]:
                    result["key_points"] = result["metadata"]["key_points"]
                if "treatment_plan" in result["metadata"]:
                    result["treatment_plan"] = result["metadata"]["treatment_plan"]
                
                return result
            else:
                raise Exception(f"Session {session_id} not found")
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if self.pool is None:
            await self.connect()
        
        query = "DELETE FROM sessions WHERE id = $1;"
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, session_id)
            return result == "DELETE 1"
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("PostgreSQL connection pool closed")

# Global instance
postgres_client = None

def get_postgres_client() -> PostgresClient:
    """Get or create PostgreSQL client instance"""
    global postgres_client
    if postgres_client is None:
        postgres_client = PostgresClient()
    return postgres_client