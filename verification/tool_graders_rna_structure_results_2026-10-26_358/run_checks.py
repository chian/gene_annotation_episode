"""All 358 tests/probes execute inside the required shared local lifecycle."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

PACKET = Path(__file__).resolve().parent
RUN = PACKET / ("check_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
RUN.mkdir()
for name in ("tmp", "cache", "source_snapshots", "examples"):
    (RUN / name).mkdir()
PRODUCTION = ["native_rna_structure_acquisition", "native_rna_structure_result_worker", "native_rna_structure_result_publication",
    "rna_structure_result_views", "native_rna_structure_results", "native_rna_structure_returns"]
TESTS = ["test_native_rna_structure_acquisition", "test_native_rna_structure_result_publication", "test_native_rna_structure_result_views",
    "test_native_rna_structure_recalculation", "test_native_rna_structure_returns"]
paths = [REPO / "gene_annotation_episode" / (name + ".py") for name in PRODUCTION] + [REPO / "tests" / (name + ".py") for name in TESTS]
paths += [PACKET / "fixture_helpers.py", Path(__file__)]
hashes = {}
for source in paths:
    raw = source.read_bytes()
    hashes[str(source.relative_to(REPO))] = hashlib.sha256(raw).hexdigest()
    shutil.copyfile(source, RUN / "source_snapshots" / source.name)
command = [str(REPO / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "--tb=short",
    "--basetemp=" + str(RUN / "tmp/pytest"), *[str(REPO / "tests" / (name + ".py")) for name in TESTS], *sys.argv[1:]]
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
(RUN / "command.json").write_text(json.dumps({"command": command, "launcher_cwd": str(REPO), "cwd": str(RUN), "policy": policy.to_dict(), "source_sha256": hashes}, indent=2) + "\n")
print(RUN, flush=True)
result = run_local_job(command, cwd=RUN, policy=policy, stdout_path=RUN / "stdout.txt", stderr_path=RUN / "stderr.txt",
    env={"PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(RUN / "tmp"),
        "TMP": str(RUN / "tmp"), "TEMP": str(RUN / "tmp"), "XDG_CACHE_HOME": str(RUN / "cache"),
        "RNA_RESULTS_EXAMPLE_OUTPUT": str(RUN / "examples")})
receipt = {"returncode": result.returncode, "metadata": result.metadata, "stdout_path": str(result.stdout_path),
    "stderr_path": str(result.stderr_path), "source_unchanged": all(hashlib.sha256(path.read_bytes()).hexdigest() == hashes[str(path.relative_to(REPO))] for path in paths)}
(RUN / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print((RUN / "stdout.txt").read_text(), flush=True)
print(json.dumps(receipt, indent=2, sort_keys=True), flush=True)
raise SystemExit(result.returncode)
