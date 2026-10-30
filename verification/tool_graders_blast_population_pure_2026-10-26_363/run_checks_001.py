"""Owned verification runner: actual local_jobs custody and source pins."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
run = packet / sys.argv[1]
run.mkdir(exist_ok=False)
for name in ("temporary", "cache"):
    (run / name).mkdir()
selected = sys.argv[2:]
script_mode = selected[0] == "--script"
scripts = [packet / selected[1]] if script_mode else [ROOT / name for name in selected]
arguments = [str(scripts[0]), *selected[2:]] if script_mode else ["-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(run / "temporary/pytest"), *map(str, scripts)]
command = [str(ROOT / ".venv/bin/python"), "-B", *arguments]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
env = {**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "tests"),
    "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(run / "temporary"),
    "TMP": str(run / "temporary"), "TEMP": str(run / "temporary"), "XDG_CACHE_HOME": str(run / "cache")}
paths = sorted(set([*scripts, Path(__file__), *packet.glob("*.py"),
    *ROOT.glob("gene_annotation_episode/blast_*.py"), *ROOT.glob("gene_annotation_episode/native_blast_*.py"),
    ROOT / "gene_annotation_episode/local_jobs.py", ROOT / "tests/test_blast_sequence_database.py",
    ROOT / "tests/test_blast_explicit_associations.py", ROOT / "tests/test_blast_database_population_associations.py",
    ROOT / "tests/test_blast_sequence_population_association.py"]))
def pins():
    return [dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                 size_bytes=p.stat().st_size) for p in paths]
(run / "source_before.json").write_text(json.dumps(pins(), indent=2) + "\n")
(run / "request.json").write_text(json.dumps(dict(command=command, cwd=str(run), policy=policy.to_dict(),
    evidence="synthetic_or_retained_data_only_no_native_database_execution"), indent=2) + "\n")
try:
    result = run_local_job(command, cwd=run, policy=policy, stdout_path=run / "stdout.txt",
        stderr_path=run / "stderr.txt", env=env)
except Exception as error:
    (run / "failure.json").write_text(json.dumps(dict(type=type(error).__name__, detail=str(error)), indent=2) + "\n")
    raise
finally:
    (run / "source_after.json").write_text(json.dumps(pins(), indent=2) + "\n")
(run / "receipt.json").write_text(json.dumps(dict(returncode=result.returncode,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), metadata=result.metadata), indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
