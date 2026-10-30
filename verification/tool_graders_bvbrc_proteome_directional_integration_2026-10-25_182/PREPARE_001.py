"""Compose an isolated D/F checkout from applied numerical code and reviewed176.

This does not apply176 or alter any production, frozen candidate or authority.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / "candidate"
UPSTREAM = ROOT / "verification/tool_graders_bvbrc_proteome_api_integration_2026-10-25_176"
NUMERICAL = ROOT / "verification/tool_graders_bvbrc_proteome_directional_build_2026-10-25_179"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


assert not CANDIDATE.exists()
manifest_path = UPSTREAM / "DELTA_MANIFEST_002.json"
manifest = json.loads(manifest_path.read_text())
assert len(manifest["files"]) == 20
assert not manifest["unexpected_original_changes"]
assert sha(UPSTREAM / "DELTA_002.patch") == manifest["patch_sha256"]
assert sha(NUMERICAL / "APPLICATION_RECEIPT_001.json") == manifest["root179_application_receipt_sha256"]
numerical = json.loads((NUMERICAL / "APPLICATION_RECEIPT_001.json").read_text())
for row in numerical["files"]:
    assert sha(ROOT / row["path"]) == row["after_sha256"], row["path"]
sources = {}
for base in ("gene_annotation_episode", "tests", "method_loop"):
    for path in sorted((ROOT / base).rglob("*")):
        relative = path.relative_to(ROOT)
        if "__pycache__" in relative.parts or any(p.startswith(".pytest") for p in relative.parts):
            continue
        assert not path.is_symlink(), str(relative)
        if path.is_file() and path.suffix not in (".pyc", ".pyo"):
            sources[str(relative)] = path
sources["pyproject.toml"] = ROOT / "pyproject.toml"
# The176 retained contract/native examples are actual input fixtures, not a
# dependency on its temporary test directories or frozen source imports.
for path in sorted((UPSTREAM / "candidate/verification").rglob("*")):
    assert not path.is_symlink()
    if path.is_file():
        relative = str(path.relative_to(UPSTREAM / "candidate"))
        assert sha(path) == sha(ROOT / relative), relative
        sources[relative] = ROOT / relative
original = {name: sha(path) for name, path in sources.items()}
overlays = {}
for row in manifest["files"]:
    name = row["path"]
    assert sha(UPSTREAM / "candidate" / name) == row["candidate_sha256"], name
    actual = sha(ROOT / name) if (ROOT / name).exists() else None
    assert actual == row["before_sha256"], name
    sources[name] = UPSTREAM / "candidate" / name
    overlays[name] = row["candidate_sha256"]
CANDIDATE.mkdir()
baseline = {}
for name, source in sorted(sources.items()):
    destination = CANDIDATE / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    baseline[name] = sha(destination)
    assert baseline[name] == sha(source), name
assert all(sha(ROOT / name) == value for name, value in original.items())
save("ROOT_BEFORE_001.json", original)
save("BASELINE_001.json", baseline)
save("COMPOSITION_RECEIPT_001.json", {
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "candidate": str(CANDIDATE),
    "files": len(baseline),
    "root_source_files_unchanged": len(original),
    "production_applied": False,
    "delta176_manifest_sha256": sha(manifest_path),
    "delta176_patch_sha256": manifest["patch_sha256"],
    "delta176_files": overlays,
    "numerical179_application_sha256": sha(NUMERICAL / "APPLICATION_RECEIPT_001.json"),
    "numerical179_applied_verification_sha256": sha(NUMERICAL / "applied_verification_001/receipt.json"),
    "upstream176_status": "verified_candidate_not_yet_applied_to_root",
    "D_F_status": "not_implemented",
    "live_service_execution_verified": False,
})
print(json.dumps({"candidate": str(CANDIDATE), "files": len(baseline),
                  "reviewed176_overlays": len(overlays), "production_applied": False}))
