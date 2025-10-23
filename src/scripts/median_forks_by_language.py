"""
Барчарт: медианное число форков по языкам.
Берём forks_count и относим проект ко всем его языкам.
Фильтруем языки с малым числом наблюдений для устойчивости метрики.
"""

import argparse
from collections import defaultdict
from statistics import median
from typing import Dict, List, Tuple

from scripts.common.mongo import iter_projects
from scripts.common.plot import barh_chart


def main():
    ap = argparse.ArgumentParser(description="Медианное число форков по языкам")
    ap.add_argument("--top", type=int, default=20, help="Показать топ-N языков по медиане форков")
    ap.add_argument("--min-projects", type=int, default=10, help="Минимум проектов на язык для расчёта медианы")
    ap.add_argument("--out", type=str, default="/app/outputs/median_forks_by_language.png", help="PNG выход")
    args = ap.parse_args()

    buckets: Dict[str, List[int]] = defaultdict(list)
    total_seen = 0
    with_forks = 0

    # тянем только нужные поля
    for p in iter_projects({"languages": 1, "forks_count": 1}):
        total_seen += 1
        langs = list((p.get("languages") or {}).keys())
        forks = p.get("forks_count")

        # валидируем forks_count
        if not langs or not isinstance(forks, (int, float)) or forks < 0:
            continue

        forks_i = int(forks)
        with_forks += 1

        # учитываем проект для каждого его языка (по одному разу на язык)
        for lang in set(langs):
            buckets[lang].append(forks_i)

    if not buckets:
        print("Нет данных по форкам/языкам. Сначала загрузите проекты и их языки.")
        return

    # агрегируем медианы по языкам и отбрасываем редкие
    medians: List[Tuple[str, float, int]] = []
    for lang, vals in buckets.items():
        if len(vals) < args.min_projects:
            continue
        medians.append((lang, float(median(vals)), len(vals)))

    if not medians:
        print(f"После фильтра по min-projects={args.min_projects} не осталось языков. Уменьшите порог.")
        return

    # сортируем по медиане по убыванию и берём топ-N
    medians.sort(key=lambda x: x[1], reverse=True)
    medians = medians[: args.top]

    labels = [f"{lang} (n={n})" for lang, _, n in medians]
    values = [m for _, m, _ in medians]

    out = barh_chart(
        labels,
        values,
        args.out,
        title="Медианное число форков по языкам (GitLab)",
        xlabel="Форков (медиана)",
        ylabel=""
    )

    print(f"Готово: {out}")
    print(f"Проектов просмотрено: {total_seen}, с валидным forks_count: {with_forks}, языков на графике: {len(labels)}")


if __name__ == "__main__":
    main()
