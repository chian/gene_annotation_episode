"""Synthetic source contrasts only; no primary literature measurements."""
from copy import deepcopy
import json

import numpy as np
import pytest

from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_optical_calculations import calculate_nadh_optical_rate
from gene_annotation_episode.literature_optical_inputs import (
    LEXICAL_DEPENDENCY, PRIMITIVE_ORDER, optical_arguments_schema, read_optical_rate_operands,
)


SOURCE = "source_" + "1" * 24
COV_SOURCE = "source_" + "2" * 24
ARTIFACT = "artifact_" + "1" * 24
TEXT = ("Synthetic sample NADH slope -0.012 AU/min; blank -0.002 AU/min; "
        "epsilon 5000 M^-1 cm^-1; path 10 mm; wavelength 340 nm. "
        "Matched no-reaction background, same endpoint and interval, supported initial rate. "
        "A single unnamed preparation of construct X.")


def witness(text, quote, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"source_ref": SOURCE, "representation": "original", "start": len(text[:start].encode()),
        "end": len(text[:start + len(quote)].encode()), "quote": quote}


def meaning(value, text, quote=None):
    return {"value": value, "witnesses": [] if value == "unknown" else [witness(text, quote or text)]}


def quantity(text, quote, number, unit, occurrence=0):
    w = witness(text, quote, occurrence)
    start = quote.index(number)
    unit_occurrence = text[:text.index(quote)].count(unit) if unit else 0
    return {"measurement_identity": None, "condition": None, "measured_entity": None, "interval": None,
        "measurement": {"number": {"witness": w, "number_start": start, "number_end": start + len(number)},
            "unit": witness(text, unit, unit_occurrence) if unit else None},
        "qualification": meaning("reported_point", text, quote)}


def fixture(text=TEXT, sample=("-0.012 AU/min", "-0.012", "AU/min"),
            blank=("-0.002 AU/min", "-0.002", "AU/min"),
            epsilon=("5000 M^-1 cm^-1", "5000", "M^-1 cm^-1"),
            path=("10 mm", "10", "mm"), wavelength=("340 nm", "340", "nm")):
    args = {"source_ref": SOURCE, "source_kind": "synthetic_fixture",
        "molecule": None, "construct": None, "preparation": None, "condition": None, "measured_entity": None,
        "signal_kind": meaning("absorbance_slope", text),
        "signals": {"sample": quantity(text, *sample) if sample else None,
                    "blank": quantity(text, *blank) if blank else None},
        "calibration": {"epsilon": quantity(text, *epsilon) if epsilon else None,
            "path_length": quantity(text, *path) if path else None,
            "wavelength": quantity(text, *wavelength) if wavelength else None},
        "relation": meaning("applicable_extinction_relation", text),
        "blank_role": meaning("matched_no_reaction_background", text),
        "same_endpoint": meaning("same", text), "matched_window": meaning("same", text),
        "rate_window": meaning("source_supported_rate_interval", text), "covariance_source_ref": None}
    sources = {SOURCE: {"artifact_ref": ARTIFACT, "content": text.encode()}}
    calls = []
    def reader(ref, representation):
        calls.append((ref, representation))
        return deepcopy(sources[ref])
    return args, sources, reader, calls


def result(args, reader):
    return read_optical_rate_operands(args, read_source=reader)


def rows(extraction):
    return [extraction["signals"]["sample"], extraction["signals"]["blank"],
            extraction["calibration"]["epsilon"], extraction["calibration"]["path_length"]]


def add_covariance(args, sources, reader, matrix=None, status="known"):
    extraction = result(args, reader)
    owners = rows(extraction)
    # Source native units have epsilon scale .001 and path scale .1.
    if matrix is None:
        matrix = [[1e-8, 5e-9, 0, 0], [5e-9, 1e-8, 0, 0],
                  [0, 0, 10000, 0], [0, 0, 0, .01]]
    data = {"version": "a105_optical_covariance_v1", "primitive_order": list(PRIMITIVE_ORDER),
        "primitive_measurement_keys": [r["measurement_key"] for r in owners],
        "primitive_physical_observation_keys": [r["physical_observation_key"] for r in owners],
        "primitive_owner_keys": [r["owner_key"] for r in owners],
        "primitive_units": [r["unit"]["raw_unit"] for r in owners], "covariance": matrix,
        "origin": "synthetic", "covariance_status": status}
    sources[COV_SOURCE] = {"artifact_ref": "artifact_" + "2" * 24, "content": json.dumps(data).encode()}
    args["covariance_source_ref"] = COV_SOURCE
    return data


