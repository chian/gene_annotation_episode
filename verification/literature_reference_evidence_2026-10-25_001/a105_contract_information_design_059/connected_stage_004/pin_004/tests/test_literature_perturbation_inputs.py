"""Synthetic custody/data-boundary tests; no experimental source is acquired."""
import hashlib
import json
import math

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_perturbation_inputs import (
    DATA_VERSION, LITERAL_FIELDS, PRIMITIVE_ORDER, VERSION,
    perturbation_population_schema, read_perturbation_inputs,
)


SOURCE = "source_" + "1" * 24
DATA = "source_" + "2" * 24
OTHER = "source_" + "3" * 24
ARTIFACT = "artifact_" + "4" * 24
DATA_ARTIFACT = "artifact_" + "5" * 24
TEXT = "µ source: molecule M; recipient C; matched endpoint; selective perturbation and restoration."


def witness(quote="matched endpoint", *, source=SOURCE, representation="original"):
    start = TEXT.encode().index(quote.encode())
    return {"source_ref": source, "representation": representation,
            "start": start, "end": start + len(quote.encode()), "quote": quote}


def fixture(*, populated=False):
    args = {"source_ref": SOURCE, "data_source_ref": DATA if populated else None,
            "source_kind": "synthetic_fixture", "literals": dict.fromkeys(LITERAL_FIELDS),
            "design": "unknown", "measurement_status": "unknown",
            "same_endpoint_scope": "unknown", "amount_role": "unknown", "orientation": None,
            "interpretation_witnesses": []}
    args["literals"]["molecule"] = witness("molecule M")
    payloads = {SOURCE: {"artifact_ref": ARTIFACT, "content": TEXT.encode()}}
    data = {"version": DATA_VERSION, "endpoint_unit": "events_per_100000_cells",
            "exposure_unit": "molecules_per_cell", "origin": "synthetic",
            "uncertainty_basis": "unreported", "measurements": {
                role: {"value": value, "measurement_id": "observation_" + role}
                for role, value in zip(PRIMITIVE_ORDER, [100, 20, 90, 100, 90, 8, 7])}}
    payloads[DATA] = {"artifact_ref": DATA_ARTIFACT, "content": json.dumps(data).encode()}
    calls = []
    def read_source(reference, representation):
        calls.append((reference, representation))
        return payloads[reference]
    return args, payloads, data, calls, read_source


def read(fix):
    return read_perturbation_inputs(fix[0], read_source=fix[4])


def set_data(fix):
    fix[1][DATA]["content"] = json.dumps(fix[2], ensure_ascii=False).encode()


def interpreted(fix, **changes):
    fix[0].update(changes)
    fix[0]["interpretation_witnesses"] = [witness()]
    return fix


def test_no_data_preserves_exact_unknowns_unreported_units_and_literal_custody():
    fix = fixture()
    out = read(fix)
    assert set(out) == {"version", "source_ref", "source_kind", "data_source_ref", "literals",
        "design", "measurement_status", "same_endpoint_scope", "amount_role", "orientation",
        "interpretation_witnesses", "primitive_order", "values", "measurement_keys",
        "primitive_observations", "endpoint_unit", "exposure_unit", "data_origin",
        "uncertainty_basis", "source_refs"}
    assert out["version"] == VERSION
    assert out["primitive_order"] == list(PRIMITIVE_ORDER)
    for field in ("values", "measurement_keys", "primitive_observations"):
        assert out[field] == dict.fromkeys(PRIMITIVE_ORDER)
    assert out["endpoint_unit"] == out["exposure_unit"] == out["uncertainty_basis"] == "unreported"
    assert out["data_origin"] is out["data_source_ref"] is None
    assert out["literals"]["molecule"] == {"value": "molecule M",
        "witness": {**witness("molecule M"), "artifact_ref": ARTIFACT}}
    assert out["literals"]["recipient"] is None
    assert out["source_refs"] == [SOURCE]
    assert fix[3] == [(SOURCE, "original")]


