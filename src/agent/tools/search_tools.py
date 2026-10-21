"""Semantic lookups — Chroma side of the FC33 routing split (FC9 searches,
FC22 catalog/degree questions). Never backfilled from the SQL side: an empty
collection answer stays empty (grounded-answers rule)."""
from __future__ import annotations

from typing import List, Optional


class SearchTools:
    """Closure-style toolset over the vector manager."""

    def __init__(self, vector_db_manager) -> None:
        self._vector = vector_db_manager

    def semantic_courses(self, query: str, k: int = 6) -> List[dict]:
        """FC9 semantic search over course descriptions → normalized hits."""
        if self._vector is None or not (query or "").strip():
            return []
        hits = self._vector.similarity_search("courses", query, k=k)
        results: List[dict] = []
        for hit in hits:
            metadata = hit.get("metadata") or {}
            results.append({
                "course_id": metadata.get("course_id") or hit["id"].split(":", 1)[-1],
                "title": metadata.get("title") or hit["text"].split(".")[0],
                "description": metadata.get("description") or "",
                "credit_hours": metadata.get("credit_hours"),
            })
        return results

    def catalog_search(self, query: str, k: int = 4) -> List[dict]:
        """FC22 fuel: degree-requirement / certificate / general-core text."""
        if self._vector is None or not (query or "").strip():
            return []
        hits = self._vector.similarity_search("catalog", query, k=k)
        return [
            {"source": hit.get("metadata", {}).get("source"),
             "kind": hit.get("metadata", {}).get("kind"),
             "text": hit["text"][:1200]}
            for hit in hits
        ]