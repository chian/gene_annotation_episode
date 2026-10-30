"""Retain a bounded local-job invocation, source pin, complete outputs and receipt."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
sources = [REPO / "gene_annotation_episode" / ("rna_structure_" + name + ".py")
    for name in ("contracts", "topology", "native", "calculations")]
tests = [REPO / "tests" / ("test_rna_structure_" + name + ".py")
    for name in ("contracts", "topology", "native", "calculations")]
sources += tests + [PACKET / name for name in ("run_verification.py", "fixture_helpers.py", "topology_oracles.json")]
sources += [REPO / "gene_annotation_episode" / name for name in ("local_jobs.py", "native_lifecycle.py", "_local_job_worker.py")]
pins = []
for source in sources:
    content = source.read_bytes()
    relative = source.relative_to(REPO)
    snapshot = directory / "source_snapshot" / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(content)
    pins.append({"path": str(relative), "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
(directory / "source_pins.json").write_text(json.dumps(pins, indent=2) + "\n")
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
argv = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(directory / "temporary"), *map(str, tests)]
environment = {"PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory / "temporary"),
    "XDG_CACHE_HOME": str(directory / "cache"), "RNA_CORE_EXAMPLE_OUTPUT": str(directory / "actual_examples")}
(directory / "temporary").mkdir()
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment}, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
    stderr_path=directory / "stderr.txt", env=environment)
unchanged = all(hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest() == row["sha256"] for row in pins)
receipt = {"returncode": result.returncode, "source_pins_unchanged": unchanged,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"directory": str(directory), "returncode": result.returncode, "source_pins_unchanged": unchanged}))
raise SystemExit(result.returncode if unchanged else 99)