def test_source_bound_conversion_supplies_existing_rate_and_variance_without_sheet_execution():
    args, sources, reader, calls = fixture()
    data = add_covariance(args, sources, reader)
    calls.clear()
    extraction = result(args, reader)
    operands = extraction["calculation_inputs"]
    assert [operands[k] for k in PRIMITIVE_ORDER] == [-.012, -.002, 5., 1.]
    assert np.array(operands["covariance"]) == pytest.approx(np.array([
        [1e-8, 5e-9, 0, 0], [5e-9, 1e-8, 0, 0], [0, 0, .01, 0], [0, 0, 0, .0001]]))
    assert extraction["covariance_source"]["data"] == data
    assert extraction["lexical_dependency"] == LEXICAL_DEPENDENCY
    assert calls == [(SOURCE, "original"), (COV_SOURCE, "original")]
    cells = calculate_nadh_optical_rate(operands)
    assert cells["net_depletion_rate"]["value"] == pytest.approx(2.)
    assert cells["net_depletion_variance"]["value"] == pytest.approx(.0024)
    assert extraction["calibration"]["wavelength"]["value"] == 340
    assert "wavelength" not in operands
    assert not any(extraction["input_unavailable_reasons"].values())


@pytest.mark.parametrize("source_kind,source_origin", [("primary_source", "reported"),
    ("retained_extraction", "derived"), ("synthetic_fixture", "synthetic")])
def test_origin_preserves_actual_source_kind_and_conversion(source_kind, source_origin):
    args, _, reader, _ = fixture()
    args["source_kind"] = source_kind
    extraction = result(args, reader)
    assert extraction["signals"]["sample"]["source_origin"] == source_origin
    assert extraction["signals"]["sample"]["origin"] == source_origin
    assert extraction["calibration"]["epsilon"]["source_origin"] == source_origin
    assert extraction["calibration"]["epsilon"]["origin"] == "derived"


@pytest.mark.parametrize("raw,number,unit,value", [
    ("-0.0002 AU/s", "-0.0002", "AU/s", -.012),
    ("-0.2 mAU/s", "-0.2", "mAU/s", -.012),
    ("-12 mAU min−1", "-12", "mAU min−1", -.012),
    ("−0.012 absorbance min⁻¹", "−0.012", "absorbance min⁻¹", -.012),
    ("-0.012 AU min<sup>−1</sup>", "-0.012", "AU min<sup>−1</sup>", -.012),
])
def test_optical_slope_units_preserve_case_and_source_inverse_exponents(raw, number, unit, value):
    text = TEXT.replace("-0.012 AU/min", raw)
    args, _, reader, _ = fixture(text, sample=(raw, number, unit))
    extraction = result(args, reader)
    assert extraction["calculation_inputs"]["sample_slope"] == value
    assert extraction["signals"]["sample"]["unit"]["raw_unit"] == unit
    assert calculate_nadh_optical_rate(extraction["calculation_inputs"])["net_depletion_rate"]["value"] == pytest.approx(2.)


@pytest.mark.parametrize("raw,number,unit,expected", [
    ("5 mM−1cm−1", "5", "mM−1cm−1", 5.),
    ("5000 L mol<sup>−1</sup> cm<sup>−1</sup>", "5000", "L mol<sup>−1</sup> cm<sup>−1</sup>", 5.),
    ("0.005 μM^-1 cm^-1", "0.005", "μM^-1 cm^-1", 5.),
    ("5000 1/(M cm)", "5000", "1/(M cm)", 5.),
])
def test_finite_extinction_grammar_and_micro_utf8_byte_custody(raw, number, unit, expected):
    text = "µ synthetic context. " + TEXT.replace("5000 M^-1 cm^-1", raw)
    args, _, reader, _ = fixture(text, epsilon=(raw, number, unit))
    extraction = result(args, reader)
    epsilon = extraction["calibration"]["epsilon"]
    assert epsilon["value"] == expected
    assert epsilon["number"]["selector"]["witness"]["start"] != text.index(raw)


