"""Run the 314/002 shared-port checks through the existing local limit wrapper."""
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    label, *tests = sys.argv[1:]
    directory = HERE / label
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    tests = tests or [str(ROOT / "tests/test_blast_iteration_target_context.py")]
    command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", *tests,
        "--basetemp", str(temporary / "pytest"), "-o", "cache_dir=" + str(temporary / "pytest-cache"),
        "--junitxml", str(directory / "junit.xml")]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode,
        metadata=result.metadata, evidence_kind="synthetic taxonomy inputs and saved native-format fixtures; no database BLAST")
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
