from typing import Any, Dict, Iterable, List, Optional
from pymongo.collection import Collection
from app.config import SETTINGS
from app.db import get_db as _get_db  # берём готовое подключение с ретраями/индексами

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

def histogram_languages_per_project() -> Dict[int, int]:
    hist: Dict[int, int] = {}
    for p in iter_projects({"languages": 1}):
        n = len(p.get("languages") or {})
        hist[n] = hist.get(n, 0) + 1
    return hist
