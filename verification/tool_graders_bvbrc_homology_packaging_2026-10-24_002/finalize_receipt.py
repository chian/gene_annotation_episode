"""Check immutable comparison inputs and current-source equality, then hash evidence."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


packages = json.loads((HERE / "PACKAGE_SOURCE_SHA256.json").read_text())
assert all(digest(ROOT / name) == expected for name, expected in packages.items())
provenance = json.loads((HERE / "FIXTURE_PROVENANCE.json").read_text())
assert all(digest(ROOT / name) == expected for name, expected in provenance["prior_retained_files_sha256"].items())
previous = json.loads((ROOT / "verification/tool_graders_bvbrc_homology_packaging_2026-10-24/verification.json").read_text())
assert digest(ROOT / previous["wheel"]) == previous["wheel_sha256"]
wheel = json.loads((HERE / "WHEEL.json").read_text())
assert digest(ROOT / wheel["wheel"]) == wheel["sha256"]
assert all(json.loads((HERE / name).read_text())["exit_code"] == 0
           for name in ("serialize-result.json", "build-result.json", "isolated-result.json"))
report = {
    "status": "passed", "current_source_files_still_equal_wheel": len(packages),
    "prior_wheel_unchanged": True, "prior_wheel_sha256": previous["wheel_sha256"],
    "prior_retained_comparison_inputs_unchanged": True,
    "current_wheel_sha256": wheel["sha256"],
}
(HERE / "FINAL_AUDIT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
manifest = {str(path.relative_to(HERE)): digest(path) for path in sorted(HERE.rglob("*"))
            if path.is_file() and path.name != "EVIDENCE_SHA256.json"}
(HERE / "EVIDENCE_SHA256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(json.dumps(report, sort_keys=True))
