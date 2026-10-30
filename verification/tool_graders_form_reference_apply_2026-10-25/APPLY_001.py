"""Apply the reviewed seven-file form-validation delta, preserving receipts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DELIVERY = ROOT / "verification/tool_graders_form_reference_integration_2026-10-25_178"
EXPECTED = {
    "gene_annotation_episode/bvbrc_alignment_returns.py",
    "gene_annotation_episode/bvbrc_genome_alignment_bundle_adapter.py",
    "gene_annotation_episode/bvbrc_genome_alignment_returns.py",
    "gene_annotation_episode/communication.py",
    "gene_annotation_episode/form_reference_validation.py",
    "tests/test_bvbrc_genome_alignment_episode_flow.py",
    "tests/test_form_reference_validation.py",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def save(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


assert not (HERE / "APPLICATION_RECEIPT_001.json").exists()
manifest_path = DELIVERY / "DELTA_HASHES_007.json"
manifest = json.loads(manifest_path.read_text())
assert len(manifest) == 7 and {r["path"] for r in manifest} == EXPECTED
for row in manifest:
    assert sha(ROOT / row["path"]) == row["before_sha256"], row["path"]
    assert sha(DELIVERY / "candidate" / row["path"]) == row["after_sha256"], row["path"]
patch = DELIVERY / "READY_DELTA_007.patch"
protected = {}
for folder in (
    "verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25",
    "verification/tool_graders_form_reference_validation_2026-10-25",
):
    for path in (ROOT / folder).rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            protected[str(path.relative_to(ROOT))] = sha(path)
save("PREFLIGHT_001.json", {
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "manifest_sha256": sha(manifest_path), "patch_sha256": sha(patch),
    "files": manifest, "protected_historical_files": protected,
})
for name, command in (
    ("DRY_RUN_001", ["patch", "--dry-run", "--forward", "-p1"]),
    ("APPLY_001", ["patch", "--forward", "-p1"]),
):
    result = subprocess.run(command, cwd=ROOT, input=patch.read_bytes(), capture_output=True)
    with (HERE / (name + ".log")).open("xb") as stream:
        stream.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"{name} failed; receipt retained")
for row in manifest:
    assert sha(ROOT / row["path"]) == row["after_sha256"], row["path"]
for path, before in protected.items():
    assert sha(ROOT / path) == before, path
save("APPLICATION_RECEIPT_001.json", {
    "recorded_at": datetime.now(timezone.utc).isoformat(), "production_applied": True,
    "files": manifest, "historical_files_unchanged": len(protected),
    "scope": "Synchronous form-local authenticated fact reuse and three prospective fixture corrections",
    "applied_workflow_verification": "pending",
})
print(json.dumps({"production_applied": True, "file_count": len(manifest),
    "historical_files_unchanged": len(protected)}))
