"""Validate the current factual progress record without importing application code."""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
record = json.loads((HERE / "WORK_STATUS.json").read_text())
rows = {row["id"]: row for row in record["rows"]}
assert len(rows) == len(record["rows"]), "Duplicate evidence row IDs"
assert all(set(record["columns"]) <= row.keys() for row in rows.values())
bindings = record["resource_bindings"]
assert len({binding["id"] for binding in bindings}) == len(bindings)
evidence = {item["id"]: item for item in record["verification_evidence"]}
assert len(evidence) == len(record["verification_evidence"])

view = record["current_named_entry_progress"]
assert view["schema"] == "named_entry_implementation_progress_v1"
assert view["audit_is_required_for_goal_delivery"] is True
entries = view["entries"]
assert len({entry["name"] for entry in entries}) == len(entries)
assert len({entry["row_ids"][0] for entry in entries}) == len(entries)
assert view["evidence_id"] in evidence

# Canonical goal memberships and existing families are names, not format,
# lifecycle, alias, or independent-grader counts.
memberships = {
    (row["id"], membership["category"], membership["name"])
    for row in rows.values()
    for membership in row.get("current_goal_accounting", {}).get("goal_memberships", [])
}
assert memberships == {
    (entry["row_ids"][0], entry["category"], entry["name"])
    for entry in entries if entry["category"] != "existing_family"
}
for row in rows.values():
    accounting = row.get("current_goal_accounting", {})
    if accounting.get("role") in {"alias", "required_capability", "excluded", "outside_current_goal"}:
        assert not accounting.get("goal_memberships"), row["id"]

for entry in entries:
    status = entry["status"]
    assert status in {"done", "partial", "not_started"}, entry["name"]
    assert entry["row_ids"] and len(set(entry["row_ids"])) == len(entry["row_ids"])
    assert all(identity in rows for identity in entry["row_ids"])
    primary = rows[entry["row_ids"][0]]
    assert primary["overall"] == status, entry["name"]
    assert primary["current_named_progress_entry"] == entry["name"]
    assert bool(entry["missing_functionality"]) == (status != "done"), entry["name"]
    assert entry["evidence_ids"], entry["name"]
    audit = entry["audit_status"]
    assert audit in {"open", "selected_scope_verified", "not_started"}
    if audit == "open":
        assert entry["open_audit_work"], entry["name"]
    elif audit == "selected_scope_verified":
        assert status == "done" and not entry["open_audit_work"], entry["name"]
    if status == "not_started":
        assert audit == "not_started", entry["name"]

counts = dict(Counter(entry["status"] for entry in entries))
assert counts == view["counts"]
assert dict(Counter(entry["audit_status"] for entry in entries)) == view["audit_counts"]
assert view["counts_by_category"] == {
    category: dict(Counter(entry["status"] for entry in entries if entry["category"] == category))
    for category in {entry["category"] for entry in entries}
}
previous, current = Counter(), Counter()
for transition, count in view["status_transition_counts"].items():
    before, after = transition.split("->")
    assert before in view["status_meanings"] and after in view["status_meanings"]
    assert type(count) is int and count >= 0
    previous[before] += count
    current[after] += count
assert dict(previous) == view["superseded_reported_counts"]
assert dict(current) == counts

if "initial_run_scope" in view:
    scope = view["initial_run_scope"]
    assert scope["schema"] == "initial_run_scope_accounting_v1"
    assert scope["evidence_id"] in evidence
    assert scope["audit_requirements_preserved"] is True
    assert scope["full_inventory_retained"] is True
    for entry in entries:
        assert entry["initial_run_disposition"] in {"included", "deferred"}
    included = [entry for entry in entries if entry["initial_run_disposition"] == "included"]
    deferred = [entry for entry in entries if entry["initial_run_disposition"] == "deferred"]
    unfinished = [entry for entry in included if entry["status"] != "done"]
    assert scope["included_names"] == [entry["name"] for entry in included]
    assert scope["deferred_names"] == [entry["name"] for entry in deferred]
    assert scope["implementation_completion_names"] == [entry["name"] for entry in unfinished]
    assert scope["included_status_counts"] == dict(Counter(entry["status"] for entry in included))
    assert scope["deferred_status_counts"] == dict(Counter(entry["status"] for entry in deferred))
    assert scope["implementation_completion_counts"] == dict(Counter(entry["status"] for entry in unfinished))
    assert len(included) + len(deferred) == len(entries)
    print(
        f"Initial-run implementation list: {len(unfinished)} unfinished entries; "
        f"{len(deferred)} entries deferred. Required audits remain included."
    )

if "current_goal_progress" in view:
    goal = view["current_goal_progress"]
    assert goal["schema"] == "fixed_goal_member_progress_v1"
    by_name = {entry["name"]: entry for entry in entries}
    members = goal["member_names"]
    assert len(members) == len(set(members)) == goal["member_count"]
    assert all(name in by_name for name in members)
    assert all(by_name[name]["initial_run_disposition"] == "included" for name in members)
    assert goal["implementation_counts"] == dict(Counter(by_name[name]["status"] for name in members))
    assert goal["audit_counts"] == dict(Counter(by_name[name]["audit_status"] for name in members))
    complete = [name for name in members if by_name[name]["status"] == "done"
        and by_name[name]["audit_status"] == "selected_scope_verified"]
    assert goal["completed_names"] == complete
    assert goal["unfinished_names"] == [name for name in members if name not in complete]
    assert goal["deferred_count"] == sum(entry["initial_run_disposition"] == "deferred" for entry in entries)
    print(f"Fixed goal: {len(complete)}/{len(members)} complete with audit; "
        f"{len(goal['unfinished_names'])} unfinished.")

print(
    f"PASS: {len(entries)} unique named entries; "
    f"{counts.get('done', 0)} implemented, {counts.get('partial', 0)} partial, "
    f"{counts.get('not_started', 0)} not started. "
    "Memberships, gaps, references, audit states and prior-count reconciliation agree. "
    "Scientific completion was not tested."
)
