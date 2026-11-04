"""Retained BLAST+ 2.17.0 coordinate evidence and labeled synthetic edge cases.

No searches run here. Database/Homology envelopes below are test projections of
actual paired measurements, not claims of executed database or BV-BRC jobs.
"""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.blast_database_grader import build_database_sheet, calculate_database_probabilities
from gene_annotation_episode.blast_hsp_site_calculators import calculate_blast_hsp_column_components
from gene_annotation_episode.blast_hsp_site_inputs import extract_blast_hsp_columns
from gene_annotation_episode.blast_pairwise_grader import _axis_geometry, alignment_components, blast_hsp_column_correspondence, build_pairwise_sheet
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_search import PROGRAM_UNITS
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_alignment_supplements
from gene_annotation_episode.bvbrc_homology_inputs import _table_hsp_agrees


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_blast_pairwise_2026-10-26_294"
CASES = [
    ("native_examples", "blastx_reverse", [239, 242], [0, 1], -1, 1, 240, 80, 80),
    ("native_examples", "tblastn_reverse", [0, 1], [239, 242], 1, -1, 80, 240, 80),
    ("native_examples", "tblastx_frames", [2, 5], [239, 242], 1, -1, 240, 240, 80),
    ("native_examples", "blastp_gaps", [0, 1], [0, 1], 1, 1, 243, 243, 243),
    ("native_ranges", "blastn_reverse", [0, 1], [239, 240], 1, -1, 240, 240, 240),
]


def retained_search(folder, case, fmt):
    """Read original reports using their retained actual format declaration."""
    directory = NATIVE / folder / (case + "_" + fmt)
    plan = json.loads((directory / "plan.json").read_text())
    bundle = json.loads((directory / "attempt/bundle.json").read_text())
    job = plan["requested_job"]["native_blast"]
    program = job["program"]
    operands, lengths = [], {}
    # These selected examples have value-taking option pairs, retained intact.
    options = dict(zip(job["options"][::2], job["options"][1::2]))
    qunit, runit, _ = PROGRAM_UNITS[program]
    for operand, unit in zip(job["operands"], (qunit, runit)):
        role = "query" if operand["role"] == "query_sequence" else "subject"
        lines = (directory / "attempt/inputs" / (operand["role"] + ".fa")).read_text().splitlines()
        title, length = lines[0][1:], len("".join(lines[1:]))
        lengths["query" if role == "query" else "reference"] = length
        selected = options.get("-query_loc" if role == "query" else "-subject_loc")
        interval = [int(selected.split("-")[0]) - 1, int(selected.split("-")[1])] if selected else None
        operands.append({"role": role, "artifact_key": operand["role"], "record_ordinal": 0,
            "native_id": title.split()[0], "native_title": title, "subject_ref": "retained_" + role,
            "molecule": "protein" if unit == "aa" else "dna", "length": length,
            "selected_interval": interval, "identity": None})
    output = next(row for row in job["outputs"] if row["role"] not in ("stdout", "stderr"))
    raw = (directory / "attempt" / output["relative_path"]).read_bytes()
    artifact = {"artifact_key": "report", **{key: output[key] for key in ("role", "format", "fields", "delimiter")}}
    invocation = {"execution_program": program, "scientific_mode": "pairwise", "resource_kind": "local",
        "query_kind": "sequence", "reference_kind": "sequence", "request": plan["requested_job"],
        "effective_options": {**options, "requested_hit_limit": None, "requested_hsp_limit": None},
        "operands": operands, "completion": {"native_returncode": bundle["returncode"],
            "producer_complete": not bundle["failures"]}}
    collection = parse_blast_report_collection({"report": raw}, artifacts=[artifact], invocation=invocation)
    assert not collection["issues"] and len(collection["searches"]) == 1
    search = collection["searches"][0]
    assert search["program_context"]["geometry_program"] == program
    assert not search["issues"]
    return search, lengths


def site_sheet(hsp, program, lengths, *, limit=4096):
    qunit, runit, aunit = PROGRAM_UNITS[program]
    return extract_blast_hsp_columns(hsp, program=program, query_length=lengths["query"],
        reference_length=lengths["reference"], column_offset=0, column_limit=limit,
        operands={role: {"subject_ref": "retained_" + role, "length": lengths[role],
            "unit": unit, "alignment_unit": aunit, "molecule": "protein" if unit == "aa" else "dna"}
            for role, unit in (("query", qunit), ("reference", runit))},
        source={"alignment_ref": "explicit_retained_hsp", "source_ref": "retained_native_report",
            "native_artifact_ref": "retained_native_report", "provider": "ncbi_blast",
            "format": "ncbi_blast_json_hsp", "native_version": "2.17.0+",
            "native_locator": {"report_ordinal": 0, "hit_ordinal": 0, "hsp_ordinal": 0}})


