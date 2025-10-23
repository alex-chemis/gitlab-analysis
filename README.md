# GitLab Language Usage Stats

Собираем хотя бы 100+ публичных проектов с GitLab API, сохраняем в MongoDB,
считаем распределение: _сколько проектов используют определённый язык_.

## Быстрый старт

1) Скопируй `.env.example` → `.env` и при необходимости задай `GITLAB_TOKEN`.
   Токен повышает лимиты API (персональный токен GitLab).

2) Запусти:
```bash
docker compose up -d --build
