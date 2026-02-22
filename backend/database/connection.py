from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import settings

MONGO_URL = settings.MONGODB_URL
DB_NAME = settings.DB_NAME

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(MONGO_URL)
    db.db = db.client[DB_NAME]
    
    # Create Indexes
    await db.db.designs.create_index([("user_id", 1)])
    await db.db.designs.create_index([("created_at", -1)])
    await db.db.users.create_index([("email", 1)], unique=True)
    try:
        await db.db.jobs.create_index([("user_id", 1)])
        await db.db.jobs.create_index([("created_at", -1)])
    except:
        pass
        
    print(f"Connected to MongoDB at {MONGO_URL}")

async def close_mongo_connection():
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")

def get_database():
    return db.db
