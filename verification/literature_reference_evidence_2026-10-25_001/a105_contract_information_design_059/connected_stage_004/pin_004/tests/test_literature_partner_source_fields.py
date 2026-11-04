"""Real byte/token boundaries and unit arithmetic, without source interpretation."""
from copy import deepcopy
from fractions import Fraction
import math

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_source_fields import (
    convert_source_number, number_selector_schema, read_source_number, read_source_rate_unit,
    validate_source_spread_unit,
)

SOURCE = "source_" + "a" * 24
ARTIFACT = "artifact_" + "b" * 64


def fixture(text):
    calls = []
    def read(ref, representation):
        calls.append((ref, representation))
        assert ref == SOURCE and representation == "original"
        return {"artifact_ref": ARTIFACT, "content": text.encode()}
    return _Sources(read), calls


def witness(text, quote=None):
    quote = text if quote is None else quote
    start = text.encode().index(quote.encode())
    return {"source_ref": SOURCE, "representation": "original", "start": start,
        "end": start + len(quote.encode()), "quote": quote}


def selector(text, token, *, quote=None):
    selected = witness(text, quote)
    start = selected["quote"].index(token)
    return {"witness": selected, "number_start": start, "number_end": start + len(token)}


def number(text, token, *, role="rate", quote=None):
    sources, _ = fixture(text)
    return read_source_number(selector(text, token, quote=quote), sources=sources, role=role)


