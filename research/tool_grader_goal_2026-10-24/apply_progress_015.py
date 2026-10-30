"""Record installed Codon parsing/calculation evidence without claiming a path."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / "WORK_STATUS.json"
raw = path.read_bytes()
prior = json.loads((HERE / "PROGRESS_UPDATE_014.json").read_text())
before_hash = hashlib.sha256(raw).hexdigest()
assert before_hash == prior["new_status_sha256"] == "f14d0fe92feb70e87f18d63bea35aabf7860694e7cf383c375a8f70acbb5b923"
assert not (HERE / "PROGRESS_UPDATE_015.json").exists()
work = json.loads(raw)
old = deepcopy(work)
base = "verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/"
report = json.loads((ROOT / base / "PRODUCTION_CODON_VERIFICATION_001.json").read_text())
assert report["tests"] == {"passed": 250, "failed": 0, "errors": 0, "skipped": 0}
assert report["saved_cases_reproduced"] == 31
assert report["forbidden_access_attempts"] == 0 and report["saved_inputs_unchanged"]
identity = "CODONTREE-NATIVE-AND-CALCULATORS-PRODUCTION-250"
assert identity not in {row["id"] for row in work["verification_evidence"]}
evidence = {
    "id": identity, "kind": "component_verification", "passed": 250, "failed": 0,
    "summary": "Two pure Codon modules installed; 159 parser and 91 calculation cases pass from production. All 31 saved calculation cases reproduce exactly without I/O, new imports or parsing.",
    "qualification": "Retained native membership/final alignment and source-derived or synthetic edge cases. Provider assembly, service binding, typed episode return and live resource verification remain unfinished. No scientific tool completion claim.",
    "reports": [{"path": base + name, "sha256": hashlib.sha256((ROOT / base / name).read_bytes()).hexdigest()}
        for name in ("PRODUCTION_CODON_INSTALLATION_001.json", "PRODUCTION_CODON_VERIFICATION_001.json",
                     "production-codon-tests-001.xml", "codon-native-numeric-correction-125/VALIDATION.json",
                     "codon-calculators-verification/VERIFICATION_REPORT_004.json")],
}
rows = {row["id"]: row for row in work["rows"]}
bindings = {row["id"]: row for row in work["resource_bindings"]}
row = rows["C-L193-CodonTree"]
row["overall"] = "shared_and_codon_components_installed_provider_and_episode_path_unfinished"
row["native_parser"] = "shared_formats_raxml8_and_four_codon_native_table_parsers_installed_and_verified"
row["metadata_extractor"] = "native_tables_and_raxml_values_retained_provider_identity_and_metadata_joins_in_progress"
row["deterministic_calculator"] = "eight_shared_and_three_codon_pure_calculations_verified_provider_grader_in_progress"
row["numerical_verification"] = "250_production_codon_tests_and_31_offline_saved_case_replays_pass_prior_150_shared_tests_preserved"
row["evidence_ids"].append(identity)
row["note"] += (" Update015: installed Codon native-table parsers and three separate calculations. "
    "Production tests: 250 passed; 31 complete saved cases reproduced with I/O, parsers, subprocesses, "
    "network and new imports disabled. Nonzero decimal underflow is failed/null with original token, "
    "not zero. Unknown empty historical populations retain explicit requirements. Retained final "
    "matrix sum_squared_frequency=10056.41975308642, mean=0.657282336803034, native rank=81.30133501475134. "
    "This does not reconstruct missing pre-trim history. Provider assembly and full service/episode "
    "integration remain in progress; live verification remains unfinished.")
binding = bindings["C-L193-CodonTree::api"]
binding["evidence_ids"] = deepcopy(row["evidence_ids"])
work["verification_evidence"].append(evidence)
assert len(work["rows"]) == len(old["rows"]) == 308
assert len(work["resource_bindings"]) == len(old["resource_bindings"]) == 288
assert work["complete_scientific_tools_claimed"] == old["complete_scientific_tools_claimed"] == 0
changes = []
for group in ("rows", "resource_bindings"):
    original = {row["id"]: row for row in old[group]}
    assert set(original) == {row["id"] for row in work[group]}
    for row in work[group]:
        if row != original[row["id"]]:
            changes.append({"group": group, "id": row["id"], "before": original[row["id"]], "after": deepcopy(row)})
after = (json.dumps(work, indent=2) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-24",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_hash, "new_status_sha256": hashlib.sha256(after).hexdigest(),
    "previous_goal_turn_classification": "no progress: the intervening bug explanation reported existing evidence; this continuation installed and verified the next available components",
    "changes": changes, "added_evidence": [evidence], "scope_changes": False,
    "specific_pending_NCBI_job_verification_included": False, "complete_scientific_tools_claimed": 0}
with (HERE / "PROGRESS_UPDATE_015.json").open("x") as record:
    record.write(json.dumps(update, indent=2) + "\n")
path.write_bytes(after)
print(json.dumps({"checkpoint": 15, "changes": len(changes), "added_evidence": 1,
    "scope_rows": 308, "resource_bindings": 288, "complete_scientific_tools_claimed": 0,
    "new_status_sha256": update["new_status_sha256"]}))
