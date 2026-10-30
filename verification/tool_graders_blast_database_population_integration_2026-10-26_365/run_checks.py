"""Run this workload's tests through the established bounded local_jobs path."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
out = packet / sys.argv[1]
out.mkdir(exist_ok=False)
temporary, cache = out / "tmp", out / "cache"
temporary.mkdir(); cache.mkdir()
paths = list((ROOT / "gene_annotation_episode").glob("*blast*.py")) + [ROOT / "tests/test_native_blast_database_population_integration.py", ROOT / "tests/test_blast_population_association_recalculation.py", ROOT / "tests/blast_population_integration_fixtures.py"]
def pins(label):
    result = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (out / (label + "-source-pins.json")).write_text(json.dumps(result, indent=2) + "\n")
    return result
before = pins("before")
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(out / "temporary"), *sys.argv[2:]]
env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / "tests"), PYTHONDONTWRITEBYTECODE="1",
    TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary), XDG_CACHE_HOME=str(cache))
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(out / "request.json").write_text(json.dumps(dict(command=command, cwd=str(out), policy=dict(memory_bytes=policy.memory_bytes, scratch_bytes=policy.scratch_bytes, wall_seconds=policy.wall_seconds)), indent=2) + "\n")
result = run_local_job(command, cwd=out, policy=policy, stdout_path=out / "stdout.txt", stderr_path=out / "stderr.txt", env=env)
receipt = dict(returncode=result.returncode, metadata=result.metadata, command=command, cwd=str(out), policy=policy.to_dict())
(out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
after = pins("after")
print(json.dumps(receipt, indent=2))
print((out / "stdout.txt").read_text()[-24000:])
print((out / "stderr.txt").read_text()[-6000:])
if before != after: print("DEPENDENCY_SOURCE_CHANGED_DURING_RUN")
sys.exit(receipt["returncode"])
