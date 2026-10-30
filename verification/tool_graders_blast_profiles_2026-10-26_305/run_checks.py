"""Run pure verification through the existing caller-owned local boundary."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = (Path(__file__).parent / sys.argv[1]).resolve()
directory.mkdir(exist_ok=False)
tests = ["test_blast_profile_inputs.py", "test_blast_profile_calculators.py",
         "test_blast_program_context.py", "test_blast_report_collection.py",
         "test_blast_pairwise_grader.py", "test_blast_native_coordinate_conventions.py"]
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
           *(str(ROOT / "tests" / name) for name in tests), "--basetemp", str(directory / "temporary"),
           "--junitxml", str(directory / "junit.xml"), "-o", "cache_dir=" + str(directory / "pytest-cache")]
(directory / "command.json").write_text(json.dumps(command, indent=2) + "\n")
paths = [ROOT / "gene_annotation_episode" / name for name in
         ("blast_profile_inputs.py", "blast_profile_calculators.py", "blast_program_context.py",
          "blast_report_collection.py", "blast_pairwise_grader.py", "blast_grading_inputs.py")]
paths += [ROOT / "tests" / name for name in tests]
(directory / "source_hashes.json").write_text(json.dumps({str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                                       for path in paths}, indent=2) + "\n")
result = run_local_job(command, cwd=directory,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3),
    stdout_path=directory / "stdout.log", stderr_path=directory / "stderr.log", env={"PYTHONPATH": str(ROOT)})
(directory / "receipt.json").write_text(json.dumps({"returncode": result.returncode,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
