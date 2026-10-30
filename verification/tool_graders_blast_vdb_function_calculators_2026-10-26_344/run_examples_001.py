"""Save full checkable examples through the actual bounded local runner."""
from pathlib import Path
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
run_dir = PACKET / sys.argv[1]
run_dir.mkdir(exist_ok=False)
result = run_local_job([str(ROOT / ".venv/bin/python"), "-B", str(PACKET / "generate_examples_001.py"), str(run_dir / "examples")],
    cwd=run_dir, policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None),
    stdout_path=run_dir / "stdout.txt", stderr_path=run_dir / "stderr.txt",
    env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests")})
(run_dir / "receipt.json").write_text(json.dumps(result.metadata, sort_keys=True, indent=2) + "\n")
if result.returncode:
    print(result.stdout_path.read_text()); print(result.stderr_path.read_text())
else:
    summary = json.loads((run_dir / "examples/manifest.json").read_text())
    print(json.dumps({"cases": [{"name": c["name"], "status": c["status"]} for c in summary["cases"]],
        "complete_manifest": str(run_dir / "examples/manifest.json")}, indent=2))
print(json.dumps({"returncode": result.returncode, "receipt": str(run_dir / "receipt.json")}))
raise SystemExit(result.returncode)
