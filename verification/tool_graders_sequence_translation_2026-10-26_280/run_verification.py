"""Execute workload280 native studies/tests with the existing local envelope."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

output = Path(__file__).parent / sys.argv[1]
output.mkdir()
mode = sys.argv[2]
paths = ["gene_annotation_episode/sequence_translation_grader.py",
         "gene_annotation_episode/sequence_ops.py", "gene_annotation_episode/sequence_mapping.py",
         "tests/test_sequence_translation_grader.py", "gene_annotation_episode/knowledge/sequence-translation.md"]
paths = [path for path in paths if (ROOT / path).is_file()]
hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
if mode == "study":
    command = [str(ROOT / ".venv/bin/python"), str(Path(__file__).with_name("native_study.py")), str(output)]
else:
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
               str(ROOT / "tests/test_sequence_translation_grader.py"),
               "--basetemp=" + str(output / "temporary"), "--junitxml=" + str(output / "junit.xml"), *sys.argv[3:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(output / "intent.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(),
    "source_hashes": hashes}, indent=2) + "\n")
result = run_local_job(command, cwd=output, policy=policy,
                      env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
after = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
(output / "receipt.json").write_text(json.dumps({"returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path),
    "source_hashes_before": hashes, "source_hashes_after": after, "sources_unchanged": after == hashes}, indent=2) + "\n")
print(json.dumps({"directory": str(output), "returncode": result.returncode,
    "stdout_tail": result.stdout_path.read_text()[-18000:], "stderr_tail": result.stderr_path.read_text()[-2000:]}))
raise SystemExit(result.returncode)
