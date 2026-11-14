"""Independent supplied-output controls; genuine source execution is opt-in."""
from copy import deepcopy
import ast
import builtins
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import traceback

import pytest

from gene_annotation_episode.biopython_pairwise_grader import count_literal_alignment_columns
from gene_annotation_episode.primer_placement_measurements import (
    NATIVE_SCHEMA, build_primer_placement_sheet, calculate_primer_placement_components,
)
from gene_annotation_episode.sequence_mapping import VERSION


def mapping(length, reference, start=0, strand="+"):
    return {"version": VERSION, "units_per_symbol": 1, "symbol_length": length,
        "path": [{"subject_ref": reference, "start": start, "end": start + length, "unit": "nt", "strand": strand}]}


def operands(target="AAAACCCCAAAA", primers="AAAA"):
    occurrences = [primers] if type(primers) is str else primers
    return {"target_sequence": target, "primers": deepcopy(primers), "target_ref": "supplied:target",
        "primer_refs": ["supplied:primer:" + str(i) for i in range(len(occurrences))],
        "target_mapping": mapping(len(target), "source:target", 100),
        "primer_mappings": [mapping(len(p), "source:primer:" + str(i), 500) if type(p) is str and p else None for i, p in enumerate(occurrences)]}


def native_fixture(groups, outcome="completed"):
    return {"schema": NATIVE_SCHEMA, "outcome": outcome, "result": {
        "explanation": "labelled synthetic supplied-output control, not a native claim", "sequences": deepcopy(groups)},
        "failure": {"exception_type": "SyntheticControl", "message": "explicit failure control"} if outcome == "failed" else None,
        "source_identity": {"path": "labelled-synthetic-fixture", "callable": "align_sequences", "sha256": "0" * 64}}


HITS = [{"position": 0, "strand": "+", "mismatches": []},
        {"position": 1, "strand": "+", "mismatches": [[3, "A", "C"]]},
        {"position": 7, "strand": "+", "mismatches": [[0, "A", "C"]]},
        {"position": 8, "strand": "+", "mismatches": []}]
GROUP = {"sequence": "AAAA", "alignments": HITS}


def components(record=None, args=None):
    return calculate_primer_placement_components(build_primer_placement_sheet(
        native_fixture([GROUP]) if record is None else record, **(operands() if args is None else args)))


def codes(result):
    return {r["code"] for r in result["issues"]}


def test_shared_literal_column_authority_preserves_existing_gaps_and_ambiguity_arithmetic():
    assert count_literal_alignment_columns("ACD-EFG", "ACTVE-G") == {
        "alignment_columns": 7, "paired_positions": 5, "identical_positions": 4,
        "substituted_positions": 1, "query_gap_columns": 1, "reference_gap_columns": 1,
        "query_aligned_positions": 6, "reference_aligned_positions": 6}
    assert count_literal_alignment_columns("ANN", "ANA")["identical_positions"] == 2
    assert count_literal_alignment_columns("AAAA", "AAAC")["substituted_positions"] == 1


def test_independent_four_placements_exact_counts_denominators_and_full_input_retention():
    native, args = native_fixture([GROUP]), operands("aaaaccccaaaa", "aaaa")
    before = deepcopy((native, args))
    sheet = build_primer_placement_sheet(native, **args)
    result = calculate_primer_placement_components(sheet)
    assert (native, args) == before
    assert sheet["inputs"]["target_sequence"] == "aaaaccccaaaa"
    assert sheet["inputs"]["primers"] == "aaaa"
    assert result["status"] == "complete"
    assert result["summary"] == {"target_length_symbols": 12, "requested_primer_occurrence_count": 1,
        "native_group_count": 1, "known_native_hit_list_count": 1,
        "retained_native_hit_occurrence_count": 4, "usable_saved_hit_count": 4,
        "plus_hit_count": 4, "minus_hit_count": 0, "strand_known_hit_count": 4,
        "source_compatible_hit_count": 4, "mismatch_count_sum": 2, "mismatch_count_denominator_hits": 4}
    group = result["groups"][0]
    assert group["candidate_windows_per_orientation"] == 9
    assert group["candidate_oriented_windows"] == 18
    assert [h["target_interval"] for h in group["hits"]] == [[0, 4], [1, 5], [7, 11], [8, 12]]
    assert [h["mismatch_fraction"] for h in group["hits"]] == [
        {"numerator": 0, "denominator": 4, "value": 0}, {"numerator": 1, "denominator": 4, "value": .25},
        {"numerator": 1, "denominator": 4, "value": .25}, {"numerator": 0, "denominator": 4, "value": 0}]
    assert set(result["summary"]) <= set(result["definitions"])
    assert all("unit" in result["definitions"][field] and "missing_behavior" in result["definitions"][field] for field in result["summary"])
    assert not any(key in result for key in ("score", "confidence", "evalue"))


