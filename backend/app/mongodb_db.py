"""MongoDB database implementation with connection pooling and indexes."""

from typing import Any
from urllib.parse import quote_plus

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

from .config import get_settings
from .logger import get_logger


class MongoDBDatabase:
    """MongoDB database wrapper with connection pooling and indexing."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: AsyncIOMotorClient | None = None
        self.db = None
        self.logger = get_logger(__name__)
    
    async def connect(self) -> None:
        """Establish MongoDB connection with connection pooling."""
        if not self.settings.enable_mongodb:
            self.logger.info("MongoDB disabled, using local JSON storage")
            return
        
        try:
            # Properly encode the MongoDB URI
            uri = self.settings.mongodb_uri
            
            # Parse and encode the URI to handle special characters in username/password
            if "://" in uri:
                scheme, rest = uri.split("://", 1)
                if "@" in rest:
                    auth_part, host_part = rest.split("@", 1)
                    if ":" in auth_part:
                        username, password = auth_part.split(":", 1)
                        # URL encode username and password
                        encoded_username = quote_plus(username)
                        encoded_password = quote_plus(password)
                        uri = f"{scheme}://{encoded_username}:{encoded_password}@{host_part}"
            
            self.logger.info(f"Attempting to connect to MongoDB")
            
            self.client = AsyncIOMotorClient(
                uri,
                maxPoolSize=50,
                minPoolSize=5,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            self.db = self.client[self.settings.mongodb_db_name]
            self.logger.info(f"Connected to MongoDB: {self.settings.mongodb_db_name}")
            
            # Create indexes
            await self._create_indexes()
            
        except ConnectionFailure as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            self.logger.warning("Falling back to local JSON storage")
            raise
        except OperationFailure as e:
            self.logger.error(f"MongoDB operation failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to MongoDB: {e}")
            self.logger.warning("Falling back to local JSON storage")
            raise
    
    async def _create_indexes(self) -> None:
        """Create database indexes for optimal query performance."""
        if not self.db:
            return
        
        try:
            # Users collection indexes
            await self.db.users.create_indexes([
                IndexModel([("username", ASCENDING)], unique=True),
                IndexModel([("created_at", DESCENDING)]),
            ])
            
            # Refresh sessions indexes
            await self.db.refresh_sessions.create_indexes([
                IndexModel([("jti", ASCENDING)], unique=True),
                IndexModel([("username", ASCENDING)]),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
            ])
            
            # Occupancy logs indexes
            await self.db.occupancy_logs.create_indexes([
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("timestamp", DESCENDING)]),
                IndexModel([("classroom", ASCENDING)]),
                IndexModel([("course_code", ASCENDING)]),
                IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("classroom", ASCENDING), ("course_code", ASCENDING)]),
            ])
            
            self.logger.info("Database indexes created successfully")
            
        except OperationFailure as e:
            self.logger.warning(f"Failed to create some indexes: {e}")
    
    async def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed")
    
    @property
    def users(self):
        """Users collection."""
        if not self.db:
            raise RuntimeError("Database not connected")
        return self.db.users
    
    @property
    def refresh_sessions(self):
        """Refresh sessions collection."""
        if not self.db:
            raise RuntimeError("Database not connected")
        return self.db.refresh_sessions
    
    @property
    def occupancy_logs(self):
        """Occupancy logs collection."""
        if not self.db:
            raise RuntimeError("Database not connected")
        return self.db.occupancy_logs


# Global MongoDB instance
mongodb = MongoDBDatabase()


async def get_mongodb() -> MongoDBDatabase:
    """Get MongoDB database instance."""
    if not mongodb.db and mongodb.settings.enable_mongodb:
        await mongodb.connect()
    return mongodb
