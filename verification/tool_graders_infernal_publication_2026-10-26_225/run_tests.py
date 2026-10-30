"""Run publication checks under the user's explicit local resource allocation."""
from pathlib import Path
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).resolve().parent
label, *extra = sys.argv[1:]
working = DIRECTORY / ("run_" + label)
working.mkdir()
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
    str(ROOT / "tests/test_native_infernal_publication.py"),
    "--junitxml=" + str(DIRECTORY / ("tests_" + label + ".xml")),
    "--basetemp=" + str(working / "pytest"), *extra]
result = run_local_job(command, cwd=working,
    policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None),
    stdout_path=working / "tests.stdout",
    stderr_path=working / "tests.stderr",
    env={"PYTHONPATH": str(ROOT)})
receipt = {"command": command, "returncode": result.returncode, "metadata": result.metadata}
(DIRECTORY / ("TEST_RECEIPT_" + label + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
