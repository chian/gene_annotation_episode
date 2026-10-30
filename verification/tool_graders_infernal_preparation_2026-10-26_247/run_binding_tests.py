"""Bounded practical integration verification with its actual shared sources."""
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
files = list((root / "gene_annotation_episode").glob("*infernal_preparation*.py"))
shared = ["practical_execution_records", "practical_execution_operations", "practical_execution_state",
    "practical_execution_credit", "practical_resource_episodes", "practical_receipt_information",
    "native_lifecycle", "native_infernal_contracts", "native_infernal_driver", "local_jobs",
    "execution_episodes", "execution_contracts", "execution_progress", "episode_receipts",
    "episode_services", "episode_return_records", "episode_bindings", "form_reference_validation",
    "runtime", "storage", "scientific_process_library"]
files += [root / "gene_annotation_episode" / (name + ".py") for name in shared]
files += [Path(__file__).resolve(), root / "tests/test_native_infernal_preparation_driver.py",
    root / "tests/test_native_infernal_preparation_results_integration.py", root / "tests/test_runtime.py"]
files += [root / arg.split("::")[0] for arg in sys.argv[2:] if arg.startswith("tests/")]
def hashes():
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files if path.is_file()}
before = hashes()
command = [str(root / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(temporary / "pytest"), "--junitxml=" + str(destination / "tests.xml"),
    *(str(root / arg) if arg.startswith("tests/") else arg for arg in sys.argv[2:])]
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
