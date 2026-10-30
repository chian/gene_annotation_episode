"""Selected bounded Python reproduction; no native database execution."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
check = packet / "check001"
check.mkdir()
for name in ("temporary", "cache"):
    (check / name).mkdir()
command = [str(ROOT / ".venv/bin/python"), "-B", str(packet / "reproduce.py")]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
    "TMPDIR": str(check / "temporary"), "TMP": str(check / "temporary"), "TEMP": str(check / "temporary"),
    "XDG_CACHE_HOME": str(check / "cache")}
names = ["blast_sequence_database", "blast_database_grader", "native_blast_database_metadata",
    "native_blast_standard_database_metadata", "native_blast_database_result_worker",
    "native_blast_standard_database_calculators", "native_blast_standard_database_result_worker",
    "native_blast_standard_database_contracts", "native_blast_standard_database_result_views",
    "native_blast_database_contracts", "blast_iteration_inputs", "blast_iteration_calculators",
    "blast_vdb_inputs", "blast_report_collection", "domain"]
sources = []
for name in names:
    path = ROOT / "gene_annotation_episode" / (name + ".py")
    raw = path.read_bytes()
    destination = check / "source_snapshot" / path.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    sources.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
(check / "source_snapshot.json").write_text(json.dumps(sources, indent=2) + "\n")
(check / "selection.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
    evidence="retained_synthetic_bytes_and_pure_public_consumer_reproduction_no_database_execution"), indent=2) + "\n")
try:
    result = run_local_job(command, cwd=check, policy=policy, stdout_path=check / "stdout.txt",
        stderr_path=check / "stderr.txt", env=env)
except Exception as error:
    (check / "failure.json").write_text(json.dumps(dict(type=type(error).__name__, detail=str(error)), indent=2) + "\n")
    raise
(check / "receipt.json").write_text(json.dumps(dict(returncode=result.returncode,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), metadata=result.metadata), indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
