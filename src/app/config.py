import os
from dataclasses import dataclass

def _get_env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name, default)
    return val


def _get_bool(name: str, default: str = "1") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

@dataclass(frozen=True)
class Settings:
    gitlab_base_url: str = _get_env("GITLAB_BASE_URL", "https://gitlab.com/api/v4")
    gitlab_token: str | None = _get_env("GITLAB_TOKEN", None)

    mongo_uri: str = _get_env("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = _get_env("MONGO_DB", "gitlab_stats")
    mongo_coll_projects: str = _get_env("MONGO_COLL_PROJECTS", "projects")
    mongo_coll_lang_dist: str = _get_env("MONGO_COLL_LANG_DIST", "lang_distribution")

    fetch_limit: int = int(_get_env("FETCH_LIMIT", "150"))
    requests_per_second: float = float(_get_env("REQUESTS_PER_SECOND", "2"))
    log_level: str = _get_env("LOG_LEVEL", "INFO")
    include_statistics: bool = _get_bool("INCLUDE_STATISTICS", "1")
    progress_every: int = int(_get_env("PROGRESS_EVERY", "10"))
    
SETTINGS = Settings()
