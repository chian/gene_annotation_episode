"""Check the same four reference tests with the original communication source."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


packet = Path(__file__).resolve().parent
root = packet.parents[1]
baseline = packet / "communication_before_001.py"
if "--worker" in sys.argv:
    import gene_annotation_episode
    spec = importlib.util.spec_from_file_location("gene_annotation_episode.communication", baseline)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    setattr(gene_annotation_episode, "communication", module)
    spec.loader.exec_module(module)
    import pytest
    raise SystemExit(pytest.main([str(root / "tests/test_reference_resolution.py"), "-q",
        "-p", "no:cacheprovider", "--basetemp=" + sys.argv[-1]]))

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = packet / ("reference_baseline_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
directory.mkdir()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
command = [str(root / ".venv/bin/python"), "-B", str(Path(__file__).resolve()), "--worker", str(directory / "tmp")]
result = run_local_job(command, cwd=directory, policy=policy,
    stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
    env={"PYTHONPATH": str(root) + ":" + str(root / "tests"), "PYTHONDONTWRITEBYTECODE": "1"})
files = [baseline, root / "gene_annotation_episode/runtime.py", root / "tests/test_reference_resolution.py"]
receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode, metadata=result.metadata,
    source_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files})
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(directory)
print(result.stdout_path.read_text()[-12000:])
print(result.stderr_path.read_text()[-2000:])
raise SystemExit(result.returncode)
