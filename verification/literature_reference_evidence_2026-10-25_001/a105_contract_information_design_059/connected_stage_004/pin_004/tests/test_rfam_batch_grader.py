from copy import deepcopy
import json
import socket
import subprocess
import urllib.request

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS, rfam_digest
from gene_annotation_episode.rfam_batch_grader import calculate_rfam_batch_components
from test_rfam_batch_inputs import (native_example, parse, model_metadata, identity, capture,
    EXAMPLES, live_single_operands)


def calculate(sheet):
    return calculate_rfam_batch_components(sheet, parameters=deepcopy(RFAM_CALCULATION_PARAMETERS))


def test_documented_numerical_example_has_separate_native_and_derived_values():
    sheet = parse()["sheet"]
    result = calculate(sheet)
    hit = result["hits"][0]
    assert result["sheet_digest"] == rfam_digest(sheet)
    assert hit["native_score_bits"] == 104.9 and hit["native_evalue"] == 4.5e-24
    assert hit["native_gc_fraction"] == .49
    assert hit["query_span_nt"] == 119 and hit["query_span_fraction"] == 1.
    assert hit["represented_model_positions"] is None
    assert hit["model_length_positions"] is None and hit["model_coverage_fraction"] is None
    plus, minus = result["query_strands"]
    assert (plus["selected_row_count"], plus["query_strand_sum_span_nt"], plus["query_strand_union_span_nt"], plus["query_strand_overlap_excess_nt"]) == (1, 119, 119, 0)
    assert (minus["selected_row_count"], minus["query_strand_sum_span_nt"], minus["query_strand_union_span_nt"], minus["query_strand_union_fraction"]) == (0, 0, 0, 0.)
    assert plus["population_complete"] and minus["population_complete"]


def test_duplicate_and_overlapping_coordinates_have_explicit_multiplicity():
    result = calculate(parse(fixture="synthetic-duplicate-hits.json")["sheet"])
    assert len(result["hits"]) == 2 and result["population"]["duplicate_row_count"] == 1
    plus = result["query_strands"][0]
    assert (plus["query_strand_sum_span_nt"], plus["query_strand_union_span_nt"], plus["query_strand_overlap_excess_nt"]) == (238, 119, 119)
    native = native_example()
    row = native["hits"]["5S_rRNA"][0]
    second = deepcopy(row)
    row.update(start=1, end=60)
    second.update(start=40, end=100)
    native["hits"]["5S_rRNA"].append(second)
    native["numHits"] = 2
    result = calculate(parse(native)["sheet"])
    assert [r["query_span_nt"] for r in result["hits"]] == [60, 61]
    plus = result["query_strands"][0]
    assert (plus["query_strand_sum_span_nt"], plus["query_strand_union_span_nt"], plus["query_strand_overlap_excess_nt"]) == (121, 100, 21)
    assert result["population"]["duplicate_row_count"] == 0


def test_reverse_coordinates_remain_physical_and_opposite_strands_separate():
    sheet = parse(fixture="synthetic-partial.json")["sheet"]
    result = calculate(sheet)
    assert result["population"]["reported_row_count"] == 3
    assert result["population"]["valid_interval_row_count"] == 2
    assert result["population"]["interval_population_complete"] is False
    assert result["hits"][1]["query_span_nt"] is None
    assert result["hits"][1]["native_score_bits"] == 104.9
    assert result["hits"][2]["query_span_nt"] == 101
    plus, minus = result["query_strands"]
    assert plus["query_strand_union_span_nt"] == 119
    assert plus["population_complete"] is False
    assert minus["query_strand_union_span_nt"] == 101
    assert minus["query_strand_union_fraction"] == 101 / 119


def test_direction_contradiction_does_not_erase_native_score():
    result = calculate(parse(fixture="synthetic-conflicting-strand.json")["sheet"])
    hit = result["hits"][0]
    assert hit["native_score_bits"] == 104.9 and hit["query_span_nt"] is None
    assert hit["missing"]["query_span_fraction"] == "coordinates_invalid"
    assert result["query_strands"][1]["population_complete"] is False


