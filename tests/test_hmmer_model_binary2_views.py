"""Engineered HMMER2 EVD saved-view and existing typed-boundary controls.

Packed bytes and fabricated grammar records here are engineering inputs only.
They establish neither a native producer nor Store/episode custody. Authentic
upstream fixture and current original-producer proof are separately selected.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode import hmmer_preparation_result_views as views
from gene_annotation_episode import native_hmmer_preparation_worker as worker
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.domain import ContractError
from test_hmmer_artifact_data import payload
from test_hmmer_model_binary2 import packed
from test_hmmer_model_legacy import synthetic


PATHS = ["calibration.EVD.mu", "calibration.EVD.lambda"]


def prepared(raw, *, format):
    item = payload(raw, "models", oid="engineering/input/models/0")
    operation = {"program": "hmmconvert", "mode": "binary" if format == "hmmer_binary" else "ascii",
        "engine_version": "3.4", "settings": {}}
    grading = worker.grade_hmmer_preparation(operation=operation, inputs={"models": [item]}, outputs={},
        formats={item["occurrence"]["occurrence_id"]: format}, metadata={}, parameters={})
    occurrences = [{**item["occurrence"], "format": format, "relative_path": "input/models/0"}]
    return grading, occurrences


def selector():
    return {"version": "native_hmmer_preparation_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"collection": "input_records", "rows": {"offset": 0, "limit": 1},
            "quantities": PATHS[:], "checks": []}, "artifacts": []}


def project(grading, occurrences):
    return views.project_preparation_result(grading, selector=selector(),
        source_ref="engineering:original-result-source", occurrences=occurrences)


def replace_model(grading, mutate):
    row = deepcopy(grading["sheet"]["input_records"][0])
    mutate(row)
    grading["sheet"]["input_records"][0] = row
    grading["sheet"]["model_extractions"][0]["records"][0] = deepcopy(row)


@pytest.mark.parametrize("kind", ["ascii", "little", "big"])
def test_original_evd_pair_is_selectable_through_existing_profile_and_typed_fact_schema(kind, monkeypatch):
    raw = synthetic(extra_headers="EVD -2.5 0.7\n") if kind == "ascii" else packed(order=kind)[0]
    grading, occurrences = prepared(raw, format="hmmer2_ascii" if kind == "ascii" else "hmmer_binary")
    before = deepcopy(grading)
    expected = grading["sheet"]["input_records"][0]["representation"]["legacy"]["evd"][0]["values"]
    def forbidden(*args, **kwargs):
        raise AssertionError("saved EVD projection attempted IO, parsing or calculation")
    with monkeypatch.context() as patch:
        patch.setattr("builtins.open", forbidden)
        patch.setattr(worker, "grade_hmmer_preparation", forbidden)
        patch.setattr("gene_annotation_episode.hmmer_model_data.extract_hmmer_models", forbidden)
        patch.setattr("gene_annotation_episode.hmmer_model_calculations.calculate_hmmer_model_components", forbidden)
        result = project(grading, occurrences)
    assert grading == before
    row, = result["rows"]
    assert row["quantities"] == [{"path": path, "value": value, "state": "present", "unit": unit}
        for path, value, unit in zip(PATHS, expected, ["bit", "inverse_bit"])]
    assert row["artifact_ref"] == occurrences[0]["artifact_ref"]
    assert result["artifacts"] == [{"source_ref": row["source_ref"], **{key: occurrences[0][key]
        for key in views.ARTIFACT_SCHEMA["properties"] if key != "source_ref"}}]
    received = {(row["source_ref"], "execution_result"), (row["artifact_ref"], "artifact"),
        (row["record_key"], "native_hmmer_preparation_row"), (row["name"], "native_hmmer_preparation_name")}
    if row["accession"] is not None:
        received.add((row["accession"], "native_hmmer_preparation_accession"))
    fact = views.preparation_fact_sources()["execution_hmmer_preparation_rows"]["report_schema"]
    schema = {"type": "object", "additionalProperties": False,
        "properties": {"rows": fact}, "required": ["rows"]}
    validate_form({"rows": result["rows"]}, schema, lambda ref, namespace: (ref, namespace) in received)
    with pytest.raises(ValueError):
        validate_form({"rows": result["rows"]}, schema,
            lambda ref, namespace: (ref, namespace) in received and ref != row["source_ref"])


def test_old_saved_legacy_pair_does_not_require_a_newly_recorded_common_calibration():
    grading, occurrences = prepared(synthetic(extra_headers="EVD -2.5 0.7\n"), format="hmmer2_ascii")
    replace_model(grading, lambda row: row.update(calibration=[]))
    assert [q["value"] for q in project(grading, occurrences)["rows"][0]["quantities"]] == [-2.5, 0.7]


@pytest.mark.parametrize("kind", ["ascii", "binary"])
def test_absent_native_calibration_is_missing_not_zero_or_another_hmmer_mode(kind):
    raw = synthetic() if kind == "ascii" else packed(evd=False)[0]
    grading, occurrences = prepared(raw, format="hmmer2_ascii" if kind == "ascii" else "hmmer_binary")
    assert [(q["value"], q["state"]) for q in project(grading, occurrences)["rows"][0]["quantities"]] == [(None, "missing")] * 2


@pytest.mark.parametrize("headers,state", [("EVD -2.5 0\n", "invalid"), ("EVD nan 1\n", "invalid"),
    ("EVD -2.5\n", "invalid"), ("EVD -2.5 0.7\nEVD -8 0.2\n", "incompatible")])
def test_invalid_or_ambiguous_native_pairs_remain_qualified_without_first_or_last_selection(headers, state):
    grading, occurrences = prepared(synthetic(extra_headers=headers), format="hmmer2_ascii")
    assert [(q["value"], q["state"]) for q in project(grading, occurrences)["rows"][0]["quantities"]] == [(None, state)] * 2


@pytest.mark.parametrize("change", ["tokens", "values", "line", "common", "native-bytes", "native-offset"])
def test_saved_evd_scalar_requires_exact_original_tokens_or_native_source_slots(change):
    binary = change.startswith("native-")
    raw = packed()[0] if binary else synthetic(extra_headers="EVD -2.5 0.7\n")
    grading, occurrences = prepared(raw, format="hmmer_binary" if binary else "hmmer2_ascii")
    def mutate(row):
        entry = row["representation"]["legacy"]["evd"][0]
        if change == "tokens": entry["tokens"][0] = "-4"
        elif change == "values": entry["values"][0] = -4
        elif change == "line": entry["line"] += 1
        elif change == "common": row["calibration"][0]["parameters"][0]["value"] = -4
        else:
            field = next(value for value in row["representation"]["native_fields"] if value["field"] == "EVD.mu")
            if change == "native-bytes": field["raw_hex"] = "00000000"
            else: field["byte_start"] += 4; field["byte_end"] += 4
    replace_model(grading, mutate)
    with pytest.raises(ContractError, match="evd_(source_invalid|projection_conflict)"):
        project(grading, occurrences)


def test_unavailable_binary_header_does_not_promote_retained_evd_to_a_complete_model():
    raw, offsets = packed()
    grading, occurrences = prepared(raw[:offsets["begin[1]"]], format="hmmer_binary")
    result = project(grading, occurrences)
    assert [(q["value"], q["state"]) for q in result["rows"][0]["quantities"]] == [(None, "incomplete")] * 2


def test_new_paths_are_finite_and_do_not_allow_arbitrary_calibration_array_selection():
    catalog = views.preparation_projection_catalog("hmmconvert", "ascii")["input_records"]["quantities"]
    assert [catalog[path]["unit"] for path in PATHS] == ["bit", "inverse_bit"]
    request = selector()
    request["projection"]["quantities"] = ["calibration.0.parameters.0.value"]
    with pytest.raises(ContractError, match="field_not_in_operation_collection"):
        views.validate_preparation_result_selector(request, program="hmmconvert", mode="ascii")
