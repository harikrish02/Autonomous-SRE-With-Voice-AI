import logging
import os
from typing import Optional

from qdrant_client import QdrantClient

logger = logging.getLogger("qdrant_service")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "runbooks"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client: Optional[QdrantClient] = None
_model = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        if QDRANT_URL and QDRANT_API_KEY:
            _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            logger.info(f"Connected to Qdrant Cloud: {QDRANT_URL}")
        else:
            _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            logger.info(f"Connected to local Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    return _client


def _get_model():
    """Lazy-load the sentence-transformers model (same as seed_qdrant.py)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
        except Exception as exc:
            logger.error(f"Failed to load embedding model: {exc}")
            raise
    return _model


def _embed(text: str) -> list[float]:
    """Embed text using the same model as seed_qdrant.py."""
    model = _get_model()
    return model.encode(text).tolist()


def query_runbook(error_description: str, top_k: int = 3) -> list[dict]:
    """
    Query Qdrant for the best matching runbook entries given an error description.
    """
    try:
        client = _get_client()
        query_vector = _embed(error_description)

        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
        )

        matches = []
        for hit in results:
            matches.append({
                "score": round(hit.score, 4),
                "error_pattern": hit.payload.get("error_pattern", ""),
                "root_cause": hit.payload.get("root_cause", ""),
                "recommended_fix": hit.payload.get("recommended_fix", ""),
                "action_type": hit.payload.get("action_type", "none"),
                "applicable_services": hit.payload.get("applicable_services", ""),
                "severity": hit.payload.get("severity", "medium"),
            })

        return matches

    except Exception as exc:
        logger.error(f"Qdrant query failed: {exc}")
        return []


def get_best_solution(error_description: str) -> Optional[dict]:
    """Get the single best matching runbook solution."""
    matches = query_runbook(error_description, top_k=1)
    if matches and matches[0]["score"] > 0.3:
        return matches[0]
    return None