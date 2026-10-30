"""Run focused tests from readonly pins and retain the exact worked projection."""
from pathlib import Path
import json
import sys

import pytest

from gene_annotation_episode.genomic_overlap_result_views import project_genomic_overlap_result


attempt, snapshot = map(Path, sys.argv[1:3])
phase = sys.argv[3]
arguments = ["-q", "-p", "no:cacheprovider", "--basetemp", str(attempt / "temporary/pytest"),
    "--rootdir", str(snapshot), "--junitxml", str(attempt / "pytest.xml"),
    str(snapshot / "tests/test_genomic_overlap_result_views.py")]
if phase == "projection":
    arguments.extend(["-k", "not joined"])
status = pytest.main(arguments)
if status:
    raise SystemExit(status)
worked = json.loads((snapshot / "verification/tool_graders_genomic_overlap_contract_2026-10-27_418/WORKED_EXAMPLE.json").read_text())
result = project_genomic_overlap_result(worked["sheet"], worked["components"], selector=worked["selector"])
(attempt / "worked_projection.json").write_text(json.dumps(result, indent=2) + "\n")
assert result == worked["requested_return"]["overlap"]
print(json.dumps({"evidence": "hand_worked_supplied_fixture", "phase": phase,
    "measurements": result["pair_rows"][0]["measurements"],
    "result_extent": result["result_extent"], "reference_relation": result["pair_rows"][0]["reference_relation"]}))
