"""Save complete Codon operands/results and reproduce them without acquisition.

Run from staging with the repository's absolute .venv Python and staging
PYTHONPATH. --prepare reads the retained native example and owned test fixture
constructors. Replay loads saved operands/results before denying file, network,
process, import/model-client loading and parser access inside calculations.
"""
from __future__ import annotations

import argparse
import ast
import builtins
from copy import deepcopy
from fractions import Fraction
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import runpy
import socket
import subprocess
from unittest.mock import patch
import urllib.request

from gene_annotation_episode import bvbrc_codon_tree_calculators as calc
from gene_annotation_episode import phylogeny_calculation_contracts as checks
from gene_annotation_episode import phylogeny_format_contracts as format_checks
from gene_annotation_episode import phylogeny_formats as formats


HERE = Path(__file__).resolve().parent
STAGING = HERE.parent / "staging"
REPO = STAGING.parents[2]
GOAL = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
SOURCE = REPO / "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/codon_trees"
OPERANDS = HERE / "SAVED_OPERANDS_004.json"
FILLED = HERE / "FILLED_COMPONENTS_004.json.gz"
FUNCTIONS = {name: getattr(calc, name) for name in calc.__all__ if name != "codon_calculation_requirements"}


def invoke(cases):
    outputs = []
    for case in cases:
        component = FUNCTIONS[case["function"]](*case["args"], **case["kwargs"])
        outputs.append({"case_id": case["case_id"], "component": component,
                        "requirements": calc.codon_calculation_requirements(component)})
    return outputs


def native_function_comparison(doc, component):
    """Run only the inspected upstream arithmetic function, not its program.

    No upstream module imports or scientific job executes. The small adapter
    supplies the exact access operations used by calcAlignmentStats; all original
    saved row strings and labels are passed unchanged.
    """
    source = (SOURCE / "lib/phylocode.py").read_text()
    syntax = ast.parse(source)
    function = next(node for node in syntax.body if isinstance(node, ast.FunctionDef) and node.name == "calcAlignmentStats")
    namespace = {"log": math.log}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "retained_phylocode_calcAlignmentStats", "exec"), namespace)
    class Record:
        def __init__(self, row):
            self.id = row["member_label"]
    class SavedAlignment:
        def __len__(self):
            return len(doc["rows"])
        def get_alignment_length(self):
            return doc["observed_column_count"]
        def __iter__(self):
            return iter(Record(row) for row in doc["rows"])
        def __getitem__(self, index):
            rows, column = index
            assert rows == slice(None, None, None)
            return "".join(row["sequence"][column] for row in doc["rows"])
    native = namespace["calcAlignmentStats"](SavedAlignment())
    differences = {}
    for native_key, field in (("gaps", "gaps"), ("prop_gaps", "gap_fraction"),
                              ("sum_squared_freq", "literal_nongap_sum_squared_frequency"),
                              ("mean_squared_freq", "literal_nongap_mean_squared_frequency")):
        differences[field] = component[field]["value"] - native[native_key]
        assert math.isclose(component[field]["value"], native[native_key], rel_tol=1e-12, abs_tol=1e-12)
    for row, computed in zip(doc["rows"], component["rows"]):
        assert math.isclose(native["perseq_meanlogfreq"][row["member_label"]],
                            computed["mean_log2_literal_frequency"]["value"], rel_tol=1e-12, abs_tol=1e-12)
    return {"kind": "isolated_retained_native_arithmetic_function_on_supplied_final_rows",
            "not_a_scientific_program_execution": True, "native_function_output": native,
            "computed_minus_native": differences,
            "floating_point_note": "Calculator uses math.fsum; upstream accumulates successive floating-point additions.",
            "limitation": "Final alignment measurements do not reconstruct any historical pre-trim family rows or same-genome denominator."}


