"""Replay the full saved Codon examples against the installed pure modules."""
from pathlib import Path
import builtins
from copy import deepcopy
import gzip
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
from unittest.mock import patch
import urllib.request
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode import bvbrc_codon_tree_calculators as calc
from gene_annotation_episode import bvbrc_codon_tree_native as native
from gene_annotation_episode import phylogeny_calculation_contracts as checks
from gene_annotation_episode import phylogeny_format_contracts as format_checks
from gene_annotation_episode import phylogeny_formats as formats


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    installation_path = HERE / "PRODUCTION_CODON_INSTALLATION_001.json"
    installation = json.loads(installation_path.read_text())
    for row in installation["files"]:
        assert digest(ROOT / row["path"]) == row["installed_sha256"], row["path"]
    modules = (calc, native, checks, format_checks, formats)
    for module in modules:
        assert Path(module.__file__).resolve().parent == ROOT / "gene_annotation_episode"
    operand_path = HERE / "codon-calculators-verification/SAVED_OPERANDS_004.json"
    result_path = HERE / "codon-calculators-verification/FILLED_COMPONENTS_004.json.gz"
    assert digest(operand_path) == "6403db6b821b2674aa376a310c3f1e617e8dd867eac6697b32963a5514e8c941"
    assert digest(result_path) == "7fad371ac5707f9e6ab811a4999e97dbae7c3522b0c251cf6f45a3d2ff3e74e7"
    stored = json.loads(operand_path.read_text())
    expected = json.loads(gzip.decompress(result_path.read_bytes()))
    before = deepcopy(stored)
    calls = {name: getattr(calc, name) for name in calc.__all__}
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("forbidden I/O, process, network, parser or import during saved calculation")

    targets = [(builtins, "open"), (io, "open"), (os, "open"), (os, "system"),
               (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"),
               (socket, "create_connection"), (urllib.request, "urlopen"),
               (builtins, "__import__")]
    targets += [(module, name) for module in (formats, native) for name in dir(module)
                if name.startswith("parse_")]
    guards = [patch.object(module, name, denied) for module, name in targets]
    for guard in guards:
        guard.start()
    try:
        actual = []
        for case in stored["cases"]:
            component = calls[case["function"]](*case["args"], **case["kwargs"])
            actual.append({"case_id": case["case_id"], "component": component,
                           "requirements": calc.codon_calculation_requirements(component)})
    finally:
        for guard in reversed(guards):
            guard.stop()
    assert actual == expected
    assert stored == before and not attempts
    suite_path = HERE / "production-codon-tests-001.xml"
    suite = ET.parse(suite_path).getroot().find("testsuite")
    assert {k: int(suite.attrib[k]) for k in ("tests", "failures", "errors", "skipped")} == {
        "tests": 250, "failures": 0, "errors": 0, "skipped": 0}
    index = {row["case_id"]: row["component"] for row in actual}
    matrix = index["retained_official_final_alignment"]
    report = {
        "scope": "Two installed Codon modules: supplied-byte parsers and pure saved-sheet calculators",
        "tests": {"passed": 250, "failed": 0, "errors": 0, "skipped": 0},
        "saved_cases_reproduced": len(actual), "forbidden_access_attempts": len(attempts),
        "saved_inputs_unchanged": stored == before,
        "module_origins": {module.__name__: str(Path(module.__file__).resolve()) for module in modules},
        "native_final_matrix": {"rows": matrix["n_rows"]["value"],
            "columns": matrix["n_columns"]["value"], "cells": matrix["gap_fraction"]["denominator"],
            "gaps": matrix["gaps"]["value"],
            "sum_squared_frequency": matrix["literal_nongap_sum_squared_frequency"]["value"],
            "mean_squared_frequency": matrix["literal_nongap_mean_squared_frequency"]["value"],
            "ranking_statistic": matrix["native_family_ranking_score"]["value"]},
        "native_origin": "Retained official repository final alignment; historical and boundary cases are explicitly synthetic",
        "files": {str(p.relative_to(ROOT)): digest(p) for p in [
            installation_path, operand_path, result_path, suite_path, Path(__file__),
            *[Path(module.__file__).resolve() for module in modules]]},
        "provider_sheet_assembly_verified": False,
        "selected_tool_to_episode_return_verified": False,
        "live_execution_verified": False,
    }
    with (HERE / "PRODUCTION_CODON_VERIFICATION_001.json").open("x") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: report[k] for k in ("tests", "saved_cases_reproduced",
          "forbidden_access_attempts", "saved_inputs_unchanged", "native_final_matrix")}))


if __name__ == "__main__":
    main()
