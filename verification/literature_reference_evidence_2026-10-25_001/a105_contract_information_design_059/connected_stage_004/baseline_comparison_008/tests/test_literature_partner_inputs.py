"""Retained-byte/custody fixtures, not automatic reading of primary papers."""
from copy import deepcopy
from fractions import Fraction
import json

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode import literature_partner_inputs as reader


SOURCE, DATA, TEXT_SOURCE = ("source_" + str(i) * 24 for i in range(1, 4))
TEXT = "µ synthetic subject A; partner B; PLP endpoint; same declared conditions."


def witness(quote="same declared conditions.", *, reference=SOURCE, representation="original"):
    start = TEXT.encode().index(quote.encode())
    return {"source_ref": reference, "representation": representation,
        "start": start, "end": start + len(quote.encode()), "quote": quote}


def arm(role, value, *, coverage="complete"):
    return {"subject_ref": "subject_A", "partner_ref": "partner_B",
        "partner_state": "absent" if role == "omitted" else "present",
        "endpoint_ref": "PLP_formation", "normalization_ref": "per_mg_subject_A",
        "unit": "pmol/min/mg", "conditions": {"coverage": coverage,
            "factors": [] if coverage == "unreported" else [
                {"factor": "nitrogen", "level": "glutamine", "unit": "identity"},
                {"factor": "temperature", "level": 37, "unit": "degC"}]},
        "measurement": {"measurement_id": "measurement_" + role,
            "status": "observed", "value": value, "origin": "synthetic",
            "spread": {"kind": "unreported", "magnitude": None}}}


def fixture(*, coverage="complete"):
    inputs = {"version": "literature_partner_inputs_v1", "arms": {
        role: arm(role, value, coverage=coverage)
        for role, value in (("reference", 100), ("omitted", 20), ("addback", 90))}}
    recipe = {"version": reader.DATA_VERSION, "inputs": inputs}
    args = {"source_ref": SOURCE, "data_source_ref": DATA, "source_kind": "synthetic_fixture",
        "literals": dict.fromkeys(reader.LITERAL_FIELDS),
        "interpretation_witnesses": [witness()] if coverage == "complete" else []}
    payloads = {SOURCE: {"artifact_ref": "artifact_" + "1" * 24, "content": TEXT.encode()},
        DATA: {"artifact_ref": "artifact_" + "2" * 24, "content": b""},
        TEXT_SOURCE: {"artifact_ref": "artifact_" + "3" * 24, "content": TEXT.encode()}}
    calls = []

    def read_source(reference, representation):
        calls.append((reference, representation))
        return payloads[reference]

    fix = args, recipe, payloads, calls, read_source
    retain(fix)
    return fix


def retain(fix):
    fix[2][DATA]["content"] = json.dumps(fix[1]).encode()


def read(fix):
    return reader.read_partner_inputs(fix[0], read_source=fix[4])


def check_error(fix, code):
    with pytest.raises(ExperimentalContractError) as caught:
        read(fix)
    assert caught.value.code == code


def test_retained_source_values_reach_components_once_without_caller_mutation(monkeypatch):
    fix = fixture()
    originals = deepcopy((fix[0], fix[1], fix[2]))
    calls = []
    original = reader.populate_partner_components

    def calculate(inputs):
        calls.append(deepcopy(inputs))
        return original(inputs)

    monkeypatch.setattr(reader, "populate_partner_components", calculate)
    out = read(fix)
    assert set(out) == {"version", "arguments", "sources", "literals", "interpretations",
                        "recipe", "calculation", "cells"}
    assert out["version"] == reader.VERSION
    assert calls == [fix[1]["inputs"]]
    assert out["sources"] == [SOURCE, DATA]
    assert fix[3] == [(SOURCE, "original"), (DATA, "original")]
    assert out["recipe"] == fix[1]
    assert out["arguments"] == fix[0]
    assert out["cells"] == out["calculation"]["cells"]
    assert tuple(out["cells"]) == reader.COMPONENTS
    assert [out["cells"][key]["value"] for key in reader.COMPONENTS] == [
        100, 20, 90, 80, .8, 70, .875, .7]
    assert all(cell["bound_kind"] == "point_only_not_uncertainty" for cell in out["cells"].values())
    assert (fix[0], fix[1], fix[2]) == originals
    json.dumps(out, allow_nan=False)
    out["cells"]["partner_loss"]["value"] = -5
    out["recipe"]["inputs"]["arms"]["reference"]["measurement"]["value"] = 400
    fix[0]["source_kind"] = "primary_source"
    assert out["calculation"]["cells"]["partner_loss"]["value"] == 80
    assert out["calculation"]["inputs"]["arms"]["reference"]["measurement"]["value"] == 100
    assert out["arguments"]["source_kind"] == "synthetic_fixture"


