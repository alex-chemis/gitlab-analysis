from .db import recompute_lang_distribution
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
        ok_count = asyncio.run(_run())
    else:
        client = GitLabClient(
            base_url=SETTINGS.gitlab_base_url,
            token=SETTINGS.gitlab_token,
            rps=SETTINGS.requests_per_second,
        )
        ok_count = client.fetch_projects_with_metrics(target)

    elapsed = time.time() - t0
    log.info("Fetch finished: fetched=%s target=%s in %.1fs (avg_rps=%.2f)",
             ok_count, target, elapsed, (ok_count / elapsed) if elapsed > 0 else 0.0)
    return ok_count


def aggregate() -> list[dict]:
    t0 = time.time()
    dist = recompute_lang_distribution()
    elapsed = time.time() - t0
    if dist:
        top = dist[:10]
        log.info("Aggregated %s languages in %.1fs", len(dist), elapsed)
    return dist
