# cnexus-runtime

CNexus Runtime — FastAPI service + Python cognitive kernel.

**Monorepo locations:**

| Component | Path |
|-----------|------|
| FastAPI app | `brain-memory-ui/api/` |
| Python kernel | `brain_memory/`, `core/`, `api/` (v1) |
| Dockerfile | `brain-memory-ui/Dockerfile.runtime` (build context = repo root) |

When split to its own repository, keep repo root as Python project root with `brain-memory-ui/api/` as the HTTP layer.

## Quick start (dev)

```bash
pip install -r requirements.txt -r brain-memory-ui/api/requirements.txt
cd brain-memory-ui
python -m api.main
```

API: http://localhost:8000 — health at `/health`

## Docker

From monorepo root:

```bash
docker compose -f docker-compose.runtime.yml up --build
```

Full stack (Product + Runtime):

```bash
docker compose -f docker-compose.full.yml up --build
```

## Product contract endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/mind/overview` | Mind dashboard snapshot |
| WS | `/ws/state` | Live state stream |
| POST | `/chat` | Cognitive chat |
| GET | `/health` | Liveness |

## CI

`.github/workflows/cnexus-runtime.yml` — pytest contract suite, Docker image.
