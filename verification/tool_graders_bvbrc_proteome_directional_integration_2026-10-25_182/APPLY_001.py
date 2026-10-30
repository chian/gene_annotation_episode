"""Apply the exact verified D/F delta, then check the actual root facade.

This script is prepared before final host/Workflow verification. It refuses to
change production until those exact source-stable runs have terminal success.
It never edits authority, historical receipts or an unrelated source file.
"""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / "candidate"
TESTS = (
    "test_bvbrc_proteome_bundle_v2_contracts.py",
    "test_bvbrc_proteome_bundle_v2_resolution.py",
    "test_bvbrc_proteome_directional_saved_validation.py",
    "test_bvbrc_proteome_directional_publication.py",
    "test_bvbrc_proteome_directional_fact_contracts.py",
    "test_bvbrc_proteome_directional_projection.py",
    "test_bvbrc_proteome_directional_returns.py",
    "test_bvbrc_proteome_directional_episode_path.py",
    "test_bvbrc_proteome_directional_tool_info.py",
    "test_bvbrc_proteome_returns.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read(relative):
    return json.loads((HERE / relative).read_text())


def save(relative, value):
    target = HERE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def check_run(relative, expected_sources, *, expected_cases=None):
    receipt = read(relative + "/receipt.json")
    assert receipt["passed"] and receipt["exit_code"] == 0, relative
    assert not receipt["changed_sources"], relative
    assert read(relative + "/source_before.json") == expected_sources, relative
    assert read(relative + "/source_after.json") == expected_sources, relative
    counts = receipt["case_counts"]
    assert counts["passed"] > 0 and all(counts[key] == 0 for key in ("failed", "error", "skipped")), relative
    if expected_cases is not None:
        assert counts["passed"] == expected_cases, (relative, counts)
    cases = read(relative + "/cases.json")
    identities = {(case["classname"], case["name"]) for case in cases}
    assert len(identities) == len(cases) == counts["passed"], relative
    return identities


assert not (HERE / "APPLICATION_RECEIPT_001.json").exists()
freeze1, freeze2, final = (read(name) for name in (
    "FREEZE_INDEPENDENT_001.json", "FREEZE_INDEPENDENT_002.json", "FREEZE_001.json"))
first_sources, host_sources, final_sources = (item["sources"] for item in (freeze1, freeze2, final))
assert set(first_sources) == set(host_sources)
assert [name for name in first_sources if first_sources[name] != host_sources[name]] == [
    "tests/test_bvbrc_proteome_directional_returns.py"]
assert set(final_sources) - set(host_sources) == {"tests/test_bvbrc_proteome_directional_episode_path.py"}
assert all(final_sources[name] == value for name, value in host_sources.items())
assert all(sha(CANDIDATE / name) == value for name, value in final_sources.items())

unit_ids = check_run("final_unit_001", first_sources, expected_cases=737)
host_ids = check_run("final_host_001", host_sources)
workflow_ids = check_run("final_workflow_001", final_sources, expected_cases=2)
assert not unit_ids.intersection(host_ids | workflow_ids)
assert not host_ids.intersection(workflow_ids)
package = read("package_verification_001/receipt.json")
assert package["passed"] and not package["changed_sources"]
assert read("package_verification_001/source_before.json") == first_sources
assert read("package_verification_001/source_after.json") == first_sources
installed = read("package_verification_001/installed_result.json")
assert installed["implementation_sha256"] == "7dbdd8cfbc5193d149af6bfd314e0199ff074a1d671a39e1395a785b22b10ce9"
assert installed["legacy_implementation_sha256"] == "4a38563301a75481c9fc8cfcde77e0a09b9d8e08f3c0562e9635c18692e44a20"

production_review = read("PRODUCTION_REVIEW_001.json")
assert sha(HERE / "PRODUCTION_DELTA_001.patch") == production_review["patch_sha256"]
for entry in production_review["files"]:
    assert sha(ROOT / entry["path"]) == entry["before_sha256"], entry["path"]
    assert sha(CANDIDATE / entry["path"]) == entry["candidate_sha256"], entry["path"]
baseline = read("BASELINE_001.json")
assert all(sha(ROOT / name) == value for name, value in baseline.items())
allowed = {entry["path"] for entry in production_review["files"]} | {"tests/" + name for name in TESTS}
changed = {name for name, value in final_sources.items() if sha(ROOT / name) != value}
assert changed == allowed and len(changed) == 25, sorted(changed ^ allowed)
before = {name: sha(ROOT / name) for name in final_sources}
files, patch = [], []
for name in sorted(allowed):
    original = (ROOT / name).read_text() if (ROOT / name).is_file() else ""
    candidate = (CANDIDATE / name).read_text()
    files.append({"path": name, "before_sha256": before[name], "candidate_sha256": final_sources[name]})
    patch.extend(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True),
                                    fromfile="a/" + name, tofile="b/" + name))
