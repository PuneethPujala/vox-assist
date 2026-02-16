from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime

# Load env from backend/.env
load_dotenv(os.path.join("backend", ".env"))

MONGO_URI = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "vox_assist_db")

def check_db():
    print(f"\n--- Checking MongoDB ({DB_NAME}) ---")
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Inspect Designs
        design_count = db.designs.count_documents({})
        print(f"\n[+] Total Designs stored: {design_count}")
        
        if design_count > 0:
            print("\n    Breakdown by User ID:")
            pipeline = [
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            results = list(db.designs.aggregate(pipeline))
            
            for res in results:
                uid = res["_id"]
                count = res["count"]
                # Mask User ID for privacy if needed, but here we just show it
                print(f"    - User '{uid}': {count} designs")
                
            print("\n    [!] NOTE: When a user calls GET /api/v1/my-designs, the Backend")
            print("        EXPLICITLY filters by their User ID.")
            print(f"        e.g. db.designs.find({{'user_id': '{results[0]['_id']}'}})")
            
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    check_db()
