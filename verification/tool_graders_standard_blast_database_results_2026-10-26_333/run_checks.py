"""Retain each caller-limited local pytest receipt; never invokes native BLAST."""
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir(exist_ok=False)
(directory / "tmp").mkdir()
tests = sys.argv[2:] or [str(ROOT / "tests" / ("test_native_blast_standard_database_" + part + ".py"))
    for part in ("calculators", "result_views", "result_worker")]
result = run_local_job([str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(directory / "pytest-tmp"), *tests],
    cwd=directory, policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None),
    env={**os.environ, "PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests"), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory / "tmp")},
    stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt")
(directory / "receipt.json").write_text(json.dumps(dict(returncode=result.returncode, metadata=result.metadata), indent=2) + "\n")
print(json.dumps(dict(returncode=result.returncode, receipt=str(directory / "receipt.json"))))