with (HERE / "DELTA_001.patch").open("x") as stream:
    stream.write("".join(patch))
save("DELTA_MANIFEST_001.json", {"files": files, "patch_sha256": sha(HERE / "DELTA_001.patch"),
                               "freeze_sha256": sha(HERE / "FREEZE_001.json")})
save("PREFLIGHT_001.json", {"source_before": before, "source_target": final_sources,
                          "distinct_passing_candidate_cases": len(unit_ids | host_ids | workflow_ids),
                          "unit_cases": len(unit_ids), "host_cases": len(host_ids),
                          "workflow_cases": len(workflow_ids),
                          "verification_receipts": {name: sha(HERE / name) for name in (
                              "final_unit_001/receipt.json", "final_host_001/receipt.json",
                              "final_workflow_001/receipt.json", "package_verification_001/receipt.json")}})

receipt = {"started_at": datetime.now(timezone.utc).isoformat(), "production_applied": False,
           "applied_facade_verified": False, "live_service_execution_verified": False,
           "files": files, "written_paths": [], "unchanged_v1_implementation_sha256": installed["legacy_implementation_sha256"],
           "v2_implementation_sha256": installed["implementation_sha256"],
           "distinct_passing_candidate_cases": len(unit_ids | host_ids | workflow_ids),
           "delta_manifest_sha256": sha(HERE / "DELTA_MANIFEST_001.json")}
clock = time.monotonic()
try:
    for entry in files:
        destination = ROOT / entry["path"]
        assert sha(destination) == entry["before_sha256"], entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name("." + destination.name + ".apply182.tmp")
        with temporary.open("xb") as stream:
            stream.write((CANDIDATE / entry["path"]).read_bytes())
        temporary.replace(destination)
        receipt["written_paths"].append(entry["path"])
    assert all(sha(ROOT / name) == value for name, value in final_sources.items())
    receipt["production_applied"] = True
    output = HERE / "applied_native_check_001"
    output.mkdir(exist_ok=False)
    command = [sys.executable, "-I", str(HERE / "PACKAGE_PROBE_001.py"), str(ROOT),
               str(HERE / "evidence_d/package_input_001.json")]
    save("applied_native_check_001/command.json", {"argv": command, "cwd": str(output)})
    result = subprocess.run(command, cwd=output, text=True, capture_output=True)
    (output / "stdout.log").write_text(result.stdout)
    (output / "stderr.log").write_text(result.stderr)
    receipt["applied_probe_exit_code"] = result.returncode
    assert result.returncode == 0, "applied native facade probe failed"
    checked = json.loads(result.stdout)
    assert checked == installed, "applied facade differs from the installed frozen facade"
    save("applied_native_check_001/result.json", checked)
    receipt["applied_facade_verified"] = True
except Exception as error:
    receipt.update(error_type=type(error).__name__, error=str(error))
finally:
    after = {name: sha(ROOT / name) for name in final_sources}
    save("APPLICATION_SOURCE_AFTER_001.json", after)
    receipt.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - clock,
                   source_count=len(after), unexpected_sources=[name for name in after if after[name] != final_sources[name]])
    save("APPLICATION_RECEIPT_001.json", receipt)
    print(json.dumps({key: receipt[key] for key in (
        "production_applied", "applied_facade_verified", "written_paths", "source_count", "unexpected_sources")}))
sys.exit(0 if receipt["production_applied"] and receipt["applied_facade_verified"] and not receipt["unexpected_sources"] else 1)
