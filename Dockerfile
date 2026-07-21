# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies required to build some Python packages (e.g. argon2-cffi, asyncpg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default command runs the API server.
# Override with `saq src.workers.settings.settings` to run the background worker instead.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
