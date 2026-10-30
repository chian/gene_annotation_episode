"""Protected example-retention invocation; no native scientific work."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


base = Path(__file__).resolve().parent
run = base / sys.argv[1]
run.mkdir()
(run / "temporary").mkdir()
command = [str(ROOT / ".venv/bin/python"), str(base / "retain_examples.py"), str(run / "examples")]
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
result = run_local_job(command, cwd=run, policy=policy,
    env={"PYTHONPATH": str(ROOT), "TMPDIR": str(run / "temporary"), "PYTHONDONTWRITEBYTECODE": "1"},
    stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt")
(run / "receipt.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(),
    "returncode": result.returncode, "metadata": result.metadata}, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
