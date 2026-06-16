# CNexus repository split guide

Two independently deployable products share one HTTP/WS contract.

**Security & deployment levels:** see [DEPLOYMENT_SECURITY.md](./DEPLOYMENT_SECURITY.md).  
**Personal vs Enterprise EXE:** see [EDITIONS.md](./EDITIONS.md).

```
┌─────────────────────┐     REST / WS      ┌─────────────────────┐
│   cnexus-product    │ ◄────────────────► │   cnexus-runtime    │
│   Next.js Mind UI   │   (optional)       │   FastAPI + kernel  │
└─────────────────────┘                    └─────────────────────┘
         │                                              │
         ▼                                              ▼
  Demo: local mock                           brain_memory + core
  Docker: cnexus-product                     Docker: cnexus-runtime
```

## cnexus-product

| Include | Exclude |
|---------|---------|
| `brain-memory-ui/frontend/**` | `brain_memory/`, Python `api/` |
| `brain-memory-ui/docs/CNEXUS_PRODUCT_API.md` | Runtime Dockerfile |
| `docker-compose.product.yml` | |

**Extract with git filter-repo:**

```bash
git filter-repo --path brain-memory-ui/frontend/ \
  --path brain-memory-ui/docs/CNEXUS_PRODUCT_API.md \
  --path brain-memory-ui/docker-compose.product.yml \
  --path-rename brain-memory-ui/frontend/:/
```

Then add root `README.md`, `.github/workflows/cnexus-product.yml`, and adjust compose paths.

## cnexus-runtime

| Include | Exclude |
|---------|---------|
| `brain_memory/`, `core/`, `api/` | `brain-memory-ui/frontend/` |
| `config/`, `requirements.txt` | Next.js |
| `brain-memory-ui/api/`, `Dockerfile.runtime` | |

**Extract:**

```bash
git filter-repo --path brain_memory/ --path core/ --path api/ \
  --path config/ --path requirements.txt \
  --path brain-memory-ui/api/ --path brain-memory-ui/Dockerfile.runtime \
  --path tests/test_cnexus_runtime_contract.py
```

Move `brain-memory-ui/api/` → `service/api/` (optional rename) and set `Dockerfile` build context to repo root.

## Deployment matrix

| Mode | Compose file | Data |
|------|--------------|------|
| Demo | `docker-compose.product.yml` | Mock (`demoMindOverview`) |
| Runtime only | `docker-compose.runtime.yml` | Live API |
| Combined | `docker-compose.full.yml` | Product + Runtime |

## Environment

```bash
CNEXUS_API_BASE=http://localhost:8000
CNEXUS_WS_BASE=ws://localhost:8000
```

Product image reads these at **container start** — no frontend rebuild when Runtime URL changes.

## Future: desktop (Tauri / EXE)

Embed `cnexus-product` static export or WebView; point `CNEXUS_API_BASE` to bundled Runtime or remote URL.
