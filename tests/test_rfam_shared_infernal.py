"""Common Infernal authority for retained Rfam bytes and labeled edge cases."""
from copy import deepcopy
import json
import socket
import subprocess

import pytest

from gene_annotation_episode import infernal_search_grader
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.infernal_search_contracts import SHEET_SCHEMA, SCORE_SCHEMA
from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS, rfam_digest
from gene_annotation_episode.rfam_batch_grader import calculate_rfam_batch_components
from gene_annotation_episode.rfam_batch_report_grader import calculate_rfam_batch_report_components
from gene_annotation_episode.rfam_batch_table_grader import calculate_rfam_batch_table_components
from gene_annotation_episode.rfam_batch_infernal import (
    HIT_ALIASES, POPULATION_ALIASES, project_rfam_infernal_result, upgrade_saved_rfam_search_sheet,
    select_rfam_common_sheet,
)
from gene_annotation_episode.rfam_batch_inputs import populate_rfam_batch_json_sheet
from test_rfam_batch_inputs import EXAMPLES, identity, capture, native_example, parse as parse_json
from test_rfam_batch_grader import alignment_bundle
from test_rfam_batch_report import actual_case, one_query, synthetic, parse as parse_report
from test_rfam_batch_table import native_case, parse as parse_table


def full_json():
    content = (EXAMPLES / "official-single-result.json").read_bytes()
    operand, acquired = identity(), capture(content, evidence_kind="official_documentation_example")
    return populate_rfam_batch_json_sheet(content, input_identity=operand, capture=acquired,
        alignment_components=alignment_bundle(content, operand, acquired))


def project(sheet, scores, representation, family="hit", metrics=None):
    return project_rfam_infernal_result(sheet, scores, representation=representation,
        projection=dict(family=family, rows={"offset": 0, "limit": 50},
            metrics=metrics or ["native_score_bits", "query_span_nt"]),
        artifact_bindings=dict(source_ref=sheet["source_context"]["capture"]["source_ref"],
            sheet_ref="saved:sheet", calculation_ref="saved:scores",
            sheet_digest=rfam_digest(sheet), calculation_digest=rfam_digest(scores)))


@pytest.mark.parametrize("representation", ["json", "out", "tblout"])
def test_all_adapters_invoke_exact_same_calculator_once(monkeypatch, representation):
    parsed = {"json": full_json, "out": lambda: parse_report(actual_case()),
              "tblout": lambda: parse_table(native_case())}[representation]()
    sheet = parsed["sheet"]
    assert parsed["version"] == "rfam_batch_parse_result_v2"
    assert parsed["representation"] == representation and sheet["schema"] == SHEET_SCHEMA
    assert sheet["lineage"] is None
    descriptor = sheet["artifacts"][0]["source_descriptor"]
    assert descriptor["byte_hash_verified"] is True
    assert descriptor["source_byte_length"] == len(sheet["artifacts"][0]["content"].encode("utf-8"))
    actual = infernal_search_grader.calculate_infernal_search_scores
    calls = []
    def spy(selected, *, parameters=None):
        calls.append((selected, parameters))
        return actual(selected, parameters=parameters)
    monkeypatch.setattr(infernal_search_grader, "calculate_infernal_search_scores", spy)
    delegate = {"json": calculate_rfam_batch_components, "out": calculate_rfam_batch_report_components,
                "tblout": calculate_rfam_batch_table_components}[representation]
    scores = delegate(parsed if representation == "tblout" else sheet,
        parameters={"hit_scope": "reported"} if representation == "tblout" else RFAM_CALCULATION_PARAMETERS)
    assert len(calls) == 1 and calls[0] == (sheet, {"hit_scope": "reported"})
    assert scores["schema"] == SCORE_SCHEMA and scores["sheet_digest"] == rfam_digest(sheet)
    assert "native_calculation" not in scores


def test_json_unknown_native_cells_and_official_correspondence():
    sheet = full_json()["sheet"]
    scores = calculate_rfam_batch_components(sheet, parameters=RFAM_CALCULATION_PARAMETERS)
    hit, measured = sheet["hits"][0], scores["hits"][0]["attributed_components"]
    assert sheet["operation"] == {"program": None, "native_version": None, "settings": {}}
    assert all(hit.get(k) is None for k in ("program", "algorithm", "inclusion", "model_from", "model_to", "native_query_name"))
    assert hit["sequence"]["name"] is None and hit["sequence"]["identity"]["metadata_index"] == 0
    assert measured["bitscore"] == 104.9 and measured["evalue"] == 4.5e-24 and measured["gc_fraction"] == .49
    assert measured["sequence_span_length"] == 119 and measured["sequence_span_fraction"] == 1
    assert measured["represented_model_positions"] == measured["represented_query_positions"] == 119
    assert measured["model_consensus_equal_count"] == 79 and measured["model_consensus_compared_count"] == 119
    assert measured["model_consensus_equal_fraction"] == 79 / 119
    assert measured["consensus_length"] is None and measured["represented_model_fraction"] is None
    assert hit["source_details"]["raw_row"]["score"] == 104.9


