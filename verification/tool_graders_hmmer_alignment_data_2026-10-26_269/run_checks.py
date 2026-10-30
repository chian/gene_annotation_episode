"""Explicit bounded verification wrapper; not a production workflow."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    name, *arguments = sys.argv[1:]
    directory = HERE / name
    directory.mkdir(exist_ok=False)
    (directory / "temporary").mkdir()
    command = ([str(ROOT / ".venv/bin/python"), *arguments[1:]] if arguments and arguments[0] == "--script" else
               [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "--basetemp", str(directory / "temporary"), *arguments])
    policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
    intent = {"argv": command, "policy": policy.to_dict(), "cwd": str(directory), "source_hashes": {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [ROOT / "gene_annotation_episode/hmmer_alignment_preparation_data.py",
                     ROOT / "gene_annotation_episode/hmmer_alignment_preparation_calculations.py",
                     ROOT / "tests/test_hmmer_alignment_preparation_data.py",
                     ROOT / "tests/test_hmmer_alignment_preparation_calculations.py"]}}
    (directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
    result = run_local_job(command, cwd=directory, policy=policy,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT), "TMPDIR": str(directory / "temporary"),
             "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = {**intent, "returncode": result.returncode, "metadata": result.metadata,
               "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print(result.stdout_path.read_text())
    print(result.stderr_path.read_text())


if __name__ == "__main__":
    main()
