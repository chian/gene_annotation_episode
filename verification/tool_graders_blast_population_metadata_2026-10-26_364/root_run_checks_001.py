"""Bounded root verification of the missing-identity review finding."""
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
run = PACKET / sys.argv[1]
run.mkdir(exist_ok=False)
temporary = run / "temporary"
temporary.mkdir()
paths = [ROOT / "gene_annotation_episode/native_blast_database_population_metadata.py",
         ROOT / "tests/test_native_blast_population_unknown_identity_root.py",
         ROOT / "tests/test_native_blast_database_population_metadata.py"]

def pins():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
           "--basetemp", str(temporary / "pytest"), *sys.argv[2:]]
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
environment = {"PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests"), "PYTHONDONTWRITEBYTECODE": "1",
               "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary)}
(run / "command.json").write_text(json.dumps(dict(command=command, cwd=str(run), policy=policy.to_dict(), env=environment), indent=2) + "\n")
(run / "source_before.json").write_text(json.dumps(pins(), indent=2) + "\n")
result = run_local_job(command, cwd=run, policy=policy, stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt", env=environment)
(run / "receipt.json").write_text(json.dumps(dict(returncode=result.returncode, metadata=result.metadata), indent=2) + "\n")
(run / "source_after.json").write_text(json.dumps(pins(), indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