def test_actual_six_query_report_table_use_same_physical_measurements():
    report = parse_report(actual_case())["sheet"]
    table = parse_table(native_case())["sheet"]
    r = infernal_search_grader.calculate_infernal_search_scores(report)
    t = infernal_search_grader.calculate_infernal_search_scores(table)
    for left, right in zip(r["hits"], t["hits"]):
        for name in ("bitscore", "evalue", "gc_fraction", "sequence_from", "sequence_to", "sequence_length",
                     "sequence_span_length", "sequence_span_fraction", "model_from", "model_to", "model_span_length"):
            assert left["attributed_components"][name] == right["attributed_components"][name]
        assert left["query_occurrence_key"] == right["query_occurrence_key"]
    assert [h["components"]["represented_model_positions"] for h in r["hits"]] == [120, 120, 120, 71, 120, 120]
    assert [h["components"]["model_consensus_equal_count"] for h in r["hits"]] == [75, 75, 75, 43, 75, 75]
    assert [h["components"]["model_consensus_compared_count"] for h in r["hits"]] == [118, 118, 118, 70, 118, 117]
    prefix = r["hits"][3]["components"]
    assert prefix["display_model_to"] == 120 and prefix["model_to"] == 71
    assert prefix["truncated_model_count_3p"] == 49 and prefix["native_alignment_accuracy"] == .99
    assert prefix["consensus_length"] is None
    assert all(h["correspondence"] is None for h in table["hits"])


def test_partial_json_union_is_versioned_missing_fraction_with_observed_numerator():
    native = native_example()
    row = native["hits"]["5S_rRNA"][0]
    second = deepcopy(row)
    row.update(start=1, end=60)
    second.update(start=40, end=100)
    native["hits"]["5S_rRNA"].append(second)
    native["numHits"] = 2
    sheet = parse_json(native, capture_changes={"body_complete": False})["sheet"]
    scores = infernal_search_grader.calculate_infernal_search_scores(sheet)
    plus, minus = scores["sequence_strand_aggregates"]
    assert [h["components"]["sequence_span_length"] for h in scores["hits"]] == [60, 61]
    assert (plus["span_sum"], plus["union_numerator"], plus["overlap_excess"]) == (121, 100, 21)
    assert plus["union_span_fraction"] is None and not plus["complete_for_selected_population"]
    assert minus["hit_count"] is None and minus["union_numerator"] is None


@pytest.mark.parametrize("complete", [False, True])
def test_declared_empty_json_populations_preserve_missing_versus_zero(complete):
    sheet = parse_json(fixture="synthetic-empty.json", capture_changes={"body_complete": complete})["sheet"]
    scores = infernal_search_grader.calculate_infernal_search_scores(sheet)
    assert len(scores["sequence_strand_aggregates"]) == 2
    for row in scores["sequence_strand_aggregates"]:
        assert row["union_denominator"] == 119
        for cell in ("hit_count", "valid_geometry_count", "span_sum", "union_numerator", "overlap_excess", "union_span_fraction"):
            assert row[cell] == (0 if complete else None)


@pytest.mark.parametrize("representation", ["json", "out", "tblout"])
@pytest.mark.parametrize("forge_context", [False, True])
def test_saved_complete_flags_cannot_create_a_completed_population(representation, forge_context):
    if representation == "json":
        sheet = parse_json(fixture="synthetic-empty.json", capture_changes={"body_complete": False})["sheet"]
    else:
        case = actual_case() if representation == "out" else native_case()
        case[3].update(body_complete=False, evidence_kind="synthetic_fixture")
        sheet = (parse_report if representation == "out" else parse_table)(case)["sheet"]
    select_rfam_common_sheet(sheet, representation=representation)
    for population in sheet["sequence_populations"]:
        population["reported_set_complete"] = True
    for hit in sheet["hits"]:
        hit["population_complete"] = True
    if forge_context:
        context = sheet["source_context"]
        if representation == "json":
            context["population"]["reported_set_complete"] = True
        elif representation == "out":
            context["population_complete"] = True
        else:
            for population in context["query_population"]:
                population["reported_set_complete"] = True
    with pytest.raises(ContractError):
        select_rfam_common_sheet(sheet, representation=representation)


def test_unknown_inclusion_and_strand_do_not_manufacture_selection_or_population():
    sheet = full_json()["sheet"]
    included = infernal_search_grader.calculate_infernal_search_scores(sheet, parameters={"hit_scope": "included"})
    assert included["hits"][0]["inclusion"] is None
    assert included["sequence_strand_aggregates"][0]["unknown_selection_count"] == 1
    assert included["sequence_strand_aggregates"][0]["union_span_fraction"] is None
    native = native_example()
    native["hits"]["5S_rRNA"][0]["strand"] = "?"
    scores = infernal_search_grader.calculate_infernal_search_scores(parse_json(native)["sheet"])
    assert all(not r["complete_for_selected_population"] and r["union_span_fraction"] is None
               for r in scores["sequence_strand_aggregates"])


