"""Native-span population, with supplied synthetic experimental meanings."""
from copy import deepcopy
from fractions import Fraction
import json

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode import literature_partner_native_inputs as reader


ROOT, DATA = ("source_" + str(i) * 24 for i in (1, 2))


def fixture(*, reference="0.1", omitted="0.02", addback="0.09", unit="nmol/min/mg",
            spreads=("0.01", "0.002", "0.009"), spread_units=(None, None, None), root_binary=True):
    def spread_text(index):
        return spreads[index] + (" " + spread_units[index] if spread_units[index] else "")
    text = ("µ SubjectS with PartnerP measures product formation; normalized per mg SubjectS. "
        "Nitrogen glutamine; alternative ammonium. Temperature 37 degC and pH 8. "
        "Condition panel complete. SD denotes reported standard deviation. "
        "SEM denotes reported standard error. CI denotes reported confidence halfwidth.\n"
        f"measurement_W: {reference} {unit} ± {spread_text(0)}.\n"
        f"measurement_O: {omitted} {unit} ± {spread_text(1)}.\n"
        f"measurement_A: {addback} {unit} ± {spread_text(2)}.\n")
    raw = text.encode()
    payloads = {ROOT: {"artifact_ref": "artifact_" + "1" * 24,
        "content": b"\xff\x00binary source" if root_binary else raw},
        DATA: {"artifact_ref": "artifact_" + "2" * 24, "content": raw}}
    calls = []

    def read_source(ref, representation):
        calls.append((ref, representation))
        return payloads[ref]

    def witness(quote, *, start_at=0):
        start = raw.index(quote.encode(), start_at)
        return {"source_ref": DATA, "representation": "original", "start": start,
            "end": start + len(quote.encode()), "quote": quote}

    def number(token, *, start_at=0):
        selected = witness(token, start_at=start_at)
        return {"witness": selected, "number_start": 0, "number_end": len(token)}

    arms = {}
    for index, (role, suffix, token, spread) in enumerate((("reference", "W", reference, spreads[0]),
            ("omitted", "O", omitted.lstrip("<≤="), spreads[1]),
            ("addback", "A", addback, spreads[2]))):
        at = raw.index(("measurement_" + suffix).encode())
        arms[role] = {"subject": witness("SubjectS"), "partner": witness("PartnerP"),
            "endpoint": witness("product formation"), "normalization": witness("per mg SubjectS"),
            "partner_state": "absent" if role == "omitted" else "present",
            "conditions": {"coverage": "complete", "factors": [
                {"factor": "nitrogen_source", "level": {"kind": "literal", "witness": witness("glutamine")}},
                {"factor": "temperature", "level": {"kind": "number", "selector": number("37"),
                    "unit_witness": witness("degC")}},
                {"factor": "pH", "level": {"kind": "number", "selector": number("8"), "unit_witness": None}}]},
            "measurement_identity": witness("measurement_" + suffix), "origin": "synthetic",
            "rate": {"value": number(token, start_at=at), "unit": witness(unit, start_at=at),
                "spread": {"kind": "unspecified", "magnitude": number(spread, start_at=at),
                    "unit": witness(spread_units[index], start_at=raw.index(spread.encode(), at))
                        if spread_units[index] else None, "witnesses": []}}}
    args = {"source_ref": ROOT, "data_source_ref": DATA, "source_kind": "synthetic_fixture",
        "literals": dict.fromkeys(reader.LITERAL_FIELDS),
        "interpretation_witnesses": [witness("Condition panel complete.")],
        "input_mode": "native_source_spans", "arms": arms}
    args["literals"].update(subject=witness("SubjectS"), partner=witness("PartnerP"),
        endpoint=witness("product formation"), normalization=witness("per mg SubjectS"))
    return args, payloads, calls, read_source, witness, number


def read(fix):
    return reader.read_partner_native_inputs(fix[0], read_source=fix[3])


def error(fix, code=None):
    with pytest.raises(ExperimentalContractError) as caught:
        read(fix)
    if code is not None:
        assert caught.value.code == code
    return caught.value


