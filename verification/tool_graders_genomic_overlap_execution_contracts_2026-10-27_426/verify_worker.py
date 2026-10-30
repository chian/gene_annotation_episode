"""Bounded pure validation and supplied synthetic numerical examples."""
import json
from importlib import import_module
from pathlib import Path
import sys

import pytest

attempt, snapshot = map(Path, sys.argv[1:])
status = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(attempt / "temporary/pytest"),
    "--rootdir", str(snapshot), "--junitxml", str(attempt / "pytest.xml"),
    str(snapshot / "tests/test_native_genomic_overlap_contracts.py"),
    str(snapshot / "tests/test_native_genomic_overlap_tool_info.py")])
if status:
    raise SystemExit(status)
fixtures = import_module("verification.tool_graders_genomic_overlap_execution_contracts_2026-10-27_426.fixtures")
example = fixtures.numerical_example()
(attempt / "FILLED_EXAMPLE.json").write_text(json.dumps(example, indent=2) + "\n")
print(json.dumps({"evidence": example["evidence_label"], "native_execution_claim": False,
    "pair_counts": [row["unfiltered"]["native_pair_count"] for row in example["components"]["pairs"]],
    "pairwise_width_sums_bp": [row["unfiltered"]["pairwise_overlap_bp_sum"] for row in example["components"]["pairs"]],
    "unique_intersections_bp": [row["unfiltered"]["intersection_union_bp"] for row in example["components"]["pairs"]],
    "jaccard": [row["unfiltered"]["jaccard_bp"]["value"] for row in example["components"]["pairs"]]}))
