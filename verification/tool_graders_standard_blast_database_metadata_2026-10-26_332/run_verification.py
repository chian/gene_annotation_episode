"""Run explicitly selected pure synthetic cases under the existing local policy."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
check = packet / sys.argv[1]
check.mkdir()
for name in ("temporary", "cache"):
    (check / name).mkdir()
tests = sys.argv[2:] or ["tests/test_native_blast_standard_database_metadata.py"]
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--basetemp", str(check / "temporary/pytest"), *[str(ROOT / p) for p in tests]]
env = {**os.environ, "PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests"), "PYTHONDONTWRITEBYTECODE": "1",
       "TMPDIR": str(check / "temporary"), "TMP": str(check / "temporary"), "TEMP": str(check / "temporary"),
       "XDG_CACHE_HOME": str(check / "cache")}
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
sources = ["gene_annotation_episode/native_blast_standard_database_metadata.py",
           "gene_annotation_episode/native_blast_standard_database_contracts.py",
           "gene_annotation_episode/native_blast_database_metadata.py", "gene_annotation_episode/blast_report_collection.py",
           "gene_annotation_episode/blast_sequence_database.py", "gene_annotation_episode/blast_database_grader.py",
           "gene_annotation_episode/blast_pssm_inputs.py", "gene_annotation_episode/blast_pssm_master_inputs.py",
           "gene_annotation_episode/blast_program_context.py", "gene_annotation_episode/domain.py",
           "tests/test_native_blast_standard_database_contracts.py", *[p.split("::")[0] for p in tests]]
snapshots = []
for relative in dict.fromkeys(sources):
    raw = (ROOT / relative).read_bytes()
    destination = check / "source_snapshot" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    snapshots.append(dict(path=relative, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
(check / "source_snapshot.json").write_text(json.dumps(snapshots, indent=2) + "\n")
(check / "selection.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
    evidence="synthetic_database_reports_and_one_retained_paired_report_format_only_no_database_execution"), indent=2) + "\n")
try:
    result = run_local_job(command, cwd=check, policy=policy, stdout_path=check / "stdout.txt",
                           stderr_path=check / "stderr.txt", env=env)
except Exception as error:
    (check / "failure.json").write_text(json.dumps(dict(type=type(error).__name__, detail=str(error)), indent=2) + "\n")
    raise
(check / "receipt.json").write_text(json.dumps(dict(returncode=result.returncode, stdout_path=str(result.stdout_path),
    stderr_path=str(result.stderr_path), metadata=result.metadata), indent=2) + "\n")
print(json.dumps(dict(directory=str(check), returncode=result.returncode)))
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
