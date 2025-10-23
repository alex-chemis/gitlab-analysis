#!/bin/sh
set -e
export PYTHONPATH="/app/src:${PYTHONPATH}"

# подхватить .env (если есть), игнорируя комментарии
if [ -f ".env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs) >/dev/null 2>&1 || true
fi

# если пришла пользовательская команда — выполнить её
if [ "$#" -gt 0 ]; then
  echo "ENTRYPOINT: exec -> $*"
  exec "$@"
fi

# режим «ничего не делаем» по флагу
if [ "${APP_AUTO_RUN:-1}" = "0" ]; then
  echo "APP_AUTO_RUN=0 -> idle mode (container stays up)."
  tail -f /dev/null
fi

# поведение по умолчанию
exec python -m app fetch-and-aggregate