def homology_projection(normalized):
    """Synthetic Homology envelope containing unchanged native measurements."""
    normalized = deepcopy(normalized)
    for hit in normalized["hits"]:
        hit["source_locator"] = {"report_index": 0, "hit_index": hit["hit_index"]}
        for ordinal, hsp in enumerate(hit["hsps"]):
            hsp["source_locator"] = {**hit["source_locator"], "hsp_index": ordinal,
                                     "pointer": f"/hits/{hit['hit_index']}/hsps/{ordinal}"}
    return {"schema": "bvbrc_homology_sheet_v1", "queries": [{"report_index": 0,
        "source_locator": {"report_index": 0}, "query_binding": None,
        "native_tabular_measurements": [], "normalized_result": normalized}]}


@pytest.mark.parametrize("folder,case,qp,rp,qd,rd,qcovered,rcovered,paired", CASES)
def test_actual_native_json_and_tabular_agree_through_all_geometry_consumers(
        folder, case, qp, rp, qd, rd, qcovered, rcovered, paired):
    json_search, lengths = retained_search(folder, case, "json15")
    tab_search, tab_lengths = retained_search(folder, case, "tabular7")
    assert lengths == tab_lengths
    native = deepcopy([json_search, tab_search])
    json_sheet = build_pairwise_sheet(json_search["normalized"])
    tab_sheet = build_pairwise_sheet(tab_search["normalized"])
    assert len(json_sheet["hsps"]) == len(tab_sheet["hsps"])
    for first, second in zip(json_sheet["hsps"], tab_sheet["hsps"]):
        a, b = first["components"], second["components"]
        assert a["geometry_available"] and b["geometry_available"]
        assert a["counts"] == b["counts"] and a["pairs"] == b["pairs"]
        assert a["fractions"] == b["fractions"]
    assert json_sheet["union"] == tab_sheet["union"]
    top = json_sheet["hsps"][0]["components"]
    assert top["counts"]["paired_columns"] == paired
    assert top["counts"]["paired_query_positions"] == qcovered
    assert top["counts"]["paired_reference_positions"] == rcovered
    assert top["fractions"]["query_paired_coverage"] == qcovered / lengths["query"]
    assert top["fractions"]["reference_paired_coverage"] == rcovered / lengths["reference"]
    first = top["pairs"][0]
    assert [first["query_start"], first["query_end"]] == qp
    assert [first["reference_start"], first["reference_end"]] == rp
    for search, paired_sheet in ((json_search, json_sheet), (tab_search, tab_sheet)):
        # This tests the database caller with a synthetic mode envelope; the
        # preserved report remains actual paired output, not a database search.
        projection = deepcopy(search["normalized"])
        projection["mode"] = "database"
        database = build_database_sheet(projection)
        assert database["normalized_result"] == projection
        assert database["hits"][0]["hsp_components"] == [row["components"] for row in paired_sheet["hsps"]]
        supplements = calculate_homology_alignment_supplements(homology_projection(search["normalized"]))
        assert [row["alignment_components"] for row in supplements["queries"][0]["hits"][0]["hsps"]] == [
            row["components"] for row in paired_sheet["hsps"]]
    hsp = json_search["normalized"]["hits"][0]["hsps"][0]
    selected = site_sheet(hsp, json_search["normalized"]["search"]["program"], lengths)
    column = selected["columns"][0]
    assert (column["query_interval"], column["reference_interval"]) == (qp, rp)
    assert (column["query_direction"], column["reference_direction"]) == (qd, rd)
    values = calculate_blast_hsp_column_components(selected)["summary"]
    assert values["paired_columns"] == paired
    assert values["query_paired_units"] == qcovered and values["reference_paired_units"] == rcovered
    assert selected["native_input"] == hsp
    assert [json_search, tab_search] == native