@pytest.mark.parametrize("kind", ["absorbance_difference", "static_absorbance", "unknown"])
def test_static_difference_unknown_and_even_claimed_rate_window_cannot_supply_slope(kind):
    args, _, reader, _ = fixture()
    args["signal_kind"] = meaning(kind, TEXT)
    extraction = result(args, reader)
    assert extraction["signals"]["sample"]["value"] == -.012
    assert extraction["calculation_inputs"]["sample_slope"] is None
    assert extraction["calculation_inputs"]["rate_window"] == "source_supported_rate_interval"
    assert calculate_nadh_optical_rate(extraction["calculation_inputs"])["net_depletion_rate"]["value"] is None


def test_static_units_and_amount_rate_are_retained_without_optical_slope_inference():
    text = TEXT.replace("-0.012 AU/min", "0.12 AU")
    args, _, reader, _ = fixture(text, sample=("0.12 AU", "0.12", "AU"))
    extraction = result(args, reader)
    assert extraction["signals"]["sample"]["value"] == .12
    assert extraction["signals"]["sample"]["unit"]["canonical_unit"] == "absorbance"
    assert "optical_signal_unit_mismatch" in extraction["input_unavailable_reasons"]["sample_slope"]
    text = TEXT.replace("-0.012 AU/min", "12 nmol/min")
    args, _, reader, _ = fixture(text, sample=("12 nmol/min", "12", "nmol/min"))
    extraction = result(args, reader)
    assert extraction["signals"]["sample"]["number"]["value"] == 12
    assert extraction["signals"]["sample"]["value"] is None


@pytest.mark.parametrize("unit", ["MAU/min", "au/min", "OD/min", "A340/min", "min^-1", "dimensionless", "U/mg"])
def test_unsupported_or_wrong_case_units_remain_raw_unknown(unit):
    text = TEXT.replace("-0.012 AU/min", "-0.012 " + unit)
    args, _, reader, _ = fixture(text, sample=("-0.012 " + unit, "-0.012", unit))
    row = result(args, reader)["signals"]["sample"]
    assert row["unit"]["raw_unit"] == unit
    assert row["unit"]["canonical_unit"] is None
    assert row["value"] is None
    assert row["number"]["value"] == -.012


@pytest.mark.parametrize("where,name,primitive", [("signals", "sample", "sample_slope"),
    ("signals", "blank", "blank_slope"), ("calibration", "epsilon", "epsilon"),
    ("calibration", "path_length", "path_length")])
def test_missing_required_field_leaves_partial_other_observations_without_defaults(where, name, primitive):
    args, _, reader, _ = fixture()
    args[where][name] = None
    extraction = result(args, reader)
    assert extraction["calculation_inputs"][primitive] is None
    assert extraction["input_unavailable_reasons"][primitive] == ["source_measurement_unreported"]
    assert calculate_nadh_optical_rate(extraction["calculation_inputs"])["net_depletion_rate"]["value"] is None


def test_epsilon_only_source_does_not_create_rate_or_default_path_blank():
    text = "Synthetic extinction coefficient 5000 M^-1 cm^-1."
    args, _, reader, _ = fixture(text, sample=None, blank=None, path=None, wavelength=None)
    args["signal_kind"] = meaning("unknown", text)
    extraction = result(args, reader)
    assert extraction["calculation_inputs"]["epsilon"] == 5
    assert all(extraction["calculation_inputs"][key] is None for key in ("sample_slope", "blank_slope", "path_length"))


@pytest.mark.parametrize("prefix,relation,approx", [("<", "lt", False), (">=", "ge", False),
    ("approximately ", "point", True), ("about >", "gt", True), ("&lt;", "lt", False)])
