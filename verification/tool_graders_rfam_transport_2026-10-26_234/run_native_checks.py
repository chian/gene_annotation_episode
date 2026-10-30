"""Run retained-format qualification with the same bounded local runner."""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


directory = Path(__file__).resolve().parent
repo = directory.parents[1]
output = directory / "native_checks_001"
output.mkdir()
temporary = output / "temporary"
temporary.mkdir()
command = [str(repo / ".venv/bin/python"), str(directory / "verify_native_formats.py")]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {"PYTHONPATH": str(repo), "PYTHONDONTWRITEBYTECODE": "1",
               "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
               "XDG_CACHE_HOME": str(output / "cache")}
result = run_local_job(command, cwd=output, policy=policy, env=environment)
receipt = {"command": command, "policy": policy.to_dict(), "environment": environment,
           "returncode": result.returncode, "stdout_path": str(result.stdout_path),
           "stderr_path": str(result.stderr_path), "metadata": result.metadata,
           "source_sha256": {str(path.relative_to(repo)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in (directory / "verify_native_formats.py",
                            repo / "gene_annotation_episode/infernal_search_inputs.py",
                            repo / "gene_annotation_episode/infernal_search_grader.py")}}
(output / "verification-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
