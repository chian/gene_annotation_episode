"""Run only348's independently warranted census review, with caller limits."""
import json
from pathlib import Path
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
run_dir = PACKET / sys.argv[1]
run_dir.mkdir(exist_ok=False)
result = run_local_job(
    [str(ROOT / ".venv/bin/python"), "-B", str(PACKET / "reproduce_001.py"), str(run_dir / "artifacts")],
    cwd=run_dir,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None),
    stdout_path=run_dir / "stdout.txt", stderr_path=run_dir / "stderr.txt",
    env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT)},
)
(run_dir / "receipt.json").write_text(json.dumps(result.metadata, indent=2, sort_keys=True) + "\n")
print(json.dumps({"returncode": result.returncode, "receipt": str(run_dir / "receipt.json")}))
if result.returncode:
    print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
