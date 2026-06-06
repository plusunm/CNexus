# Brain-Memory G1 — Quick Start Guides

Three practical paths: **daily use**, **development integration**, and **deployment for others**.

---

## 1. Daily Use (3 Steps)

For running the system locally, checking status, capturing memories, and occasional chat.

### Step 1 — One-shot bootstrap

From the project root:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts/load_g1.ps1
```

```bash
# Linux / macOS — manual equivalent
export BRAIN_MEMORY_ROOT="$(pwd)"
export PYTHONPATH="$(pwd)"
export BM_MEMORY_DIR="${BM_MEMORY_DIR:-/var/lib/brain-memory-g1/data}"
mkdir -p "$BM_MEMORY_DIR"

cd brain-memory-ui && python -m api.main &   # :8000
cd brain-memory-ui/frontend && npm run dev   # :3000
```

The bootstrap script will:

- Use persistent data at `C:\ProgramData\brain-memory-g1\data` (Windows) or `$BM_MEMORY_DIR`
- Start the API on `:8000` and the frontend on `:3000`
- Fall back to hash embeddings if Ollama is unavailable (memory still works)

Open **http://localhost:3000** in your browser.

### Step 2 — Know the four pages

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/` | Stability, narrative coherence, identity metrics |
| Memory | `/memory` | Manual capture and recall testing |
| Chat | `/chat` | Memory-augmented conversation (requires a model) |
| Run logs | `/logs` | Capture, recall, chat, and system events |

**Common actions:**

- On **Memory**, write a goal with `layer=goal` and high importance (0.8+)
- Test recall: *"What did we do before?"*, *"What is brain-memory-g1?"*
- On **Models** (`/models`), configure Ollama / OpenAI / DeepSeek, then use **Chat**

### Step 3 — Routine maintenance

```powershell
# Health check
Invoke-RestMethod http://127.0.0.1:8000/health

# Current cognitive state
Invoke-RestMethod http://127.0.0.1:8000/governance/state

# Run one governance cycle (drift detection, stability validation)
Invoke-RestMethod -Method POST http://127.0.0.1:8000/governance/cycle
```

**Notes:**

- Memory and recall **do not require an LLM**; only `/chat` does
- When importing chat transcripts, stop the API first or wait until import finishes — avoid two processes writing the same data directory

---

## 2. Development Integration (3 Steps)

For Cursor, Python scripts, and other agents sharing one cognitive runtime.

### Step 1 — Route everything through the HTTP API

All external callers should hit **one API instance**. Do not run multiple `create_runtime()` processes against the same disk path while the API is live.

```text
Your app / Cursor agent / automation script
        ↓  HTTP
http://127.0.0.1:8000
        ↓
BrainMemoryRuntime (single instance per API process)
        ↓
BM_MEMORY_DIR  (shared persistent store)
```

**Core endpoints:**

```http
POST /memory/capture       # Write memory
GET  /memory/recall?query= # Semantic recall + SelfModel context
POST /chat                 # Memory-augmented chat (optional)
GET  /governance/state     # Current runtime state
POST /governance/cycle     # Governance cycle
WS   /ws/state             # Live state stream
WS   /logs/ws              # Live log stream
```

### Step 2 — Code examples

**Python (recommended for integrations):**

```python
import requests

BASE = "http://127.0.0.1:8000"

# Capture
requests.post(f"{BASE}/memory/capture", json={
    "role": "user",
    "content": "My long-term goal is to build a stable AI assistant",
    "layer": "goal",
    "importance": 0.9,
})

# Recall (returns full context: DNA, narrative, SelfModel, relevant memories)
ctx = requests.get(f"{BASE}/memory/recall", params={
    "query": "What is my long-term goal?"
}).json()["context"]

# Chat with memory
reply = requests.post(f"{BASE}/chat", json={
    "message": "Based on our past work, what should I do next?",
    "use_memory": True,
}).json()["reply"]
```

**PowerShell:**

```powershell
$body = @{ role="user"; content="Message from Cursor"; layer="episodic"; importance=0.7 } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/memory/capture" -Body $body -ContentType "application/json"

Invoke-RestMethod "http://127.0.0.1:8000/memory/recall?query=brain-memory-g1"
```

**Python SDK (offline scripts / tests only — do not write concurrently with the API):**

```python
from brain_memory import create_runtime

rt = create_runtime(project_root=".")
rt.process_interaction("User said...", assistant_output="Assistant replied...")
print(rt.recall("related question"))
```

