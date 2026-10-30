"""Labelled supplied-data controls and an opt-in genuine original-source oracle.

Fixtures below are synthetic measurements, never claimed to be native output.
The explicitly selected oracle alone executes the pinned source with real Bio.
"""
from collections import namedtuple
from copy import deepcopy
import ast
import builtins
import contextlib
import hashlib
import io
from itertools import product
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.orf_measurements import (
    NATIVE_SCHEMA, build_orf_sheet, calculate_orf_components,
)
from gene_annotation_episode.sequence_mapping import VERSION


def supplied_table():
    # Explicit standard-code test reference in T,C,A,G lexical codon order.
    symbols = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
    entries = dict(zip(("".join(c) for c in product("TCAG", repeat=3)), symbols))
    return {"code": 1, "names": ["Standard"], "start_codons": ["TTG", "CTG", "ATG"],
        "stop_codons": ["TAA", "TAG", "TGA"],
        "forward_table": {k: v for k, v in entries.items() if v != "*"},
        "biopython_version": "labelled-synthetic-fixture"}


def native_fixture(rows, *, outcome="completed", summary=None):
    return {"schema": NATIVE_SCHEMA, "outcome": outcome,
        "result": {"orfs": deepcopy(rows), "summary_stats": summary or {
            "total_orfs": 2, "forward_orfs": 2, "reverse_orfs": 0, "avg_length": 9.0},
            "explanation": "labelled synthetic supplied-output control"},
        "failure": None,
        "source_identity": {"path": "labelled-synthetic-fixture", "callable": "annotate_open_reading_frames", "sha256": "0" * 64},
        "biopython_version": "labelled-synthetic-fixture",
        "translation": {"table": "Standard", "to_stop": True, "cds": False}}


ROWS = [["ATGAAAATGTAA", "MKM", 0, 12, "+", 1], ["ATGTAA", "M", 6, 12, "+", 1]]


def operands(sequence="ATGAAAATGTAA", **request):
    return {"input_sequence": sequence, "subject_ref": "supplied:whole-dna",
        "parent_mapping": {"version": VERSION, "units_per_symbol": 1, "symbol_length": len(sequence),
            "path": [{"subject_ref": "source:original", "start": 100, "end": 100 + len(sequence), "unit": "nt", "strand": "+"}]},
        "request": {"min_length": 6, "search_reverse": False, "filter_subsets": False, **request},
        "genetic_code": supplied_table()}


def components(native=None, **parameters):
    native = native_fixture(ROWS) if native is None else native
    return calculate_orf_components(build_orf_sheet(native, **(parameters or operands())))


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def test_independent_nested_orf_lengths_counts_mean_and_exact_source_paths():
    native, args = native_fixture(ROWS), operands()
    before = deepcopy((native, args))
    sheet = build_orf_sheet(native, **args)
    result = calculate_orf_components(sheet)
    assert (native, args) == before
    assert result["status"] == "complete"
    assert result["summary"] == {"input_length_nt": 12, "reported_row_count": 2,
        "usable_saved_row_count": 2, "forward_row_count": 2, "reverse_row_count": 0,
        "strand_known_row_count": 2, "retained_length_sum_nt": 18,
        "retained_length_denominator_rows": 2, "mean_retained_orf_length_nt": 9,
        "source_definition_compatible_row_count": 2, "translation_compatible_row_count": 2}
    first, second = result["rows"]
    assert first["translation"]["termination_codon_index"] == 3
    assert first["translation"]["termination_codon"] == "TAA"
    assert first["translation"]["untranslated_suffix_nt"] == 0
    assert first["protein_source_path"] == [{"subject_ref": "source:original", "start": 100, "end": 109, "unit": "nt", "strand": "+"}]
    assert second["omitted_stop_source_path"] == [{"subject_ref": "source:original", "start": 109, "end": 112, "unit": "nt", "strand": "+"}]
    assert result["native_summary_comparisons"]["avg_length"]["difference"] == 0
    assert "confidence" not in result and "score" not in result


