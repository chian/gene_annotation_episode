"""Supplied-file Rfam table verification under the existing bounded runner."""
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
paths = [ROOT / "gene_annotation_episode/rfam_batch_table.py", ROOT / "tests/test_rfam_batch_table.py",
    ROOT / "gene_annotation_episode/infernal_search_inputs.py", ROOT / "gene_annotation_episode/infernal_search_grader.py",
    Path(__file__), HERE / "verify_examples.py"]
paths.extend(sorted(path for path in (ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/multi").rglob("*")
    if path.is_file() and (path.name in ("input.seq", "input-manifest.json", "original_handle.json", "snapshot.json", "response.body"))))


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(temporary / "pytest"), "--junitxml=" + str(directory / "tests.xml"),
    str(ROOT / "tests/test_rfam_batch_table.py"), *sys.argv[2:]]
if sys.argv[2:] == ["examples"]:
    command = [str(ROOT / ".venv/bin/python"), str(HERE / "verify_examples.py"), str(directory / "examples")]
environment = {"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")}
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
before = hashes()
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
receipt = {"scope": "supplied native batch table and membership; synthetic counterexamples; saved-sheet calculations; no new native execution or network",
    "command": command, "environment": environment, "policy": policy.to_dict(),
    "source_hashes_before": before, "source_hashes_after": hashes(), "returncode": result.returncode,
    "metadata": result.metadata, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
raise SystemExit(result.returncode)
