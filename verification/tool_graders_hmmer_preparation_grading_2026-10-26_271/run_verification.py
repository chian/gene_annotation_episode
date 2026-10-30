"""Run D1 tests through the established local resource envelope; no native runs."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

output = Path(__file__).parent / sys.argv[1]
output.mkdir()
paths = ["gene_annotation_episode/native_hmmer_preparation_worker.py", "tests/test_native_hmmer_preparation_worker.py"]
paths += [str(path.relative_to(ROOT)) for path in (ROOT / "gene_annotation_episode").glob("hmmer_*_*.py")]
hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
           str(ROOT / paths[1]), "--basetemp=" + str(output / "temporary"),
           "--junitxml=" + str(output / "junit.xml"), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(output / "intent.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(),
                                              "source_hashes": hashes}, indent=2) + "\n")
result = run_local_job(command, cwd=output, policy=policy,
                      env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
after = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
(output / "receipt.json").write_text(json.dumps({"returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
    "source_hashes_before": hashes, "source_hashes_after": after, "sources_unchanged": after == hashes}, indent=2) + "\n")
print(json.dumps({"directory": str(output), "returncode": result.returncode,
    "stdout_tail": result.stdout_path.read_text()[-14000:], "stderr_tail": result.stderr_path.read_text()[-1500:]}))
raise SystemExit(result.returncode)