def test_native_points_populate_the_existing_sheet_with_exact_conversion_and_no_json_source(monkeypatch):
    fix = fixture()
    original = deepcopy((fix[0], fix[1]))
    calls = []
    calculate = reader.populate_partner_components

    def once(inputs):
        calls.append(deepcopy(inputs))
        return calculate(inputs)

    monkeypatch.setattr(reader, "populate_partner_components", once)
    out = read(fix)
    assert out["version"] == reader.VERSION
    assert set(out) == {"version", "arguments", "sources", "literals", "interpretations",
                        "recipe", "calculation", "cells", "native_evidence"}
    assert len(calls) == 1 and calls[0] == out["recipe"]["inputs"]
    assert [out["cells"][c]["value"] for c in reader.COMPONENTS] == [100, 20, 90, 80, .8, 70, .875, .7]
    assert out["sources"] == [ROOT, DATA]
    assert fix[2] == [(ROOT, "original"), (DATA, "original")]
    validate_schema(out["native_evidence"], reader.native_evidence_schema())
    assert (fix[0], fix[1]) == original
    json.dumps(out, allow_nan=False)
    native = out["native_evidence"]["reference"]["rate"]
    assert native["value"]["raw_number"] == "0.1" and native["value"]["value"] == .1
    assert native["unit"]["raw_unit"] == "nmol/min/mg"
    assert native["unit"]["canonical_unit"] == "pmol/min/mg"
    assert native["canonical_value"] == 100 and native["canonical_spread"] == 10
    assert out["calculation"]["inputs"]["arms"]["reference"]["measurement"]["spread"] == {
        "kind": "unspecified", "magnitude": 10}
    assert out["calculation"]["inputs"]["arms"]["reference"]["conditions"]["factors"] == [
        {"factor": "nitrogen_source", "level": "glutamine", "unit": "source_literal"},
        {"factor": "temperature", "level": 37, "unit": "degC"},
        {"factor": "pH", "level": 8, "unit": "dimensionless"}]


@pytest.mark.parametrize("prefix,relation", [("<", "lt"), ("≤", "le"), ("<=", "le")])
def test_native_upper_limit_cannot_become_zero_or_a_point(prefix, relation):
    fix = fixture(omitted=prefix + "0.005")
    out = read(fix)
    assert out["native_evidence"]["omitted"]["rate"]["value"]["relation"] == relation
    omitted = out["cells"]["omitted_rate"]
    assert omitted["value"] is None and (omitted["lower"], omitted["upper"]) == (0, 5)
    restored = out["cells"]["addback_fraction"]
    assert restored["value"] is None and restored["status"] == "bounded"
    assert Fraction(restored["lower"]) <= Fraction(85, 95)
    assert Fraction(restored["upper"]) >= Fraction(9, 10)


def test_absolute_spread_uses_its_own_source_unit_and_preserves_both_native_scales():
    fix = fixture(spreads=("5", "0.002", "0.009"),
                  spread_units=("pmol/min/mg", None, None))
    out = read(fix)
    native = out["native_evidence"]["reference"]["rate"]
    assert native["unit"]["raw_unit"] == "nmol/min/mg"
    assert native["unit"]["multiplier"] == 1000
    assert native["spread"]["unit"]["raw_unit"] == "pmol/min/mg"
    assert native["spread"]["unit"]["multiplier"] == 1
    assert native["canonical_value"] == 100 and native["canonical_spread"] == 5
    assert out["recipe"]["inputs"]["arms"]["reference"]["measurement"]["spread"]["magnitude"] == 5
    validate_schema(out["native_evidence"], reader.native_evidence_schema())


def test_a_printed_different_absolute_spread_unit_cannot_be_ignored(monkeypatch):
    fix = fixture(spreads=("5", "0.002", "0.009"),
                  spread_units=("pmol/min/mg", None, None))
    fix[0]["arms"]["reference"]["rate"]["spread"]["unit"] = None
    monkeypatch.setattr(reader, "populate_partner_components", lambda _: pytest.fail("wrong spread unit reached core"))
    caught = error(fix)
    assert "spread" in caught.code


def test_explicit_common_spread_unit_may_use_the_declared_common_unit_association():
    fix = fixture(spread_units=("nmol/min/mg", None, None))
    fix[0]["arms"]["reference"]["rate"]["spread"]["unit"] = None
    out = read(fix)
    native = out["native_evidence"]["reference"]["rate"]
    assert native["spread"]["unit"] is None and native["canonical_spread"] == 10


def test_absolute_spread_dimension_must_equal_the_rate_dimension():
    fix = fixture(spread_units=("uM/min", None, None))
    error(fix, "spread_rate_dimension_mismatch")


@pytest.mark.parametrize("printed_unit", ["%", "percent", "per cent"])
def test_relative_error_is_not_an_absolute_rate_spread(printed_unit, monkeypatch):
    fix = fixture(spreads=("5", "0.002", "0.009"),
                  spread_units=(printed_unit, None, None))
    fix[0]["arms"]["reference"]["rate"]["spread"]["unit"] = None
    monkeypatch.setattr(reader, "populate_partner_components", lambda _: pytest.fail("relative error reached core"))
    caught = error(fix)
    assert "spread" in caught.code


