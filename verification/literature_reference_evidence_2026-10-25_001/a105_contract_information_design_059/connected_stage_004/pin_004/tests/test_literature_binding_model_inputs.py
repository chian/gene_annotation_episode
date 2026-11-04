"""Synthetic retained models only; no paper or retained paper packet is read."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from gene_annotation_episode.literature_binding_model_inputs import (
    MODEL_VERSION, read_binding_model,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


OWNERS = {"reference": "binding_measurement_fixture_reference",
          "test": "binding_measurement_fixture_test"}


def model(**changes):
    return {"version": MODEL_VERSION, "parameter_kind": "ic50",
            "measurement_order": ["reference", "test"],
            "measurement_keys": list(OWNERS.values()),
            "log_covariance": [[.04, .01], [.01, .09]],
            "variance_status": "known", "censoring_model": "none",
            "log_basis": "natural_log_nM", "origin": "synthetic", **changes}


def source(value=None):
    return {"source_ref": "source:synthetic-model", "artifact_ref": "artifact:synthetic-model",
            "content": json.dumps(model() if value is None else value, allow_nan=False).encode("utf-8")}


def read(value=None, **kwargs):
    return read_binding_model(source() if value is None else value,
                              parameter_kind=kwargs.pop("parameter_kind", "ic50"),
                              measurement_keys=kwargs.pop("measurement_keys", deepcopy(OWNERS)), **kwargs)


def test_exact_normalized_model_and_source_refs_preserved_as_detached_json_values():
    value = source()
    before = deepcopy(value)
    result = read(value)
    assert result == {"model": model(), "source": {key: value[key] for key in ("source_ref", "artifact_ref")}}
    assert result == json.loads(json.dumps(result, allow_nan=False))
    result["model"]["log_covariance"][0][0] = 100
    result["source"]["source_ref"] = "changed"
    assert value == before
    assert read(value)["model"] == model()


@pytest.mark.parametrize("parameter_kind", ["ic50", "reported_hill_kd"])
@pytest.mark.parametrize("variance_status", ["known", "estimated", "unknown"])
@pytest.mark.parametrize("censoring_model", ["none", "threshold_of_log_estimate", "unknown"])
@pytest.mark.parametrize("origin", ["reported", "derived", "synthetic"])
def test_allowed_source_declarations_are_preserved_without_scientific_upgrade(
        parameter_kind, variance_status, censoring_model, origin):
    declared = model(parameter_kind=parameter_kind, variance_status=variance_status,
                     censoring_model=censoring_model, origin=origin)
    assert read(source(declared), parameter_kind=parameter_kind)["model"] == declared


@pytest.mark.parametrize("field,value", [
    ("version", "other"), ("version", None), ("version", []),
    ("parameter_kind", "kd"), ("parameter_kind", None), ("parameter_kind", {}),
    ("measurement_order", ["test", "reference"]), ("measurement_order", ["reference"]),
    ("measurement_order", {"reference": 0, "test": 1}), ("measurement_order", None),
    ("measurement_keys", list(reversed(list(OWNERS.values())))),
    ("measurement_keys", [OWNERS["reference"], "different-source-owner"]),
    ("measurement_keys", [OWNERS["reference"], None]), ("measurement_keys", OWNERS),
    ("measurement_keys", [OWNERS["reference"], OWNERS["test"], "extra"]),
    ("log_basis", "log10_nM"), ("log_basis", "natural_log_uM"), ("log_basis", []),
    ("variance_status", "sd"), ("variance_status", None), ("variance_status", True),
    ("censoring_model", "reported_limit"), ("censoring_model", None), ("censoring_model", {}),
    ("origin", "estimated"), ("origin", None), ("origin", 1),
])
def test_wrong_declared_kind_order_owners_basis_and_scalar_types_are_rejected(field, value):
    with pytest.raises(ExperimentalContractError) as error:
        read(source(model(**{field: value})))
    assert error.value.code
    assert error.value.field == "model." + field


def test_supported_parameter_kind_still_has_to_match_selected_binding_sheet():
    with pytest.raises(ExperimentalContractError, match="binding_parameter_kind_mismatch"):
        read(source(model(parameter_kind="reported_hill_kd")))


@pytest.mark.parametrize("bad", [None, [], "ic50", {}, {**OWNERS, "extra": "key"},
    {"reference": OWNERS["reference"]}, {**OWNERS, "reference": None},
    {**OWNERS, "test": " "}, {**OWNERS, "test": 1}, {**OWNERS, "test": []}])
def test_expected_owner_mapping_is_closed_complete_and_nonempty(bad):
    with pytest.raises(ExperimentalContractError) as error:
        read(measurement_keys=bad)
    assert error.value.field.startswith("measurement_keys")


@pytest.mark.parametrize("kind", [None, "", "kd", [], {}, 1, True])
def test_selected_parameter_kind_is_validated(kind):
    with pytest.raises(ExperimentalContractError, match="unsupported_binding_parameter_kind:parameter_kind"):
        read(parameter_kind=kind)


@pytest.mark.parametrize("matrix", [None, {}, [], [1, 2], [[1, 0]],
    [[1, 0], [0, 1], [0, 0]], [[1, 0, 0], [0, 1]],
    [[True, 0], [0, 1]], [[1, None], [None, 1]], [[1, "0"], ["0", 1]],
    [[1, []], [[], 1]], [[1, {}], [{}, 1]], [[1, .01], [.010000000000000002, 1]],
])
def test_covariance_requires_exact_finite_symmetric_two_by_two_numbers(matrix):
    with pytest.raises(ExperimentalContractError) as error:
        read(source(model(log_covariance=matrix)))
    assert error.value.field.startswith("model.log_covariance")


@pytest.mark.parametrize("matrix", [[[0, 0], [0, 0]], [[1, 1], [1, 1]],
                                    [[1, 2], [2, 1]], [[-1, 0], [0, 1]]])
def test_positive_definiteness_is_explicitly_left_to_calculator(matrix):
    assert read(source(model(log_covariance=matrix)))["model"]["log_covariance"] == matrix


def test_same_physical_owner_cannot_claim_different_covariance_rows():
    owners = dict.fromkeys(("reference", "test"), "binding_measurement_shared_fixture")
    declared = model(measurement_keys=list(owners.values()))
    with pytest.raises(ExperimentalContractError, match="shared_measurement_covariance_mismatch"):
        read(source(declared), measurement_keys=owners)
    # Consistent repeated ownership is singular; the calculator owns rejection of
    # that density model. The source parser verifies only ownership consistency.
    declared["log_covariance"] = [[.04, .04], [.04, .04]]
    assert read(source(declared), measurement_keys=owners)["model"] == declared


@pytest.mark.parametrize("text", ["", "{", "[]", "null", "true", "1", '"model"',
    "{} trailing", '{"version":"a","version":"b"}',
    '{"outer":{"key":1,"key":2}}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
    '{"x":1e999}', '{"x":1e-999}', '\ufeff{}',
    '[' * 2000 + ']' * 2000])
def test_strict_json_rejects_bad_encoding_shape_duplicate_keys_nonfinite_and_range(text):
    with pytest.raises(ExperimentalContractError) as error:
        read({**source(), "content": text.encode("utf-8")})
    assert error.value.code


def test_valid_numeric_json_cannot_hide_nonfinite_or_underflowing_covariance():
    for token in ("1e999", "1e-999", "-1e-999", "NaN", "Infinity", "-Infinity"):
        text = json.dumps(model()).replace("0.04", token)
        with pytest.raises(ExperimentalContractError):
            read({**source(), "content": text.encode("utf-8")})
    assert read({**source(), "content": json.dumps(model()).replace("0.01", "0e-999").encode()})[
        "model"]["log_covariance"][0][1] == 0


def test_unrepresentably_large_json_integer_is_not_a_finite_covariance():
    text = json.dumps(model()).replace("0.04", "1" + "0" * 400)
    with pytest.raises(ExperimentalContractError, match="finite_number_required"):
        read({**source(), "content": text.encode()})


def test_invalid_utf8_returns_repairable_contract_failure():
    with pytest.raises(ExperimentalContractError, match="malformed_binding_model_source:source.content"):
        read({**source(), "content": b"\xff"})


@pytest.mark.parametrize("field", list(model()))
def test_all_model_fields_required(field):
    declared = model()
    declared.pop(field)
    with pytest.raises(ExperimentalContractError, match="closed_fields_required:model"):
        read(source(declared))


def test_unknown_model_fields_rejected_without_inference_or_fallback():
    with pytest.raises(ExperimentalContractError, match="closed_fields_required:model"):
        read(source(model(independent_preparation_count=3)))


@pytest.mark.parametrize("mutation", [lambda x: x.pop("artifact_ref"),
    lambda x: x.update(extra=1), lambda x: x.update(source_ref=" "),
    lambda x: x.update(artifact_ref=None), lambda x: x.update(content="{}"),
    lambda x: x.update(content=bytearray(b"{}")), lambda x: x.update(content=None)])
def test_source_envelope_requires_closed_refs_and_exact_bytes(mutation):
    value = source()
    mutation(value)
    with pytest.raises(ExperimentalContractError) as error:
        read(value)
    assert error.value.field.startswith("source")


def test_reader_does_not_read_write_fetch_or_call_models():
    value = source()
    with patch("builtins.open", side_effect=AssertionError("unexpected filesystem access")), \
            patch("io.open", side_effect=AssertionError("unexpected filesystem access")), \
            patch("urllib.request.urlopen", side_effect=AssertionError("unexpected acquisition")), \
            patch("socket.create_connection", side_effect=AssertionError("unexpected connection")):
        assert read(value)["model"] == model()
