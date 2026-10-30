"""Prepare disjoint ComparativeSystems work without changing production.

The copied baseline includes the applied legacy proteome path. The separate
directional integration is still under verification; its later application is
an explicit shared-file reconciliation, not a dependency of native/calculator
implementation in new files.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / "candidate"
PRIOR = ROOT / "verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


assert not CANDIDATE.exists()
prior = json.loads((PRIOR / "BASELINE_001.json").read_text())
assert all(sha(ROOT / name) == value for name, value in prior.items())
sources = {name: ROOT / name for name in prior}
library = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
for path in sorted(library.rglob("*")):
    assert not path.is_symlink(), str(path)
    if path.is_file():
        sources[str(path.relative_to(ROOT))] = path
before = {name: sha(path) for name, path in sources.items()}
CANDIDATE.mkdir()
for name, path in sorted(sources.items()):
    assert not path.is_symlink(), name
    destination = CANDIDATE / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(path.read_bytes())
    assert sha(destination) == before[name], name
assert all(sha(ROOT / name) == value for name, value in before.items())
save("BASELINE_001.json", before)
save("PREPARATION_RECEIPT_001.json", {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "candidate": str(CANDIDATE),
    "copied_files": len(before),
    "source_files_unchanged": len(before),
    "prior_baseline_sha256": sha(PRIOR / "BASELINE_001.json"),
    "library_files": sum(name.startswith("research/") for name in before),
    "production_modified": False,
    "implementation_assigned": False,
    "contract_status": "185 additive interface closures under review",
    "shared_file_reconciliation": "182 directional integration remains a separate pending delta",
})
print(json.dumps({"candidate": str(CANDIDATE), "copied_files": len(before),
                  "production_modified": False, "implementation_assigned": False}))
