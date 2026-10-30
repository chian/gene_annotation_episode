"""Run one explicitly chosen verification command under the fixed local limits."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
label, mode = sys.argv[1:3]
if mode not in {"capture", "tests"} or (mode == "capture" and label != "original_job_out_001"):
    raise SystemExit("Explicit capture or tests mode required")
directory = HERE / label
directory.mkdir()
temporary = directory / "temporary"
temporary.mkdir()
paths = [*sorted((ROOT / "gene_annotation_episode").glob("*.py")),
    *sorted((ROOT / "method_loop").rglob("*.py")), *sorted(HERE.glob("*.py")),
    ROOT / "tests/test_rfam_composed_workflow.py",
    ROOT / "verification/tool_graders_rfam_implementation_2026-10-26_234/REPORT_WORKFLOW_WORKLOAD_010.md"]
new_test = ROOT / "tests/test_rfam_report_composed_workflow.py"
if new_test.exists():
    paths.append(new_test)


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def write(name, value):
    (directory / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(directory / "cache"),
    "RFAM_REPORT_WORKFLOW_RUNS": str(directory / "runs")}
command = ([str(ROOT / ".venv/bin/python"), str(HERE / "capture_original_out.py")] if mode == "capture"
    else [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
        str(new_test), "--basetemp", str(temporary / "pytest"), "--junitxml", str(directory / "tests.xml"),
        *sys.argv[3:]])
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
before = hashes()
write("intent.json", {"command": command, "environment": environment,
    "policy": policy.to_dict(), "source_hashes_before": before})
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
after = hashes()
write("receipt.json", {"command": command, "environment": environment, "policy": policy.to_dict(),
    "source_hashes_before": before, "source_hashes_after": after,
    "changed_files": [path for path in before if before[path] != after.get(path)],
    "returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)})
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
raise SystemExit(result.returncode)
