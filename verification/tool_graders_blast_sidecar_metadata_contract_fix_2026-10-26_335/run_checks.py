"""Retain one bounded local test run, including failed-before evidence."""
import hashlib
import json
import os
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
directory = HERE / sys.argv[1]
directory.mkdir(exist_ok=False)
(directory / "temporary").mkdir()
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--basetemp", str(directory / "temporary/pytest"),
           *[str(ROOT / name) for name in sys.argv[2:]]]
source_path = ROOT / "gene_annotation_episode/native_blast_database_metadata.py"
before = hashlib.sha256(source_path.read_bytes()).hexdigest()
result = run_local_job(command, cwd=directory,
    policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None),
    stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
    env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory)})
receipt = dict(command=command, returncode=result.returncode, metadata=result.metadata,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path),
    source_sha256_before=before, source_sha256_after=hashlib.sha256(source_path.read_bytes()).hexdigest())
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
print("\n".join(result.stdout_path.read_text().splitlines()[-6:]))
print(result.stderr_path.read_text())
