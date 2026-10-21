"""VectorDatabaseManager (§4) — Chroma persistent store (FC33 unstructured side).

Two routed collections (FC33):
- `courses`: course-description embeddings (FC9 semantic search); document ids
  are `course:<corpus id>`.
- `catalog`: degree-requirement documents, certificate text, general-core text
  — semantic fuel for FC22 degree/requirement questions.

The embedding model is pluggable (`vector/embeddings.py`); the manager itself
never constructs one unless asked, keeping tests offline-deterministic.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from database.base import DatabaseManager

_logger = logging.getLogger("database.vector")

COURSES_COLLECTION = "courses"
CATALOG_COLLECTION = "catalog"
COLLECTIONS = (COURSES_COLLECTION, CATALOG_COLLECTION)


class VectorDatabaseManager(DatabaseManager):
    """§4 vector side: ingest_documents + similarity_search + chat embeddings seam."""

    def __init__(self, path: str, embedding_function: Optional[Any] = None) -> None:
        super().__init__(path)
        self.path = path
        self._embedding_function = embedding_function
        self._client = None

    # ------------------------------------------------------------- lifecycle

    def connect(self) -> bool:
        """Open the persistent Chroma client (idempotent)."""
        if self.is_connected:
            return True
        import chromadb
        from chromadb.config import Settings

        Path(self.path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.path),
            settings=Settings(anonymized_telemetry=False),
        )
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        """Drop the client reference; Chroma flushes persistent data on close."""
        self._client = None
        self.is_connected = False

    def execute_query(self, query: Any, params: Any = None) -> Any:
        raise NotImplementedError(
            "VectorDatabaseManager routes by collection — use similarity_search/ingest_documents"
        )

    # ------------------------------------------------------------- collections

    def _collection(self, collection: str):
        if self._client is None:
            raise RuntimeError("VectorDatabaseManager is not connected")
        kwargs: Dict[str, Any] = {"name": collection}
        if self._embedding_function is not None:
            kwargs["embedding_function"] = self._embedding_function
            kwargs["configuration"] = {"hnsw": {"space": "cosine"}}
        return self._client.get_or_create_collection(**kwargs)

    # --------------------------------------------------------------- contracts

    def ingest_documents(self, collection: str, documents: List[dict]) -> None:
        """§4 contract: ingest id+text+metadata documents (upsert — refresh safe)."""
        if not documents:
            return
        col = self._collection(collection)
        col.upsert(
            ids=[d["id"] for d in documents],
            documents=[d["text"] for d in documents],
            # chroma rejects empty-dict metadata; None is treated as "no metadata"
            metadatas=[d.get("metadata") or None for d in documents],
        )
        _logger.info("ingested %d documents into collection %r", len(documents), collection)

    def similarity_search(
        self, collection: str, query: str, k: int = 5, where: Optional[dict] = None
    ) -> List[dict]:
        """§4 contract (FC9/FC22): nearest documents by embedding similarity.

        Empty collection → empty list (honest). Results are plain dicts:
        {id, text, metadata, distance}.
        """
        if self._collection(collection).count() == 0:
            return []
        result = self._collection(collection).query(
            query_texts=[query], n_results=k, where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        return [
            {
                "id": ids[i],
                "text": result["documents"][0][i],
                "metadata": result["metadatas"][0][i] or {},
                "distance": result["distances"][0][i],
            }
            for i in range(len(ids))
        ]

    def count(self, collection: str) -> int:
        return self._collection(collection).count()

    def reset(self, collection: str) -> None:
        """Reload semantics: drop a collection so re-seeding cannot accumulate
        stale documents (id set is always exactly the seed files' content)."""
        if self._client is not None and collection in COLLECTIONS:
            try:
                self._client.delete_collection(collection)
            except Exception:  # first run — nothing to delete
                pass
            _logger.info("reset collection %r for reload", collection)