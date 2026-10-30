"""Caller-owned recorded local verification; no scientific search runs."""
import json
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).parent / sys.argv[1]
directory.mkdir(exist_ok=False)
directory = directory.resolve()
tests = sys.argv[2:] or ["test_blast_sequence_database.py", "test_blast_database_context.py",
    "test_blast_database_grader.py", "test_blast_explicit_associations.py",
    "test_blast_graders_integration.py", "test_bvbrc_homology_grader.py",
    "test_bvbrc_homology_workflow.py", "test_bvbrc_homology_composed_workflow.py",
    "test_blast_native_coordinate_conventions.py", "test_blast_report_collection.py"]
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", *[str(ROOT / "tests" / path) for path in tests],
    "--basetemp", str(directory / "temporary"), "--junitxml", str(directory / "junit.xml"),
    "-o", "cache_dir=" + str(directory / "pytest-cache")]
(directory / "command.json").write_text(json.dumps(command, indent=2) + "\n")
sources = list((ROOT / "gene_annotation_episode").glob("blast_*.py")) + list((ROOT / "gene_annotation_episode").glob("bvbrc_homology_*.py"))
sources += [ROOT / "tests" / path for path in tests]
def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
(directory / "source_hashes_before.json").write_text(json.dumps(hashes(), indent=2)+"\n")
result = run_local_job(command, cwd=directory,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3),
    stdout_path=directory / "stdout.log", stderr_path=directory / "stderr.log",
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
(directory / "receipt.json").write_text(json.dumps({"returncode": result.returncode,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}, indent=2) + "\n")
(directory / "source_hashes_after.json").write_text(json.dumps(hashes(), indent=2)+"\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
