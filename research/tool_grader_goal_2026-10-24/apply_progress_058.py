"""Record inspected final HMMER preparation evidence without changing scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_058.json"
BASE = "verification/tool_graders_hmmer_preparation_workflow_2026-10-26_277"
AUTHORITY = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(relative):
    return {"path": relative, "sha256": sha(ROOT / relative)}


if UPDATE.exists():
    raise RuntimeError("immutable progress update already exists")
if sha(AUTHORITY) != "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7":
    raise RuntimeError("authority identity changed")
previous = json.loads((HERE / "PROGRESS_UPDATE_057.json").read_text())
before_sha = sha(STATUS)
if before_sha != previous["new_status_sha256"]:
    raise RuntimeError("status changed after057; inspect before updating")
status = json.loads(STATUS.read_text())
scope_sha = sha(HERE / "SCOPE.json")
before_ids = [row["id"] for row in status["rows"]]
before_bindings = deepcopy(status["resource_bindings"])
manifest = json.loads((ROOT / BASE / "FINAL_MANIFEST.json").read_text())
index = json.loads((ROOT / BASE / "EVIDENCE_INDEX.json").read_text())
for key, expected in {"tests_passed": 112, "native_attempts": 52,
                      "native_modes": 26, "slotted_native_programs": 10}.items():
    if manifest[key] != expected or index[key] != expected:
        raise RuntimeError("evidence count mismatch: " + key)
for group in ("run_receipts", "junit_results", "tested_verification_files"):
    for item in manifest[group].values():
        if sha(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError("retained evidence changed: " + item["path"])
for key in ("evidence_index", "readme"):
    item = manifest[key]
    if sha(ROOT / item["path"]) != item["sha256"]:
        raise RuntimeError("retained evidence changed: " + item["path"])
verification = []
for check, count in (("check009", 36), ("check010", 76)):
    folder = ROOT / BASE / check
    receipt = json.loads((folder / "receipt.json").read_text())
    suites = ET.parse(folder / "junit.xml").getroot().findall("testsuite")
    totals = {key: sum(int(s.get(key, 0)) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    if receipt["returncode"] != 0 or totals != {"tests": count, "failures": 0, "errors": 0, "skipped": 0}:
        raise RuntimeError("final verification mismatch: " + check)
    verification.append({"directory": BASE + "/" + check, "passed": count,
        "failed": 0, "receipt": descriptor(BASE + "/" + check + "/receipt.json"),
        "junit": descriptor(BASE + "/" + check + "/junit.xml")})
evidence = {"id": "HMMER-PREPARATION-FULL-WORKFLOW-058",
    "kind": "native_local_and_scripted_shared_workflow_evidence",
    "summary": "112 final tests;52 native attempts;26 declared modes;10 programs through both requested scientific parent boundaries.",
    "reports": [descriptor(BASE + "/" + name) for name in
        ("README.md", "FINAL_MANIFEST.json", "EVIDENCE_INDEX.json")],
    "qualification": "Exact retained test snapshots; scripted decisions and scientific horizons; actual native work, practical completion and typed returns. Two unrelated literature files changed during runs. Later translation/extraction edits are outside these snapshots. API/HPC and configured-model science are unverified; opaque format internals remain explicit."}
if any(item["id"] == evidence["id"] for item in status["verification_evidence"]):
    raise RuntimeError("evidence already present")
status["verification_evidence"].append(evidence)
programs = ("alimask", "hmmbuild", "hmmconvert", "hmmemit", "hmmfetch", "hmmpress",
            "hmmsim", "hmmstat", "makehmmerdb", "hmmerfm-exactmatch")
changes = []
for program in programs:
    row = next(item for item in status["rows"] if item["id"] == "A-L076-" + program)
    before = deepcopy(row)
    row.update(overall="local_numerical_preparation_path_verified_remaining_subcases_explicit",
        invocation_contract="verified_declared_modes_through_selected_local_native_execution",
        production_result_binding="verified_existing_launch_local_results_and_two_scientific_boundaries",
        integration_verification="verified_all26_declared_modes_and10_program_nested_typed_return_paths",
        live_resource_verification="verified_tiny_actual_local_native_jobs_no_api_or_hpc_deployment_claim")
    row["evidence_ids"] = list(dict.fromkeys([*row["evidence_ids"], evidence["id"]]))
    row["note"] += (" Update058: final36 mode/workflow and76 nested tests passed, including52 actual local attempts, all26 declared modes and10 programs through results-to-scientific_process-to-annotation requested forms. Saved-data recalculation, exact replay, requested-only disclosure, forged facts, partial outputs, explicit native failures and practical exact-zero closure are covered. This adds the row to numerical implementation progress, not full scientific/resource completion. Original opaque-format, unestablished expert-mode, prompt and resource gaps remain; no API/HPC or configured-model science claimed.")
    changes.append({"group": "rows", "id": row["id"], "before": before, "after": deepcopy(row)})
assert len(status["rows"]) == 308 and [row["id"] for row in status["rows"]] == before_ids
assert status["resource_bindings"] == before_bindings
assert sha(HERE / "SCOPE.json") == scope_sha
tally_before = previous["numerical_grader_progress_tally"]["after"]
tally_after = tally_before + len(changes)
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_sha, "new_status_sha256": hashlib.sha256(raw).hexdigest(),
    "scope_sha256_unchanged": scope_sha, "scope_changes": [], "changes": changes,
    "added_evidence": [evidence], "verification": verification,
    "numerical_grader_progress_tally": {"before": tally_before, "after": tally_after,
        "added_row_ids": [row["id"] for row in changes],
        "meaning": "Implemented numerical preparation/validation with tested declared local episode paths; not all-resource or every-variant completion."},
    "remaining_fixed_rows_outside_tally": 308 - tally_after,
    "completed_work": ["Ten HMMER preparation programs now have inspected final native mode and nested episode verification.",
        "Original action/return ownership, exact-zero practical completion, no repeated credit and requested-only disclosure verified."],
    "unfinished_work": ["Translation/extraction publication and Workflow verification in progress; neither row counted here.",
        "Explicit binary/HMMER2/index-internal and additional native subcase gaps remain.",
        "Previously recorded shared receipt fixture gaps outside this verified HMMER boundary remain.",
        "Remaining fixed308-row goal, resource deployments and generic TASK/STEERING/integration gaps remain."],
    "excluded_claims": ["Whole-goal completion", "API/HPC deployment", "Every possible native option",
        "Configured-model scientific investigation", "Whole-checkout frozen verification", "W05 or annotation scoring", "Literature graders"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.058.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_rows": len(changes), "numerical_grader_progress_tally": tally_after,
    "scope_rows": len(status["rows"]), "new_status_sha256": sha(STATUS)}))
