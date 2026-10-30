"""Run the one authorized live workload inside the native resource limits."""
import hashlib
import json
from pathlib import Path
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
directory = HERE / "live_001"
directory.mkdir()
temporary = directory / "temporary"
temporary.mkdir()
paths = [*sorted((ROOT / "gene_annotation_episode").glob("*.py")),
    *sorted((ROOT / "method_loop").rglob("*.py")),
    *sorted((ROOT / "research/slotted_process_library/publications/2026-10-24-001").rglob("*.json")),
    HERE / "run_live.py", Path(__file__), ROOT / "tests/test_rfam_composed_workflow.py",
    ROOT / "verification/tool_graders_rfam_implementation_2026-10-26_234/LIVE_WORKLOAD_007.md"]
def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
def write(name, value):
    (directory / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
command = [str(ROOT / ".venv/bin/python"), str(HERE / "run_live.py")]
environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")}
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
before = hashes()
write("intent.json", {"command": command, "environment": environment,
    "policy": policy.to_dict(), "source_hashes_before": before})
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
after = hashes()
loaded = json.loads((directory / "loaded-source-hashes.json").read_text()) if (directory / "loaded-source-hashes.json").exists() else {}
write("receipt.json", {"command": command, "environment": environment, "policy": policy.to_dict(),
    "source_hashes_before": before, "source_hashes_after": after,
    "changed_files": [path for path in before if before[path] != after.get(path)],
    "changed_loaded_sources": [path for path in loaded if path in before and before[path] != after.get(path)],
    "returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)})
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
raise SystemExit(result.returncode)
