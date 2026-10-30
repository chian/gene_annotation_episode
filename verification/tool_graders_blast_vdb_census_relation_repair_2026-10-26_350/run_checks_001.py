"""Run350 checks with caller-owned20GiB RAM/4GiB scratch and no wall cap."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
run_name, mode = sys.argv[1:]
assert mode in {"focused", "suite", "examples"}
run_dir = PACKET / run_name
run_dir.mkdir(exist_ok=False)
names = ["gene_annotation_episode/blast_vdb_function_inputs.py",
         "gene_annotation_episode/blast_vdb_function_calculators.py",
         "tests/test_blast_vdb_function_census_relations.py"]
if mode == "suite":
    names += ["tests/test_blast_vdb_function_inputs.py", "tests/test_blast_vdb_function_saved_relations.py",
              "tests/test_blast_vdb_function_calculators.py"]
pins = {}
for name in names:
    source = ROOT / name
    destination = run_dir / "source" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    raw = source.read_bytes()
    pins[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
(run_dir / "source_pins.json").write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
command = [str(ROOT / ".venv/bin/python"), "-B"]
if mode == "examples":
    command += [str(PACKET / "record_examples_001.py"), str(run_dir / "artifacts")]
else:
    command += ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=short",
                "--basetemp=" + str(run_dir / "temporary"), "--junitxml=" + str(run_dir / "junit.xml")]
    if mode == "suite":
        command += [str(ROOT / name) for name in names[3:]]
    command += [str(ROOT / "tests/test_blast_vdb_function_census_relations.py")]
result = run_local_job(command, cwd=run_dir,
    policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None),
    stdout_path=run_dir / "stdout.txt", stderr_path=run_dir / "stderr.txt",
    env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests")})
(run_dir / "receipt.json").write_text(json.dumps(result.metadata, indent=2, sort_keys=True) + "\n")
unchanged = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == pin["sha256"] for name, pin in pins.items())
(run_dir / "source_stability.json").write_text(json.dumps({"all_sources_unchanged": unchanged}, indent=2) + "\n")
assert unchanged
print(json.dumps({"returncode": result.returncode, "receipt": str(run_dir / "receipt.json"),
                  "stdout": str(result.stdout_path), "stderr": str(result.stderr_path)}))
raise SystemExit(result.returncode)
