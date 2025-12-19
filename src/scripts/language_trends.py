from collections import defaultdict
from typing import Dict, List
from app.db import get_db
from app.config import SETTINGS
from scripts.common.plot_forcast import plot_trends, plot_timeseries_absolute, plot_timeseries_share
import os
import argparse
import numpy as np


def load_language_timeseries(months: int, top: int, until: str | None = None) -> Dict[str, List[int]]:
    """
    Возвращает:
    {
      "Python": [12, 15, 18, ...],
      "Java":   [10,  9,  8,  ...],
    }
    """
    db = get_db()
    coll = db[SETTINGS.mongo_coll_projects]

    pipeline = []

    if until:
        pipeline.append({
            "$match": {
                "last_activity_at": {
                    "$lte": f"{until}-31"
                }
            }
        })

    pipeline.extend([
        {
            "$project": {
                "languages": {"$objectToArray": "$languages"},
                "month": {
                    "$dateToString": {
                        "format": "%Y-%m",
                        "date": {"$toDate": "$last_activity_at"}
                    }
                }
            }
        },
        {"$unwind": "$languages"},
        {
            "$group": {
                "_id": {
                    "language": "$languages.k",
                    "month": "$month"
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id.month": 1}},
    ])


    rows = list(coll.aggregate(pipeline, allowDiskUse=True))

    # сгруппировать в language → month → count
    temp = defaultdict(dict)
    for r in rows:
        lang = r["_id"]["language"]
        month = r["_id"]["month"]
        temp[lang][month] = r["count"]

    # берём top языков по сумме
    ranked = sorted(
        temp.items(),
        key=lambda kv: sum(kv[1].values()),
        reverse=True
    )[:top]

    # унифицируем ось времени
    all_months = sorted({m for _, d in ranked for m in d.keys()})[-months:]

    series = {}
    for lang, data in ranked:
        series[lang] = [data.get(m, 0) for m in all_months]

    return series, all_months

def compute_trends(series: Dict[str, List[int]]) -> List[dict]:
    """
    Возвращает список:
    {
      language,
      trend,
      current,
      momentum,
      volume
    }
    """
    results = []

    for lang, ys in series.items():
        if len(ys) < 4:
            continue

        x = np.arange(len(ys))
        y = np.array(ys)

        # линейный тренд
        slope = float(np.polyfit(x, y, 1)[0])

        # momentum: последние 3 месяца / предыдущие 3
        recent = sum(y[-3:])
        prev = sum(y[-6:-3]) if len(y) >= 6 else 1
        momentum = recent / max(prev, 1)

        results.append({
            "language": lang,
            "trend": slope,
            "current": y[-1],
            "momentum": momentum,
            "volume": int(sum(y)),
        })

    return results

def main():
    ap = argparse.ArgumentParser("Прогноз популярности языков")
    ap.add_argument("--months", type=int, default=18)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", type=str, default="/app/outputs")
    ap.add_argument("--until", type=str, default=None, help="Последний месяц включительно, формат YYYY-MM")
    ap.add_argument("--forecast", type=int, default=6, help="Число месяцев прогноза")

    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    series, months = load_language_timeseries(args.months, args.top, args.until)
    trends = compute_trends(series)

    plot_trends(trends, f"{args.out}/forecast_trends.png")
    plot_timeseries_absolute(series, months, f"{args.out}/forecast_timeseries_absolute.png", forecast=args.forecast)
    plot_timeseries_share(series, months, f"{args.out}/forecast_timeseries_share.png", forecast=args.forecast)

    print("Готово")


if __name__ == "__main__":
    main()