@pytest.mark.parametrize("case,prefix", [("blastx_reverse", "query"), ("tblastn_reverse", "hit")])
def test_native_negative_ascending_bounds_need_explicit_json_convention(case, prefix):
    search, lengths = retained_search("native_examples", case, "json15")
    hsp = search["normalized"]["hits"][0]["hsps"][0]
    before = deepcopy(hsp)
    arguments = dict(program=search["normalized"]["search"]["program"],
                     query_length=lengths["query"], reference_length=lengths["reference"])
    default = alignment_components(hsp, **arguments)
    assert not default["geometry_available"]
    assert {"code": "frame_coordinate_direction_conflict", "operand": prefix} in default["issues"]
    actual = alignment_components(hsp, **arguments, coordinate_convention="blast_json2")
    assert actual["geometry_available"] and actual["counts"]["paired_columns"] == 80
    view = blast_hsp_column_correspondence(hsp, **arguments, coordinate_convention="blast_json2")
    assert view["geometry_status"] == "available"
    assert view["columns"][0][("query" if prefix == "query" else "reference") + "_direction"] == -1
    assert hsp == before
    # A copied declared tabular envelope is deliberately incompatible: resource
    # provenance must not silently select JSON endpoint semantics.
    for resource in ("local", "api", "hpc"):
        projection = deepcopy(search["normalized"])
        projection.update(format="tabular", resource=resource)
        assert not build_pairwise_sheet(projection)["hsps"][0]["components"]["geometry_available"]
        projection["mode"] = "database"
        assert not build_database_sheet(projection)["hits"][0]["hsp_components"][0]["geometry_available"]


def test_synthetic_both_axes_reverse_with_gaps_uses_one_orientation_algorithm():
    hsp = {"query_from": 3, "query_to": 11, "query_frame": -3,
        "hit_from": 4, "hit_to": 12, "hit_frame": -2, "qseq": "M-KG", "hseq": "MA-G",
        "align_len": 4, "identity": 2, "gaps": 2}
    before = deepcopy(hsp)
    view = blast_hsp_column_correspondence(hsp, program="tblastx", query_length=13,
        reference_length=13, coordinate_convention="blast_json2")
    assert [row["query_interval"] for row in view["columns"]] == [[8, 11], None, [5, 8], [2, 5]]
    assert [row["reference_interval"] for row in view["columns"]] == [[9, 12], [6, 9], None, [3, 6]]
    assert all(row["query_direction"] == row["reference_direction"] == -1 for row in view["columns"])
    counts = alignment_components(hsp, program="tblastx", query_length=13,
        reference_length=13, coordinate_convention="blast_json2")
    assert counts["counts"]["paired_query_positions"] == counts["counts"]["paired_reference_positions"] == 6
    assert counts["fractions"]["query_paired_coverage"] == counts["fractions"]["reference_paired_coverage"] == 6 / 13
    descending = {**hsp, "query_from": 11, "query_to": 3, "hit_from": 12, "hit_to": 4}
    for convention in ("directional", "blast_json2"):
        assert alignment_components(descending, program="tblastx", query_length=13,
            reference_length=13, coordinate_convention=convention) == counts
    assert hsp == before


@pytest.mark.parametrize("changes,code", [
    ({"query_frame": -2}, "frame_coordinate_phase_conflict"),
    ({"query_frame": 0}, "invalid_translation_frame"),
    ({"query_frame": -4}, "invalid_translation_frame"),
    ({"query_frame": True}, "invalid_frame"),
    ({"query_frame": "-3"}, "invalid_frame"),
    ({"query_strand": "Plus"}, "strand_coordinate_conflict"),
    ({"query_strand": "unknown"}, "invalid_strand"),
    ({"query_to": 241}, "traceback_coordinate_span_conflict"),
    ({"query_from": 2, "query_to": 241}, "frame_coordinate_phase_conflict"),
    ({"query_from": 242, "query_to": 3, "query_frame": 3}, "frame_coordinate_direction_conflict"),
])
def test_invalid_translated_json_preserves_counts_but_never_positions(changes, code):
    search, lengths = retained_search("native_examples", "blastx_reverse", "json15")
    hsp = {**search["normalized"]["hits"][0]["hsps"][0], **changes}
    before = deepcopy(hsp)
    result = alignment_components(hsp, program="blastx", query_length=244,
        reference_length=80, coordinate_convention="blast_json2")
    assert result["counts"]["paired_columns"] == result["counts"]["identical_pairs"] == 80
    assert not result["geometry_available"] and result["pairs"] == []
    assert code in {row["code"] for row in result["issues"]}
    selected = site_sheet(hsp, "blastx", lengths, limit=2)
    assert selected["measured_counts"]["paired_columns"] == 2
    assert selected["measured_counts"]["query_paired_units"] is None
    assert all(row["query_direction"] is None for row in selected["columns"])
    assert hsp == before


