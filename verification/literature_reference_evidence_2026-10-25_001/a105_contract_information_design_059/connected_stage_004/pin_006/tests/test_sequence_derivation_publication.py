"""Actual local transformations and their retained numerical grading artifacts.

Inputs are synthetic sequences. No biological annotation or remote execution
is claimed. Failure injections are explicitly separate from native examples.
"""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry
from test_sequence_views_integration import LocalOnly, pinned_rna_reference, product_from_response, product_sequence
from test_tool_grading_publication import numerical, operation_count


CASES = [
    ("sequence.translate", "CATGAAATAAC", "dna",
     {"code": 11, "frame": 1}, "MK*",
     {"input_length_nt": 11, "selected_length_nt": 11, "frame_skipped_nt": 1,
      "translated_length_nt": 9, "trailing_untranslated_bases": 1,
      "translated_codon_count": 3, "output_symbol_count": 3,
      "amino_acid_symbol_count": 2, "terminal_stop_symbol_count": 1,
      "omitted_terminal_stop_codon_count": 0}),
    ("sequence.translate", "GTGAAATAA", "dna",
     {"code": 11, "cds": True}, "MK",
     {"translated_length_nt": 9, "translated_codon_count": 3,
      "output_symbol_count": 2, "amino_acid_symbol_count": 2,
      "terminal_stop_symbol_count": 0, "omitted_terminal_stop_codon_count": 1}),
    ("sequence.translate", "ATGTGATAA", "dna", {"code": 2}, "MW*",
     {"translated_codon_count": 3, "internal_stop_count": 0,
      "terminal_stop_symbol_count": 1, "compatible_codon_count": 3}),
    ("sequence.view", "ACGTACGTAA", "dna",
     {"molecule": "dna", "orientation": "reverse_complement",
      "segments": [{"start": 4, "end": 8}, {"start": 1, "end": 5},
                   {"start": 1, "end": 3}]}, "CGTACGACGT",
     {"input_symbol_count": 10, "output_symbol_count": 10,
      "requested_segment_count": 3, "selected_symbol_occurrence_count": 10,
      "distinct_selected_input_symbol_count": 7,
      "repeated_selected_input_symbol_count": 3, "selected_input_fraction": .7,
      "selected_input_fraction_denominator_symbols": 10,
      "compared_symbol_count": 10, "matching_symbol_count": 10,
      "mismatching_symbol_count": 0}),
    ("sequence.view", "AUGC", "rna",
     {"molecule": "rna", "orientation": "reverse_complement"}, "GCAU",
     {"input_symbol_count": 4, "output_symbol_count": 4,
      "matching_symbol_count": 4, "mismatching_symbol_count": 0}),
    ("sequence.view", "MACDEFGH", "protein",
     {"molecule": "protein", "segments": [{"start": 1, "end": 4}]}, "ACD",
     {"input_symbol_count": 8, "output_symbol_count": 3,
      "distinct_selected_input_symbol_count": 3, "selected_input_fraction": 3/8}),
]


def calculator(operation):
    family = "translation" if operation == "sequence.translate" else "extraction"
    return getattr(importlib.import_module("gene_annotation_episode.sequence_" + family + "_grader"),
                   "calculate_" + family + "_scores")


