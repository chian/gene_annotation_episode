"""Retained development checks through the existing protected local-job lifecycle."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


base = Path(__file__).resolve().parent
run = base / sys.argv[1]
run.mkdir()
temporary = run / "temporary"
temporary.mkdir()
mode = sys.argv[2]
if mode in {"baseline", "compare"}:
    command = [str(ROOT / ".venv/bin/python"), "-B", str(base / "retain_calculator_comparison.py"), mode]
elif mode == "examples":
    command = [str(ROOT / ".venv/bin/python"), "-B", str(base / "retain_examples.py")]
else:
    tests = (sys.argv[3:] if len(sys.argv) > 3 else [
        "tests/test_blast_pssm_master_inputs.py", "tests/test_blast_pssm_inputs.py",
        "tests/test_blast_pssm_calculators.py", "tests/test_blast_pssm_alphabet.py",
        "tests/test_blast_iteration_inputs.py", "tests/test_blast_iteration_calculators.py"])
    command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q",
               *(str(ROOT / test) for test in tests), "--basetemp", str(temporary / "pytest"),
               "-o", "cache_dir=" + str(temporary / "pytest-cache")]
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
paths = [ROOT / name for name in (
    "gene_annotation_episode/blast_pssm_master_inputs.py", "gene_annotation_episode/blast_pssm_calculators.py",
    "gene_annotation_episode/blast_pssm_inputs.py", "gene_annotation_episode/blast_iteration_inputs.py",
    "gene_annotation_episode/blast_iteration_calculators.py", "tests/test_blast_pssm_master_inputs.py")]
paths.extend(Path(arg) for arg in command if arg.endswith(".py") and Path(arg).is_file())
def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in dict.fromkeys(paths) if path.is_file()}
before = hashes()
result = run_local_job(command, cwd=run, policy=policy,
    env={"PYTHONPATH": str(ROOT), "TMPDIR": str(temporary), "PYTHONDONTWRITEBYTECODE": "1"},
    stdout_path=run / "stdout.txt", stderr_path=run / "stderr.txt")
receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path), metadata=result.metadata,
    source_hashes_before=before, source_hashes_after=hashes())
(run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
print(json.dumps(dict(returncode=result.returncode, receipt=str(run / "receipt.json"))))
raise SystemExit(result.returncode)
