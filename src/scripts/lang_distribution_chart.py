"""
Строит столбчатую диаграмму: топ-N языков по числу проектов.
Берёт данные из коллекции lang_distribution (результат агрегирования).
"""
import argparse
from pathlib import Path
from scripts.common.mongo import load_lang_distribution
from scripts.common.plot import bar_chart
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def parse_args():
    p = argparse.ArgumentParser(
        description="Гистограмма топ-N языков по числу проектов (из MongoDB)."
    )
    p.add_argument("--top", type=int, default=20, help="Сколько языков показать (топ-N)")
    p.add_argument(
        "--out",
        type=str,
        default="/app/outputs/lang_top20.png",
        help="Путь к выходному PNG",
    )
    return p.parse_args()

def main():
    args = parse_args()
    data = load_lang_distribution(top=args.top)
    if not data:
        print("Коллекция lang_distribution пуста. Сначала запусти сбор и агрегирование:")
        print("  docker compose run --rm app python -m app fetch")
        print("  docker compose run --rm app python -m app aggregate")
        return

    labels = [d["language"] for d in data]
    values = [d["project_count"] for d in data]

    out_path = Path(args.out)
    title = f"Топ-{args.top} языков по количеству проектов (GitLab)"
    saved = bar_chart(labels, values, out_path, title=title, xlabel="Язык", ylabel="Проектов")

    print(f"График сохранён: {saved}")

if __name__ == "__main__":
    main()
