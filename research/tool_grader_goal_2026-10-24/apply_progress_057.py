"""Append inspected HMMER return/integration evidence; retain the fixed scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_057.json"
AUTHORITY = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def descriptor(relative):
    return {"path": relative, "sha256": sha(ROOT / relative)}

if UPDATE.exists():
    raise RuntimeError("immutable progress update already exists")
if sha(AUTHORITY) != "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7":
    raise RuntimeError("authority identity changed")
previous = json.loads((HERE / "PROGRESS_UPDATE_056.json").read_text())
before_sha = sha(STATUS)
if before_sha != previous["new_status_sha256"]:
    raise RuntimeError("status changed after056; inspect before updating")
status = json.loads(STATUS.read_text())
scope_sha = sha(HERE / "SCOPE.json")
before_ids = [row["id"] for row in status["rows"]]
before_bindings = deepcopy(status["resource_bindings"])

components = [
    ("HMMER-ARTIFACT-RECALCULATION-057", "tool_graders_hmmer_artifact_data_2026-10-26_268",
     [("check004", 105, 10), ("check005", 115, 0)], "RECALCULATION_ADDENDUM_001.md",
     "Fixed canonical-JSON annotation ordering; ten retained-native saved-recalculation cases fail before and pass after the fix, with native/network/file work forbidden."),
    ("HMMER-RETURNS-057", "tool_graders_hmmer_preparation_returns_2026-10-26_275",
     [("check004", 88, 0), ("check005", 7, 0)], "REPORT_001.md",
     "95 distinct retained-result/typed-return/preflight cases: partial preservation, requested-only forwarding, tamper rejection, replay and no duplicate credit."),
    ("HMMER-PRACTICAL-057", "tool_graders_hmmer_preparation_practical_2026-10-26_276",
     [("check001", 40, 0), ("check002", 100, 1)], "REPORT_001.md",
     "Exact local preparation request binding, five actual HMMER executions, binary-safe progress and explicit retry/replay. One old regression fixture requested the removed root state.query action; corrected separately in278/check003."),
    ("HMMER-SHARED-BOUNDARIES-057", "tool_graders_hmmer_preparation_shared_binding_2026-10-26_278",
     [("check001", 33, 0), ("check002", 5, 0), ("check003", 1, 0)], "README.md",
     "Shared execution/receipt hooks implemented. Existing boundary regressions, all five source-only receipt cases and corrected practical parent receipt test pass. Full26-mode Workflow proof remains pending."),
]
added, verification = [], []
for identity, directory, checks, report, summary in components:
    base = "verification/" + directory
    reports = [descriptor(base + "/" + report)]
    for check, passed, failed in checks:
        relative = base + "/" + check
        receipt = json.loads((ROOT / relative / "receipt.json").read_text())
        output = (ROOT / relative / "stdout.log").read_text()
        if receipt["returncode"] != (1 if failed else 0):
            raise RuntimeError("receipt status mismatch: " + relative)
        if not re.search(r"\b" + str(passed) + r" passed\b", output):
            raise RuntimeError("passed count mismatch: " + relative)
        if failed and not re.search(r"\b" + str(failed) + r" failed\b", output):
            raise RuntimeError("failed count mismatch: " + relative)
        evidence = descriptor(relative + "/receipt.json")
        reports.append(evidence)
        verification.append({"directory": relative, "passed": passed, "failed": failed,
                             "receipt": evidence})
    added.append({"id": identity, "kind": "component_and_shared_boundary_evidence",
        "summary": summary, "reports": reports,
        "qualification": "Original failed checkpoints are preserved; no complete resource or complete26-mode Workflow claim."})
if {e["id"] for e in status["verification_evidence"]}.intersection(e["id"] for e in added):
    raise RuntimeError("evidence already present")
status["verification_evidence"].extend(added)
changes = []
programs = ("alimask", "hmmbuild", "hmmconvert", "hmmemit", "hmmfetch", "hmmpress",
            "hmmsim", "hmmstat", "makehmmerdb", "hmmerfm-exactmatch")
for program in programs:
    row = next(r for r in status["rows"] if r["id"] == "A-L076-" + program)
    before = deepcopy(row)
    row["invocation_contract"] = "exact_local_practical_request_dispatch_and_original_attempt_identity_verified"
    row["production_result_binding"] = "capture_grading_publication_and_typed_returns_verified_shared_hooks_implemented"
    row["integration_verification"] = "component_and_shared_boundary_tests_passed_full26_mode_Workflow_verification_pending"
    row["evidence_ids"] = list(dict.fromkeys([*row["evidence_ids"], *[
        item["id"] for item in added if item["id"] != "HMMER-ARTIFACT-RECALCULATION-057"
        or program in {"hmmconvert", "hmmfetch", "hmmpress"}]]))
    row["note"] += (" Update057: exact local practical binding, requested typed returns and shared reference boundaries verified. Canonical-JSON optional-field ordering was corrected with a failing-before/passing-after regression. The obsolete practical receipt test no longer asks root to execute state.query. Full shared Workflow verification remains pending; tally unchanged.")
    changes.append({"group": "rows", "id": row["id"], "before": before, "after": deepcopy(row)})
assert len(status["rows"]) == 308 and [r["id"] for r in status["rows"]] == before_ids
assert status["resource_bindings"] == before_bindings
assert sha(HERE / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_sha, "new_status_sha256": hashlib.sha256(raw).hexdigest(),
    "scope_sha256_unchanged": scope_sha, "scope_changes": [], "changes": changes,
    "added_evidence": added, "verification": verification, "count_change": {},
    "numerical_grader_progress_tally": {"before": 79, "after": 79, "added_row_ids": [],
        "meaning": "Ten HMMER preparation rows remain outside the tally until full episode-path verification."},
    "remaining_fixed_rows_outside_tally": 229,
    "completed_work": ["Return and practical integration components implemented and verified within their declared scopes.",
        "Shared execution/receipt integration and source-only admission tests pass.",
        "Confirmed saved-sheet ordering defect fixed and115 component tests pass.",
        "One obsolete root-tool fixture corrected and its actual Workflow test passes."],
    "unfinished_work": ["Complete26-mode and both-parent-boundary HMMER Workflow verification.",
        "Explicit native mode/format gaps, including binary/HMMER2 body/index decoding and unestablished alignment-map cases.",
        "Previously recorded shared receipt fixture gaps not reaudited by this isolated practical fixture correction.",
        "Remaining fixed308-row goal, resource deployment and recorded generic TASK/STEERING/integration gaps."],
    "excluded_claims": ["Whole-goal completion", "Full26-mode Workflow completion", "API/HPC deployment",
        "Whole-checkout frozen verification", "W05 or annotation scoring", "Literature graders"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.057.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_rows": len(changes), "added_evidence": len(added),
    "numerical_grader_progress_tally": 79, "scope_rows": len(status["rows"]),
    "new_status_sha256": sha(STATUS)}))
