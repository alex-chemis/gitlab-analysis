"""
Круговая диаграмма распределения проектов по языкам.
Берём lang_distribution; если коллекция пустая — считаем по projects.languages.
С подробными логами и понятными ошибками.
"""

import argparse
import os
from typing import List, Tuple
from scripts.common.mongo import load_lang_distribution, compute_lang_distribution_from_projects
from scripts.common.plot import pie_chart


def compress_top(labels: List[str], values: List[int], top: int = 12) -> Tuple[List[str], List[int]]:
    if len(labels) <= top:
        return labels, values
    labels_top = labels[: top - 1]
    values_top = values[: top - 1]
    other = sum(values[top - 1 :])
    labels_top.append("Other")
    values_top.append(other)
    return labels_top, values_top


def main():
    ap = argparse.ArgumentParser(description="Pie chart: распределение проектов по языкам")
    ap.add_argument("--top", type=int, default=12, help="Оставить топ-N, остальные в 'Other'")
    ap.add_argument("--out", type=str, default="/app/outputs/lang_pie.png", help="PNG выход")
    ap.add_argument("--seed", type=int, default=None, help="Seed для воспроизводимой цветовой палитры")
    args = ap.parse_args()

    print(f"[pie] target file: {args.out}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    rows = load_lang_distribution(top=None)
    if rows:
        print(f"[pie] lang_distribution rows: {len(rows)}")
    else:
        print("[pie] lang_distribution пуст — считаю по projects.languages …")
        counts = compute_lang_distribution_from_projects()
        rows = sorted(
            [{"language": k, "project_count": v} for k, v in counts.items()],
            key=lambda x: x["project_count"],
            reverse=True,
        )
        print(f"[pie] computed from projects: {len(rows)} languages")

    if not rows:
        print("[pie][ERROR] нет данных (ни lang_distribution, ни projects). Сначала запусти fetch + aggregate.")
        return

    labels = [r["language"] for r in rows]
    values = [int(r["project_count"]) for r in rows]
    total = sum(values)
    print(f"[pie] total projects counted across languages: {total}")

    if total <= 0:
        print("[pie][ERROR] сумма значений равна 0 — диаграмму строить нельзя.")
        return

    labels, values = compress_top(labels, values, top=args.top)
    print(f"[pie] plotting {len(labels)} slices (top={args.top}, last is 'Other' if present)")
    out = pie_chart(
        labels,
        values,
        args.out,
        title="Распределение проектов по языкам",
        random_colors=True,
        seed=args.seed,
    )
    # sanity-check: убедимся, что файл реально записан
    if os.path.exists(out) and os.path.getsize(out) > 0:
        print(f"[pie] готово: {out} ({os.path.getsize(out)} bytes)")
    else:
        print(f"[pie][ERROR] файл не создан: {out}")


if __name__ == "__main__":
    main()