def test_actual_filter_choice_is_not_reapplied_or_used_to_delete_supplied_rows():
    selected = native_fixture(ROWS[:1], summary={"total_orfs": 1, "forward_orfs": 1, "reverse_orfs": 0, "avg_length": 12.0})
    result = components(selected, **operands(filter_subsets=True))
    assert result["summary"]["reported_row_count"] == 1
    assert result["summary"]["mean_retained_orf_length_nt"] == 12
    conflicting = components(**operands(filter_subsets=True))
    assert "orf_source_subset_filter_conflict" in codes(conflicting)
    assert len(conflicting["rows"]) == 2


def test_reverse_frames_use_the_complete_input_and_preserve_split_source_order():
    rows = [["ATGAAAATGTAA", "MKM", 0, 12, "-", -1], ["ATGTAA", "M", 0, 6, "-", -1]]
    native = native_fixture(rows, summary={"total_orfs": 2, "forward_orfs": 0, "reverse_orfs": 2, "avg_length": 9.0})
    args = operands("TTACATTTTCAT", search_reverse=True)
    args["parent_mapping"]["path"] = [
        {"subject_ref": "source:a", "start": 20, "end": 24, "unit": "nt", "strand": "+"},
        {"subject_ref": "source:b", "start": 50, "end": 58, "unit": "nt", "strand": "-"}]
    result = components(native, **args)
    assert result["status"] == "complete"
    assert result["rows"][0]["frame"] == -1
    assert result["rows"][0]["protein_source_path"] == [
        {"subject_ref": "source:b", "start": 50, "end": 58, "unit": "nt", "strand": "+"},
        {"subject_ref": "source:a", "start": 23, "end": 24, "unit": "nt", "strand": "-"}]
    assert result["rows"][1]["omitted_stop_source_path"] == [
        {"subject_ref": "source:a", "start": 20, "end": 23, "unit": "nt", "strand": "-"}]


def test_ambiguity_stop_preserves_long_nt_orf_short_actual_protein_and_untranslated_suffix():
    native = native_fixture([["ATGTARTAA", "M", 0, 9, "+", 1]],
        summary={"total_orfs": 1, "forward_orfs": 1, "reverse_orfs": 0, "avg_length": 9.0})
    result = components(native, **operands("ATGTARTAA"))
    row = result["rows"][0]
    assert row["native_row"] == ["ATGTARTAA", "M", 0, 9, "+", 1]
    assert row["source_definition"] == row["translation"]["state"] == "compatible"
    assert row["nucleotide_symbol_count"] == 9 and row["protein_symbol_count"] == 1
    assert row["translation"]["termination_codon_index"] == 1
    assert row["translation"]["termination_codon"] == "TAR"
    assert row["translation"]["early_ambiguity_termination"] is True
    assert row["translation"]["untranslated_suffix_nt"] == 3
    assert row["translation"]["omitted_stop_codon_count"] == 1
    assert "orf_translation_terminates_before_literal_orf_stop" in codes(result)
    assert row["protein_source_path"][0]["end"] == 103
    assert row["omitted_stop_source_path"][0]["start"] == 103


def test_threshold_equality_and_stable_ties_are_checked_without_sorting_or_enumerating():
    rows = [["ATGTAA", "M", 0, 6, "+", 1], ["ATGTGA", "M", 6, 12, "+", 1]]
    native = native_fixture(rows, summary={"total_orfs": 2, "forward_orfs": 2, "reverse_orfs": 0, "avg_length": 6.0})
    result = components(native, **operands("ATGTAAATGTGA"))
    assert result["status"] == "complete"
    native["result"]["orfs"].reverse()
    reversed_result = components(native, **operands("ATGTAAATGTGA"))
    assert "orf_source_order_conflict" in codes(reversed_result)
    assert reversed_result["rows"][0]["interval"] == [6, 12]
    too_short = components(native, **operands("ATGTAAATGTGA", min_length=7))
    assert too_short["summary"]["source_definition_compatible_row_count"] == 0
    # Deliberately omitted native rows are not re-enumerated by the reader.
    native["result"]["orfs"] = rows[:1]
    omitted = components(native, **operands("ATGTAAATGTGA"))
    assert len(omitted["rows"]) == 1
    assert "orf_native_summary_conflicts_with_retained_rows" in codes(omitted)