def test_json_family_conflict_retains_raw_numbers_and_suppresses_attribution():
    native = native_example()
    native["hits"]["5S_rRNA"][0]["id"] = "foreign"
    sheet = parse_json(native)["sheet"]
    scores = calculate_rfam_batch_components(sheet, parameters=RFAM_CALCULATION_PARAMETERS)
    row = scores["hits"][0]
    assert row["components"]["bitscore"] == 104.9
    assert all(v is None for v in row["attributed_components"].values())
    view = project(sheet, scores, "json")
    assert view["rows"][0]["unavailable"][0] == dict(name="native_score_bits", reason="identity_rejected")


def test_report_conflict_keeps_original_cells_and_does_not_recover_underflow():
    case = one_query()
    changed = case[0].replace(b"1.4e-24", b"1e-999")
    sheet = parse_report(synthetic(case, changed))["sheet"]
    scores = calculate_rfam_batch_report_components(sheet, parameters=RFAM_CALCULATION_PARAMETERS)
    assert scores["hits"][0]["components"]["evalue"] is None
    assert scores["hits"][0]["components"]["bitscore"] == 104.6
    assert sheet["hits"][0]["source_details"]["raw_cells"]["score"]["evalue"] == "1e-999"


@pytest.mark.parametrize("representation", ["json", "out", "tblout"])
def test_saved_recalculation_projection_copy_aliases_without_parser_or_io(monkeypatch, representation):
    sheet = {"json": full_json, "out": lambda: parse_report(actual_case()),
             "tblout": lambda: parse_table(native_case())}[representation]()["sheet"]
    expected = infernal_search_grader.calculate_infernal_search_scores(sheet)
    copied = json.loads(json.dumps(sheet))
    before = deepcopy(copied)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-only calculation or projection attempted acquisition/parser")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_inputs.populate_rfam_batch_json_sheet", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_report.populate_rfam_batch_report_sheet", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_table.populate_rfam_batch_tblout_sheet", forbidden)
    assert infernal_search_grader.calculate_infernal_search_scores(copied) == expected
    monkeypatch.setattr(infernal_search_grader, "calculate_infernal_search_scores", forbidden)
    for family, metrics in (("hit", ["native_score_bits", "query_span_nt", "model_coverage_fraction"]),
                            ("query_strand", list(POPULATION_ALIASES))):
        view = project(copied, expected, representation, family, metrics)
        rows = expected["hits" if family == "hit" else "sequence_strand_aggregates"]
        for projected, row in zip(view["rows"], rows):
            for cell in projected["measured"]:
                aliases = HIT_ALIASES if family == "hit" else POPULATION_ALIASES
                values = row["attributed_components"] if family == "hit" else row
                assert cell["value"] == values[aliases[cell["name"]]]
    assert copied == before


@pytest.mark.parametrize("representation,relative,legacy_schema", [
    ("json", "tool_graders_rfam_numerical_2026-10-26_235/examples_001/examples/live_single.sheet.json", "rfam_batch_sheet_v1"),
    ("out", "tool_graders_rfam_report_2026-10-26_242/examples_011/native.sheet.json", "rfam_batch_report_sheet_v1"),
    ("tblout", "tool_graders_rfam_live_workflow_2026-10-26_243/live_001/parse.json", "rfam_batch_tblout_parse_result_v1"),
])
def test_saved_legacy_conversion_is_explicit_pure_and_does_not_rewrite_old_cells(monkeypatch, representation, relative, legacy_schema):
    path = EXAMPLES.parents[1] / relative
    original_bytes = path.read_bytes()
    old = json.loads(original_bytes)
    before = deepcopy(old)
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy conversion acquired or reparsed data")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_inputs.populate_rfam_batch_json_sheet", forbidden)
    converted = upgrade_saved_rfam_search_sheet(old, representation=representation)
    assert converted["lineage"] == dict(source_sheet_schema=legacy_schema, source_sheet_digest=rfam_digest(old))
    assert converted["artifacts"][0]["source_descriptor"]["byte_hash_verified"] is False
    assert converted["artifacts"][0]["source_descriptor"]["source_byte_length"] is None
    assert old == before
    scores = infernal_search_grader.calculate_infernal_search_scores(converted)
    assert scores["hits"][0]["components"]["bitscore"] == 104.6
    assert scores["hits"][0]["components"]["sequence_span_length"] == 119
    delegate = {"json": calculate_rfam_batch_components, "out": calculate_rfam_batch_report_components,
                "tblout": calculate_rfam_batch_table_components}[representation]
    with pytest.raises((ValueError, ContractError)):
        delegate(old, parameters={"hit_scope": "reported"} if representation == "tblout" else RFAM_CALCULATION_PARAMETERS)
