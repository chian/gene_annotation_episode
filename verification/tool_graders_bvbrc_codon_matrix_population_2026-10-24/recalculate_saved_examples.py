"""Reproduce historical and new saved operands with the production calculator.

--prepare writes only this directory's new examples from the new test fixtures.
Replay reads saved JSON/gzip before disabling access during all calculations.
Historical operands, components, source stages and receipts are read-only.
"""
from __future__ import annotations

import argparse
import builtins
from copy import deepcopy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
from unittest.mock import patch
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode import bvbrc_codon_tree_calculators as calc
from gene_annotation_episode import bvbrc_codon_tree_native as native
from gene_annotation_episode import phylogeny_calculation_contracts as checks
from gene_annotation_episode import phylogeny_format_contracts as format_checks
from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import phylogeny_raxml_inputs as raxml

HISTORICAL = ROOT / "verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/codon-calculators-verification"
NEW_OPERANDS = HERE / "SAVED_OPERANDS.json"
NEW_FILLED = HERE / "FILLED_COMPONENTS.json"
FUNCTIONS = {name: getattr(calc, name) for name in calc.__all__ if name != "codon_calculation_requirements"}


def invoke(cases):
    result = []
    for case in cases:
        component = FUNCTIONS[case["function"]](*case["args"], **case["kwargs"])
        result.append({"case_id": case["case_id"], "component": component,
                       "requirements": calc.codon_calculation_requirements(component)})
    return result


def prepare():
    fixtures = runpy.run_path(str(ROOT / "tests/test_bvbrc_codon_tree_matrix_population.py"))
    selected = [
        ("complete_main_subset_with_external_memberships", fixtures["scoped_sheet"](), "main", "synthetic"),
        ("complete_empty_main_with_unrelated_memberships", fixtures["scoped_sheet"](empty=True), "main", "synthetic"),
        ("external_optional_scope_without_matrix_rows", fixtures["scoped_sheet"](), "optional", "synthetic"),
        ("retained_memberships_explicit_single_genome_scope", fixtures["retained_subset_sheet"](), "main",
         "retained_native_membership_and_gene_table_with_explicit_test_subset_not_live_main_request"),
    ]
    cases = [{"case_id": name, "function": "codon_family_population_components", "args": [sheet],
              "kwargs": {"family_population_id": "returned", "genome_population_id": genome},
              "evidence_kind": kind} for name, sheet, genome, kind in selected]
    NEW_OPERANDS.write_text(json.dumps({"cases": cases}, indent=2) + "\n")
    NEW_FILLED.write_text(json.dumps(invoke(cases), indent=2) + "\n")


def sha(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def recalculate():
    modules = (calc, native, checks, format_checks, formats, raxml)
    for module in modules:
        assert Path(module.__file__).resolve().parent == ROOT / "gene_annotation_episode", module.__file__
    old_operands = HISTORICAL / "SAVED_OPERANDS_004.json"
    old_filled = HISTORICAL / "FILLED_COMPONENTS_004.json.gz"
    historical = json.loads(old_operands.read_text())
    historical_expected = json.loads(gzip.decompress(old_filled.read_bytes()))
    new = json.loads(NEW_OPERANDS.read_text())
    new_expected = json.loads(NEW_FILLED.read_text())
    before = deepcopy((historical, new))
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Forbidden access or native parsing during saved recalculation")

    targets = [(builtins, "open"), (io, "open"), (os, "open"), (os, "system"),
               (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"),
               (socket, "create_connection"), (urllib.request, "urlopen"), (builtins, "__import__")]
    targets += [(module, name) for module in (native, formats, raxml)
                for name in dir(module) if name.startswith("parse_")]
    guards = [patch.object(module, name, denied) for module, name in targets]
    for guard in guards:
        guard.start()
    try:
        historical_actual = invoke(historical["cases"])
        new_actual = invoke(new["cases"])
    finally:
        for guard in reversed(guards):
            guard.stop()
    assert len(historical_actual) == 31
    assert historical_actual == historical_expected
    assert new_actual == new_expected
    assert (historical, new) == before
    assert attempts == []
    report = {
        "historical_cases_reproduced": len(historical_actual),
        "historical_components_and_requirements_exactly_equal": True,
        "historical_case_ids": [case["case_id"] for case in historical_actual],
        "new_cases_reproduced": len(new_actual), "new_components_and_requirements_exactly_equal": True,
        "new_case_ids": [case["case_id"] for case in new_actual],
        "inputs_unchanged": True, "forbidden_access_attempts": len(attempts),
        "guarded_entry_points": [module.__name__ + "." + name for module, name in targets],
        "module_origins": {module.__name__: module.__file__ for module in modules},
        "file_hashes": [sha(path) for path in (old_operands, old_filled, NEW_OPERANDS, NEW_FILLED,
            Path(calc.__file__), Path(__file__), ROOT / "tests/test_bvbrc_codon_tree_matrix_population.py")],
        "limitations": ["Numerical recalculation only; no authenticated service or episode typed-return path exercised.",
            "Native memberships and final-alignment history are retained artifacts, not a new live scientific run.",
            "New synthetic sheets exercise the calculator operands, not the provider's full source-validation contract."],
    }
    (HERE / "SAVED_RECALCULATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("historical_cases_reproduced",
        "historical_components_and_requirements_exactly_equal", "new_cases_reproduced", "inputs_unchanged",
        "forbidden_access_attempts")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    recalculate()
