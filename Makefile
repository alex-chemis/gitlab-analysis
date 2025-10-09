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
