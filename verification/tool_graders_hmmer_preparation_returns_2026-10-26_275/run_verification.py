"""Run retained-result path verification under the existing local policy."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).parent / sys.argv[1]
directory.mkdir()
paths = sorted([*ROOT.glob("gene_annotation_episode/*hmmer*preparation*.py"),
                *ROOT.glob("gene_annotation_episode/hmmer_*data.py"),
                *ROOT.glob("gene_annotation_episode/hmmer_*calculations.py"),
                *ROOT.glob("tests/test_native_hmmer_preparation_return*.py"),
                *ROOT.glob("tests/test_native_hmmer_preparation_failure*.py")])
hashes = lambda: {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before = hashes()
tests = sys.argv[2:] or [str(ROOT / "tests/test_native_hmmer_preparation_returns.py"),
    str(ROOT / "tests/test_native_hmmer_preparation_results.py"),
    str(ROOT / "tests/test_native_hmmer_preparation_failure_views.py")]
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
    "unchanged_sources": receipt["source_hashes_before"] == receipt["source_hashes_after"],
    "stdout_tail": result.stdout_path.read_text()[-18000:], "stderr_tail": result.stderr_path.read_text()[-3000:]}))
raise SystemExit(result.returncode)
