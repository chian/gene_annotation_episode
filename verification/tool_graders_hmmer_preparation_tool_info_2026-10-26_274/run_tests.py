"""Bounded I1 verification only; tests consume retained P1 requests, no native run."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


output = Path(__file__).parent / sys.argv[1]
output.mkdir()
test = ROOT / "tests/test_native_hmmer_preparation_tool_info.py"
paths = [test, Path(__file__), ROOT / "gene_annotation_episode/native_hmmer_preparation_tool_info.py",
    ROOT / "gene_annotation_episode/native_hmmer_preparation_contracts.py",
    ROOT / "gene_annotation_episode/native_hmmer_preparation_job_schema.py",
    ROOT / "gene_annotation_episode/native_hmmer_preparation_driver.py",
    ROOT / "gene_annotation_episode/native_hmmer_preparation_local.py",
    ROOT / "gene_annotation_episode/native_infernal_contracts.py",
    ROOT / "gene_annotation_episode/native_infernal_preparation_tool_info.py",
    ROOT / "gene_annotation_episode/hmmer_preparation_result_views.py",
    ROOT / "gene_annotation_episode/local_jobs.py"]
producer = ROOT / "verification/tool_graders_hmmer_preparation_producer_2026-10-26_267"
cases_path = producer / "check005_native_cases.json"
paths += [cases_path]
cases = [case for case in json.loads(cases_path.read_bytes())["cases"]
    if "/test_actual_all_selected_modes" in case["case"]]
paths += [producer / case["bundle"] for case in cases]
paths += [producer / case["receipt"] for case in cases]
hashes = {str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path): digest(path) for path in paths}
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", str(test),
    "-o", "cache_dir=" + str(output / "pytest-cache"), "--basetemp=" + str(output / "temporary"),
    "--junitxml=" + str(output / "junit.xml"), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(output / "intent.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(),
    "source_hashes": hashes, "native_executions_requested": 0,
    "retained_p1_request_count": len(cases)}, indent=2) + "\n")
result = run_local_job(command, cwd=output, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
(output / "receipt.json").write_text(json.dumps({"returncode": result.returncode,
    "metadata": result.metadata, "stdout_path": str(result.stdout_path),
    "stderr_path": str(result.stderr_path)}, indent=2) + "\n")
changed = [str(path) for path in paths if digest(path) != hashes[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)]]
(output / "source_stability.json").write_text(json.dumps({"changed_during_run": changed}, indent=2) + "\n")
print(json.dumps({"directory": str(output), "returncode": result.returncode,
    "changed_during_run": changed, "stdout_tail": result.stdout_path.read_text()[-6500:],
    "stderr_tail": result.stderr_path.read_text()[-1500:]}))
raise SystemExit(result.returncode)
