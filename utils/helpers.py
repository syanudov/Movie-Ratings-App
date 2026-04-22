from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List

import pandas as pd
from bson import ObjectId

from pymongo import ASCENDING, DESCENDING

def safe_object_id(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None



def parse_genres(text: str) -> List[str]:
    return [item.strip() for item in text.split(",") if item.strip()]



def serialize_value(value: Any):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    return value



def serialize_docs(docs: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for doc in docs:
        rows.append({k: serialize_value(v) for k, v in doc.items()})
    return rows



def format_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)



def ensure_indexes(db):
    # movies
    db["movies"].create_index([("title", ASCENDING)], name="movie_title_unique_idx", unique=True)

    # users
    db["users"].create_index([("username", ASCENDING)], name="username_1", unique=True)
    db["users"].create_index([("email", ASCENDING)], name="email_1", unique=True)

    # ratings
    db["ratings"].create_index(
        [("userId", ASCENDING), ("movieId", ASCENDING)],
        name="userId_1_movieId_1",
        unique=True
    )
    db["ratings"].create_index(
        [("movieId", ASCENDING), ("rating", DESCENDING)],
        name="movieId_1_rating_-1"
    )
    db["ratings"].create_index([("movieId", ASCENDING)], name="movieId_1")
    db["ratings"].create_index([("userId", ASCENDING)], name="userId_1")
