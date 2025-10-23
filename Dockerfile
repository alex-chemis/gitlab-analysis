FROM python:3.12-slim

# системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tzdata && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# зависимости python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# исходники
COPY src ./src

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

COPY README.md .
COPY .env .

# небезопасно запускать от root
RUN useradd -m appuser
USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

ENTRYPOINT ["./entrypoint.sh"]