def test_target_mismatch_paths_preserve_split_reversed_original_ancestry():
    args = operands()
    args["target_mapping"]["path"] = [
        {"subject_ref": "source:a", "start": 100, "end": 104, "unit": "nt", "strand": "+"},
        {"subject_ref": "source:b", "start": 200, "end": 208, "unit": "nt", "strand": "-"}]
    result = components(args=args)
    hit = result["groups"][0]["hits"][1]
    assert hit["target_mapping"]["intervals"] == [
        {"subject_ref": "source:a", "start": 101, "end": 104, "unit": "nt", "strand": "+"},
        {"subject_ref": "source:b", "start": 207, "end": 208, "unit": "nt", "strand": "-"}]
    mismatch = hit["mismatches"][0]
    assert mismatch["target_position"] == 4
    assert mismatch["target_source_intervals"] == [
        {"subject_ref": "source:b", "start": 207, "end": 208, "unit": "nt", "strand": "-"}]
    assert result["groups"][0]["hits"][2]["mismatches"][0]["target_source_intervals"] == [
        {"subject_ref": "source:b", "start": 204, "end": 205, "unit": "nt", "strand": "-"}]


def test_reverse_native_mismatch_position_is_oriented_and_maps_to_original_primer():
    record = native_fixture([{"sequence": "CGTT", "alignments": [
        {"position": 1, "strand": "-", "mismatches": [[2, "C", "T"]]}]}])
    result = components(record, operands("AAATGGG", "CGTT"))
    hit = result["groups"][0]["hits"][0]
    assert result["status"] == "complete"
    assert hit["oriented_source_primer"] == "AACG"
    assert hit["target_window"] == "AATG"
    mismatch = hit["mismatches"][0]
    assert mismatch["oriented_primer_position"] == 2
    assert mismatch["original_primer_position"] == 1
    assert mismatch["target_position"] == 3
    assert mismatch["primer_source_intervals"] == [
        {"subject_ref": "source:primer:0", "start": 501, "end": 502, "unit": "nt", "strand": "-"}]
    assert hit["mismatch_fraction"]["value"] == .25


def test_palindromes_and_repeated_primer_occurrences_are_not_deduplicated():
    palindrome = {"sequence": "ATAT", "alignments": [
        {"position": p, "strand": strand, "mismatches": []} for strand in ("+", "-") for p in (0, 2)]}
    result = components(native_fixture([palindrome, palindrome]), operands("ATATAT", ["ATAT", "ATAT"]))
    assert result["status"] == "complete"
    assert result["summary"]["requested_primer_occurrence_count"] == 2
    assert result["summary"]["retained_native_hit_occurrence_count"] == 8
    assert result["summary"]["plus_hit_count"] == result["summary"]["minus_hit_count"] == 4
    assert [g["primer_occurrence_ordinal"] for g in result["groups"]] == [0, 1]
    assert [(h["strand"], h["target_interval"][0]) for h in result["groups"][0]["hits"]] == [("+", 0), ("+", 2), ("-", 0), ("-", 2)]


def test_native_duplicate_and_out_of_order_occurrences_are_retained_and_qualified():
    native = native_fixture([{"sequence": "AAAA", "alignments": [HITS[1], HITS[1], HITS[0]]}])
    result = components(native)
    assert result["summary"]["retained_native_hit_occurrence_count"] == 3
    assert result["summary"]["mismatch_count_sum"] == 2
    assert {"primer_repeated_native_hit_occurrence", "primer_native_source_order_conflict"} <= codes(result)
    assert [h["target_interval"][0] for h in result["groups"][0]["hits"]] == [1, 1, 0]


