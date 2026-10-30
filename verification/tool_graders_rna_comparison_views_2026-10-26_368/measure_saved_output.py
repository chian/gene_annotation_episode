"""Measure the already-verified selected scan serialization in a bounded job."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = PACKET / "measurement001"
directory.mkdir(exist_ok=False)
source = PACKET / "check003/temporary/pytest/test_large_scan_retains_all_me0/large_scan_selected_projection.json"
temporary, cache = directory / "temporary", directory / "cache"
temporary.mkdir()
cache.mkdir()
program = """from pathlib import Path
import json
import sys
value = json.loads(Path(sys.argv[1]).read_text())
projection = value["projection"]
serialized = json.dumps(projection)
print(json.dumps({"provenance": value["provenance"], "retained_member_count": value["retained_member_count"],
    "default_json_utf8_bytes": len(serialized.encode("utf-8")), "default_json_characters": len(serialized),
    "tested_upper_bound_bytes": 12000, "selected_numeric_cell_count": len(projection["payload"]["measurements"])}))
"""
argv = [str(REPO / ".venv/bin/python"), "-B", "-c", program, str(source)]
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
environment = {"PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
    "TMP": str(temporary), "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache), "PIP_CACHE_DIR": str(cache / "pip")}
(directory / "selected_request.json").write_text(json.dumps({"argv": argv, "cwd": str(directory),
    "policy": policy.to_dict(), "environment": environment}, indent=2) + "\n")
pins = [{"path": str(p.relative_to(REPO)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in (source, Path(__file__), REPO / "gene_annotation_episode/rna_structure_comparison_views.py")]
(directory / "source_pins_before.json").write_text(json.dumps(pins, indent=2) + "\n")
result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
    stderr_path=directory / "stderr.txt", env=environment)
after = [{"path": row["path"], "sha256": hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest()} for row in pins]
(directory / "source_pins_after.json").write_text(json.dumps(after, indent=2) + "\n")
receipt = {"returncode": result.returncode, "metadata": result.metadata,
    "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "source_pins_unchanged": pins == after}
(directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(result.stdout_path.read_text(), end="")
raise SystemExit(result.returncode)
