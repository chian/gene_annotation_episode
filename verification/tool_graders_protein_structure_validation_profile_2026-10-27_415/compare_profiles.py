"""Compare retained415 profiles without rerunning validation or changing baseline."""
from pathlib import Path
import hashlib
import json
import pstats
import sqlite3

packet = Path(__file__).resolve().parent
old, new = packet / "check001", packet / "check002"


def read(directory, name):
    return json.loads((directory / name).read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def records(directory):
    path = directory / "diagnostic-state/state.sqlite3"
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    episode_id, action, result = connection.execute("SELECT episode_id,action,result FROM runtime_actions "
        "WHERE json_extract(action,'$.tool')='execution.results.collect' ORDER BY rowid LIMIT 1").fetchone()
    form, facts = connection.execute("SELECT form,facts FROM runtime_forms WHERE episode_id=?",
        (episode_id,)).fetchone()
    request, = connection.execute("SELECT request FROM runtime_episodes WHERE episode_id=?",
        (episode_id,)).fetchone()
    connection.close()
    return {"episode_id": episode_id, "action": action, "result": result,
        "form": form, "facts": facts, "request": request}


before_records, after_records = records(old), records(new)
record_comparison = {name: {"identical": before_records[name] == after_records[name],
    "before_sha256": sha(before_records[name].encode()), "after_sha256": sha(after_records[name].encode()),
    "byte_length": len(after_records[name].encode())} for name in before_records}
(new / "admitted_input_form.json").write_text(after_records["form"])
(new / "frozen_input_facts.json").write_text(after_records["facts"])

stages_before = {row["stage"]: row for row in read(old, "profile_stages.json")}
stages_after = {row["stage"]: row for row in read(new, "profile_stages.json")}
stage_comparison = []
for name, before in stages_before.items():
    after = stages_after[name]
    stage_comparison.append({"stage": name, "outcomes_identical": before["outcome"] == after["outcome"],
        "before_wall_seconds": before["wall_seconds"], "after_wall_seconds": after["wall_seconds"],
        "before_process_cpu_seconds": before["process_cpu_seconds"],
        "after_process_cpu_seconds": after["process_cpu_seconds"]})

selected = {("native_protein_structure_contracts.py", name) for name in
    ("protein_structure_execution_schema", "_execution_validator", "_checked",
     "validate_protein_structure_requested_job", "validate_protein_structure_job",
     "validate_protein_structure_request", "compile_protein_structure_job", "_definitions")}
selected |= {("_core.py", "crawl"), ("copy.py", "deepcopy"), ("communication.py", "plain"),
    ("validators.py", "check_schema"), ("native_protein_structure_returns.py", "authenticate"),
    ("episode_return_records.py", "authenticate"), ("native_protein_structure_returns.py", "_commission"),
    ("protein_structure_result_receipts.py", "completed_receipts"),
    ("native_protein_structure_results.py", "_verify_artifacts"), ("native_protein_structure_results.py", "_bytes")}


def selected_profile(directory):
    stats = pstats.Stats(str(directory / "diagnostic.prof"))
    result = {}
    for (filename, line, name), values in stats.stats.items():
        key = (Path(filename).name, name)
        if key in selected:
            label = ":".join(key)
            assert label not in result
            result[label] = {"file": filename, "line": line, "primitive_calls": values[0],
                "total_calls": values[1], "self_seconds": values[2], "cumulative_seconds": values[3]}
    return {"total_calls": stats.total_calls, "primitive_calls": stats.prim_calls,
        "total_self_seconds": stats.total_tt, "functions": result}


before_profile, after_profile = selected_profile(old), selected_profile(new)
function_comparison = [{"function": name, "before": before_profile["functions"].get(name),
    "after": after_profile["functions"].get(name)} for name in
    sorted(set(before_profile["functions"]) | set(after_profile["functions"]))]

pins_before = {row["path"]: row for row in read(old, "source_pins_before.json")}
pins_after = {row["path"]: row for row in read(new, "source_pins_before.json")}
source_changes = [{"path": name, "before": pins_before.get(name), "after": pins_after.get(name)}
    for name in sorted(set(pins_before) | set(pins_after)) if pins_before.get(name) != pins_after.get(name)]
baseline_pins = read(packet, "CHECK002_AUTHORIZATION_AND_PREFLIGHT.json")["baseline_manifest"]
current_pins = []
for path in sorted(old.rglob("*")):
    if path.is_file():
        raw = path.read_bytes()
        current_pins.append({"path": str(path.relative_to(old)), "sha256": sha(raw), "byte_length": len(raw)})

receipt_before, receipt_after = read(old, "receipt.json"), read(new, "receipt.json")
measurement_before, measurement_after = read(old, "profile_measurement.json"), read(new, "profile_measurement.json")
comparison = {
    "scope": "same fresh-process retained410/check007 extraction-result diagnostic, with cProfile overhead; not whole Workflow timing",
    "diagnostic_outcomes_identical": read(old, "diagnostic.json") == read(new, "diagnostic.json"),
    "stdout_identical": (old / "stdout.txt").read_bytes() == (new / "stdout.txt").read_bytes(),
    "exact_record_comparison": record_comparison,
    "returned_parent_report_serialized": False,
    "return_value_limit": "The unchanged harness validates and admits the exact original form but does not serialize the returned ParentReport object; comparison is of actual admission inputs and outcomes, not a separate output-object byte check.",
    "baseline_check001_files_unchanged": baseline_pins == current_pins,
    "baseline_file_count": len(baseline_pins),
    "retained_input_identity_all_four_manifests_equal": read(old, "retained_input_pins_before.json") == read(old, "retained_input_pins_after.json") == read(new, "retained_input_pins_before.json") == read(new, "retained_input_pins_after.json"),
    "source_changes_between_executed_snapshots": source_changes,
    "before": {"measurement": measurement_before, "profile": {k: v for k, v in before_profile.items() if k != "functions"}, "receipt": receipt_before},
    "after": {"measurement": measurement_after, "profile": {k: v for k, v in after_profile.items() if k != "functions"}, "receipt": receipt_after},
    "wall_seconds_reduction": measurement_before["wall_seconds"] - measurement_after["wall_seconds"],
    "wall_percent_reduction_this_profiled_diagnostic": 100 * (1 - measurement_after["wall_seconds"] / measurement_before["wall_seconds"]),
    "call_count_reduction": before_profile["total_calls"] - after_profile["total_calls"],
    "stage_comparison": stage_comparison,
    "function_comparison": function_comparison,
}
(new / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
print(json.dumps({name: comparison[name] for name in (
    "diagnostic_outcomes_identical", "stdout_identical", "baseline_check001_files_unchanged",
    "baseline_file_count", "retained_input_identity_all_four_manifests_equal", "exact_record_comparison",
    "source_changes_between_executed_snapshots", "wall_seconds_reduction",
    "wall_percent_reduction_this_profiled_diagnostic", "call_count_reduction")}, indent=2))
