"""
Столбчатая диаграмма: сколько проектов используют 1 язык, 2, 3 и т.д. (батчево)
"""
import argparse
import os
from scripts.common.mongo import histogram_languages_per_project_batched
from scripts.common.plot import bar_chart

BATCH_SIZE = 1000

def main():
    ap = argparse.ArgumentParser(description="Гистограмма: число языков на проект (батчево)")
    ap.add_argument("--out", type=str, default="/app/outputs/languages_per_project.png", help="PNG выход")
    ap.add_argument("--top", type=int, default=None, help="Ограничить максимумом языков (например 20)")
    ap.add_argument("--debug", action="store_true", help="Печатать больше диагностики")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    hist = histogram_languages_per_project_batched(limit=args.top)
    if not hist:
        print("Нет данных. Сначала запусти сбор/агрегацию.")
        return

    xs = sorted(hist.keys())
    labels = [str(x) for x in xs]
    values = [hist[x] for x in xs]

    if args.debug:
        print(f"[debug] final xs: {xs}")
        print(f"[debug] final values: {values}")

    out = bar_chart(
        labels,
        values,
        args.out,
        title="Сколько проектов используют N языков",
        xlabel="Число языков в проекте",
        ylabel="Число проектов, млн.",
        rotate_x=0
    )

    # sanity check
    if os.path.exists(out):
        print(f"Готово: {out} ({os.path.getsize(out)} bytes)")
    else:
        print(f"[ERROR] файл не создан: {out}")


if __name__ == "__main__":
    main()