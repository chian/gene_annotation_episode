"""Run capture checks under the existing caller-owned local policy."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

output = Path(__file__).parent / sys.argv[1]
output.mkdir()
paths = ["gene_annotation_episode/native_hmmer_preparation_" + suffix + ".py"
         for suffix in ("acquisition", "contracts", "driver", "local")]
paths += ["gene_annotation_episode/hmmer_fm_data.py", "tests/test_native_hmmer_preparation_acquisition.py"]
paths += ["tests/test_native_hmmer_preparation_contracts.py", "tests/test_native_hmmer_preparation_driver.py"]
hashes = lambda: {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
before = hashes()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
argv = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
        str(ROOT / "tests/test_native_hmmer_preparation_acquisition.py"),
        "--basetemp=" + str(output / "temporary"), "--junitxml=" + str(output / "junit.xml"), *sys.argv[2:]]
(output / "intent.json").write_text(json.dumps({"argv": argv, "policy": policy.to_dict(),
    "source_sha256": before}, indent=2) + "\n")
result = run_local_job(argv, cwd=output, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
receipt = {"returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
    "source_hashes_before": before, "source_hashes_after": hashes()}
(output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"directory": str(output), "returncode": result.returncode,
    "unchanged_sources": receipt["source_hashes_before"] == receipt["source_hashes_after"],
    "stdout_tail": result.stdout_path.read_text()[-9000:], "stderr_tail": result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
