"""Prepare explicit verification operands, then reproduce saved components.

Run from staging with the repository's absolute .venv Python. --prepare loads
retained native fixtures and the owned test constructors. Recalculation loads
saved JSON before denying file/network/process/import access inside calculator
calls. This verifies pure shared arithmetic, not provider or episode binding.
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

from gene_annotation_episode import phylogeny_calculators as calc
from gene_annotation_episode import phylogeny_calculation_contracts as checks
from gene_annotation_episode import phylogeny_format_contracts as format_checks
from gene_annotation_episode import phylogeny_formats as formats


OUTPUT = Path(__file__).resolve().parent
STAGING = OUTPUT.parent / "staging"
OPERANDS = OUTPUT / "SAVED_OPERANDS_002.json"
COMPONENTS = OUTPUT / "FILLED_COMPONENTS_002.json.gz"
FUNCTIONS = {name: getattr(calc, name) for name in calc.__all__ if name != "calculation_requirements"}


def invoke(cases):
    return [{"case_id": case["case_id"], "components": FUNCTIONS[case["function"]](*case["args"], **case["kwargs"])}
            for case in cases]


def prepare():
    fixtures = runpy.run_path(str(STAGING / "tests" / "test_phylogeny_calculators.py"))
    f = fixtures
    doc = f["alignment"]()
    original = f["alignment"](("AA-C",))
    gene = f["hand_tree"](lengths={0: 99, 1: 1, 2: 0, 3: -0.5, 4: 2, 5: 3, 6: 4})
    organismal = f["hand_tree"]((("A", "C"), ("B", "D")), name="organismal")
    reps = [f["hand_tree"](name="rep" + str(i)) for i in range(3)] + [f["hand_tree"]((("A", "C"), ("B", "D")), name="rep3")]
    cases = []
    def add(case_id, function, args, kwargs, kind="constructed_hand_arithmetic"):
        cases.append({"case_id": case_id, "evidence_kind": kind, "function": function, "args": args, "kwargs": kwargs})
    add("hand_alignment", "alignment_components", [doc], {"population": f["apop"](doc), "alphabet": "protein", "case_policy": "uppercase", "pairs": [[0, 1]]})
    add("staged_coordinates", "ungapped_coordinate_map", [doc], {"row_indices": [0, 1, 2, 3]})
    maps = [f["correspondence"](original, i, interval) for i, interval in enumerate(([2, 5], [4, 7], None, [7, 8]))]
    add("original_coverage", "original_member_coverage", [original], {"population": f["apop"](original), "members": [f["original_member"](original)], "correspondences": maps})
    add("missing_original_map", "original_member_coverage", [original], {"population": f["apop"](original), "members": [f["original_member"](original)], "correspondences": []})
    add("signed_tree_lengths", "tree_components", [gene], {"leaf_population": f["lpop"](gene), "support_observations": [], "native_measurements": [], "branch_unit": "native_unknown", "pairs": [[2, 3], [2, 5]]})
    add("three_of_four_bootstraps", "bootstrap_split_frequencies", [gene], {"replicates": reps, "replicate_population": f["bootstrap_population"](reps), "tip_join": f["replicate_join"](gene, reps), "method": "rapid_bootstrap"})
    add("function_two_of_four_vs_two_of_three", "function_composition", [], {"population": f["cpop"](), "assignments": [f["function"](0, "A"), f["function"](1, "A"), f["function"](2, "B")]})
    add("taxon_known_denominator", "taxon_components", [], {"population": f["cpop"](), "rank": "species", "assignments": [f["taxon"](0, "s1"), f["taxon"](1, "s1"), f["taxon"](2, "s2")]})
    add("conflicting_topology_rf", "compare_unrooted_relationships", [gene], {"comparison_id": "hand_comparison", "organismal_tree": organismal, "injective_tip_join": f["comparison_join"](gene, organismal)})
    genome_population = f["cpop"](4, kind="genome")
    genome_population["unit"] = "genome"
    genome_taxa = [f["taxon"](0, "X"), f["taxon"](1, "X"), f["taxon"](2, "Y")]
    for row in genome_taxa:
        row["subject"]["kind"] = "genome"
    add("genome_taxon_population", "taxon_components", [], {"population": genome_population, "rank": "species", "assignments": genome_taxa})
    pruning_tree = f["hand_tree"](((("A", "E"), "B"), ("C", "D")), name="five_tips")
    four_tips = f["hand_tree"](name="four_tips")
    add("restricted_split_saved_identity", "compare_unrooted_relationships", [pruning_tree],
        {"comparison_id": "five_to_four", "organismal_tree": four_tips, "injective_tip_join": f["comparison_join"](pruning_tree, four_tips)})
    native = f["native_documents"].__wrapped__()
    aligned = native["alignment"]
    best, supported = native["best"]["trees"][0], native["supported"]["trees"][0]
    bootstrap = native["bootstraps"]["trees"]
    kind = "retained_official_repository_example_not_live_service"
    add("native_codon_matrix", "alignment_components", [aligned], {"population": f["apop"](aligned), "alphabet": "unknown", "case_policy": "literal"}, kind)
    add("native_bootstrap_six_splits", "bootstrap_split_frequencies", [supported], {"replicates": bootstrap, "replicate_population": f["bootstrap_population"](bootstrap), "tip_join": f["replicate_join"](supported, bootstrap), "method": "rapid_bootstrap"}, kind)
    add("native_best_supported_rf", "compare_unrooted_relationships", [best], {"comparison_id": "native_topology_comparison", "organismal_tree": supported, "injective_tip_join": f["comparison_join"](best, supported)}, kind)
    data = {"cases": cases, "native_partitions": native["partitions"],
            "qualification": "Caller-supplied fixture IDs are not C4 custody or episode-return attestations."}
    OPERANDS.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")
    # Persist the complete component values, including every selected site.
    payload = json.dumps(invoke(cases), sort_keys=True, separators=(",", ":")).encode()
    COMPONENTS.write_bytes(gzip.compress(payload, mtime=0))


def recalculate():
    for module in (calc, checks, format_checks, formats):
        assert Path(module.__file__).resolve().parent == STAGING / "gene_annotation_episode", module.__file__
    saved = json.loads(OPERANDS.read_text())
    expected = json.loads(gzip.decompress(COMPONENTS.read_bytes()))
    before = deepcopy(saved)
    forbidden_attempts = []
    def denied(*args, **kwargs):
        forbidden_attempts.append(True)
        raise AssertionError("Forbidden access during saved-data calculation")
    guards = [(builtins, "open"), (io, "open"), (os, "open"), (os, "system"),
              (subprocess, "Popen"), (subprocess, "run"), (socket, "socket"),
              (socket, "create_connection"), (urllib.request, "urlopen"), (builtins, "__import__")]
    active = [patch.object(module, name, denied) for module, name in guards]
    for guard in active:
        guard.start()
    try:
        actual = invoke(saved["cases"])
        requirements = {row["case_id"]: calc.calculation_requirements(row["components"])
                        for row in actual if type(row["components"]) is dict}
    finally:
        for guard in reversed(active):
            guard.stop()
    # Tuple return from ungapped_coordinate_map has the same JSON array meaning.
    actual_json = json.loads(json.dumps(actual, sort_keys=True, separators=(",", ":")))
    assert actual_json == expected
    assert saved == before
    assert not forbidden_attempts
    report = {"cases_reproduced": len(actual), "forbidden_access_attempts": 0, "inputs_unchanged": True,
              "module_origins": {m.__name__: m.__file__ for m in (calc, checks, format_checks, formats)},
              "saved_operands_sha256": hashlib.sha256(OPERANDS.read_bytes()).hexdigest(),
              "filled_components_sha256": hashlib.sha256(COMPONENTS.read_bytes()).hexdigest(),
              "requirements": requirements}
    (OUTPUT / "SAVED_RECALCULATION_002.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("cases_reproduced", "forbidden_access_attempts", "inputs_unchanged")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    recalculate()
