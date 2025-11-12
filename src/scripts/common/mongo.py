from typing import Any, Dict, Iterable, List, Optional
from pymongo.collection import Collection
from collections import Counter
from pymongo import MongoClient
from app.db import get_db
from app.config import SETTINGS
from app.db import get_db as _get_db  # берём готовое подключение с ретраями/индексами

BATCH_SIZE = 1000

def get_db():
    return _get_db()

def projects_coll() -> Collection:
    return get_db()[SETTINGS.mongo_coll_projects]

def lang_dist_coll() -> Collection:
    return get_db()[SETTINGS.mongo_coll_lang_dist]

def load_lang_distribution(top: Optional[int] = None) -> List[Dict[str, Any]]:
    cur = lang_dist_coll().find().sort("project_count", -1)
    if top:
        cur = cur.limit(top)
    return list(cur)

def iter_projects(projection: Optional[Dict[str, int]] = None) -> Iterable[Dict[str, Any]]:
    prj = projects_coll()
    if projection is None:
        projection = {"languages": 1, "details.statistics": 1}
    yield from prj.find({}, projection)

def compute_lang_distribution_from_projects() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in iter_projects({"languages": 1}):
        langs = (p.get("languages") or {}).keys()
        for lang in langs:
            counts[lang] = counts.get(lang, 0) + 1
    return counts

def histogram_languages_per_project_batched(limit: int | None = None) -> dict[int, int]:
    """
    Считает распределение по количеству языков на проект (батчево, без полной выгрузки).
    Возвращает словарь: {число_языков: количество_проектов}.
    """
    db = get_db()
    projects = db["projects"]

    counter = Counter()
    cursor = projects.find({}, {"languages": 1}, no_cursor_timeout=True).batch_size(BATCH_SIZE)

    try:
        for idx, doc in enumerate(cursor, start=1):
            # диагностический вывод раз в 100k (безопасно)
            if idx % 100000 == 0:
                print(f"[scan] processed {idx} documents...")

            langs = doc.get("languages")
            if not langs:
                continue
            num_langs = len(langs)
            counter[num_langs] += 1
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    # сортируем по ключу (число языков)
    items = sorted(counter.items(), key=lambda kv: kv[0])  # (num_langs, count)
    total_unique = len(items)
    total_projects = sum(v for _, v in items)
    print(f"[diag] unique num_langs values found: {total_unique}, total projects counted: {total_projects}")

    # применяем лимит (если задан) — сохраняем порядок по возрастанию числа языков
    items = sorted(counter.items())
    result = {}
    for k, v in items:
        if limit and k == limit:
            result[f"{limit}+"] = v
        else:
            result[str(k)] = v

    return result
