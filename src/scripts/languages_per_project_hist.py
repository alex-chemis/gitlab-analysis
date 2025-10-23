"""
Столбчатая диаграмма: сколько проектов используют 1 язык, 2, 3 и т.д.
"""
import argparse
from scripts.common.mongo import histogram_languages_per_project
from scripts.common.plot import bar_chart

def main():
    ap = argparse.ArgumentParser(description="Гистограмма: число языков на проект")
    ap.add_argument("--out", type=str, default="/app/outputs/languages_per_project.png", help="PNG выход")
    args = ap.parse_args()

    hist = histogram_languages_per_project()
    if not hist:
        print("Нет данных. Сначала запусти сбор/агрегацию.")
        return

    # сортируем по ключу (кол-во языков)
    xs = sorted(hist.keys())
    labels = [str(x) for x in xs]
    values = [hist[x] for x in xs]

    out = bar_chart(labels, values, args.out,
                    title="Сколько проектов используют N языков",
                    xlabel="Число языков в проекте",
                    ylabel="Проектов",
                    rotate_x=0)
    print(f"Готово: {out}")

if __name__ == "__main__":
    main()
