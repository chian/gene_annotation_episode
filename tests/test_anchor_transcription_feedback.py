"""Reasoning rejects mismatched citations and leaves the correction to its caller."""
from copy import deepcopy

import pytest

from gene_annotation_episode.state import Store
from test_state import empty_payload, source


@pytest.mark.parametrize("mistake,kind", [
    ("missing_newline", "quote_byte_length"),
    ("character_count_as_byte_count", "quote_byte_length"),
    ("same_length_different_text", "quote_bytes"),
    ("outside_artifact", "range_outside_artifact"),
])
def test_reasoning_reports_selected_range_and_quote_bytes_without_repairing(
        tmp_path, mistake, kind):
    # Synthetic source text; this exercises citation custody, not biology.
    raw = '{"label":"α","length":370}\n'
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACD", molecule="protein")
        src = source(store, raw)
        anchor = dict(source_ref=src["id"], artifact_ref=src["artifact_ref"],
            start=0, end=len(raw.encode()), quote=raw)
        if mistake == "missing_newline":
            anchor["quote"] = raw[:-1]
        elif mistake == "character_count_as_byte_count":
            anchor["end"] = len(raw)
        elif mistake == "same_length_different_text":
            anchor["quote"] = raw.replace("α", "β")
        else:
            anchor["end"] += 1
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
            quote_utf8_byte_count=len(anchor["quote"].encode()), mismatch_kind=kind)]
        assert payload == before
        assert store.commit_reasoning(payload, scope, "mismatched-citation") == rejected
        assert store.get_artifact(src["artifact_ref"]) == raw.encode()

        # A separately chosen request supplies an exact citation. The earlier
        # rejection neither amends the request nor publishes a guessed record.
        corrected = deepcopy(payload)
        corrected["source_subjects"][0]["anchor"].update(end=len(raw.encode()), quote=raw)
        accepted = store.commit_reasoning(corrected, scope, "caller-corrected-citation")
        assert accepted["status"] == "completed" and accepted["errors"] == []
        assert len(accepted["record_refs"]) == 1
        record = store.get(accepted["aliases"]["candidate"])
        assert record["anchor"] == corrected["source_subjects"][0]["anchor"]
        assert record["sequence_ref"] is None
        assert not store.list("observation") and not store.list("assessment")
