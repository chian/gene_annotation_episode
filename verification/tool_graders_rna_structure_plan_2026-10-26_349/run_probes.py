"""Execute tiny import/source probes through the existing bounded local runner."""
from dataclasses import asdict
from pathlib import Path
import json
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

repo = Path(__file__).resolve().parents[2]
packet = Path(__file__).resolve().parent
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
for label, interpreter in (
    ("project", repo / ".venv/bin/python"),
    ("upstream", repo / "reference/episode_tools/.venv/bin/python"),
):
    directory = packet / ("probe_" + label)
    directory.mkdir(exist_ok=False)
    request = {"argv": [str(interpreter), "-B", str(packet / "probe_rna.py")],
               "cwd": str(directory), "policy": policy.to_dict()}
    (directory / "selected_request.json").write_text(json.dumps(request, indent=2) + "\n")
    result = run_local_job(request["argv"], cwd=directory, policy=policy,
                           stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
                           env={"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory),
                                "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = {"returncode": result.returncode, "stdout_path": str(result.stdout_path),
               "stderr_path": str(result.stderr_path), "metadata": result.metadata}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"label": label, "returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
