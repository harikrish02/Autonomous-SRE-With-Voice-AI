# DevOps Incident Detection & Auto-Remediation Platform — Technical Details

## Architecture Overview

This platform consists of 5 main components running as separate processes/containers:

### 1. Microservices (A → B → C)

Three FastAPI services forming a request chain:

- **Service A** (port 8001) — Entry point, calls Service B
- **Service B** (port 8002) — Middle tier, calls Service C
- **Service C** (port 8003) — Leaf service, processes and returns

Each service:
- Exposes `/health` and `/process` endpoints
- Generates/propagates `traceId` via `X-Trace-Id` header
- Supports failure simulation via `fail` and `fail_at` query params
- Sends structured JSON logs to the admin service after every request

### 2. Admin Service (port 8000)

Central orchestrator with these components:

| Component | Purpose |
|-----------|---------|
| **Logs Router** | `POST /logs/`, `GET /logs/` — ingest and query structured logs |
| **Incidents Router** | CRUD for incidents with lifecycle state management |
| **Approval Router** | Approve/reject incidents, Vapi voice integration |
| **Infra Router** | Restart/scale services via Docker API |
| **Qdrant Router** | Query runbook vector database for solutions |
| **Audit Router** | `GET /audit/` — full audit trail |
| **Watchdog** | Background task polling logs every 10s for anomalies |

**Database (SQLite):**
- `logs` — all structured logs from services
- `incidents` — detected incidents with lifecycle state
- `audit_logs` — approval/action audit trail
- `service_user_mapping` — service-to-owner mapping
- `service_state` — current service status tracking

### 3. Watchdog (Background Task)

Runs inside admin service, polls every 10 seconds:

| Detection Rule | Threshold | Severity |
|---------------|-----------|----------|
| High error rate | ≥50% errors in 30s window | high (≥80%) / medium |
| Service down | All requests failed + connection/timeout errors | critical |
| Latency spike | Avg ≥4000ms or ≥2 LATENCY logs in 30s | medium |

On detection → creates incident → queries Qdrant → attaches solution → transitions to ANALYZED.

### 4. Qdrant Vector Database (port 6333)

- 15 pre-seeded runbook entries covering common failure patterns
- Embedding model: `all-MiniLM-L6-v2` (sentence-transformers)
- Queried with error description → returns root cause + recommended action
- Action types: `restart`, `scale`, `none` (manual/dev team)

### 5. React Frontend (port 5173)

Single-page dashboard with:
- **Service Cards** — live green/red status for each service
- **Traffic Metrics** — total requests, success rate, error count, avg latency
- **Action Panel** — buttons to send requests, burst errors, burst latency, restart/scale
- **Incident Timeline** — live incidents with approve/reject buttons
- **Logs Table** — real-time log stream with service/status/trace filtering

All data fetched from real APIs via polling (4-5s intervals). Vite proxy routes `/api/*` to admin service.

## Key Design Decisions

1. **Infra Abstraction** — `InfraController` base class with `DockerController` implementation. `KubernetesController` placeholder exists for future extension. No Docker commands outside this layer.

2. **Graceful Degradation** — Vapi voice calls are optional. If `VAPI_API_KEY` is not set, the system falls back to REST-based approval. Qdrant queries gracefully return "no solution" if not seeded.

3. **Audit Everything** — Every approval, rejection, restart, scale action, and state transition is recorded in `audit_logs` with timestamps and actor identification.

4. **Cascading Error Propagation** — Errors at Service C propagate through B to A with full context, mimicking real distributed system failures.

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (all services) |
| GET/POST | `/process` | Process request with optional failure simulation |
| POST | `/logs/` | Ingest log entry |
| GET | `/logs/` | Query logs (filters: service, trace_id, status, limit) |
| GET | `/incidents/` | List incidents (filters: service, status) |
| GET | `/incidents/{id}` | Get specific incident |
| PATCH | `/incidents/{id}/status` | Update incident lifecycle state |
| POST | `/approval/approve/{id}` | Approve incident + execute remediation |
| POST | `/approval/reject/{id}` | Reject incident |
| POST | `/approval/notify/{id}` | Trigger Vapi voice call |
| POST | `/approval/vapi-webhook` | Vapi callback endpoint |
| POST | `/infra/restart/{service}` | Restart service container |
| POST | `/infra/scale/{service}` | Scale service replicas |
| GET | `/infra/status` | All service statuses |
| GET | `/infra/status/{service}` | Single service status |
| POST | `/qdrant/query` | Query runbook by error description |
| GET | `/qdrant/search?q=...` | Search runbooks |
| GET | `/audit/` | Audit trail (optional incident_id filter) |

## Environment Variables (.env)

```env
SERVICE_A_URL=http://localhost:8001
SERVICE_B_URL=http://localhost:8002
SERVICE_C_URL=http://localhost:8003
ADMIN_SERVICE_URL=http://localhost:8000
QDRANT_HOST=localhost
QDRANT_PORT=6333
VAPI_API_KEY=           # Optional — leave empty for fallback mode
VAPI_PHONE_NUMBER=      # Optional
NGROK_URL=              # Optional — set when using ngrok
```
