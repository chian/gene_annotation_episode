"""Development verification through the existing protected local job lifecycle."""
import hashlib
import json
import os
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
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
           str(ROOT / "tests/test_blast_pssm_inputs.py"), str(ROOT / "tests/test_blast_pssm_calculators.py"),
           "--basetemp", str(temporary / "pytest"), "-o", "cache_dir=" + str(temporary / "pytest-cache")]
env = {"PYTHONPATH": str(ROOT), "TMPDIR": str(temporary), "PYTHONDONTWRITEBYTECODE": "1"}
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
result = run_local_job(command, cwd=run, policy=policy, env=env,
                       stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt")
receipt = {"command": command, "policy": policy.to_dict(), "returncode": result.returncode,
           "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}
(run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
print(json.dumps({"returncode": result.returncode, "receipt": str(run / "receipt.json")}))
raise SystemExit(result.returncode)