def test_completed_empty_has_zero_counts_null_mean_and_native_zero_convention_separate():
    native = native_fixture([], summary={"total_orfs": 0, "forward_orfs": 0, "reverse_orfs": 0, "avg_length": 0})
    result = components(native, **operands("CCCCCCCCCCCC"))
    assert result["summary"]["reported_row_count"] == 0
    assert result["summary"]["retained_length_sum_nt"] == 0
    assert result["summary"]["retained_length_denominator_rows"] == 0
    assert result["summary"]["mean_retained_orf_length_nt"] is None
    assert result["native_summary_comparisons"]["avg_length"] == {
        "native_value": 0, "retained_population_value": 0, "difference": 0}


@pytest.mark.parametrize("outcome", ["failed", "truncated", "partial"])
def test_failure_and_truncation_keep_retained_partial_work_without_claiming_a_complete_population(outcome):
    native = native_fixture(ROWS, outcome=outcome)
    native["failure"] = {"exception_type": "labelled-control", "message": "not a native claim"} if outcome == "failed" else None
    result = components(native, **operands())
    assert result["native_outcome"] == outcome
    assert result["summary"]["reported_row_count"] == 2
    assert "orf_native_population_" + outcome in codes(result)
    native["result"] = None
    unavailable = components(native, **operands())
    assert unavailable["summary"]["reported_row_count"] is None
    assert unavailable["summary"]["forward_row_count"] is None
    assert unavailable["summary"]["retained_length_sum_nt"] is None
    assert unavailable["summary"]["mean_retained_orf_length_nt"] is None


@pytest.mark.parametrize("damage", ["snapshot", "version", "settings"])
def test_missing_observed_translation_reference_retains_independent_lengths_without_protein_mapping(damage):
    native, args = native_fixture(ROWS), operands()
    if damage == "snapshot":
        args["genetic_code"] = None
    elif damage == "version":
        native.pop("biopython_version")
    else:
        native["translation"]["cds"] = True
    result = components(native, **args)
    assert result["summary"]["mean_retained_orf_length_nt"] == 9
    assert result["rows"][0]["protein_symbol_count"] == 3
    assert result["rows"][0]["translation"]["state"] == "unknown"
    assert result["rows"][0]["protein_source_path"] is None
    assert result["rows"][0]["omitted_stop_source_path"] is None


@pytest.mark.parametrize("replacement,code", [
    (["ATGAAAATGTAA", "MKM", False, 12, "+", 1], "orf_interval_outside_full_input_or_missing"),
    (["ATGAAAATGTAA", "QQQ", 0, 12, "+", 1], "orf_translation_incompatible"),
    (["ATGAAAATGTAA", "MKM", 0, 12, "+", -1], "orf_source_definition_or_input_conflict"),
    (["ATGTAGATGTAA", "M*M", 0, 12, "+", 1], "orf_source_definition_or_input_conflict"),
    (["only-five", "M", 0, 12, "+"], "orf_native_row_fields_required"),
])
def test_malformed_source_rows_keep_other_usable_rows(replacement, code):
    native = native_fixture([replacement, ROWS[1]])
    result = components(native, **operands())
    assert code in codes(result)
    assert result["rows"][1]["translation"]["state"] == "compatible"
    assert result["rows"][1]["protein_source_path"][0]["start"] == 106


