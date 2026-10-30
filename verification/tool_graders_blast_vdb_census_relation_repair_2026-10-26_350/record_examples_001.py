"""Retain complete public-path inputs/results for350's before/after evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from test_blast_vdb_function_census_relations import (
    MODEL_POLICIES, checked_calculate, census_link, fixture, original_input,
    model_for, weights, saved_only,
)
from gene_annotation_episode import blast_vdb_function_inputs as inputs
from gene_annotation_episode import blast_vdb_function_calculators as calculator

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(sys.argv[1])
DEST.mkdir(exist_ok=False)
pins = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
    "gene_annotation_episode/blast_vdb_function_inputs.py",
    "gene_annotation_episode/blast_vdb_function_calculators.py",
    "tests/test_blast_vdb_function_census_relations.py")}
cases = []


def add(name, original, fixture_input, grouping, policy, expectation):
    cases.append((name, deepcopy(fixture_input), model_for(original, grouping, policy), expectation))


whole = fixture("whole_t1")
bridge = fixture("full_census_bridge")
for grouping, policy in MODEL_POLICIES:
    suffix = grouping + "__" + policy
    missing = grouping == "known_source_blocks" and policy == "withhold_weights"
    expected = None if missing else {"A": .5, "B": .5} if grouping == "target_duplicates_only" else {"A": .8, "B": .2}
    add("unresolved_edge__" + suffix, whole, fixture("unresolved_census_edge_baseline")["fixture_input"], grouping, policy,
        {"corrected": expected, "status": "complete" if grouping == "target_duplicates_only" else "partial"})
    add("contradictory_samples__" + suffix, bridge, fixture("census_observed_sample_contradiction")["fixture_input"], grouping, policy,
        {"corrected": None, "status": "partial"})
    _, unknown = original_input("whole_t1")
    unknown["census_records"][0]["entities"][2].update(origin_sample_keys=[], sample_relation_status="unavailable")
    add("unknown_census_sample__" + suffix, whole, unknown, grouping, policy,
        {"corrected": expected, "status": "complete" if grouping == "target_duplicates_only" else "partial"})
    _, conflict = original_input("whole_t1")
    census = conflict["census_records"][0]
    address = deepcopy(census["entities"][0]["address"])
    census["dependency_records"] = [{"dependency_key": "contradictory-dependence", "relation": "same_library",
        "entities": [address, deepcopy(address)], "sources": [],
        "native_record": {"fixture_kind": "synthetic_conflicting_and_unresolved_dependency"}}]
    add("conflicting_dependency__" + suffix, whole, conflict, grouping, policy,
        {"corrected": None, "status": "partial"})
_, original_bridge = original_input("full_census_bridge")
add("original_full_census_bridge", bridge, original_bridge, "known_source_blocks", "qualify_separate",
    {"corrected": {"A": 1/7, "B": 2/7, "C": 4/7}, "status": "complete"})
records = []
for name, fixture_input, model, expectation in cases:
    before_input = deepcopy(fixture_input)
    sheet = inputs.populate_blast_vdb_function_sheet(**fixture_input)
    assert fixture_input == before_input
    components = checked_calculate(sheet, model)
    body = {"fixture_kind": "synthetic_counterexample_or_control", "fixture_input": fixture_input,
        "sheet": sheet, "model": model, "components": components, "source_pins": pins,
        "expectation": expectation, "original_inputs_unchanged": True,
        "live_database_execution": False, "episode_return_verified": False}
    raw = json.dumps(body, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    (DEST / (name + ".json")).write_bytes(raw)
    census = components["census_results"][0]
    records.append({"name": name, "file": name + ".json", "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw), "status": components["status"], "census_link": census_link(sheet),
        "census_status": census["status"], "enumeration_complete": census["enumeration_complete"],
        "correction_available": census["correction_available"], "base_entity_count": census["base_entity_count"],
        "target_unit_count": census["target_unit_count"], "model_group_count": census["model_group_count"],
        "conditional": weights(components), "corrected": weights(components, "representation_adjusted_function_weight"),
        "function_counts": census["function_counts"], "assumptions": components["assumptions"], "expectation": expectation})
old = fixture("census_observed_sample_contradiction")
validation = {}
with saved_only():
    for name, call in (
        ("saved_validator", lambda: inputs.validate_blast_vdb_function_sheet(old["sheet"])),
        ("saved_calculator", lambda: calculator.calculate_blast_vdb_function_components(old["sheet"], model=old["model"]))):
        try:
            call()
        except ValueError as error:
            validation[name] = {"accepted": False, "error": str(error)}
        else:
            validation[name] = {"accepted": True, "error": None}
summary = {"source_pins": pins, "examples": records, "old_available_conflict_sheet": validation,
           "acquisition_population_native_parse_and_base_calculation_forbidden_during_saved_checks": True}
(DEST / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n")
print(json.dumps({"example_count": len(records), "old_available_conflict_sheet": validation,
    "outputs": [{"name": r["name"], "status": r["status"], "census_status": r["census_status"],
                 "conditional": r["conditional"], "corrected": r["corrected"]} for r in records]}, sort_keys=True, indent=2))
