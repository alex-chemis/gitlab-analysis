"""
Комплексный анализ масштаба проектов по языкам программирования
ОТНОСИТЕЛЬНАЯ КЛАССИФИКАЦИЯ - делит языки на категории по перцентилям
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

        star_count = p.get("star_count", 0) or 0
        forks_count = p.get("forks_count", 0) or 0
        issues_count = p.get("open_issues_count", 0) or 0

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


def calculate_relative_composite_score(stars_median: float, forks_median: float, issues_median: float,
                                     all_scores: List[float]) -> Tuple[float, str]:
    """
    ОТНОСИТЕЛЬНАЯ классификация - делит языки на категории по перцентилям
    """
    # Вычисляем композитную оценку (простая сумма нормализованных значений)
    composite = (stars_median * 0.4 + forks_median * 0.35 + issues_median * 0.25)

    # Определяем категорию ОТНОСИТЕЛЬНО других языков
    if not all_scores:
        return composite, "НЕИЗВЕСТНО"

    # Сортируем все оценки для вычисления перцентилей
    sorted_scores = sorted(all_scores)
    n = len(sorted_scores)

    # Находим позицию текущего языка
    position = sorted_scores.index(composite) if composite in sorted_scores else n // 2
    percentile = (position / n) * 100

    # Определяем категорию по перцентилю
    if percentile >= 90:
        category = "ОЧЕНЬ КРУПНЫЙ"  # Топ 10%
    elif percentile >= 70:
        category = "КРУПНЫЙ"        # Топ 30%
    elif percentile >= 40:
        category = "СРЕДНИЙ"        # Средние 30%
    elif percentile >= 20:
        category = "НЕБОЛЬШОЙ"      # Нижние 20%
    else:
        category = "МИНИМАЛЬНЫЙ"    # Самые маленькие 20%

    return round(composite, 1), category


def get_balanced_language_selection(metrics_data: Dict, min_projects: int = 10):
    """
    Выбирает сбалансированную выборку языков из всех категорий
    """
    composite_scores = []
    all_composite_scores = []

    # Сначала собираем все оценки для относительной классификации
    for lang in set().union(*[set(data.keys()) for data in metrics_data.values()]):
        if all(lang in metrics_data[metric] for metric in ['stars', 'forks', 'issues']):
            stars_vals = metrics_data['stars'][lang]
            forks_vals = metrics_data['forks'][lang]
            issues_vals = metrics_data['issues'][lang]

            if len(stars_vals) >= min_projects:
                stars_med = median(stars_vals)
                forks_med = median(forks_vals)
                issues_med = median(issues_vals)

                # Временная оценка для вычисления перцентилей
                temp_composite = (stars_med * 0.4 + forks_med * 0.35 + issues_med * 0.25)
                all_composite_scores.append(temp_composite)

    # Теперь вычисляем финальные оценки с относительной классификацией
    for lang in set().union(*[set(data.keys()) for data in metrics_data.values()]):
        if all(lang in metrics_data[metric] for metric in ['stars', 'forks', 'issues']):
            stars_vals = metrics_data['stars'][lang]
            forks_vals = metrics_data['forks'][lang]
            issues_vals = metrics_data['issues'][lang]

            if len(stars_vals) >= min_projects:
                stars_med = median(stars_vals)
                forks_med = median(forks_vals)
                issues_med = median(issues_vals)

                # ИСПОЛЬЗУЕМ ОТНОСИТЕЛЬНУЮ КЛАССИФИКАЦИЮ
                composite, category = calculate_relative_composite_score(
                    stars_med, forks_med, issues_med, all_composite_scores
                )
                project_count = len(stars_vals)

                composite_scores.append((lang, composite, stars_med, forks_med, issues_med, project_count, category))

    # Сортируем по убыванию оценки
    composite_scores.sort(key=lambda x: x[1], reverse=True)

    # Разделяем по категориям
    very_large = [lang for lang in composite_scores if lang[6] == "ОЧЕНЬ КРУПНЫЙ"]
    large = [lang for lang in composite_scores if lang[6] == "КРУПНЫЙ"]
    medium = [lang for lang in composite_scores if lang[6] == "СРЕДНИЙ"]
    small = [lang for lang in composite_scores if lang[6] == "НЕБОЛЬШОЙ"]
    minimal = [lang for lang in composite_scores if lang[6] == "МИНИМАЛЬНЫЙ"]

    logger.info(f"📊 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
    logger.info(f"  ОЧЕНЬ КРУПНЫЕ: {len(very_large)} языков")
    logger.info(f"  КРУПНЫЕ: {len(large)} языков")
    logger.info(f"  СРЕДНИЕ: {len(medium)} языков")
    logger.info(f"  НЕБОЛЬШИЕ: {len(small)} языков")
    logger.info(f"  МИНИМАЛЬНЫЕ: {len(minimal)} языков")

    # Выбираем по 3 языка из каждой категории (если есть)
    balanced_selection = []

    # ОЧЕНЬ КРУПНЫЕ - берем все или максимум 3
    balanced_selection.extend(very_large[:3])

    # КРУПНЫЕ - берем максимум 3
    balanced_selection.extend(large[:3])

    # СРЕДНИЕ - берем максимум 3
    balanced_selection.extend(medium[:3])

    # НЕБОЛЬШИЕ - берем максимум 3
    balanced_selection.extend(small[:3])

    # МИНИМАЛЬНЫЕ - берем максимум 3
    balanced_selection.extend(minimal[:3])

    # Если в каких-то категориях нет языков, добираем из других
    if len(balanced_selection) < 10:
        # Добавляем топовые языки из общего списка
        for lang_data in composite_scores:
            if lang_data not in balanced_selection and len(balanced_selection) < 15:
                balanced_selection.append(lang_data)

    logger.info(f"📋 ВЫБОРКА ДЛЯ ГРАФИКА: {len(balanced_selection)} языков")
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
        # Создаем информативную метку
        label = f"{lang} ({category})"
        labels.append(label)
        values.append(composite)

    # Создаем график
    result_path = barh_chart(
        labels=labels,
        values=values,
        out_path=output_path,
        title="Анализ масштаба проектов по языкам программирования",
        xlabel="Композитная оценка масштаба",
        ylabel="Языки программирования"
    )

    return result_path


def main():
    parser = argparse.ArgumentParser(
        description="Анализ масштаба проектов по языкам программирования"
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
        default="/app/outputs/project_scale_analysis.png",
        help="Путь для сохранения графика"
    )

    args = parser.parse_args()

    # Анализируем масштаб проектов
    metrics_data = analyze_project_scale()

    # Получаем сбалансированную выборку
    logger.info("📊 Формирование сбалансированной выборки...")
    balanced_selection = get_balanced_language_selection(metrics_data, args.min_projects)

    # Создаем сбалансированный график
    balanced_path = create_balanced_chart(balanced_selection, args.out)

    # Выводим результаты
    logger.info(f"\n🎯 АНАЛИЗ МАСШТАБА ПРОЕКТОВ (ОТНОСИТЕЛЬНАЯ КЛАССИФИКАЦИЯ)")
    logger.info("=" * 80)

    logger.info("📊 ЛЕГЕНДА КАТЕГОРИЙ:")
    logger.info("  ОЧЕНЬ КРУПНЫЙ - Топ 10% языков по масштабу проектов")
    logger.info("  КРУПНЫЙ - Следующие 20% (топ 11-30%)")
    logger.info("  СРЕДНИЙ - Средние 30% (31-60%)")
    logger.info("  НЕБОЛЬШОЙ - Следующие 20% (61-80%)")
    logger.info("  МИНИМАЛЬНЫЙ - Нижние 20% (81-100%)")
    logger.info("")

    # Группируем по категориям для вывода
    categories = {}
    for lang_data in balanced_selection:
        category = lang_data[6]
        if category not in categories:
            categories[category] = []
        categories[category].append(lang_data)

    # Выводим по категориям
    for category_name in ["ОЧЕНЬ КРУПНЫЙ", "КРУПНЫЙ", "СРЕДНИЙ", "НЕБОЛЬШОЙ", "МИНИМАЛЬНЫЙ"]:
        if category_name in categories and categories[category_name]:
            logger.info(f"\n{category_name}:")
            for lang, composite, stars, forks, issues, count, _ in categories[category_name]:
                logger.info(f"  {lang:<15} {composite:5.1f} | Stars:{stars:4.0f} Forks:{forks:3.0f} Issues:{issues:3.0f} (n={count})")

    logger.info(f"\n✅ ГРАФИК СОХРАНЕН: {balanced_path}")
    logger.info("🎯 Анализ масштаба проектов завершен!")


if __name__ == "__main__":
    main()
