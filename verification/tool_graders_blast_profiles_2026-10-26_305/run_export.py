"""Record the bounded offline example export."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = (Path(__file__).parent / sys.argv[1]).resolve()
directory.mkdir(exist_ok=False)
command = [str(ROOT / ".venv/bin/python"), str(Path(__file__).with_name("write_examples.py").resolve()), str(directory / "filled")]
(directory / "command.json").write_text(json.dumps(command, indent=2) + "\n")
result = run_local_job(command, cwd=directory, policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3),
    stdout_path=directory / "stdout.log", stderr_path=directory / "stderr.log", env={"PYTHONPATH": str(ROOT)})
(directory / "receipt.json").write_text(json.dumps({"returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}, indent=2) + "\n")
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
