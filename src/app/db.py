from datetime import datetime, timezone
from typing import Iterable
from pymongo import MongoClient, UpdateOne, ASCENDING
from .config import SETTINGS

def get_db():
    client = MongoClient(SETTINGS.mongo_uri)
    db = client[SETTINGS.mongo_db]
    # индексы
    db[SETTINGS.mongo_coll_projects].create_index([("project_id", ASCENDING)], unique=True)
    db[SETTINGS.mongo_coll_lang_dist].create_index([("language", ASCENDING)], unique=True)
    return db

def upsert_projects(project_docs: Iterable[dict]) -> int:
    db = get_db()
    ops = []
    now = datetime.now(timezone.utc).isoformat()
    for doc in project_docs:
        doc["fetched_at"] = now
        ops.append(UpdateOne(
            {"project_id": doc["project_id"]},
            {"$set": doc},
            upsert=True
        ))
    if not ops:
        return 0
    res = db[SETTINGS.mongo_coll_projects].bulk_write(ops, ordered=False)
    return (res.upserted_count or 0) + (res.modified_count or 0)

def recompute_lang_distribution() -> list[dict]:
    """Читает projects, считает количество проектов на язык и сохраняет в lang_distribution."""
    db = get_db()
    coll_projects = db[SETTINGS.mongo_coll_projects]
    coll_dist = db[SETTINGS.mongo_coll_lang_dist]

    counts: dict[str, int] = {}
    for p in coll_projects.find({}, {"languages": 1}):
        langs = p.get("languages") or {}
        for lang in set(langs.keys()):
            counts[lang] = counts.get(lang, 0) + 1

    # upsert в БД
    ops = [
        UpdateOne({"language": lang}, {"$set": {"language": lang, "project_count": cnt}}, upsert=True)
        for lang, cnt in counts.items()
    ]
    coll_dist.delete_many({})  # перезаписываем полностью, чтобы удалить устаревшие
    if ops:
        coll_dist.bulk_write(ops, ordered=False)

    # возвращаем отсортированный список
    return sorted(
        [{"language": k, "project_count": v} for k, v in counts.items()],
        key=lambda x: x["project_count"],
        reverse=True,
    )
