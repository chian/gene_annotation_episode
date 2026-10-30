"""Synthetic interface probes only; no paper, Store, runtime or model access."""
from copy import deepcopy
import json
from pathlib import Path

from test_literature_binding_visual_inputs import fixture, reader
from test_literature_binding_interaction_calculations import example
from gene_annotation_episode.literature_binding_visual_inputs import (
    _Inputs, read_binding_visual_inputs,
)
from gene_annotation_episode.literature_binding_reader import _measurement
from gene_annotation_episode.literature_binding_interaction_calculations import (
    ROLES, populate_binding_interaction,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def main():
    arguments, sources, _ = fixture()
    unknown = deepcopy(arguments)
    unknown["context"]["state"] = {"value": "unknown", "witnesses": []}
    try:
        read_binding_visual_inputs(unknown, read_source=reader(sources))
    except ExperimentalContractError as error:
        state_error = {"code": error.code, "field": error.field}
    else:
        raise AssertionError("Expected current witnessed-context contract")
    assert state_error["code"] == "interpretation_witness_required"
    # Existing frozen mechanics can authenticate/parse the raw cell without
    # pretending to know its molecular state. This is not a new public API.
    mechanics = _Inputs(reader(sources))
    mechanics.image(arguments["images"][0])
    selected = arguments["cells"][0]["expression"]["candidates"][0]
    authenticated = mechanics.witness(selected)
    assert authenticated["error"] is None
    raw = _measurement(selected["quote"], 1.0, "synthetic.expression")
    assert raw == (7.25, "eq", .35)
    inputs = example()
    operand = inputs["operands"][ROLES[0]]
    operand["uncertainty"].update(statistic="confidence_interval", interval=[4, 6], confidence_level=None)
    try:
        populate_binding_interaction(inputs)
    except ExperimentalContractError as error:
        uncertainty_error = {"code": error.code, "field": error.field}
    else:
        raise AssertionError("Expected current complete-CI contract")
    assert uncertainty_error["code"] == "finite_number_required"
    receipt = {
        "synthetic_only": True,
        "paper_or_model_or_runtime_execution": False,
        "public_visual_reader_unknown_state_error": state_error,
        "existing_private_mechanics_preserve_raw_cell_without_state": {
            "value": raw[0], "relation": raw[1], "reported_spread": raw[2],
            "scope": "byte/geometry authentication and literal parsing only"},
        "four_cell_incomplete_confidence_interval_error": uncertainty_error,
        "meaning": "Existing bounded interfaces need an honest partial adapter; no source metadata or uncertainty was fabricated",
    }
    with Path(__file__).with_name("SYNTHETIC_INTERFACE_RECEIPT_001.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps(receipt, separators=(",", ":")))


if __name__ == "__main__":
    main()