def test_same_canonical_physical_witness_blocks_reused_baseline_addback():
    fix = fixture(addback="0.1")
    fix[0]["arms"]["addback"]["measurement_identity"] = deepcopy(fix[0]["arms"]["reference"]["measurement_identity"])
    out = read(fix)
    arms = out["calculation"]["inputs"]["arms"]
    assert arms["reference"]["measurement"]["measurement_id"] == arms["addback"]["measurement"]["measurement_id"]
    assert out["cells"]["partner_loss_fraction"]["value"] == .8
    for name in ("addback_gain", "addback_fraction", "restored_reference_fraction"):
        assert out["cells"][name]["unavailable_reason"] == "role_measurement_not_distinct"


def test_numeric_spans_do_not_invent_physical_measurement_identity():
    fix = fixture()
    fix[0]["arms"]["reference"]["measurement_identity"] = None
    out = read(fix)
    assert out["calculation"]["inputs"]["arms"]["reference"]["measurement"]["measurement_id"] is None
    assert out["cells"]["reference_rate"]["value"] == 100
    assert out["cells"]["partner_loss"]["unavailable_reason"] == "measurement_identity_unreported"
    assert out["cells"]["addback_gain"]["value"] == 70


def test_different_canonical_entity_witness_remains_a_different_identity():
    fix = fixture()
    fix[0]["arms"]["omitted"]["subject"] = fix[4]("PartnerP")
    out = read(fix)
    assert out["cells"]["partner_loss"]["unavailable_reason"] == "subject_mismatch"


def test_source_condition_difference_and_missing_mass_identity_keep_native_values():
    fix = fixture()
    fix[0]["source_kind"] = "primary_source"
    for arm in fix[0]["arms"].values():
        arm["origin"] = "reported"
        arm["normalization"] = None
        arm["conditions"]["coverage"] = "partial"
    fix[0]["arms"]["omitted"]["conditions"]["factors"][0]["level"]["witness"] = fix[4]("ammonium")
    fix[0]["arms"]["addback"] = None
    out = read(fix)
    assert [out["cells"][k]["value"] for k in reader.COMPONENTS] == [100, 20, None, None, None, None, None, None]
    assert out["calculation"]["comparison_checks"]["reference_omitted"] == {
        "status": "different", "differing_factors": ["nitrogen_source"],
        "unavailable_reason": "nonpartner_conditions_differ"}
    assert out["cells"]["addback_rate"]["origin"] is None


def test_supplied_pdx_operands_remain_native_points_with_untyped_spreads_and_unavailable_loss():
    # Supplied source-case operands in an explicitly controlled text fixture;
    # this test acquires/reads no paper or paper-specific evidence packet.
    fix = fixture(reference="774", omitted="284", unit="pmol min-1 mg-1",
                  spreads=("58", "33", "0.009"))
    fix[0]["source_kind"] = "retained_extraction"
    for arm in fix[0]["arms"].values():
        arm["origin"] = "reported"
        arm["normalization"] = None
        arm["measurement_identity"] = None
        arm["conditions"]["coverage"] = "partial"
    fix[0]["arms"]["omitted"]["conditions"]["factors"][0]["level"]["witness"] = fix[4]("ammonium")
    fix[0]["arms"]["addback"] = None
    out = read(fix)
    assert [out["cells"][k]["value"] for k in reader.COMPONENTS] == [774, 284, None, None, None, None, None, None]
    assert out["native_evidence"]["reference"]["rate"]["value"]["raw_number"] == "774"
    assert out["native_evidence"]["omitted"]["rate"]["spread"]["magnitude"]["raw_number"] == "33"
    assert out["recipe"]["inputs"]["arms"]["reference"]["measurement"]["spread"] == {
        "kind": "unspecified", "magnitude": 58}
    assert out["cells"]["partner_loss"]["unavailable_reason"] == "nonpartner_conditions_differ"


def test_unknown_rate_condition_and_entity_remain_unknown():
    fix = fixture()
    ref = fix[0]["arms"]["reference"]
    ref["rate"] = None
    ref["subject"] = None
    ref["conditions"]["coverage"] = "partial"
    ref["conditions"]["factors"][0]["level"] = None
    out = read(fix)
    native = out["native_evidence"]["reference"]
    core = out["recipe"]["inputs"]["arms"]["reference"]
    assert native["rate"] is native["subject"] is None
    assert core["subject_ref"] is None and core["unit"] == "unreported"
    assert core["conditions"]["factors"][0] == {"factor": "nitrogen_source", "level": None, "unit": "unreported"}
    assert core["measurement"]["status"] == "unreported"
    assert out["cells"]["reference_rate"]["value"] is None


@pytest.mark.parametrize("kind,basis", [("SD", "SD denotes reported standard deviation."),
    ("SEM", "SEM denotes reported standard error."), ("CI", "CI denotes reported confidence halfwidth.")])
