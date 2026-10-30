"""Read-only comparison of pinned tested inputs with the mutable workspace."""
from pathlib import Path
import hashlib
import json
import sys


packet = Path(__file__).resolve().parent
repo = packet.parents[1]
attempt = packet / sys.argv[1]
if not attempt.is_dir() or attempt.parent != packet:
    raise ValueError("original_attempt_required")
base = Path((repo / ".venv/pyvenv.cfg").read_text().split("home = ", 1)[1].splitlines()[0]).parent
roots = {
    "source": (attempt / "source_snapshot", repo),
    "dependency": (attempt / "dependencies", repo / ".venv/lib/python3.12/site-packages"),
    "standard_library": (attempt / "runtime/lib/python3.12", base / "lib/python3.12"),
    "binary": (attempt / "runtime", repo / ".venv/bin"),
}
result = {"attempt": str(attempt), "meaning": "Current inputs compared with the tested immutable snapshot; this does not rewrite that snapshot.", "comparisons": {}}
for label, (saved_root, current_root) in roots.items():
    rows = json.loads((attempt / (label + "_pins_before.json")).read_text())
    changed = []
    for row in rows:
        relative = Path(row["path"]).relative_to(saved_root)
        current = current_root / relative
        current_sha = hashlib.sha256(current.read_bytes()).hexdigest() if current.is_file() else None
        if current_sha != row["sha256"]:
            changed.append({"relative_path": str(relative), "tested_sha256": row["sha256"],
                            "current_sha256": current_sha})
    result["comparisons"][label] = {"compared_file_count": len(rows), "changed": changed}
destination = attempt / "workspace_drift.json"
destination.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({label: len(value["changed"]) for label, value in result["comparisons"].items()}))
