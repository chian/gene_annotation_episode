"""Bounded pure checks and retained supplied-record numerical example."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

import pytest


attempt, snapshot = map(Path, sys.argv[1:])
tests = ["test_genomic_overlap_inputs.py", "test_genomic_overlap_calculations.py",
         "test_genomic_overlap_result_views.py", "test_genomic_overlap_analytic_capture_loss.py"]
status = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(attempt / "temporary/pytest"),
    "--rootdir", str(snapshot), "--junitxml", str(attempt / "pytest.xml"),
    *(str(snapshot / "tests" / name) for name in tests)])
counts = {}
for case in ET.parse(attempt / "pytest.xml").iter("testcase"):
    name = case.attrib["classname"]
    counts[name] = counts.get(name, 0) + 1
(attempt / "test_counts.json").write_text(json.dumps(counts, indent=2) + "\n")
if status:
    raise SystemExit(status)

from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
from gene_annotation_episode.genomic_overlap_result_views import project_genomic_overlap_result
from test_genomic_overlap_analytic_capture_loss import canonical, mixed_example, selector
from test_genomic_overlap_inputs import PARAMETERS

original, current = mixed_example()
components = calculate_genomic_overlap_components(current, parameters=PARAMETERS)
changed = calculate_genomic_overlap_components(current, parameters={**PARAMETERS, "minimum_overlap_bp": 4})
projection = project_genomic_overlap_result(current, components, selector=selector(current))
for name, value in (("original-sheet.json", original), ("current-sheet.json", current),
        ("original-receipts.json", [pair["receipt"] for pair in original["comparisons"]]),
        ("current-receipts.json", [pair["receipt"] for pair in current["comparisons"]]),
        ("components-minimum-1.json", components), ("components-minimum-4.json", changed),
        ("projection-ab-only.json", projection)):
    (attempt / name).write_bytes(canonical(value))
summary = {"evidence_label": "hand_worked_synthetic_supplied_records", "native_execution_claim": False,
    "filesystem_recovery_or_custody_claim": False, "test_counts": counts,
    "sets": [{key: row[key] for key in ("set_key", "result_extent", "input_data_row_count",
        "valid_region_count", "region_count", "union_bp")} for row in components["sets"]],
    "pairs": [{"comparison_key": row["comparison_key"], "result_extent": row["result_extent"],
        "jaccard_bp": row["unfiltered"]["jaccard_bp"], "observed": row["observed"]}
        for row in components["pairs"]],
    "minimum_4_ab_selected": changed["pairs"][0]["selected"],
    "ab_only_failures": projection["failures"]}
(attempt / "FILLED_EXAMPLE.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