def prepare():
    f = runpy.run_path(str(STAGING / "tests/test_bvbrc_codon_tree_calculators.py"))
    cases = []
    def add(case_id, function, args, kwargs, kind="constructed_numerical_fixture_not_observed_biology"):
        cases.append({"case_id": case_id, "function": function, "args": args, "kwargs": kwargs, "evidence_kind": kind})
    def literal(case_id, doc, pop=None, kind="constructed_numerical_fixture_not_observed_biology"):
        add(case_id, "native_codon_literal_statistics", [doc], {"population": f["apop"](doc) if pop is None else pop}, kind)
    def families(case_id, value):
        add(case_id, "codon_family_population_components", [value],
            {"family_population_id": "families/evaluated", "genome_population_id": "genomes/main"})
    def history(case_id, op):
        add(case_id, "native_codon_worst_sequence_ratios", [], op)
    literal("four_row_literal", f["alignment"]())
    literal("empty_alignment", f["alignment"](()))
    literal("literal_case_gap_and_x", f["alignment"](("X-a.*", "X-A.*")))
    literal("truncated_alignment", f["alignment"](("AC", "A"), complete="truncated"))
    value = f["sheet"]()
    for index, representation in enumerate(("protein", "coding_nucleotide")):
        value["families"][0]["memberships"].append({"representation": representation,
            "feature_ids": ["F1_G1a", "F1_G1b", "F1_G2", "F1_G3"], "genome_ids": ["G1", "G2", "G3"],
            "deleted_feature_ids": [], "missing_codon_feature_ids": [], "source_table_id": "synthetic/dependent", "source_row_index": index})
    families("four_genome_family_copies_dependent_representations", value)
    families("accepted_provider_assembly_and_actual_reader_outcome", f["enriched_sheet"]())
    value = f["sheet"]()
    value["populations"]["genomes"][0]["genome_ids"] = ["G1"]
    value["families"][0]["matrix"][0]["feature_ids"] += ["additional_1", "additional_2"]
    families("negative_initial_rank", value)
    value = f["sheet"]()
    value["populations"]["genomes"].clear()
    families("missing_genome_population", value)
    value = f["sheet"]()
    value["populations"]["families"][0]["completeness"] = "unknown"
    families("unknown_family_population_known_individual_families", value)
    value = f["sheet"]()
    value["families"][0]["matrix"].pop()
    families("missing_genome_membership_not_absence", value)
    value = f["sheet"]()
    value["populations"]["genomes"][0]["genome_ids"] = []
    families("empty_genome_population", value)
    value = f["sheet"]()
    value["populations"]["genomes"][0]["genome_ids"] = []
    value["families"] = []
    families("empty_genome_population_no_unused_family_records", value)
    history("complete_historical_ratios", f["historical"]())
    op = f["historical"]()
    op["pretrim_sequence_rows"].pop()
    history("missing_historical_feature_genome_unknown", op)
    op = f["historical"]()
    op["pretrim_sequence_rows"][-1]["value"].update(value=None, state="missing")
    history("missing_historical_value_genome_known", op)
    op = f["historical"]()
    op["evaluated_family_population"]["population"]["completeness"] = "truncated"
    history("truncated_evaluated_family_population", op)
    op = f["historical"]()
    op["pretrim_sequence_rows"][0]["value"]["value"] = .2
    history("positive_historical_value_incompatible", op)
    op = f["historical"]()
    op["pretrim_sequence_rows"][0]["value"].update(value=None, state="incompatible")
    history("incompatible_historical_measurement_without_acquisition_need", op)
    op = f["historical"]()
    for row in op["pretrim_sequence_rows"]:
        row["value"]["value"] = 0
    history("zero_historical_values", op)
    op = f["historical"]()
    op["pretrim_sequence_rows"] = []
    for membership in op["evaluated_family_population"]["expected_sequence_memberships"]:
        membership["feature_ids"] = []
    history("empty_expected_sequence_populations", op)
    for family_state, membership_state in (("complete", "complete"), ("unknown", "complete"),
            ("partial", "complete"), ("truncated", "complete"), ("complete", "unknown"),
            ("complete", "partial"), ("complete", "truncated"), ("unknown", "unknown")):
        history("empty_historical_" + family_state + "_" + membership_state, {
            "pretrim_sequence_rows": [], "evaluated_family_population": {
                "population": f["family_population"]([], complete=family_state), "expected_sequence_memberships": [],
                "completeness": membership_state}})
    op = f["historical"]()
    op["pretrim_sequence_rows"] = []
    history("known_expected_families_no_supplied_rows", op)
    op = f["historical"]()
    op["pretrim_sequence_rows"][0]["value"].update(value=None, state="missing", requirement_ids=[
        "phylogeny/original%2Fpretrim/pretrim_sequence_measurement_required"])
    history("retained_original_missing_requirement", op)
    doc = f["native_alignment"].__wrapped__()
    literal("retained_official_final_alignment", doc, kind="retained_official_repository_example_not_live_service")
    stored = {"cases": cases, "qualification": "Synthetic historical inputs and retained final matrix are distinct evidence kinds; no live service or custody/episode path verified."}
    OPERANDS.write_text(json.dumps(stored, sort_keys=True, separators=(",", ":")) + "\n")
    filled = invoke(cases)
    FILLED.write_bytes(gzip.compress(json.dumps(filled, sort_keys=True, separators=(",", ":")).encode(), mtime=0))
    comparison = native_function_comparison(doc, filled[-1]["component"])
    (HERE / "NATIVE_ARITHMETIC_COMPARISON_004.json").write_text(json.dumps(comparison, indent=2) + "\n")