def test_censored_input_has_conditional_domain_and_shared_omission_arithmetic():
    fix = fixture()
    omitted = fix[1]["inputs"]["arms"]["omitted"]["measurement"]
    omitted.update(status="upper_bound", value=5)
    retain(fix)
    out = read(fix)
    assert out["cells"]["omitted_rate"]["value"] is None
    assert (out["cells"]["omitted_rate"]["lower"], out["cells"]["omitted_rate"]["upper"]) == (0, 5)
    fraction = out["cells"]["addback_fraction"]
    assert fraction["value"] is None and fraction["status"] == "bounded"
    assert Fraction(fraction["lower"]) <= Fraction(85, 95)
    assert Fraction(fraction["upper"]) >= Fraction(9, 10)
    assert fraction["bound_kind"] == "conditional_input_domain_not_CI"
    assert fraction["unavailable_reason"] == "censored_point_unreported"


def test_source_inspired_crossed_conditions_keep_native_values_without_necessity_inference():
    # Controlled retained fixture using supplied source-case operands. No paper
    # is acquired or freshly interpreted by this reader test.
    fix = fixture(coverage="partial")
    fix[0]["source_kind"] = "retained_extraction"
    arms = fix[1]["inputs"]["arms"]
    for role, value, spread in (("reference", 774, 58), ("omitted", 284, 33)):
        arms[role]["normalization_ref"] = None
        arms[role]["measurement"].update(value=value, origin="reported",
            spread={"kind": "unspecified", "magnitude": spread})
    arms["omitted"]["conditions"]["factors"][0]["level"] = "ammonium_sulfate"
    arms["addback"] = None
    retain(fix)
    out = read(fix)
    assert (out["cells"]["reference_rate"]["value"], out["cells"]["omitted_rate"]["value"]) == (774, 284)
    assert out["calculation"]["comparison_checks"]["reference_omitted"]["differing_factors"] == ["nitrogen"]
    assert all(out["cells"][name]["value"] is None for name in reader.COMPONENTS[3:])
    assert out["cells"]["reference_rate"]["lower"] == out["cells"]["reference_rate"]["upper"] == 774
    assert out["calculation"]["inputs"]["arms"]["reference"]["measurement"]["spread"] == {
        "kind": "unspecified", "magnitude": 58}
    assert out["cells"]["addback_rate"]["unavailable_reason"] == "arm_unreported"


def test_all_literal_meanings_utf8_byte_offsets_enrichment_and_source_deduplication():
    fix = fixture()
    for name in reader.LITERAL_FIELDS:
        fix[0]["literals"][name] = witness("µ synthetic subject A", reference=TEXT_SOURCE, representation="text")
    fix[0]["interpretation_witnesses"] = [witness(reference=TEXT_SOURCE, representation="text"), witness("partner B")]
    out = read(fix)
    assert out["sources"] == [SOURCE, DATA, TEXT_SOURCE]
    assert fix[3] == [(SOURCE, "original"), (DATA, "original"), (TEXT_SOURCE, "text")]
    for field in reader.LITERAL_FIELDS:
        assert out["literals"][field] == {"value": "µ synthetic subject A", "witness": {
            **fix[0]["literals"][field], "artifact_ref": fix[2][TEXT_SOURCE]["artifact_ref"]}}
    assert out["interpretations"][1]["artifact_ref"] == fix[2][SOURCE]["artifact_ref"]


def test_binary_root_custody_and_all_missing_arms_without_text_requirement():
    fix = fixture(coverage="unreported")
    fix[1]["inputs"]["arms"] = dict.fromkeys(("reference", "omitted", "addback"))
    fix[2][SOURCE]["content"] = b"\xff\x00original binary source"
    retain(fix)
    out = read(fix)
    assert out["sources"] == [SOURCE, DATA]
    assert out["literals"] == dict.fromkeys(reader.LITERAL_FIELDS)
    assert out["interpretations"] == []
    assert all(c["value"] is None for c in out["cells"].values())


def test_root_and_recipe_same_reference_are_read_once():
    fix = fixture(coverage="partial")
    fix[0]["source_ref"] = DATA
    out = read(fix)
    assert out["sources"] == [DATA]
    assert fix[3] == [(DATA, "original")]


def test_complete_conditions_require_an_actual_interpretation_witness():
    fix = fixture()
    fix[0]["interpretation_witnesses"] = []
    check_error(fix, "interpretation_witness_required")


@pytest.mark.parametrize("role", ["reference", "omitted", "addback"])
def test_synthetic_fixture_rejects_nonsynthetic_arm_origin(role):
    fix = fixture()
    fix[1]["inputs"]["arms"][role]["measurement"]["origin"] = "reported"
    retain(fix)
    check_error(fix, "synthetic_origin_required")


@pytest.mark.parametrize("change,code", [
    (lambda w: w.update(quote="wrong quote"), "source_quote_mismatch"),
    (lambda w: w.update(start=-1), "nonnegative_integer_offset_required"),
    (lambda w: w.update(start=True), "nonnegative_integer_offset_required"),
    (lambda w: w.update(end=999), "source_span_out_of_bounds"),
    (lambda w: w.update(end=w["start"]), "nonempty_source_span_required"),
    (lambda w: w.update(representation="html"), "unknown_source_representation"),
    (lambda w: w.update(extra=1), "closed_fields_required"),
])
def test_bad_literal_witnesses_fail_with_original_specific_reason(change, code):
    fix = fixture()
    selected = witness("subject A")
    change(selected)
    fix[0]["literals"]["subject"] = selected
    check_error(fix, code)