def test_boundary_single_nucleotide_on_either_strand():
    for strand in ("+", "-"):
        native = native_example()
        native["hits"]["5S_rRNA"][0].update(start=119, end=119, strand=strand)
        result = calculate(parse(native)["sheet"])
        assert result["hits"][0]["query_span_nt"] == 1
        assert result["hits"][0]["query_span_fraction"] == 1 / 119


def test_family_identity_rejection_retains_raw_cells_without_attributed_metrics():
    native = native_example()
    native["hits"]["5S_rRNA"][0]["id"] = "different_family"
    sheet = parse(native)["sheet"]
    assert sheet["hits"][0]["native"]["score_bits"] == 104.9
    result = calculate(sheet)
    assert result["hits"][0]["native_score_bits"] is None
    assert result["hits"][0]["family_accession"] is None
    assert result["hits"][0]["missing"]["native_score_bits"] == "identity_rejected"
    assert result["population"]["valid_interval_row_count"] == 0


def test_empty_and_partial_count_denominators():
    empty = calculate(parse(fixture="synthetic-empty.json")["sheet"])
    assert empty["hits"] == []
    assert all(r["population_complete"] and r["query_strand_union_span_nt"] == 0 for r in empty["query_strands"])
    partial = calculate(parse(fixture="synthetic-conflicting-count.json")["sheet"])
    assert partial["population"]["reported_row_count"] == 1
    assert all(r["population_complete"] is False for r in partial["query_strands"])
    assert partial["query_strands"][0]["query_strand_union_span_nt"] == 119


def test_saved_recalculation_performs_no_network_execution_or_file_io(monkeypatch, tmp_path):
    # Save and read before forbidding IO; repeat arithmetic solely in memory.
    path = tmp_path / "sheet.json"
    path.write_text(json.dumps(parse()["sheet"]))
    sheet = json.loads(path.read_text())
    expected = calculate(sheet)
    snapshot = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("recalculation attempted acquisition/execution/file IO")
    with monkeypatch.context() as m:
        m.setattr("builtins.open", forbidden)
        m.setattr("pathlib.Path.open", forbidden)
        m.setattr(socket, "socket", forbidden)
        m.setattr(socket, "create_connection", forbidden)
        m.setattr(urllib.request, "urlopen", forbidden)
        m.setattr(subprocess, "Popen", forbidden)
        assert calculate(sheet) == expected
    assert sheet == snapshot


@pytest.mark.parametrize("changes", [{"hit_population": "included"}, {"temperature": 1}, {"duplicate_policy": "drop"}])
def test_no_hidden_parameters_or_population_substitution(changes):
    with pytest.raises(ContractError, match="rfam_parameters_invalid"):
        calculate_rfam_batch_components(parse()["sheet"], parameters={**RFAM_CALCULATION_PARAMETERS, **changes})


def test_modified_saved_identity_or_fabricated_model_denominator_rejected():
    sheet = parse()["sheet"]
    bad = deepcopy(sheet)
    bad["input"]["submitted_length_nt"] = 120
    with pytest.raises(ContractError):
        calculate(bad)
    bad = deepcopy(sheet)
    bad["hits"][0]["model_length_positions"] = 119
    bad["hits"][0]["model_metadata_ref"] = "some_model"
    with pytest.raises(ContractError, match="rfam_model_binding_unverified"):
        calculate(bad)


def test_unknown_model_metadata_only_suppresses_dependent_cells():
    result = calculate(parse(model_metadata=model_metadata(119))["sheet"])
    hit = result["hits"][0]
    assert hit["query_span_fraction"] == 1
    assert hit["missing"]["model_coverage_fraction"] == "model_binding_unverified"


def alignment_bundle(content, operand, acquired):
    from gene_annotation_episode.rfam_batch_alignment import parse_rfam_alignment_display
    native = json.loads(content)
    rows = []
    for family, hits in native["hits"].items():
        for index, hit in enumerate(hits):
            pointer = "/hits/" + family.replace("~", "~0").replace("/", "~1") + "/" + str(index)
            rows.append(parse_rfam_alignment_display(hit["alignment"],
                hit_identity={"artifact_ref": acquired["artifact_ref"], "hit_key": acquired["artifact_ref"] + pointer,
                    "query_occurrence_key": operand["query_occurrence_key"], "family_accession": hit["acc"]},
                query_sequence=operand["submitted_sequence"], native_start=hit["start"],
                native_end=hit["end"], native_strand=hit["strand"]))
    return {"version": "rfam_alignment_components_bundle_v1", "artifact_ref": acquired["artifact_ref"],
        "source_sha256": acquired["source_sha256"], "rows": rows}