def test_nonfinite_component_is_recorded_as_rejected_not_missing_zero_and_does_not_erase_other_rows():
    native = native_fixture([ROWS[0], ["ATGTAA", "M", float("nan"), 12, "+", 1]])
    sheet = build_orf_sheet(native, **operands())
    assert sheet["inputs"]["native_record"]["result"]["orfs"][1][2] is None
    assert sheet["rejected_values"] == [{"path": "/native_record/result/orfs/1/2", "value_type": "float", "nonfinite_token": "nan"}]
    result = calculate_orf_components(json.loads(json.dumps(sheet, allow_nan=False)))
    assert "orf_non_json_value_rejected" in codes(result)
    assert result["rows"][0]["translation"]["state"] == "compatible"
    assert result["rows"][1]["interval"] is None
    assert result["rows"][1]["protein_symbol_count"] == 1


def test_native_version_and_reference_conflict_does_not_inject_installed_version():
    native, args = native_fixture(ROWS), operands()
    args["genetic_code"]["biopython_version"] = "another-reference-version"
    sheet = build_orf_sheet(native, **args)
    result = calculate_orf_components(sheet)
    assert sheet["inputs"]["native_record"]["biopython_version"] == "labelled-synthetic-fixture"
    assert "genetic_code_version_conflict" in codes(result)
    assert result["rows"][0]["protein_source_path"] is None
    assert result["summary"]["retained_length_sum_nt"] == 18


def test_partial_frozen_reference_keeps_independently_compatible_orf_and_never_fills_missing_codon():
    args = operands()
    del args["genetic_code"]["forward_table"]["AAA"]
    result = components(native_fixture(ROWS), **args)
    assert result["rows"][0]["translation"]["state"] == "unknown"
    assert result["rows"][0]["protein_symbol_count"] == 3
    assert result["rows"][0]["protein_source_path"] is None
    assert result["rows"][1]["translation"]["state"] == "compatible"
    assert result["rows"][1]["protein_source_path"][0]["start"] == 106
    assert result["summary"]["retained_length_sum_nt"] == 18


def test_saved_corruption_is_unavailable_and_other_saved_rows_still_calculate():
    sheet = build_orf_sheet(native_fixture(ROWS), **operands())
    sheet["rows"][0]["protein_source_path"][0]["subject_ref"] = "unrelated:source"
    sheet["measurements"]["input_length_nt"] = 999
    result = calculate_orf_components(sheet)
    assert result["rows"][0]["state"] == "incompatible"
    assert result["rows"][0]["saved_row"]["protein_source_path"][0]["subject_ref"] == "unrelated:source"
    assert result["rows"][1]["interval"] == [6, 12]
    assert result["summary"]["input_length_nt"] is None
    assert result["summary"]["mean_retained_orf_length_nt"] == 6
    assert result["summary"]["retained_length_denominator_rows"] == 1


def test_json_saved_recalculation_needs_no_imports_io_native_or_network(monkeypatch):
    sheet = build_orf_sheet(native_fixture(ROWS), **operands())
    expected = calculate_orf_components(sheet)
    saved = json.loads(json.dumps(sheet, sort_keys=True))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved ORF calculation attempted external work")
    for owner, name in ((builtins, "open"), (io, "open"), (Path, "read_text"), (Path, "read_bytes"),
                        (socket, "socket"), (subprocess, "Popen"), (builtins, "__import__")):
        monkeypatch.setattr(owner, name, forbidden)
    assert calculate_orf_components(saved) == expected
    assert saved == before


