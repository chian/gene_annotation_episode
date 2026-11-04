"""Synthetic retained-data/custody checks; no primary-source acquisition."""
import hashlib
import json
import math

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_reaction_inputs import (
    BUDGET_BASES, DATA_VERSION, LITERAL_FIELDS, RATIO_KINDS, VERSION,
    reaction_population_schema, read_reaction_inputs,
)


SOURCE = "source_" + "1" * 24
DATA = "source_" + "2" * 24
OTHER = "source_" + "3" * 24
ARTIFACT = "artifact_" + "4" * 24
DATA_ARTIFACT = "artifact_" + "5" * 24
TEXT = "µ source: molecule M; construct C; product-pair ratio; resource context."


def witness(quote="product-pair ratio", *, source=SOURCE, representation="original"):
    start = TEXT.encode().index(quote.encode())
    return {"source_ref": source, "representation": representation,
            "start": start, "end": start + len(quote.encode()), "quote": quote}


def fixture(*, populated=False):
    args = {"source_ref": SOURCE, "data_source_ref": DATA if populated else None,
            "source_kind": "synthetic_fixture", "literals": dict.fromkeys(LITERAL_FIELDS),
            "interpretation_witnesses": []}
    args["literals"]["molecule"] = witness("molecule M")
    data = {"version": DATA_VERSION,
            "ratio": {"mode": "independent_units", "ratio_kind": "product_pair",
                "unit": "mol_per_mol", "origin": "synthetic",
                "observations": [{"measurement_key": "preparation1", "value": .7},
                                 {"measurement_key": "preparation2", "value": .9}],
                "mean": None, "sample_sd": None, "independent_n": None,
                "claim": 1, "alternatives": [{"key": "half_ratio", "prediction": .5}]},
            "budget": {"basis": "usable_batch", "unit": "umol", "origin": "synthetic",
                "resources_complete": True, "resources": [
                    {"resource_key": "usable_A", "value": 12, "lower": 10, "upper": 14,
                     "coefficient": 1},
                    {"resource_key": "usable_B", "value": 6, "lower": 5, "upper": 7,
                     "coefficient": 1}], "demand": 10}}
    payloads = {SOURCE: {"artifact_ref": ARTIFACT, "content": TEXT.encode()},
                DATA: {"artifact_ref": DATA_ARTIFACT, "content": json.dumps(data).encode()}}
    calls = []

    def read_source(reference, representation):
        calls.append((reference, representation))
        return payloads[reference]
    return args, payloads, data, calls, read_source


def read(fix):
    return read_reaction_inputs(fix[0], read_source=fix[4])


def set_data(fix):
    fix[1][DATA]["content"] = json.dumps(fix[2], ensure_ascii=False).encode()


def make_summary(fix, **updates):
    fix[2]["ratio"].update(mode="source_summary", observations=[], mean=1,
                           sample_sd=None, independent_n=None)
    fix[2]["ratio"].update(updates)
    set_data(fix)
    return fix


