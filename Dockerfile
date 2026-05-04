# syntax=docker/dockerfile:1
# Multi-stage: build SPA, then run FastAPI + static files from one image.

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-prod.txt /app/backend/requirements-prod.txt
RUN pip install --no-cache-dir -r /app/backend/requirements-prod.txt

COPY backend/ /app/backend/
RUN rm -rf /app/backend/tests /app/backend/__pycache__ /app/backend/.pytest_cache 2>/dev/null || true

COPY --from=frontend-build /src/dist /app/frontend/dist

RUN mkdir -p /app/backend/data \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app --no-create-home app \
    && chown -R app:app /app

WORKDIR /app/backend

ARG APP_VERSION=0.2.0-pre.1
ARG GIT_SHA=unknown
ENV APP_VERSION=$APP_VERSION
ENV GIT_SHA=$GIT_SHA

USER app

LABEL org.opencontainers.image.title="Fine Net Dash" \
      org.opencontainers.image.description="Portfel dywidendowy (pre-alfa)" \
      org.opencontainers.image.source="https://github.com/blazejwrobel98/Fine-net-dash"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD-SHELL curl -fsS "http://127.0.0.1:$${PORT}/api/health" >/dev/null || exit 1

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host \"${HOST}\" --port \"${PORT}\""]
