from __future__ import annotations
import time
import logging
from typing import Iterator
import requests

from .config import SETTINGS

log = logging.getLogger(__name__)

class GitLabClient:
    def __init__(self, base_url: str | None = None, token: str | None = None, rps: float = 2.0):
        self.base_url = (base_url or SETTINGS.gitlab_base_url).rstrip("/")
        self.session = requests.Session()
        headers = {
            "Accept": "application/json",
            "User-Agent": "gitlab-lang-stats/1.0",
        }
        if token:
            headers["PRIVATE-TOKEN"] = token
        self.session.headers.update(headers)
        self.min_interval = 1.0 / max(rps, 0.1)
        self._last_ts = 0.0

    def _throttle(self):
        dt = time.time() - self._last_ts
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        backoff = 1.0
        for attempt in range(8):
            self._throttle()
            resp = self.session.request(method, url, timeout=30, **kwargs)
            self._last_ts = time.time()
            # 2xx
            if 200 <= resp.status_code < 300:
                return resp
            # 429 (rate limit) — уважаем Retry-After если он есть
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else backoff
                log.warning("Hit 429, sleeping for %.1fs", wait)
                time.sleep(wait)
                backoff = min(backoff * 2, 30.0)
                continue
            # 5xx — пробуем с бэкофом
            if 500 <= resp.status_code < 600:
                log.warning("GitLab %s on %s, retrying in %.1fs", resp.status_code, path, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            # другое — поднимаем
            resp.raise_for_status()
        resp.raise_for_status()
        return resp  # для типа

    def iter_projects(self, per_page: int = 100) -> Iterator[dict]:
        """
        Итерируем публичные проекты, отсортированные по звёздам (самые популярные — первыми).
        """
        page = 1
        while True:
            params = {
                "per_page": per_page,
                "page": page,
                "order_by": "star_count",
                "sort": "desc",
                "simple": "true",
                "visibility": "public",
                "archived": "false",
            }
            r = self._request("GET", "/projects", params=params)
            data = r.json()
            if not data:
                break
            for p in data:
                yield p
            page += 1

    def project_languages(self, project_id: int) -> dict[str, float]:
        r = self._request("GET", f"/projects/{project_id}/languages")
        # Формат: {"Python": 82.1, "Shell": 17.9}
        return r.json() or {}

    def fetch_projects_with_languages(self, limit: int) -> list[dict]:
        collected: list[dict] = []
        for p in self.iter_projects(per_page=100):
            pid = p["id"]
            langs = {}
            try:
                langs = self.project_languages(pid)
            except requests.HTTPError as e:
                log.warning("Failed to fetch languages for project %s: %s", pid, e)
            collected.append({
                "project_id": pid,
                "name": p.get("name"),
                "path_with_namespace": p.get("path_with_namespace"),
                "web_url": p.get("web_url"),
                "star_count": p.get("star_count", 0),
                "languages": langs,
            })
            if len(collected) >= limit:
                break
        return collected