### Step 3 — Import Cursor chat transcripts

```powershell
cd <project-root>
$env:BM_MEMORY_DIR = "C:\ProgramData\brain-memory-g1\data"
python scripts/import_chat_transcript.py `
  "<path-to>/agent-transcripts/<uuid>/<uuid>.jsonl" `
  --root "<project-root>"
```

Each imported turn:

1. Calls `process_interaction()` to update the unified SelfModel
2. Writes semantic / narrative memories

**Cursor integration pattern:** treat Cursor as the reasoning layer and Brain-Memory G1 as the continuity layer — capture turns via `POST /memory/capture` or batch-import JSONL transcripts.

---

## 3. Deployment for Others (3 Steps)

For LAN or server hosting so Web, mobile, and agents share one brain.

### Step 1 — Environment and data directory

**Requirements:**

- Python 3.10+
- Node.js 18+ (frontend)
- Optional: Ollama (embeddings + local LLM)

**Key environment variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `BM_MEMORY_DIR` | Persistent data path (must be stable) | `C:\ProgramData\brain-memory-g1\data` |
| `BRAIN_MEMORY_ROOT` | Project root | `/opt/brain-memory-g1` |
| `BM_API_PORT` | API port | `8000` |
| `BM_CORS_ORIGINS` | Allowed frontend origins | `http://192.168.1.10:3000,https://your.domain` |
| `NEXT_PUBLIC_API_BASE` | Frontend → API URL | `http://192.168.1.10:8000` |
| `NEXT_PUBLIC_WS_BASE` | WebSocket URL | `ws://192.168.1.10:8000` |

**Production API (listens on all interfaces):**

```bash
export BM_MEMORY_DIR=/var/lib/brain-memory-g1/data
export BRAIN_MEMORY_ROOT=/opt/brain-memory-g1
export PYTHONPATH=/opt/brain-memory-g1
cd brain-memory-ui
python -m api.main   # default 0.0.0.0:8000
```

**Production frontend:**

```bash
cd brain-memory-ui/frontend
export NEXT_PUBLIC_API_BASE=http://192.168.1.10:8000
export NEXT_PUBLIC_WS_BASE=ws://192.168.1.10:8000
npm run build && npm start   # :3000
```

### Step 2 — Models and security

1. Open **http://&lt;server-ip&gt;:3000/models**
2. Add Ollama / OpenAI / DeepSeek (or compatible) profiles; set one as default
3. Click **Test** to verify LLM connectivity

**Security checklist:**

- Do not expose the API directly on the public internet; use Nginx/Caddy with HTTPS
- Keep model API keys in `config/models.local.json` — never commit secrets
- Firewall only required ports (e.g. 443 → reverse proxy → 8000)
- Back up the entire `BM_MEMORY_DIR` directory regularly

### Step 3 — Multi-client access and ops

```text
         ┌─ Web UI (:3000)
         ├─ Mobile browser / app (REST)
Clients ─┼─ Cursor / scripts (POST /memory/capture)
         └─ Other agents (GET /memory/recall)
                    │
                    ▼
            Single API instance (:8000)
                    │
                    ▼
         BM_MEMORY_DIR (shared memory & identity)
```

**Operations:**

```bash
# Health probe (monitoring)
curl http://<server>:8000/health

# Backup data
cp -a "$BM_MEMORY_DIR" "/backup/brain-memory-$(date +%Y%m%d)"

# Logs: Web UI /logs or GET /logs
```

**Deployment rules:**

- ✅ Multiple clients **reading** + one API **writing** — supported
- ✅ Same `BM_MEMORY_DIR` across clients — one shared identity and memory
- ❌ Do not run multiple API processes or direct-write scripts against the same data directory concurrently

---

## Cheat Sheet

| Scenario | Entry point |
|----------|-------------|
| Daily startup | `scripts/load_g1.ps1` → http://localhost:3000 |
| Script integration | `POST/GET http://127.0.0.1:8000/memory/*` |
| Import chat history | `scripts/import_chat_transcript.py` |
| Share with others | Fixed `BM_MEMORY_DIR` + single API + `NEXT_PUBLIC_API_BASE` |
| Repository | https://github.com/plusunm/brain-memory-g1 |

See also: [ARCHITECTURE.md](ARCHITECTURE.md) · [DEPLOYMENT.md](DEPLOYMENT.md)
