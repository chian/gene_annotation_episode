"""Actual retained 294 reports -> 297 publication -> received HSP column reader.

These are supplied-artifact tests, not new BLAST executions. Deliberate native
faults are separately labeled synthetic inputs; trustworthy observations are
only produced by the actual preparation/publication functions.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_hsp_site_inputs import extract_blast_hsp_columns
from gene_annotation_episode.blast_hsp_site_calculators import calculate_blast_hsp_column_components
from gene_annotation_episode.blast_result_views import _original_hsp, blast_hsp_facts, read_blast_hsp
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.native_blast_hsp_views import native_blast_pairwise_hsp
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_blast_pairwise_publication import (
    EXAMPLES, fixture, native_path, prepare, publish, replace_report, selector, values,
)


def example(name, value):
    destination = os.environ.get("EPISODE_NATIVE_BLAST_SITE_EXAMPLES")
    if destination:
        directory = Path(destination)
        directory.mkdir(exist_ok=True, parents=True)
        (directory / (name + ".json")).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def published(tmp_path, label="blastp_gaps_json15", **kwargs):
    case = fixture(tmp_path, label, **kwargs)
    selection = selector()
    prepared = prepare(case, tmp_path / "grading", selection)
    source, publication = publish(case, prepared, selection)
    return {**case, "prepared": prepared, "source": source, "publication": publication}


def read(case, row=None, offset=0, limit=4096):
    row = row or case["publication"]["rows"][0]
    reference = row["observation_ref"]
    return read_blast_hsp(case["store"], reference, offset, limit,
        permitted_inputs=[reference], scope=case["scope"])


def grading(case, result):
    return json.loads(case["store"].get_artifact(result["site_grading_artifact_ref"]))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.parent.name)
def test_all_twenty_retained_native_reports_use_original_publication(tmp_path, path, monkeypatch):
    case = published(tmp_path, path.parent.name)
    try:
        before = {kind: case["store"].count(kind) for kind in ("source", "observation")}
        examples = []
        for row in case["publication"]["rows"]:
            assert row["status"] == "published", row
            result = read(case, row)
            envelope = grading(case, result)
            sheet, scores = envelope["grading"]["sheet"], envelope["grading"]["scores"]
            assert result["site_grading_failure"] is None
            assert "native_blast" not in result
            assert result["native_blast_pairwise"] == case["store"].get(row["observation_ref"])["native_blast_pairwise"]
            assert envelope["native_artifact_ref"] == case["capture"]["bundle_artifact_ref"]
            artifact = next(item for item in case["capture"]["artifacts"]
                if item["relative_path"] == row["search_key"]["artifact_key"])
            assert sheet["source"]["native_artifact_ref"] == artifact["artifact_ref"]
            expected_format = "native_blast_json_hsp" if artifact["format"] == "json15" else "native_blast_tabular_hsp"
            assert sheet["source"]["format"] == expected_format
            assert sheet["source"]["provider"] == "episode.execution_result"
            assert sheet["source"]["native_version"] != "native_blast_bundle_v1"
            assert sheet["source"]["native_locator"] == {key: row[key] for key in ("search_key", "hit_ordinal", "hsp_ordinal")}
            summary, original = scores["summary"], values(row)
            assert summary["window_alignment_columns"] == original["alignment_columns"]
            assert summary["paired_columns"] == original["paired_positions"]
            assert summary["identical_pairs"] == original["identical_positions"]
            assert summary["query_paired_coverage"] == original["query_paired_coverage"]
            assert summary["reference_paired_coverage"] == original["reference_paired_coverage"]
            assert sheet["inherited_native_measurements"]["native_scores"]["bit_score"] == original["native_score_bits"]
            assert result["column_correspondence"] == [{key: column[key] for key in result["column_correspondence"][0]}
                for column in sheet["columns"][:12]]
            assert result["column_correspondence_count"] == len(sheet["columns"])
            assert blast_hsp_facts(case["store"], [row["observation_ref"]]) == []
            terminal = grading(case, read(case, row, offset=sheet["total_columns"], limit=1))["grading"]
            assert terminal["sheet"]["columns"] == []
            assert terminal["scores"]["summary"]["paired_columns"] == 0
            assert terminal["scores"]["summary"]["paired_identity"] is None
            assert terminal["scores"]["ratios"]["query_paired_coverage"]["denominator"] == original["query_length"]
            examples.append({"original_row": row, "result": result, "sheet": sheet, "scores": scores,
                             "empty_terminal": terminal})
        assert {kind: case["store"].count(kind) for kind in before} == before
        if not examples:
            collection = json.loads(case["store"].get_artifact(case["prepared"]["sheet_artifact_ref"]))["collection"]
            assert all(search["normalized"]["hits"] == [] for search in collection["searches"])
            assert case["store"].count("observation") == 0
        example(path.parent.name, {"input_kind": "retained_actual_native_report",
            "original_manifest": str(path.parent / "attempt/bundle.json"),
            "prepared": case["prepared"], "publication": case["publication"], "windows": examples})
        def forbidden(*args, **kwargs):
            pytest.fail("Saved site calculation performed I/O or execution")
        with monkeypatch.context() as isolated:
            isolated.setattr(Path, "open", forbidden)
            isolated.setattr(socket, "socket", forbidden)
            isolated.setattr(subprocess, "Popen", forbidden)
            for item in examples:
                assert calculate_blast_hsp_column_components(item["sheet"]) == item["scores"]
    finally:
        case["store"].close()


@pytest.fixture(scope="module")
def gap_case(tmp_path_factory):
    case = published(tmp_path_factory.mktemp("native-gap-custody"))
    yield case
    case["store"].close()


def test_host_helper_has_exact_read_only_port_and_selected_gap_numbers(gap_case, monkeypatch):
    case, row = gap_case, gap_case["publication"]["rows"][0]
    observation = case["store"].get(row["observation_ref"])
    before = list(case["store"].db.iterdump())
    def forbidden(*args, **kwargs):
        pytest.fail("Host HSP validation attempted publication, worker, calculator or execution")
    with monkeypatch.context() as isolated:
        for target in ("native_blast_result_worker.run", "blast_report_collection.parse_blast_report_collection",
            "blast_pairwise_results.calculate_blast_pairwise_components",
            "blast_pairwise_results.populate_blast_pairwise_sheet",
            "blast_hsp_site_calculators.calculate_blast_hsp_column_components"):
            isolated.setattr("gene_annotation_episode." + target, forbidden)
        isolated.setattr(case["store"], "put", forbidden)
        isolated.setattr(case["store"], "artifact", forbidden)
        isolated.setattr(socket, "socket", forbidden)
        isolated.setattr(subprocess, "Popen", forbidden)
        bound = native_blast_pairwise_hsp(case["store"], observation)
        assert set(bound) == {"native_hsp", "source", "reference", "source_descriptor", "program",
                             "query_length", "reference_length"}
    assert list(case["store"].db.iterdump()) == before
    full = grading(case, read(case))["grading"]
    gap = next(row["column"] for row in full["sheet"]["columns"] if row["relationship"] == "reference_gap")
    selected = grading(case, read(case, offset=gap - 1, limit=12))["grading"]
    summary = selected["scores"]["summary"]
    assert summary["window_alignment_columns"] == 12
    assert summary["reference_gap_columns"] == 10
    assert summary["paired_columns"] == 2
    assert selected["scores"]["ratios"]["query_paired_coverage"] == {"numerator": 2, "denominator": 253, "value": 2/253}
    assert selected["sheet"]["inherited_native_measurements"] == full["sheet"]["inherited_native_measurements"]
    example("selected_gap_window", selected)


def test_received_identity_and_complete_query_footprint_are_required(gap_case):
    case, ref = gap_case, gap_case["publication"]["rows"][0]["observation_ref"]
    with pytest.raises(ContractError, match="input_not_received"):
        read_blast_hsp(case["store"], ref, 0, 1, permitted_inputs=[], scope=case["scope"])
    scope = deepcopy(case["scope"])
    scope["segments"] = [{"target_ref": case["subject"], "start": 1, "end": 253, "unit": "aa"}]
    with pytest.raises(ContractError, match="outside_assigned_scope"):
        read_blast_hsp(case["store"], ref, 0, 1, permitted_inputs=[ref], scope=scope)
    with pytest.raises(ContractError, match="window_out_of_bounds"):
        read(case, offset=254, limit=1)


@pytest.mark.parametrize("fault", ["measurement", "extra_measurement", "interval", "row", "hsp", "search"])
def test_changed_observation_with_new_hash_cannot_replace_original_publication(gap_case, fault):
    case = gap_case
    original = case["store"].get(case["publication"]["rows"][0]["observation_ref"])
    payload = {key: deepcopy(value) for key, value in original.items() if key not in {"id", "record_type", "origin"}}
    if fault == "measurement":
        payload["measurements"][0]["value"]["value"] += 1
    elif fault == "extra_measurement":
        payload["measurements"].append({"name": "bitscore", "value": {"type": "number", "value": 3, "unit_ref": None}})
    elif fault == "interval":
        payload["operand_intervals"][0]["start"] += 1
    elif fault == "row":
        payload["native_blast_pairwise"]["record_key"] += "0"
    elif fault == "hsp":
        payload["native_blast_pairwise"]["hsp_ordinal"] += 1
    else:
        payload["native_blast_pairwise"]["search_key"]["search_pointer"] += "/0"
    forged = case["store"].put("observation", payload, origin="tool", scope=case["scope"])
    with pytest.raises(ContractError, match="(frozen_observation|complete_row_identity)_conflict"):
        native_blast_pairwise_hsp(case["store"], forged)


@pytest.mark.parametrize("operand", ["query", "reference"])
def test_same_length_wrong_operand_never_produces_a_trustworthy_hsp(tmp_path, operand):
    case = published(tmp_path, **{"wrong_" + operand: True})
    try:
        assert case["publication"]["rows"][0]["status"] == "invalid"
        assert case["publication"]["rows"][0]["observation_ref"] is None
        assert case["store"].count("observation") == 0
    finally:
        case["store"].close()


def test_original_ordinals_survive_synthetic_invalid_hsp_sibling(tmp_path):
    def change(bundle, overrides):
        raw = json.loads((native_path().parent / "attempt/report.json").read_bytes())
        raw["BlastOutput2"][0]["report"]["results"]["bl2seq"][0]["hits"][0]["hsps"].insert(0, "synthetic invalid sibling")
        replace_report(bundle, overrides, json.dumps(raw).encode())
    case = published(tmp_path, transform=change)
    try:
        rows = case["publication"]["rows"]
        assert [row["status"] for row in rows] == ["invalid", "published"]
        result = read(case, rows[1])
        assert result["native_blast_pairwise"]["hsp_ordinal"] == 1
        assert grading(case, result)["grading"]["scores"]["summary"]["identical_pairs"] == 238
    finally:
        case["store"].close()


@pytest.mark.parametrize("fault", ["strings_absent", "one_string_missing", "geometry", "midline"])
def test_synthetic_partial_native_inputs_preserve_independent_fields(gap_case, fault):
    base = grading(gap_case, read(gap_case))["grading"]["sheet"]
    native = deepcopy(base["native_input"])
    if fault == "strings_absent":
        native.pop("qseq"); native.pop("hseq")
    elif fault == "one_string_missing":
        native.pop("qseq")
    elif fault == "geometry":
        native["query_to"] -= 1
    else:
        native["midline"] = "short"
    sheet = extract_blast_hsp_columns(native, program=base["program"], query_length=253,
        reference_length=243, column_offset=0, column_limit=12, operands=base["operands"],
        source=base["source"], original_mappings=base["original_mapping_inputs"])
    scores = calculate_blast_hsp_column_components(sheet)
    assert sheet["inherited_native_measurements"]["native_scores"]["bit_score"] == 486.878
    assert scores["summary"]["query_paired_coverage"] is None
    if "string" in fault:
        assert sheet["realized_window"] is None and scores["summary"]["paired_columns"] is None
    else:
        assert sheet["realized_window"] == {"column_offset": 0, "column_end": 12}
        assert scores["summary"]["paired_columns"] == 12
    example("synthetic_" + fault, {"input_kind": "explicit_synthetic_fault", "sheet": sheet, "scores": scores})


@pytest.fixture
def native_action(tmp_path, gap_case):
    from test_alignment_site_action_records import setup_case, saved_context, requested
    destination = tmp_path / "state"
    shutil.copytree(gap_case["store"].path, destination)
    with Store(destination) as store:
        case = setup_case(store, ToolRegistry(store))
        case.alignment = gap_case["publication"]["rows"][0]["observation_ref"]
        case.context = saved_context(case, requested("blast_hsp_column_rows",
            "matching_alignment_window", alignment=case.alignment,
            window={"column_offset": 2, "column_limit": 4}))
        yield case


def test_native_action_keeps_bundle_envelope_report_descriptor_and_receipt_order(native_action, monkeypatch):
    from test_alignment_site_action_records import blast_read, page, project
    case = native_action
    case.receipts.receive(case.context.episode_id, [case.alignment], kind="initial")
    before = case.store.count("observation")
    outcome = blast_read(case, case.context)
    def forbidden(*args, **kwargs):
        pytest.fail("Own-action projection recalculated a saved site")
    monkeypatch.setattr("gene_annotation_episode.blast_hsp_site_calculators.calculate_blast_hsp_column_components", forbidden)
    row, = page(case, case.context, "blast_hsp_column_rows")["records"]
    source = case.store.get(case.store.get(case.alignment)["source_ref"])
    assert row["binding"]["native_artifact_ref"] != source["artifact_ref"]
    assert row["grading"]["sheet"]["source"]["native_artifact_ref"] == row["binding"]["native_artifact_ref"]
    group, = project(case, case.context, "blast_hsp_column_rows")
    assert group["components"]["paired_columns"] == 4
    assert group["rows"][0]["column"] == 2
    assert outcome["record_refs"] == [] and case.store.count("observation") == before


@pytest.mark.parametrize("receipt_index,accepted", [(2, True), (3, False), (4, False)])
def test_native_action_requires_received_hsp_before_own_action(native_action, receipt_index, accepted):
    from test_alignment_site_action_records import blast_read, page
    case = native_action
    blast_read(case, case.context, index=3)
    case.receipts.receive(case.context.episode_id, [case.alignment], kind="child_form", source_index=receipt_index)
    if accepted:
        assert len(page(case, case.context, "blast_hsp_column_rows")["records"]) == 1
    else:
        with pytest.raises(ValueError, match="original_hsp_receipt_required"):
            page(case, case.context, "blast_hsp_column_rows")


@pytest.mark.parametrize("fault", ["api_marker", "native_marker", "report_as_bundle", "bundle_as_report",
                                  "window", "native_locator", "program"])
def test_native_own_action_rejects_foreign_markers_and_artifact_roles(native_action, fault):
    from test_alignment_site_action_records import blast_read, page, change_outcome, change_grading
    from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading
    case = native_action
    case.receipts.receive(case.context.episode_id, [case.alignment], kind="initial")
    blast_read(case, case.context)
    if fault in {"api_marker", "native_marker", "report_as_bundle"}:
        def alter(outcome):
            result = outcome["result"]
            if fault == "api_marker":
                result["native_blast"] = result.pop("native_blast_pairwise")
            elif fault == "native_marker":
                result["native_blast_pairwise"]["hsp_ordinal"] += 1
            else:
                envelope = json.loads(case.store.get_artifact(result["site_grading_artifact_ref"]))
                result["site_grading_artifact_ref"] = retain_tool_grading(case.store,
                    provider=envelope["provider"],
                    native_artifact_ref=envelope["grading"]["sheet"]["source"]["native_artifact_ref"],
                    grading=envelope["grading"])
        change_outcome(case, case.context, 3, alter)
    else:
        def alter(grading):
            sheet = grading["sheet"]
            if fault == "bundle_as_report":
                sheet["source"]["native_artifact_ref"] = case.store.get(
                    case.store.get(case.alignment)["source_ref"])["artifact_ref"]
            elif fault == "window":
                sheet["requested_window"]["column_limit"] += 1
            elif fault == "native_locator":
                sheet["source"]["native_locator"]["search_key"]["search_pointer"] += "/0"
            else:
                sheet["program"] = "blastn"
        change_grading(case, case.context, 3, "blast_hsp_column_rows", alter)
    with pytest.raises(ValueError, match="(native_hsp_.*conflict|grading_custody_conflict|sheet_.*conflict)"):
        page(case, case.context, "blast_hsp_column_rows")


def test_saved_native_format_selects_exact_reverse_translated_convention(gap_case):
    source = deepcopy(grading(gap_case, read(gap_case))["grading"]["sheet"]["source"])
    operands = {"query": {"subject_ref": "synthetic_query", "length": 9, "unit": "nt",
        "alignment_unit": "aa", "molecule": "dna"},
        "reference": {"subject_ref": "synthetic_reference", "length": 2, "unit": "aa",
            "alignment_unit": "aa", "molecule": "protein"}}
    native = {"query_from": 2, "query_to": 7, "query_frame": -3,
        "hit_from": 1, "hit_to": 2, "qseq": "MK", "hseq": "MK",
        "identity": 2, "align_len": 2, "gaps": 0, "bit_score": 11.125}
    def extract(native, source):
        return extract_blast_hsp_columns(native, program="blastx", query_length=9,
            reference_length=2, column_offset=0, column_limit=2, operands=operands, source=source)
    json_sheet = extract(native, source)
    assert json_sheet["availability"]["geometry"] == "available"
    assert [row["query_interval"] for row in json_sheet["columns"]] == [[4, 7], [1, 4]]
    table_source = {**source, "format": "native_blast_tabular_hsp"}
    table_sheet = extract({**native, "query_from": 7, "query_to": 2}, table_source)
    assert table_sheet["columns"] == json_sheet["columns"]
    assert calculate_blast_hsp_column_components(table_sheet) == calculate_blast_hsp_column_components(json_sheet)
    conflicting = extract(native, table_source)
    assert conflicting["availability"]["geometry"] == "incompatible"
    assert calculate_blast_hsp_column_components(conflicting)["summary"]["paired_columns"] == 2
    assert calculate_blast_hsp_column_components(conflicting)["summary"]["query_paired_coverage"] is None
    changed = deepcopy(json_sheet)
    changed["source"] = table_source
    with pytest.raises(ValueError, match="blast_hsp_column_sheet_conflict"):
        calculate_blast_hsp_column_components(changed)
    example("synthetic_format_conventions", {"input_kind": "explicit_synthetic_coordinate_fixture",
        "json": json_sheet, "table": table_sheet, "wrong_format_geometry": conflicting})


@pytest.mark.parametrize("fault", ["provider", "format", "api_locator", "negative_hsp",
                                  "report_bool", "member_bool", "empty_pointer"])
def test_native_source_format_and_exact_locator_validation(gap_case, fault):
    sheet = deepcopy(grading(gap_case, read(gap_case))["grading"]["sheet"])
    source, locator = sheet["source"], sheet["source"]["native_locator"]
    if fault == "provider":
        source["provider"] = "ncbi_blast"
    elif fault == "format":
        source["format"] = "native_blast_bundle_v1"
    elif fault == "api_locator":
        source["native_locator"] = {"report_ordinal": 0, "hit_ordinal": 0, "hsp_ordinal": 0}
    elif fault == "negative_hsp":
        locator["hsp_ordinal"] = -1
    elif fault == "report_bool":
        locator["search_key"]["report_index"] = True
    elif fault == "member_bool":
        locator["search_key"]["member_ordinal"] = False
    else:
        locator["search_key"]["search_pointer"] = ""
    with pytest.raises(ValueError, match="site_source(_locator)?_invalid"):
        calculate_blast_hsp_column_components(sheet)
