"""A preparation source delivers selected references, not its retained archive."""
import pytest

from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store


@pytest.mark.parametrize("kind", ["initial", "decision_input", "own_action", "child_form", "report_redelivery"])
def test_hmmer_bundle_receipt_does_not_disclose_unrequested_artifacts(tmp_path, monkeypatch, kind):
    with Store(tmp_path / "store") as store:
        bundle = store.artifact(b"synthetic original bundle")
        selected = store.artifact(b"synthetic requested output")
        unrequested = store.artifact(b"synthetic unrequested output")
        source = store.put("source", {"provider": "episode.execution_result", "accession": "fixture",
            "uri": None, "artifact_ref": bundle, "text_ref": bundle, "request_ref": None,
            "version": "native_hmmer_preparation_bundle_v1", "retrieved_at": None,
            "auxiliary_artifact_refs": [selected, unrequested]}, origin="tool")["id"]
        receipts = EpisodeReceipts(store, "synthetic-receipt-verification")
        receipts.bind("receiver")
        monkeypatch.setattr(store, "get_artifact", lambda *a: pytest.fail("receipt expanded retained bytes"))
        receipts.receive("receiver", [source], kind=kind, source_index=0)
        assert set(receipts.known("receiver")) == {source}
        receipts.receive("receiver", [source, selected], kind=kind, source_index=1)
        assert set(receipts.known("receiver")) == {source, selected}
        before = list(store.db.execute("SELECT * FROM runtime_record_receipts ORDER BY receipt_index"))
        receipts.receive("receiver", [selected, source], kind=kind, source_index=2)
        assert list(store.db.execute("SELECT * FROM runtime_record_receipts ORDER BY receipt_index")) == before
        assert bundle not in receipts.known("receiver") and unrequested not in receipts.known("receiver")
