# DevOps Incident Detection & Auto-Remediation Platform

## The Problem

In modern microservice architectures, failures cascade silently — a single downstream service going down can degrade the entire system. Traditional monitoring requires engineers to manually detect issues, look up runbooks, and execute fixes. This is slow, error-prone, and doesn't scale.

## Our Solution

An **AI-powered DevOps platform** that automatically detects incidents across a distributed microservice system, identifies root causes using vector-similarity runbook search, notifies operators via voice call, and executes approved remediation actions — all without manual intervention.

## How It Works

```
User Request → Service A → Service B → Service C
                    │              │            │
                    └──────── Logs sent to Admin Service ────┐
                                                             │
                                                     ┌──────┴──────┐
                                                     │   Watchdog   │
                                                     │  (10s poll)  │
                                                     └──────┬──────┘
                                                             │
                                              Incident Detected (error rate/latency)
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

## Key Capabilities

| Capability | Description |
|-----------|-------------|
| **Distributed Tracing** | Every request gets a `traceId` propagated across all services via headers |
| **Structured Logging** | JSON logs with traceId, service name, status, error type, duration — stored in SQLite |
| **Failure Simulation** | Query params (`fail=error\|timeout\|high_latency`, `fail_at=service-a\|b\|c`) to trigger realistic failures |
| **Sliding Window Detection** | Watchdog polls logs every 10s, detects error rate ≥50%, service down, latency ≥4000ms |
| **RAG-based Root Cause** | Qdrant vector DB with 15 runbook entries, queried using sentence-transformers embeddings |
| **Voice Approval** | Vapi integration for voice-based incident approval (with fallback REST API) |
| **Infra Abstraction** | `InfraController` interface with `DockerController` implementation (Kubernetes-ready) |
| **Full Audit Trail** | Every approval, action, and state transition logged with timestamps |
| **Real-time Dashboard** | React UI with live service status, traffic metrics, incidents, and action controls |

## Incident Lifecycle

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

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, httpx |
| Database | SQLite (admin service) |
| Vector DB | Qdrant (Docker, sentence-transformers all-MiniLM-L6-v2) |
| Frontend | React (Vite), Tailwind CSS |
| Infra | Docker, docker-compose |
| Voice | Vapi (optional, with REST fallback) |
| Tunneling | ngrok (for external Vapi callbacks) |

## What Makes This Different

1. **End-to-end automation** — from detection to remediation, not just alerting
2. **Voice-first approval** — operators don't need to be at a screen
3. **RAG-powered analysis** — runbook lookup via semantic search, not keyword matching
4. **Infra-agnostic** — abstracted controller layer supports Docker today, Kubernetes tomorrow
5. **Fully observable** — every action has an audit trail, every request has a trace