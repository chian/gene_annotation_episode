from pathlib import Path
import json
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
repo = packet.parents[1]
directory = packet / "arithmetic"
directory.mkdir(exist_ok=False)
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
argv = [str(repo / ".venv/bin/python"), "-B", str(packet / "check_example_arithmetic.py")]
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory), "policy": policy.to_dict()}, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy,
    stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
    env={"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory), "XDG_CACHE_HOME": str(directory / "cache")})
receipt = {"returncode": result.returncode, "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, sort_keys=True))
