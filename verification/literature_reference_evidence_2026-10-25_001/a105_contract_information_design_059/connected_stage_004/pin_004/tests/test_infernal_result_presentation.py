"""Scope and value preservation for the pure Infernal receiver projection."""

from collections import UserDict
from copy import deepcopy
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from gene_annotation_episode.infernal_result_presentation import infernal_receiver_context


NATIVE_VERSION = "native_infernal_observation_v1"
SAVED_CONTEXT = (
    Path(__file__).parent
    / "fixtures/native_infernal_episode/scientific-decision-6.json"
)


def native_observation(program="cmsearch"):
    return {
        "id": "observation_native",
        "native_infernal": {
            "version": NATIVE_VERSION,
            "program": program,
            "family": "search_hit" if program != "cmalign" else "alignment",
        },
        "measurements": [
            {"name": "bitscore", "value": {"type": "number", "value": 71.4}},
            {"name": "evalue", "value": {"type": "number", "value": 3.6e-22}},
            {"name": "bias_bits", "value": {"type": "number", "value": 0.0}},
        ],
        "dependencies": ["source_native", "input_target", "reference_model"],
    }


def test_omits_complete_native_rows_and_retains_other_rows_in_order():
    retained = [
        {"id": "ordinary", "measurements": [{"name": "zero", "value": 0}]},
        {"id": "unknown", "native_infernal": {"version": "native_infernal_observation_v2"}},
        {"id": "missing_version", "native_infernal": {"program": "cmsearch"}},
        {"id": "wrong_case", "native_infernal": {"version": NATIVE_VERSION.upper()}},
        {"id": "non_object_marker", "native_infernal": NATIVE_VERSION},
        {"id": "null_marker", "native_infernal": None},
        [native_observation()],
        "record-reference",
        None,
        0,
    ]
    original = {
        "working_state": {
            "observations": [
                native_observation(),
                *retained[:2],
                native_observation("cmscan"),
                *retained[2:],
                native_observation("cmalign"),
            ],
            "sources": [{"id": "source_native", "sheet": {"full": [0, None, 3.6e-22]}}],
        },
        "current_credit": 0.875,
        "current_report_basis_refs": ["observation_native"],
    }
    before = deepcopy(original)
    expected = deepcopy(original)
    expected["working_state"]["observations"] = retained

    projected = infernal_receiver_context(original)

    assert projected == expected
    assert list(projected) == list(original)
    assert list(projected["working_state"]) == list(original["working_state"])
    assert original == before


def test_explicit_returns_lookups_outcomes_and_caller_data_are_unchanged():
    native = native_observation()
    requested_row = {
        "observation_ref": "observation_native",
        "source_ref": "source_native",
        "subject_ref": "input_target",
        "reference_refs": ["reference_model"],
        "measurements": [{"name": "bitscore", "value": 71.4}],
        "status": "published",
        "unavailable": [{"name": "requested_missing", "reason": "not_measured"}],
        "population": None,
    }
    original = {
        "working_state": {"observations": [native], "explicit_result": native},
        "child_reports": [
            {"completed": True, "references": ["source_native", "observation_native"]},
            {"completed": True, "rows": [requested_row]},
            {"completed": True, "requested_observations": [native]},
        ],
        "last_local_outcome": {"observations": [native]},
        "lookup_result": {"working_state": {"observations": [native]}},
        "caller_data": {"nested": {"working_state": {"observations": [native]}}},
        "observations": [native],
        "native_infernal": {"version": NATIVE_VERSION},
    }
    before = deepcopy(original)
    expected = deepcopy(original)
    expected["working_state"]["observations"] = []

    projected = infernal_receiver_context(original)

    assert projected == expected
    assert projected["child_reports"][1]["rows"] == [requested_row]
    assert projected["child_reports"][0]["references"] == ["source_native", "observation_native"]
    assert original == before

    projected["child_reports"][1]["rows"][0]["measurements"][0]["value"] = -7.25
    projected["last_local_outcome"]["observations"][0]["dependencies"].append("new_reference")
    assert original == before
    original["child_reports"][0]["references"].append("later_source")
    assert projected["child_reports"][0]["references"] == ["source_native", "observation_native"]


@pytest.mark.parametrize(
    "context",
    [
        {},
        {"working_state": None},
        {"working_state": []},
        {"working_state": "unknown"},
        {"working_state": 0},
        {"working_state": {}},
        {"working_state": {"observations": None}},
        {"working_state": {"observations": "observation_native"}},
        {"working_state": {"observations": {"native": native_observation()}}},
        {"working_state": {"observations": (native_observation(),)}},
    ],
)
def test_missing_or_differently_shaped_state_is_preserved_and_detached(context):
    original = {**deepcopy(context), "caller_data": {"values": [0, None, -1.25]}}
    before = deepcopy(original)

    projected = infernal_receiver_context(original)

    assert projected == original
    assert projected is not original
    projected["caller_data"]["values"].append(7)
    assert original == before


@pytest.mark.parametrize("mapping_type", [dict, UserDict, MappingProxyType])
def test_accepts_mapping_input_and_returns_dict(mapping_type):
    original = mapping_type({"working_state": {"observations": [native_observation()]}})

    projected = infernal_receiver_context(original)

    assert type(projected) is dict
    assert projected == {"working_state": {"observations": []}}
    assert original["working_state"]["observations"] == [native_observation()]


@pytest.mark.parametrize("context", [None, [], (), 0, False, "context"])
def test_rejects_non_mapping_context(context):
    with pytest.raises(TypeError, match="context must be a mapping"):
        infernal_receiver_context(context)


def test_saved_actual_context_preserves_only_the_requested_measurements():
    saved = json.loads(SAVED_CONTEXT.read_text())
    original = saved["context"]
    if isinstance(original, str):
        original = json.loads(original)
    before = deepcopy(original)
    observations = original["working_state"]["observations"]
    assert len(observations) == 1
    assert observations[0]["native_infernal"]["version"] == NATIVE_VERSION
    assert len(observations[0]["measurements"]) == 10
    requested_row = original["child_reports"][1]["rows"][0]
    assert requested_row["measurements"] == [{"name": "bitscore", "value": 71.4}]
    assert requested_row["observation_ref"] == observations[0]["id"]

    expected = deepcopy(original)
    expected["working_state"]["observations"] = []
    projected = infernal_receiver_context(original)
    repeated = infernal_receiver_context(projected)

    assert projected == expected
    assert repeated == projected
    assert repeated is not projected
    assert repeated["working_state"] is not projected["working_state"]
    assert repeated["child_reports"] is not projected["child_reports"]
    assert projected["child_reports"] == original["child_reports"]
    assert original == before
    repeated["child_reports"][1]["rows"][0]["measurements"][0]["value"] = 0.0
    assert projected == expected
    assert original == before