def test_qualitative_reconstitution_preserves_source_meanings_and_no_numeric_data():
    fix = interpreted(fixture(), design="cas_free_reconstitution",
                      measurement_status="qualitative_only", same_endpoint_scope="yes")
    fix[0]["literals"]["recipient"] = witness("recipient C")
    out = read(fix)
    assert out["design"] == "cas_free_reconstitution"
    assert out["measurement_status"] == "qualitative_only"
    assert out["same_endpoint_scope"] == "yes"
    assert all(value is None for value in out["values"].values())
    assert out["literals"]["recipient"]["value"] == "recipient C"
    assert out["interpretation_witnesses"][0]["artifact_ref"] == ARTIFACT


def test_retained_data_preserves_raw_entries_values_origin_and_physical_units():
    fix = interpreted(fixture(populated=True), design="native_deletion_restoration",
                      measurement_status="validated_ratio_scale", same_endpoint_scope="yes",
                      amount_role="nuisance", orientation=1)
    out = read(fix)
    assert out["values"] == dict(zip(PRIMITIVE_ORDER, [100, 20, 90, 100, 90, 8, 7]))
    assert out["data_origin"] == "synthetic"
    assert out["source_refs"] == [SOURCE, DATA]
    for role in PRIMITIVE_ORDER:
        obs = out["primitive_observations"][role]
        assert obs["raw_entry"] == fix[2]["measurements"][role]
        assert obs["value"] == fix[2]["measurements"][role]["value"]
        assert obs["source_ref"] == DATA and obs["artifact_ref"] == DATA_ARTIFACT
        assert obs["unit"] == ("molecules_per_cell" if role.startswith("A_") else "events_per_100000_cells")
    assert fix[3] == [(SOURCE, "original"), (DATA, "original")]
    fix[2]["measurements"]["W"]["value"] = -5
    fix[0]["literals"]["molecule"]["quote"] = "changed"
    assert out["primitive_observations"]["W"]["raw_entry"]["value"] == 100
    assert out["literals"]["molecule"]["value"] == "molecule M"


