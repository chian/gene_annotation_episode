"""Verification only, through the existing bounded local_jobs lifecycle."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

base = Path(__file__).resolve().parent
run = base / sys.argv[1]
run.mkdir()
temporary = run / "temporary"
temporary.mkdir()
names = ["test_blast_iteration_inputs.py", "test_blast_iteration_calculators.py"]
if "--regression" in sys.argv:
    names += ["test_blast_sequence_database.py", "test_blast_profile_inputs.py", "test_blast_profile_calculators.py",
              "test_blast_pssm_inputs.py", "test_blast_pssm_calculators.py", "test_blast_archive_member_digest.py",
              "test_blast_table_layout.py"]
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", *[str(ROOT / "tests" / n) for n in names],
           "--basetemp", str(temporary / "pytest"), "-o", "cache_dir=" + str(temporary / "pytest-cache"),
           "--junitxml", str(run / "junit.xml")]
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
result = run_local_job(command, cwd=run, policy=policy,
    env={"PYTHONPATH": str(ROOT), "TMPDIR": str(temporary), "PYTHONDONTWRITEBYTECODE": "1"},
    stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt")
(run / "receipt.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), metadata=result.metadata), indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
print(json.dumps({"returncode": result.returncode, "receipt": str(run / "receipt.json")}))
raise SystemExit(result.returncode)
