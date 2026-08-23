# Alternative deploy path: builds the frontend and the backend in one image.
#
# Use this when you would rather not commit web/dist. Point Render at "Docker" instead
# of "Python" and it needs no further configuration.
#
#   docker build -t uniforge .
#   docker run -p 8000:8000 uniforge

# ── stage 1: build the web bundle ─────────────────────────────────────────────
FROM node:22-alpine AS web

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --omit=optional --no-audit --no-fund

COPY web/ ./
RUN npm run build


# ── stage 2: the Python service ───────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UNIFORGE_ALLOW_FETCH=0

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY uniforge/ ./uniforge/
COPY server/ ./server/
COPY tools/ ./tools/
COPY data/ ./data/

# the bundle built in stage 1
COPY --from=web /web/dist ./web/dist

# Compile once at build time so the first request is fast and any pipeline error
# fails the build rather than the running service.
RUN python -m uniforge.cli compile --limit 1000

EXPOSE 8000

# Render and most hosts inject $PORT; fall back to 8000 locally.
CMD ["sh", "-c", "python -m uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
