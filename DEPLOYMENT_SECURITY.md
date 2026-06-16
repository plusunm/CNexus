# CNexus Deployment & Security

Local-first cognitive OS: **protect Tier 1 Runtime**, semi-open Contract/Kernel, weak-protect Product UI.

> **Principle:** UI may be open · Kernel must converge · Runtime must isolate.

See also: [EDITIONS.md](./EDITIONS.md) (**统一安装包** · 个人/企业模式), [REPO_SPLIT.md](./REPO_SPLIT.md), [CNEXUS_PRODUCT_API.md](./brain-memory-ui/docs/CNEXUS_PRODUCT_API.md)

---

## 1. Asset tiers

| Tier | What | Protect? |
|------|------|------------|
| **T1** | `core/`, `brain_memory/`, `runtime/`, `memory/`, `storage/` — recall, fusion, goal/conflict, belief/identity | **Must** — private repo + dist image |
| **T2** | `cnexus-kernel/`, `MindOverviewContract`, WS/REST schema | Semi-open — document contract, hide synthesis |
| **T3** | Float / Chat / Shell / themes | Weak — minify, no business rules |
| **T4** | User `memory/`, logs, identity state | Privacy — encryption at rest (Phase 2) |

---

## 2. Threat model (realistic)

| Threat | Mitigation |
|--------|------------|
| Docker image → full source copy | Wheel dist image (`Dockerfile.runtime`), no `COPY . .` |
| Architecture clone (MindStore / UI) | Kernel boundary CI (`npm run test:kernel-boundary`) |
| Re-badge & resell | License + API token + legal terms; Phase 3 hybrid/SaaS |

---

## 3. Three-layer isolation

```
CNexus Product (UI)     →  components/mind/*
CNexus Kernel (bridge)    →  cnexus-kernel/*
CNexus Runtime (core)     →  cnexus-runtime-core wheel / private repo
         Contract: GET /v1/mind/overview · WS /ws/state
```

Kernel convergence (done) is the security foundation: **one WS bridge, one overview hook, no UI state fusion**.

---

## 4. Deployment levels

| Level | Audience | Runtime image | License | Source in image |
|-------|----------|---------------|---------|-----------------|
| **L1 Dev** | Engineers | `Dockerfile.runtime.dev` | Off | Full repo |
| **L2 Internal** | Team / lab | `Dockerfile.runtime` | Off (`CNEXUS_DEPLOY_LEVEL=internal`) | Wheel only |
| **L3 Enterprise** | Customer on-prem | `Dockerfile.runtime` | Host-bound + API token | Wheel (+ Phase 2: compiled `.so`) |
| **L4 Commercial** | Paid product | Product public · Runtime private | Strong license · optional mTLS | No Runtime source · hybrid optional |

### Environment variables

| Variable | Purpose |
|----------|---------|
| `CNEXUS_DEPLOY_LEVEL` | `dev` · `internal` · `enterprise` · `commercial` |
| `CNEXUS_LICENSE` / `CNEXUS_LICENSE_FILE` | Host-bound token (L3+) |
| `CNEXUS_LICENSE_SECRET` | **Build-time only** — used by `scripts/issue_license.py`, never in customer images |
| `CNEXUS_LICENSE_SKIP` | CI only — do not use in production |
| `CNEXUS_API_TOKEN` | Request header `X-CNexus-Token` (L3+) |
| `CNEXUS_API_TOKEN_SKIP` | CI only |
| `BRAIN_MEMORY_ROOT` | Runtime config root (`/app` in Docker) |
| `BM_MEMORY_DIR` | Persistent memory volume |

---

## 5. Docker images

### Runtime — distribution (default)

```bash
docker build -f brain-memory-ui/Dockerfile.runtime -t cnexus-runtime .
docker run -p 8000:8000 \
  -e BM_MEMORY_DIR=/data/memory \
  -e CNEXUS_DEPLOY_LEVEL=internal \
  cnexus-runtime
```

Image contains:

- `cnexus-runtime-core` wheel (T1 packages)
- Thin HTTP layer: `brain-memory-ui/api/`
- `config/` defaults
- **No** frontend, tests, or full git tree

### Runtime — dev (full source)

```bash
docker build -f brain-memory-ui/Dockerfile.runtime.dev -t cnexus-runtime:dev .
```

### Product (UI only)

```bash
docker compose -f docker-compose.product.yml up --build
```

### Combined

```bash
docker compose -f docker-compose.full.yml up --build
```

---

## 6. License workflow (L3+)

1. Customer sends machine fingerprint (printed on failed startup or via support).
2. Vendor runs **offline** (secret never shipped):

```bash
python scripts/issue_license.py --secret "$CNEXUS_LICENSE_SECRET" --fingerprint "<customer_fp>"
```

3. Customer sets:

```bash
CNEXUS_DEPLOY_LEVEL=enterprise
CNEXUS_LICENSE=CNX1.<fingerprint>.<sig>
CNEXUS_API_TOKEN=<random>
```

4. Product reads token from `/cnexus-config.json` (written by Product entrypoint).

---

## 7. Repository split (Phase 1)

| Repo | Contains | Visibility |
|------|----------|------------|
| **cnexus-product** | `brain-memory-ui/frontend`, contract docs | Public / customer |
| **cnexus-runtime** | T1 + `brain-memory-ui/api`, wheel pipeline | **Private** |

Monorepo today mirrors both; extract per [REPO_SPLIT.md](./REPO_SPLIT.md).

---

## 8. Frontend rules (enforced in CI)

- UI / Shell **must not** import `@/lib/store` — use `@/cnexus-kernel`
- **Must not** call `mindOverview()` / WS outside `cnexus-kernel/`
- **Must not** reference Python paths (`core/`, `brain_memory/`)
- UI = render + events → kernel hooks only

```bash
cd brain-memory-ui/frontend && npm run test:kernel-boundary
```

Build hygiene: production `next build` without browser source maps; no decision logic in components.

---

## 9. Phase roadmap

### Phase 1 (now)

- [x] `DEPLOYMENT_SECURITY.md`
- [x] Wheel-based `Dockerfile.runtime`
- [x] `Dockerfile.runtime.dev` for L1
- [x] License + API token skeleton
- [x] Kernel boundary CI script
- [ ] Private runtime repo (git filter-repo)

### Phase 2 — Enterprise L3

- Nuitka/Cython compile hot paths in `core/`
- Encrypt `memory/` at rest (AES + OS keychain for Tauri)
- Split Product / Runtime release pipelines

### Phase 3 — Commercial L4

- Hybrid: Product local, Runtime cloud
- mTLS, subscription license server
- Native extensions only if L3 insufficient

---

## 10. What we are **not** doing

- JS DRM / anti-debug (false security)
- Hiding the public Contract ( slows integration)
- Protecting UI as Tier 1 (wrong layer)

**Protect the cognitive loop implementation — not every file in the monorepo.**