@pytest.mark.parametrize("live", [False, True])
def test_separate_actual_alignment_reader_composes_into_sheet_and_saved_calculator(live):
    from gene_annotation_episode.rfam_batch_inputs import populate_rfam_batch_json_sheet
    if live:
        content, operand, acquired = live_single_operands()
    else:
        content = (EXAMPLES / "official-single-result.json").read_bytes()
        operand, acquired = identity(), capture(content, evidence_kind="official_documentation_example")
    bundle = alignment_bundle(content, operand, acquired)
    result = populate_rfam_batch_json_sheet(content, input_identity=operand, capture=acquired, alignment_components=bundle)
    hit = calculate(result["sheet"])["hits"][0]
    assert hit["represented_model_positions"] == (120 if live else 119)
    assert hit["model_consensus_compared_count"] == (118 if live else 119)
    if not live:
        assert hit["model_consensus_equal_count"] == 79
        assert hit["model_consensus_equal_fraction"] == 79 / 119
    assert hit["model_length_positions"] is None and hit["model_coverage_fraction"] is None
    assert hit["query_span_nt"] == 119 and hit["query_span_fraction"] == 1.
    assert hit["display_model_to"] == (120 if live else 119)
    assert calculate(json.loads(json.dumps(result["sheet"])))["hits"][0] == hit


@pytest.mark.parametrize("mutation", ["artifact", "query", "family", "strand", "pointer", "duplicate", "foreign",
    "duplicate_query_position", "wrong_posterior_bin"])
def test_alignment_component_misbinding_only_disables_alignment(mutation):
    from gene_annotation_episode.rfam_batch_inputs import populate_rfam_batch_json_sheet
    content, operand, acquired = live_single_operands()
    bundle = alignment_bundle(content, operand, acquired)
    row = bundle["rows"][0]
    if mutation == "artifact":
        bundle["source_sha256"] = "0" * 64
    elif mutation == "query":
        row["hit_identity"]["query_occurrence_key"] = "foreign:query"
    elif mutation == "family":
        row["hit_identity"]["family_accession"] = "RF99999"
    elif mutation == "strand":
        row["query_strand"] = "-"
    elif mutation == "pointer":
        row["raw_alignment_ref"]["json_pointer"] = "/hits/5S_rRNA/1/alignment"
    elif mutation == "duplicate":
        bundle["rows"].append(deepcopy(row))
    elif mutation == "duplicate_query_position":
        row["paired_positions"][1]["query_position"] = row["paired_positions"][0]["query_position"]
    elif mutation == "wrong_posterior_bin":
        row["posterior_segments"][0]["lower_bound"] = 0.
    else:
        row["hit_key"] = acquired["artifact_ref"] + "/hits/5S_rRNA/1"
    result = populate_rfam_batch_json_sheet(content, input_identity=operand, capture=acquired, alignment_components=bundle)
    hit = calculate(result["sheet"])["hits"][0]
    assert hit["native_score_bits"] == 104.6 and hit["query_span_nt"] == 119
    assert hit["represented_model_positions"] is None


def test_missing_optional_pp_preserves_supplied_geometry_and_native_scores():
    from gene_annotation_episode.rfam_batch_inputs import populate_rfam_batch_json_sheet
    native = native_example()
    del native["hits"]["5S_rRNA"][0]["alignment"]["pp"]
    content = json.dumps(native).encode()
    operand, acquired = identity(), capture(content)
    bundle = alignment_bundle(content, operand, acquired)
    result = populate_rfam_batch_json_sheet(content, input_identity=operand, capture=acquired, alignment_components=bundle)
    hit = calculate(result["sheet"])["hits"][0]
    assert result["status"] == "partial"
    assert hit["represented_model_positions"] == 119
    assert hit["model_consensus_equal_count"] == 79 and hit["native_score_bits"] == 104.9
