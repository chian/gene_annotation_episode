"""Synthetic detached-contract repro; original Store authentication is unexercised."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

from test_literature_kinetic_inputs import fixture
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast

OUT = Path(__file__).resolve().parent
SNAPSHOT = OUT.parent / "a105_kinetic_integration_047/snapshot_005/gene_annotation_episode/literature_kinetic_validation.py"


def main():
    spec = importlib.util.spec_from_file_location(
        "gene_annotation_episode._parent_detached_validation_005", SNAPSHOT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, selection = fixture()
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    calculation = populate_kinetic_contrast(extraction["calculation_inputs"])
    mutations = [("source_number_relation", "relation", "gt"),
                 ("source_number_approximation", "approximate", True),
                 ("populated_cell_unavailable_reason", None, None)]
    results = []
    for name, field, value in mutations:
        changed_extraction, changed_calculation = deepcopy(extraction), deepcopy(calculation)
        if field:
            changed_extraction["operands"]["numerator"]["number"][field] = value
        else:
            changed_calculation["cells"]["numerator_parameter"]["unavailable_reason"] = "source_measurement_unreported"
        module.validate_saved_kinetic(selection, changed_extraction, changed_calculation)
        results.append({"mutation": name, "snapshot_005": "inconsistent_detached_state_accepted"})
    receipt = {"synthetic_only": True, "original_store_authentication_exercised": False,
               "snapshot_validator_sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
               "results": results,
               "meaning": "Detached semantic gaps only; no claim of bypassing immutable saved-operation authentication"}
    with (OUT / "DETACHED_BASELINE_005.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"synthetic_detached_gaps_reproduced": len(results), "store_bypass_claim": False}))


if __name__ == "__main__":
    main()
