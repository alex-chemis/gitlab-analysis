"""
Барчарт: медианное число звёзд (star_count) по языкам.
Проект учитывается во всех своих языках. Для устойчивости метрики
есть фильтр по минимуму проектов на язык (--min-projects).
"""

import argparse
from collections import defaultdict
from statistics import median
from typing import Dict, List, Tuple

from scripts.common.mongo import iter_projects
from scripts.common.plot import barh_chart


def main():
    ap = argparse.ArgumentParser(description="Медианное число звёзд по языкам")
    ap.add_argument("--top", type=int, default=20, help="Показать топ-N языков по медиане звёзд")
    ap.add_argument("--min-projects", type=int, default=10, help="Минимум проектов на язык для расчёта медианы")
    ap.add_argument("--out", type=str, default="/app/outputs/median_stars_by_language.png", help="PNG выход")
    args = ap.parse_args()

    buckets: Dict[str, List[int]] = defaultdict(list)
    total_seen = 0
    with_stars = 0

    # читаем только нужные поля
    for p in iter_projects({"languages": 1, "star_count": 1}):
        total_seen += 1
        langs = list((p.get("languages") or {}).keys())
        stars = p.get("star_count")

        # валидируем star_count
        if not langs or not isinstance(stars, (int, float)) or stars < 0:
            continue

        with_stars += 1
        stars_i = int(stars)

        # один проект учитываем по одному разу на язык
        for lang in set(langs):
            buckets[lang].append(stars_i)

    if not buckets:
        print("Нет данных по звёздам/языкам. Сначала загрузите проекты и их языки.")
        return

    # медианы по языкам + фильтр редких
    medians: List[Tuple[str, float, int]] = []
    for lang, vals in buckets.items():
        if len(vals) < args.min_projects:
            continue
        medians.append((lang, float(median(vals)), len(vals)))

    if not medians:
        print(f"После фильтра по min-projects={args.min_projects} не осталось языков. Уменьшите порог.")
        return

    # сортировка по медиане убыв., берём топ-N
    medians.sort(key=lambda x: x[1], reverse=True)
    medians = medians[: args.top]

    labels = [f"{lang} (n={n})" for lang, _, n in medians]
    values = [m for _, m, _ in medians]

    out = barh_chart(
        labels,
        values,
        args.out,
        title="Медианное число звёзд по языкам (GitLab)",
        xlabel="Звёзд (медиана)",
        ylabel=""
    )

    print(f"Готово: {out}")
    print(f"Проектов просмотрено: {total_seen}, с валидным star_count: {with_stars}, языков на графике: {len(labels)}")


if __name__ == "__main__":
    main()