def physical_key(source, artifact, local_id):
    owner = {"source_ref": source, "artifact_ref": artifact, "measurement_id": local_id}
    raw = json.dumps(owner, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode()
    return "literature_measurement_" + hashlib.sha256(raw).hexdigest()


def test_unknown_dataset_preserves_nulls_literal_custody_and_exact_output_contract():
    fix = fixture()
    out = read(fix)
    assert set(out) == {"version", "arguments", "sources", "literals", "interpretations",
                        "observations", "calculation_inputs"}
    assert out["version"] == VERSION
    assert out["observations"] is None
    assert out["calculation_inputs"] == {"ratio": None, "budget": None}
    assert out["sources"] == [SOURCE]
    assert out["literals"]["molecule"] == {"value": "molecule M",
        "witness": {**witness("molecule M"), "artifact_ref": ARTIFACT}}
    assert out["literals"]["denominator"] is None
    assert out["interpretations"] == []
    assert fix[3] == [(SOURCE, "original")]


def test_retained_data_preserves_raw_values_and_does_no_calculation():
    fix = fixture(populated=True)
    out = read(fix)
    assert out["observations"] == fix[2]
    assert out["sources"] == [SOURCE, DATA]
    assert out["arguments"] == fix[0]
    assert out["calculation_inputs"]["ratio"]["observations"][0] == {
        "measurement_key": physical_key(DATA, DATA_ARTIFACT, "preparation1"), "value": .7}
    assert out["calculation_inputs"]["ratio"]["mean"] is None
    assert out["calculation_inputs"]["ratio"]["independent_n"] is None
    assert out["calculation_inputs"]["ratio"]["alternatives"] == [{"key": "half_ratio", "prediction": .5}]
    assert out["calculation_inputs"]["budget"]["resources"][1] == {
        "resource_key": physical_key(DATA, DATA_ARTIFACT, "usable_B"),
        "value": 6, "lower": 5, "upper": 7, "coefficient": 1}
    assert "cells" not in out and "resource_capacity" not in out
    fix[0]["literals"]["molecule"]["quote"] = "changed"
    fix[2]["ratio"]["observations"][0]["value"] = -3
    assert out["arguments"]["literals"]["molecule"]["quote"] == "molecule M"
    assert out["observations"]["ratio"]["observations"][0]["value"] == .7
    out["calculation_inputs"]["budget"]["resources"][0]["value"] = 100
    assert out["observations"]["budget"]["resources"][0]["value"] == 12


def test_namespace_uses_exact_local_unicode_id_source_and_artifact_not_value():
    fix = fixture(populated=True)
    observations = fix[2]["ratio"]["observations"]
    observations[0].update(measurement_key="référence µ", value=.9)
    set_data(fix)
    out = read(fix)
    first, second = out["calculation_inputs"]["ratio"]["observations"]
    assert first["measurement_key"] == physical_key(DATA, DATA_ARTIFACT, "référence µ")
    assert first["measurement_key"] != second["measurement_key"]
    assert first["value"] == second["value"]
    original = first["measurement_key"]
    fix[1][DATA]["artifact_ref"] = ARTIFACT
    assert read(fix)["calculation_inputs"]["ratio"]["observations"][0]["measurement_key"] != original
    fix[1][DATA]["artifact_ref"] = DATA_ARTIFACT
    fix[1][OTHER] = fix[1][DATA]
    fix[0]["data_source_ref"] = OTHER
    assert read(fix)["calculation_inputs"]["ratio"]["observations"][0]["measurement_key"] != original


def test_reported_summary_is_not_rewritten_as_single_exact_independent_unit():
    fix = make_summary(fixture(populated=True), origin="reported", alternatives=[])
    out = read(fix)
    ratio = out["calculation_inputs"]["ratio"]
    assert ratio["mode"] == "source_summary"
    assert ratio["mean"] == 1 and ratio["observations"] == []
    assert ratio["sample_sd"] is ratio["independent_n"] is None
    assert ratio["alternatives"] == []
    assert ratio["origin"] == "reported"


@pytest.mark.parametrize("mean,sd,count", [(None, None, None), (1, .2, None),
    (None, .2, 3), (1, .2, 3), (1, None, 1)])
def test_summary_partial_operands_remain_missing_without_conversion(mean, sd, count):
    fix = make_summary(fixture(populated=True), mean=mean, sample_sd=sd, independent_n=count)
    ratio = read(fix)["calculation_inputs"]["ratio"]
    assert (ratio["mean"], ratio["sample_sd"], ratio["independent_n"]) == (mean, sd, count)


@pytest.mark.parametrize("ratio_kind", RATIO_KINDS)
def test_ratio_kinds_preserve_denominator_meaning_and_supported_units(ratio_kind):
    fix = fixture(populated=True)
    unit = "signal_per_signal" if ratio_kind == "signal_ratio" else "mol_per_mol"
    fix[2]["ratio"].update(ratio_kind=ratio_kind, unit=unit)
    set_data(fix)
    assert read(fix)["calculation_inputs"]["ratio"]["ratio_kind"] == ratio_kind
    fix[2]["ratio"]["unit"] = "mol_per_mol" if unit == "signal_per_signal" else "signal_per_signal"
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match="ratio_kind_unit_mismatch"):
        read(fix)


