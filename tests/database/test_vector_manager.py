"""VectorDatabaseManager tests (FC9, FC33) — deterministic hash embeddings.

Offline per the tester skill: an in-repo deterministic embedding function
stands in for the ONNX model; Chroma itself runs against an ephemeral
persistent path via pytest tmp_path.
"""
from pathlib import Path

import pytest
from chromadb.api.types import EmbeddingFunction

from database.vector.chroma_manager import VectorDatabaseManager
from database.vector.embeddings import HashEmbeddings

COURSES, CATALOG = "courses", "catalog"


@pytest.fixture()
def manager(tmp_path: Path) -> VectorDatabaseManager:
    mgr = VectorDatabaseManager(tmp_path / "chroma", embedding_function=HashEmbeddings())
    mgr.connect()
    yield mgr
    mgr.disconnect()


# ------------------------------------------------------------ FC9 / FC33

def test_ingest_then_similarity_search_returns_grounded_hits(manager):
    """FC9/FC33: semantic search consults only ingested corpus documents."""
    manager.ingest_documents(COURSES, [
        {"id": "course:3330", "text": "DATABASE SYSTEMS AND FILE STRUCTURES. Database system architecture; relational model.",
         "metadata": {"course_id": "3330", "department": "CSE"}},
        {"id": "course:1426", "text": "CALCULUS I. Limits, derivatives, integrals.",
         "metadata": {"course_id": "1426", "department": "MATH"}},
    ])
    hits = manager.similarity_search(COURSES, "relational database systems", k=1)
    assert len(hits) == 1
    assert hits[0]["id"] == "course:3330"
    assert hits[0]["metadata"]["course_id"] == "3330"
    assert "distance" in hits[0]


def test_search_k_limit_respected(manager):
    """FC9: `k` caps the number of returned candidates."""
    manager.ingest_documents(COURSES, [
        {"id": f"course:{i}", "text": f"algorithms course number {i}", "metadata": {"course_id": str(i)}}
        for i in range(5)
    ])
    assert len(manager.similarity_search(COURSES, "algorithms course", k=3)) == 3


def test_unknown_query_returns_empty_list_honestly(manager):
    """FC9: an empty/irrelevant store answers with an empty list — the manager
    never fabricates candidates."""
    manager.ingest_documents(CATALOG, [{"id": "catalog:x", "text": "gen core document", "metadata": {}}])
    assert manager.similarity_search(COURSES, "anything", k=5) == []


def test_collections_are_independent(manager):
    """FC33: course descriptions and catalog/requirement text live in separate
    collections — one store, routed collections (results never mix)."""
    manager.ingest_documents(COURSES, [{"id": "course:3330", "text": "database systems", "metadata": {"course_id": "3330"}}])
    manager.ingest_documents(CATALOG, [{"id": "catalog:general", "text": "general core curriculum", "metadata": {"kind": "general_core"}}])
    assert manager.count(COURSES) == 1
    assert manager.count(CATALOG) == 1
    catalog_hits = manager.similarity_search(CATALOG, "database systems")
    assert all(h["id"].startswith("catalog:") for h in catalog_hits)  # never course ids
    course_hits = manager.similarity_search(COURSES, "database systems")
    assert [h["id"] for h in course_hits] == ["course:3330"]  # never catalog ids


def test_reingest_same_ids_upserts_without_duplicates(manager):
    """Seed refresh semantics: reloading the corpus must not duplicate rows."""
    doc = [{"id": "course:3330", "text": "database systems", "metadata": {"course_id": "3330"}}]
    manager.ingest_documents(COURSES, doc)
    manager.ingest_documents(COURSES, [{"id": "course:3330", "text": "database systems v2", "metadata": {"course_id": "3330"}}])
    assert manager.count(COURSES) == 1
    hits = manager.similarity_search(COURSES, "database systems v2", k=1)
    assert hits[0]["text"] == "database systems v2"


def test_reset_clears_collection_for_full_reload(manager):
    """Reload-on-startup: a collection reset leaves zero stale documents."""
    manager.ingest_documents(CATALOG, [{"id": "catalog:general", "text": "old text", "metadata": {}}])
    manager.reset(CATALOG)
    assert manager.count(CATALOG) == 0


def test_embeddings_seam_selects_onnx_or_hash():
    """The embeddings seam is pluggable (domain model §4 embedding_model)."""
    from database.vector.embeddings import get_embedding_function

    assert HashEmbeddings().name() == "hash_embeddings"
    ef = get_embedding_function("hash")
    assert isinstance(ef, EmbeddingFunction)
    with pytest.raises(ValueError):
        get_embedding_function("bogus-mode")


def test_hash_embeddings_deterministic():
    """Same input text ⇒ same vector (offline reproducibility for tests)."""
    ef = HashEmbeddings()
    first = [float(x) for x in ef(["database systems"])[0]]
    second = [float(x) for x in ef(["database systems"])[0]]
    assert first == second
    other = [float(x) for x in ef(["calculus"])[0]]
    assert first != other