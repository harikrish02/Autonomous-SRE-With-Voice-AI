"""
Qdrant Runbook Seeder — One-time script to populate Qdrant with runbook data.

This script is SEPARATE from the main project and should be run ONCE before
starting the platform. It connects to a running Qdrant instance and loads
error patterns, runbooks, and remediation actions for the 3 microservices.

Uses sentence-transformers (all-MiniLM-L6-v2) for high-quality semantic
embeddings. The model will be downloaded on first run (~80MB).

Prerequisites:
    - Qdrant must be running:  docker-compose up -d qdrant
    - Install deps:            pip install -r seed_requirements.txt

Usage:
    cd C:\\HackBLR
    pip install -r seed_requirements.txt
    python seed_qdrant.py

Environment variables (optional):
    QDRANT_HOST  — default: localhost
    QDRANT_PORT  — default: 6333
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "runbooks"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384  # Output dimension of all-MiniLM-L6-v2

# ---------------------------------------------------------------------------
# RUNBOOK DATA
#
# Each entry contains:
#   error_pattern        — keywords/phrases the watchdog error summary would
#                          contain when this scenario happens
#   root_cause           — human-readable explanation of why this happens
#   recommended_fix      — what action to take
#   action_type          — one of: restart | scale | none
#                          "restart" → InfraController.restart_service()
#                          "scale"   → InfraController.scale_service()
#                          "none"    → no infra action, manual intervention
#   applicable_services  — comma-separated service names this applies to
#   severity             — critical | high | medium
# ---------------------------------------------------------------------------

RUNBOOKS: list[dict] = [
    # ─── Service Down / Connection Errors ───────────────────────────
    {
        "error_pattern": "Service appears DOWN all requests failed Connection timeout errors detected service unavailable",
        "root_cause": "The service process has crashed or the container has stopped responding to health checks.",
        "recommended_fix": "Restart the affected service container to restore availability.",
        "action_type": "restart",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "critical",
    },
    {
        "error_pattern": "connection_error service is unavailable cannot connect refused connection reset",
        "root_cause": "The downstream service is not accepting TCP connections. Likely the container exited or the port is not exposed.",
        "recommended_fix": "Restart the downstream service container. If it keeps crashing, check container logs for OOM or startup errors.",
        "action_type": "restart",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "critical",
    },

    # ─── High Error Rate ────────────────────────────────────────────
    {
        "error_pattern": "High error rate detected requests failed internal_error downstream_error 500 server error",
        "root_cause": "A downstream service is returning 5xx errors causing cascading failures across the call chain A to B to C.",
        "recommended_fix": "Identify the root-cause service (usually the deepest in the chain) and restart it. If errors persist after restart, escalate to the development team.",
        "action_type": "restart",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "high",
    },
    {
        "error_pattern": "High error rate internal_error 500 application exception unhandled bug logic error code defect",
        "root_cause": "Application-level bug or unhandled exception in business logic. Not an infrastructure issue.",
        "recommended_fix": "This is a code-level defect. Contact the development team to investigate and deploy a fix. No infrastructure action will resolve this.",
        "action_type": "none",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "medium",
    },

    # ─── Timeout Errors ─────────────────────────────────────────────
    {
        "error_pattern": "timeout timed out 504 gateway timeout downstream timed out request took too long",
        "root_cause": "The downstream service is taking too long to respond, exceeding the configured timeout threshold.",
        "recommended_fix": "Scale up the slow service to handle more concurrent requests.",
        "action_type": "scale",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "high",
    },
    # ─── Latency Spikes ────────────────────────────────────────────
    {
        "error_pattern": "Latency spike detected avg response time high latency requests slow response degraded performance",
        "root_cause": "The service is under heavy load or resource-constrained, causing response times to exceed acceptable thresholds.",
        "recommended_fix": "Scale up the affected service to add more capacity. Monitor after scaling to confirm latency returns to normal.",
        "action_type": "scale",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "medium",
    },
    {
        "error_pattern": "high latency slow response time degraded performance resource exhaustion CPU memory",
        "root_cause": "Resource exhaustion (CPU/memory) on the service container, or the service is blocking on a slow external dependency.",
        "recommended_fix": "Scale the service horizontally to distribute load.",
        "action_type": "scale",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "medium",
    },

    # ─── Cascading Failures ─────────────────────────────────────────
    {
        "error_pattern": "received error from service-b received error from service-c cascading downstream error upstream failure",
        "root_cause": "A failure in a downstream service (C) is cascading upstream through B and A. The root cause is at the deepest failing service.",
        "recommended_fix": "Restart the deepest failing service in the chain (usually service-c). Monitor upstream services — they should recover automatically once the root cause is fixed.",
        "action_type": "restart",
        "applicable_services": "service-c",
        "severity": "high",
    },

    # ─── Service-Specific Runbooks ──────────────────────────────────
    {
        "error_pattern": "service-a error failure crash unresponsive down entry point gateway",
        "root_cause": "Service A is the API gateway / entry point. If it fails, no external traffic can reach the system.",
        "recommended_fix": "Restart service-a immediately. This is the entry point — downtime here means total system unavailability.",
        "action_type": "restart",
        "applicable_services": "service-a",
        "severity": "critical",
    },
    {
        "error_pattern": "service-b error failure crash unresponsive down middle tier processing",
        "root_cause": "Service B is the middle-tier processing service. Failures here break the A to B to C pipeline.",
        "recommended_fix": "Restart service-b. If it keeps failing, check if service-c (its downstream dependency) is healthy first.",
        "action_type": "restart",
        "applicable_services": "service-b",
        "severity": "high",
    },
    {
        "error_pattern": "service-c error failure crash unresponsive down leaf backend",
        "root_cause": "Service C is the leaf service at the end of the chain. Failures here cascade upstream to B and A.",
        "recommended_fix": "Restart service-c. Since it has no downstream dependencies, a restart should resolve the issue cleanly.",
        "action_type": "restart",
        "applicable_services": "service-c",
        "severity": "high",
    },
    # ─── Resource / Scaling ─────────────────────────────────────────
    {
        "error_pattern": "out of memory OOM killed container memory exceeded resource limit crash restart loop",
        "root_cause": "The service container exceeded its memory limit and was killed by the container runtime.",
        "recommended_fix": "Restart the service and increase its memory limit in docker-compose.yml. Consider scaling horizontally if load is too high.",
        "action_type": "restart",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "critical",
    },
    {
        "error_pattern": "CPU throttling high CPU usage performance degradation thread starvation",
        "root_cause": "The service is CPU-bound and being throttled by container resource limits.",
        "recommended_fix": "Scale the service horizontally to distribute CPU load across multiple replicas.",
        "action_type": "scale",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "medium",
    },

    # ─── Non-Infra / Manual Intervention ────────────────────────────
    {
        "error_pattern": "logic error business rule violation data corruption invalid state unexpected behavior",
        "root_cause": "Application logic error — the service is producing incorrect results due to a bug in business logic.",
        "recommended_fix": "Contact the on-call developer.",
        "action_type": "none",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "medium",
    },
    {
        "error_pattern": "authentication authorization 401 403 forbidden unauthorized token expired permission denied",
        "root_cause": "Authentication or authorization failure. Could be expired credentials, misconfigured tokens, or permission changes.",
        "recommended_fix": "Verify service account permissions. Contact the security team.",
        "action_type": "none",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "medium",
    },
    {
        "error_pattern": "deadlock database slow SQL queries long running transactions",
        "root_cause": "The database is experiencing deadlocks or slow queries, likely due to inefficient queries or long-running transactions.",
        "recommended_fix": "Temporarily scale down to ease the load on the database or Contact the database team.",
        "action_type": "none",
        "applicable_services": "service-a, service-b, service-c",
        "severity": "medium",
    },
]

def seed_instance(client: QdrantClient, model: SentenceTransformer, label: str) -> None:
    """Seed a specific Qdrant instance (Cloud or Local)."""
    print(f"\n--- Seeding {label} ---")
    
    # Recreate collection (idempotent — safe to re-run)
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in collections:
        print(f"Deleting existing collection '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)

    print(f"Creating collection '{COLLECTION_NAME}' with vector size {VECTOR_SIZE}...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    # Build points
    print(f"Embedding {len(RUNBOOKS)} runbook entries...")
    points: list[PointStruct] = []
    for i, runbook in enumerate(RUNBOOKS):
        # Combine error_pattern + root_cause for a richer embedding
        text_to_embed = f"{runbook['error_pattern']} {runbook['root_cause']}"
        vector = model.encode(text_to_embed).tolist()

        point = PointStruct(
            id=i + 1,
            vector=vector,
            payload={
                "error_pattern": runbook["error_pattern"],
                "root_cause": runbook["root_cause"],
                "recommended_fix": runbook["recommended_fix"],
                "action_type": runbook["action_type"],
                "applicable_services": runbook["applicable_services"],
                "severity": runbook["severity"],
            },
        )
        points.append(point)
        print(f"  [{i + 1}/{len(RUNBOOKS)}] {runbook['error_pattern'][:70]}...")

    # Upsert all points
    print(f"Upserting {len(points)} points into Qdrant...")
    client.upsert(collection_name=COLLECTION_NAME, points=points)

    # Verify
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"Seeding complete for {label}!")
    print(f"   Collection : {COLLECTION_NAME}")
    print(f"   Points     : {collection_info.points_count}")


def main() -> None:
    print(f"Loading embedding model '{EMBEDDING_MODEL}'...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # 1. Seed Cloud if configured
    if QDRANT_URL and QDRANT_API_KEY:
        print(f"\nConnecting to Qdrant Cloud: {QDRANT_URL}...")
        cloud_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        seed_instance(cloud_client, model, "QDRANT CLOUD")

    # 2. Seed Local Docker
    print(f"\nConnecting to local Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    local_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    seed_instance(local_client, model, "LOCAL DOCKER")

    # Quick test queries
    # test_queries = [
    #     "service-c is down connection refused",
    #     "High error rate detected 100% requests failed internal_error",
    #     "Latency spike detected avg response time 5000ms slow",
    #     "logic error business rule violation unexpected behavior",
    # ]
    # for query in test_queries:
    #     print(f"\n--- Test: '{query}' ---")
    #     qv = model.encode(query).tolist()
    #     results = client.search(collection_name=COLLECTION_NAME, query_vector=qv, limit=2)
    #     for hit in results:
    #         print(f"  Score: {hit.score:.4f} | Action: {hit.payload['action_type']}")
    #         print(f"  Fix  : {hit.payload['recommended_fix'][:100]}")


if __name__ == "__main__":
    main()