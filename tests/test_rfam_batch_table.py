"""Native retained Rfam table reuse, plus explicitly synthetic counterexamples."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores
from gene_annotation_episode.infernal_search_inputs import populate_infernal_search_sheet
from gene_annotation_episode.rfam_batch_table import (
    RFAM_BATCH_TABLE_ISSUE_CODES, RfamBatchTableIssue, RfamBatchTableParseResult,
    parse_rfam_report_membership, populate_rfam_batch_tblout_sheet,
    validate_rfam_batch_file_input,
)


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/multi"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def native_case():
    """No new native run: adapt the separately retained original input manifest."""
    submitted = (NATIVE / "input.seq").read_bytes()
    manifest = json.loads((NATIVE / "input-manifest.json").read_text())
    capture_record = json.loads((NATIVE / "004-fetch-tblout/snapshot.json").read_text())
    content = (NATIVE / "004-fetch-tblout/response.body").read_bytes()
    submission_ref = str(NATIVE.relative_to(ROOT) / "001-submit/snapshot.json")
    identity = {"version": "rfam_batch_file_input_v1", "expected_job_id": capture_record["request"]["job_id"],
        "submission_source_ref": submission_ref, "submitted_file_sha256": manifest["file_sha256"],
        "submitted_file_bytes": manifest["file_bytes"], "filename": manifest["filename"],
        "header_transform": "unchanged_unique_headers", "queries": []}
    for ordinal, row in enumerate(manifest["records"]):
        identity["queries"].append({key: row[key] for key in (
            "query_occurrence_key", "original_record_ordinal", "original_header", "submitted_sequence",
            "submitted_sequence_sha256", "submitted_length_nt")})
        # The original input ref names this exact already transformed FASTA
        # member. Its earlier public-example derivation remains in the old
        # immutable manifest; there is no new sequence-coordinate transform.
        identity["queries"][-1].update(subject_ref="retained-selected-subject:" + str(ordinal),
            original_input_ref=str(NATIVE.relative_to(ROOT) / "input.seq"),
            selected_occurrence_ordinal=ordinal, native_query_name=row["original_header"].split()[0],
            input_to_submitted_transform="unchanged", input_coordinate_mapping_ref=None)
    capture = {"artifact_ref": str(NATIVE.relative_to(ROOT) / "004-fetch-tblout/response.body"),
        "source_ref": str(NATIVE.relative_to(ROOT) / "004-fetch-tblout/snapshot.json"),
        "source_sha256": capture_record["content_sha256"], "evidence_kind": "native_response",
        "representation": "tblout", "http_status": capture_record["transport"]["status"],
        "body_complete": capture_record["transport"]["body_complete"], "request_job_id": identity["expected_job_id"],
        "request_file_sha256": identity["submitted_file_sha256"], "submission_source_ref": submission_ref}
    return content, submitted, identity, capture


def report_case():
    _, _, _, capture = native_case()
    content = (NATIVE / "005-fetch-out/response.body").read_bytes()
    record = json.loads((NATIVE / "005-fetch-out/snapshot.json").read_text())
    capture.update(artifact_ref=str(NATIVE.relative_to(ROOT) / "005-fetch-out/response.body"),
        source_ref=str(NATIVE.relative_to(ROOT) / "005-fetch-out/snapshot.json"),
        source_sha256=record["content_sha256"], representation="out")
    return content, capture


def parse(case, **kwargs):
    content, submitted, identity, capture = case
    return populate_rfam_batch_tblout_sheet(content, input_identity=identity, capture=capture,
        submitted_content=submitted, **kwargs)


def synthetic_table(case, content):
    _, submitted, identity, capture = deepcopy(case)
    capture.update(source_sha256=digest(content), evidence_kind="synthetic_fixture")
    return content, submitted, identity, capture


def synthetic_input(case, identity, submitted):
    content, _, _, capture = deepcopy(case)
    identity.update(submitted_file_sha256=digest(submitted), submitted_file_bytes=len(submitted))
    capture.update(request_file_sha256=digest(submitted), evidence_kind="synthetic_fixture")
    return content, submitted, identity, capture


def native_rows(content):
    return [line for line in content.splitlines() if line.strip() and not line.startswith(b"#")]


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def test_retained_six_query_native_table_reuses_exact_infernal_sheet():
    case = native_case()
    content, submitted, identity, capture = case
    assert digest(content) == "46b3e1c6554f1f20d7869e447298beb782ad2cf6735196bd11a39be80e5fad25"
    assert digest(submitted) == "4dc1529db76f089ec36caf8f3d176028d3bb5c828a1d04bfd130e72f92f515f4"
    assert validate_rfam_batch_file_input(identity, submitted_content=submitted) is None
    before = deepcopy(case)
    result = parse(case)
    assert case == before
    assert set(result) == {"version", "representation", "status", "format", "sheet", "issues"}
    assert result["version"] == "rfam_batch_parse_result_v2"
    assert result["status"] == "partial"  # Original model length is absent.
    assert result["issues"] == []
    assert result["sheet"]["source_context"]["supplied_model_metadata"] is None
    expected = populate_infernal_search_sheet(
        [{"artifact_id": capture["artifact_ref"], "format": "infernal_tblout", "table_format": 1,
          "complete": True, "content": content.decode("ascii")}],
        operation={"program": "cmscan", "native_version": "1.1.5", "settings": {}},
        sequence_metadata=[{"name": q["native_query_name"], "length": q["submitted_length_nt"],
            "sequence": q["submitted_sequence"], "artifact_id": capture["artifact_ref"]} for q in identity["queries"]],
        model_metadata=None)
    # Source-format normalization adds occurrence declarations, while all
    # shared native hit measurements remain the same.
    actual_scores = calculate_infernal_search_scores(result["sheet"])
    expected_scores = calculate_infernal_search_scores(expected)
    assert [h["components"] for h in actual_scores["hits"]] == [h["components"] for h in expected_scores["hits"]]
    assert [h["hit_id"] for h in result["sheet"]["hits"]] == [h["hit_id"] for h in expected["hits"]]
    assert result["sheet"]["artifacts"][0]["content"].encode("ascii") == content
    assert all("occurrence" not in row for row in result["sheet"]["sequence_metadata"])
    assert [row["sequence_metadata_index"] for row in result["sheet"]["source_context"]["occurrence_bindings"]] == list(range(6))
    assert [row["reported_row_count"] for row in result["sheet"]["source_context"]["query_population"]] == [1] * 6
    assert all(row["reported_set_complete"] for row in result["sheet"]["source_context"]["query_population"])


def test_native_numerical_example_and_strand_separation():
    result = parse(native_case())
    scores = calculate_infernal_search_scores(result["sheet"], parameters={"hit_scope": "reported"})
    assert [h["components"]["bitscore"] for h in scores["hits"]] == [104.6, 104.6, 104.6, 51.3, 95.5, 95.2]
    assert [h["components"]["evalue"] for h in scores["hits"]] == [1.4e-24, 1.4e-24, 1.4e-24, 9.5e-11, 3.5e-22, 4e-22]
    assert [h["components"]["gc_fraction"] for h in scores["hits"]] == [.49, .49, .49, .50, .48, .48]
    assert [h["components"]["sequence_span_length"] for h in scores["hits"]] == [119, 119, 119, 70, 120, 118]
    assert [h["components"]["model_span_length"] for h in scores["hits"]] == [120, 120, 120, 71, 120, 120]
    assert all(h["components"]["sequence_span_fraction"] == 1.0 for h in scores["hits"])
    assert all(h["components"]["model_span_fraction"] is None for h in scores["hits"])
    assert all(h["components"]["bias_bits"] == 0.0 for h in scores["hits"])
    assert result["sheet"]["hits"][3]["truncation"] == "3'"
    assert result["sheet"]["hits"][3]["pass"] == 3
    aggregates = scores["sequence_strand_aggregates"]
    assert len(aggregates) == 12
    aggregates = [r for r in aggregates if r["hit_count"]]
    assert aggregates[0]["sequence_identity"] != aggregates[1]["sequence_identity"]
    assert aggregates[2]["strand"] == "-"
    assert aggregates[2]["union_intervals"] == [[0, 119]]
    assert all(row["union_span_fraction"] == 1.0 for row in aggregates)
    assert scores["search_space"]["inferred_database_size"] is None


def test_reordered_rows_bind_native_names_not_table_ordinals():
    case = native_case()
    lines = case[0].splitlines()
    rows = iter(reversed(native_rows(case[0])))
    content = b"\n".join(next(rows) if line.strip() and not line.startswith(b"#") else line for line in lines) + b"\n"
    result = parse(synthetic_table(case, content))
    assert [hit["sequence"]["metadata_join"]["metadata_index"] for hit in result["sheet"]["hits"]] == [5, 4, 3, 2, 1, 0]
    assert [row["selected_occurrence_ordinal"] for row in result["sheet"]["source_context"]["occurrence_bindings"]] == list(range(6))
    assert [row["reported_row_count"] for row in result["sheet"]["source_context"]["query_population"]] == [1] * 6


def test_repeated_subject_and_sequence_original_ordinals_do_not_merge():
    content, submitted, identity, capture = native_case()
    identity["queries"][1]["subject_ref"] = identity["queries"][0]["subject_ref"]
    identity["queries"][1]["original_record_ordinal"] = identity["queries"][0]["original_record_ordinal"]
    identity["queries"][0]["original_record_ordinal"] = 70
    identity["queries"][1]["original_record_ordinal"] = 70
    result = parse((content, submitted, identity, capture))
    assert len(result["sheet"]["source_context"]["occurrence_bindings"]) == 6
    assert [h["sequence"]["metadata_join"]["metadata_index"] for h in result["sheet"]["hits"][:2]] == [0, 1]
    assert result["sheet"]["source_context"]["input_identity"]["queries"][1]["original_record_ordinal"] == 70


def test_generated_headers_allow_null_original_headers_and_declared_mapping():
    content, submitted, identity, capture = native_case()
    identity["header_transform"] = "generated_unique_headers"
    identity["queries"][0].update(original_header=None, original_record_ordinal=None,
        input_to_submitted_transform="registered_view", input_coordinate_mapping_ref="retained:mapping-0")
    assert validate_rfam_batch_file_input(identity, submitted_content=submitted) is None
    result = parse((content, submitted, identity, capture))
    assert result["sheet"]["source_context"]["input_identity"]["queries"][0]["original_header"] is None


@pytest.mark.parametrize("mutation, expected", [
    (lambda i: i.update(extra="x"), "rfam_batch_input_invalid"),
    (lambda i: i.update(submitted_file_sha256="0" * 64), "rfam_batch_submitted_file_conflict"),
    (lambda i: i.update(submitted_file_bytes=i["submitted_file_bytes"] + 1), "rfam_batch_submitted_file_conflict"),
    (lambda i: i["queries"].pop(), "rfam_batch_fasta_membership_conflict"),
    (lambda i: i["queries"][0].update(submitted_length_nt=120), "rfam_batch_sequence_conflict"),
    (lambda i: i["queries"][0].update(submitted_sequence_sha256="0" * 64), "rfam_batch_sequence_conflict"),
    (lambda i: i["queries"][0].update(submitted_sequence="A" * 119), "rfam_batch_sequence_conflict"),
    (lambda i: i["queries"][0].update(native_query_name="other"), "rfam_batch_fasta_membership_conflict"),
    (lambda i: i["queries"][1].update(query_occurrence_key=i["queries"][0]["query_occurrence_key"]), "rfam_batch_occurrence_key_ambiguous"),
    (lambda i: i["queries"][1].update(selected_occurrence_ordinal=0), "rfam_batch_input_invalid"),
    (lambda i: i["queries"][0].update(original_input_ref=""), "rfam_batch_input_invalid"),
    (lambda i: i["queries"][0].update(original_record_ordinal=True), "rfam_batch_input_invalid"),
    (lambda i: i["queries"][0].update(input_to_submitted_transform="registered_view"), "rfam_batch_input_invalid"),
    (lambda i: i["queries"][0].update(input_to_submitted_transform="reverse_complement"), "rfam_batch_input_invalid"),
    (lambda i: i["queries"][0].update(original_header="wrong original header"), "rfam_batch_header_transform_conflict"),
])
def test_manifest_validation_failures_have_stable_codes(mutation, expected):
    case = native_case()
    mutation(case[2])
    with pytest.raises(ValueError, match="^" + expected + "$"):
        validate_rfam_batch_file_input(case[2], submitted_content=case[1])
    result = parse(case)
    assert result["status"] == "rejected"
    assert result["sheet"] is None
    assert codes(result) == {expected}


def test_duplicate_native_first_token_rejected_even_with_distinct_descriptions():
    case = native_case()
    submitted = case[1].replace(b">rfam_example_repeat", b">rfam_example_original second description")
    changed = synthetic_input(case, case[2], submitted)
    changed[2]["queries"][1].update(native_query_name="rfam_example_original", original_header="rfam_example_original second description")
    result = parse(changed)
    assert result["status"] == "rejected"
    assert codes(result) == {"rfam_batch_native_name_ambiguous"}


@pytest.mark.parametrize("submitted", [b"ACGT\n", b">q\n", b">q\nA CGT\n", b">q\nACGX\n", b">q\nACGT\x00\n", b">q\nACGT\r", b">q\nACGT\xff"])
def test_ambiguous_or_malformed_fasta_is_never_repaired(submitted):
    case = native_case()
    result = parse(synthetic_input(case, case[2], submitted))
    assert result["status"] == "rejected"
    assert codes(result) <= {"rfam_batch_fasta_invalid", "rfam_batch_submitted_content_invalid"}


def test_exact_lowercase_wrapped_sequence_is_preserved():
    case = native_case()
    identity = case[2]
    seq = identity["queries"][0]["submitted_sequence"].lower()
    identity["queries"][0].update(submitted_sequence=seq, submitted_sequence_sha256=digest(seq.encode("ascii")))
    old = case[1].splitlines()[1]
    submitted = case[1].replace(old + b"\n", seq[:40].encode() + b"\r\n" + seq[40:].encode() + b"\n", 1)
    result = parse(synthetic_input(case, identity, submitted))
    assert result["sheet"]["sequence_metadata"][0]["sequence"] == seq


def test_complete_input_no_hit_occurrence_and_complete_zero_table():
    case = native_case()
    row = deepcopy(case[2]["queries"][0])
    row.update(query_occurrence_key="synthetic-no-hit", subject_ref="synthetic-no-hit-subject",
        original_record_ordinal=6, selected_occurrence_ordinal=6, native_query_name="synthetic_no_hit",
        original_header="synthetic_no_hit", submitted_sequence="NNNN", submitted_length_nt=4,
        submitted_sequence_sha256=digest(b"NNNN"))
    case[2]["queries"].append(row)
    case = synthetic_input(case, case[2], case[1] + b">synthetic_no_hit\nNNNN\n")
    result = parse(case)
    assert result["sheet"]["source_context"]["query_population"][-1] == {"query_occurrence_key": "synthetic-no-hit", "submitted_length_nt": 4,
        "membership_basis": "frozen_complete_input", "reported_row_count": 0, "reported_set_complete": True}
    content = b"\n".join(line for line in case[0].splitlines() if line.startswith(b"#")) + b"\n"
    zero = parse(synthetic_table(case, content))
    assert zero["status"] == "complete"
    assert zero["sheet"]["hits"] == []
    assert len(zero["sheet"]["source_context"]["occurrence_bindings"]) == 7
    assert [q["reported_row_count"] for q in zero["sheet"]["source_context"]["query_population"]] == [0] * 7
    assert all(q["reported_set_complete"] for q in zero["sheet"]["source_context"]["query_population"])
    assert len(calculate_infernal_search_scores(zero["sheet"], parameters={"hit_scope": "reported"})["sequence_strand_aggregates"]) == 14
    assert all(r["hit_count"] == 0 and r["union_span_fraction"] == 0 for r in calculate_infernal_search_scores(zero["sheet"])["sequence_strand_aggregates"])


@pytest.mark.parametrize("kind", ["body", "footer", "whole_footer", "after_marker", "duplicate_marker", "partial_row"])
def test_incomplete_table_retains_cells_without_completed_zero(kind):
    case = native_case()
    first, last = native_rows(case[0])[0], native_rows(case[0])[-1]
    content = case[0].replace(last + b"\n", b"")
    if kind == "footer":
        content = content.replace(b"# [ok]\n", b"")
    elif kind == "whole_footer":
        content = content[:content.index(b"#\n# Program:")]
    elif kind == "after_marker":
        content += first + b"\n"
    elif kind == "duplicate_marker":
        content += b"# [ok]\n"
    elif kind == "partial_row":
        content = content.replace(first, b"5S_rRNA RF00001")
    case = synthetic_table(case, content)
    if kind == "body":
        case[3]["body_complete"] = False
    result = parse(case)
    assert result["status"] == "partial"
    assert result["sheet"]["hits"]
    assert result["sheet"]["source_context"]["query_population"][-1]["reported_row_count"] is None
    assert not any(q["reported_set_complete"] for q in result["sheet"]["source_context"]["query_population"])
    assert all(hit["components"]["model_span_fraction"] is None
        for hit in calculate_infernal_search_scores(result["sheet"], parameters={"hit_scope": "reported"})["hits"])


def test_partial_numeric_cell_preserves_other_native_measurements():
    case = native_case()
    first = native_rows(case[0])[0]
    content = case[0].replace(first, first.replace(b"104.6", b"bad-score"))
    result = parse(synthetic_table(case, content))
    components = calculate_infernal_search_scores(result["sheet"])["hits"][0]["components"]
    assert components["bitscore"] is None
    assert components["evalue"] == 1.4e-24
    assert components["sequence_span_fraction"] == 1.0
    assert all(q["reported_set_complete"] for q in result["sheet"]["source_context"]["query_population"])


def test_foreign_native_query_retains_unbound_row_and_qualifies_population():
    case = native_case()
    content = case[0].replace(b"rfam_example_deletion", b"foreign_query")
    result = parse(synthetic_table(case, content))
    assert "rfam_batch_foreign_native_query" in codes(result)
    assert result["status"] == "partial"
    assert len(result["sheet"]["hits"]) == 6
    assert result["sheet"]["hits"][-1]["sequence"]["identity"] is None
    assert result["sheet"]["source_context"]["query_population"][-1]["reported_row_count"] is None
    assert not any(q["reported_set_complete"] for q in result["sheet"]["source_context"]["query_population"])


@pytest.mark.parametrize("field,value,expected", [
    ("request_job_id", "infernal_cmscan-other", "rfam_batch_result_job_conflict"),
    ("request_file_sha256", "0" * 64, "rfam_batch_result_file_conflict"),
    ("submission_source_ref", "other:submission", "rfam_batch_submission_source_conflict"),
    ("source_sha256", "0" * 64, "rfam_batch_source_identity_conflict"),
    ("http_status", 404, "rfam_batch_http_error"),
    ("http_status", None, "rfam_batch_http_error"),
])
def test_original_capture_conflicts_reject_attribution(field, value, expected):
    case = native_case()
    case[3][field] = value
    result = parse(case)
    assert result["status"] == "rejected"
    assert result["sheet"] is None
    assert codes(result) == {expected}


@pytest.mark.parametrize("before,after,expected,status", [
    (b"# Version:         1.1.5", b"# Version:         1.1.4", "rfam_batch_native_version_unsupported", "unsupported"),
    (b"# Program:         cmscan", b"# Program:         cmsearch", "rfam_batch_native_program_unsupported", "unsupported"),
    (b"# Pipeline mode:   SCAN", b"# Pipeline mode:   SEARCH", "rfam_batch_native_mode_unsupported", "unsupported"),
    (b"inc description of target", b"inc mdl len seq len description of target", "rfam_batch_table_format_unsupported", "unsupported"),
    (b"# Query file:      infernal_cmscan-R20261026-031924-0036-5332137-p1m.sequence", b"# Query file:      infernal_cmscan-other.sequence", "rfam_batch_native_query_file_conflict", "rejected"),
])
def test_native_profile_and_original_filename_are_checked(before, after, expected, status):
    case = native_case()
    result = parse(synthetic_table(case, case[0].replace(before, after)))
    assert result["status"] == status
    assert expected in codes(result)
    assert result["sheet"] is None
    assert result["sheet"] is None


def test_table_inconsistent_coordinate_boundary_keeps_score_but_no_fraction():
    case = native_case()
    first = native_rows(case[0])[0]
    content = case[0].replace(first, first.replace(b"     119", b"     120"))
    result = parse(synthetic_table(case, content))
    calc = calculate_infernal_search_scores(result["sheet"])
    assert calc["hits"][0]["components"]["bitscore"] == 104.6
    assert calc["hits"][0]["components"]["sequence_span_fraction"] is None
    assert "coordinates_exceed_validated_length" in {issue["code"] for issue in result["sheet"]["issues"]}


def test_duplicate_overlapping_rows_are_not_independent_or_double_union():
    case = native_case()
    first = native_rows(case[0])[0]
    content = case[0].replace(first + b"\n", first + b"\n" + first + b"\n")
    result = parse(synthetic_table(case, content))
    calc = calculate_infernal_search_scores(result["sheet"], parameters={"hit_scope": "reported"})
    first_aggregate = calc["sequence_strand_aggregates"][0]
    assert result["sheet"]["source_context"]["query_population"][0]["reported_row_count"] == 2
    assert first_aggregate["hit_count"] == 2
    assert first_aggregate["union_numerator"] == 119
    assert len(first_aggregate["duplicate_representation_memberships"][0]) == 2
    assert first_aggregate["overlap_memberships"][0]["overlap_length"] == 119


def test_model_metadata_is_saved_but_never_joined_by_family_accession():
    metadata = {"version": "rfam_model_metadata_v1", "records": [{"accession": "RF00001", "model_length_positions": 120,
        "model_release": "current-unsourced-release"}], "bindings": []}
    result = parse(native_case(), model_metadata=metadata)
    assert result["sheet"]["source_context"]["supplied_model_metadata"] == metadata
    assert result["sheet"]["source_context"]["supplied_model_metadata"] is not metadata
    assert result["sheet"]["model_metadata"] is None
    assert codes(result) == {"rfam_batch_model_provenance_unverified"}
    assert result["issues"][0]["field"] == "supplied_model_metadata"
    assert all(h["components"]["model_span_fraction"] is None for h in calculate_infernal_search_scores(result["sheet"])["hits"])


@pytest.mark.parametrize("metadata", [[], {"length": float("nan")}, {1: "invalid key"}])
def test_invalid_model_metadata_does_not_erase_native_cells(metadata):
    result = parse(native_case(), model_metadata=metadata)
    assert result["sheet"]["source_context"]["supplied_model_metadata"] is None
    assert codes(result) == {"rfam_batch_model_metadata_invalid"}
    assert result["sheet"]["hits"][0]["bitscore"] == 104.6


def test_native_report_membership_lines_and_agreement():
    content, capture = report_case()
    report = parse_rfam_report_membership(content, capture=capture)
    assert report["complete"] is True
    assert report["issues"] == []
    assert len(report["queries"]) == 6
    lines = content.decode("ascii").splitlines()
    for query in report["queries"]:
        assert query["native_query_name"] in lines[query["query_header_line"] - 1]
        assert lines[query["reported_hit_count_line"] - 1].startswith("Total CM hits reported:")
        assert lines[query["close_marker_line"] - 1] == "//"
        assert query["reported_hit_count"] == 1
    result = parse(native_case(), report_membership=report)
    assert all(q["membership_basis"] == "both" and q["reported_set_complete"] for q in result["sheet"]["source_context"]["query_population"])


@pytest.mark.parametrize("kind,expected", [
    ("wrong_job", "rfam_batch_report_job_conflict"),
    ("missing", "rfam_batch_report_query_missing"),
    ("foreign", "rfam_batch_report_foreign_query"),
    ("duplicate", "rfam_batch_report_name_ambiguous"),
    ("length", "rfam_batch_report_length_conflict"),
    ("count", "rfam_batch_report_count_conflict"),
    ("invalid_closed", "rfam_batch_report_invalid"),
])
def test_supplied_report_conflicts_cannot_certify_population(kind, expected):
    content, capture = report_case()
    report = parse_rfam_report_membership(content, capture=capture)
    if kind == "wrong_job":
        report["request_job_id"] = "infernal_cmscan-other"
    elif kind == "missing":
        report["queries"].pop()
    elif kind == "foreign":
        report["queries"][-1]["native_query_name"] = "foreign"
    elif kind == "duplicate":
        report["queries"][-1]["native_query_name"] = report["queries"][0]["native_query_name"]
    elif kind == "length":
        report["queries"][0]["length_nt"] = 120
    elif kind == "count":
        report["queries"][0]["reported_hit_count"] = 2
    else:
        report["queries"][0]["other"] = "not permitted"
    result = parse(native_case(), report_membership=report)
    assert expected in codes(result)
    assert result["status"] == "partial"
    assert len(result["sheet"]["hits"]) == 6
    assert not any(q["reported_set_complete"] for q in result["sheet"]["source_context"]["query_population"])


@pytest.mark.parametrize("kind,expected", [
    ("wrong_filename", "rfam_batch_report_query_file_conflict"),
    ("body", "rfam_batch_report_incomplete"),
    ("footer", "rfam_batch_report_incomplete"),
    ("close", "rfam_batch_report_query_unclosed"),
    ("count", "rfam_batch_report_count_invalid"),
    ("count_duplicate", "rfam_batch_report_count_duplicate"),
    ("duplicate_name", "rfam_batch_report_name_ambiguous"),
    ("wrong_version", "rfam_batch_report_profile_unsupported"),
])
def test_report_native_source_failure_and_partial_membership(kind, expected):
    content, capture = report_case()
    if kind == "wrong_filename":
        content = content.replace((capture["request_job_id"] + ".sequence").encode(), b"infernal_cmscan-other.sequence")
    elif kind == "body":
        capture["body_complete"] = False
    elif kind == "footer":
        content = content.removesuffix(b"[ok]\n")
    elif kind == "close":
        content = content.replace(b"//\n", b"", 1)
    elif kind == "count":
        content = content.replace(b"Total CM hits reported:", b"Unavailable CM hit count:", 1)
    elif kind == "count_duplicate":
        line = next(line for line in content.splitlines() if line.startswith(b"Total CM hits reported:"))
        content = content.replace(line + b"\n", line + b"\n" + line + b"\n", 1)
    elif kind == "duplicate_name":
        content = content.replace(b"Query:       rfam_example_repeat", b"Query:       rfam_example_original")
    elif kind == "wrong_version":
        content = content.replace(b"# INFERNAL 1.1.5", b"# INFERNAL 1.1.6")
    capture.update(source_sha256=digest(content), evidence_kind="synthetic_fixture")
    report = parse_rfam_report_membership(content, capture=capture)
    assert report["complete"] is False
    assert expected in codes(report)
    assert len(report["queries"]) == 6
    result = parse(native_case(), report_membership=report)
    assert result["status"] == "partial"
    assert not any(q["reported_set_complete"] for q in result["sheet"]["source_context"]["query_population"])


def test_zero_hit_report_and_zero_table_agree_without_biological_absence_claim():
    case = native_case()
    content = b"\n".join(line for line in case[0].splitlines() if line.startswith(b"#")) + b"\n"
    report_content, report_capture = report_case()
    header = report_content.split(b"Query:", 1)[0]
    report_content = header + b"".join(
        f'Query: {q["native_query_name"]} [L={q["submitted_length_nt"]}]\nHit scores:\n'
        '   [No hits detected that satisfy reporting thresholds]\n'
        'Total CM hits reported: 0 (0); includes 0 truncated hit(s)\n//\n'.encode()
        for q in case[2]["queries"]) + b"[ok]\n"
    report_capture.update(source_sha256=digest(report_content), evidence_kind="synthetic_fixture")
    report = parse_rfam_report_membership(report_content, capture=report_capture)
    result = parse(synthetic_table(case, content), report_membership=report)
    assert result["status"] == "complete"
    assert [q["reported_row_count"] for q in result["sheet"]["source_context"]["query_population"]] == [0] * 6
    assert "not biological absence" in result["sheet"]["no_hit_meaning"]


def test_saved_recalculation_and_parsing_forbid_acquisition_and_execution(tmp_path, monkeypatch):
    case = native_case()
    content, capture = report_case()

    def forbidden(*args, **kwargs):
        raise AssertionError("acquisition or execution forbidden in supplied-data calculation")

    with monkeypatch.context() as patch:
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        report = parse_rfam_report_membership(content, capture=capture)
        result = parse(case, report_membership=report)
        saved = tmp_path / "native-sheet.json"
        saved.write_text(json.dumps(result["sheet"]))
        original = saved.read_bytes()
        reloaded = json.loads(original)
        baseline = calculate_infernal_search_scores(reloaded, parameters={"hit_scope": "reported"})
        changed = calculate_infernal_search_scores(reloaded, parameters={"hit_scope": "included"})
        assert saved.read_bytes() == original
        assert baseline["hits"][0]["components"]["sequence_span_fraction"] == 1.0
        assert baseline["parameters"] != changed["parameters"]
        assert [r["components"] for r in baseline["hits"]] == [r["components"] for r in changed["hits"]]


def test_wrapper_issues_are_closed_and_native_issues_stay_in_sheet():
    case = native_case()
    case[3]["body_complete"] = False
    result = parse(case, model_metadata={"records": []})
    for issue in result["issues"]:
        assert set(issue) == set(RfamBatchTableIssue.__annotations__)
        assert issue["code"] in RFAM_BATCH_TABLE_ISSUE_CODES
        assert issue["severity"] in ("warning", "error")
    assert any(issue["code"] == "length_denominator_missing" for issue in result["sheet"]["issues"])
    assert not any(issue["code"] == "length_denominator_missing" for issue in result["issues"])


def test_unhashable_supplied_report_issue_code_is_rejected_without_exception():
    content, capture = report_case()
    report = parse_rfam_report_membership(content, capture=capture)
    report.update(complete=False, issues=[{"code": [], "severity": "error", "field": None,
        "native_query_name": None, "source_line": None}])
    result = parse(native_case(), report_membership=report)
    assert "rfam_batch_report_invalid" in codes(result)
    assert len(result["sheet"]["hits"]) == 6


@pytest.mark.parametrize("membership", [[], {"complete": float("nan")}, b"not a membership object"])
def test_invalid_optional_report_object_preserves_native_table_cells(membership):
    result = parse(native_case(), report_membership=membership)
    assert "rfam_batch_report_invalid" in codes(result)
    assert len(result["sheet"]["hits"]) == 6
    assert "report_membership" not in result["sheet"]["source_context"]
    scores = calculate_infernal_search_scores(result["sheet"])
    assert scores["hits"][0]["components"]["bitscore"] == 104.6
    assert all(row["union_span_fraction"] is None for row in scores["sequence_strand_aggregates"])


def test_wrong_report_filename_does_not_supply_query_membership():
    content, capture = report_case()
    content = content.replace((capture["request_job_id"] + ".sequence").encode(), b"infernal_cmscan-other.sequence")
    capture.update(source_sha256=digest(content), evidence_kind="synthetic_fixture")
    report = parse_rfam_report_membership(content, capture=capture)
    result = parse(native_case(), report_membership=report)
    assert "rfam_batch_report_query_file_conflict" in codes(result)
    assert all(q["membership_basis"] == "frozen_complete_input" for q in result["sheet"]["source_context"]["query_population"])


@pytest.mark.parametrize("field", ["length", "count"])
def test_unrepresentable_native_report_integer_is_a_structured_failure(field):
    content, capture = report_case()
    if field == "length":
        content = content.replace(b"[L=119]", b"[L=" + b"9" * 5000 + b"]", 1)
    else:
        content = content.replace(b"Total CM hits reported:                                          1",
            b"Total CM hits reported: " + b"9" * 5000, 1)
    capture.update(source_sha256=digest(content), evidence_kind="synthetic_fixture")
    report = parse_rfam_report_membership(content, capture=capture)
    assert report["complete"] is False
    assert ("rfam_batch_report_query_invalid" if field == "length" else "rfam_batch_report_count_invalid") in codes(report)
