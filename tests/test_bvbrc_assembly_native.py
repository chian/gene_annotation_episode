"""Engineered bytes and descriptors; no BV-BRC task or Source custody claim."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode import bvbrc_assembly_native as native
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta, read_fasta_records


def observed(raw, *, representation="assembly_fasta", complete=True):
    sha = hashlib.sha256(raw).hexdigest()
    return native.parse_assembly_artifact(raw, content=dict(source_ref="source_" + "a" * 24,
        artifact_field="artifact_ref", artifact_ref="artifact_" + sha, sha256=sha, byte_count=len(raw)),
        representation=representation, capture_complete=complete, expected_task_id="engineering-task")


def test_literal_variable_length_records_share_reader_without_claiming_alignment():
    raw = ">α full label\r\nacgTN\n>α other occurrence\nNN\n".encode()
    document = observed(raw)
    fasta = document["native_document"]
    assert fasta["completeness"] == "complete" and fasta["observed_record_count"] == 2
    assert [row["raw_header"] for row in fasta["rows"]] == ["α full label", "α other occurrence"]
    assert [row["sequence"] for row in fasta["rows"]] == ["acgTN", "NN"]
    assert [row["member_label"] for row in fasta["rows"]] == ["α", "α"]
    assert "observed_column_count" not in fasta and "alignment_id" not in fasta
    for row in fasta["rows"]:
        location = row["source_location"]
        assert raw[location["byte_start_0based"]:location["byte_end_0based_exclusive"]].startswith(
            (">" + row["raw_header"]).encode())
    artifact = fasta["artifact"]
    assert read_fasta_records(raw, artifact=artifact, id_rule="first_whitespace_token", encoding="utf-8")["status"] == "ok"
    aligned = parse_aligned_fasta(raw, artifact=artifact, id_rule="first_whitespace_token", encoding="utf-8")
    assert aligned["status"] == "partial" and aligned["value"]["observed_column_count"] is None
    assert aligned["value"]["rows"] == fasta["rows"]
    assert [row["code"] for row in aligned["diagnostics"]] == ["phylogeny_alignment_lengths_unequal"]


@pytest.mark.parametrize("lengths,total,n50,l50,crossing", [
    ([5, 3, 2], 10, 5, 1, 0), ([3, 3, 3], 9, 3, 2, 1),
    ([1, 6, 3], 10, 6, 1, 1), ([3, 2], 5, 3, 1, 0),
    ([0, 0], 0, None, None, None), ([0, 4], 4, 4, 1, 1),
])
def test_contiguity_uses_complete_original_occurrences_and_exact_half_crossing(lengths, total, n50, l50, crossing):
    raw = "".join(">same duplicate header\n" + "A" * size + "\n" for size in lengths).encode()
    result = native.calculate_assembly_components(observed(raw))
    assert result["population"] == dict(scope="one_selected_retained_artifact", complete_artifact_population=True,
        observed_record_count=len(lengths), intended_genome_completeness=None)
    assert [row["composition"]["components"]["length"] for row in result["records"]] == lengths
    assert (result["total_length_nt"], result["n50_nt"], result["l50"], result["n50_crossing_record_ordinal"]) == (
        total, n50, l50, crossing)
    assert result["n_count"] == result["n_block_count"] == 0


def test_n_blocks_do_not_join_at_record_boundaries_and_composition_keeps_original_case():
    result = native.calculate_assembly_components(observed(b">a\nANn\n>b\nnNA\n"))
    assert result["total_length_nt"] == 6 and result["n_count"] == 4 and result["n_block_count"] == 2
    assert [row["n_run_intervals_0based"] for row in result["records"]] == [[[1, 3]], [[0, 2]]]
    assert result["records"][0]["composition"]["sheet"]["sequence"] == "ANn"
    assert result["records"][0]["composition"]["components"]["ambiguity_fraction"] == 2 / 3


@pytest.mark.parametrize("raw,complete", [(b">a\nACGT\n>b\nNN\n", False),
    (b"before header\n>a\nACGT\n", True), (b">a\nACGT!\n", True), (b">\nACGT\n", True)])
def test_unresolved_or_invalid_populations_do_not_acquire_whole_artifact_counts(raw, complete):
    result = native.calculate_assembly_components(observed(raw, complete=complete))
    assert result["population"]["complete_artifact_population"] is False
    assert result["retained_symbol_total"] > 0
    assert all(result[key] is None for key in ("total_length_nt", "n50_nt", "l50", "n_count", "n_block_count"))
    assert result["records"] and result["status"] == "partial"


def test_empty_file_and_explicit_empty_record_have_distinct_observed_populations():
    empty = native.calculate_assembly_components(observed(b""))
    explicit = native.calculate_assembly_components(observed(b">empty\n"))
    assert empty["population"]["observed_record_count"] == 0 and empty["retained_symbol_total"] == 0
    assert empty["total_length_nt"] is None and empty["n_count"] is None
    assert explicit["population"]["observed_record_count"] == 1 and explicit["total_length_nt"] == 0
    assert explicit["n_count"] == explicit["n_block_count"] == 0
    assert empty["n50_nt"] is explicit["n50_nt"] is None


def test_reported_sars2_null_zero_missing_and_derived_fasta_zero_stay_separate():
    nulls = native.calculate_assembly_components(observed(b'{"total_ns":null,"n_blocks":0}',
        representation="sars2_assembly_details"))
    first, second = nulls["native_reported_fields"]
    assert first["state"] == "null" and first["native_value"] == dict(kind="null", value=None)
    assert first["integer_value"] is None and second["integer_value"] == 0
    missing = native.calculate_assembly_components(observed(b'{}', representation="sars2_assembly_details"))
    assert [row["state"] for row in missing["native_reported_fields"]] == ["missing", "missing"]
    assert all(row["integer_value"] is None for row in missing["native_reported_fields"])
    fasta = native.calculate_assembly_components(observed(b">a\nACGT\n"))
    assert fasta["n_count"] == fasta["n_block_count"] == 0
    assert nulls["records"] is None and nulls["n_count"] is None


@pytest.mark.parametrize("token", [b"false", b"1.0", b"-1", b"9007199254740993"])
def test_native_counts_preserve_tokens_without_bool_float_negative_or_unsafe_integer_substitution(token):
    document = observed(b'{"total_ns":' + token + b'}', representation="sars2_assembly_details")
    field = native.calculate_assembly_components(document)["native_reported_fields"][0]
    assert field["state"] == "present" and field["integer_value"] is None
    assert field["integer_state"] == "not_represented_as_safe_integer"
    assert field["native_value"] == (dict(kind="boolean", value=False) if token == b"false" else
        dict(kind="number", token=token.decode()))


def test_duplicate_report_keys_and_duplicate_sequence_labels_are_never_first_match_substitutions():
    document = observed(b'{"total_ns":1,"total_ns":2,"n_blocks":0}', representation="sars2_assembly_details")
    field = native.calculate_assembly_components(document)["native_reported_fields"][0]
    assert field["state"] == "ambiguous" and field["integer_value"] is None
    assert [member["value"]["token"] for member in document["native_document"]["members"]
        if member["name"] == "total_ns"] == ["1", "2"]


@pytest.mark.parametrize("raw,state", [(b'{}', "parent_missing"),
    (b'{"contig_filtering":null}', "parent_null"), (b'{"contig_filtering":3}', "parent_incompatible")])
def test_unavailable_parent_report_does_not_become_the_requested_child_count(raw, state):
    fields = native.calculate_assembly_components(observed(raw, representation="genome_assembly_details"))["native_reported_fields"]
    assert len(fields) == 4 and all(row["state"] == state and row["integer_value"] is None
        and row["native_value"] is None for row in fields)


def test_native_report_count_conflicts_are_literal_data_and_never_repaired_from_other_files():
    reported = native.calculate_assembly_components(observed(
        b'{"contig_filtering":{"total contigs":"4","num contigs above thresholds":"2","num contigs below thresholds":"3"}}',
        representation="genome_assembly_details"))
    assert [row["integer_value"] for row in reported["native_reported_fields"]] == [4, 2, 3, None]
    assert reported["total_length_nt"] is None and reported["population"]["observed_record_count"] is None


@pytest.mark.parametrize("raw,representation", [(b"\xff", "assembly_fasta"), (b"{", "genome_assembly_details"),
    (b"\xff", "native_text")])
def test_unavailable_native_representation_retains_binding_and_unknown_counts(raw, representation):
    document = observed(raw, representation=representation)
    assert document["parsing_state"] == "unavailable" and document["native_document"] is None
    assert document["issues"][0]["path"] == "/native_document"
    result = native.calculate_assembly_components(document)
    assert result["records"] is None and result["retained_symbol_total"] is None and result["n50_nt"] is None


def test_saved_calculation_uses_shared_composition_without_any_native_parser_or_io(monkeypatch):
    document = observed(b">a\nAcgNN\n>b\nNA\n"); original = deepcopy(document)
    calls = []
    calculate = native.calculate_sequence_composition_scores
    def measured(sheet, **kwargs):
        calls.append(sheet["sequence"])
        return calculate(sheet, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved assembly calculation parsed or reopened native bytes")
    monkeypatch.setattr(native, "calculate_sequence_composition_scores", measured)
    monkeypatch.setattr(native, "read_fasta_records", forbidden)
    monkeypatch.setattr(native, "_parse", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    result = native.calculate_assembly_components(document)
    assert calls == ["AcgNN", "NA"] and document == original
    assert result["n_count"] == 3 and result["n_block_count"] == 2 and result["n50_nt"] == 5
