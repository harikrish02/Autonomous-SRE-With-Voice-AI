# 🚨 Autonomous SRE - DevOps Incident Detection & Auto-Remediation Platform

> **AI-powered incident management for distributed microservice systems** — automatically detects failures, identifies root causes via RAG, notifies operators by voice call, and executes approved remediation actions via natural language using an MCP-style Gemini agent.

Built for **Hack BLR 2026** 🏆

## Demo Video

[Demo Video (Google Drive)](https://drive.google.com/file/d/1cF8FPXTEqLGIXuP2EYlWQ4j0jak-grMB/view?usp=sharing)

---

## 🎯 The Problem

In modern microservice architectures, failures cascade silently. A single downstream service going down can degrade the entire system. Traditional monitoring forces engineers to:
- Manually detect issues buried in logs
- Dig through runbooks to find root causes
- Execute fixes under pressure — often late at night

This is **slow, error-prone, and doesn't scale**.

---

## 💡 Our Solution

An end-to-end AI platform that closes the loop from **detection → diagnosis → approval → remediation** — without manual intervention at every step.



```
User Request → Service A → Service B → Service C
                    │              │            │
                    └──────── Logs → Admin Service ────┐
                                                       │
                                               ┌───────┴───────┐
                                               │    Watchdog    │
                                               │  (10s polling) │
                                               └───────┬───────┘
                                                       │
                                          Incident Detected (error/latency)
                                                       │
                                               ┌───────┴───────┐
                                               │  Qdrant RAG   │
                                               │ Runbook Search│
                                               └───────┬───────┘
                                                       │
                                            Root cause + fix identified
                                                       │
                                               ┌───────┴───────┐
                                               │  Vapi Voice   │
                                               │  Call / API   │
                                               └───────┬───────┘
                                                       │
                                             User approves / rejects
                                                       │
                                               ┌───────┴───────┐
                                               │ InfraController│
                                               │ restart/scale  │
                                               └───────┬───────┘
                                                       │
                                              Service recovered ✅
```

---

## ✨ Key Features

| Capability | Description |
|-----------|-------------|
| 🔍 **Distributed Tracing** | Every request gets a `traceId` propagated across all services via headers |
| 📋 **Structured Logging** | JSON logs with traceId, service name, status, error type, duration — stored in SQLite |
| 💥 **Failure Simulation** | Query params (`fail=error\|timeout\|high_latency`, `fail_at=service-a\|b\|c`) to trigger realistic failures |
| 📊 **Sliding Window Detection** | Watchdog polls logs every 10s — detects error rate ≥50%, service down, or latency ≥4000ms |
| 🧠 **RAG-based Root Cause** | Qdrant vector DB with multiple runbook entries, queried via sentence-transformers embeddings |
| 📞 **Voice Approval** | Vapi integration for voice-based incident approval (with fallback REST API) |
| 🏗️ **Infra Abstraction** | `InfraController` interface with `DockerController` implementation (Kubernetes-ready) |
| 📝 **Full Audit Trail** | Every approval, action, and state transition logged with timestamps |
| 🖥️ **Real-time Dashboard** | React UI with live service status, traffic metrics, incidents, and action controls |
| 🤖 **MCP Natural Language Control** | Gemini-powered MCP endpoint translates plain-English prompts into infra actions (restart/scale/stop/transfer) with Ollama as local fallback |

---

## 🏛️ Architecture

### Services

| Service | Port | Role |
|---------|------|------|
| **Admin Service** | `8000` | Central orchestrator — logs, incidents, approvals, watchdog, MCP, infra control |
| **Service A** | `8001` | Entry point microservice |
| **Service B** | `8002` | Middle-tier microservice |
| **Service C** | `8003` | Leaf microservice |
| **Qdrant** | `6333` | Vector database for runbook search |
| **Ollama** | `11434` | Local LLM runtime — fallback for MCP when Gemini is unavailable |
| **Frontend** | `5173` | React dashboard (Vite dev server) |

### Incident Lifecycle

```
DETECTED → ANALYZED → USER_NOTIFIED → APPROVED → ACTION_TAKEN → RESOLVED
                                          └──→ REJECTED
```

1. **DETECTED** — Watchdog identifies anomaly from log patterns
2. **ANALYZED** — Qdrant returns matching runbook with root cause and fix
3. **USER_NOTIFIED** — Vapi voice call or dashboard notification
4. **APPROVED** — User approves suggested remediation
5. **ACTION_TAKEN** — InfraController executes restart/scale
6. **RESOLVED** — Service recovers, incident closed

### Watchdog Detection Rules

| Rule | Threshold | Severity |
|------|-----------|----------|
| High error rate | ≥50% errors in 30s window | High (≥80%) / Medium |
| Service down | All requests failed + connection/timeout errors | Critical |
| Latency spike | Avg ≥4000ms or ≥2 LATENCY logs in 30s | Medium |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, httpx |
| **Database** | SQLite (admin service) |
| **Vector DB** | Qdrant (Docker) + `all-MiniLM-L6-v2` sentence-transformers |
| **Frontend** | React (Vite), Tailwind CSS |
| **Infra** | Docker, docker-compose |
| **Voice** | Vapi (optional, with REST fallback) |
| **Tunneling** | ngrok (for external Vapi callbacks) |
| **MCP / AI Agent** | Google Gemini 2.5 Flash (primary) + Ollama/Llama3 (local fallback) |

---

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js](https://nodejs.org/) v18+ (for frontend dev server)
- Python 3.11+ (for seeding Qdrant)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/hack-blr-2026.git
cd hack-blr-2026
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
SERVICE_A_URL=http://localhost:8001
SERVICE_B_URL=http://localhost:8002
SERVICE_C_URL=http://localhost:8003
ADMIN_SERVICE_URL=http://localhost:8000
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MCP — Gemini-powered natural language infra control
GEMINI_API_KEY=        # Required for MCP; falls back to keyword parser if missing

# Optional — leave empty to use REST-based approval fallback
VAPI_API_KEY=
VAPI_PHONE_NUMBER=
NGROK_URL=
```

### 3. Start All Backend Services

```bash
docker-compose up --build
```

This starts the admin service, service-a/b/c, Qdrant, and Ollama in a shared Docker network.

### 4. Seed the Runbook Vector Database

```bash
pip install -r seed_requirements.txt
python seed_qdrant.py
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧪 Simulating Failures

Use query parameters to trigger realistic failure scenarios:

```bash
# Trigger a 500 error at Service B
curl "http://localhost:8001/process?fail=error&fail_at=service-b"

# Trigger a timeout at Service C
curl "http://localhost:8001/process?fail=timeout&fail_at=service-c"

# Trigger high latency at Service A
curl "http://localhost:8001/process?fail=high_latency&fail_at=service-a"
```

The **Watchdog** will detect the anomaly within 10 seconds, query the runbook database, and create an incident on the dashboard.

---

## 📡 API Reference

### Admin Service (`localhost:8000`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/logs/` | Ingest a structured log entry |
| `GET` | `/logs/` | Query logs (filters: service, trace_id, status) |
| `GET` | `/incidents/` | List all incidents |
| `GET` | `/incidents/{id}` | Get a specific incident |
| `PATCH` | `/incidents/{id}/status` | Update incident lifecycle state |
| `POST` | `/approval/approve/{id}` | Approve incident & execute remediation |
| `POST` | `/approval/reject/{id}` | Reject incident |
| `POST` | `/approval/notify/{id}` | Trigger Vapi voice call |
| `POST` | `/approval/vapi-webhook` | Vapi callback endpoint |
| `POST` | `/infra/restart/{service}` | Restart a service container |
| `POST` | `/infra/scale/{service}` | Scale service replicas |
| `GET` | `/infra/status` | All service statuses |
| `POST` | `/qdrant/query` | Query runbook by error description |
| `GET` | `/qdrant/search?q=...` | Search runbooks |
| `GET` | `/audit/` | Full audit trail |
| `POST` | `/mcp/execute` | **MCP endpoint** — send a natural language prompt to execute infra actions |

---

## 🗂️ Project Structure

```
hack-blr-2026/
├── docker-compose.yml          # Orchestrates all services
├── seed_qdrant.py              # Seeds Qdrant with runbook entries
├── seed_requirements.txt
├── test_mcp.py                 # MCP endpoint smoke tests
├── services/
│   ├── admin-service/          # Central orchestrator (FastAPI)
│   │   ├── routers/
│   │   │   ├── mcp.py          # MCP endpoint — Gemini/Ollama intent router
│   │   │   ├── logs.py
│   │   │   ├── incidents.py
│   │   │   ├── approval.py
│   │   │   ├── infra.py
│   │   │   ├── qdrant.py
│   │   │   └── audit.py
│   │   ├── models/             # SQLAlchemy models
│   │   ├── infra/              # InfraController + DockerController
│   │   └── watchdog.py         # Background anomaly detection loop
│   ├── service-a/              # Entry microservice (FastAPI)
│   ├── service-b/              # Middle microservice (FastAPI)
│   └── service-c/              # Leaf microservice (FastAPI)
└── frontend/                   # React + Vite dashboard
    └── src/
        └── components/         # ServiceCard, IncidentTimeline, LogsTable, etc.
```

---

## 🎨 Dashboard Preview

The React dashboard provides:
- 🟢🔴 **Live service health cards** with real-time status
- 📈 **Traffic metrics** — requests, success rate, error count, avg latency
- 🎛️ **Action panel** — send requests, burst errors/latency, restart/scale services
- ⚡ **Incident timeline** — with approve/reject buttons
- 📜 **Structured log stream** — filterable by service, status, and trace ID

---

## 🤖 MCP — Natural Language Infra Control

The platform exposes a **Model Context Protocol-inspired endpoint** (`POST /mcp/execute`) that lets you control your infrastructure using plain English.

### How It Works

```
Plain-English Prompt
        │
        ▼
  Gemini 2.5 Flash  ──(rate-limited?)──▶  Ollama / Llama3 (local fallback)
        │                                           │
        └──────────────────┬────────────────────────┘
                           │
              Structured JSON intent extracted:
              { action, service_name, replicas, approval_status }
                           │
               ┌───────────┴──────────────┐
               │   approved?              │ rejected?
               ▼                          ▼
     InfraController               Logged to Audit
  restart / scale / stop           (operation aborted)
```

### Supported Actions

| Action | Example Prompt | Effect |
|--------|---------------|--------|
| `restart` | `"restart service-a"` | Restarts the container via Docker API |
| `scale` | `"scale service-b to 3 replicas"` | Scales the container |
| `stop` | `"stop service-c"` | Stops the container |
| `call_transfer` | `"transfer service-a to manual support"` | Marks incident as TRANSFERRED |
| reject | `"reject restart of service-b"` | Logs rejection, no action taken |

### Fallback Chain

1. **Gemini 2.5 Flash** (primary) — fast, structured JSON output
2. **Ollama / Llama3** (local fallback) — runs inside Docker, no API key needed
3. **Keyword parser** — instant last-resort fallback for offline/no-key scenarios

### Testing the MCP Endpoint

```bash
# Approve a restart
curl -X POST http://localhost:8000/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "restart service-a"}'

# Reject an action
curl -X POST http://localhost:8000/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "reject restart of service-b"}'

# Or run the built-in test script
python test_mcp.py
```

All MCP-triggered actions are recorded in the audit trail with `approved_by: mcp_agent` and the original prompt text for full traceability.

---

## 🔑 Design Decisions

1. **MCP as the AI Control Plane** — The `/mcp/execute` endpoint acts as a natural language gateway to infrastructure. Any LLM (Gemini, Ollama, or even a keyword parser) can drive `InfraController` actions, making the system model-agnostic by design.

2. **Infra Abstraction** — `InfraController` base class with `DockerController` implementation. A `KubernetesController` placeholder exists for future extension. No Docker commands leak outside this layer.

3. **Graceful Degradation** — Vapi voice calls are optional. If `VAPI_API_KEY` is not set, the system falls back to REST-based approval seamlessly. Same for MCP — works without a Gemini key via keyword parsing.

4. **Audit Everything** — Every approval, rejection, restart, and scale action — including MCP-triggered ones — is recorded in `audit_logs` with timestamps and the originating prompt.

5. **Cascading Error Propagation** — Errors at Service C propagate through B to A with full context, mimicking real distributed system failures.

---

## 🏆 Built At

**Hack BLR 2026** — Bengaluru's flagship hackathon

---

## 📄 License

MIT License — feel free to fork, extend, and build on top of this.
