"""Read N's saved source-executed-synthetic sheets through actual C exports."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from gene_annotation_episode.bvbrc_comparative_systems_calculators import calculate_comparative_systems_components
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256

BASE = Path(__file__).resolve().parents[1]
FIXTURE = BASE / "candidate/tests/fixtures/bvbrc_comparative_systems_calculators/saved_examples.json"
examples = json.loads(FIXTURE.read_text())["examples"]
receipt = {"basis": "actual N builder output over retained source-executed synthetic inputs; no live service result",
           "cases": [], "successful_value_checks": 0}


def check(name, requests, expected):
    path = BASE / "evidence_n" / (name + "_sheet_actual.json")
    content = path.read_bytes()
    sheet = json.loads(content)
    before = canonical_sha256(sheet)
    parameters = deepcopy(examples[name + "_components"]["parameters"])
    parameters["requests"] = requests
    result = calculate_comparative_systems_components(sheet, parameters=parameters)
    values = {component["component_id"]: component["value"] for component in result["components"]}
    for component_id, number in expected.items():
        assert values[component_id]["state"] == "available", (component_id, values[component_id])
        assert math.isclose(values[component_id]["value"], number, rel_tol=1e-12, abs_tol=1e-12), (component_id, values[component_id], number)
        receipt["successful_value_checks"] += 1
    assert before == canonical_sha256(sheet) == result["sheet_sha256"]
    output = BASE / "evidence_c" / (name + "_actual_builder_components_002.json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    row = {"name": name, "sheet_file_sha256": hashlib.sha256(content).hexdigest(), "sheet_sha256": before,
           "components_file": str(output.relative_to(BASE)), "expected": expected,
           "actual": {key: value["value"] for key, value in values.items()}}
    receipt["cases"].append(row)
    print(json.dumps(row, sort_keys=True))


pathway_requests = deepcopy(examples["pathway_subsystem_components"]["parameters"]["requests"])
expected = {"retained_pathway_percent": 100 * 3 / 4, "later_pathway_percent": 100 * 4 / 9,
            "retained_subsystem_percent": 100 * 3 / 4, "synthetic_reference_representation": 2 / 4,
            "unambiguous_active_genomes": 0, "unambiguous_likely_genomes": 1}
for index, quantity, expected_number in ((0, "pathway_retained_feature_density", 4 / 4),
                                         (1, "pathway_record_feature_density", 5 / 9),
                                         (2, "subsystem_retained_feature_density", 4 / 4)):
    request = deepcopy(pathway_requests[index])
    request.update(component_id=quantity, quantity=quantity)
    pathway_requests.append(request)
    expected[quantity] = expected_number
later_reference = deepcopy(examples["saved_sheet_recalculation"]["parameters"]["requests"][0])
pathway_requests.append(later_reference)
expected[later_reference["component_id"]] = 3 / 4
for formula in ("pathway_ec_conservation", "pathway_gene_conservation", "subsystem_role_conservation",
                "subsystem_gene_conservation", "subsystem_prop_active"):
    request = deepcopy(pathway_requests[0 if formula.startswith("pathway") else 2])
    request.update(component_id=formula, quantity="reported_formula_check", native_formula=formula)
    request["view_selection"]["view_id"] = formula.split("_", 1)[0] + "_summary"
    pathway_requests.append(request)
    expected[formula] = 0
check("pathway_subsystem", pathway_requests, expected)

family_requests = deepcopy(examples["families_components"]["parameters"]["requests"])
expected = {"family_occupancy": 2 / 3, "family_occurrence_mean": 3 / 2,
            "family_cv": math.sqrt(((100 - 200) ** 2 + (200 - 200) ** 2 + (300 - 200) ** 2) / 3) / 200}
for kind in ("plfam", "pgfam"):
    for quantity in ("observed_family_set_intersection_count", "observed_family_set_union_count", "observed_family_set_jaccard"):
        request = deepcopy(family_requests[0])
        request.update(component_id=kind + ":" + quantity, quantity=quantity, family_kind=kind,
                       comparison_genome_ids=["1.1", "2.1"])
        request["entity"] = {key: None for key in request["entity"]}
        request["entity"].update(kind="pair", comparison_id="source_witness_genome_pair")
        request["view_selection"]["view_id"] = kind
        family_requests.append(request)
        expected[request["component_id"]] = 1
check("families", family_requests, expected)
check("hex_256", examples["hex_256_components"]["parameters"]["requests"],
      {"family_occupancy": 1, "family_occurrence_mean": 257 / 2, "family_cv": 0})
(BASE / "evidence_c/ACTUAL_BUILDER_CONSUMPTION_001.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("Successful independent value checks:", receipt["successful_value_checks"])