def test_noncanonical_source_rc_remains_literal_and_is_never_repaired_to_iupac_science():
    native = native_fixture([{"sequence": "AR", "alignments": [
        {"position": 0, "strand": "+", "mismatches": []},
        {"position": 2, "strand": "+", "mismatches": [[1, "R", "C"]]},
        {"position": 1, "strand": "-", "mismatches": [[1, "T", "A"]]}]}])
    result = components(native, operands("ARAC", "AR"))
    hits = result["groups"][0]["hits"]
    assert hits[2]["oriented_source_primer"] == "RT"
    assert hits[2]["target_window"] == "RA"
    assert [h["native_mismatch_entry_count"] for h in hits] == [0, 1, 1]
    assert all(h["mismatch_count"] is None and h["source_acceptance"] == "unsupported" for h in hits)
    assert all(h["mismatch_list_matches_full_operands"] is True for h in hits)
    assert hits[2]["primer_mapping"]["intervals"] is None
    assert "primer_source_noncanonical_rc_is_not_iupac_science" in codes(result)


def test_empty_primer_pseudo_hits_keep_native_entries_without_zero_mismatch_science():
    hits = [{"position": p, "strand": strand, "mismatches": []} for strand in ("+", "-") for p in (0, 1, 2)]
    result = components(native_fixture([{"sequence": "", "alignments": hits}]), operands("AC", ""))
    group = result["groups"][0]
    assert group["reported_hit_count"] == 6 and group["candidate_oriented_windows"] is None
    assert result["summary"]["retained_native_hit_occurrence_count"] == 6
    assert result["summary"]["mismatch_count_denominator_hits"] == 0
    assert all(h["mismatch_fraction"] == {"numerator": None, "denominator": 0, "value": None} for h in group["hits"])
    assert all(h["target_interval"] is None and h["native_mismatch_entry_count"] == 0 for h in group["hits"])


def test_longer_primer_and_explicit_empty_occurrence_list_have_completed_empty_native_results():
    longer = components(native_fixture([{"sequence": "AAAA", "alignments": []}]), operands("AA", "AAAA"))
    assert longer["status"] == "complete"
    assert longer["groups"][0]["candidate_oriented_windows"] == 0
    assert longer["summary"]["retained_native_hit_occurrence_count"] == 0
    empty = components(native_fixture([]), operands("AA", []))
    assert empty["summary"]["requested_primer_occurrence_count"] == 0
    assert empty["summary"]["retained_native_hit_occurrence_count"] == 0


def test_missing_groups_and_native_failure_preserve_unknown_and_known_partial_populations():
    record = native_fixture([GROUP], outcome="truncated")
    result = components(record, operands(primers=["AAAA", "AAAA"]))
    assert result["native_outcome"] == "truncated"
    assert result["summary"]["retained_native_hit_occurrence_count"] == 4
    assert result["summary"]["known_native_hit_list_count"] == 1
    assert result["groups"][1]["reported_hit_count"] is None
    assert "primer_native_primer_population_conflict" in codes(result)
    record = native_fixture([], outcome="failed");record["result"] = None
    failed = components(record)
    assert failed["native_outcome"] == "failed"
    assert failed["summary"]["retained_native_hit_occurrence_count"] is None
    assert failed["summary"]["plus_hit_count"] is None
    assert failed["summary"]["mismatch_count_sum"] is None


def test_wrong_native_primer_sequence_is_not_rematched_by_name_or_ordinal_repaired():
    record = native_fixture([{"sequence": "CCCC", "alignments": HITS}])
    result = components(record)
    assert result["groups"][0]["native_group"]["sequence"] == "CCCC"
    assert result["summary"]["source_compatible_hit_count"] == 0
    assert result["groups"][0]["hits"][1]["mismatch_count"] == 1
    assert result["groups"][0]["hits"][1]["target_mapping"]["intervals"] is None


