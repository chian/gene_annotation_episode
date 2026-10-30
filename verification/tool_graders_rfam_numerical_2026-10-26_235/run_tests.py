"""Rfam pure numerical verification within the required local resource limits."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
directory = HERE / sys.argv[1]
directory.mkdir()
temporary = directory / "temporary"
temporary.mkdir()
paths = [ROOT / "gene_annotation_episode" / ("rfam_batch_" + name + ".py")
         for name in ("contracts", "inputs", "grader", "views")]
paths.append(ROOT / "gene_annotation_episode/rfam_batch_alignment.py")
tests = [ROOT / "tests" / ("test_rfam_batch_" + name + ".py") for name in ("inputs", "grader", "views")]
tests.append(ROOT / "tests/test_rfam_batch_alignment.py")
paths.extend(tests + [Path(__file__), HERE / "verify_examples.py"])
paths.extend(sorted((ROOT / "verification/tool_graders_rfam_contract_2026-10-26_232/examples").glob("*.json")))
native = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live"
for kind in ("single", "multi"):
    paths.extend(native / kind / name for name in ("input.seq", "input-manifest.json", "original_handle.json",
        "003-fetch-json/response.body", "003-fetch-json/snapshot.json"))


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(temporary / "pytest"), "--junitxml=" + str(directory / "tests.xml"),
    *map(str, tests), *sys.argv[2:]]
if sys.argv[2:] == ["examples"]:
    command = [str(ROOT / ".venv/bin/python"), str(HERE / "verify_examples.py"), str(directory / "examples")]
environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")}
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
before = hashes()
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
receipt = {"scope": "supplied native JSON, saved sheet arithmetic and selected projection; no native program or API execution",
    "command": command, "environment": environment, "policy": policy.to_dict(),
    "source_hashes_before": before, "source_hashes_after": hashes(), "returncode": result.returncode,
    "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
raise SystemExit(result.returncode)
