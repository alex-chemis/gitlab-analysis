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
        self._req_count = 0

    def _throttle(self):
        dt = time.time() - self._last_ts
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        backoff = 1.0
        for attempt in range(8):
            self._throttle()
            t0 = time.time()
            resp = self.session.request(method, url, timeout=30, **kwargs)
            self._last_ts = time.time()
            self._req_count += 1
            log.debug("HTTP %s %s [%s] in %.0fms", method, path, resp.status_code, (time.time() - t0) * 1000)
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
            log.error("GitLab API error %s on %s: %s", resp.status_code, path, (resp.text or "")[:400])
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
            log.info("Fetching projects page=%s per_page=%s ...", page, per_page)
            r = self._request("GET", "/projects", params=params)
            data = r.json()
            if not data:
                log.info("Projects: page=%s is empty, stopping", page)
                break
            log.info("Projects: page=%s returned %s items", page, len(data))
            for p in data:
                yield p
            page += 1

    def project_details(self, project_id: int, want_stats: bool = True) -> dict:
        """
        Получаем подробные поля проекта. Если есть права (Reporter+) и включено want_stats,
        добавляем statistics (sizes, commit_count и пр.). Иначе — без них.
        """
        params = {}
        if want_stats and SETTINGS.include_statistics:
            params["statistics"] = True
        try:
            r = self._request("GET", f"/projects/{project_id}", params=params)
        except requests.HTTPError as e:
            # Возможно 403 из-за statistics — повторим без него
            if hasattr(e, "response") and e.response is not None and e.response.status_code in (400, 401, 403):
                log.debug("No access to project statistics for %s, retrying without statistics", project_id)
                r = self._request("GET", f"/projects/{project_id}")
            else:
                raise
        data = r.json() or {}
        # оставим только полезные и стабильные поля
        keep = [
            "name", "path_with_namespace", "web_url", "description", "topics",
            "star_count", "forks_count", "open_issues_count",
            "default_branch", "visibility",
            "created_at", "last_activity_at", "readme_url",
            "issues_enabled", "merge_requests_enabled", "jobs_enabled", "wiki_enabled", "snippets_enabled",
            "container_registry_access_level", "package_registry_access_level",
            "namespace", "license", "repository_storage",
        ]
        details = {k: data.get(k) for k in keep if k in data}
        if "statistics" in data:
            details["statistics"] = data["statistics"]
        return details


    def project_languages(self, project_id: int) -> dict[str, float]:
        r = self._request("GET", f"/projects/{project_id}/languages")
        # Формат: {"Python": 82.1, "Shell": 17.9}
        return r.json() or {}

    def fetch_projects_with_metrics(self, limit: int) -> list[dict]:
        """
        Собираем: подробные поля проекта (+ statistics при наличии прав) и languages.
        """
        collected: list[dict] = []
        t0 = time.time()
        pages_seen = 0
        ok_details = 0
        fail_details = 0
        ok_langs = 0
        fail_langs = 0
        for p in self.iter_projects(per_page=100):
            pid = p["id"]
            try:
                details = self.project_details(pid, want_stats=True)
                ok_details += 1
            except requests.HTTPError as e:
                log.warning("Failed to fetch details for project %s: %s", pid, e)
                details = {}
                fail_details += 1
            langs = {}
            try:
                langs = self.project_languages(pid)
                ok_langs += 1
            except requests.HTTPError as e:
                log.warning("Failed to fetch languages for project %s: %s", pid, e)
                fail_langs += 1
            doc = {
                "project_id": pid,
                # дублируем ключевые метрики наверх для удобной фильтрации/индексации
                "name": details.get("name") or p.get("name"),
                "path_with_namespace": details.get("path_with_namespace") or p.get("path_with_namespace"),
                "web_url": details.get("web_url") or p.get("web_url"),
                "star_count": details.get("star_count", p.get("star_count")),
                "forks_count": details.get("forks_count"),
                "open_issues_count": details.get("open_issues_count"),
                "visibility": details.get("visibility"),
                "created_at": details.get("created_at"),
                "last_activity_at": details.get("last_activity_at"),
                # полноценный блок деталей
                "details": details,
                # языки — как и раньше, для агрегации
                "languages": langs,
            }
            collected.append(doc)
            n = len(collected)
            if n % SETTINGS.progress_every == 0:
                elapsed = time.time() - t0
                rps = n / elapsed if elapsed > 0 else 0.0
                eta = (limit - n) / rps if rps > 0 and limit > n else 0
                log.info(
                    "Progress: %s/%s projects (details ok/fail=%s/%s, langs ok/fail=%s/%s) | req=%s | rps=%.2f | ETA=%.0fs",
                    n, limit, ok_details, fail_details, ok_langs, fail_langs, self._req_count, rps, eta
                )
            if n >= limit:
                break
        return collected
