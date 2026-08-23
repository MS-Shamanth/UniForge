# Deploying UniForge

## The error you hit

```
Error loading ASGI app. Could not import module "app".
```

Uvicorn was told to import `app`. There is no top-level `app.py` in this repository — the
ASGI application lives at `server/app.py`, so the import path is `server.app:app`.

**Correct start command:**

```
python -m uvicorn server.app:app --host 0.0.0.0 --port $PORT --workers 1
```

Three things go wrong most often, in order of frequency:

| Symptom | Cause | Fix |
|---|---|---|
| `Could not import module "app"` | start command says `app:app` | use `server.app:app` |
| Deploy succeeds, page is a JSON blob | `web/dist` missing | run `npm run build` in `web/` and commit it |
| Health check times out on first boot | check hit an endpoint that compiles | point it at `/api/health`, which never compiles |

---

## Option A — Render, Python runtime (recommended)

`render.yaml` in the repository root already describes this. Render will pick it up if you
create the service as a **Blueprint**. To configure it by hand instead:

- **Environment:** Python 3
- **Build command:** `pip install --upgrade pip && pip install -r requirements.txt`
- **Start command:** `python -m uvicorn server.app:app --host 0.0.0.0 --port $PORT --workers 1`
- **Health check path:** `/api/health`

**Environment variables**

| Key | Value | Why |
|---|---|---|
| `PYTHON_VERSION` | `3.12.7` | matches `runtime.txt` |
| `UNIFORGE_ROW_LIMIT` | `1000` | caps rows per run so the free tier's memory holds |
| `UNIFORGE_ALLOW_FETCH` | `0` | no live retrieval in a hosted environment |
| `PYTHONUNBUFFERED` | `1` | logs appear immediately |

This path installs **no Node toolchain**, which is why `web/dist` is committed. Rebuild it
before every push that touches the frontend:

```bash
cd web && npm run build && cd ..
git add web/dist && git commit -m "rebuild web bundle"
```

### Cold start

The pipeline compiles on the **first API request**, not at boot — roughly 3 to 10 seconds
for 1,000 rows. `/api/health` answers instantly and reports `run.ready`, so the health
check never waits on it. The landing page is fully static and does not touch the API at
all; only `/console` does.

On Render's free tier the instance also sleeps after inactivity, so the first visit after
a nap pays both the wake-up and the compile.

---

## Option B — Docker (no committed bundle)

`Dockerfile` builds the frontend and the backend in one image, so `web/dist` need not be
in the repository. Set the Render environment to **Docker** and it needs nothing else.

```bash
docker build -t uniforge .
docker run -p 8000:8000 uniforge
```

The image runs `uniforge compile` during the build, so a pipeline error fails the build
rather than the running service, and the first request is already warm.

---

## Verifying a deployment

Both suites accept a base URL, so point them at the live service:

```bash
python tools/smoke_api.py https://your-service.onrender.com
python tools/smoke_web.py https://your-service.onrender.com
```

The API suite asserts the things that matter: 252 delivery columns, zero hallucinations,
no claim published without a locator, 100% character-limit and approved-unit compliance,
and that a marketplace URL is refused by the sourcing gate.

---

## Other hosts

`Procfile` covers anything that reads one (Railway, Heroku-likes). The start command is
identical. Two requirements hold everywhere:

- **Writable disk.** The compiler writes to `data/out/`. On an ephemeral filesystem the
  artefacts vanish on restart, which is harmless — they are rebuilt on the next compile.
- **Memory.** A 1,000-row run with the full evidence ledger sits comfortably under 512 MB.
  Lower `UNIFORGE_ROW_LIMIT` if a host is tighter than that.
