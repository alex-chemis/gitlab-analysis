import argparse
import logging
from .aggregate import fetch as do_fetch, aggregate as do_aggregate
from .config import SETTINGS
from .db import get_db

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, SETTINGS.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

def cmd_fetch(args):
    limit = args.limit or SETTINGS.fetch_limit
    do_fetch(limit=limit)

def cmd_aggregate(_args):
    do_aggregate()

def cmd_fetch_and_aggregate(args):
    cmd_fetch(args)
    cmd_aggregate(args)

def cmd_report(_args):
    db = get_db()
    items = list(db[SETTINGS.mongo_coll_lang_dist].find().sort("project_count", -1).limit(50))
    print("\n=== Language distribution (by number of projects) ===")
    for i, it in enumerate(items, 1):
        print(f"{i:>2}. {it['language']:<18} {it['project_count']}")

def main():
    setup_logging()

    parser = argparse.ArgumentParser(
        prog="gitlab-lang-stats",
        description="Сбор языков проектов GitLab и подсчёт распределения (кол-во проектов на язык)."
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_fetch = sub.add_parser("fetch", help="Собрать проекты и их языки")
    p_fetch.add_argument("--limit", type=int, default=None, help="Минимум проектов для загрузки (>=100)")
    p_fetch.set_defaults(func=cmd_fetch)

    p_agg = sub.add_parser("aggregate", help="Пересчитать распределение языков")
    p_agg.set_defaults(func=cmd_aggregate)

    p_both = sub.add_parser("fetch-and-aggregate", help="Сначала сбор, затем агрегация")
    p_both.add_argument("--limit", type=int, default=None)
    p_both.set_defaults(func=cmd_fetch_and_aggregate)

    p_report = sub.add_parser("report", help="Вывести топ языков из БД")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if not args.cmd:
        # Поведение по умолчанию, если команда не указана
        args = parser.parse_args(["fetch-and-aggregate"])
    args.func(args)
