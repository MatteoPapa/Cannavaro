# utils/db_utils.py

from pymongo import MongoClient
import os

# Default fallback values
DEFAULT_MONGO_URI = "mongodb://localhost:27017/cannavaro_db"

def get_mongo_uri():
    return os.getenv("MONGO_URI", DEFAULT_MONGO_URI)

def connect_to_mongo(uri=None):
    uri = uri or get_mongo_uri()
    try:
        client = MongoClient(uri)
        db = client.get_default_database()  # Gets DB name from URI path
        # Trigger connection early to catch issues
        db.command("ping")
        print(f"✅ Connected to MongoDB: {db.name}")
        return client, db
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None, None

from datetime import datetime

def insert_patch(db, service, description):
    patch = {
        "service": service,
        "description": description,
        "timestamp": datetime.utcnow()
    }
    try:
        result = db.patches.insert_one(patch)
        print(f"✅ Patch logged with ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        print(f"❌ Failed to insert patch: {e}")
        return None