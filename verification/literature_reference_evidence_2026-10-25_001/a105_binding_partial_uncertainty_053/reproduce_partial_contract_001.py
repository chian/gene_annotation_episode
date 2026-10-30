"""Synthetic-only baseline partial-uncertainty probes; no source/runtime reads."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from test_literature_binding_interaction_calculations import example, observation_model
from gene_annotation_episode.literature_binding_interaction_calculations import (
    ROLES, populate_binding_interaction,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def main():
    baseline = json.loads((OUT / "BASELINE_001.json").read_bytes())
    for name, row in baseline["source_files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == row["sha256"]
    complete = example()
    complete_sheet = populate_binding_interaction(complete)
    assert complete_sheet["cells"]["interaction_ratio"]["value"] == 4
    assert complete_sheet["cells"]["signed_profile_log_ratio"]["value"] is None
    complete_known_model = populate_binding_interaction(complete, observation_model(complete))
    cases = []
    configurations = [
        ("unresolved_whole_metadata", None),
        ("sd_magnitude_unavailable", {"statistic": "sd"}),
        ("sem_magnitude_unavailable", {"statistic": "sem"}),
        ("unspecified_magnitude_unavailable", {"statistic": "unspecified"}),
        ("ci_level_unknown", {"statistic": "confidence_interval", "interval": [4, 6]}),
        ("ci_endpoints_unknown", {"statistic": "confidence_interval", "confidence_level": .95}),
        ("ci_upper_unknown", {"statistic": "confidence_interval", "interval": [4, None], "confidence_level": .95}),
        ("ci_lower_unknown", {"statistic": "confidence_interval", "interval": [None, 6], "confidence_level": .95}),
        ("ci_both_endpoints_unknown", {"statistic": "confidence_interval", "interval": [None, None]}),
    ]
    for name, update in configurations:
        inputs = deepcopy(complete)
        operand = inputs["operands"][ROLES[0]]
        if update is None:
            operand["uncertainty"] = None
        else:
            operand["uncertainty"].update(update)
        try:
            populate_binding_interaction(inputs)
        except ExperimentalContractError as error:
            cases.append({"case": name, "status": "rejected", "code": error.code, "field": error.field})
        else:
            raise AssertionError("Baseline unexpectedly accepted " + name)
    result = {"synthetic_only": True, "baseline_sha256": baseline["source_files"],
        "complete_native_interaction": complete_sheet["cells"]["interaction_ratio"],
        "complete_known_model_cells": complete_known_model["cells"],
        "partial_states_rejected": cases,
        "meaning": "Pure contract gaps only, not source truth, Store authentication or configured-model evidence",
        "production_or_test_edits": False}
    with (OUT / "SYNTHETIC_BASELINE_RECEIPT_001.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"synthetic_only": True, "complete_interaction": 4,
                      "partial_contract_rejections": len(cases), "production_edits": False}))


if __name__ == "__main__":
    main()
