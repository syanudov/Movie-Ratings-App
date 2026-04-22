import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_name = os.getenv("MONGO_DB_NAME", "movieRatingsDB")
base_dir = Path(__file__).resolve().parent

print("=== Movie Ratings App Check ===")
print(f"MONGO_URI: {mongo_uri}")
print(f"MONGO_DB_NAME: {db_name}")

for rel in ["data/movieRatingsDB.movies.json", "data/movieRatingsDB.users.json", "data/movieRatingsDB.ratings.json"]:
    path = base_dir / rel
    print(f"{rel}: {'OK' if path.exists() else 'MISSING'}")

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("MongoDB connection: OK")
    db = client[db_name]
    print("Collections now:", db.list_collection_names())
except Exception as e:
    print("MongoDB connection: FAILED")
    print(f"Error: {e}")