def test_actual_lexical_bounds_and_approximation_survive_reported_point(prefix, relation, approx):
    text = TEXT.replace("-0.012 AU/min", prefix + "-0.012 AU/min")
    args, _, reader, _ = fixture(text)
    extraction = result(args, reader)
    row = extraction["signals"]["sample"]
    assert row["number"]["relation"] == relation
    assert row["approximate"] is approx
    assert row["value"] == -.012
    assert extraction["calculation_inputs"]["sample_slope"] is None


@pytest.mark.parametrize("qualification", ["source_qualified_approximate", "unknown", "conflicting"])
def test_nonadjacent_qualified_unknown_and_conflicting_reporting_keep_exact_scalar_unavailable(qualification):
    text = TEXT.replace("epsilon 5000", "an approximate coefficient of 5000")
    args, _, reader, _ = fixture(text)
    q = args["calibration"]["epsilon"]
    q["qualification"] = meaning(qualification, text)
    if qualification == "conflicting":
        q["qualification"]["witnesses"].append(witness(text, "Matched no-reaction background"))
    extraction = result(args, reader)
    assert extraction["calibration"]["epsilon"]["number"]["approximate"] is False
    assert extraction["calculation_inputs"]["epsilon"] is None


@pytest.mark.parametrize("field,value,reason", [("blank_role", "condition_reference", "blank_role_not_background"),
    ("blank_role", "component_omission", "blank_role_not_background"),
    ("relation", "unknown", "optical_relation_unknown"),
    ("same_endpoint", "different", "endpoint_mismatch_or_unknown"),
    ("matched_window", "unknown", "window_mismatch_or_unknown"),
    ("rate_window", "interval_mean_only", "rate_interval_unestablished")])
def test_scientific_meanings_pass_to_existing_calculator_without_unit_inference(field, value, reason):
    args, _, reader, _ = fixture()
    args[field] = meaning(value, TEXT)
    extraction = result(args, reader)
    assert extraction["calculation_inputs"][field] == value
    assert calculate_nadh_optical_rate(extraction["calculation_inputs"])["net_depletion_rate"]["unavailable_reason"] == reason


def test_known_and_conflicting_meanings_require_real_distinct_custody_witnesses():
    args, _, reader, _ = fixture()
    args["relation"]["witnesses"] = []
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        result(args, reader)
    args["relation"] = meaning("conflicting", TEXT)
    args["relation"]["witnesses"] *= 2
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        result(args, reader)
    args["relation"]["witnesses"].append(witness(TEXT, "Matched no-reaction background"))
    assert result(args, reader)["relation"]["value"] == "conflicting"


@pytest.mark.parametrize("replacement,quote,number,unit,code", [
    ("-10.012 AU/min", "0.012 AU/min", "0.012", "AU/min", "partial_source_numeric_token"),
    ("-0.012e2 AU/min", "-0.012 AU/min", "-0.012", "AU/min", "source_quote_mismatch"),
    ("1/-0.012 AU/min", "-0.012 AU/min", "-0.012", "AU/min", "source_arithmetic_expression_unsupported"),
    ("-0.012 × 10 AU/min", "-0.012 × 10 AU/min", "-0.012", "AU/min", "source_arithmetic_expression_unsupported"),
    ("-0.012 to 1 AU/min", "-0.012 to 1 AU/min", "-0.012", "AU/min", "interval_source_number_unsupported"),
    ("-0.012 AU/min/mg", "-0.012 AU/min/mg", "-0.012", "AU/min", "partial_source_optical_unit"),
    ("-0.012 AU/min per mg", "-0.012 AU/min per mg", "-0.012", "AU/min", "partial_source_optical_unit"),
])
def test_partial_arithmetic_range_or_hidden_unit_continuation_cannot_pass(replacement, quote, number, unit, code):
    text = TEXT.replace("-0.012 AU/min", replacement)
    # One malformed-source case intentionally nominates nonexistent bytes.
    if code == "source_quote_mismatch":
        args, sources, reader, _ = fixture()
        sources[SOURCE]["content"] = text.encode()
    else:
        args, _, reader, _ = fixture(text, sample=(quote, number, unit))
    with pytest.raises(ExperimentalContractError, match=code):
        result(args, reader)