@pytest.mark.parametrize("basis", BUDGET_BASES)
def test_supply_batch_and_usable_rate_are_distinct_and_missing_bounds_not_imputed(basis):
    fix = fixture(populated=True)
    unit = "uM_per_min" if basis == "usable_rate" else "uM"
    budget = fix[2]["budget"]
    budget.update(basis=basis, unit=unit, resources_complete=False, demand=None)
    budget["resources"][0].update(value=None, lower=None, upper=10)
    budget["resources"][1].update(value=0, lower=0, upper=0)
    set_data(fix)
    out = read(fix)["calculation_inputs"]["budget"]
    assert out["basis"] == basis and out["unit"] == unit
    assert out["resources_complete"] is False and out["demand"] is None
    assert out["resources"][0]["lower"] is out["resources"][0]["value"] is None
    assert out["resources"][1]["value"] == 0
    budget["unit"] = "umol" if unit == "uM_per_min" else "umol_per_min"
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match="budget_basis_unit_mismatch"):
        read(fix)


def test_signed_ratio_values_and_predictions_keep_negative_net_measurement():
    fix = fixture(populated=True)
    fix[2]["ratio"]["observations"][0]["value"] = -.7
    fix[2]["ratio"]["claim"] = -1
    fix[2]["ratio"]["alternatives"][0]["prediction"] = -.5
    set_data(fix)
    out = read(fix)["calculation_inputs"]["ratio"]
    assert out["observations"][0]["value"] == -.7
    assert out["claim"] == -1 and out["alternatives"][0]["prediction"] == -.5


def test_source_encounter_order_is_root_then_fixed_literals_interpretations_dataset():
    fix = fixture(populated=True)
    fix[1][OTHER] = {"artifact_ref": ARTIFACT, "content": TEXT.encode()}
    fix[0]["literals"]["denominator"] = witness(source=OTHER, representation="text")
    fix[0]["interpretation_witnesses"] = [witness(source=OTHER, representation="text")]
    out = read(fix)
    assert out["sources"] == [SOURCE, OTHER, DATA]
    assert fix[3] == [(SOURCE, "original"), (OTHER, "text"), (DATA, "original")]
    assert out["interpretations"][0] == {**witness(source=OTHER, representation="text"),
                                           "artifact_ref": ARTIFACT}


@pytest.mark.parametrize("target", ["literal", "interpretation"])
@pytest.mark.parametrize("mutation", [{"start": True}, {"start": -1}, {"end": 10000},
    {"start": 0, "end": 1, "quote": "µ"}, {"quote": "invented"},
    {"representation": "unsupported"}, {"extra": 1}])