@pytest.mark.skipif(os.environ.get("HMMER_NATIVE_ORACLE_ORF") != "1", reason="explicit bounded original-source oracle only")
def test_selected_pinned_original_orf_callable_retains_full_outputs_and_real_errors(tmp_path):
    from Bio.Data import CodonTable
    from Bio.Seq import Seq
    from importlib.metadata import version

    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    source_path = Path(os.environ.get("HMMER_NATIVE_ORACLE_ORF_SOURCE", str(Path(__file__).resolve().parents[1]
        / "reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/molecular_biology.py")))
    source = source_path.read_bytes()
    module = ast.parse(source, filename=str(source_path))
    selected = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "annotate_open_reading_frames"]
    assert len(selected) == 1
    target = selected[0]
    definition = ast.get_source_segment(source.decode(), target).encode()
    pin = hashlib.sha256(definition).hexdigest()
    assert pin == "bc32fff2924e09ec940f6d9b8d74732a8ef86d0894761430a3ad57ea7148269b"
    namespace = {"Seq": Seq, "namedtuple": namedtuple}
    exec(compile(ast.Module(body=[target], type_ignores=[]), str(source_path), "exec"), namespace)
    original = namespace["annotate_open_reading_frames"]
    installed = version("biopython")
    table = CodonTable.unambiguous_dna_by_id[1]
    snapshot = {"code": 1, "names": list(table.names), "start_codons": list(table.start_codons),
        "stop_codons": list(table.stop_codons), "forward_table": dict(table.forward_table), "biopython_version": installed}
    cases = [("nested", "ATGAAAATGTAA", False, False), ("subset", "ATGAAAATGTAA", False, True),
        ("reverse", "TTACATTTTCAT", True, False), ("ambiguous_stop", "ATGTARTAA", False, False),
        ("translation_error", "ATG?AATAA", False, False)]
    capture = {"schema": "orf_original_source_oracle_v1", "source_path": str(source_path),
        "source_sha256": hashlib.sha256(source).hexdigest(), "callable_sha256": pin,
        "biopython_version": installed, "cases": []}
    for name, dna, reverse, subsets in cases:
        stdout, stderr = io.StringIO(), io.StringIO()
        record = {"schema": NATIVE_SCHEMA, "outcome": "completed", "result": None, "failure": None,
            "source_identity": {"path": str(source_path), "callable": "annotate_open_reading_frames", "sha256": pin},
            "biopython_version": installed, "translation": {"table": "Standard", "to_stop": True, "cds": False}}
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                record["result"] = json.loads(json.dumps(original(dna, 6, search_reverse=reverse, filter_subsets=subsets)))
            except Exception as error:
                record.update(outcome="failed", failure={"exception_type": type(error).__name__, "message": str(error)})
        args = operands(dna, search_reverse=reverse, filter_subsets=subsets)
        args["genetic_code"] = snapshot
        sheet = build_orf_sheet(record, **args)
        calculated = calculate_orf_components(sheet)
        capture["cases"].append({"case": name, "full_input": dna, "request": args["request"],
            "native_record": record, "stdout": stdout.getvalue(), "stderr": stderr.getvalue(),
            "sheet": sheet, "components": calculated})
    output = attempt / "orf-original-source-oracle.json"
    output.write_text(json.dumps(capture, allow_nan=False, indent=2))
    by_name = {row["case"]: row for row in capture["cases"]}
    assert by_name["nested"]["native_record"]["result"]["orfs"] == ROWS
    assert by_name["nested"]["components"]["summary"]["mean_retained_orf_length_nt"] == 9
    assert by_name["subset"]["native_record"]["result"]["orfs"] == ROWS[:1]
    assert by_name["reverse"]["components"]["summary"]["reverse_row_count"] == 2
    ambiguous = by_name["ambiguous_stop"]
    assert ambiguous["native_record"]["result"]["orfs"] == [["ATGTARTAA", "M", 0, 9, "+", 1]]
    assert ambiguous["components"]["rows"][0]["translation"]["state"] == "compatible"
    assert ambiguous["components"]["rows"][0]["translation"]["untranslated_suffix_nt"] == 3
    error = by_name["translation_error"]
    assert error["native_record"]["outcome"] == "failed"
    assert error["native_record"]["failure"]["exception_type"] == "TranslationError"
    assert error["native_record"]["result"] is None
    assert error["components"]["summary"]["reported_row_count"] is None
