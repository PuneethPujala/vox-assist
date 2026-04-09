from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import logging

logger = logging.getLogger(__name__)

MONGO_URL = settings.MONGODB_URL
DB_NAME = settings.DB_NAME

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

import asyncio
async def connect_to_mongo():
    for attempt in range(3):
        try:
            db.client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db.db = db.client[DB_NAME]
            print(f"Connected to MongoDB at {MONGO_URL}")
            # Ping db to verify connection
            await db.client.admin.command('ping')
            return
        except Exception as e:
            print(f"WARNING: MongoDB connection failed on attempt {attempt+1}: {e}")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                print("ERROR: MongoDB connection failed after retries.")
                # We won't raise so the app doesn't crash, but DB ops will fail later

async def create_database_indexes():
    """
    Perform index creation in the background to avoid blocking the main server startup.
    """
    if db.db is None:
        return

    # Create Indexes
    try:
        await db.db.designs.create_index([("user_id", 1)])
        await db.db.designs.create_index([("created_at", -1)])
        await db.db.users.create_index([("email", 1)], unique=True)
        await db.db.jobs.create_index([("user_id", 1)])
        await db.db.jobs.create_index([("created_at", -1)])
        print("Database indexes created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database indexes: {e}")
        print(f"WARNING: Database index creation failed: {e}")

async def close_mongo_connection():
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")

def get_database():
    return db.db
