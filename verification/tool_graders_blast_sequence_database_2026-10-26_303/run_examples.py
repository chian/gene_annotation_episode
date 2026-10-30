"""Export complete examples entirely inside the monitored local job directory."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).parent
directory = (packet / sys.argv[1]).resolve()
directory.mkdir(exist_ok=False)
sources = [ROOT / "gene_annotation_episode" / name for name in (
    "blast_sequence_database.py", "blast_database_grader.py", "blast_report_collection.py",
    "blast_grading_inputs.py", "blast_program_context.py", "blast_pairwise_grader.py")]
sources += [packet / "write_examples.py", ROOT / "tests/test_blast_sequence_database.py"]
def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
(directory / "source_hashes_before.json").write_text(json.dumps(hashes(), indent=2)+"\n")
command = [str(ROOT / ".venv/bin/python"), str(packet / "write_examples.py"), str(directory)]
(directory / "command.json").write_text(json.dumps(command, indent=2)+"\n")
result = run_local_job(command, cwd=directory,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3),
    stdout_path=directory / "stdout.log", stderr_path=directory / "stderr.log",
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
(directory / "receipt.json").write_text(json.dumps({"returncode": result.returncode,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}, indent=2)+"\n")
(directory / "source_hashes_after.json").write_text(json.dumps(hashes(), indent=2)+"\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
