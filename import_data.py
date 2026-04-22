import json
import os
from pathlib import Path

from bson import json_util
from dotenv import load_dotenv

from utils.db import get_database
from utils.helpers import ensure_indexes

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

FILES = {
    "movies": DATA_DIR / "movieRatingsDB.movies.json",
    "users": DATA_DIR / "movieRatingsDB.users.json",
    "ratings": DATA_DIR / "movieRatingsDB.ratings.json",
}


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f, object_hook=json_util.object_hook)



def main():
    db = get_database()
    ensure_indexes(db)

    for collection_name, file_path in FILES.items():
        if not file_path.exists():
            print(f"[SKIP] File not found: {file_path}")
            continue

        docs = load_json(file_path)
        collection = db[collection_name]
        collection.delete_many({})
        if docs:
            collection.insert_many(docs)
        print(f"[OK] Imported {len(docs)} documents into {collection_name}")

    print("Done.")


if __name__ == "__main__":
    main()
