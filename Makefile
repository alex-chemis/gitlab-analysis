.PHONY: up down logs rebuild aggregate fetch report

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f app

rebuild:
	docker compose build --no-cache

fetch:
	docker compose run --rm app python -m app fetch

aggregate:
	docker compose run --rm app python -m app aggregate

report:
	docker compose run --rm app python -m app report

chart_pie:
	docker compose run --rm app python -m scripts.lang_pie_chart --top 12 --out /app/outputs/lang_pie.png

chart_langs_per_project:
	docker compose run --rm app python -m scripts.languages_per_project_hist --out /app/outputs/languages_per_project.png

chart_median_forks:
	docker compose run --rm app python -m scripts.median_forks_by_language \
		--top-langs 20 --top 20 --min-projects 10 --out /app/outputs/median_forks_by_language.png

chart_median_stars:
	docker compose run --rm app python -m scripts.median_stars_by_language \
		--top-langs 20 --top 20 --min-projects 10 --out /app/outputs/median_stars_by_language.png

chart_forecast:
	docker compose run --rm app python -m scripts.forecast_languages \
    --months 18 \
    --top 10 \
    --out /app/outputs
