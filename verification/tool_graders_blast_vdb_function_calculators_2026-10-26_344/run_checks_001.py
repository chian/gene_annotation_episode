"""Run isolated pure calculator verification under the existing local limits."""
from pathlib import Path
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
run_dir = PACKET / sys.argv[1]
run_dir.mkdir(exist_ok=False)
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest",
    str(ROOT / "tests/test_blast_vdb_function_calculators.py"), "-q", "-p", "no:cacheprovider",
    "--basetemp", str(run_dir / "pytest_tmp")]
command.extend(sys.argv[2:])
result = run_local_job(command, cwd=run_dir,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None),
    stdout_path=run_dir / "stdout.txt", stderr_path=run_dir / "stderr.txt",
    env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests")})
(run_dir / "receipt.json").write_text(json.dumps(result.metadata, indent=2, sort_keys=True) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
print(json.dumps({"returncode": result.returncode, "receipt": str(run_dir / "receipt.json")}))
raise SystemExit(result.returncode)
