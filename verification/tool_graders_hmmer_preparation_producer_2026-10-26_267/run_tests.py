"""Reproducible bounded verification; each native test also uses local_jobs."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

output = Path(__file__).parent / sys.argv[1]
output.mkdir()
tests = ["tests/test_native_hmmer_preparation_" + kind + ".py" for kind in ("contracts", "job_schema", "driver", "local")]
paths = tests + ["gene_annotation_episode/native_hmmer_preparation_" + kind + ".py" for kind in ("contracts", "job_schema", "driver", "local")]
paths += ["gene_annotation_episode/hmmer_fm_data.py"]
hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", *[str(ROOT / path) for path in tests],
           "--basetemp=" + str(output / "temporary"), "--junitxml=" + str(output / "junit.xml"), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(output / "intent.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(), "source_hashes": hashes}, indent=2)+"\n")
result = run_local_job(command, cwd=output, policy=policy,
    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
(output / "receipt.json").write_text(json.dumps({"returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}, indent=2)+"\n")
print(json.dumps({"directory": str(output), "returncode": result.returncode,
    "stdout_tail": result.stdout_path.read_text()[-6000:], "stderr_tail": result.stderr_path.read_text()[-1500:]}))
raise SystemExit(result.returncode)
