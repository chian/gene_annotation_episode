"""Run L1 checks under the existing caller-owned local resource boundary."""
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
tests = sys.argv[2:] or ["tests/test_hmmer_preparation_practical_integration.py"]
files = [Path(__file__), *[ROOT / name for name in (
    "gene_annotation_episode/practical_execution_records.py",
    "gene_annotation_episode/practical_execution_operations.py",
    "gene_annotation_episode/execution_progress.py",
    "gene_annotation_episode/practical_execution_state.py",
    "gene_annotation_episode/practical_resource_episodes.py",
    "gene_annotation_episode/practical_receipt_information.py",
    "gene_annotation_episode/native_hmmer_preparation_local.py",
    "gene_annotation_episode/native_hmmer_preparation_contracts.py",
    "gene_annotation_episode/native_hmmer_preparation_job_schema.py",
    "gene_annotation_episode/native_hmmer_preparation_driver.py",
    "gene_annotation_episode/native_hmmer_preparation_tool_info.py",
    "gene_annotation_episode/native_hmmer_preparation_acquisition.py",
    "gene_annotation_episode/hmmer_preparation_result_views.py",
    "gene_annotation_episode/local_jobs.py", "gene_annotation_episode/native_lifecycle.py",
    "gene_annotation_episode/episode_monitoring.py", "gene_annotation_episode/progress_records.py",
    "tests/test_hmmer_preparation_practical_integration.py")]]
files += [ROOT / test for test in tests if (ROOT / test).is_file()]
for batch in ("producer_2026-10-26_267", "capture_2026-10-26_270"):
    directory = ROOT / ("verification/tool_graders_hmmer_preparation_" + batch + "/check005/temporary")
    files += sorted(directory.glob("test_actual_all_selected_modes*/plan.json"))
hashes = {str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path): digest(path)
    for path in dict.fromkeys(files)}
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
    *[str(ROOT / test) if (ROOT / test).is_file() else test for test in tests],
    "-o", "cache_dir=" + str(output / "pytest-cache"), "--basetemp=" + str(output / "temporary"),
    "--junitxml=" + str(output / "junit.xml")]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(output / "intent.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(),
    "source_hashes": hashes, "scope": "L1 practical operations, original target progress, and selected regression checks"}, indent=2) + "\n")
result = run_local_job(command, cwd=output, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(output)})
(output / "receipt.json").write_text(json.dumps({"returncode": result.returncode,
    "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}, indent=2) + "\n")
changed = [name for name, sha in hashes.items() if digest(ROOT / name) != sha]
(output / "source_stability.json").write_text(json.dumps({"changed_during_run": changed}, indent=2) + "\n")
print(json.dumps({"directory": str(output), "returncode": result.returncode, "changed_during_run": changed,
    "stdout_tail": result.stdout_path.read_text()[-7000:], "stderr_tail": result.stderr_path.read_text()[-1500:]}))
raise SystemExit(result.returncode)
