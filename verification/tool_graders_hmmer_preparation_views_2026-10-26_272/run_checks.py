"""Run the owned projection tests under the caller's exact local limits."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

HERE = Path(__file__).resolve().parent


def main():
    directory = HERE / sys.argv[1]
    directory.mkdir()
    policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
        "--basetemp", str(directory / "temporary"), str(ROOT / "tests/test_hmmer_preparation_result_views.py"), *sys.argv[2:]]
    paths = [ROOT / "gene_annotation_episode/hmmer_preparation_result_views.py", ROOT / "tests/test_hmmer_preparation_result_views.py",
        ROOT / "gene_annotation_episode/native_hmmer_preparation_worker.py", ROOT / "tests/test_native_hmmer_preparation_worker.py",
        *sorted((ROOT / "gene_annotation_episode").glob("hmmer_*data.py")), *sorted((ROOT / "gene_annotation_episode").glob("hmmer_*calculations.py"))]
    intent = {"argv": command, "cwd": str(directory), "policy": asdict(policy),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    (directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
    result = run_local_job(command, cwd=directory, policy=policy, env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "XDG_CACHE_HOME": str(directory / "cache"), "TMPDIR": str(directory)})
    receipt = {**intent, "returncode": result.returncode, "metadata": result.metadata,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print(result.stdout_path.read_text())


if __name__ == "__main__":
    main()
