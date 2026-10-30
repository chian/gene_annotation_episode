"""Read-only baseline comparison; write only the selected 417 analysis output."""
from pathlib import Path
import hashlib
import json
import pstats
import sqlite3
import sys

root, packet, output = map(Path, sys.argv[1:])
old = root / "verification/tool_graders_protein_structure_validation_profile_2026-10-27_415/check002"
new = packet / "profile001"


def read(directory, name):
    return json.loads((directory / name).read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def records(directory):
    connection = sqlite3.connect(f"file:{directory / 'diagnostic-state/state.sqlite3'}?mode=ro&immutable=1", uri=True)
    try:
        episode, action, result = connection.execute("SELECT episode_id,action,result FROM runtime_actions "
            "WHERE json_extract(action,'$.tool')='execution.results.collect' ORDER BY rowid LIMIT 1").fetchone()
        form, facts = connection.execute("SELECT form,facts FROM runtime_forms WHERE episode_id=?", (episode,)).fetchone()
        request, = connection.execute("SELECT request FROM runtime_episodes WHERE episode_id=?", (episode,)).fetchone()
        return dict(episode_id=episode, action=action, result=result, form=form, facts=facts, request=request)
    finally:
        connection.close()


before, after = records(old), records(new)
record_comparison = {name: {"identical": before[name] == after[name],
    "before_sha256": sha(before[name].encode()), "after_sha256": sha(after[name].encode()),
    "byte_length": len(after[name].encode())} for name in before}
(output / "admitted_input_form.json").write_text(after["form"])
(output / "frozen_input_facts.json").write_text(after["facts"])

selected = {("native_protein_structure_contracts.py", name) for name in (
    "protein_structure_execution_schema", "_execution_validator", "_checked", "_definitions",
    "validate_protein_structure_requested_job", "validate_protein_structure_job",
    "validate_protein_structure_request", "compile_protein_structure_job")}
selected |= {("_core.py", "crawl"), ("copy.py", "deepcopy"), ("communication.py", "plain"),
    ("validators.py", "check_schema"), ("native_protein_structure_returns.py", "authenticate"),
    ("episode_return_records.py", "authenticate"), ("native_protein_structure_returns.py", "_commission"),
    ("protein_structure_result_receipts.py", "completed_receipts"),
    ("native_protein_structure_results.py", "_verify_artifacts"), ("native_protein_structure_results.py", "_bytes")}


def profile(directory):
    stats = pstats.Stats(str(directory / "diagnostic.prof"))
    functions = {}
    for (filename, line, name), values in stats.stats.items():
        key = (Path(filename).name, name)
        if key in selected:
            label = ":".join(key)
            assert label not in functions
            functions[label] = dict(file=filename, line=line, primitive_calls=values[0],
                total_calls=values[1], self_seconds=values[2], cumulative_seconds=values[3])
    return dict(total_calls=stats.total_calls, primitive_calls=stats.prim_calls,
        total_self_seconds=stats.total_tt, functions=functions)


before_profile, after_profile = profile(old), profile(new)
with (output / "profile_all_cumulative.txt").open("w") as stream:
    pstats.Stats(str(new / "diagnostic.prof"), stream=stream).sort_stats("cumulative").print_stats()
with (output / "profile_all_tottime.txt").open("w") as stream:
    pstats.Stats(str(new / "diagnostic.prof"), stream=stream).sort_stats("tottime").print_stats()

before_stages = {row["stage"]: row for row in read(old, "profile_stages.json")}
after_stages = {row["stage"]: row for row in read(new, "profile_stages.json")}
stage_comparison = [{"stage": name, "before": before_stages[name], "after": after_stages[name]}
    for name in before_stages]
before_pins = {row["path"]: row for row in read(old, "source_pins_before.json")}
after_pins = {row["path"]: row for row in read(new, "source_pins_before.json")}
source_changes = [{"path": path, "before": before_pins.get(path), "after": after_pins.get(path)}
    for path in sorted(set(before_pins) | set(after_pins)) if before_pins.get(path) != after_pins.get(path)]
prechange = read(packet, "PRECHANGE_001.json")["source_and_baseline_pins"]
preservation = []
for row in prechange:
    # The production module is the deliberately changed input; all other
    # baseline415/416 artifacts and existing tests must remain exact.
    if row["path"] == "gene_annotation_episode/native_protein_structure_contracts.py":
        continue
    path = root / row["path"]
    raw = path.read_bytes()
    preservation.append({"path": row["path"], "unchanged":
        row["sha256"] == sha(raw) and row["byte_length"] == len(raw)})

before_measurement, after_measurement = [read(directory, "profile_measurement.json") for directory in (old, new)]
comparison = {
    "scope": "Same closed410/check007 retained admission diagnostic, fresh Python process and cProfile overhead; not whole Workflow timing.",
    "diagnostic_outcomes_identical": read(old, "diagnostic.json") == read(new, "diagnostic.json"),
    "stdout_identical": (old / "stdout.txt").read_bytes() == (new / "stdout.txt").read_bytes(),
    "exact_record_comparison": record_comparison,
    "returned_parent_report_serialized": False,
    "return_value_limit": "The byte-identical harness admits the exact original form with actual resolver and semantic callbacks but does not serialize its returned ParentReport; comparison covers admission input/facts and outcomes.",
    "baseline_and_existing_test_files_unchanged": all(row["unchanged"] for row in preservation),
    "baseline_and_existing_test_file_count": len(preservation),
    "retained_input_identity_all_four_manifests_equal": read(old, "retained_input_pins_before.json") ==
        read(old, "retained_input_pins_after.json") == read(new, "retained_input_pins_before.json") ==
        read(new, "retained_input_pins_after.json"),
    "retained_input_root_identical": read(old, "selected_request.json")["retained_input"] ==
        read(new, "selected_request.json")["retained_input"],
    "source_changes_between_executed_snapshots": source_changes,
    "before": {"measurement": before_measurement, "profile": before_profile, "receipt": read(old, "receipt.json")},
    "after": {"measurement": after_measurement, "profile": after_profile, "receipt": read(new, "receipt.json")},
    "wall_seconds_reduction": before_measurement["wall_seconds"] - after_measurement["wall_seconds"],
    "wall_percent_reduction_this_profiled_diagnostic": 100 * (1 - after_measurement["wall_seconds"] / before_measurement["wall_seconds"]),
    "stage_comparison": stage_comparison,
    "function_comparison": [{"function": name, "before": before_profile["functions"].get(name),
        "after": after_profile["functions"].get(name)} for name in
        sorted(set(before_profile["functions"]) | set(after_profile["functions"]))],
}
(output / "baseline_preservation.json").write_text(json.dumps(preservation, indent=2) + "\n")
(output / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
assert comparison["diagnostic_outcomes_identical"] and comparison["stdout_identical"]
assert comparison["baseline_and_existing_test_files_unchanged"]
assert comparison["retained_input_identity_all_four_manifests_equal"] and comparison["retained_input_root_identical"]
assert all(row["identical"] for row in record_comparison.values())
assert all(row["after"]["outcome"] == row["before"]["outcome"] == "accepted" for row in stage_comparison)
assert not after_measurement["blocked_dispatch_calls"]
for label in selected - {("_core.py", "crawl"), ("copy.py", "deepcopy"), ("communication.py", "plain")}:
    key = ":".join(label)
    assert before_profile["functions"][key]["total_calls"] == after_profile["functions"][key]["total_calls"]
assert after_profile["functions"]["_core.py:crawl"]["total_calls"] < before_profile["functions"]["_core.py:crawl"]["total_calls"]
print(json.dumps({name: comparison[name] for name in (
    "diagnostic_outcomes_identical", "exact_record_comparison", "baseline_and_existing_test_files_unchanged",
    "baseline_and_existing_test_file_count", "retained_input_identity_all_four_manifests_equal",
    "retained_input_root_identical", "wall_seconds_reduction", "wall_percent_reduction_this_profiled_diagnostic",
    "function_comparison")}, indent=2))
