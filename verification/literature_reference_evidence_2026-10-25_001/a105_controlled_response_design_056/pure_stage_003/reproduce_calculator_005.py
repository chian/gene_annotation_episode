"""Run invented parsed-input examples through the actual pure calculator.

No document/image reading, source interpretation, model service, selected
operation, episode observation or annotation credit occurs. Graph-origin flags
are invented applicability inputs, not measured images. Output is new only.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.literature_controlled_response_calculations import (
    COMPONENTS, PRIMITIVE_ORDER, populate_controlled_response,
)


def main():
    base = json.loads((HERE / "INPUT_CONTRACT_EXAMPLE_003.json").read_text())
    cases = {"native_root_example_model_none": base}

    def fresh(name):
        value = deepcopy(base)
        cases[name] = value
        return value

    known = fresh("stipulated_known_normal_model")
    known["model_kind"] = "known_joint_normal_source_means"
    negative = fresh("signed_negative_effect")
    negative["arms"][PRIMITIVE_ORDER[0]]["value"] = 1
    negative["model_kind"] = "known_joint_normal_source_means"
    estimated = fresh("estimated_covariance_not_known_likelihood")
    estimated.update(variance_status="estimated", model_kind="known_joint_normal_source_means")
    missing_cov = fresh("covariance_unavailable_not_independent")
    missing_cov.update(covariance=None, variance_status="unknown")
    norm = fresh("known_different_biological_denominator")
    norm["arms"][PRIMITIVE_ORDER[1]]["normalization_id"] = "synthetic_lipid_mass"
    partial = fresh("unknown_second_pair_normalization")
    partial["arms"][PRIMITIVE_ORDER[3]]["normalization_id"] = None
    partial["arms"][PRIMITIVE_ORDER[3]]["meaning_statuses"]["normalization"] = "unknown"
    dimensions = fresh("root_review_different_pair_dimensions")
    dimensions.update(covariance=None, variance_status="unknown")
    for i, unit in enumerate(("umol/min", "umol/min", "uM/min", "uM/min")):
        dimensions["arms"][PRIMITIVE_ORDER[i]]["unit"] = unit
    shared = fresh("actual_shared_control_joint_cancellation")
    left = shared["arms"][PRIMITIVE_ORDER[1]]
    right = shared["arms"][PRIMITIVE_ORDER[3]]
    right.update(value=2, condition_id=left["condition_id"], physical_observation_id=left["physical_observation_id"])
    shared["relationships"].update(condition0_control_application="shared_reference_assumption",
        control_reference_reuse="same_reference_with_stated_invariance")
    shared["covariance"]["physical_observation_ids"][3] = left["physical_observation_id"]
    shared["covariance"]["matrix"] = [[1, 0, 0, 0], [0, .25, 0, .25], [0, 0, .36, 0], [0, .25, 0, .25]]
    censored = deepcopy(shared)
    cases["shared_censored_control_no_threshold_likelihood"] = censored
    censored["model_kind"] = "known_joint_normal_source_means"
    for i in (1, 3):
        censored["arms"][PRIMITIVE_ORDER[i]].update(status="bound", value=None, threshold=2, relation="ge")
    no_identity = deepcopy(censored)
    cases["unknown_identity_equal_limits_do_not_cancel"] = no_identity
    no_identity.update(covariance=None, variance_status="unknown")
    no_identity["relationships"]["control_reference_reuse"] = "unknown"
    for i in (1, 3):
        no_identity["arms"][PRIMITIVE_ORDER[i]]["physical_observation_id"] = None
        no_identity["arms"][PRIMITIVE_ORDER[i]]["meaning_statuses"]["physical_observation"] = "unknown"
    graph = fresh("invented_graph_nominal_and_reading_interval")
    graph["model_kind"] = "known_joint_normal_source_means"
    graph["arms"][PRIMITIVE_ORDER[0]].update(origin="graph_derived", relation="interval",
        digitization_interval={"lower": 11, "upper": 13})
    range_partial = fresh("one_graph_endpoint_out_of_numeric_range")
    range_partial.update(covariance=None, variance_status="unknown")
    range_partial["arms"][PRIMITIVE_ORDER[0]].update(origin="graph_derived", unit="mmol/min",
        value=1e305, relation="interval", digitization_interval={"lower": .001, "upper": 1e308})
    underflow = fresh("variance_range_does_not_erase_uncertainty_or_profile")
    underflow["model_kind"] = "known_joint_normal_source_means"
    for name, value in zip(PRIMITIVE_ORDER, (2e-160, 0, 1e-160, 0)):
        underflow["arms"][name]["value"] = value
    underflow["covariance"]["matrix"] = [[1e-320 if i == j else 0 for j in range(4)] for i in range(4)]

    records = {name: populate_controlled_response(inputs) for name, inputs in cases.items()}
    assert records["native_root_example_model_none"]["cells"][COMPONENTS[6]]["value"] == .006
    assert records["root_review_different_pair_dimensions"]["cells"][COMPONENTS[6]]["value"] is None
    assert records["actual_shared_control_joint_cancellation"]["cells"][COMPONENTS[7]]["value"] == .00000136
    output = {"scope": "Wholly invented pure-input examples; no scientific measurements or source/model run",
              "runtime_observations": 0, "annotation_credit_computed": False, "cases": records}
    with (HERE / "NUMERICAL_FIXTURES_005.json").open("x") as stream:
        json.dump(output, stream, indent=2, allow_nan=False); stream.write("\n")
    lines = ["# Synthetic pure-calculator fixture table", "",
        "Every operand/model here is invented. Graph flags are parsed-input scenarios; no image was measured.",
        "All displayed values are actual calls to the new pure calculator. Null is unavailable, never zero.", "",
        "The root example's native e=6 nmol/min/mg and V=1.7 (nmol/min/mg)^2 become .006 and .0000017 in canonical units.", "",
        "| Synthetic case | d1 | d0 | e | V | sqrt(V) | S | B | e reasons |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    def display(value):
        return "null" if value is None else format(value, ".12g")
    for name, result in records.items():
        values = [result["cells"][COMPONENTS[i]]["value"] for i in (4, 5, 6, 7, 8, 10, 11)]
        reason = ", ".join(result["cells"][COMPONENTS[6]]["unavailable_reason"] or ())
        lines.append("| " + name + " | " + " | ".join(display(value) for value in values) + " | " + reason + " |")
    lines += ["", "Each row's exact actual input, units, bound states, finite reasons and full cells are in NUMERICAL_FIXTURES_005.json.",
        "For the range-partial scenario inspect protein_condition1_response: value=1e308, lower=1, upper=null, status=partial, upper bound_state=numeric_range_failure.",
        "No selected operation, source reader, typed runtime handoff, W05 aggregation or annotation credit is implemented by this table.", ""]
    with (HERE / "NUMERICAL_FIXTURES_005.md").open("x") as stream:
        stream.write("\n".join(lines))
    print(json.dumps({"status": "passed", "synthetic_cases": len(records), "runtime_observations": 0}))


if __name__ == "__main__":
    main()
