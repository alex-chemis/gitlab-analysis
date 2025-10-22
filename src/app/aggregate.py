from .db import upsert_projects, recompute_lang_distribution
from .gitlab_client import GitLabClient
from .gitlab_client_async import AsyncGitLabClient
from .config import SETTINGS
import logging
import time

log = logging.getLogger(__name__)

def fetch(limit: int | None = None) -> int:
    target = limit or SETTINGS.fetch_limit
    t0 = time.time()
    if SETTINGS.use_async:
        # ускоренный режим
        async def _run():
            client = AsyncGitLabClient()
            try:
                return await client.fetch_projects_with_metrics(target)
            finally:
                await client.aclose()
        import asyncio, uvloop
        try:
            uvloop.install()
        except Exception:
            pass
        docs = asyncio.run(_run())
    else:
        client = GitLabClient(
            base_url=SETTINGS.gitlab_base_url,
            token=SETTINGS.gitlab_token,
            rps=SETTINGS.requests_per_second,
        )
        docs = client.fetch_projects_with_metrics(target)
    elapsed = time.time() - t0
    rps = (len(docs) / elapsed) if elapsed > 0 else 0.0
    cnt = upsert_projects(docs)
    log.info("Fetch finished: fetched=%s target=%s in %.1fs (avg_rps=%.2f), upserted=%s",
            len(docs), target, elapsed, rps, cnt)
    return cnt

def aggregate() -> list[dict]:
    t0 = time.time()
    dist = recompute_lang_distribution()
    elapsed = time.time() - t0
    if dist:
        top = dist[:10]
        log.info("Aggregated %s languages in %.1fs", len(dist), elapsed)
    return dist