def test_full_canonical_unicode_physical_key_uses_source_artifact_and_explicit_id():
    fix = fixture(populated=True)
    fix[2]["measurements"]["W"]["measurement_id"] = "référence µ"
    set_data(fix)
    owner = {"source_ref": DATA, "artifact_ref": DATA_ARTIFACT, "measurement_id": "référence µ"}
    digest = hashlib.sha256(json.dumps(owner, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    expected = "literature_measurement_" + digest
    assert read(fix)["measurement_keys"]["W"] == expected
    assert len(expected) == len("literature_measurement_") + 64
    fix[1][DATA]["artifact_ref"] = ARTIFACT
    assert read(fix)["measurement_keys"]["W"] != expected
    fix[1][DATA]["artifact_ref"] = DATA_ARTIFACT
    fix[1][OTHER] = fix[1][DATA]
    fix[0]["data_source_ref"] = OTHER
    assert read(fix)["measurement_keys"]["W"] != expected


def test_equal_values_are_distinct_unless_source_explicitly_aliases_measurement_id():
    fix = fixture(populated=True)
    fix[2]["measurements"]["R"]["value"] = 100
    set_data(fix)
    out = read(fix)
    assert out["measurement_keys"]["W"] != out["measurement_keys"]["R"]
    fix[2]["measurements"]["R"]["measurement_id"] = "observation_W"
    set_data(fix)
    out = read(fix)
    assert out["measurement_keys"]["W"] == out["measurement_keys"]["R"]


@pytest.mark.parametrize("role", PRIMITIVE_ORDER)
def test_missing_value_may_retain_source_id_but_has_no_computed_key(role):
    fix = fixture(populated=True)
    fix[2]["measurements"][role]["value"] = None
    set_data(fix)
    out = read(fix)
    assert out["values"][role] is out["measurement_keys"][role] is None
    assert out["primitive_observations"][role]["raw_entry"]["measurement_id"] == "observation_" + role


@pytest.mark.parametrize("field,value", [("design", "variant_replacement"),
    ("design", "conflicting"), ("measurement_status", "qualitative_only"),
    ("same_endpoint_scope", "no"), ("amount_role", "intended_change"), ("orientation", -1)])
def test_each_interpretation_requires_at_least_one_actual_witness(field, value):
    fix = fixture()
    fix[0][field] = value
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        read(fix)
    fix[0]["interpretation_witnesses"] = [witness()]
    assert read(fix)[field] == value


def test_extra_direct_sources_are_read_once_and_preserved_in_order():
    fix = fixture(populated=True)
    fix[1][OTHER] = {"artifact_ref": ARTIFACT, "content": TEXT.encode()}
    fix[0]["literals"]["recipient"] = witness("recipient C", source=OTHER, representation="text")
    fix[0]["interpretation_witnesses"] = [witness(source=OTHER, representation="text")]
    out = read(fix)
    assert out["source_refs"] == [SOURCE, OTHER, DATA]
    assert fix[3] == [(SOURCE, "original"), (OTHER, "text"), (DATA, "original")]


@pytest.mark.parametrize("mutation", [{"start": True}, {"start": -1}, {"end": 99999},
    {"start": 0, "end": 1, "quote": "µ"}, {"quote": "invented"},
    {"representation": "unsupported"}, {"extra": "field"}])
def test_source_witness_checks_actual_bytes_utf8_offsets_and_closed_fields(mutation):
    fix = fixture()
    fix[0]["literals"]["molecule"].update(mutation)
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("orientation", [True, False, 1.0, -1.0, "1", 0, 2])
def test_orientation_is_literal_integer_sign_only(orientation):
    fix = interpreted(fixture(), orientation=orientation)
    with pytest.raises(ExperimentalContractError, match="orientation_integer_sign_required"):
        read(fix)


@pytest.mark.parametrize("value,error", [(True, "finite_number_required"),
    (False, "finite_number_required"), ("100", "finite_number_required"),
    (-1, "nonnegative_measurement_required"), (math.inf, "finite_number_required"),
    (math.nan, "finite_number_required"), (10**400, "finite_number_required")])
def test_retained_point_values_are_finite_nonnegative_numbers_not_booleans(value, error):
    fix = fixture(populated=True)
    fix[2]["measurements"]["W"]["value"] = value
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("raw,error", [
    (b'{"version":"one","version":"two"}', "duplicate_json_key"),
    (b'{"nested":{"x":1,"x":2}}', "duplicate_json_key"),
    (b'{"x":NaN}', "finite_number_required"), (b'{"x":Infinity}', "finite_number_required"),
    (b'{"x":-Infinity}', "finite_number_required"), (b'{"x":1e999}', "finite_number_required"),
    (b'{"x":1e-999}', "numerical_model_range"), (b'{"x":-1e-999}', "numerical_model_range"),
    (b'{"x":' + b'1' * 400 + b'}', "finite_number_required"),
    (b'\xff', "malformed_perturbation_measurements_source"),
    (b'{} trailing', "malformed_perturbation_measurements_source"),
    (b'[' * 2000 + b']' * 2000, "malformed_perturbation_measurements_source|closed_fields_required"),
])
def test_strict_utf8_json_rejects_duplicates_nonfinite_underflow_and_malformed_data(raw, error):
    fix = fixture(populated=True)
    fix[1][DATA]["content"] = raw
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("mutation,error", [
    (lambda d: d.update(extra=1), "closed_fields_required"),
    (lambda d: d.update(version="wrong"), "unsupported_perturbation_measurements_version"),
    (lambda d: d.update(endpoint_unit="unreported"), "unsupported_endpoint_unit"),
    (lambda d: d.update(exposure_unit="unreported"), "unsupported_exposure_unit"),
    (lambda d: d.update(origin="derived"), "unknown_measurement_origin"),
    (lambda d: d.update(uncertainty_basis="sem"), "unsupported_uncertainty_basis"),
    (lambda d: d["measurements"].pop("R"), "closed_fields_required"),
    (lambda d: d["measurements"]["W"].update(extra="field"), "closed_fields_required"),
    (lambda d: d["measurements"]["W"].update(measurement_id=None), "known_measurement_id_required"),
    (lambda d: d["measurements"]["W"].update(measurement_id=" "), "nonempty_source_token_required"),
])
def test_retained_data_closed_schema_units_origin_and_measurement_identity(mutation, error):
    fix = fixture(populated=True)
    mutation(fix[2])
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("role", ["W", "K", "R"])
def test_qualitative_endpoint_cannot_be_converted_to_numeric_point(role):
    fix = interpreted(fixture(populated=True), measurement_status="qualitative_only")
    for other in ("W", "K", "R"):
        if other != role:
            fix[2]["measurements"][other]["value"] = None
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match="qualitative_endpoint_has_no_numeric_values"):
        read(fix)


def test_uncalibrated_conflicting_status_preserves_points_without_calculating_effects():
    fix = interpreted(fixture(populated=True), measurement_status="conflicting", same_endpoint_scope="no")
    out = read(fix)
    assert out["values"]["W"] == 100
    assert out["measurement_status"] == "conflicting" and out["same_endpoint_scope"] == "no"
    assert "cells" not in out


@pytest.mark.parametrize("role", ["K", "A_reference"])
def test_same_source_measurement_id_cannot_declare_different_value_or_unit(role):
    fix = fixture(populated=True)
    fix[2]["measurements"][role]["measurement_id"] = "observation_W"
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match="shared_measurement_value_or_unit_mismatch"):
        read(fix)


