"""Bound capture tests to existing local_jobs and preserve exact source evidence."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


root = Path(__file__).resolve().parents[2]
destination = Path(__file__).resolve().parent / sys.argv[1]
destination.mkdir()
temporary = destination / "temporary"
temporary.mkdir()
tests = sys.argv[2:] or ["tests/test_native_infernal_preparation_acquisition.py"]
files = [root / "gene_annotation_episode" / name for name in (
    "native_infernal_preparation_acquisition.py", "native_infernal_preparation_driver.py",
    "native_infernal_preparation_local.py", "native_infernal_preparation_contracts.py",
    "native_infernal_contracts.py", "native_infernal_acquisition.py", "materials.py", "state.py",
    "practical_execution_state.py", "execution_contracts.py", "local_jobs.py", "native_lifecycle.py")]
files += [root / name.split("::")[0] for name in tests if name.startswith("tests/")]
files += [Path(__file__).resolve()]
producer = root / "verification/tool_graders_infernal_preparation_producer_2026-10-26_251"
index = producer / "NATIVE_PRODUCER_INDEX_001.json"
files.append(index)
for case in json.loads(index.read_bytes())["reservations"]:
    for value in case.values():
        if isinstance(value, dict) and "path" in value:
            files.append(root / value["path"])
for path in (producer / "producer_001/temporary/pytest").glob("test_actual_selected_native_mo*/plan.json"):
    if not path.parent.is_symlink():
        files.append(path)
        files.append(Path(json.loads(path.read_bytes())["attempt_directory"]) / "bundle.json")


def hashes():
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


before = hashes()
command = [str(root / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(temporary / "pytest"), "--junitxml=" + str(destination / "tests.xml"),
    *(str(root / arg) if arg.startswith("tests/") else arg for arg in tests)]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {"PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(destination / "cache")}
result = run_local_job(command, cwd=destination, policy=policy, env=environment)
receipt = {"command": command, "policy": policy.to_dict(), "environment": environment,
    "source_hashes_before": before, "source_hashes_after": hashes(), "returncode": result.returncode,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}
(destination / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(destination / "receipt.json")}))
raise SystemExit(result.returncode)
