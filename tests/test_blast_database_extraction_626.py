"""Saved native BLAST extraction oracles and explicitly synthetic counterexamples."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.blast_database_extraction import (
    parse_blastdbcmd_sequences, validate_sequence_extraction,
)
from gene_annotation_episode.domain import ContractError


EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_database_readers_2026-10-28_626"


def occurrence(content, *, oid="out", complete="complete"):
    return {"occurrence_id": oid, "direction": "output", "role": "stdout", "ordinal": 0,
            "artifact_ref": "fixture:" + oid, "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content), "native_format": "blastdbcmd_tabular_v1",
            "completeness": complete, "native_path": None}


def context(selectors=("seqA",), *, molecule="dna", selected_range=None, strand="plus",
            returncode=0, database_path="/explicit/database"):
    return {
        "operation": {"version": "blast_utility_operation_v1", "program": "blastdbcmd",
            "mode": "extract_sequences", "input_occurrence_ids": ["db-file"], "database_key": "db",
            "molecule": molecule, "parameters": {
                "selectors": [{"ordinal": i, "value": s} for i, s in enumerate(selectors)],
                "output_format": "blastdbcmd_tabular_v1", "range": selected_range,
                "strand": strand, "get_dups": False, "target_only": False}},
        "database_binding": {"database_key": "db", "kind": "blast_nucleotide_sequence" if molecule == "dna" else "blast_protein_sequence",
            "molecule": molecule, "identity": {"namespace": "explicit_fixture", "value": "db", "version": None, "release": None},
            "source_ref": "fixture:database", "native_paths": [database_path], "occurrence_ids": ["db-file"], "inventory_complete": True},
        "outcome": {"started": True, "returncode": returncode, "state": "succeeded" if returncode == 0 else "failed",
            "writer_closed": True, "inventory_complete": True},
    }


def native_case(name):
    provenance = json.loads((EVIDENCE / "FIXTURE_PROVENANCE_001.json").read_text())
    row = next(row for row in provenance["cases"] if row["name"] == name)
    data = (EVIDENCE / "fixtures" / name / "stdout.txt").read_bytes()
    assert hashlib.sha256(data).hexdigest() == row["stdout"]["sha256"]
    assert len(data) == row["stdout"]["size_bytes"]
    argv = row["argv"]
    value = lambda flag: argv[argv.index(flag) + 1]
    selected_range = None
    if "-range" in argv:
        start, end = value("-range").split("-")
        selected_range = {"start_1based": int(start), "end_1based": int(end)}
    ctx = context(value("-entry").split(","), molecule="dna" if value("-dbtype") == "nucl" else "protein",
                  selected_range=selected_range, strand=value("-strand") if "-strand" in argv else "plus",
                  returncode=row["returncode"], database_path=value("-db"))
    return data, ctx


def parse(data, ctx=None, **kwargs):
    ctx = context() if ctx is None else ctx
    return parse_blastdbcmd_sequences(data, occurrence=occurrence(data), **ctx, **kwargs)


@pytest.mark.parametrize("name,lengths,molecule", [
    ("extract_dna_v4", [12, 12, 7], "dna"),
    ("extract_dna_v5", [12, 12, 7], "dna"),
    ("extract_protein_v5", [20, 15], "protein"),
])
def test_authentic_selected_outputs_retain_lengths_identities_and_saved_copy(name, lengths, molecule):
    data, ctx = native_case(name)
    result = parse(data, ctx)
    assert result["population_completeness"] == "complete_selection"
    assert result["failures"] == []
    assert [r["returned_symbol_count"] for r in result["records"]] == lengths
    assert [r["native_reported_length"] for r in result["records"]] == lengths
    assert all(r["molecule"] == molecule and r["native_length_basis"] == "full_sequence" for r in result["records"])
    assert result["records"][0]["native_identifier"].startswith("lcl|")
    saved = json.loads(json.dumps(result))
    assert validate_sequence_extraction(saved) == result
    saved["records"][0]["normalized_sequence"] = "changed"
    assert result["records"][0]["normalized_sequence"] != "changed"
    with pytest.raises(ContractError):
        validate_sequence_extraction(saved)


@pytest.mark.parametrize("name,expected,interval,strand", [
    ("range_plus", "CGTACG", (1, 7), "plus"),
    ("range_minus", "CGTACG", (1, 7), "minus"),
    ("range_past_end", "TACGT", (7, 12), "plus"),
    ("strand_plus", "TGCAAT", (1, 7), "plus"),
    ("strand_minus", "ATTGCA", (1, 7), "minus"),
])
def test_authentic_ranges_keep_full_length_and_actual_fragment(name, expected, interval, strand):
    data, ctx = native_case(name)
    result = parse(data, ctx)
    row = result["records"][0]
    assert row["original_sequence"] == expected
    assert row["returned_symbol_count"] == len(expected)
    assert row["native_reported_length"] == 12
    assert row["effective_range"] == {"start_0based": interval[0], "end_exclusive": interval[1], "strand": strand}
    assert result["population_completeness"] == "complete_selection"


def test_authentic_duplicate_requests_and_rows_are_not_deduplicated_or_order_joined():
    data, ctx = native_case("duplicate_selectors")
    result = parse(data, ctx)
    assert len(result["operation"]["parameters"]["selectors"]) == 2
    assert len(result["records"]) == 2
    assert [r["native_oid"] for r in result["records"]] == [0, 0]
    assert [r["matched_selector_ordinals"] for r in result["records"]] == [[0, 1], [0, 1]]
    assert [r["record_key"] for r in result["records"]] == ["out#/records/0", "out#/records/1"]
    assert result["failures"] == []


def test_authentic_missing_selector_keeps_present_sequence_with_failed_outcome():
    data, ctx = native_case("missing_selector")
    result = parse(data, ctx)
    assert result["original_outcome"]["returncode"] == 1
    assert result["population_completeness"] == "partial_selection"
    assert result["missing_selector_ordinals"] == [1]
    assert result["records"][0]["returned_symbol_count"] == 12
    assert result["records"][0]["completeness"] == "complete"
    assert {f["code"] for f in result["failures"]} == {"native_nonzero_exit", "selection_incomplete"}


@pytest.mark.parametrize("bad", [b"broken\n", b"\xff\n", b"\n", b"0\t\tseqA\t12\tACGTACGTACGT\n"])
def test_synthetic_invalid_row_does_not_renumber_next_native_row(bad):
    data = bad + b"1\tlcl|seqB\tseqB\t4\tTTGC\n"
    result = parse(data, context(("seqB",)))
    assert result["records"][0]["native_row_ordinal"] == 1
    assert result["records"][0]["line_number"] == 2
    assert result["records"][0]["record_key"] == "out#/records/1"
    failure = next(f for f in result["failures"] if f["code"] == "native_row_invalid")
    assert failure["line_number"] == 1 and failure["record_key"] == "out#/records/0"


@pytest.mark.parametrize("sequence", ["AC-T", "AC.T", "AC T", "AC?T", "ACUT"])
def test_synthetic_invalid_sequence_keeps_original_without_derived_length(sequence):
    result = parse(f"0\tlcl|seqA\tseqA\t4\t{sequence}\n".encode())
    row = result["records"][0]
    assert row["original_sequence"] == sequence
    assert row["native_reported_length"] == 4
    assert row["returned_symbol_count"] is None and row["effective_range"] is None
    assert "sequence_symbol_invalid" in {f["code"] for f in row["failures"]}


def test_synthetic_native_length_conflict_is_retained_without_repair():
    result = parse(b"0\tlcl|seqA\tseqA\t99\tACGT\n")
    row = result["records"][0]
    assert row["native_reported_length"] == 99
    assert row["original_sequence"] == "ACGT"
    assert row["returned_symbol_count"] is None and row["effective_range"] is None
    assert "sequence_length_conflict" in {f["code"] for f in row["failures"]}


@pytest.mark.parametrize("oid,length", [("invalid", "4"), ("0", "invalid")])
def test_synthetic_invalid_native_numeric_cell_qualifies_aggregate_syntax(oid, length):
    result = parse(f"{oid}\tlcl|seqA\tseqA\t{length}\tACGT\n".encode())
    assert len(result["records"]) == 1
    assert next(c for c in result["checks"] if c["name"] == "syntax")["status"] == "fail"
    assert "native_row_invalid" in {f["code"] for f in result["failures"]}


def test_synthetic_alias_requires_explicit_binding_and_preserves_that_basis():
    data = b"0\tlcl|seqA\tseqA\t4\tacgt\n"
    ctx = context(("aliasA",))
    unmatched = parse(data, ctx)
    assert unmatched["missing_selector_ordinals"] == [0]
    assert unmatched["records"][0]["association"] == "unresolved"
    explicit = parse(data, ctx, record_bindings=[{"native_row_ordinal": 0, "selector_ordinals": [0]}])
    assert explicit["records"][0]["association"] == "explicit"
    assert explicit["records"][0]["normalized_sequence"] == "ACGT"
    assert explicit["records"][0]["original_sequence"] == "acgt"


def test_synthetic_explicit_binding_cannot_omit_exact_duplicate_request():
    data = b"0\tlcl|seqA\tseqA\t4\tACGT\n"
    with pytest.raises(ContractError, match="supplied_binding_conflict"):
        parse(data, context(("seqA", "seqA")), record_bindings=[{"native_row_ordinal": 0, "selector_ordinals": [0]}])


def test_synthetic_duplicate_oid_conflict_retains_both_rows():
    data = b"0\tlcl|seqA\tseqA\t4\tACGT\n0\tlcl|seqA\tseqA\t4\tAAAA\n"
    result = parse(data)
    assert len(result["records"]) == 2
    assert all("duplicate_native_identity" in {f["code"] for f in r["failures"]} for r in result["records"])
    assert result["population_completeness"] == "partial_selection"


def test_synthetic_open_last_row_keeps_prior_closed_record():
    data = b"0\tlcl|seqA\tseqA\t4\tACGT\n1\tlcl|seqB\tseqB\t4\tTT"
    ctx = context(("seqA", "seqB"))
    ctx["outcome"] = {"started": True, "returncode": None, "state": "incomplete", "writer_closed": False, "inventory_complete": False}
    result = parse_blastdbcmd_sequences(data, occurrence=occurrence(data, complete="partial"), **ctx)
    assert result["records"][0]["completeness"] == "complete"
    assert result["records"][1]["completeness"] == "partial"
    assert result["records"][1]["original_sequence"] == "TT"
    assert result["population_completeness"] == "partial_selection"


def test_synthetic_internal_protein_stop_reuses_existing_symbol_semantics():
    result = parse(b"0\tlcl|seqA\tseqA\t4\tM*AA\n", context(molecule="protein"))
    assert result["records"][0]["returned_symbol_count"] == 4


def test_bytes_and_supplied_context_are_checked_without_path_io():
    data = b"0\tlcl|seqA\tseqA\t4\tACGT\n"
    ctx = context(database_path="/not/an/existing/database")
    assert parse(data, ctx)["population_completeness"] == "complete_selection"
    wrong = occurrence(data)
    wrong["sha256"] = "0" * 64
    with pytest.raises(ContractError, match="input_identity_mismatch"):
        parse_blastdbcmd_sequences(data, occurrence=wrong, **ctx)
    changed = deepcopy(ctx)
    changed["database_binding"]["database_key"] = "other"
    with pytest.raises(ContractError):
        parse(data, changed)


def test_synthetic_empty_output_never_proves_absent_database_entry():
    result = parse(b"", context(returncode=1))
    assert result["records"] == []
    assert result["population_completeness"] == "unknown"
    assert result["missing_selector_ordinals"] == [0]
