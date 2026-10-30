"""Bounded regression of the shared execution and reference boundaries."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).parent / sys.argv[1]
directory.mkdir()
paths = sorted([*ROOT.glob("gene_annotation_episode/*.py"),
                ROOT / "tests/test_execution_episodes_family.py",
                ROOT / "tests/test_hmmer_preparation_receipt_visibility.py",
                ROOT / "tests/test_practical_runtime.py",
                ROOT / "tests/test_native_infernal_preparation_reference_visibility.py"])
hashes = lambda: {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before = hashes()
tests = sys.argv[2:] or [str(ROOT / "tests/test_execution_episodes_family.py"),
    str(ROOT / "tests/test_native_infernal_preparation_reference_visibility.py")]
argv = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--basetemp=" + str(directory / "temporary"), "--junitxml=" + str(directory / "junit.xml"), *tests]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(directory / "intent.json").write_text(json.dumps({"argv": argv, "policy": policy.to_dict(), "source_sha256": before}, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
receipt = {"returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
    "source_hashes_before": before, "source_hashes_after": hashes()}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(directory), "returncode": result.returncode,
    "changed_sources": [k for k in before if before[k] != receipt["source_hashes_after"].get(k)],
    "stdout_tail": result.stdout_path.read_text()[-16000:], "stderr_tail": result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