def test_native_selected_query_span_requires_explicit_full_length_and_no_offset():
    search, lengths = retained_search("native_ranges", "blastx_range_reverse", "json15")
    normalized = search["normalized"]
    hsp = normalized["hits"][0]["hsps"][0]
    before = deepcopy(normalized)
    assert normalized["query"]["length"] == 186 and lengths["query"] == 244
    assert not build_pairwise_sheet(normalized)["hsps"][0]["components"]["geometry_available"]
    correct = alignment_components(hsp, program="blastx", query_length=244,
        reference_length=80, coordinate_convention="blast_json2")
    assert correct["geometry_available"] and correct["counts"]["paired_columns"] == 62
    assert correct["pairs"][:2] == [
        {"query_start": 212, "query_end": 215, "reference_start": 9, "reference_end": 10, "identical": True},
        {"query_start": 209, "query_end": 212, "reference_start": 10, "reference_end": 11, "identical": True}]
    assert correct["fractions"]["query_paired_coverage"] == 186 / 244
    assert correct["fractions"]["reference_paired_coverage"] == 62 / 80
    tabular, _ = retained_search("native_ranges", "blastx_range_reverse", "tabular7")
    tab_hsp = tabular["normalized"]["hits"][0]["hsps"][0]
    assert alignment_components(tab_hsp, program="blastx", query_length=244, reference_length=80)["pairs"] == correct["pairs"]
    assert site_sheet(hsp, "blastx", lengths, limit=2)["columns"][0]["query_interval"] == [212, 215]
    phase = alignment_components(hsp, program="blastx", query_length=243,
        reference_length=80, coordinate_convention="blast_json2")
    assert "frame_coordinate_phase_conflict" in {row["code"] for row in phase["issues"]}
    assert normalized == before


@pytest.mark.parametrize("fmt", ["json15", "tabular7"])
def test_native_selected_nucleotide_range_keeps_original_coordinates(fmt):
    search, lengths = retained_search("native_ranges", "blastn_range_forward", fmt)
    normalized = search["normalized"]
    assert normalized["query"]["length"] == 180 and lengths == {"query": 240, "reference": 240}
    hsp = normalized["hits"][0]["hsps"][0]
    before = deepcopy(hsp)
    actual = alignment_components(hsp, program="blastn", query_length=240, reference_length=240,
        coordinate_convention="blast_json2" if fmt == "json15" else "directional")
    assert actual["pairs"][0] == {"query_start": 30, "query_end": 31,
        "reference_start": 30, "reference_end": 31, "identical": True}
    assert actual["pairs"][-1]["query_end"] == 210
    assert actual["counts"]["paired_columns"] == 180
    assert actual["fractions"]["query_paired_coverage"] == actual["fractions"]["reference_paired_coverage"] == .75
    assert hsp == before


def test_missing_length_keeps_json_codons_with_unknown_coverage_and_phase():
    search, _ = retained_search("native_examples", "blastx_reverse", "json15")
    hsp = search["normalized"]["hits"][0]["hsps"][0]
    actual = alignment_components(hsp, program="blastx", query_length=None, reference_length=80,
        coordinate_convention="blast_json2")
    assert actual["geometry_available"] and actual["counts"]["paired_query_positions"] == 240
    assert actual["pairs"][0]["query_start"] == 239
    assert actual["fractions"]["query_paired_coverage"] is None


def test_negative_nt_frame_does_not_override_untranslated_native_strand():
    hsp = {"query_from": 2, "query_to": 4, "query_frame": -1, "query_strand": "Plus",
           "hit_from": 5, "hit_to": 3, "hit_strand": "Minus", "qseq": "ACG", "hseq": "ACG"}
    view = blast_hsp_column_correspondence(hsp, program="blastn", query_length=6, reference_length=6,
        coordinate_convention="blast_json2")
    assert [row["query_interval"] for row in view["columns"]] == [[1, 2], [2, 3], [3, 4]]
    assert [row["reference_interval"] for row in view["columns"]] == [[4, 5], [3, 4], [2, 3]]
    assert all(row["query_direction"] == 1 and row["reference_direction"] == -1 for row in view["columns"])