@pytest.mark.parametrize("operation,sequence,molecule,arguments,expected,quantities", CASES)
def test_native_transformation_retains_actual_sheet_numbers_and_original_mapping(
        tmp_path, monkeypatch, operation, sequence, molecule, arguments, expected, quantities):
    directory = tmp_path / "state"
    with Store(directory) as store:
        target, = store.create_problem(raw_sequence=sequence, molecule=molecule)["subject_refs"]
        original = store.get_input(target)
        registry = ToolRegistry(store, clients=LocalOnly())
        args = {"subject_ref": target, **arguments}
        result = registry.execute(operation, args, operation_key="selected-transformation")
        product = product_from_response(store, result)
        assert product_sequence(store, product) == expected
        source = store.get(result["result"]["source_ref"])
        native_bytes = store.get_artifact(source["artifact_ref"])
        native = json.loads(native_bytes)
        grading, = source_tool_gradings(store, source["id"])
        sheet, scores = grading["sheet"], grading["scores"]
        assert sheet["input_sequence"] == sequence
        assert sheet["subject_ref"] == target
        assert sheet["parent_mapping"] == store.sequence_mapping(target)
        assert sheet["native_result"]["sequence"] == native["sequence"] == expected
        observation = store.get(result["result"]["records"][0]["observation_ref"])
        projected = numerical(observation)
        for name, value in quantities.items():
            assert scores["summary"][name] == pytest.approx(value), name
            assert projected[name] == pytest.approx(value), name
        if operation == "sequence.translate":
            snapshot = native["genetic_code_snapshot"]
            assert snapshot["code"] == arguments["code"]
            assert snapshot["biopython_version"] == native["biopython_version"]
            assert snapshot["forward_table"]["ATG"] == "M"
        assert registry.execute(operation, args, operation_key="selected-transformation") == result
        assert operation_count(store, operation) == store.count("observation") == 1
        assert store.get_input(target) == original and store.count("annotation") == 0
        assert "sheet" not in result["result"] and "scores" not in result["result"]
        grading_before = deepcopy(grading)
    with Store(directory) as store:
        retained, = source_tool_gradings(store, source["id"])
        assert retained == grading_before
        assert store.get_artifact(source["artifact_ref"]) == native_bytes
        saved = json.loads(json.dumps(retained["sheet"], sort_keys=True))
        calculate = calculator(operation)
        from gene_annotation_episode import sequence_ops, sequence_views
        def forbidden(*args, **kwargs):
            raise AssertionError("Saved-sheet calculation attempted acquisition or a native rerun")
        with monkeypatch.context() as blocked:
            blocked.setattr(sequence_ops, "translate", forbidden)
            blocked.setattr(sequence_views, "view_sequence", forbidden)
            blocked.setattr(ToolRegistry, "execute", forbidden)
            blocked.setattr(socket, "socket", forbidden)
            blocked.setattr(Path, "open", forbidden)
            assert calculate(saved) == retained["scores"]
        assert store.count("observation") == 1


@pytest.mark.parametrize("operation,family,arguments", [
    ("sequence.translate", "translation", {"code": 11}),
    ("sequence.view", "extraction", {"molecule": "dna"}),
])
def test_grading_failure_preserves_native_product_and_exact_partial_replay(
        tmp_path, monkeypatch, operation, family, arguments):
    module = importlib.import_module("gene_annotation_episode.sequence_" + family + "_grader")
    def reject(*args, **kwargs):
        raise ValueError("injected_derivation_grading_failure")
    monkeypatch.setattr(module, "grade_" + family, reject)
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")["subject_refs"]
        registry = ToolRegistry(store, clients=LocalOnly())
        args = {"subject_ref": target, **arguments}
        result = registry.execute(operation, args, operation_key="partial-transform")
        assert result["status"] == "partial", result
        product = next(store.get(ref) for ref in result["record_refs"]
                       if store.get(ref)["record_type"] == "product")
        assert product_sequence(store, product) == ("MK*" if family == "translation" else "ATGAAATAA")
        grading, = source_tool_gradings(store, result["result"]["source_ref"])
        assert grading == {"sheet": None, "scores": None,
            "failure": {"category": "grading_input", "code": "injected_derivation_grading_failure"}}
        assert registry.execute(operation, args, operation_key="partial-transform") == result
        assert store.count("product") == store.count("observation") == 1
        assert operation_count(store, operation) == 1 and store.count("annotation") == 0


