"""Caller-bounded local export of retained test evidence and source pins."""
from pathlib import Path
import json
import os
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

out = PACKET / "examples_001"
out.mkdir(exist_ok=False)
temporary, cache = out / "tmp", out / "cache"
temporary.mkdir(); cache.mkdir()
command = [str(ROOT / ".venv/bin/python"), "-B", str(PACKET / "record_examples_001.py"), str(out)]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(temporary), TMP=str(temporary),
    TEMP=str(temporary), XDG_CACHE_HOME=str(cache))
result = run_local_job(command, cwd=out, policy=policy, stdout_path=out / "stdout.txt", stderr_path=out / "stderr.txt", env=env)
receipt = dict(command=command, cwd=str(out), policy=policy.to_dict(), returncode=result.returncode, metadata=result.metadata)
(out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print((out / "stdout.txt").read_text())
print((out / "stderr.txt").read_text())
print(json.dumps(receipt))
sys.exit(result.returncode)
