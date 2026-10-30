"""Retain every bounded F-wire test run, including unsuccessful runs."""
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
source_paths = sorted(set((ROOT / "gene_annotation_episode").glob("*.py")) | {
    ROOT / "tests/test_native_blast_vdb_function_metadata.py",
    ROOT / "tests/test_native_blast_database_metadata.py", ROOT / "tests/test_blast_vdb_function_inputs.py",
    ROOT / "tests/test_blast_vdb_inputs.py", ROOT / "tests/test_blast_vdb_calculators.py", Path(__file__)})
def pins():
    return [dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size_bytes=p.stat().st_size)
            for p in source_paths]
before = pins()
(directory / "source_pins_before.json").write_text(json.dumps(before, indent=2, sort_keys=True) + "\n")
saved = directory / "sources"
saved.mkdir()
for relative in ("gene_annotation_episode/native_blast_vdb_function_metadata.py",
                 "gene_annotation_episode/native_blast_database_metadata.py",
                 "gene_annotation_episode/blast_vdb_function_inputs.py",
                 "tests/test_native_blast_vdb_function_metadata.py"):
    source = ROOT / relative
    (saved / source.name).write_bytes(source.read_bytes())
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest",
    str(ROOT / "tests/test_native_blast_vdb_function_metadata.py"),
    "-q", "-p", "no:cacheprovider", "--basetemp", str(directory / "temporary")]
command.extend(sys.argv[2:])
if "--frozen-helper" in command:
    command.remove("--frozen-helper")
    command[2:4] = [str(PACKET / "frozen_helper_pytest_001.py")]
result = run_local_job(command, cwd=directory,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None),
    stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
    env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests")})
(directory / "receipt.json").write_text(json.dumps(result.metadata, indent=2, sort_keys=True) + "\n")
after = pins()
(directory / "source_pins_after.json").write_text(json.dumps(after, indent=2, sort_keys=True) + "\n")
(directory / "source_changes.json").write_text(json.dumps([dict(before=b, after=a) for b, a in zip(before, after) if b != a], indent=2, sort_keys=True) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
raise SystemExit(result.returncode)
