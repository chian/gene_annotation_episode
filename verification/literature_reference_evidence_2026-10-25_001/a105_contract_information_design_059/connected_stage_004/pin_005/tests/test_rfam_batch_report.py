"""Byte-exact native Rfam reports and explicitly marked synthetic variants."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS, rfam_digest
from gene_annotation_episode.rfam_batch_report import populate_rfam_batch_report_sheet
from gene_annotation_episode.rfam_batch_report_contracts import (
    RFAM_REPORT_METRICS, REPORT_METRIC_DEFINITIONS, validate_rfam_report_sheet,
    validate_rfam_report_calculation,
)
from gene_annotation_episode.rfam_batch_report_grader import calculate_rfam_batch_report_components
from gene_annotation_episode.rfam_batch_report_views import project_rfam_batch_report_result
from test_rfam_batch_table import native_case, report_case


def actual_case():
    _, submitted, identity, _ = native_case()
    content, capture = report_case()
    return content, submitted, identity, capture


def parse(case):
    content, submitted, identity, capture = case
    return populate_rfam_batch_report_sheet(content, input_identity=identity,
        capture=capture, submitted_content=submitted)


def synthetic(case, content=None, *, submitted=None, identity=None):
    original, original_submitted, original_identity, capture = deepcopy(case)
    content = original if content is None else content
    submitted = original_submitted if submitted is None else submitted
    identity = original_identity if identity is None else deepcopy(identity)
    identity.update(submitted_file_sha256=hashlib.sha256(submitted).hexdigest(), submitted_file_bytes=len(submitted))
    capture.update(evidence_kind="synthetic_fixture", source_sha256=hashlib.sha256(content).hexdigest(),
                   request_file_sha256=identity["submitted_file_sha256"],
                   artifact_ref="synthetic:" + hashlib.sha256(content).hexdigest(),
                   source_ref="synthetic-source:" + hashlib.sha256(content).hexdigest())
    return content, submitted, identity, capture


def one_query():
    case = actual_case()
    content, submitted, identity, _ = case
    content = content.split(b"//\n", 1)[0] + b"//\n[ok]\n"
    submitted = submitted.split(b">", 2)[0] + b">" + submitted.split(b">", 2)[1]
    identity = deepcopy(identity)
    identity["queries"] = identity["queries"][:1]
    return synthetic(case, content, submitted=submitted, identity=identity)


def calculate(sheet):
    return calculate_rfam_batch_report_components(sheet, parameters=RFAM_CALCULATION_PARAMETERS)


def project(sheet, calculation, *, family="hit", metrics=None, rows=None):
    return project_rfam_batch_report_result(sheet, calculation,
        projection=dict(family=family, rows=rows or {"offset": 0, "limit": 20},
                        metrics=metrics or list(RFAM_REPORT_METRICS[family])),
        artifact_bindings=dict(source_ref=sheet["capture"]["source_ref"], sheet_ref="saved-sheet",
            calculation_ref="saved-calculation", sheet_digest=rfam_digest(sheet), calculation_digest=rfam_digest(calculation)))


def codes(result):
    return {item["code"] for item in result["issues"]}


def test_retained_six_queries_native_measurements_and_exact_source_lines():
    case = actual_case()
    before = deepcopy(case)
    result = parse(case)
    assert result["status"] == "partial"
    assert codes(result) == {"rfam_alignment_correspondence_unrepresented"}
    sheet = result["sheet"]
    assert sheet["population_complete"]
    assert validate_rfam_report_sheet(sheet) == sheet
    calculation = calculate(sheet)
    assert validate_rfam_report_calculation(calculation, sheet=sheet) == calculation
    assert [r["native_score_bits"] for r in calculation["hits"]] == [104.6, 104.6, 104.6, 51.3, 95.5, 95.2]
    assert [r["query_span_nt"] for r in calculation["hits"]] == [119, 119, 119, 70, 120, 118]
    assert [r["model_consensus_compared_count"] for r in calculation["hits"]] == [118, 118, 118, 70, 118, 117]
    assert [r["query_insert_count"] for r in calculation["hits"]] == [1, 1, 1, 0, 2, 1]
    assert [r["model_delete_count"] for r in calculation["hits"]] == [2, 2, 2, 1, 2, 3]
    assert all(r["query_span_fraction"] == 1 for r in calculation["hits"])
    assert len({r["query_occurrence_key"] for r in calculation["hits"]}) == 6
    assert len(calculation["query_strands"]) == 12
    assert calculation["hits"][2]["strand"] == "-"
    assert calculation["hits"][2]["native_start_1i"] == 119
    assert calculation["hits"][2]["native_end_1i"] == 1
    assert calculation["hits"][3]["native_model_span_positions"] == 71
    assert calculation["hits"][3]["represented_model_positions"] == 71
    assert calculation["hits"][3]["display_model_to"] == 120
    assert calculation["hits"][3]["truncated_model_count_3p"] == 49
    assert all(r["model_length_positions"] is None and r["model_coverage_fraction"] is None for r in calculation["hits"])
    raw = case[0].decode().splitlines()
    for hit in sheet["hits"]:
        assert hit["family_accession"] is None and hit["model_name"] == "5S_rRNA"
        assert hit["hit_key"] == sheet["capture"]["artifact_ref"] + "/lines/" + str(hit["score_line"])
        assert all(line["text"] == raw[line["line"] - 1] for line in hit["source_lines"])
        assert all(line["text"] == raw[line["line"] - 1] for block in hit["correspondence"]["blocks"] for line in block["source_lines"])
    projection = project(sheet, calculation, metrics=["native_score_bits", "represented_model_positions", "model_coverage_fraction"])
    assert projection["rows"][0]["model_name"] == "5S_rRNA"
    assert projection["rows"][0]["family_accession"] is None
    assert projection["rows"][0]["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
    assert case == before


def test_metric_definitions_cover_every_allowed_numerical_cell():
    assert set(REPORT_METRIC_DEFINITIONS) == set().union(*[set(v) for v in RFAM_REPORT_METRICS.values()])
    assert all(set(row) == {"inputs", "meaning", "formula", "unit", "denominator", "population", "coordinates", "uncertainty", "missing", "kind"}
               for row in REPORT_METRIC_DEFINITIONS.values())


def test_saved_sheet_recalculation_and_projection_forbid_acquisition_or_parser(monkeypatch):
    sheet = parse(actual_case())["sheet"]
    expected = calculate(sheet)
    sheet = json.loads(json.dumps(sheet, allow_nan=False))
    def forbidden(*args, **kwargs):
        raise AssertionError("pure saved-sheet operation attempted acquisition or parsing")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_report.populate_rfam_batch_report_sheet", forbidden)
    actual = calculate(sheet)
    assert actual == expected
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_report_grader.calculate_rfam_batch_report_components", forbidden)
    view = project(sheet, actual, rows={"record_keys": [actual["hits"][2]["hit_key"]]}, metrics=["query_span_nt"])
    assert view["selected_row_count"] == 1 and view["rows"][0]["strand"] == "-"


def test_native_parser_operates_on_supplied_bytes_without_io(monkeypatch):
    case = actual_case()
    def forbidden(*args, **kwargs):
        raise AssertionError("native parser attempted acquisition or execution")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    result = parse(case)
    assert result["sheet"]["population_complete"] and len(result["sheet"]["hits"]) == 6


@pytest.mark.parametrize("field,changed,code", [
    ("request_job_id", "infernal_cmscan-foreign", "rfam_batch_result_job_conflict"),
    ("request_file_sha256", "0" * 64, "rfam_batch_result_file_conflict"),
    ("source_sha256", "0" * 64, "rfam_batch_source_identity_conflict"),
    ("submission_source_ref", "foreign", "rfam_batch_submission_source_conflict")])
def test_original_custody_conflicts_reject(field, changed, code):
    case = actual_case()
    case[3][field] = changed
    result = parse(case)
    assert result["status"] == "rejected" and result["sheet"] is None and code in codes(result)


def test_wrong_submitted_sequence_or_unheaded_file_is_not_guessed():
    case = actual_case()
    result = parse((case[0], case[1].replace(b"AGTT", b"AGCT", 1), case[2], case[3]))
    assert result["status"] == "rejected"
    one = one_query()
    assert parse((one[0], one[1].split(b"\n", 1)[1], one[2], one[3]))["status"] == "rejected"


def test_partial_native_report_preserves_independent_hits_without_complete_population():
    case = actual_case()
    content = case[0].split(b"Query:       rfam_example_deletion")[0]
    result = parse(synthetic(case, content))
    assert result["status"] == "partial" and len(result["sheet"]["hits"]) == 5
    assert not result["sheet"]["population_complete"]
    values = calculate(result["sheet"])
    assert values["hits"][0]["model_consensus_compared_count"] == 118
    assert all(row["query_strand_union_fraction"] is None for row in values["query_strands"])


def test_foreign_query_has_no_attributed_measurements_and_valid_siblings_survive():
    case = actual_case()
    changed = case[0].replace(b"rfam_example_repeat", b"foreign_query_name_")
    sheet = parse(synthetic(case, changed))["sheet"]
    assert not sheet["population_complete"]
    assert sheet["hits"][1]["query_occurrence_key"] is None
    result = calculate(sheet)
    assert all(result["hits"][1][metric] is None for metric in RFAM_REPORT_METRICS["hit"])
    assert result["hits"][0]["native_score_bits"] == 104.6


def test_malformed_optional_pp_keeps_geometry_and_native_score():
    case = actual_case()
    changed = case[0].replace(b"****************************************.", b"?***************************************.", 1)
    sheet = parse(synthetic(case, changed))["sheet"]
    row = calculate(sheet)["hits"][0]
    assert row["model_consensus_compared_count"] == 118 and row["native_score_bits"] == 104.6
    assert "rfam_alignment_invalid" in codes(sheet["hits"][0])


def test_synthetic_complete_zero_hit_is_measured_zero():
    case = one_query()
    text = case[0].decode()
    start, end = text.index("Hit scores:"), text.index("Internal CM pipeline")
    text = text[:start] + "Hit scores:\n\n   [No hits detected that satisfy reporting thresholds]\n\nHit alignments:\n\n   [No hits detected that satisfy reporting thresholds]\n\n" + text[end:]
    text = re.sub(r"Total CM hits reported:\s+1", "Total CM hits reported: 0", text)
    sheet = parse(synthetic(case, text.encode()))["sheet"]
    assert sheet["population_complete"] and sheet["hits"] == []
    rows = calculate(sheet)["query_strands"]
    assert all(row["selected_row_count"] == 0 and row["query_strand_union_fraction"] == 0 for row in rows)


def test_synthetic_reordered_query_blocks_preserve_original_occurrences():
    case = actual_case()
    parts = re.split(br"(?=Query:)", case[0])
    blocks = [p.replace(b"[ok]\n", b"") for p in parts[1:]]
    sheet = parse(synthetic(case, parts[0] + b"".join(reversed(blocks)) + b"[ok]\n"))["sheet"]
    assert sheet["population_complete"]
    assert sheet["hits"][0]["query_occurrence_key"] == case[2]["queries"][-1]["query_occurrence_key"]
    assert calculate(sheet)["hits"][0]["query_span_nt"] == 118


@pytest.mark.parametrize("mutation", [
    lambda s: s["hits"][0].update(query_occurrence_key="foreign"),
    lambda s: s["hits"][0].update(family_accession="RF00001"),
    lambda s: s["hits"][0]["correspondence"].update(model_consensus_equal_count=99),
    lambda s: s["hits"][0]["correspondence"]["paired_positions"][0].update(query_position=5),
    lambda s: s["hits"][0]["source_lines"][0].update(extra=True),
])
def test_closed_saved_sheet_associations_reject_tampering(mutation):
    sheet = parse(actual_case())["sheet"]
    mutation(sheet)
    with pytest.raises(ContractError):
        calculate(sheet)


def test_synthetic_duplicate_overlap_retains_two_rows_without_double_union():
    case = one_query()
    text = case[0].decode()
    score = next(line for line in text.splitlines() if line.lstrip().startswith("(1)"))
    display_start, display_end = text.index(">>"), text.index("Internal CM pipeline")
    display = text[display_start:display_end]
    text = text.replace(score, score + "\n" + score.replace("(1)", "(2)"), 1)
    text = text.replace(display, display + display.replace("(1)", "(2)"), 1)
    text = re.sub(r"Total CM hits reported:\s+1", "Total CM hits reported: 2", text)
    sheet = parse(synthetic(case, text.encode()))["sheet"]
    assert sheet["population_complete"] and len(sheet["hits"]) == 2
    row = calculate(sheet)["query_strands"][0]
    assert row["selected_row_count"] == 2 and row["query_strand_sum_span_nt"] == 238
    assert row["query_strand_union_span_nt"] == row["query_strand_overlap_excess_nt"] == 119
    assert row["query_strand_union_fraction"] == 1
    ambiguous = synthetic(case, text.replace("(2)", "(1)").encode())
    result = parse(ambiguous)
    assert "rfam_report_rank_ambiguous" in codes(result)
    assert len(result["sheet"]["hits"]) == 2 and not result["sheet"]["population_complete"]
    assert all(row["correspondence"] is None for row in result["sheet"]["hits"])
    assert calculate(result["sheet"])["query_strands"][0]["query_strand_sum_span_nt"] == 238


def test_synthetic_malformed_score_sibling_keeps_independent_cells_and_other_hits():
    case = actual_case()
    text = case[0].decode()
    # Both repeated source cells malformed; no fallback to an arbitrary row.
    text = text.replace("  104.6 ", "  broken ", 2)
    sheet = parse(synthetic(case, text.encode()))["sheet"]
    result = calculate(sheet)
    assert result["hits"][0]["native_score_bits"] is None
    assert result["hits"][0]["native_evalue"] == 1.4e-24
    assert result["hits"][0]["model_consensus_compared_count"] == 118
    assert result["hits"][1]["native_score_bits"] == 104.6


def test_synthetic_conflicting_repeated_coordinates_cannot_attach_alignment():
    case = one_query()
    text = case[0].decode().replace("[]           1         119", "[]           2         119", 1)
    result = parse(synthetic(case, text.encode()))
    assert "rfam_report_cell_conflict" in codes(result)
    row = calculate(result["sheet"])["hits"][0]
    assert row["query_span_nt"] is None and row["model_consensus_compared_count"] is None
    assert row["native_score_bits"] == 104.6


def test_synthetic_same_name_wrong_sequence_rejects_attribution():
    case = one_query()
    submitted = case[1].replace(b"AGTT", b"ACTT", 1)
    identity = deepcopy(case[2])
    query = identity["queries"][0]
    query["submitted_sequence"] = query["submitted_sequence"].replace("AGTT", "ACTT", 1)
    query["submitted_sequence_sha256"] = hashlib.sha256(query["submitted_sequence"].encode()).hexdigest()
    sheet = parse(synthetic(case, submitted=submitted, identity=identity))["sheet"]
    assert "rfam_alignment_query_conflict" in codes(sheet)
    assert sheet["hits"][0]["query_occurrence_key"] is None
    assert not sheet["population_complete"]
    assert all(calculate(sheet)["hits"][0][metric] is None for metric in RFAM_REPORT_METRICS["hit"])


def test_synthetic_missing_alignment_and_missing_query_remain_distinct():
    case = one_query()
    content = re.sub(br"Hit alignments:.*?Internal CM pipeline", b"Internal CM pipeline", case[0], flags=re.S)
    sheet = parse(synthetic(case, content))["sheet"]
    row = calculate(sheet)["hits"][0]
    assert row["query_span_nt"] == 119 and row["model_consensus_compared_count"] is None
    assert not sheet["population_complete"]
    assert "rfam_report_alignment_missing" in codes(sheet)
    incomplete = parse(synthetic(case, case[0].split(b"Query:")[0]))["sheet"]
    assert "rfam_batch_report_query_missing" in codes(incomplete)
    assert all(row["selected_row_count"] is None for row in calculate(incomplete)["query_strands"])


def test_synthetic_repeated_query_names_do_not_get_occurrence_measurements():
    case = one_query()
    prefix, block = case[0].split(b"Query:", 1)
    block = b"Query:" + block.replace(b"[ok]\n", b"")
    sheet = parse(synthetic(case, prefix + block + block + b"[ok]\n"))["sheet"]
    assert "rfam_batch_report_name_ambiguous" in codes(sheet)
    assert all(row["query_occurrence_key"] is None for row in sheet["hits"])
    assert all(row["native_score_bits"] is None for row in calculate(sheet)["hits"])


@pytest.mark.parametrize("old,new,status,code", [
    (b"INFERNAL 1.1.5", b"INFERNAL 1.1", "unsupported", "rfam_batch_report_profile_unsupported"),
    (b"# cmscan ::", b"# cmsearch ::", "unsupported", "rfam_batch_report_profile_unsupported"),
    (b"p1m.sequence", b"foreign.sequence", "rejected", "rfam_batch_report_query_file_conflict"),
])
def test_native_version_mode_and_original_query_file_are_validated(old, new, status, code):
    case = actual_case()
    result = parse(synthetic(case, case[0].replace(old, new)))
    assert result["status"] == status and result["sheet"] is None
    assert code in codes(result)


def test_synthetic_early_eof_inside_display_preserves_siblings():
    case = actual_case()
    content = case[0][:case[0].index(b"Query:       rfam_example_deletion")]
    last_block = b"Query:       rfam_example_deletion" + case[0].split(b"Query:       rfam_example_deletion", 1)[1]
    content += last_block.split(b"\n  rfam_example_deletion", 1)[0]
    sheet = parse(synthetic(case, content))["sheet"]
    result = calculate(sheet)
    assert result["hits"][0]["model_consensus_compared_count"] == 118
    assert not sheet["population_complete"]
    assert result["hits"][-1]["model_consensus_compared_count"] is None


def test_synthetic_native_boundary_symbols_are_not_silent_coordinate_changes():
    case = one_query()
    changed = case[0].replace(b"+ [] 1.00", b"+ .. 1.00", 1)
    sheet = parse(synthetic(case, changed))["sheet"]
    row = calculate(sheet)["hits"][0]
    assert "rfam_report_coordinates_invalid" in codes(sheet)
    assert row["query_span_nt"] is None and row["model_consensus_compared_count"] is None
    assert row["native_score_bits"] == 104.6


def test_synthetic_profile_with_retained_upstream_wrapped_display_has_real_geometry():
    """1.1 tutorial display preserved; synthetic 1.1.5 header is NOT a native run."""
    root = Path(__file__).resolve().parents[1]
    original = (root / "resources/software/infernal-1.1.5/tutorial/minifam-metag.out").read_bytes()
    assert hashlib.sha256(original).hexdigest() == "79fa771808a40d33f00d58eeb9320289a2bc48740c9928fafbeee66ae91262e4"
    fixture = json.loads((root / "verification/tool_graders_rfam_alignment_2026-10-26_236/fixtures/upstream-cobalamin-wrapped-local-end.json").read_text())
    case = one_query()
    head = case[0].split(b"Query:")[0]
    block = b"Query:" + original.split(b"Query:       AAFY01022046.1", 1)[1].split(b"//", 1)[0]
    block = block.replace(b"Query:", b"Query:       AAFY01022046.1", 1)
    sequence = fixture["query_sequence"]
    submitted = (">AAFY01022046.1\n" + sequence + "\n").encode()
    identity = deepcopy(case[2])
    query = identity["queries"][0]
    query.update(native_query_name="AAFY01022046.1", original_header="AAFY01022046.1", submitted_sequence=sequence,
        submitted_sequence_sha256=hashlib.sha256(sequence.encode()).hexdigest(), submitted_length_nt=len(sequence))
    sheet = parse(synthetic(case, head + block + b"//\n[ok]\n", submitted=submitted, identity=identity))["sheet"]
    assert sheet["population_complete"]
    correspondence = sheet["hits"][0]["correspondence"]
    assert len(correspondence["blocks"]) == 2
    assert correspondence["status"] == "partial"
    row = calculate(sheet)["hits"][0]
    assert row["native_model_from_1i"] == 32 and row["native_model_to_1i"] == 191
    assert row["native_model_span_positions"] == 160
    assert row["represented_model_positions"] == row["represented_query_positions"] == 99
    assert row["model_consensus_compared_count"] == 98 and row["model_consensus_equal_count"] == 49
    assert row["local_end_model_omitted_count"] == 61 and row["local_end_query_count"] == 4
    assert row["truncated_model_count_5p"] == 31
    means = [p for p in correspondence["posterior_segments"] if p["meaning"] == "span_mean_placement_bin"]
    assert len(means) == 1 and means[0]["lower_bound"] == .65 and means[0]["upper_bound"] == .75


def test_signed_native_bias_is_preserved_without_an_unestablished_bound():
    case = one_query()
    text = case[0].replace(b"104.6   0.0", b"104.6  -0.4")
    sheet = parse(synthetic(case, text))["sheet"]
    calculation = calculate(sheet)
    assert sheet["hits"][0]["native"]["bias"] == -.4
    assert calculation["hits"][0]["native_bias_bits"] == -.4
    assert project(sheet, calculation, metrics=["native_bias_bits"])["rows"][0]["measured"] == [
        {"name": "native_bias_bits", "value": -.4, "unit": "bits"}]


@pytest.mark.parametrize("mutation", [
    lambda c: c["hits"][0].update(native_score_bits=99),
    lambda c: c["hits"][0].update(model_length_positions=120),
    lambda c: c["hits"][0].update(model_consensus_compared_count=1),
    lambda c: c["hits"][0].update(query_occurrence_key="foreign"),
    lambda c: c["hits"][0].update(model_name="foreign"),
    lambda c: c["hits"][0].update(represented_query_positions=1.5),
    lambda c: c["query_strands"][0].update(query_length_nt=1),
    lambda c: c["parameters"].update(hit_population="best_only"),
])
def test_saved_calculation_tampering_is_rejected_before_projection(mutation):
    sheet = parse(actual_case())["sheet"]
    calculation = calculate(sheet)
    mutation(calculation)
    with pytest.raises(ContractError):
        project(sheet, calculation)


def test_projection_requires_exact_supplied_artifact_digests():
    sheet = parse(actual_case())["sheet"]
    calculation = calculate(sheet)
    with pytest.raises(ContractError, match="rfam_projection_reference_conflict"):
        project_rfam_batch_report_result(sheet, calculation,
            projection={"family": "hit", "rows": {"offset": 0, "limit": 1}, "metrics": ["query_span_nt"]},
            artifact_bindings={"source_ref": sheet["capture"]["source_ref"], "sheet_ref": "saved",
                "calculation_ref": "saved", "sheet_digest": rfam_digest(sheet), "calculation_digest": "0" * 64})


def test_legacy_alignment_outputs_exactly_match_the_preexisting_retained_objects():
    from gene_annotation_episode.rfam_batch_alignment import parse_rfam_alignment_display
    root = Path(__file__).resolve().parents[1]
    evidence = root / "verification/tool_graders_rfam_alignment_2026-10-26_236"
    for name in ("native-rfam_example_original", "native-rfam_example_repeat", "native-rfam_example_reverse_complement",
                 "native-rfam_example_prefix70", "native-rfam_example_insertion", "native-rfam_example_deletion",
                 "upstream-cobalamin-wrapped-local-end"):
        fixture = json.loads((evidence / "fixtures" / (name + ".json")).read_text())
        expected = json.loads((evidence / "examples_001/examples" / (name + ".components.json")).read_text())
        result = parse_rfam_alignment_display(fixture["alignment"], **{key: fixture[key] for key in
            ("hit_identity", "query_sequence", "native_start", "native_end", "native_strand")})
        assert result == expected
    for name, path in (
        ("live-single", root / "verification/tool_graders_rfam_transport_2026-10-26_234/live/single/003-fetch-json/response.body"),
        ("official-documentation-single", root / "verification/tool_graders_rfam_contract_2026-10-26_232/examples/official-single-result.json")):
        expected = json.loads((evidence / "examples_001/examples" / (name + ".components.json")).read_text())["rows"][0]
        original = json.loads(path.read_text())
        hit = original["hits"]["5S_rRNA"][0]
        actual = parse_rfam_alignment_display(hit["alignment"], hit_identity=expected["hit_identity"],
            query_sequence=original["searchSequence"], native_start=hit["start"], native_end=hit["end"], native_strand=hit["strand"])
        assert actual == expected