def test_byte_spans_literal_and_interpretation_witnesses_enforce_utf8_custody(target, mutation):
    fix = fixture()
    selected = witness()
    selected.update(mutation)
    if target == "literal":
        fix[0]["literals"]["endpoint"] = selected
    else:
        fix[0]["interpretation_witnesses"] = [selected]
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("raw,error", [
    (b'{"version":"one","version":"two"}', "duplicate_json_key"),
    (b'{"nested":{"x":1,"x":2}}', "duplicate_json_key"),
    (b'{"x":NaN}', "finite_number_required"), (b'{"x":Infinity}', "finite_number_required"),
    (b'{"x":-Infinity}', "finite_number_required"), (b'{"x":1e999}', "finite_number_required"),
    (b'{"x":1e-999}', "numerical_model_range"), (b'{"x":-1e-999}', "numerical_model_range"),
    (b'{"x":' + b'1' * 400 + b'}', "finite_number_required"),
    (b'\xff', "malformed_reaction_measurements_source"),
    (b'{} trailing', "malformed_reaction_measurements_source"),
    (b'[' * 2000 + b']' * 2000, "malformed_reaction_measurements_source|closed_fields_required"),
])
def test_strict_json_rejects_nonfinite_duplicates_underflow_and_malformed_bytes(raw, error):
    fix = fixture(populated=True)
    fix[1][DATA]["content"] = raw
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("mutation,error", [
    (lambda d: d.update(version="bad"), "unsupported_reaction_measurements_version"),
    (lambda d: d.update(extra=1), "closed_fields_required"),
    (lambda d: d.pop("budget"), "closed_fields_required"),
    (lambda d: d["ratio"].update(extra=1), "closed_fields_required"),
    (lambda d: d["ratio"].update(mode="technical_repeats"), "unsupported_mode"),
    (lambda d: d["ratio"].update(ratio_kind="yield"), "unsupported_ratio_kind"),
    (lambda d: d["ratio"].update(origin="guessed"), "unsupported_origin"),
    (lambda d: d["ratio"].update(unit="percent"), "unsupported_unit"),
    (lambda d: d["ratio"].update(mean=.8), "independent_unit_summary_fields_must_be_null"),
    (lambda d: d["ratio"].update(observations=[]), "nonempty_array_required"),
    (lambda d: d["ratio"].update(mode="source_summary"), "source_summary_observations_must_be_empty"),
    (lambda d: d["ratio"]["observations"][0].update(extra=1), "closed_fields_required"),
    (lambda d: d["ratio"]["observations"][0].update(measurement_key=" "), "nonempty_source_token_required"),
    (lambda d: d["ratio"]["observations"][1].update(measurement_key="preparation1"), "duplicate_physical_or_model_key"),
    (lambda d: d["ratio"].update(alternatives=None), "array_required"),
    (lambda d: d["ratio"]["alternatives"].append({"key": "half_ratio", "prediction": None}), "duplicate_physical_or_model_key"),
    (lambda d: d["ratio"]["alternatives"][0].update(extra=1), "closed_fields_required"),
    (lambda d: d["budget"].update(basis="genome_hit"), "unsupported_basis"),
    (lambda d: d["budget"].update(origin="guessed"), "unsupported_origin"),
    (lambda d: d["budget"].update(resources_complete=1), "boolean_required"),
    (lambda d: d["budget"].update(resources=[]), "nonempty_array_required"),
    (lambda d: d["budget"]["resources"][1].update(resource_key="usable_A"), "duplicate_physical_or_model_key"),
    (lambda d: d["budget"]["resources"][0].update(lower=15), "ordered_bounds_required"),
    (lambda d: d["budget"]["resources"][0].update(value=9), "nominal_value_outside_bounds"),
    (lambda d: d["budget"]["resources"][0].update(value=15), "nominal_value_outside_bounds"),
    (lambda d: d["budget"]["resources"][0].update(coefficient=None), "finite_number_required"),
    (lambda d: d["budget"]["resources"][0].update(coefficient=0), "positive_value_required"),
    (lambda d: d["budget"].update(demand=0), "positive_value_required"),
])
def test_closed_dataset_schema_and_meaningful_relationships(mutation, error):
    fix = fixture(populated=True)
    mutation(fix[2])
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("value", [True, False, "1", math.inf, math.nan, 10**400])
@pytest.mark.parametrize("path", ["observation", "prediction", "resource", "coefficient", "demand"])
def test_numbers_never_accept_booleans_strings_or_nonfinite(value, path):
    fix = fixture(populated=True)
    if path == "observation": fix[2]["ratio"]["observations"][0]["value"] = value
    elif path == "prediction": fix[2]["ratio"]["alternatives"][0]["prediction"] = value
    elif path == "resource": fix[2]["budget"]["resources"][0]["value"] = value
    elif path == "coefficient": fix[2]["budget"]["resources"][0]["coefficient"] = value
    else: fix[2]["budget"]["demand"] = value
    set_data(fix)
    with pytest.raises(ExperimentalContractError, match="finite_number_required"):
        read(fix)


