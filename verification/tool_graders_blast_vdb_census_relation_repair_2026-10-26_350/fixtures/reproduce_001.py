"""Independent narrow census-boundary reproductions; no existing test rerun."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

from gene_annotation_episode import blast_vdb_function_calculators as calc
from gene_annotation_episode import blast_vdb_function_inputs as inp
from gene_annotation_episode import blast_vdb_inputs as native
from gene_annotation_episode import blast_vdb_calculators as base

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "verification/tool_graders_blast_vdb_function_calculators_2026-10-26_344/example_run_004/examples"
DEST = Path(sys.argv[1])
DEST.mkdir(exist_ok=False)
PINS = {
    "gene_annotation_episode/blast_vdb_function_inputs.py": "78e0491b2d52cfed4bc013b04f2f3487fb86a65691dd3b10a4c97541f6d71b84",
    "gene_annotation_episode/blast_vdb_function_calculators.py": "31d88b0d724ced992c6ca69aab7161632ada3e24d91f2f264387b03d31ef749a",
}


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(v):
    return hashlib.sha256(v).hexdigest()


def write(name, value):
    data = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    (DEST / name).write_bytes(data)
    return {"file": name, "sha256": digest(data), "size_bytes": len(data)}


for path, expected in PINS.items():
    assert digest((ROOT / path).read_bytes()) == expected

# Read and inspect each entire retained JSON, not just the prose or manifest
# projection. This is artifact inspection, not a repeat of the180 checks.
manifest = json.loads((EXAMPLES / "manifest.json").read_bytes())
inspection = []
loaded = {}
for entry in manifest["cases"]:
    raw = (EXAMPLES / entry["file"]).read_bytes()
    data = json.loads(raw)
    assert len(raw) == entry["size_bytes"] and digest(raw) == entry["sha256"]
    assert digest(canonical(data["sheet"])) == entry["sheet_canonical_sha256"] == data["sheet_canonical_sha256"]
    assert data["model"] == data["components"]["model"]
    assert data["components"]["search_key"] == data["sheet"]["base_sheet"]["search"]["search_key"]
    assert data["live_database_execution"] is False and data["episode_return_verified"] is False
    assert data["sheet"]["base_components"]["population_components"]["function_weight_model"] == {
        "status": "unavailable", "components": None, "reason": "vdb_function_weight_model_not_defined"}
    original = {o["observation_key"]: o for o in data["sheet"]["observations"]}
    numerical = []
    for stratum in data["components"]["strata"]:
        for group in stratum["groups"]:
            for contribution in group["function_contributions"]:
                observations = [original[k] for k in contribution["observation_keys"]]
                available = [o for o in observations if o["qualification"] == "available"]
                assert all(o["function"] == contribution["function"] for o in observations)
                assert max(o["native_bit_score"]["value"] for o in available) == contribution["best_bit_score"]["value"]
                assert set(contribution["winning_observation_keys"]) == {
                    o["observation_key"] for o in available
                    if o["native_bit_score"]["value"] == contribution["best_bit_score"]["value"]}
        numerical.append({k: deepcopy(stratum[k]) for k in (
            "assignment_scope", "namespace", "status", "counts", "functions",
            "unknown_reference_kernel_mass", "assigned_reference_kernel_mass",
            "unknown_reference_kernel_fraction", "conditional_weight_denominator",
            "representation_adjusted_weight_denominator")})
    inspection.append({"file": entry["file"], "sha256": digest(raw), "size_bytes": len(raw),
        "sheet_sha256": digest(canonical(data["sheet"])), "model": data["model"],
        "status": data["components"]["status"], "strata": numerical})
    loaded[entry["name"]] = data
for source in manifest["source_identities"]:
    raw = (ROOT / source["path"]).read_bytes()
    assert digest(raw) == source["sha256"] and len(raw) == source["size_bytes"]
artifact_record = write("complete_example_inspection.json", inspection)

cases = []


def add_case(name, original, census, grouping, policy, expectation):
    original_sheet = original["sheet"]
    fixture_input = {
        "vdb_sheet": deepcopy(original_sheet["base_sheet"]),
        "supplied_assignments": deepcopy(original_sheet["assignment_records"]),
        "dependency_records": deepcopy(original_sheet["dependency_records"]),
        "census_records": [deepcopy(census)],
    }
    sheet = inp.populate_blast_vdb_function_sheet(**fixture_input)
    model = deepcopy(original["model"])
    model.update(grouping_model=grouping, unknown_source_dependency=policy)
    cases.append((name, fixture_input, sheet, model, expectation))


whole = loaded["whole_t1"]
census = deepcopy(whole["sheet"]["census_records"][0])
# Both dependency endpoints exist in the complete enumeration. Only source
# support is absent: this is an unresolved optional edge, not a missing member,
# changed sequence, changed population, changed annotation or truncated census.
census["dependency_records"] = [{
    "dependency_key": "review348-source-not-supplied",
    "relation": "same_library",
    "entities": [deepcopy(census["entities"][0]["address"]), deepcopy(census["entities"][2]["address"])],
    "sources": [],
    "native_record": {"fixture_kind": "synthetic_relation_with_missing_provenance", "library": "L"},
}]
for name, grouping, policy, expected in (
    ("unresolved_census_edge_baseline", "target_duplicates_only", "qualify_separate", {"A": 0.5, "B": 0.5}),
    ("unresolved_census_edge_separate", "known_source_blocks", "qualify_separate", {"A": 0.8, "B": 0.2}),
    ("unresolved_census_edge_withhold", "known_source_blocks", "withhold_weights", None),
):
    add_case(name, whole, census, grouping, policy,
             {"representation_adjusted_function_weight": expected,
              "basis": "338 sections1/6 and addendum007; unresolved edge is unused or explicitly qualified separately"})

bridge = loaded["full_census_bridge"]
conflict = deepcopy(bridge["sheet"]["census_records"][0])
c = next(e for e in conflict["entities"] if any(f["value"] == "C" for f in e["functions"]))
assert c["origin_sample_keys"] == ["S3"]
c["origin_sample_keys"] = ["S1"]
add_case("census_observed_sample_contradiction", bridge, conflict, "known_source_blocks", "qualify_separate",
         {"correction_available": False,
          "basis": "Same exact observed entity retains source-qualifiedS3; census relabels it S1 without a changed source statement"})


def forbidden(*a, **k):
    raise AssertionError("forbidden parser/populator/base recalculation/acquisition during saved calculation")


records = []
for name, fixture_input, sheet, model, expectation in cases:
    before = canonical(sheet)
    model_before = canonical(model)
    # Actual public shared validator remains enabled. Calculating the saved
    # fixture may not return to its population or native analysis paths.
    with ExitStack() as stack:
        for module, port in (
            (inp, "populate_blast_vdb_function_sheet"),
            (inp, "extract_blast_vdb_feature_function_assignments"),
            (base, "calculate_blast_vdb_components"),
            *[(native, port) for port in ("populate_blast_vdb_sheet", "parse_ncbi_sra_runinfo",
                "parse_blast_vdb_member_sequences", "parse_ncbi_gbseq_vdb_metadata", "bind_blast_vdb_metadata",
                "_recheck_metadata", "_reparse")],
        ):
            stack.enter_context(patch.object(module, port, forbidden))
        components = calc.calculate_blast_vdb_function_components(sheet, model=model)
    assert canonical(sheet) == before and canonical(model) == model_before
    complete = {"fixture_kind": "synthetic_counterexample", "fixture_input": fixture_input,
        "sheet": sheet, "model": model, "components": components, "expectation": expectation,
        "originals_unchanged": True, "source_pins": PINS}
    artifact = write(name + ".json", complete)
    stratum = components["strata"][0]
    row = {"name": name, **artifact, "status": components["status"],
        "census_link": next(r for r in sheet["link_results"] if r["record_kind"] == "census"),
        "conditional": {r["function"]["value"]: r["conditional_function_weight"] for r in stratum["functions"]},
        "corrected": {r["function"]["value"]: r["representation_adjusted_function_weight"] for r in stratum["functions"]},
        "correction_available": components["census_results"][0]["correction_available"],
        "enumeration_complete": components["census_results"][0]["enumeration_complete"],
        "expectation": expectation}
    records.append(row)
for path, expected in PINS.items():
    assert digest((ROOT / path).read_bytes()) == expected
report = {"source_pins": PINS, "retained_example_count": len(inspection),
    "complete_example_inspection": artifact_record, "counterexamples": records,
    "existing_tests_rerun": False, "new_scientific_execution": False}
write("review_results.json", report)
print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
