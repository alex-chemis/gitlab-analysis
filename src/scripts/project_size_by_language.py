"""
Комплексный анализ масштаба проектов по языкам программирования
Показывает сбалансированную выборку из всех категорий: крупные, средние, небольшие проекты
"""

import argparse
from collections import defaultdict
from statistics import median
from typing import Dict, List, Tuple
import logging

from scripts.common.mongo import iter_projects
from scripts.common.plot import barh_chart

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_project_scale():
    """
    Анализирует масштаб проектов по языкам используя реальные метрики
    """
    logger.info("🏗️  Комплексный анализ масштаба проектов...")

    metrics = {
        'stars': defaultdict(list),
        'forks': defaultdict(list),
        'issues': defaultdict(list)
    }

    total_projects = 0
    projects_analyzed = 0

    for p in iter_projects({"languages": 1, "star_count": 1, "forks_count": 1, "open_issues_count": 1}):
        total_projects += 1

        languages = p.get("languages", {})
        if not languages:
            continue

        star_count = p.get("star_count")
        forks_count = p.get("forks_count")
        issues_count = p.get("open_issues_count")

        if star_count is None or forks_count is None:
            continue

        if issues_count is None:
            issues_count = 0

        projects_analyzed += 1

        for lang in languages.keys():
            metrics['stars'][lang].append(int(star_count))
            metrics['forks'][lang].append(int(forks_count))
            metrics['issues'][lang].append(int(issues_count))

    logger.info(f"📈 ФИНАЛЬНАЯ СТАТИСТИКА:")
    logger.info(f"  Всего проектов в базе: {total_projects}")
    logger.info(f"  Проектов с полными метриками: {projects_analyzed}")
    logger.info(f"  Уникальных языков: {len(metrics['stars'])}")

    return metrics


def calculate_composite_score(stars_median: float, forks_median: float, issues_median: float) -> Tuple[float, str]:
  """
  Вычисляет композитную оценку с адаптивными порогами
  Основано на анализе реального распределения данных из базы
  """

  # ПЕРЦЕНТИЛИ из анализа твоей базы (2218 проектов):
  # На основе твоих реальных данных!
  stars_percentiles = {10: 10, 25: 20, 50: 37, 75: 100, 90: 173, 95: 500, 99: 1000}
  forks_percentiles = {10: 5, 25: 10, 50: 19, 75: 50, 90: 123, 95: 200, 99: 500}
  issues_percentiles = {10: 0, 25: 5, 50: 17, 75: 30, 90: 50, 95: 100, 99: 200}

  def get_score(value, percentiles):
    """Вычисляет оценку 1-10 на основе перцентилей"""
    if value >= percentiles[99]:
      return 10  # Топ 1% проектов
    elif value >= percentiles[95]:
      return 9  # Топ 5% проектов
    elif value >= percentiles[90]:
      return 8  # Топ 10% проектов
    elif value >= percentiles[75]:
      return 7  # Топ 25% проектов
    elif value >= percentiles[50]:
      return 6  # Выше медианы
    elif value >= percentiles[25]:
      return 4  # Средние значения
    elif value >= percentiles[10]:
      return 2  # Ниже среднего
    else:
      return 1  # Низкие значения

  stars_score = get_score(stars_median, stars_percentiles)
  forks_score = get_score(forks_median, forks_percentiles)
  issues_score = get_score(issues_median, issues_percentiles)

  # Взвешенная сумма (issues важнее для размера проекта)
  composite = (stars_score * 0.2 + forks_score * 0.3 + issues_score * 0.5)

  # Определяем категорию на основе композитной оценки
  if composite >= 7.0:
    category = "КРУПНЫЙ"  # 8-10 баллов по ключевым метрикам
  elif composite >= 4.5:
    category = "СРЕДНИЙ"  # 5-7 баллов по ключевым метрикам
  elif composite >= 2.5:
    category = "НЕБОЛЬШОЙ"  # 3-4 балла по ключевым метрикам
  else:
    category = "МИНИМАЛЬНЫЙ"  # 1-2 балла по ключевым метрикам

  return composite, category


