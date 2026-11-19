"""Real metadata/receipt controls over a fresh Store."""
import pytest

from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
from gene_annotation_episode.state import Store


def test_fresh_store_without_tool_operations_has_no_publication_restriction(tmp_path, monkeypatch):
    store = Store(tmp_path / "fresh")
    try:
        reference = store.artifact(b"ordinary initial material", "text/plain")
        before = store.db.total_changes
        def forbidden(*args, **kwargs):
            pytest.fail("privacy classification must not read artifact bytes")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        assert molecular_reference_restriction(store, None, reference, "artifact", private_only=True) is None
        assert store.db.total_changes == before
        assert store.db.execute("SELECT 1 FROM sqlite_master WHERE name='tool_operations'").fetchone() is None
    finally:
        store.close()

