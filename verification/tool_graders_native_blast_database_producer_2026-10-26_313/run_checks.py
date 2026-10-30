"""Explicit synthetic/pure checks under the existing local_jobs allocation."""
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]


def main():
    label, *selected = sys.argv[1:]
    directory = Path(__file__).resolve().parent / label
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    if not selected:
        selected = [str(ROOT / "tests" / name) for name in (
            "test_native_blast_database_contracts.py", "test_native_blast_database_driver.py", "test_native_blast_database_tool_info.py")]
    command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", *selected,
        "--basetemp", str(temporary / "pytest"), "-o", "cache_dir=" + str(temporary / "pytest-cache")]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    result = run_local_job(command, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
            "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = {"command": command, "policy": policy.to_dict(), "returncode": result.returncode,
        "metadata": result.metadata, "evidence_kind": "synthetic and pure contract checks; no native database BLAST"}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
