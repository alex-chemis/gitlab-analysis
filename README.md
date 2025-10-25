# Gitlab language analysis

## Тема: "Анализ использования языков программирования на GitLab"

## Задачи:
1. Распределение языков по количеству проектов - Сколько проектов используют определённый язык?
2. Кластеризация проектов по использованным языкам - Разные языки используются для разных целей. Значит, по языкам проекты можно кластеризировать по типам, например: "веб-приложения", "мобильная разработка" и т. д.
3. Прогноз популярности языков - Как изменится популярность языков в ближайшем будущем?
4. Сколько проектов используют определённое количество языков? - Сколько тех, что используют лишь один язык? А два? А три?  т. д.
5. Как соотносятся размеры репозиториев и их языки? - На чем пишут большие проекты, а на чём небольшие?

## Команда:
- Семичев Александр Сергеевич, гр. 5140904/50202, @alex-chemis
- Нефедев Виктор Константинович, гр. 5140904/50202, @Koteron
- Истаев Эрдэм Эрдэниевич, гр. 5140904/50101, @Isterd
- Ефимов Максим Андреевич, гр. 5140904/50201, @Grayaga1n

## Первичный анализ

- Формат датасета: https://github.com/alex-chemis/gitlab-analysis/tree/main/data
- Cкрипты: https://github.com/alex-chemis/gitlab-analysis/tree/main/src/scripts
- Артефакты: https://github.com/alex-chemis/gitlab-analysis/tree/main/outputs


## Запуск

#### 1) Нужно изменить `.env.example` → `.env` и задать `GITLAB_TOKEN`.
   Токен повышает лимиты API (персональный токен GitLab).

#### 2) Собрать проект:
```bash
docker compose up -d --build
```

#### 3) Далее можно использовать следующие команды:
```bash
# Для сбора данных
docker compose run --rm app python -m app fetch

# Для построения гистограммы топ 20 языков
docker compose run --rm app python -m scripts.lang_distribution_chart --top 20 --out /app/outputs/lang_top20.png

# Для построения графика медианных форков по языкам
docker compose run --rm app python -m scripts.median_forks_by_language \
		--top-langs 20 --top 20 --min-projects 10 --out /app/outputs/median_forks_by_language.png

# Для построения графика медианных звёзд по языкам
docker compose run --rm app python -m scripts.median_stars_by_language \
		--top-langs 20 --top 20 --min-projects 10 --out /app/outputs/median_stars_by_language.png

# Для построения круговой диаграммы распределния проектов по языкам
docker compose run --rm app python -m scripts.lang_pie_chart --top 12 --out /app/outputs/lang_pie.png

# Для построения гистограммы количества языков по проектам
docker compose run --rm app python -m scripts.languages_per_project_hist --out /app/outputs/languages_per_project.png
```

#### 4) Результаты 

После выполнения вышеперечисленных команд система будет создавать графики в папке outputs

В данном репозитории приведены данные графики после обработки 10 000 данных проектов