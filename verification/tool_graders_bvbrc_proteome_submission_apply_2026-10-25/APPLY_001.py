"""Apply the reviewed immutable delta after original verification has ended."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DELIVERY = ROOT / "verification/tool_graders_bvbrc_proteome_submission_binding_2026-10-25_175"
ORIGINAL = ROOT / "verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


assert not (HERE / "APPLICATION_RECEIPT_001.json").exists()
terminal = read(ORIGINAL / "TERMINAL_RECEIPT_001.json")
assert terminal["natural_exit_code"] == 1
assert not terminal["run_interrupted"] and not terminal["run_restarted"]
assert not Path("/proc", str(terminal["pytest_pid"])).exists()
run = ROOT / terminal["run_directory"]
original_before = read(run / "SOURCE_HASHES_BEFORE.json")
original_after = read(run / "SOURCE_HASHES_AFTER_TESTS.json")
guard = read(run / "SOURCE_GUARD_AFTER_TESTS.json")
assert not guard["all_changes"] and not guard["used_changes"] and not guard["used_without_before_hash"]
for path in guard["used_paths"]:
    assert original_before[path] == original_after[path] == sha(ROOT / path), path
manifest = read(DELIVERY / "DELTA_MANIFEST_002.json")
patch = DELIVERY / "DELTA_002.patch"
assert sha(patch) == manifest["patch_sha256"] == "734c792da3235b66e960fb1a09a073cc4d358b174963ef39cd0064b55bdb535c"
assert len(manifest["files"]) == 14
for row in manifest["files"]:
    target = ROOT / row["path"]
    assert (not target.exists()) if row["kind"] == "new" else (sha(target) == row["before_sha256"]), row["path"]
    assert sha(DELIVERY / "candidate" / row["path"]) == row["candidate_sha256"], row["path"]
for row in manifest["unchanged_frozen_assets"]:
    assert sha(ROOT / row["path"]) == row["sha256"], row["path"]
save("PREFLIGHT_001.json", dict(recorded_at=datetime.now(timezone.utc).isoformat(),
    original_terminal_receipt_sha256=sha(ORIGINAL / "TERMINAL_RECEIPT_001.json"),
    original_source_audit_sha256=sha(ORIGINAL / "TERMINAL_SOURCE_AUDIT_001.json"),
    original_used_sources_rehashed=len(guard["used_paths"]), original_process_absent=True,
    delta_sha256=sha(patch), target_count=len(manifest["files"]), all_targets_match=True))
for name, argv in (("DRY_RUN_001", ["patch", "--dry-run", "--forward", "-p1"]),
                   ("APPLY_001", ["patch", "--forward", "-p1"])):
    result = subprocess.run(argv, cwd=ROOT, input=patch.read_bytes(), capture_output=True)
    (HERE / (name + ".log")).write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"{name} failed: {result.returncode}; original output retained")
for row in manifest["files"]:
    assert sha(ROOT / row["path"]) == row["candidate_sha256"], row["path"]
for row in manifest["unchanged_frozen_assets"]:
    assert sha(ROOT / row["path"]) == row["sha256"], row["path"]
receipt = dict(recorded_at=datetime.now(timezone.utc).isoformat(), production_applied=True,
    patch_sha256=sha(patch), applied_file_count=len(manifest["files"]), files=manifest["files"],
    original_run_unchanged=True, historical_assets_unchanged=True, new_verification_pending=True,
    scope="Reviewed submitted-request binding only; no provider registration, episode wiring or scoring formula change")
save("APPLICATION_RECEIPT_001.json", receipt)
print(json.dumps({key: receipt[key] for key in ("production_applied", "applied_file_count", "historical_assets_unchanged", "new_verification_pending")}))
