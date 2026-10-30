"""Rfam documentation bytes and explicitly synthetic contract counterexamples."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS, rfam_digest
from gene_annotation_episode.rfam_batch_inputs import populate_rfam_batch_json_sheet


EXAMPLES = Path(__file__).resolve().parents[1] / "verification/tool_graders_rfam_contract_2026-10-26_232/examples"
LIVE = EXAMPLES.parents[1] / "tool_graders_rfam_transport_2026-10-26_234/live"


def identity():
    return json.loads((EXAMPLES / "single-input-identity.json").read_text())


def native_example():
    return json.loads((EXAMPLES / "official-single-result.json").read_bytes())


def capture(content, **changes):
    return {"artifact_ref": "fixture:artifact:result", "source_ref": "fixture:source:result",
        "source_sha256": hashlib.sha256(content).hexdigest(), "representation": "json", "http_status": None,
        "evidence_kind": "synthetic_fixture",
        "body_complete": True, "request_job_id": identity()["expected_job_id"],
        "request_sequence_sha256": identity()["submitted_sequence_sha256"], **changes}


def parse(native=None, *, fixture="official-single-result.json", input_changes=None, capture_changes=None,
          model_metadata=None, alignment_components=None):
    content = (json.dumps(native).encode() if native is not None else (EXAMPLES / fixture).read_bytes())
    original = {**identity(), **(input_changes or {})}
    kind = "official_documentation_example" if native is None and fixture == "official-single-result.json" else "synthetic_fixture"
    return populate_rfam_batch_json_sheet(content, input_identity=original,
        capture=capture(content, **{"evidence_kind": kind, **(capture_changes or {})}), model_metadata=model_metadata, alignment_components=alignment_components)


def codes(result):
    return {r["code"] for r in result["issues"]}


def model_metadata(*lengths):
    return {"version": "rfam_model_metadata_v1", "records": [
        {"metadata_ref": "fixture:model:" + str(i), "accession": "RF00001", "model_name": "5S_rRNA",
         "model_length_positions": length, "model_sha256": "a" * 64, "model_release": "14.0",
         "source_ref": "fixture:model-source:" + str(i)} for i, length in enumerate(lengths)], "bindings": []}


def test_official_documentation_bytes_native_values_not_recomputed():
    result = parse()
    assert result["status"] == "complete"
    assert result["format"] == "rfam_cmscan_single_json_v1"
    sheet = result["sheet"]
    assert sheet["population"]["reported_set_complete"] is True
    assert sheet["population"]["observed_row_count"] == 1
    assert set(sheet["format_metadata"].values()) == {None}
    row = sheet["hits"][0]
    assert row["native"] == {"start": 1, "end": 119, "strand": "+", "score_bits": 104.9, "evalue": 4.5e-24, "gc_fraction": 0.49}
    assert row["query_interval"] == [0, 119]
    assert row["native"]["gc_fraction"] != 58 / 119
    assert row["model_length_positions"] is None
    assert row["alignment_components"] is None
    assert row["missing"]["represented_model_positions"] == "alignment_not_parsed"


@pytest.mark.parametrize("fixture,code", [
    ("synthetic-conflicting-job.json", "rfam_result_job_identity_conflict"),
    ("synthetic-conflicting-sequence.json", "rfam_result_sequence_identity_conflict")])
def test_original_identity_conflict_rejects_all_scientific_attribution(fixture, code):
    result = parse(fixture=fixture)
    assert result["status"] == "rejected" and result["sheet"] is None
    assert code in codes(result)


@pytest.mark.parametrize("value,code", [(None, "rfam_result_sequence_identity_not_string"),
    ("", "rfam_result_sequence_identity_empty"), ("é", "rfam_result_sequence_identity_not_ascii"),
    ("AGU", "rfam_result_sequence_identity_conflict"), (123, "rfam_result_sequence_identity_not_string")])
def test_sequence_identity_specific_rejections(value, code):
    native = native_example()
    native["searchSequence"] = value
    result = parse(native)
    assert result["sheet"] is None and code in codes(result)


def test_no_silent_sequence_case_whitespace_or_tu_normalization():
    for transform in (str.lower, lambda s: s + "\n", lambda s: s.replace("T", "U")):
        native = native_example()
        native["searchSequence"] = transform(native["searchSequence"])
        assert "rfam_result_sequence_identity_conflict" in codes(parse(native))


def test_expired_real_retained_job_is_not_zero_search():
    content = (EXAMPLES.parent / "source_evidence/official-old-job.result.json").read_bytes()
    result = populate_rfam_batch_json_sheet(content, input_identity=identity(), capture=capture(content, evidence_kind="native_response", http_status=200))
    assert result["sheet"] is None and result["status"] == "rejected"
    assert "rfam_result_sequence_identity_empty" in codes(result)


def test_zero_and_multiple_untyped_are_distinct():
    empty = parse(fixture="synthetic-empty.json")
    assert empty["status"] == "complete" and empty["sheet"]["hits"] == []
    multiple = parse(fixture="synthetic-untyped-multiple-envelope.json")
    assert multiple["status"] == "unsupported" and multiple["sheet"] is None
    assert multiple["format"] == "rfam_multiple_sequences_json_untyped"


@pytest.mark.parametrize("content,code", [
    (b'{"a":1,"a":2}', "rfam_json_duplicate_key"),
    (b'{"a":NaN}', "rfam_json_invalid"), (b'{"a":1e999}', "rfam_json_invalid"),
    (b'{"a":Infinity}', "rfam_json_invalid"), (b'{', "rfam_json_invalid"),
    (b'\xff', "rfam_json_invalid"), (b'[]', "rfam_result_object_required")])
def test_invalid_native_document(content, code):
    result = populate_rfam_batch_json_sheet(content, input_identity=identity(), capture=capture(content))
    assert result["sheet"] is None and code in codes(result)


@pytest.mark.parametrize("changes,code", [
    ({"source_sha256": "0" * 64}, "rfam_source_identity_conflict"),
    ({"request_job_id": "infernal_cmscan-OTHER"}, "rfam_result_job_identity_conflict"),
    ({"request_sequence_sha256": "0" * 64}, "rfam_result_sequence_identity_conflict"),
    ({"http_status": 500}, "rfam_http_error")])
def test_capture_relationships(changes, code):
    result = parse(capture_changes=changes)
    assert result["sheet"] is None and code in codes(result)


def test_missing_and_invalid_optional_cells_do_not_erase_other_cells():
    native = native_example()
    row = native["hits"]["5S_rRNA"][0]
    del row["score"]
    row.update(E=-1, GC=1.5, start=True, alignment=None)
    result = parse(native)
    row = result["sheet"]["hits"][0]
    assert result["status"] == "partial"
    assert row["native"]["score_bits"] is None
    assert row["missing"]["native_score_bits"] == "not_reported"
    assert row["native"]["end"] == 119 and row["native"]["start"] is None
    assert row["query_interval"] is None
    assert row["missing"]["represented_model_positions"] == "alignment_missing"


def test_valid_zero_native_cells_and_negative_score_stay_measured():
    native = native_example()
    native["hits"]["5S_rRNA"][0].update(score=-3.25, E=0, GC=0)
    values = parse(native)["sheet"]["hits"][0]["native"]
    assert (values["score_bits"], values["evalue"], values["gc_fraction"]) == (-3.25, 0, 0)


def test_count_contradiction_and_incomplete_body_preserve_native_cells():
    for result in (parse(fixture="synthetic-conflicting-count.json"), parse(capture_changes={"body_complete": False})):
        assert result["status"] == "partial"
        assert result["sheet"]["hits"][0]["native"]["score_bits"] == 104.9
        assert result["sheet"]["population"]["reported_set_complete"] is False


def test_all_native_entries_and_json_pointer_escaping_survive():
    native = native_example()
    row = native["hits"]["5S_rRNA"][0]
    row["id"] = "a/b~c"
    native["hits"] = {"a/b~c": [row, deepcopy(row), None], "bad": {"not": "a list"}}
    native["numHits"] = 3
    result = parse(native)
    rows = result["sheet"]["hits"]
    assert len(rows) == 3 and rows[0]["native_json_pointer"] == "/hits/a~1b~0c/0"
    assert rows[1]["duplicate_of"] == rows[0]["hit_key"]
    assert rows[2]["identity_valid"] is False
    assert result["sheet"]["population"]["reported_set_complete"] is False


def test_unbound_and_conflicting_model_metadata_preserves_native_query_numbers():
    for lengths, reason in [((119,), "model_binding_unverified"), ((119, 120), "model_metadata_conflict")]:
        bundle = model_metadata(*lengths)
        bundle["bindings"] = [{"hit_key": "fixture:artifact:result/hits/5S_rRNA/0", "metadata_ref": "fixture:model:0",
            "basis": "native_model_sha256", "evidence_source_ref": "fixture:source:result", "evidence_json_pointer": "/hits/5S_rRNA/0/acc"}]
        result = parse(model_metadata=bundle)
        sheet = result["sheet"]
        assert sheet["model_metadata"] == bundle
        row = sheet["hits"][0]
        assert row["model_length_positions"] is None and row["model_metadata_ref"] is None
        assert row["missing"]["model_coverage_fraction"] == reason
        assert row["query_interval"] == [0, 119]


def test_wrong_source_alignment_bundle_disables_only_alignment():
    content = (EXAMPLES / "official-single-result.json").read_bytes()
    result = parse(alignment_components={"version": "rfam_alignment_components_bundle_v1",
        "artifact_ref": capture(content)["artifact_ref"], "source_sha256": "a" * 64, "rows": []})
    assert "rfam_alignment_binding_conflict" in codes(result)
    assert result["sheet"]["hits"][0]["query_interval"] == [0, 119]
    assert result["sheet"]["hits"][0]["missing"]["represented_model_positions"] == "alignment_conflict"


def test_inputs_unchanged_and_sheet_is_detached():
    native = native_example()
    original = deepcopy(native)
    result = parse(native)
    assert native == original
    result["sheet"]["input"]["submitted_sequence"] = "changed"
    assert native == original


def test_original_input_hash_or_length_cannot_be_supplied_as_verified_boolean():
    for changes in ({"submitted_length_nt": 120}, {"submitted_sequence_sha256": "0" * 64}, {"identity_verified": True}):
        assert parse(input_changes=changes)["sheet"] is None


def live_single_operands():
    directory = LIVE / "single"
    content = (directory / "003-fetch-json/response.body").read_bytes()
    original = json.loads((directory / "input-manifest.json").read_text())["records"][0]
    handle = json.loads((directory / "original_handle.json").read_text())
    snapshot = json.loads((directory / "003-fetch-json/snapshot.json").read_text())
    assert hashlib.sha256(content).hexdigest() == snapshot["content_sha256"]
    operand = {**identity(), **{k: original[k] for k in ("query_occurrence_key", "original_record_ordinal",
        "original_header", "submitted_sequence", "submitted_sequence_sha256", "submitted_length_nt")},
        "expected_job_id": handle["job_id"], "submission_source_ref": "retained-native:single:001-submit",
        "subject_ref": "fixture:public119", "original_input_ref": "retained-native:single:input.seq"}
    acquired = capture(content, evidence_kind="native_response", http_status=snapshot["transport"]["status"],
        body_complete=snapshot["transport"]["body_complete"], request_job_id=handle["job_id"],
        request_sequence_sha256=original["submitted_sequence_sha256"], source_ref="retained-native:single:003-fetch-json",
        artifact_ref="retained-native:single:003-fetch-json:response.body")
    return content, operand, acquired


def test_fresh_live_single_is_distinct_from_official_documentation_example():
    content, operand, acquired = live_single_operands()
    result = populate_rfam_batch_json_sheet(content, input_identity=operand, capture=acquired)
    assert result["status"] == "complete"
    row = result["sheet"]["hits"][0]
    assert row["native"]["score_bits"] == 104.6 and row["native"]["evalue"] == 1.4e-24
    assert row["native"]["gc_fraction"] == .49 and row["query_interval"] == [0, 119]
    assert row["model_length_positions"] is None
    assert result["sheet"]["source"]["evidence_kind"] == "native_response"


def test_live_flat_multi_json_cannot_be_assigned_by_hit_order():
    directory = LIVE / "multi"
    content = (directory / "003-fetch-json/response.body").read_bytes()
    native = json.loads(content)
    assert len(native["hits"]) == 6 and all("searchSequence" not in r for r in native["hits"])
    handle = json.loads((directory / "original_handle.json").read_text())
    result = populate_rfam_batch_json_sheet(content,
        input_identity={**identity(), "expected_job_id": handle["job_id"]},
        capture=capture(content, evidence_kind="native_response", http_status=200, request_job_id=handle["job_id"]))
    assert result["status"] == "unsupported" and result["sheet"] is None
    assert "rfam_multiple_sequences_schema_unestablished" in codes(result)


def test_native_underflow_is_unavailable_instead_of_measured_zero():
    content = (EXAMPLES / "official-single-result.json").read_bytes().replace(b"4.5e-24", b"1e-999")
    result = populate_rfam_batch_json_sheet(content, input_identity=identity(), capture=capture(content))
    assert result["sheet"]["hits"][0]["native"]["evalue"] is None
    assert result["sheet"]["hits"][0]["missing"]["native_evalue"] == "invalid_native_value"
    assert result["sheet"]["hits"][0]["native"]["score_bits"] == 104.9


def test_native_response_requires_actual_status_and_fixture_kinds_are_retained():
    assert parse(capture_changes={"evidence_kind": "native_response", "http_status": None})["sheet"] is None
    assert parse()["sheet"]["source"]["evidence_kind"] == "official_documentation_example"
    assert parse(fixture="synthetic-empty.json")["sheet"]["source"]["evidence_kind"] == "synthetic_fixture"


def test_different_unbound_model_versions_do_not_create_a_false_length_conflict():
    metadata = model_metadata(119, 120)
    metadata["records"][1].update(model_sha256="b" * 64, model_release="15.0")
    row = parse(model_metadata=metadata)["sheet"]["hits"][0]
    assert row["model_length_positions"] is None
    assert row["missing"]["model_length_positions"] == "model_binding_unverified"