def test_cut_utf8_codepoint_does_not_form_a_valid_witness():
    fix = fixture()
    fix[0]["literals"]["subject"] = {"source_ref": SOURCE, "representation": "original",
        "start": 1, "end": 2, "quote": "µ"}
    check_error(fix, "source_span_utf8_boundary_required")


def test_invalid_interpretation_witness_is_not_merely_counted():
    fix = fixture()
    fix[0]["interpretation_witnesses"][0]["quote"] = "not in source"
    check_error(fix, "source_quote_mismatch")


@pytest.mark.parametrize("change,code", [
    (lambda a: a.update(numerical_value=123), "closed_fields_required"),
    (lambda a: a.pop("data_source_ref"), "closed_fields_required"),
    (lambda a: a.update(source_ref=None), "nonempty_source_token_required"),
    (lambda a: a.update(data_source_ref=""), "nonempty_source_token_required"),
    (lambda a: a.update(source_kind=[]), "unsupported_source_kind"),
    (lambda a: a.update(source_kind="paper_grade"), "unsupported_source_kind"),
    (lambda a: a.update(literals=[]), "closed_fields_required"),
    (lambda a: a["literals"].pop("partner"), "closed_fields_required"),
    (lambda a: a.update(interpretation_witnesses=None), "array_required"),
])
def test_selected_arguments_are_closed_and_do_not_accept_scientific_numbers(change, code):
    fix = fixture()
    change(fix[0])
    check_error(fix, code)


@pytest.mark.parametrize("raw,code", [
    (b"\xff", "malformed_partner_selection_source"),
    (b"{", "malformed_partner_selection_source"),
    (b"null", "closed_fields_required"),
    (b"[]", "closed_fields_required"),
    (b"{}", "closed_fields_required"),
    (b'{"version":"old","inputs":{}}', "unsupported_partner_selection_version"),
    (b'{"version":"literature_partner_selection_v1","inputs":{},"extra":1}', "closed_fields_required"),
    (b'{"version":"literature_partner_selection_v1","version":"again","inputs":{}}', "duplicate_json_key"),
    (b'{"version":"literature_partner_selection_v1","inputs":{"a":1,"a":2}}', "duplicate_json_key"),
])
def test_malformed_retained_source_and_nested_duplicate_keys(raw, code):
    fix = fixture()
    fix[2][DATA]["content"] = raw
    check_error(fix, code)


@pytest.mark.parametrize("token,code", [
    ("NaN", "finite_number_required"), ("Infinity", "finite_number_required"),
    ("-Infinity", "finite_number_required"), ("1e400", "finite_number_required"),
    ("1e-4000", "numerical_model_range"), ("true", "finite_number_required"),
])
def test_nonfinite_overflow_underflow_and_boolean_numbers_never_silently_change(token, code):
    fix = fixture()
    fix[2][DATA]["content"] = fix[2][DATA]["content"].replace(b'"value": 100', b'"value": ' + token.encode(), 1)
    check_error(fix, code)


def test_calculator_specific_failure_is_preserved():
    fix = fixture()
    fix[1]["inputs"]["arms"]["reference"]["conditions"]["factors"] *= 2
    retain(fix)
    check_error(fix, "duplicate_condition_factor")


@pytest.mark.parametrize("bad_result,code", [
    ({"artifact_ref": "artifact_a", "content": bytearray(b"binary")}, "source_bytes_required"),
    ({"artifact_ref": None, "content": b"binary"}, "nonempty_source_token_required"),
    ({"artifact_ref": "artifact_a", "content": b"binary", "extra": 1}, "closed_fields_required"),
])
def test_callback_source_contracts_are_checked(bad_result, code):
    fix = fixture()
    fix[2][SOURCE] = bad_result
    check_error(fix, code)


def test_callback_error_propagates_without_replacement_or_reacquisition():
    fix = fixture()
    error = ExperimentalContractError("source_not_received", "source_ref")
    calls = []

    def fail(reference, representation):
        calls.append((reference, representation))
        raise error

    with pytest.raises(ExperimentalContractError) as caught:
        reader.read_partner_inputs(fix[0], read_source=fail)
    assert caught.value is error
    assert calls == [(SOURCE, "original")]


def test_argument_schema_matches_selected_operands_and_returns_independent_copies():
    fix = fixture()
    schema = reader.partner_population_schema()
    validate_schema(fix[0], schema)
    assert set(schema["properties"]) == set(fix[0])
    assert schema["additionalProperties"] is False
    schema["properties"]["literals"]["properties"]["subject"] = {}
    assert reader.partner_population_schema()["properties"]["literals"]["properties"]["subject"] != {}
    for field, value in (("rate", 10), ("source_ref", None)):
        args = deepcopy(fix[0])
        args[field] = value
        with pytest.raises(ContractError):
            validate_schema(args, reader.partner_population_schema())
