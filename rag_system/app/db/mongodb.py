from typing import Optional, List, Dict, Any
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from bson.errors import InvalidId

from app.core.config import settings
from app.models.agent import Agent, AgentCreate, AgentUpdate
from app.models.api_key import APIKey, APIKeyCreate
from app.models.file import File, FileCreate


class MongoDB:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.db = self.client[settings.mongodb_database]
        await self.create_indexes()
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
    
    async def create_indexes(self):
        """Create required indexes"""
        # Agents collection indexes
        await self.db.agents.create_index("name", unique=True)
        await self.db.agents.create_index("is_active")
        
        # API Keys collection indexes
        await self.db.api_keys.create_index("key_hash", unique=True)
        await self.db.api_keys.create_index([("agent_id", 1), ("is_active", 1)])
        
        # Files collection indexes
        await self.db.files.create_index([("agent_id", 1), ("is_deleted", 1)])
        await self.db.files.create_index("created_at")
    
    # Agent methods
    async def create_agent(self, agent_data: AgentCreate) -> Agent:
        """Create a new agent"""
        agent_dict = agent_data.model_dump()
        agent_dict["created_at"] = datetime.utcnow()
        agent_dict["updated_at"] = datetime.utcnow()
        
        result = await self.db.agents.insert_one(agent_dict)
        agent_dict["_id"] = result.inserted_id
        
        return Agent(**agent_dict)
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            doc = await self.db.agents.find_one({"_id": ObjectId(agent_id)})
            if doc:
                return Agent(**doc)
            return None
        except InvalidId:
            return None
    
    async def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        doc = await self.db.agents.find_one({"name": name})
        if doc:
            return Agent(**doc)
        return None
    
    async def get_active_agent(self, agent_id: str) -> Optional[Agent]:
        """Get active agent by ID"""
        try:
            doc = await self.db.agents.find_one({
                "_id": ObjectId(agent_id),
                "is_active": True
            })
            if doc:
                return Agent(**doc)
            return None
        except InvalidId:
            return None
    
    async def update_agent(self, agent_id: str, update_data: AgentUpdate) -> Optional[Agent]:
        """Update agent"""
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await self.db.agents.find_one_and_update(
                {"_id": ObjectId(agent_id)},
                {"$set": update_dict},
                return_document=True
            )
            if result:
                return Agent(**result)
            return None
        except InvalidId:
            return None
    
    async def list_agents(self, skip: int = 0, limit: int = 100) -> List[Agent]:
        """List agents with pagination"""
        cursor = self.db.agents.find({}).skip(skip).limit(limit)
        agents = []
        async for doc in cursor:
            agents.append(Agent(**doc))
        return agents
    
    # API Key methods
    async def create_api_key(self, api_key_data: APIKeyCreate, key_hash: str) -> APIKey:
        """Create a new API key"""
        key_dict = {
            "key_hash": key_hash,
            "agent_id": api_key_data.agent_id,
            "name": api_key_data.name,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_used": None
        }
        
        result = await self.db.api_keys.insert_one(key_dict)
        key_dict["_id"] = result.inserted_id
        
        return APIKey(**key_dict)
    
    async def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash"""
        doc = await self.db.api_keys.find_one({"key_hash": key_hash})
        if doc:
            return APIKey(**doc)
        return None
    
    async def get_active_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get active API key by hash"""
        doc = await self.db.api_keys.find_one({
            "key_hash": key_hash,
            "is_active": True
        })
        if doc:
            return APIKey(**doc)
        return None
    
    async def update_api_key_last_used(self, api_key_id: str):
        """Update last used timestamp for API key"""
        try:
            await self.db.api_keys.update_one(
                {"_id": ObjectId(api_key_id)},
                {"$set": {"last_used": datetime.utcnow()}}
            )
        except InvalidId:
            pass
    
    async def list_api_keys_by_agent(self, agent_id: str) -> List[APIKey]:
        """List all API keys for an agent"""
        cursor = self.db.api_keys.find({"agent_id": agent_id})
        keys = []
        async for doc in cursor:
            keys.append(APIKey(**doc))
        return keys
    
    # File methods
    async def create_file(self, file_data: FileCreate) -> File:
        """Create a new file record"""
        file_dict = file_data.model_dump()
        file_dict["chunk_count"] = 0
        file_dict["is_deleted"] = False
        file_dict["created_at"] = datetime.utcnow()
        file_dict["deleted_at"] = None
        
        result = await self.db.files.insert_one(file_dict)
        file_dict["_id"] = result.inserted_id
        
        return File(**file_dict)
    
    async def get_file(self, file_id: str) -> Optional[File]:
        """Get file by ID"""
        try:
            doc = await self.db.files.find_one({"_id": ObjectId(file_id)})
            if doc:
                return File(**doc)
            return None
        except InvalidId:
            return None
    
    async def update_file_chunk_count(self, file_id: str, chunk_count: int):
        """Update file chunk count"""
        try:
            await self.db.files.update_one(
                {"_id": ObjectId(file_id)},
                {"$set": {"chunk_count": chunk_count}}
            )
        except InvalidId:
            pass
    
    async def mark_file_deleted(self, file_id: str) -> Optional[File]:
        """Soft delete a file"""
        try:
            result = await self.db.files.find_one_and_update(
                {"_id": ObjectId(file_id)},
                {
                    "$set": {
                        "is_deleted": True,
                        "deleted_at": datetime.utcnow()
                    }
                },
                return_document=True
            )
            if result:
                return File(**result)
            return None
        except InvalidId:
            return None
    
    async def list_files_by_agent(self, agent_id: str, include_deleted: bool = False) -> List[File]:
        """List files for an agent"""
        filter_dict = {"agent_id": agent_id}
        if not include_deleted:
            filter_dict["is_deleted"] = False
        
        cursor = self.db.files.find(filter_dict)
        files = []
        async for doc in cursor:
            files.append(File(**doc))
        return files
    
    async def get_file_count_by_agent(self, agent_id: str) -> int:
        """Get count of files for an agent"""
        return await self.db.files.count_documents({
            "agent_id": agent_id,
            "is_deleted": False
        })


# Global MongoDB instance
mongodb = MongoDB()