"""Run the inspected instruction and tool-descriptor tests within local limits."""
import json
from pathlib import Path

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
directory = HERE / "check001"
directory.mkdir()
temporary = directory / "temporary"
temporary.mkdir()
command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q",
    str(ROOT / "tests/test_tool_knowledge.py"), str(ROOT / "tests/test_native_blast_database_tool_info.py"),
    "--basetemp", str(temporary / "pytest"), "-o", "cache_dir=" + str(temporary / "pytest-cache"),
    "--junitxml", str(directory / "junit.xml")]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
    stderr_path=directory / "stderr.txt", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")})
receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
    metadata=result.metadata, evidence_kind="Existing synthetic instruction-runtime and configured-descriptor tests; no scientific execution")
with (directory / "receipt.json").open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
print((directory / "stdout.txt").read_text())
print((directory / "stderr.txt").read_text())
raise SystemExit(result.returncode)
