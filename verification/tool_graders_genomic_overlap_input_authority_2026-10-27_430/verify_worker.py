"""Run actual Store/receipt authority fixtures inside the selected local job."""
import json
from pathlib import Path
import sys

import pytest


attempt, snapshot = map(Path, sys.argv[1:])
status = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(attempt / "temporary/pytest"),
    "--rootdir", str(snapshot), "--junitxml", str(attempt / "pytest.xml"),
    str(snapshot / "tests/test_genomic_overlap_operands.py")])
print(json.dumps({"verification": "actual Store and frozen receipt metadata authority",
    "native_overlap_execution": False, "scientific_calculation": False,
    "complete_episode_path": False, "pytest_exit_code": status}))
raise SystemExit(status)