def recalculate():
    for module in (calc, checks, format_checks, formats):
        assert Path(module.__file__).resolve().parent == STAGING / "gene_annotation_episode", module.__file__
    stored = json.loads(OPERANDS.read_text())
    expected = json.loads(gzip.decompress(FILLED.read_bytes()))
    before = deepcopy(stored)
    attempts = []
    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Forbidden I/O, process, network, model-client loading or parser access")
    targets = [(builtins, "open"), (io, "open"), (os, "open"), (os, "system"),
        (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"), (socket, "create_connection"),
        (urllib.request, "urlopen"), (builtins, "__import__")]
    targets += [(formats, name) for name in dir(formats) if name.startswith("parse_")]
    guards = [patch.object(module, name, denied) for module, name in targets]
    for guard in guards:
        guard.start()
    try:
        actual = invoke(stored["cases"])
    finally:
        for guard in reversed(guards):
            guard.stop()
    assert actual == expected
    assert stored == before
    assert attempts == []
    index = {row["case_id"]: row["component"] for row in actual}
    native = index["retained_official_final_alignment"]
    summary = {"cases_reproduced": len(actual), "forbidden_access_attempts": 0, "inputs_unchanged": True,
        "source_parsers_disabled_during_recalculation": True,
        "model_access": "No model dependency; imports/model-client loading, all network and process entry points disabled during calls.",
        "native_final_matrix": {"rows": native["n_rows"]["value"], "columns": native["n_columns"]["value"],
            "cells": native["gap_fraction"]["denominator"], "gaps": native["gaps"]["value"],
            "sum_squared_frequency": native["literal_nongap_sum_squared_frequency"]["value"],
            "mean_squared_frequency": native["literal_nongap_mean_squared_frequency"]["value"],
            "ranking_statistic": native["native_family_ranking_score"]["value"],
            "row_means": [r["mean_log2_literal_frequency"]["value"] for r in native["rows"]]},
        "module_origins": {m.__name__: m.__file__ for m in (calc, checks, format_checks, formats)},
        "requirements": {r["case_id"]: r["requirements"] for r in actual},
        "limitations": ["No provider or C4 artifact-custody assembly verified.", "No episode typed return path verified.",
                        "No live BV-BRC job or HPC execution.", "Retained final alignment does not reconstruct historical pre-trim populations."]}
    files = [GOAL, HERE.parent / "CODON_CALCULATIONS_CONTRACT.md", HERE.parent / "CODON_CALCULATIONS_ADDENDUM_001.md", HERE.parent / "CALCULATOR_CONTRACT.md",
        HERE.parent / "CALCULATOR_CONTRACT_ADDENDUM_001.md", Path(__file__),
        STAGING / "tests/test_bvbrc_codon_tree_calculators.py", OPERANDS, FILLED,
        SOURCE / "lib/phylocode.py", SOURCE / "scripts/p3x-build-codon-tree.py"]
    files.extend(Path(module.__file__) for module in (calc, checks, format_checks, formats))
    files.extend((STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24" / name)
                 for name in ("BOUNDARY_PROPOSAL.md", "CONTRACT_SHAPES.md"))
    files.extend((STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_provider_handoffs_2026-10-24" / name)
                 for name in ("ADDITIVE_CONTRACT.md", "ACCEPTANCE_001.md"))
    native_path = STAGING.parents[1] / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24/official_example/test9_genome_dir/test9_genome_8taxa_10cds_10proteins_codonAndProteins.phy"
    files.append(native_path)
    summary["file_hashes"] = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in files]
    (HERE / "SAVED_RECALCULATION_004.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("cases_reproduced", "forbidden_access_attempts", "inputs_unchanged", "native_final_matrix")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    recalculate()
