"""Retain full synthetic input/model/output examples, inside a bounded job."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.blast_vdb_function_calculators import calculate_blast_vdb_function_components
from test_blast_vdb_function_calculators import (
    ROOT, FROZEN, model, whole_case, translated_case, case, populate, with_census,
    census_for, bridge_case, conflicting_feature_case, feature, function, inputs, collect,
)


DESTINATION = Path(sys.argv[1])
DESTINATION.mkdir(exist_ok=False)
PINS = {
    "gene_annotation_episode/blast_vdb_function_inputs.py": "78e0491b2d52cfed4bc013b04f2f3487fb86a65691dd3b10a4c97541f6d71b84",
    "verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001/whole_sequence.json": "cc10075f976cd66858ad97fe3418cb0964b06ef718eaf073f2dc11cf49fdf9d8",
    "verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001/translated_features.json": "d2ab3559e9c9a5b410811703841172c749a07953f72894e7f7976ed7ad73b04f",
    "verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001/translated_siblings.json": "f001b0f68fa27647b736aae8f79c2cf55358facb263637be80d0db4ca6eb46ec",
}
for relative, expected in PINS.items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


manifest = []
def save(name, sheet, selected_model):
    before = canonical(sheet)
    components = calculate_blast_vdb_function_components(sheet, model=selected_model)
    assert canonical(sheet) == before
    document = dict(schema="vdb_function_calculator_verification_example_v1",
        fixture_kind="synthetic_native_format_and_explicit_supplied_metadata",
        live_database_execution=False, episode_return_verified=False,
        sheet_canonical_sha256=hashlib.sha256(before).hexdigest(),
        sheet=sheet, model=selected_model, components=components)
    path = DESTINATION / (name + ".json")
    payload = json.dumps(document, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    path.write_bytes(payload)
    projection = [dict(scope=s["assignment_scope"], namespace=s["namespace"], status=s["status"],
        weights={r["function"]["value"]: r["conditional_function_weight"] for r in s["functions"]},
        corrected={r["function"]["value"]: r["representation_adjusted_function_weight"] for r in s["functions"]})
        for s in components["strata"]]
    manifest.append(dict(name=name, file=path.name, sha256=hashlib.sha256(payload).hexdigest(), size_bytes=len(payload),
        sheet_canonical_sha256=document["sheet_canonical_sha256"], status=components["status"], projection=projection))


whole = json.loads((FROZEN / "whole_sequence.json").read_text())
census_key = whole["census_records"][0]["census_key"]
save("whole_t1", whole, model(census=census_key))
save("whole_t2", whole, model(temperature=2, census=census_key))
assert manifest[0]["sheet_canonical_sha256"] == manifest[1]["sheet_canonical_sha256"]

for name in ("translated_features", "translated_siblings"):
    sheet = json.loads((FROZEN / (name + ".json")).read_text())
    save(name, sheet, model(temperature=2))

for destination in ("missing_feature", "other_bound_feature"):
    save("assignment_conflict_" + destination, conflicting_feature_case(destination), model())

values, assignments = case(samples=("S1", "S1", "S2"))
sheet = populate(values, assignments)
save("source_cap_baseline", sheet, model())
save("source_cap_selected", sheet, model(grouping="known_source_blocks"))

sheet = bridge_case()
save("full_census_bridge", sheet, model(grouping="known_source_blocks", census=sheet["census_records"][0]["census_key"]))

values, assignments = case(scores=(20, 18), labels=("A", "B"), samples=("S", "S"))
save("own_function_score_split", populate(values, assignments), model(grouping="known_source_blocks"))
values, assignments = case(labels=("A", "B", None))
save("unknown_target_mass", populate(values, assignments), model())

priors = [dict(assignment_scope="whole_sequence", namespace="fixture_function", function=function(k), weight=w)
          for k, w in (("A", 1), ("B", 0))]
save("explicit_zero_prior", whole, model(priors=priors, census=census_key))
priors = deepcopy(priors)
priors[0]["weight"], priors[1]["weight"] = 1e-300, 1e300
save("positive_prior_underflow", whole, model(priors=priors, census=census_key))

values, assignments = case(scores=(2000, 0), labels=("A", "B"))
save("log2_minus_2000", populate(values, assignments), model())

values, assignments = case(scores=(1, 0), labels=("A", "B"))
feature(values, interval=[0, 8], identifier="valid-feature", kind="misc_feature", function=function("feature-A"))
sheet = with_census(values, assignments)
save("finite_arithmetic_failure_valid_other_scope", sheet, model(temperature=1e-320, census=sheet["census_records"][0]["census_key"]))

values, assignments = whole_case()
census = census_for(populate(values, assignments)); census["datasets"][0]["snapshot"]["release"] = "different"
save("incompatible_census", with_census(values, assignments, census), model(census=census["census_key"]))

values, assignments = whole_case(); census = census_for(populate(values, assignments))
census["entities"][-1]["origin_sample_keys"] = []
census["entities"][-1]["sample_relation_status"] = "unavailable"
sheet = with_census(values, assignments, census)
save("census_unknown_dependency_separate", sheet, model(grouping="known_source_blocks", census=census["census_key"]))
save("census_unknown_dependency_withheld", sheet,
     model(grouping="known_source_blocks", unknown="withhold_weights", census=census["census_key"]))

values, assignments = whole_case(); census = census_for(populate(values, assignments)); census["annotation_bindings"] = []
zero = inputs(collect(hits=[])["searches"][0]); zero["dataset_records"] = deepcopy(values["dataset_records"])
for dataset in zero["dataset_records"]:
    dataset["metadata_keys"] = []
save("qualified_zero_hits_nonzero_census", populate(zero, censuses=[census]), model(census=census["census_key"]))
empty = populate(inputs(collect(raw=b"", format_name="tabular6", fields=["qseqid", "sseqid"])["searches"][0]))
save("empty_table6_unavailable", empty, model())

paths = [ROOT / "gene_annotation_episode/blast_vdb_function_calculators.py",
         ROOT / "tests/test_blast_vdb_function_calculators.py",
         Path(__file__), *[ROOT / p for p in PINS]]
source_identities = [dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size_bytes=p.stat().st_size) for p in paths]
summary = dict(schema="vdb_function_calculator_verification_manifest_v1", cases=manifest, source_identities=source_identities,
    scope="Pure saved-sheet arithmetic; supplied synthetic reports and census data; no live VDB or episode delivery")
(DESTINATION / "manifest.json").write_text(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n")
print(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False))
