"""
Анализ масштаба и сложности проектов по языкам программирования
Задача 5: На чем пишут большие проекты, а на чем небольшие?
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
    Анализирует масштаб проектов по языкам используя реальные метрики:
    - star_count: популярность проекта
    - forks_count: активность сообщества
    - open_issues_count: сложность поддержки
    """
    logger.info("🏗️  Анализ масштаба проектов по языкам программирования...")

    # Словари для метрик
    stars_by_lang: Dict[str, List[int]] = defaultdict(list)
    forks_by_lang: Dict[str, List[int]] = defaultdict(list)
    issues_by_lang: Dict[str, List[int]] = defaultdict(list)

    total_projects = 0
    projects_analyzed = 0

    for p in iter_projects({"languages": 1, "star_count": 1, "forks_count": 1, "open_issues_count": 1}):
        total_projects += 1

        languages = p.get("languages", {})
        if not languages:
            continue

        # Собираем метрики только для проектов с валидными данными
        star_count = p.get("star_count")
        forks_count = p.get("forks_count")
        issues_count = p.get("open_issues_count")

        has_valid_data = (
            star_count is not None and star_count >= 0 and
            forks_count is not None and forks_count >= 0 and
            issues_count is not None and issues_count >= 0
        )

        if not has_valid_data:
            continue

        projects_analyzed += 1

        # Добавляем метрики для каждого языка проекта
        for lang in languages.keys():
            stars_by_lang[lang].append(int(star_count))
            forks_by_lang[lang].append(int(forks_count))
            issues_by_lang[lang].append(int(issues_count))

    logger.info(f"📊 Статистика анализа:")
    logger.info(f"  Всего проектов в базе: {total_projects}")
    logger.info(f"  Проектов с полными метриками: {projects_analyzed}")
    logger.info(f"  Уникальных языков: {len(stars_by_lang)}")

    return {
        'stars': stars_by_lang,
        'forks': forks_by_lang,
        'issues': issues_by_lang
    }


def filter_and_analyze(metrics_data: Dict[str, Dict[str, List[int]]],
                      min_projects: int = 10,
                      top_n: int = 15):
    """Фильтрует языки и вычисляет медианные значения"""

    results = {}

    for metric_name, lang_data in metrics_data.items():
        # Фильтруем языки с достаточным количеством проектов
        filtered_data = {
            lang: values for lang, values in lang_data.items()
            if len(values) >= min_projects
        }

        logger.info(f"  {metric_name}: {len(filtered_data)} языков после фильтрации")

        if not filtered_data:
            continue

        # Вычисляем медианы
        medians = []
        for lang, values in filtered_data.items():
            medians.append((lang, median(values), len(values)))

        # Сортируем по убыванию медианы и берем топ-N
        medians.sort(key=lambda x: x[1], reverse=True)
        results[metric_name] = medians[:top_n]

    return results


def create_scale_chart(metric_results: List[Tuple[str, float, int]],
                      metric_name: str,
                      output_path: str):
    """Создает график масштаба проектов по языкам"""

    if not metric_results:
        logger.error(f"❌ Нет данных для метрики '{metric_name}'")
        return None

    # Подготавливаем данные для графика
    labels = [f"{lang} ({count} проектов)" for lang, _, count in metric_results]
    values = [median_val for _, median_val, _ in metric_results]

    # Названия для графиков
    titles = {
        'stars': 'Популярность языков по медианному количеству звёзд',
        'forks': 'Активность сообщества по медианному количеству форков',
        'issues': 'Сложность поддержки по медианному количеству issues'
    }

    xlabels = {
        'stars': 'Звёзд (медиана)',
        'forks': 'Форков (медиана)',
        'issues': 'Issues (медиана)'
    }

    descriptions = {
        'stars': '🔴 Высокие значения: популярные языки для известных проектов\n🟡 Низкие значения: нишевые языки или новые проекты',
        'forks': '🔴 Высокие значения: языки с активным сообществом\n🟡 Низкие значения: специализированные или корпоративные языки',
        'issues': '🔴 Высокие значения: сложные проекты с большой кодовой базой\n🟡 Низкие значения: простые или хорошо поддерживаемые проекты'
    }

    # Создаем график
    result_path = barh_chart(
        labels=labels,
        values=values,
        out_path=output_path,
        title=titles.get(metric_name, metric_name),
        xlabel=xlabels.get(metric_name, metric_name),
        ylabel="Языки программирования"
    )

    # Выводим интерпретацию
    logger.info(f"📈 ИНТЕРПРЕТАЦИЯ РЕЗУЛЬТАТОВ ({metric_name}):")
    logger.info(descriptions.get(metric_name, ""))
    logger.info(f"✅ График сохранен: {result_path}")

    return result_path


def main():
    parser = argparse.ArgumentParser(
        description="Анализ масштаба и сложности проектов по языкам программирования"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Количество топ языков для отображения"
    )
    parser.add_argument(
        "--min-projects",
        type=int,
        default=15,  # Увеличили для более стабильных результатов
        help="Минимальное количество проектов для языка"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="/app/outputs/repo_size_analysis.png",
        help="Базовый путь для сохранения графиков"
    )
    parser.add_argument(
        "--metric",
        type=str,
        choices=['stars', 'forks', 'issues'],
        default='stars',
        help="Метрика для анализа"
    )

    args = parser.parse_args()

    # Анализируем масштаб проектов
    metrics_data = analyze_project_scale()

    # Фильтруем и обрабатываем данные
    filtered_results = filter_and_analyze(metrics_data, args.min_projects, args.top)

    if not filtered_results:
        logger.error("❌ После фильтрации не осталось языков для анализа")
        logger.info("💡 Попробуйте уменьшить --min-projects")
        return

    # Создаем график для выбранной метрики
    selected_metric = args.metric
    if selected_metric in filtered_results and filtered_results[selected_metric]:
        metric_results = filtered_results[selected_metric]

        # Создаем график
        output_path = args.out.replace('.png', f'_{selected_metric}.png')
        create_scale_chart(metric_results, selected_metric, output_path)

        # Выводим детальные результаты
        logger.info(f"🏆 ТОП-{args.top} ЯЗЫКОВ ПО {selected_metric.upper()}:")
        for i, (lang, median_val, count) in enumerate(metric_results, 1):
            logger.info(f"  {i:2d}. {lang:<20} {median_val:8.1f} (на основе {count} проектов)")

        # Анализ результатов
        logger.info("\n🔍 КЛЮЧЕВЫЕ ВЫВОДЫ:")
        if selected_metric == 'stars':
            logger.info("  • Языки с высокими значениями: популярны среди сообщества")
            logger.info("  • Языки с низкими значениями: специализированные или новые")
        elif selected_metric == 'forks':
            logger.info("  • Высокие значения: активное сообщество, много контрибьюторов")
            logger.info("  • Низкие значения: закрытые проекты или малая аудитория")
        else:  # issues
            logger.info("  • Высокие значения: сложные проекты, большая кодовая база")
            logger.info("  • Низкие значения: простые проекты или хорошая архитектура")

    else:
        logger.error(f"❌ Метрика '{selected_metric}' недоступна после фильтрации")
        logger.info("💡 Доступные метрики:")
        for metric_name, data in filtered_results.items():
            if data:
                logger.info(f"  {metric_name}: ✅ {len(data)} языков")

    logger.info("🎯 Анализ масштаба проектов завершен!")


if __name__ == "__main__":
    main()