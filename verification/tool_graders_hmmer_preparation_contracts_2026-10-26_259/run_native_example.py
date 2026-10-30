"""Preparation-only recorder for one explicitly supplied native invocation.

Not a production binding or grader. Each call names the exact executable and
arguments; no tool/resource selection, fallback, retry or installation occurs.
"""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parent
SOFTWARE = ROOT.parents[1] / "resources/software/infernal-1.1.5/hmmer/src"

def main():
    relative, program, *arguments = sys.argv[1:]
    directory = ROOT / "native" / relative
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "receipt.json"
    if receipt.exists():
        raise ValueError("example_already_recorded_use_a_new_explicit_attempt_name")
    executable = SOFTWARE / program
    command = [str(executable), *arguments]
    intent = {"argv": command, "cwd": str(directory), "executable_sha256":
              hashlib.sha256(executable.read_bytes()).hexdigest(),
              "policy": {"memory_bytes": 20 * 1024**3,
                         "scratch_bytes": 4 * 1024**3, "wall_seconds": None}}
    (directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
    result = run_local_job(command, cwd=directory,
                          policy=LocalJobPolicy(**intent["policy"]),
                          env={"PYTHONDONTWRITEBYTECODE": "1",
                               "XDG_CACHE_HOME": str(directory / "cache")})
    body = {**intent, "returncode": result.returncode,
            "metadata": result.metadata,
            "stdout_path": str(result.stdout_path),
            "stderr_path": str(result.stderr_path)}
    receipt.write_text(json.dumps(body, indent=2) + "\n")
    print(json.dumps({"example": relative, "returncode": result.returncode,
                      "receipt": str(receipt)}))

if __name__ == "__main__":
    main()