@pytest.mark.parametrize("count", [0, -1, True, False, 1.0, "3"])
def test_summary_count_requires_actual_positive_integer(count):
    fix = make_summary(fixture(populated=True), independent_n=count)
    with pytest.raises(ExperimentalContractError, match="positive_integer_count_required"):
        read(fix)


@pytest.mark.parametrize("sd", [-.1, True, "0.2"])
def test_summary_sd_is_nonnegative_measurement_not_encoded_label(sd):
    fix = make_summary(fixture(populated=True), sample_sd=sd)
    with pytest.raises(ExperimentalContractError, match="nonnegative_value_required|finite_number_required"):
        read(fix)


def test_sample_sd_is_undefined_for_single_unit_and_cannot_be_labeled_exact_zero():
    fix = make_summary(fixture(populated=True), independent_n=1, sample_sd=0)
    with pytest.raises(ExperimentalContractError, match="sample_sd_requires_multiple_units"):
        read(fix)


def test_unknown_model_prediction_and_missing_resource_values_are_preserved():
    fix = fixture(populated=True)
    fix[2]["ratio"]["alternatives"].append({"key": "unresolved", "prediction": None})
    fix[2]["budget"]["resources"][0].update(value=None, lower=None, upper=None)
    set_data(fix)
    out = read(fix)["calculation_inputs"]
    assert out["ratio"]["alternatives"][1] == {"key": "unresolved", "prediction": None}
    assert out["budget"]["resources"][0]["value"] is None
    assert out["budget"]["resources"][0]["lower"] is None


def test_empty_known_packet_is_distinct_from_unretrieved_dataset():
    fix = fixture(populated=True)
    fix[2].update(ratio=None, budget=None)
    set_data(fix)
    out = read(fix)
    assert out["observations"] == {"version": DATA_VERSION, "ratio": None, "budget": None}
    assert out["calculation_inputs"] == {"ratio": None, "budget": None}
    assert out["sources"] == [SOURCE, DATA]


def test_schema_closed_detached_and_forbids_direct_selected_numeric_measurements():
    fix = fixture()
    validate_schema(fix[0], reaction_population_schema())
    schema = reaction_population_schema()
    schema["properties"]["source_kind"]["enum"].append("bad")
    assert "bad" not in reaction_population_schema()["properties"]["source_kind"]["enum"]
    for extra in ({"mean": 1}, {"ratio": fix[2]["ratio"]}, {"budget": fix[2]["budget"]}):
        with pytest.raises(ContractError):
            validate_schema({**fix[0], **extra}, reaction_population_schema())
        with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
            read_reaction_inputs({**fix[0], **extra}, read_source=fix[4])
    assert fix[3] == []


def test_callback_authority_error_propagates_without_source_reacquisition_or_fallback():
    fix = fixture(populated=True)
    def denied(reference, representation):
        if reference == DATA:
            raise PermissionError("source outside received scope")
        return fix[4](reference, representation)
    with pytest.raises(PermissionError, match="outside received scope"):
        read_reaction_inputs(fix[0], read_source=denied)
    assert fix[3] == [(SOURCE, "original")]


@pytest.mark.parametrize("result,error", [
    ({"artifact_ref": ARTIFACT, "content": "not bytes"}, "source_bytes_required"),
    ({"artifact_ref": "", "content": b""}, "nonempty_source_token_required"),
    ({"artifact_ref": ARTIFACT, "content": b"", "extra": 1}, "closed_fields_required"),
])
def test_source_callback_custody_contract_is_not_relaxed(result, error):
    with pytest.raises(ExperimentalContractError, match=error):
        read_reaction_inputs(fixture()[0], read_source=lambda *_: result)


def test_representable_tiny_numbers_and_zero_are_not_missing():
    fix = fixture(populated=True)
    fix[2]["ratio"]["observations"][0]["value"] = 5e-324
    fix[2]["ratio"]["observations"][1]["value"] = 0
    set_data(fix)
    values = [r["value"] for r in read(fix)["calculation_inputs"]["ratio"]["observations"]]
    assert values == [5e-324, 0]
