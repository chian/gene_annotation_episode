"""Run explicitly selected synthetic verification under the required local policy."""
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir(exist_ok=False)
source_names = [
    "native_blast_database_metadata.py", "native_blast_database_result_worker.py",
    "native_blast_database_result_views.py", "native_blast_database_result_publication.py",
    "native_blast_database_results.py", "native_blast_database_returns.py",
    "native_blast_database_tool_info.py", "execution_progress.py", "execution_episodes.py", "episode_receipts.py",
    "blast_vdb_function_inputs.py", "blast_vdb_function_calculators.py",
    "native_blast_vdb_function_metadata.py"]
paths = [ROOT / "gene_annotation_episode" / n for n in source_names]
paths += [p for p in (ROOT / "tests").glob("test_native_blast_vdb_function_*.py")]
paths += [ROOT / "tests/test_native_blast_database_metadata.py", ROOT / "tests/test_native_blast_database_result_views.py"]
# Retain all selected regression sources and their local BLAST fixture helpers.
paths += sorted((ROOT / "tests").glob("test_native_blast_database_*.py"))
paths += sorted((ROOT / "tests").glob("test_blast_vdb*.py"))
paths += [ROOT / "tests/test_blast_fasta_record_identity_integration.py"]
paths += sorted((ROOT / "gene_annotation_episode").rglob("*.py"))
paths += [Path(__file__).resolve()]
paths = list(dict.fromkeys(paths))
before = []
for path in paths:
    raw = path.read_bytes()
    target = directory / "source" / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    before.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
(directory / "source-before.json").write_text(json.dumps(before, indent=2) + "\n")
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp", str(directory / "pytest"), *sys.argv[2:]]
env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / "tests"), PYTHONDONTWRITEBYTECODE="1")
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
(directory / "request.json").write_text(json.dumps(dict(command=command, cwd=str(directory), policy=policy.to_dict(),
    scientific_inputs="explicitly synthetic fixtures; no live BLAST, database, API or HPC job"), indent=2) + "\n")
try:
    result = run_local_job(command, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt", env=env)
    receipt = dict(returncode=result.returncode, metadata=result.metadata)
except Exception as error:
    receipt = dict(exception=type(error).__name__, message=str(error), operational=getattr(error, "operational", None))
    raise
finally:
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    after = [dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
    (directory / "source-after.json").write_text(json.dumps(after, indent=2) + "\n")
print(json.dumps(dict(directory=str(directory), returncode=result.returncode,
    sources_unchanged=all(a["sha256"] == b["sha256"] for a, b in zip(before, after)))))
print((directory / "stdout.txt").read_text()[-15000:])
raise SystemExit(result.returncode)