def test_omitted_units_stay_unknown_and_remote_units_cannot_override_printed_physics():
    args, _, reader, _ = fixture()
    args["signals"]["sample"]["measurement"]["unit"] = None
    extraction = result(args, reader)
    assert extraction["signals"]["sample"]["number"]["value"] == -.012
    assert extraction["calculation_inputs"]["sample_slope"] is None
    text = TEXT.replace("-0.012 AU/min", "-0.012 nmol/min")
    args, _, reader, _ = fixture(text, sample=("-0.012 nmol/min", "-0.012", "AU/min"))
    with pytest.raises(ExperimentalContractError, match="unsupported_explicit_optical_unit"):
        result(args, reader)


def test_html_structural_fields_bound_context_and_br_remains_inline():
    text = "<table><tr><td>-0.012</td><td>unrelated 1/</td><td>-0.002</td></tr></table>" + TEXT[TEXT.index("epsilon"):]
    text += "<p>AU/min</p>"
    args, _, reader, _ = fixture(text, sample=("-0.012", "-0.012", "AU/min"), blank=("-0.002", "-0.002", "AU/min"))
    assert result(args, reader)["calculation_inputs"]["sample_slope"] == -.012
    text = TEXT.replace("-0.012 AU/min", "1/<br/>-0.012 AU/min")
    args, _, reader, _ = fixture(text)
    with pytest.raises(ExperimentalContractError, match="source_arithmetic_expression_unsupported"):
        result(args, reader)


def test_same_token_and_original_text_alias_share_local_ref_but_equal_values_do_not():
    args, _, reader, _ = fixture()
    args["signals"]["blank"] = deepcopy(args["signals"]["sample"])
    args["signals"]["blank"]["measurement"]["number"]["witness"]["representation"] = "text"
    extraction = result(args, reader)
    refs = extraction["calculation_inputs"]["primitive_observation_refs"]
    assert refs[0] == refs[1]
    assert extraction["signals"]["sample"]["owner_key"] != extraction["signals"]["blank"]["owner_key"]
    text = TEXT.replace("-0.002", "-0.012")
    args, _, reader, _ = fixture(text, blank=("-0.012 AU/min", "-0.012", "AU/min"))
    # Nominate the second literal occurrence explicitly.
    args["signals"]["blank"]["measurement"]["number"]["witness"] = witness(text, "-0.012 AU/min", 1)
    extraction = result(args, reader)
    refs = extraction["calculation_inputs"]["primitive_observation_refs"]
    assert refs[0] != refs[1]


def test_known_physical_reuse_cannot_have_different_values_or_covariance_rows():
    args, _, reader, _ = fixture()
    for q in args["signals"].values():
        q["measurement_identity"] = witness(TEXT, "A single unnamed preparation")
    with pytest.raises(ExperimentalContractError, match="reused_identity_value_mismatch"):
        result(args, reader)
    args, sources, reader, _ = fixture()
    args["signals"]["blank"] = deepcopy(args["signals"]["sample"])
    add_covariance(args, sources, reader)
    with pytest.raises(ExperimentalContractError, match="reused_identity_covariance_mismatch"):
        result(args, reader)


@pytest.mark.parametrize("field", ["primitive_order", "primitive_measurement_keys", "primitive_physical_observation_keys", "primitive_owner_keys", "primitive_units"])
def test_covariance_exact_order_and_every_owner_and_raw_unit_are_bound(field):
    args, sources, reader, _ = fixture()
    data = add_covariance(args, sources, reader)
    data[field][0] = "wrong"
    sources[COV_SOURCE]["content"] = json.dumps(data).encode()
    with pytest.raises(ExperimentalContractError, match="optical_covariance_owner_or_unit_mismatch"):
        result(args, reader)


def test_changing_scientific_owner_cannot_inherit_covariance():
    args, sources, reader, _ = fixture()
    add_covariance(args, sources, reader)
    args["signals"]["sample"]["measured_entity"] = witness(TEXT, "NADH")
    with pytest.raises(ExperimentalContractError, match="optical_covariance_owner_or_unit_mismatch"):
        result(args, reader)


