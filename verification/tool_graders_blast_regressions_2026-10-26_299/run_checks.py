"""Run only the contracted offline regressions through the native job boundary."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

EVIDENCE = Path(__file__).resolve().parent
TESTS = ["tests/test_blast_binding.py", "tests/test_blast_result_views.py",
         "tests/test_blast_typed_return_integration.py"]


def main():
    check = EVIDENCE / sys.argv[1]
    check.mkdir(exist_ok=False)
    (check / "temporary").mkdir()
    paths = sorted(ROOT.glob("gene_annotation_episode/*.py"))
    paths += [ROOT / name for name in TESTS]
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths}
    (check / "source_hashes.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if sys.argv[1] == "checks_001":
        for name in TESTS:
            shutil.copy2(ROOT / name, EVIDENCE / "initial" / name)
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-vv", "-p", "no:cacheprovider",
               *[str(ROOT / name) for name in TESTS],
               "--basetemp", str(check / "temporary/pytest"),
               "--junitxml", str(check / "junit.xml")]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    request = {"command": command, "cwd": str(check), "policy": policy.to_dict(),
               "started_at": datetime.now(timezone.utc).isoformat()}
    (check / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    result = run_local_job(command, cwd=check, policy=policy,
        stdout_path=check / "stdout.txt", stderr_path=check / "stderr.txt",
        env={"PYTHONPATH": str(ROOT), "TMPDIR": str(check / "temporary"),
             "PYTHONDONTWRITEBYTECODE": "1"})
    receipt = asdict(result)
    receipt["stdout_path"] = str(receipt["stdout_path"])
    receipt["stderr_path"] = str(receipt["stderr_path"])
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    (check / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"check": str(check), "returncode": result.returncode}, sort_keys=True))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
