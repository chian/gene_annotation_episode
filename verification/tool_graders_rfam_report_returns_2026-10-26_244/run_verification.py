"""Operator-only offline return checks with the established bounded runner."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


root = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir()
temporary = directory / "temporary"
temporary.mkdir()
command = [str(root / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
    str(root / "tests/test_rfam_report_publication_returns.py"),
    "--basetemp=" + str(temporary / "pytest"), "--junitxml=" + str(directory / "tests.xml"), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {"PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
    "XDG_CACHE_HOME": str(directory / "cache")}
paths = [root / path for path in ["tests/test_rfam_report_publication_returns.py",
    "tests/test_rfam_batch_returns.py", "tests/test_rfam_batch_publication.py", *[
    "gene_annotation_episode/" + name + ".py" for name in (
        "rfam_batch_returns", "rfam_batch_publication", "rfam_batch_report", "rfam_batch_report_contracts", "rfam_batch_report_grader", "rfam_batch_report_views", "rfam_batch_contracts", "rfam_batch_inputs",
        "rfam_batch_grader", "rfam_batch_views", "rfam_batch_alignment", "rfam_batch_table",
        "rfam_batch_table_grader", "rfam_batch_table_views", "api_rfam", "api_service_execution",
        "api_services", "episode_return_records", "communication", "state", "tools",
        "form_reference_validation", "execution_episodes")]]]
paths += [root / "verification/tool_graders_rfam_transport_2026-10-26_234/live" / name
    for name in ("multi/input.seq", "multi/input-manifest.json", "multi/001-submit/snapshot.json",
        "multi/001-submit/response.body", "multi/005-fetch-out/snapshot.json", "multi/005-fetch-out/response.body")]
def hashes():
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
before = hashes()
(directory / "before-run.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(), "source_sha256_before": before}, sort_keys=True, indent=2) + "\n")
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
after = hashes()
receipt = {"command": command, "policy": policy.to_dict(), "environment": environment,
    "returncode": result.returncode, "stdout_path": str(result.stdout_path),
    "stderr_path": str(result.stderr_path), "metadata": result.metadata,
    "source_sha256": after, "source_sha256_before": before,
    "source_changed_during_run": [path for path in before if before[path] != after[path]]}
(directory / "verification-receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "verification-receipt.json")}))
raise SystemExit(result.returncode)
