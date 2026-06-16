# cnexus-product

CNexus Product — standalone Mind UI (Demo + optional Runtime binding).

**Monorepo location:** `brain-memory-ui/frontend/`  
When split to its own repository, move that directory to the repo root.

## Quick start

```bash
cd brain-memory-ui/frontend   # or repo root after split
npm install
npm run dev
```

Open http://localhost:3000 → choose **Demo** (offline) or **Runtime** (live API).

## Docker

From monorepo:

```bash
docker compose -f docker-compose.product.yml up --build
```

From `brain-memory-ui/`:

```bash
docker compose -f docker-compose.product.yml up --build
```

## Runtime URL (no rebuild)

| Variable | Default |
|----------|---------|
| `CNEXUS_API_BASE` | `http://localhost:8000` |
| `CNEXUS_WS_BASE` | `ws://localhost:8000` |

Docker entrypoint writes `public/cnexus-config.json` at container start.

## API contract (UI-only dependency)

```
GET  /v1/mind/overview
WS   /ws/state
POST /chat
GET  /memory/recall
```

See [../brain-memory-ui/docs/CNEXUS_PRODUCT_API.md](../brain-memory-ui/docs/CNEXUS_PRODUCT_API.md).

## npm package

```bash
npm publish --access public   # tag: product-v*
```

Package name: `cnexus-product`

## CI

`.github/workflows/cnexus-product.yml` — build, Demo contract test, Docker image.
