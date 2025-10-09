#!/usr/bin/env bash
set -e

# если .env рядом с проектом — прокинем переменные в окружение контейнера
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs) >/dev/null 2>&1 || true
fi

# по умолчанию: собрать проекты, сохранить в Mongo и посчитать распределение
exec python -m app fetch-and-aggregate
