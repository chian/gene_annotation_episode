"""Reasoning rejects a citation location outside its artifact and leaves the correction to its caller."""
from copy import deepcopy

from gene_annotation_episode.state import Store
from test_state import empty_payload, source


def test_reasoning_reports_selected_range_outside_the_artifact_without_repairing(tmp_path):
    # Synthetic source text; this exercises citation custody, not biology.
    raw = '{"label":"α","length":370}\n'
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACD", molecule="protein")
        src = source(store, raw)
        anchor = dict(source_ref=src["id"], artifact_ref=src["artifact_ref"],
            start=0, end=len(raw.encode()) + 1)
        payload = empty_payload()
        payload["source_subjects"] = [dict(alias="candidate", label="α",
            reference_type="protein", source_ref=src["id"], anchor=anchor)]
        before = deepcopy(payload)
        scope = {"subject_refs": store.problem()["subject_refs"]}
        rejected = store.commit_reasoning(payload, scope, "mismatched-citation")
        assert rejected["status"] == "invalid"
        assert rejected["record_refs"] == rejected["changed_record_refs"] == []
        assert rejected["aliases"] == {} and store.list("reference") == []
        assert rejected["errors"] == [dict(section="source_subjects", row_index=0,
            code="anchor_transcription_mismatch", source_ref=src["id"],
            artifact_ref=src["artifact_ref"], start=0, end=anchor["end"],
            artifact_byte_count=len(raw.encode()), selected_byte_count=anchor["end"],
            mismatch_kind="range_outside_artifact")]
        assert payload == before
        assert store.commit_reasoning(payload, scope, "mismatched-citation") == rejected
        assert store.get_artifact(src["artifact_ref"]) == raw.encode()