def get_balanced_language_selection(metrics_data: Dict, min_projects: int = 10):
    """
    Выбирает сбалансированную выборку языков из всех категорий
    """
    composite_scores = []

    for lang in set().union(*[set(data.keys()) for data in metrics_data.values()]):
        if all(lang in metrics_data[metric] for metric in ['stars', 'forks', 'issues']):
            stars_vals = metrics_data['stars'][lang]
            forks_vals = metrics_data['forks'][lang]
            issues_vals = metrics_data['issues'][lang]

            if len(stars_vals) >= min_projects:
                stars_med = median(stars_vals)
                forks_med = median(forks_vals)
                issues_med = median(issues_vals)

                composite, category = calculate_composite_score(stars_med, forks_med, issues_med)
                project_count = len(stars_vals)

                composite_scores.append((lang, composite, stars_med, forks_med, issues_med, project_count, category))

    # Сортируем по убыванию оценки
    composite_scores.sort(key=lambda x: x[1], reverse=True)

    # Разделяем по категориям
    large_projects = [lang for lang in composite_scores if lang[6] == "КРУПНЫЙ"]
    medium_projects = [lang for lang in composite_scores if lang[6] == "СРЕДНИЙ"]
    small_projects = [lang for lang in composite_scores if lang[6] == "НЕБОЛЬШОЙ"]
    minimal_projects = [lang for lang in composite_scores if lang[6] == "МИНИМАЛЬНЫЙ"]

    logger.info(f"📊 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
    logger.info(f"  КРУПНЫЕ: {len(large_projects)} языков")
    logger.info(f"  СРЕДНИЕ: {len(medium_projects)} языков")
    logger.info(f"  НЕБОЛЬШИЕ: {len(small_projects)} языков")
    logger.info(f"  МИНИМАЛЬНЫЕ: {len(minimal_projects)} языков")

    # Выбираем представителей из каждой категории (по 5 из каждой)
    samples_large = min(5, len(large_projects))
    samples_medium = min(5, len(medium_projects))
    samples_small = min(5, len(small_projects))
    samples_minimal = min(5, len(minimal_projects))

    balanced_selection = (
        large_projects[:samples_large] +
        medium_projects[:samples_medium] +
        small_projects[:samples_small] +
        minimal_projects[:samples_minimal]
    )

    logger.info(f"📋 ВЫБОРКА ДЛЯ ГРАФИКА:")
    logger.info(f"  КРУПНЫЕ: {samples_large} языков")
    logger.info(f"  СРЕДНИЕ: {samples_medium} языков")
    logger.info(f"  НЕБОЛЬШИЕ: {samples_small} языков")
    logger.info(f"  МИНИМАЛЬНЫЕ: {samples_minimal} языков")

    return balanced_selection


def create_balanced_chart(metric_results: List[Tuple], output_path: str):
    """Создает сбалансированный график по категориям"""

    if not metric_results:
        logger.error("❌ Нет данных для графика")
        return None

    # Подготавливаем данные для графика
    labels = []
    values = []

    for lang, composite, stars, forks, issues, count, category in metric_results:
        # Создаем информативную метку (без эмодзи)
        label = f"{lang} ({category})"
        labels.append(label)
        values.append(composite)

    # Создаем график
    result_path = barh_chart(
        labels=labels,
        values=values,
        out_path=output_path,
        title="Сбалансированный анализ масштаба проектов по языкам",
        xlabel="Композитная оценка масштаба (0-10)",
        ylabel="Языки программирования"
    )

    return result_path


def main():
    parser = argparse.ArgumentParser(
        description="Сбалансированный анализ масштаба проектов по языкам программирования"
    )
    parser.add_argument(
        "--min-projects",
        type=int,
        default=10,
        help="Минимальное количество проектов для языка"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="/app/outputs/project_size_by_language",
        help="Базовый путь для сохранения графиков"
    )

    args = parser.parse_args()

    # Анализируем масштаб проектов
    metrics_data = analyze_project_scale()

    # Получаем сбалансированную выборку
    logger.info("📊 Формирование сбалансированной выборки...")
    balanced_selection = get_balanced_language_selection(metrics_data, args.min_projects)

    # Создаем сбалансированный график
    balanced_path = create_balanced_chart(balanced_selection, f"{args.out}.png")

    # Выводим результаты
    logger.info(f"\n🎯 СБАЛАНСИРОВАННЫЙ АНАЛИЗ МАСШТАБА ПРОЕКТОВ")
    logger.info("=" * 80)

    logger.info("📊 ЛЕГЕНДА КАТЕГОРИЙ:")
    logger.info("  КРУПНЫЙ (7.0-10.0) - Высокопопулярные проекты с большой кодовой базой")
    logger.info("  СРЕДНИЙ (4.5-6.9) - Заметные проекты со значительной функциональностью")
    logger.info("  НЕБОЛЬШОЙ (2.5-4.4) - Специализированные проекты или утилиты")
    logger.info("  МИНИМАЛЬНЫЙ (0.0-2.4) - Простые инструменты, скрипты")
    logger.info("")

    # Группируем по категориям для вывода
    categories = {}
    for lang_data in balanced_selection:
        category = lang_data[6]
        if category not in categories:
            categories[category] = []
        categories[category].append(lang_data)

    # Выводим по категориям
    for category_name in ["КРУПНЫЙ", "СРЕДНИЙ", "НЕБОЛЬШОЙ", "МИНИМАЛЬНЫЙ"]:
        if category_name in categories:
            logger.info(f"\n{category_name}:")
            for lang, composite, stars, forks, issues, count, _ in categories[category_name]:
                logger.info(f"  {lang:<15} {composite:5.1f}/10 | Stars:{stars:4.0f} Forks:{forks:3.0f} Issues:{issues:3.0f} (n={count})")

    logger.info(f"\n✅ ГРАФИК СОХРАНЕН: {balanced_path}")
    logger.info("🎯 Сбалансированный анализ масштаба проектов завершен!")


if __name__ == "__main__":
    main()