def test_reported_spread_semantics_need_a_basis_and_are_not_sampling_intervals(kind, basis):
    fix = fixture()
    spread = fix[0]["arms"]["reference"]["rate"]["spread"]
    spread.update(kind=kind, witnesses=[fix[4](basis)])
    out = read(fix)
    assert out["recipe"]["inputs"]["arms"]["reference"]["measurement"]["spread"] == {"kind": kind, "magnitude": 10}
    assert out["cells"]["reference_rate"]["lower"] == out["cells"]["reference_rate"]["upper"] == 100
    spread["witnesses"] = []
    error(fix, "spread_basis_witness_required")


def test_no_spread_and_all_missing_arms_preserve_custody_without_invented_values():
    fix = fixture()
    fix[0]["arms"] = dict.fromkeys(reader.ROLES)
    fix[0]["interpretation_witnesses"] = []
    out = read(fix)
    assert out["sources"] == [ROOT, DATA]
    assert out["native_evidence"] == dict.fromkeys(reader.ROLES)
    assert all(c["value"] is None for c in out["cells"].values())


@pytest.mark.parametrize("change,code", [
    (lambda a: a.update(value=123), "closed_fields_required"),
    (lambda a: a.update(input_mode="prepared_json"), "unsupported_partner_input_mode"),
    (lambda a: a.update(source_kind=[]), "unsupported_native_value"),
    (lambda a: a.update(source_ref=None), "nonempty_source_token_required"),
    (lambda a: a.update(interpretation_witnesses=None), "array_required"),
    (lambda a: a["arms"]["reference"].update(rate_value=9), "closed_fields_required"),
    (lambda a: a["arms"]["reference"].update(origin="reported"), "synthetic_origin_required"),
    (lambda a: a["arms"]["reference"].update(partner_state=[]), "unsupported_native_value"),
    (lambda a: a["arms"]["reference"]["conditions"]["factors"][0].update(factor="free form words"), "condition_factor_identifier_required"),
    (lambda a: a["arms"]["reference"]["conditions"]["factors"][0].update(level={"kind":"invented"}), "unsupported_condition_level"),
    (lambda a: a["arms"]["reference"]["conditions"]["factors"].append(deepcopy(a["arms"]["reference"]["conditions"]["factors"][0])), "duplicate_condition_factor"),
    (lambda a: a["arms"]["reference"]["rate"]["spread"].update(magnitude=None), "spread_kind_magnitude_mismatch"),
    (lambda a: a["arms"]["reference"]["rate"]["spread"].update(witnesses=None), "array_required"),
])
def test_closed_arguments_and_specific_relationship_errors(change, code):
    fix = fixture()
    change(fix[0])
    error(fix, code)


def test_complete_condition_coverage_requires_actual_interpretation_witness():
    fix = fixture()
    fix[0]["interpretation_witnesses"] = []
    error(fix, "interpretation_witness_required")


def test_source_errors_and_quote_errors_remain_repairable_and_do_not_call_core(monkeypatch):
    fix = fixture()
    fix[0]["arms"]["reference"]["subject"]["quote"] = "altered"
    monkeypatch.setattr(reader, "populate_partner_components", lambda _: pytest.fail("invalid source reached calculator"))
    error(fix, "source_quote_mismatch")
    broken = ExperimentalContractError("source_not_received", "source_ref")
    def missing(*args):
        raise broken
    with pytest.raises(ExperimentalContractError) as caught:
        reader.read_partner_native_inputs(fixture()[0], read_source=missing)
    assert caught.value is broken


def test_schemas_are_closed_independent_and_source_numeric_arguments_are_rejected():
    fix = fixture()
    schema = reader.partner_source_population_schema()
    validate_schema(fix[0], schema)
    schema["properties"]["arms"]["properties"]["reference"] = {}
    assert reader.partner_source_population_schema()["properties"]["arms"]["properties"]["reference"] != {}
    bad = deepcopy(fix[0])
    bad["arms"]["reference"]["rate"]["value"] = 100
    with pytest.raises(ContractError):
        validate_schema(bad, reader.partner_source_population_schema())
    out = read(fix)
    validate_schema(out["native_evidence"], reader.native_evidence_schema())
    out["native_evidence"]["reference"]["rate"]["value"]["value"] = "forged"
    with pytest.raises(ContractError):
        validate_schema(out["native_evidence"], reader.native_evidence_schema())


def test_returned_arguments_evidence_core_and_cells_have_no_mutation_aliases():
    fix = fixture()
    out = read(fix)
    out["native_evidence"]["reference"]["rate"]["canonical_value"] = -1
    out["recipe"]["inputs"]["arms"]["reference"]["measurement"]["value"] = -2
    out["cells"]["reference_rate"]["value"] = -3
    assert out["calculation"]["inputs"]["arms"]["reference"]["measurement"]["value"] == 100
    assert out["calculation"]["cells"]["reference_rate"]["value"] == 100
    assert fix[0]["arms"]["reference"]["rate"]["value"]["witness"]["quote"] == "0.1"