def test_explicit_zero_and_representable_tiny_point_are_not_missing():
    fix = fixture(populated=True)
    fix[2]["measurements"]["W"]["value"] = 0
    fix[2]["measurements"]["K"]["value"] = 5e-324
    set_data(fix)
    out = read(fix)
    assert out["values"]["W"] == 0
    assert out["values"]["K"] == 5e-324
    assert out["measurement_keys"]["W"] is not None


def test_population_schema_is_closed_detached_and_disallows_direct_measurement_arguments():
    fix = fixture()
    validate_schema(fix[0], perturbation_population_schema())
    schema = perturbation_population_schema()
    schema["properties"]["source_kind"]["enum"].append("bad")
    assert "bad" not in perturbation_population_schema()["properties"]["source_kind"]["enum"]
    for extra in ({"values": {"W": 100}}, {"W": 100}, {"origin": "reported"}):
        with pytest.raises(ContractError):
            validate_schema({**fix[0], **extra}, perturbation_population_schema())
        with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
            read_perturbation_inputs({**fix[0], **extra}, read_source=fix[4])
    assert fix[3] == []


@pytest.mark.parametrize("field", ["design", "measurement_status", "same_endpoint_scope", "amount_role"])
def test_unsupported_interpretation_values_rejected(field):
    fix = fixture()
    fix[0][field] = "invented"
    with pytest.raises(ExperimentalContractError, match="unknown_interpretation_value"):
        read(fix)


def test_callback_authority_failures_propagate_without_fallback():
    fix = fixture(populated=True)
    def denied(reference, representation):
        if reference == DATA:
            raise PermissionError("not received")
        return fix[4](reference, representation)
    with pytest.raises(PermissionError, match="not received"):
        read_perturbation_inputs(fix[0], read_source=denied)
    assert fix[3] == [(SOURCE, "original")]


@pytest.mark.parametrize("result,error", [
    ({"artifact_ref": ARTIFACT, "content": "not bytes"}, "source_bytes_required"),
    ({"artifact_ref": "", "content": b""}, "nonempty_source_token_required"),
    ({"artifact_ref": ARTIFACT, "content": b"", "extra": 1}, "closed_fields_required"),
])
def test_source_callback_response_must_preserve_exact_byte_custody(result, error):
    with pytest.raises(ExperimentalContractError, match=error):
        read_perturbation_inputs(fixture()[0], read_source=lambda *_: result)
