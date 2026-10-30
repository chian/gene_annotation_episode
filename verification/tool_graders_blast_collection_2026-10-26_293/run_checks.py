"""Recorded verification under the existing caller-owned local job boundary."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).parent / sys.argv[1]
directory.mkdir(exist_ok=False)
directory = directory.resolve()
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
    str(ROOT / "tests/test_blast_program_context.py"),
    str(ROOT / "tests/test_blast_report_collection.py"),
    str(ROOT / "tests/test_blast_grading_inputs.py"),
    str(ROOT / "tests/test_blast_pairwise_grader.py"),
    "--basetemp", str(directory / "temporary"),
    "--junitxml", str(directory / "junit.xml"), "-o", "cache_dir=" + str(directory / "pytest-cache")]
(directory / "command.json").write_text(json.dumps(command, indent=2) + "\n")
result = run_local_job(command, cwd=directory,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3),
    stdout_path=directory / "stdout.log", stderr_path=directory / "stderr.log", env={"PYTHONPATH": str(ROOT)})
(directory / "receipt.json").write_text(json.dumps({"returncode": result.returncode,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
    "metadata": result.metadata}, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