@pytest.mark.parametrize("case", ["blastx_reverse", "tblastn_reverse", "tblastx_frames"])
def test_actual_table_endpoint_coordinates_agree_with_shared_json_axis_helper(case):
    search, _ = retained_search("native_examples", case, "json15")
    table, _ = retained_search("native_examples", case, "tabular7")
    normalized = search["normalized"]
    qunit, runit, aunit = PROGRAM_UNITS[normalized["search"]["program"]]
    for hsp, native_row in zip(normalized["hits"][0]["hsps"], table["native"]["search"]["rows"]):
        fields = native_row["fields"]
        for prefix, key, unit, length in (("query", "q", qunit, normalized["query"]["length"]),
                                         ("hit", "s", runit, normalized["hits"][0]["length"])):
            issues = []
            axis = _axis_geometry(hsp, prefix=prefix, length=length, coordinate_unit=unit,
                alignment_unit=aunit, issues=issues, coordinate_convention="blast_json2")
            assert not issues and axis[:2] == (int(fields[key + "start"]), int(fields[key + "end"]))


@pytest.mark.parametrize("convention", [None, "json15", "api", "unknown", {}, []])
@pytest.mark.parametrize("calculator", [alignment_components, blast_hsp_column_correspondence])
def test_unsupported_convention_is_an_explicit_caller_error(calculator, convention):
    with pytest.raises(ValueError, match="unsupported_blast_coordinate_convention"):
        calculator({}, program="blastx", query_length=244, reference_length=80,
                   coordinate_convention=convention)


@pytest.mark.parametrize("case", ["blastx_reverse", "tblastn_reverse", "tblastx_frames"])
def test_homology_json_tabular_matching_uses_shared_oriented_endpoints(case):
    search, _ = retained_search("native_examples", case, "json15")
    tabular, _ = retained_search("native_examples", case, "tabular7")
    norm = search["normalized"]
    hit = norm["hits"][0]
    before = deepcopy([search, tabular])
    for hsp, native_row in zip(hit["hsps"], tabular["native"]["search"]["rows"]):
        fields = dict(native_row["fields"])
        # Homology's fixed table exposes percentages and gap opens. Derive only
        # these test adapter fields from actual counts, with declared precision.
        fields["pident"] = f"{100 * hsp['identity'] / hsp['align_len']:.3f}"
        fields["gapopen"] = "0"  # These retained translated HSPs have no gaps.
        assert _table_hsp_agrees(fields, hsp, norm["query"], hit, norm["search"]["program"],
                                  coordinate_convention="blast_json2")
        prefix = "query" if case == "blastx_reverse" else "hit"
        if hsp[prefix + "_frame"] < 0:
            assert not _table_hsp_agrees(fields, hsp, norm["query"], hit, norm["search"]["program"])
            bad = {**hsp, prefix + "_frame": -1 if hsp[prefix + "_frame"] != -1 else -2}
            assert not _table_hsp_agrees(fields, bad, norm["query"], hit, norm["search"]["program"],
                                          coordinate_convention="blast_json2")
            no_traceback = {k: v for k, v in hsp.items() if k not in ("qseq", "hseq", "midline")}
            assert _table_hsp_agrees(fields, no_traceback, norm["query"], hit, norm["search"]["program"],
                                      coordinate_convention="blast_json2")
            no_traceback[prefix + "_frame"] = bad[prefix + "_frame"]
            assert not _table_hsp_agrees(fields, no_traceback, norm["query"], hit, norm["search"]["program"],
                                          coordinate_convention="blast_json2")
    assert [search, tabular] == before


def test_saved_native_sheets_recalculate_without_acquisition_execution_or_mutation(monkeypatch):
    search, lengths = retained_search("native_examples", "blastx_reverse", "json15")
    pair = json.loads(json.dumps(build_pairwise_sheet(search["normalized"])))
    native = pair["input"]["hits"][0]["hsps"][0]
    selected = json.loads(json.dumps(site_sheet(native, "blastx", lengths)))
    projection = deepcopy(pair["input"])
    projection["mode"] = "database"
    database = json.loads(json.dumps(build_database_sheet(projection)))
    homology = json.loads(json.dumps(homology_projection(pair["input"])))
    expected = (calculate_blast_hsp_column_components(selected), calculate_database_probabilities(database),
                calculate_homology_alignment_supplements(homology))
    before = deepcopy([pair, selected, database, homology])
    def forbidden(*args, **kwargs):
        raise AssertionError("saved coordinate calculation attempted external work")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        assert build_pairwise_sheet(pair["input"]) == pair
        assert build_database_sheet(database["normalized_result"]) == database
        assert calculate_blast_hsp_column_components(selected) == expected[0]
        assert calculate_database_probabilities(database) == expected[1]
        assert calculate_homology_alignment_supplements(homology) == expected[2]
    assert [pair, selected, database, homology] == before
