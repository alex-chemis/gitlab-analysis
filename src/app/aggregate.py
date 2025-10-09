from .db import upsert_projects, recompute_lang_distribution
from .gitlab_client import GitLabClient
from .config import SETTINGS
import logging

log = logging.getLogger(__name__)

def fetch(limit: int | None = None) -> int:
    client = GitLabClient(
        base_url=SETTINGS.gitlab_base_url,
        token=SETTINGS.gitlab_token,
        rps=SETTINGS.requests_per_second,
    )
    docs = client.fetch_projects_with_languages(limit or SETTINGS.fetch_limit)
    cnt = upsert_projects(docs)
    log.info("Upserted %s projects", cnt)
    return cnt

def aggregate() -> list[dict]:
    dist = recompute_lang_distribution()
    if dist:
        top = dist[:10]
        log.info("Top languages by project count: %s", ", ".join(f"{d['language']} ({d['project_count']})" for d in top))
    return dist