def test_changing_signal_meaning_cannot_inherit_prior_semantic_owner_covariance():
    args, sources, reader, _ = fixture()
    add_covariance(args, sources, reader)
    args["signal_kind"] = meaning("static_absorbance", TEXT)
    with pytest.raises(ExperimentalContractError, match="optical_covariance_owner_or_unit_mismatch"):
        result(args, reader)


def test_covariance_cross_terms_convert_both_different_operand_scales():
    args, sources, reader, _ = fixture()
    factor = np.array([[.0001, 0, 0, 0], [.00005, .0001, 0, 0],
                       [.02, -.03, .08, 0], [.002, .001, -.001, .009]])
    canonical = factor @ factor.T
    scales = np.array([1., 1., .001, .1])
    native = canonical / np.outer(scales, scales)
    add_covariance(args, sources, reader, matrix=native.tolist())
    extraction = result(args, reader)
    assert np.array(extraction["calculation_inputs"]["covariance"]) == pytest.approx(canonical)
    jacobian = np.array([-200., 200., -.4, -2.])
    expected = jacobian @ canonical @ jacobian
    cells = calculate_nadh_optical_rate(extraction["calculation_inputs"])
    assert cells["net_depletion_variance"]["value"] == pytest.approx(expected)


def test_physical_reuse_across_distinct_tokens_keeps_source_keys_and_cancels_shared_uncertainty():
    text = TEXT.replace("blank -0.002 AU/min", "blank -12 mAU/min")
    args, sources, reader, _ = fixture(text, blank=("-12 mAU/min", "-12", "mAU/min"))
    shared = witness(text, "A single unnamed preparation")
    for row in args["signals"].values():
        row["measurement_identity"] = shared
    matrix = [[1e-8, 1e-5, 0, 0], [1e-5, .01, 0, 0], [0, 0, 10000, 0], [0, 0, 0, .01]]
    add_covariance(args, sources, reader, matrix=matrix)
    extraction = result(args, reader)
    first, second = rows(extraction)[:2]
    assert first["measurement_key"] != second["measurement_key"]
    assert first["physical_observation_key"] == second["physical_observation_key"]
    assert first["owner_key"] != second["owner_key"]
    refs = extraction["calculation_inputs"]["primitive_observation_refs"]
    assert refs[0] == refs[1]
    cells = calculate_nadh_optical_rate(extraction["calculation_inputs"])
    assert cells["net_depletion_rate"]["value"] == 0
    assert cells["net_depletion_variance"]["value"] == 0


def test_reused_physical_identity_cannot_cross_optical_dimensions_even_if_source_unit_unknown():
    args, _, reader, _ = fixture()
    shared = witness(TEXT, "A single unnamed preparation")
    args["signals"]["sample"]["measurement_identity"] = shared
    args["calibration"]["epsilon"]["measurement_identity"] = shared
    args["calibration"]["epsilon"]["measurement"]["unit"] = None
    with pytest.raises(ExperimentalContractError, match="reused_identity_dimension_mismatch"):
        result(args, reader)


def test_unknown_unit_keeps_bound_without_inventing_canonical_threshold():
    text = TEXT.replace("-0.012 AU/min", "<-0.012 arbitrary")
    args, _, reader, _ = fixture(text, sample=("-0.012 arbitrary", "-0.012", "arbitrary"))
    extraction = result(args, reader)
    row = extraction["signals"]["sample"]
    assert row["number"]["relation"] == "lt"
    assert row["number"]["value"] == -.012
    assert row["value"] is None
    assert row["status"] == "unavailable"
    assert extraction["calculation_inputs"]["sample_slope"] is None


def test_shared_header_allows_prose_after_number_without_misreading_word_as_unit_prefix():
    text = TEXT.replace("-0.012 AU/min", "-0.012 measured")
    args, _, reader, _ = fixture(text, sample=("-0.012 measured", "-0.012", "AU/min"))
    assert result(args, reader)["calculation_inputs"]["sample_slope"] == -.012


