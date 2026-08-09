# syntax=docker/dockerfile:1
# Production image. Frontend assets are bundled with Bun, then the Python app is
# assembled with uv on Python 3.13-slim. Runs as a non-root user.

FROM oven/bun:1 AS frontend
WORKDIR /build
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile
COPY tsconfig.json biome.json ./
COPY assets ./assets
RUN bun run build

FROM python:3.13-slim AS app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=config.settings.production

# uv for reproducible, fast installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen || uv sync --no-dev

COPY . .
COPY --from=frontend /build/assets/vendor ./assets/vendor

RUN useradd --system --uid 10001 appuser \
    && mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app
USER appuser

RUN uv run python manage.py collectstatic --noinput || true

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready').status==200 else 1)"]

CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