def test_chained_discontinuous_translation_and_repeated_protein_view_keep_original_units(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="CATCCGAAATAACC", molecule="dna")["subject_refs"]
        registry = ToolRegistry(store, clients=LocalOnly())
        scope = {"subject_refs": [target]}
        selected = registry.execute("sequence.view", {"subject_ref": target, "molecule": "dna",
            "segments": [{"start": 1, "end": 3}, {"start": 5, "end": 12}]},
            scope=scope, operation_key="split-input")
        nucleotide = product_from_response(store, selected)
        assert product_sequence(store, nucleotide) == "ATGAAATAA"
        translated = registry.execute("sequence.translate", {"subject_ref": nucleotide["id"],
            "code": 11, "cds": True}, scope=scope, operation_key="split-codon-translation")
        protein = product_from_response(store, translated)
        assert product_sequence(store, protein) == "MK"
        graded_translation, = source_tool_gradings(store, translated["result"]["source_ref"])
        assert graded_translation["sheet"]["parent_mapping"] == store.sequence_mapping(nucleotide["id"])
        codons = graded_translation["scores"]["codons"]
        segment = lambda start, end: {"subject_ref": target, "start": start,
                                      "end": end, "unit": "nt", "strand": "+"}
        assert codons[0]["original_source_intervals"] == [segment(1, 3), segment(5, 6)]
        assert codons[1]["original_source_intervals"] == [segment(6, 9)]
        assert codons[2]["original_source_intervals"] == [segment(9, 12)]
        assert codons[2]["output_position"] is None and codons[2]["role"] == "omitted_terminal_stop"
        assert graded_translation["scores"]["summary"]["mapped_output_symbol_count"] == 2
        assert store.sequence_mapping(protein["id"])["path"] == [segment(1, 3), segment(5, 9)]
        repeated = registry.execute("sequence.view", {"subject_ref": protein["id"], "molecule": "protein",
            "segments": [{"start": 1, "end": 2}, {"start": 0, "end": 1}, {"start": 1, "end": 2}]},
            scope=scope, operation_key="repeated-protein-regions")
        product = product_from_response(store, repeated)
        assert product_sequence(store, product) == "KMK"
        grading, = source_tool_gradings(store, repeated["result"]["source_ref"])
        scores = grading["scores"]
        assert grading["sheet"]["parent_mapping"] == store.sequence_mapping(protein["id"])
        assert {name: scores["summary"][name] for name in (
            "input_symbol_count", "output_symbol_count", "selected_symbol_occurrence_count",
            "distinct_selected_input_symbol_count", "repeated_selected_input_symbol_count",
            "selected_input_fraction", "unmapped_output_symbol_count")} == {
                "input_symbol_count": 2, "output_symbol_count": 3,
                "selected_symbol_occurrence_count": 3, "distinct_selected_input_symbol_count": 2,
                "repeated_selected_input_symbol_count": 1, "selected_input_fraction": 1.,
                "unmapped_output_symbol_count": 0}
        assert scores["verified_output_source_path"] == store.sequence_mapping(product["id"])["path"] == [
            segment(6, 9), segment(1, 3), segment(5, 6), segment(6, 9)]
        assert scores["output_source_coverage"] == [{"subject_ref": target, "unit": "nt",
            "intervals": [[1, 3], [5, 9]], "distinct_source_position_count": 6,
            "source_position_occurrence_count": 9, "repeated_source_position_count": 3}]
        for result, operation in ((selected, "sequence.view"), (translated, "sequence.translate"),
                                  (repeated, "sequence.view")):
            saved, = source_tool_gradings(store, result["result"]["source_ref"])
            assert calculator(operation)(json.loads(json.dumps(saved["sheet"], sort_keys=True))) == saved["scores"]
        assert store.count("observation") == store.count("product") == 3
        assert store.count("annotation") == 0 and [row["id"] for row in store.targets()] == [target]


def test_graded_external_reference_view_does_not_create_an_annotation_target(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MACT", molecule="protein")["subject_refs"]
        reference = pinned_rna_reference(store)
        registry = ToolRegistry(store, clients=LocalOnly())
        result = registry.execute("sequence.view", {"subject_ref": reference["id"],
            "molecule": "rna", "orientation": "reverse_complement"}, operation_key="external-view")
        product = product_from_response(store, result)
        assert product_sequence(store, product) == "GCAU"
        grading, = source_tool_gradings(store, result["result"]["source_ref"])
        assert grading["sheet"]["subject_ref"] == reference["id"]
        coverage, = grading["scores"]["output_source_coverage"]
        assert coverage["subject_ref"] == reference["id"] and coverage["unit"] == "nt"
        assert coverage["distinct_source_position_count"] == coverage["source_position_occurrence_count"] == 4
        assert coverage["repeated_source_position_count"] == 0
        assert product["footprint"] == [] and store.roots(product["id"]) == []
        assert [row["id"] for row in store.targets()] == [target]
        assert store.count("observation") == 1 and store.count("annotation") == 0