@pytest.mark.parametrize("status", ["known", "estimated", "unknown"])
def test_covariance_status_is_retained_without_becoming_independence(status):
    args, sources, reader, _ = fixture()
    add_covariance(args, sources, reader, status=status)
    extraction = result(args, reader)
    assert extraction["calculation_inputs"]["covariance_status"] == status
    cells = calculate_nadh_optical_rate(extraction["calculation_inputs"])
    assert cells["net_depletion_rate"]["value"] == pytest.approx(2.)
    assert (cells["net_depletion_variance"]["value"] is None) == (status == "unknown")


@pytest.mark.parametrize("mutation,code", [
    (lambda d: d.update(covariance=[[1]]), "four_by_four_covariance_required"),
    (lambda d: d["covariance"][0].__setitem__(0, True), "finite_number_required"),
    (lambda d: d["covariance"][0].__setitem__(0, -1), "positive_semidefinite_covariance_required"),
    (lambda d: d["covariance"][0].__setitem__(1, 1), "symmetric_covariance_required"),
    (lambda d: d.update(covariance=[[1, 2, 0, 0], [2, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]), "positive_semidefinite_covariance_required"),
])
def test_invalid_matrix_is_a_repairable_error_not_missing_scientific_information(mutation, code):
    args, sources, reader, _ = fixture()
    data = add_covariance(args, sources, reader)
    mutation(data)
    sources[COV_SOURCE]["content"] = json.dumps(data).encode()
    with pytest.raises(ExperimentalContractError, match=code):
        result(args, reader)


@pytest.mark.parametrize("raw,code", [(b'{"version":1,"version":2}', "duplicate_json_key"),
    (b'{"covariance":NaN}', "finite_number_required")])
def test_covariance_json_duplicate_keys_and_nonfinite_literals_reject(raw, code):
    args, sources, reader, _ = fixture()
    args["covariance_source_ref"] = COV_SOURCE
    sources[COV_SOURCE] = {"artifact_ref": "cov", "content": raw}
    with pytest.raises(ExperimentalContractError, match=code):
        result(args, reader)


@pytest.mark.parametrize("number,unit", [("0", "M^-1 cm^-1"), ("-5", "M^-1 cm^-1"),
    ("1e999", "M^-1 cm^-1"), ("1e-999", "M^-1 cm^-1")])
def test_invalid_exact_denominators_and_unrepresentable_literals_are_not_defaults(number, unit):
    text = TEXT.replace("5000 M^-1 cm^-1", number + " " + unit)
    args, _, reader, _ = fixture(text, epsilon=(number + " " + unit, number, unit))
    with pytest.raises(ExperimentalContractError, match="positive_optical_operand_required|numerical_model_range"):
        result(args, reader)


def test_detached_schema_selection_and_extraction_and_source_authorization():
    args, sources, reader, calls = fixture()
    original = deepcopy(args)
    validate_schema(args, optical_arguments_schema())
    schema = optical_arguments_schema()
    schema["properties"].clear()
    assert optical_arguments_schema()["properties"]
    extraction = result(args, reader)
    assert args == original
    assert calls == [(SOURCE, "original")]
    args["relation"]["witnesses"][0]["quote"] = "changed"
    assert extraction["relation"]["witnesses"][0]["quote"] == TEXT
    extraction["signals"]["sample"]["number"]["value"] = 100
    assert extraction["calculation_inputs"]["sample_slope"] == -.012
    sources[SOURCE]["content"] = b"changed"
    assert extraction["signals"]["sample"]["number"]["raw_number"] == "-0.012"


def test_closed_selection_and_failed_custody_are_not_silently_repaired():
    args, _, reader, _ = fixture()
    args["extra"] = "unsupported"
    with pytest.raises(ExperimentalContractError, match="optical_selection_schema_invalid"):
        result(args, reader)
    args.pop("extra")
    args["signals"]["sample"]["measurement"]["number"]["witness"]["quote"] = "forged"
    with pytest.raises(ExperimentalContractError, match="source_quote_mismatch"):
        result(args, reader)
