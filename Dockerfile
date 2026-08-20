FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SENTINEL_DB_PATH=/app/state/investigations.db

WORKDIR /app

COPY pyproject.toml README.md ./
COPY agents ./agents
COPY app ./app
COPY evaluation ./evaluation
COPY tools ./tools
COPY data ./data

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 sentinel \
    && mkdir -p /app/state \
    && chown -R sentinel:sentinel /app/state

USER sentinel

EXPOSE 8000

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
