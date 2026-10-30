"""Run producer251 verification through existing local_jobs and retain custody."""
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
tests = sys.argv[2:] or ["tests/test_native_infernal_preparation_driver.py", "tests/test_native_infernal_preparation_local.py"]
files = [root / "gene_annotation_episode" / name for name in (
    "native_infernal_preparation_driver.py", "native_infernal_preparation_local.py",
    "native_infernal_preparation_contracts.py", "native_infernal_driver.py", "native_infernal_local.py",
    "native_infernal_contracts.py", "native_lifecycle.py", "local_jobs.py", "_local_job_worker.py")]
files += [root / name.split("::")[0] for name in tests if name.startswith("tests/")]
files += [Path(__file__).resolve(),
    root / "verification/tool_graders_infernal_preparation_2026-10-26_247/NATIVE_COMPILED_INDEX_001.json"]
files += list((root / "resources/software/infernal-1.1.5-install/bin").glob("cm*"))

def hashes():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}

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
