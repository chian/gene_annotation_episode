"""Retained local_jobs verification, with caller-owned resource limits."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
check = packet / sys.argv[1]
check.mkdir()
for name in ("temporary", "cache"):
    (check / name).mkdir()
if sys.argv[2] == "--script":
    selected = [str(packet / sys.argv[3]), *sys.argv[4:]]
    snapshot_tests = [packet / sys.argv[3]]
else:
    snapshot_tests = [ROOT / path for path in sys.argv[2:]]
    selected = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(check / "temporary/pytest"),
                *map(str, snapshot_tests)]
command = [str(ROOT / ".venv/bin/python"), "-B", *selected]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
env = {**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "tests"),
       "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(check / "temporary"),
       "TMP": str(check / "temporary"), "TEMP": str(check / "temporary"), "XDG_CACHE_HOME": str(check / "cache")}
paths = sorted(set([*snapshot_tests, Path(__file__), ROOT / "gene_annotation_episode/domain.py",
    ROOT / "gene_annotation_episode/local_jobs.py", ROOT / "gene_annotation_episode/blast_search.py",
    *ROOT.glob("gene_annotation_episode/blast_*.py"), *ROOT.glob("gene_annotation_episode/native_blast_*.py"),
    *ROOT.glob("gene_annotation_episode/bvbrc_homology*.py"),
    *ROOT.glob("tests/test_blast*.py"), *ROOT.glob("tests/test_native_blast*.py"),
    *ROOT.glob("tests/test_bvbrc_homology*.py"), *ROOT.glob("tests/conftest.py"),
    *packet.glob("candidate/*.py"), *packet.glob("*.py")]))
inventory = []
for path in paths:
    raw = path.read_bytes()
    relative = path.relative_to(ROOT)
    destination = check / "source_snapshot" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    inventory.append(dict(path=str(relative), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
(check / "source_snapshot.json").write_text(json.dumps(inventory, indent=2) + "\n")
(check / "selection.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
    evidence="supplied_or_retained_data_tests_no_native_database_execution"), indent=2) + "\n")
try:
    result = run_local_job(command, cwd=check, policy=policy, stdout_path=check / "stdout.txt",
        stderr_path=check / "stderr.txt", env=env)
except Exception as error:
    (check / "failure.json").write_text(json.dumps(dict(type=type(error).__name__, detail=str(error)), indent=2) + "\n")
    raise
(check / "receipt.json").write_text(json.dumps(dict(returncode=result.returncode,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), metadata=result.metadata), indent=2) + "\n")
(check / "source_after.json").write_text(json.dumps([dict(path=row["path"],
    sha256=hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()) for row in inventory], indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