@pytest.mark.parametrize("bad", [
    {"position": True, "strand": "+", "mismatches": []},
    {"position": 99, "strand": "+", "mismatches": []},
    {"position": 1, "strand": "?", "mismatches": []},
    {"position": 1, "strand": "+", "mismatches": [[0, "A", "A"]]},
    {"position": 1, "strand": "+", "mismatches": [[True, "A", "C"]]},
    {"position": 1, "strand": "+", "mismatches": [[3, "A", "C"], [3, "A", "C"]]},
])
def test_malformed_native_hit_keeps_other_occurrences_and_actual_bad_entries(bad):
    result = components(native_fixture([{"sequence": "AAAA", "alignments": [bad, HITS[3]]}]))
    first, other = result["groups"][0]["hits"]
    assert first["native_hit"] == bad
    assert first["source_acceptance"] != "compatible"
    assert other["source_acceptance"] == "compatible"
    assert other["target_interval"] == [8, 12]


def test_real_two_mismatch_comparison_is_retained_but_not_accepted_as_a_source_hit():
    bad = {"position": 2, "strand": "+", "mismatches": [[2, "A", "C"], [3, "A", "C"]]}
    result = components(native_fixture([{"sequence": "AAAA", "alignments": [bad]}]))
    row = result["groups"][0]["hits"][0]
    assert row["mismatch_count"] == 2
    assert row["mismatch_fraction"]["value"] == .5
    assert row["source_acceptance"] == "incompatible"
    assert "primer_source_one_mismatch_acceptance_conflict" in codes(result)


def test_nonfinite_native_component_is_explicitly_rejected_without_erasing_other_hits():
    record = native_fixture([{"sequence": "AAAA", "alignments": [
        {"position": float("inf"), "strand": "+", "mismatches": []}, HITS[3]]}])
    sheet = build_primer_placement_sheet(record, **operands())
    assert sheet["rejected_values"] == [{"path": "/native_record/result/sequences/0/alignments/0/position",
        "value_type": "float", "nonfinite_token": "inf"}]
    result = calculate_primer_placement_components(json.loads(json.dumps(sheet, allow_nan=False)))
    assert result["groups"][0]["hits"][0]["target_interval"] is None
    assert result["groups"][0]["hits"][1]["source_acceptance"] == "compatible"


def test_saved_hit_corruption_is_unavailable_and_never_repaired_from_native_rows():
    sheet = build_primer_placement_sheet(native_fixture([GROUP]), **operands())
    sheet["groups"][0]["hits"][0]["mismatch_fraction"]["value"] = .9
    result = calculate_primer_placement_components(sheet)
    assert result["groups"][0]["hits"][0]["state"] == "incompatible"
    assert result["groups"][0]["hits"][0]["saved_hit"]["mismatch_fraction"]["value"] == .9
    assert result["summary"]["retained_native_hit_occurrence_count"] == 4
    assert result["summary"]["usable_saved_hit_count"] == 3
    assert result["summary"]["mismatch_count_sum"] == 2
    assert result["summary"]["mismatch_count_denominator_hits"] == 3


def test_missing_original_paths_preserve_literal_measurements_without_invented_mapping():
    args = operands();args["target_mapping"] = None;args["primer_mappings"] = [None]
    result = components(args=args)
    assert result["summary"]["mismatch_count_sum"] == 2
    assert result["groups"][0]["hits"][1]["target_mapping"]["state"] == "unavailable"
    assert result["groups"][0]["hits"][1]["mismatches"][0]["primer_source_intervals"] is None


def test_json_replay_requires_no_imports_native_io_or_network(monkeypatch):
    sheet = build_primer_placement_sheet(native_fixture([GROUP]), **operands())
    expected = calculate_primer_placement_components(sheet)
    saved = json.loads(json.dumps(sheet, sort_keys=True));before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved primer measurement attempted external work")
    guards = ((builtins, "open"), (io, "open"), (Path, "read_text"),
        (Path, "read_bytes"), (socket, "socket"), (subprocess, "Popen"), (builtins, "__import__"))
    originals = [(owner, name, getattr(owner, name)) for owner, name in guards]
    # setattr imports inspect, so install the import trap last. Restore every
    # guard before assertions or pytest's reporting/teardown can perform I/O.
    with monkeypatch.context() as guarded:
        for owner, name in guards:
            guarded.setattr(owner, name, forbidden)
        actual = calculate_primer_placement_components(saved)
    assert all(getattr(owner, name) is original for owner, name, original in originals)
    assert actual == expected
    assert saved == before




