from __future__ import annotations
import asyncio
import logging
import math
import random
from typing import Any, Dict, List, Tuple

import httpx

from .config import SETTINGS

log = logging.getLogger(__name__)

def _headers() -> Dict[str, str]:
    h = {
        "Accept": "application/json",
        "User-Agent": "gitlab-lang-stats/async-1.0",
    }
    if SETTINGS.gitlab_token:
        h["PRIVATE-TOKEN"] = SETTINGS.gitlab_token
    return h

class AsyncGitLabClient:
    def __init__(self) -> None:
        self.base_url = SETTINGS.gitlab_base_url.rstrip("/")
        self.sem = asyncio.Semaphore(max(1, SETTINGS.concurrency))
        self.req_count = 0

        # http2=True даёт мультиплексирование
        self.client = httpx.AsyncClient(
            http2=True,
            timeout=SETTINGS.http_timeout,
            headers=_headers(),
            base_url=self.base_url,
        )

    async def _request(self, method: str, path: str, **kw) -> httpx.Response:
        # обёртка с ретраями и уважением Retry-After
        backoff = 1.0
        for attempt in range(1, SETTINGS.retries + 1):
            async with self.sem:
                r = await self.client.request(method, path, **kw)
                self.req_count += 1
            if 200 <= r.status_code < 300:
                return r
            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                wait = float(ra) if ra else backoff
                wait += random.uniform(0, 0.25)  # чуть джиттера
                log.warning("429 on %s %s, sleeping for %.2fs (attempt %s/%s)",
                            method, path, wait, attempt, SETTINGS.retries)
                await asyncio.sleep(wait)
                backoff = min(backoff * 2, 30.0)
                continue
            if 500 <= r.status_code < 600:
                log.warning("%s on %s %s, retrying in %.1fs (attempt %s/%s)",
                            r.status_code, method, path, backoff, attempt, SETTINGS.retries)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            # иное — сразу ошибка
            log.error("GitLab API error %s %s %s: %s", method, path, r.status_code, (r.text or "")[:400])
            r.raise_for_status()
        # если все ретраи исчерпаны
        r.raise_for_status()
        return r

    async def list_projects(self, target: int) -> List[Dict[str, Any]]:
        projects: List[Dict[str, Any]] = []
        page = 1
        per_page = 100
        while len(projects) < target:
            params = {
                "per_page": per_page,
                "page": page,
                "order_by": "star_count",
                "sort": "desc",
                "simple": "true",
                "visibility": "public",
                "archived": "false",
            }
            log.info("Fetching projects page=%s ...", page)
            r = await self._request("GET", "/projects", params=params)
            batch = r.json() or []
            log.info("Projects page=%s: %s items", page, len(batch))
            if not batch:
                break
            projects.extend(batch)
            page += 1
        return projects[:target]

    async def get_details(self, pid: int, want_stats: bool = True) -> Dict[str, Any]:
        params = {}
        if want_stats and SETTINGS.include_statistics:
            params["statistics"] = True
        try:
            r = await self._request("GET", f"/projects/{pid}", params=params)
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in (400, 401, 403):
                # повтор без statistics
                r = await self._request("GET", f"/projects/{pid}")
            else:
                raise
        return r.json() or {}

    async def get_languages(self, pid: int) -> Dict[str, float]:
        r = await self._request("GET", f"/projects/{pid}/languages")
        return r.json() or {}

    async def fetch_one(self, p: Dict[str, Any]) -> Dict[str, Any]:
        pid = p["id"]
        want_details = SETTINGS.metrics_mode.lower() == "full"
        # параллелим детали и языки
        tasks: List[asyncio.Task] = []
        if want_details:
            tasks.append(asyncio.create_task(self.get_details(pid, want_stats=True)))
        else:
            # заглушка — используем simple-объект из списка
            async def _just_simple() -> Dict[str, Any]:
                return {
                    "name": p.get("name"),
                    "path_with_namespace": p.get("path_with_namespace"),
                    "web_url": p.get("web_url"),
                    "star_count": p.get("star_count"),
                    "forks_count": p.get("forks_count"),
                    "open_issues_count": p.get("open_issues_count"),
                    "visibility": p.get("visibility"),
                    "created_at": p.get("created_at"),
                    "last_activity_at": p.get("last_activity_at"),
                }
            tasks.append(asyncio.create_task(_just_simple()))
        tasks.append(asyncio.create_task(self.get_languages(pid)))

        details, langs = await asyncio.gather(*tasks, return_exceptions=True)
        # обработка исключений покомпонентно
        det: Dict[str, Any] = {}
        if isinstance(details, Exception):
            log.warning("Details failed for %s: %s", pid, details)
        else:
            det = details or {}

        lmap: Dict[str, float] = {}
        if isinstance(langs, Exception):
            log.warning("Languages failed for %s: %s", pid, langs)
        else:
            lmap = langs or {}

        doc = {
            "project_id": pid,
            "name": det.get("name") or p.get("name"),
            "path_with_namespace": det.get("path_with_namespace") or p.get("path_with_namespace"),
            "web_url": det.get("web_url") or p.get("web_url"),
            "star_count": det.get("star_count", p.get("star_count")),
            "forks_count": det.get("forks_count") or p.get("forks_count"),
            "open_issues_count": det.get("open_issues_count") or p.get("open_issues_count"),
            "visibility": det.get("visibility") or p.get("visibility"),
            "created_at": det.get("created_at") or p.get("created_at"),
            "last_activity_at": det.get("last_activity_at") or p.get("last_activity_at"),
            "details": det,
            "languages": lmap,
        }
        return doc

    async def fetch_projects_with_metrics(self, target: int) -> List[Dict[str, Any]]:
        t0 = asyncio.get_event_loop().time()
        projects = await self.list_projects(target)
        n = len(projects)
        if n == 0:
            return []
        log.info("Collected %s projects from listing, fetching details+languages with concurrency=%s",
                 n, SETTINGS.concurrency)

        results: List[Dict[str, Any]] = []
        ok = 0
        fail = 0

        async def _wrap(p):
            nonlocal ok, fail
            try:
                doc = await self.fetch_one(p)
                results.append(doc)
                ok += 1
            except Exception as e:
                fail += 1
                log.warning("Failed project %s: %s", p.get("id"), e)
            # прогресс
            done = ok + fail
            if done % SETTINGS.progress_every == 0 or done == n:
                elapsed = asyncio.get_event_loop().time() - t0
                rps = done / elapsed if elapsed > 0 else 0.0
                eta = (n - done) / rps if rps > 0 else 0.0
                log.info("Progress: %s/%s (ok=%s, fail=%s) | http req=%s | rps=%.2f | ETA=%.0fs",
                         done, n, ok, fail, self.req_count, rps, eta)

        # запускаем пачки задач, сохраняя ограничение семафора внутри _request
        await asyncio.gather(*[self._limited(_wrap, p) for p in projects[:target]])
        return results

    async def _limited(self, coro_func, *args, **kwargs):
        # просто обёртка чтобы не съезжали стеки ошибок
        return await coro_func(*args, **kwargs)

    async def aclose(self):
        await self.client.aclose()
