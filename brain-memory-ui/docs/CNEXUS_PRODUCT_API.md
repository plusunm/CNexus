# CNexus Product API Contract (RC 0.1.0-alpha)

Stable surface for **CNexus Product** (Next.js / Tauri UI). UI must not import Python — only HTTP/WebSocket.

**Authoritative spec:** [RUNTIME_CONTRACT.md](./RUNTIME_CONTRACT.md)

## Stable REST

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/health` | Liveness |
| GET | `/v1/mind/overview` | Mind dashboard snapshot (`MindOverview`) |
| POST | `/v1/memory/capture` | Write memory |
| GET | `/v1/memory/recall?query=` | Recall context |
| GET | `/v1/memory/stats` | Memory stats (optional UI) |
| POST | `/v1/memory/maintenance` | Memory maintenance (optional) |

## Stable WebSocket

```
WS /ws/state
```

Payload includes `mind_overview` (~2s tick). Same shape as `GET /v1/mind/overview`.

## Types

See `frontend/lib/runtimeTypes.ts` and `cnexus-kernel/MindOverviewContract.ts`.

## Deployment modes

| Mode | UI | API | Core |
|------|----|-----|------|
| Demo | ✅ | ❌ | ❌ |
| Runtime | ✅ | ✅ | ✅ |

Desktop: sidecar on `http://127.0.0.1:8000` (auto-started).

## Docker

```bash
cd brain-memory-ui
docker compose -f docker-compose.product.yml up --build
docker compose -f docker-compose.full.yml up --build
```

Configure: `NEXT_PUBLIC_API_BASE` / `public/cnexus-config.json`

## Version

Product installer: **0.1.0-alpha** (`VERSION` at repo root)  
MindOverview schema: **1.0.0** (independent, frozen separately)