def error(code, function, *args, **kwargs):
    with pytest.raises(ExperimentalContractError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


@pytest.mark.parametrize("token,value", [("774", 774), (".005", .005), ("+2.5", 2.5),
    ("1.25e-3", .00125), ("−2", -2), ("0", 0), ("-0", 0)])
def test_complete_native_literal_points(token, value):
    text = "µ source rate: " + token + " pmol/min/mg"
    sources, calls = fixture(text)
    selected = selector(text, token)
    original = deepcopy(selected)
    result = read_source_number(selected, sources=sources, role="rate")
    assert result == {"selector": {**selected, "witness": {**selected["witness"], "artifact_ref": ARTIFACT}},
        "raw_number": token, "value": value, "relation": "point"}
    assert selected == original
    assert calls == [(SOURCE, "original")]
    assert result["selector"]["witness"]["start"] == 0


@pytest.mark.parametrize("prefix,relation", [("<", "lt"), ("<=", "le"), ("≤ ", "le"),
    ("&lt;", "lt"), ("&#60;", "lt"), ("&#x3c;= ", "le"), ("below ", "lt"),
    ("less than ", "lt"), ("less than or equal to ", "le"), ("at most ", "le"),
    ("no more than ", "le"), ("&lt;<italic>", "lt")])
def test_upper_bound_survives_a_witness_starting_after_the_comparator(prefix, relation):
    text = "Rate " + prefix + "0.005</italic> nmol/min/mg"
    result = number(text, "0.005", quote="0.005")
    assert result["relation"] == relation and result["value"] == .005


def test_real_xml_markup_is_not_a_greater_than_comparator():
    assert number("<p><italic>774</italic> pmol/min/mg</p>", "774", quote="774")["relation"] == "point"


@pytest.mark.parametrize("prefix", [">", ">=", "≥", "&gt;", "above ", "greater than ",
    "greater than or equal to ", "at least ", "no less than "])
def test_lower_bounds_are_specific_unsupported_results(prefix):
    error("lower_bound_source_number_unsupported", number, "Rate " + prefix + "5 nmol/min/mg", "5", quote="5")


@pytest.mark.parametrize("prefix", ["~", "≈", "approximately ", "about ", "circa ", "approx. "])
def test_approximation_cannot_be_removed_by_shortening_a_quote(prefix):
    error("approximate_source_number_unsupported", number, "Rate " + prefix + "5 nmol/min/mg", "5", quote="5")


@pytest.mark.parametrize("prefix", ["not less than ", "not below ", "not greater than ",
    "not above ", "not <", "not <=", "not significantly below "])
def test_negated_comparisons_never_turn_into_inverse_upper_limits(prefix):
    error("negated_source_comparator_unsupported", number, "Rate " + prefix + "5", "5", quote="5")


@pytest.mark.parametrize("text,token", [("rate 1–5", "1"), ("rate 1–5", "5"),
    ("rate between 1 and 5", "1"), ("rate between 1 and 5", "5"),
    ("rate range [1,5]", "1"), ("CI: 5", "5")])
def test_interval_members_do_not_become_point_rates(text, token):
    error("interval_source_number_unsupported", number, text, token)


@pytest.mark.parametrize("text,token,code", [("rate 1774", "774", "partial_source_numeric_token"),
    ("rate 1.25e-3", "1.25", "partial_source_numeric_token"),
    ("rate 1.25e-3", "3", "partial_source_numeric_token"),
    ("rate -5", "5", "partial_source_numeric_token"),
    ("rate +5", "5", "partial_source_numeric_token"),
    ("rate identifier5", "5", "partial_source_numeric_token"),
    ("rate 1,000", "1", "comma_source_number_unsupported"),
    ("rate 1,000", "000", "comma_source_number_unsupported"),
    ("rate 0,5", "5", "comma_source_number_unsupported"),
    ("rate 1,000", "1,000", "literal_source_number_required"),
    ("rate NaN", "NaN", "literal_source_number_required"),
    ("rate ١e-4000", "١e-4000", "literal_source_number_required"),
    ("rate inf", "inf", "literal_source_number_required")])
def test_partial_or_nonliteral_number_selection_is_rejected(text, token, code):
    error(code, number, text, token, quote=token)


@pytest.mark.parametrize("marker", ["±", "+/-", "&plusmn;", "SD=", "SEM="])
def test_spread_does_not_masquerade_as_a_rate(marker):
    text = "Rate 774 " + marker + "58 pmol/min/mg"
    error("uncertainty_is_not_rate_point", number, text, "58", quote="58")
    assert number(text, "58", quote="58", role="spread")["value"] == 58


@pytest.mark.parametrize("role", ["spread", "condition"])
def test_spreads_and_conditions_require_points_instead_of_censor_limits(role):
    error("plain_source_point_required", number, "Rate <5", "5", role=role)


def test_negative_temperature_is_preserved_and_its_sign_cannot_be_stripped():
    assert number("Temperature -5 degC", "-5", role="condition")["value"] == -5
    error("partial_source_numeric_token", number, "Temperature -5 degC", "5", role="condition", quote="5")
    error("nonnegative_source_number_required", number, "SD=-5", "-5", role="spread")


@pytest.mark.parametrize("text,token", [("pH 8. Condition panel complete.", "8"),
    ("Rate 8.", "8"), ("Rate 1.5. Further details.", "1.5")])
def test_sentence_full_stops_do_not_turn_native_points_into_partial_tokens(text, token):
    assert number(text, token, role="condition")["value"] == float(token)


@pytest.mark.parametrize("text,token", [("Rate 5.e2", "5"), ("Rate 5.2", "5"),
    ("Rate 5..10", "5"), ("Rate ١5", "5"), ("Rate 5١", "5")])
def test_sentence_exception_cannot_hide_exponents_decimals_or_unicode_digits(text, token):
    error("partial_source_numeric_token", number, text, token)


def test_sentence_full_stop_does_not_excuse_a_clipped_leading_number():
    error("partial_source_numeric_token", number, "Rate 101.2. More details.", "1.2", quote="1.2")


def test_a_scientific_coefficient_is_not_the_whole_literal_measurement():
    error("nonliteral_scientific_expression", number, "Rate 5 × 10^-3", "5")


@pytest.mark.parametrize("text", ["LOD=5", "detection limit was 5", "upper limit of 5"])
def test_a_detection_limit_is_not_an_observed_rate_without_its_censor_relation(text):
    error("untyped_limit_source_number", number, text, "5")


@pytest.mark.parametrize("token", ["1e400", "1e-4000"])
def test_out_of_float_range_native_numbers_never_become_infinity_or_zero(token):
    error("numerical_model_range", number, "Rate " + token, token)


@pytest.mark.parametrize("raw,canonical,multiplier", [
    ("pmol/min/mg", "pmol/min/mg", 1), ("nmol min-1 mg-1", "pmol/min/mg", 1000),
    ("µmol min−1 mg−1", "pmol/min/mg", 1000000), ("μmol min⁻¹ mg⁻¹", "pmol/min/mg", 1000000),
    ("nmol min^-1 mg^-1", "pmol/min/mg", 1000),
    ("nmol min<sup>−1</sup> mg<sup>−1</sup>", "pmol/min/mg", 1000),
    ("per_min", "per_min", 1), ("min⁻¹", "per_min", 1), ("1/min", "per_min", 1),
    ("per s", "per_min", 60), ("s^-1", "per_min", 60),
    ("uM/min", "uM/min", 1), ("μM min⁻¹", "uM/min", 1), ("nM/min", "uM/min", .001),
])
def test_complete_native_unit_aliases_preserve_dimension_and_scale(raw, canonical, multiplier):
    text = "Rate 0.1 " + raw + "; conditions follow."
    sources, _ = fixture(text)
    selected = witness(text, raw)
    original = deepcopy(selected)
    result = read_source_rate_unit(selected, sources=sources)
    assert result == {"witness": {**selected, "artifact_ref": ARTIFACT}, "raw_unit": raw,
        "canonical_unit": canonical, "multiplier": multiplier}
    assert selected == original


@pytest.mark.parametrize("text,selected", [("Rate 0.1uM/min/mg", "uM/min"),
    ("Rate 0.1xnmol/min/mg", "nmol/min/mg"), ("Rate 0.1per_minute", "per_min"),
    ("Rate 0.1uM min-1 mg-1", "uM min-1"), ("Rate 0.1nM/minute", "nM/min"),
    ("Rate 0.1uM/min /mg", "uM/min"), ("Rate 0.1pmol/min/mg%", "pmol/min/mg")])
def test_a_shortened_unit_cannot_drop_a_denominator_or_prefix(text, selected):
    sources, _ = fixture(text)
    error("partial_source_rate_unit", read_source_rate_unit, witness(text, selected), sources=sources)


def test_a_unit_can_be_adjacent_to_its_complete_numeric_token():
    text = "Rate0.1nmol/min/mg"
    sources, _ = fixture(text)
    assert read_source_rate_unit(witness(text, "nmol/min/mg"), sources=sources)["multiplier"] == 1000


@pytest.mark.parametrize("raw", ["mol/min", "mmol/min/mg", "kg", "mM/min", "pmol/min"])
def test_unsupported_dimensions_or_scales_are_not_relabelled(raw):
    sources, _ = fixture(raw)
    error("unsupported_source_rate_unit", read_source_rate_unit, witness(raw), sources=sources)


@pytest.mark.parametrize("token,raw_unit,expected", [("0.1", "nmol/min/mg", 100),
    ("0.005", "nmol/min/mg", 5), ("0.09", "nmol/min/mg", 90),
    ("0.001", "umol/min/mg", 1000), ("0.5", "per_s", 30),
    ("1000", "nM/min", 1), ("-0.5", "per_s", -30)])
def test_decimal_source_conversion_is_exact_before_final_float_rounding(token, raw_unit, expected):
    text = "Rate " + token + " " + raw_unit
    sources, _ = fixture(text)
    observed = read_source_number(selector(text, token), sources=sources, role="rate")
    unit = read_source_rate_unit(witness(text, raw_unit), sources=sources)
    original = deepcopy((observed, unit))
    result = convert_source_number(observed, unit)
    assert result == expected
    assert Fraction(result) == Fraction(token) * Fraction(str(unit["multiplier"]))
    assert (observed, unit) == original


def test_conversion_range_failure_is_not_a_zero_or_infinite_result():
    for token, raw_unit in (("1e308", "umol/min/mg"), ("5e-324", "nM/min")):
        text = "Rate " + token + " " + raw_unit
        sources, _ = fixture(text)
        observed = read_source_number(selector(text, token), sources=sources, role="rate")
        unit = read_source_rate_unit(witness(text, raw_unit), sources=sources)
        error("numerical_model_range", convert_source_number, observed, unit)


def test_caller_cannot_change_the_unit_multiplier():
    text = "Rate 0.1 nmol/min/mg"
    sources, _ = fixture(text)
    n = read_source_number(selector(text, "0.1", quote="0.1"), sources=sources, role="rate")
    u = read_source_rate_unit(witness(text, "nmol/min/mg"), sources=sources)
    u["multiplier"] = 1
    error("source_unit_conversion_mismatch", convert_source_number, n, u)


def test_conversion_rejects_a_forged_repeated_native_value_and_boolean_multiplier():
    text = "Rate 0.1 pmol/min/mg"
    sources, _ = fixture(text)
    n = read_source_number(selector(text, "0.1"), sources=sources, role="rate")
    u = read_source_rate_unit(witness(text, "pmol/min/mg"), sources=sources)
    bad = deepcopy(n)
    bad["value"] = 999
    error("source_number_value_mismatch", convert_source_number, bad, u)
    u["multiplier"] = True
    error("invalid_source_unit_record", convert_source_number, n, u)


def test_forged_underflow_record_is_rejected_before_large_rational_allocation():
    text = "Rate 0 pmol/min/mg"
    sources, _ = fixture(text)
    n = read_source_number(selector(text, "0"), sources=sources, role="rate")
    u = read_source_rate_unit(witness(text, "pmol/min/mg"), sources=sources)
    n["raw_number"] = "1e-1000000000"
    error("numerical_model_range", convert_source_number, n, u)


@pytest.mark.parametrize("text,token", [("SD=58%", "58"), ("SD=58percent", "58"),
    ("SD=58 percent", "58"), ("SD=58 per cent", "58"), ("SD=58 (%)", "58"),
    ("SD (%)=58", "58"), ("CV=0.1", "0.1"),
    ("coefficient of variation was 0.1", "0.1"), ("relative error: 0.1", "0.1"),
    ("RSD=0.1", "0.1"), ("SD=0.1 (CV)", "0.1")])
def test_relative_magnitudes_are_not_absolute_rate_spreads(text, token):
    error("relative_spread_unit_unsupported", number, text, token, role="spread")


def spread_records(text, token, supplied_unit):
    sources, _ = fixture(text)
    n = read_source_number(selector(text, token, quote=token), sources=sources, role="spread")
    u = read_source_rate_unit(witness(text, supplied_unit), sources=sources)
    return sources, n, u


def test_explicit_spread_unit_must_not_be_ignored_in_favor_of_main_scale():
    text = "Mean 100 pmol/min/mg; SD 58 nmol/min/mg"
    sources, n, main = spread_records(text, "58", "pmol/min/mg")
    error("source_spread_unit_mismatch", validate_source_spread_unit, n, main, sources=sources)
    explicit = read_source_rate_unit(witness(text, "nmol/min/mg"), sources=sources)
    assert validate_source_spread_unit(n, explicit, sources=sources) is None
    assert convert_source_number(n, explicit) == 58000


def test_explicit_spread_dimension_must_match_its_supplied_unit():
    text = "Mean 100 pmol/min/mg; SD 58 uM/min"
    sources, n, main = spread_records(text, "58", "pmol/min/mg")
    error("source_spread_unit_mismatch", validate_source_spread_unit, n, main, sources=sources)


@pytest.mark.parametrize("unit", ["pmol min−1 mg−1", "pmol min⁻¹ mg⁻¹", "pmol min<sup>−1</sup> mg<sup>−1</sup>"])
def test_explicit_spread_unit_uses_supported_lexical_aliases(unit):
    text = "Mean 100 pmol/min/mg; SD 58 " + unit
    sources, n, supplied = spread_records(text, "58", "pmol/min/mg")
    assert validate_source_spread_unit(n, supplied, sources=sources) is None


@pytest.mark.parametrize("ending", [" (SD)", ". This is the SD.", ")", ""])
def test_a_plain_spread_without_explicit_unit_keeps_common_unit_interpretation(ending):
    text = "Mean 100 pmol/min/mg; SD 58" + ending
    sources, n, supplied = spread_records(text, "58", "pmol/min/mg")
    assert validate_source_spread_unit(n, supplied, sources=sources) is None
    assert convert_source_number(n, supplied) == 58


@pytest.mark.parametrize("unit", ["nmol/min", "mmol/min/mg", "nmolmin-2mg-1", "mg"])
def test_an_explicit_unsupported_spread_unit_is_not_silently_common_unit(unit):
    text = "Mean 100 pmol/min/mg; SD 58 " + unit
    sources, n, supplied = spread_records(text, "58", "pmol/min/mg")
    error("unsupported_explicit_spread_unit", validate_source_spread_unit, n, supplied, sources=sources)


def test_spread_unit_guard_rechecks_actual_source_and_complete_unit_boundary():
    text = "Mean 100 uM/min; SD 58 uM/min /mg"
    sources, n, supplied = spread_records(text, "58", "uM/min")
    error("partial_source_rate_unit", validate_source_spread_unit, n, supplied, sources=sources)
    altered = deepcopy(n)
    altered["value"] = 59
    error("source_number_record_mismatch", validate_source_spread_unit, altered, supplied, sources=sources)


def test_offsets_and_witnesses_are_exact_and_repairable():
    text = "µ Rate: 774 nmol/min/mg"
    sources, _ = fixture(text)
    selected = selector(text, "774", quote="774")
    selected["witness"]["quote"] = "775"
    error("source_quote_mismatch", read_source_number, selected, sources=sources, role="rate")
    selected = selector(text, "774")
    selected["number_start"] = True
    error("nonnegative_integer_offset_required", read_source_number, selected, sources=sources, role="rate")
    selected = selector(text, "774")
    selected["number_end"] = 999
    error("source_number_span_order_invalid", read_source_number, selected, sources=sources, role="rate")


def test_selector_schema_is_closed_and_accepts_only_source_offsets():
    text = "Rate 774"
    selected = selector(text, "774")
    schema = number_selector_schema()
    validate_schema(selected, schema)
    assert schema["additionalProperties"] is False
    for field, value in (("value", 774), ("number_start", False)):
        bad = deepcopy(selected)
        bad[field] = value
        with pytest.raises(ContractError):
            validate_schema(bad, schema)
