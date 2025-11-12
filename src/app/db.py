from datetime import datetime, timezone
from typing import Iterable
from pymongo import MongoClient, UpdateOne, ASCENDING
from .config import SETTINGS
import time
import logging
log = logging.getLogger(__name__)

_client = None
_db = None


def get_db(retries: int = 10, delay: float = 3.0):
    """Get MongoDB connection (persistent, with retries and indexes)."""
    global _client, _db

    if _db is not None:
        return _db

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            _client = MongoClient(SETTINGS.mongo_uri, serverSelectionTimeoutMS=3000)
            _client.admin.command("ping")
            _db = _client[SETTINGS.mongo_db]

            # Create indexes once
            _db[SETTINGS.mongo_coll_projects].create_index(
                [("project_id", ASCENDING)], unique=True
            )
            _db[SETTINGS.mongo_coll_lang_dist].create_index(
                [("language", ASCENDING)], unique=True
            )

            log.info("Mongo connected: %s (db=%s)", SETTINGS.mongo_uri, SETTINGS.mongo_db)
            return _db

        except Exception as e:
            last_err = e
            log.warning(
                "Mongo not ready (attempt %s/%s): %s", attempt, retries, e
            )
            time.sleep(delay)

    raise last_err

def upsert_projects(project_docs: Iterable[dict]) -> int:
    db = get_db()
    ops = []
    now = datetime.now(timezone.utc).isoformat()

    for doc in project_docs:
        # Ensure project_id is present
        doc["project_id"] = doc.get("project_id", doc.get("id"))
        if not doc.get("project_id"):
            log.warning("Skipping project without project_id: %s", doc)
            continue

        doc["fetched_at"] = now
        ops.append(UpdateOne(
            {"project_id": doc["project_id"]},
            {"$set": doc},
            upsert=True
        ))

    if not ops:
        return 0

    res = db[SETTINGS.mongo_coll_projects].bulk_write(ops, ordered=False)
    log.info("Mongo upserted: %s modified, %s upserted",
             res.modified_count or 0, res.upserted_count or 0)
    return (res.upserted_count or 0) + (res.modified_count or 0)

def recompute_lang_distribution() -> list[dict]:
    """
    Efficiently recompute language distribution directly in MongoDB
    without loading the entire 'projects' collection into RAM.
    """
    db = get_db()
    coll_projects = db[SETTINGS.mongo_coll_projects]
    coll_dist = db[SETTINGS.mongo_coll_lang_dist]

    log.info("Starting language aggregation via MongoDB pipeline...")

    # MongoDB aggregation pipeline
    pipeline = [
        {"$project": {"languages": {"$objectToArray": "$languages"}}},  # convert dict to array of {k,v}
        {"$unwind": "$languages"},
        {"$group": {"_id": "$languages.k", "project_count": {"$sum": 1}}},
        {"$sort": {"project_count": -1}},
    ]

    cursor = coll_projects.aggregate(pipeline, allowDiskUse=True)
    results = list(cursor)

    # Drop old results and upsert new ones
    coll_dist.delete_many({})
    if results:
        ops = [
            UpdateOne(
                {"language": r["_id"]},
                {"$set": {"language": r["_id"], "project_count": r["project_count"]}},
                upsert=True,
            )
            for r in results
        ]
        coll_dist.bulk_write(ops, ordered=False)
        log.info("Language distribution saved: %s languages", len(results))

    # Return sorted list
    return [
        {"language": r["_id"], "project_count": r["project_count"]}
        for r in sorted(results, key=lambda x: x["project_count"], reverse=True)
    ]
