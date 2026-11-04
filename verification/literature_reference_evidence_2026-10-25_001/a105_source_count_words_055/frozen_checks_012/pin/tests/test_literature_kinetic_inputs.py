"""Synthetic native-source checks; no primary paper or model execution."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
from gene_annotation_episode.literature_kinetic_inputs import (
    CONTEXT_FIELDS, SUBJECT_FIELDS, read_kinetic_inputs,
)

SOURCE_REF = "source_" + "a" * 24
FORBIDDEN_REF = "source_" + "b" * 24


class Source:
    def __init__(self, text):
        self.raw = text.encode()
        self.calls = []

    def read(self, reference, representation):
        self.calls.append((reference, representation))
        if reference != SOURCE_REF or representation not in ("original", "text"):
            raise ExperimentalContractError("fixture_scope_denied", "source_ref")
        return {"artifact_ref": "artifact:" + representation, "content": self.raw}

    def witness(self, text, occurrence=0):
        token = text.encode()
        first = 0
        for _ in range(occurrence + 1):
            first = self.raw.index(token, first)
            last = first + len(token)
            if _ < occurrence:
                first = last
        return {"source_ref": SOURCE_REF, "representation": "original",
                "start": first, "end": last, "quote": text}

    def number(self, quote, token, occurrence=0):
        return {"witness": self.witness(quote, occurrence),
                "number_start": quote.index(token), "number_end": quote.index(token) + len(token)}


def fixture(kind="catalytic_efficiency", unit="uM^-1min^-1", n="8", d="2", *, extra=""):
    nrow, drow = f"numerator {n} {unit}", f"denominator {d} {unit}"
    source = Source(f"<p>π ProteinFixture constructX substrateN substrateD.</p><p>Parameter {kind}.</p>"
        f"<p>{nrow}</p><p>{drow}</p><p>Same subject and definition; separate assays; reported protocols.</p>"
        f"<p>{extra}</p>")
    def interpreted(value):
        return {"value": value, "witnesses": [] if value in ("unknown", "unspecified", "unreported") else [source.witness("Same subject and definition; separate assays; reported protocols.")]}
    def operand(role, row, token, index):
        unit_witness = source.witness(row)
        unit_witness["start"] += len(row[:row.rindex(unit)].encode())
        unit_witness["end"] = unit_witness["start"] + len(unit.encode())
        unit_witness["quote"] = unit
        return {
            "parameter_kind": {"value": kind, "witnesses": [source.witness(kind)]},
            "subject": {name: source.witness("ProteinFixture") if name == "molecule" else source.witness("constructX") if name == "construct" else None for name in SUBJECT_FIELDS},
            "context": {name: source.witness("substrateN" if index == 0 else "substrateD") if name == "substrate" else None for name in CONTEXT_FIELDS},
            "measurement_identity": None,
            "measurement": {"number": source.number(row, token), "unit": unit_witness},
            "qualification": interpreted("reported_point"),
            "uncertainty": {"statistic": interpreted("unreported"), "magnitude": None,
                "interval": None, "unit": None, "unit_relationship": interpreted("unknown"),
                "confidence_level": None, "count": None,
                "repetition_basis": interpreted("unspecified"), "estimate_basis": interpreted("unknown")},
        }
    selection = {"version": "a105_kinetic_source_selection_v1", "source_ref": SOURCE_REF,
        "source_kind": "synthetic_fixture", "numerator": operand("numerator", nrow, n, 0),
        "denominator": operand("denominator", drow, d, 1),
        "comparison": {name: interpreted(value) for name, value in {
            "subject_relationship": "same_molecule_and_construct", "parameter_definition_relationship": "same",
            "substrate_arrangement": "separate_assays", "comparison_scope": "reported_protocols",
            "nonintended_conditions_relationship": "unknown"}.items()}}
    return source, selection


@pytest.mark.parametrize("kind,unit,value,expected", [
    ("Km", "M", "2", 2000000), ("Km", "mM", "2", 2000),
    ("Km", "µM", "2", 2), ("Km", "μM", "2", 2), ("Km", "nM", "2", .002),
    ("kcat", "s^-1", "2", 120), ("kcat", "s⁻¹", "2", 120),
    ("kcat", "min−1", "2", 2), ("kcat", "1/s", "2", 120),
    ("kcat", "per_min", "2", 2), ("kcat", "per_s", "2", 120),
    ("catalytic_efficiency", "M^-1s^-1", "1000000", 60),
    ("catalytic_efficiency", "mM^-1min^-1", "1000", 1),
    ("catalytic_efficiency", "µM−1 min−1", "2", 2),
    ("catalytic_efficiency", "nM^-1s^-1", "2", 120000),
    ("catalytic_efficiency", "1/(uM min)", "2", 2),
    ("catalytic_efficiency", "1/uM/min", "2", 2),
    ("catalytic_efficiency", "s^-1/M", "1000000", 60),
])
def test_dimensions_and_exact_inverse_scales(kind, unit, value, expected):
    source, selection = fixture(kind, unit, value, "1")
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert result["calculation_inputs"]["numerator"]["value"] == expected
    assert result["operands"]["numerator"]["unit"]["raw_unit"] == unit
    sheet = populate_kinetic_contrast(result["calculation_inputs"])
    assert sheet["cells"]["numerator_parameter"]["value"] == expected
    assert sheet["cells"]["source_profile_log_ratio"]["value"] is None
    assert sheet["independent_preparation_count"] is None
    json.dumps(result, allow_nan=False)


def test_exact_byte_locator_and_no_source_or_input_mutation():
    source, selection = fixture()
    before = deepcopy(selection)
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert selection == before
    assert source.calls == [(SOURCE_REF, "original")]
    row = result["calculation_inputs"]["numerator"]
    assert source.raw[row["source"]["start"]:row["source"]["end"]] == b"8"
    assert row["context"]["preparation"] is None
    result["calculation_inputs"]["numerator"]["subject"]["molecule"] = "mutated"
    assert selection == before


@pytest.mark.parametrize("qualifier,relation,approx", [
    ("<", "lt", False), ("<=", "le", False), ("&gt;", "gt", False),
    ("≥", "ge", False), ("about ", "eq", True), ("~>", "gt", True),
])
def test_qualifiers_outside_number_witness_remain(qualifier, relation, approx):
    source, selection = fixture(n=qualifier + "8")
    ns = selection["numerator"]["measurement"]["number"]
    # Narrow the quote itself to the number; qualifiers remain outside it.
    ns["witness"] = source.witness("8")
    ns["number_start"], ns["number_end"] = 0, 1
    result = read_kinetic_inputs(selection, read_source=source.read)
    operand = result["calculation_inputs"]["numerator"]
    assert operand["relation"] == relation
    assert operand["approximate"] is approx
    sheet = populate_kinetic_contrast(result["calculation_inputs"])
    if relation != "eq":
        assert sheet["cells"]["numerator_parameter"]["value"] is None
        assert sheet["cells"]["numerator_parameter"]["threshold"] == 8


@pytest.mark.parametrize("kind,unit", [("Km", "m"), ("Km", "mm"),
    ("kcat", "h^-1"), ("catalytic_efficiency", "uM/min"),
    ("catalytic_efficiency", "mM^-1h^-1"), ("Km", "UM")])
def test_complete_unsupported_unit_preserves_native_partial(kind, unit):
    source, selection = fixture(kind, unit)
    result = read_kinetic_inputs(selection, read_source=source.read)
    operand = result["calculation_inputs"]["numerator"]
    assert operand["value"] is None and operand["unit"] is None
    assert operand["unavailable_reason"] == "unsupported_source_kinetic_unit"
    assert result["operands"]["numerator"]["number"]["value"] == 8
    assert result["operands"]["numerator"]["unit"]["raw_unit"] == unit
    assert populate_kinetic_contrast(result["calculation_inputs"])["cells"]["parameter_ratio"]["unavailable_reason"] == "unsupported_source_kinetic_unit"


def test_missing_unit_preserves_specific_reason():
    source, selection = fixture()
    selection["numerator"]["measurement"]["unit"] = None
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert result["calculation_inputs"]["numerator"]["unavailable_reason"] == "source_kinetic_unit_unreported"
    assert result["operands"]["numerator"]["number"]["value"] == 8


def test_missing_kind_and_missing_operand_are_retained_without_guess():
    source, selection = fixture()
    selection["numerator"]["parameter_kind"] = {"value": "unknown", "witnesses": []}
    selection["denominator"] = None
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert result["calculation_inputs"]["numerator"] is None
    assert result["input_unavailable_reasons"]["numerator"][0] == "source_parameter_kind_unknown"
    assert result["operands"]["numerator"]["number"]["value"] == 8
    assert result["operands"]["denominator"] is None


@pytest.mark.parametrize("status", ["unknown", "conflicting"])
def test_unknown_conflicting_qualification_cannot_supply_point(status):
    source, selection = fixture()
    selection["numerator"]["qualification"] = {"value": status, "witnesses": [] if status == "unknown" else [source.witness("ProteinFixture"), source.witness("constructX")]}
    result = read_kinetic_inputs(selection, read_source=source.read)
    operand = result["calculation_inputs"]["numerator"]
    assert operand["value"] is None
    assert operand["unavailable_reason"] == "source_operand_qualification_" + status
    assert result["operands"]["numerator"]["canonical_value"] == 8


def test_same_token_cannot_gain_pair_contrast_from_different_meanings():
    source, selection = fixture()
    selection["denominator"]["measurement"] = deepcopy(selection["numerator"]["measurement"])
    result = read_kinetic_inputs(selection, read_source=source.read)
    n, d = [result["calculation_inputs"][r] for r in ("numerator", "denominator")]
    assert n["measurement_id"] == d["measurement_id"]
    sheet = populate_kinetic_contrast(result["calculation_inputs"])
    assert sheet["cells"]["parameter_ratio"]["value"] is None
    assert sheet["cells"]["parameter_ratio"]["unavailable_reason"] == "conflicting_source_observation"


def test_explicit_shared_identity_stays_shared_and_is_not_replication():
    source, selection = fixture()
    for role in ("numerator", "denominator"):
        selection[role]["measurement_identity"] = source.witness("constructX")
    result = read_kinetic_inputs(selection, read_source=source.read)
    n, d = [result["calculation_inputs"][r] for r in ("numerator", "denominator")]
    assert n["physical_measurement_id"] == d["physical_measurement_id"]
    assert populate_kinetic_contrast(result["calculation_inputs"])["cells"]["parameter_difference"]["value"] is None


def uncertainty_fixture(statistic="unspecified", *, unit="uM", kind="Km", extra="spread ± 1 uM; n=3; technical measurements; CI [4, 12] uM; 95% confidence"):
    source, selection = fixture(kind, unit, extra=extra)
    unc = selection["numerator"]["uncertainty"]
    def meaning(value):
        return {"value": value, "witnesses": [] if value in ("unknown", "unspecified", "unreported") else [source.witness(extra)]}
    unc["statistic"] = meaning(statistic)
    unc["magnitude"] = source.number(extra, "1")
    unc["unit_relationship"] = meaning("same_as_parameter")
    unc["count"] = source.number(extra, "3") if "3" in extra else None
    unc["repetition_basis"] = meaning("technical_measurements")
    return source, selection


@pytest.mark.parametrize("statistic", ["unspecified", "sd", "sem"])
def test_spread_semantics_and_technical_count_never_create_covariance(statistic):
    source, selection = uncertainty_fixture(statistic)
    result = read_kinetic_inputs(selection, read_source=source.read)
    unc = result["calculation_inputs"]["numerator"]["uncertainty"]
    assert unc["statistic"] == statistic and unc["magnitude"] == 1
    assert unc["count"] == 3 and unc["repetition_basis"] == "technical_measurements"
    sheet = populate_kinetic_contrast(result["calculation_inputs"])
    assert sheet["cells"]["log_contrast_variance"]["value"] is None


def test_literal_ci_endpoints_and_percent_level_not_halfwidth_or_sd():
    source, selection = uncertainty_fixture("ci")
    unc = selection["numerator"]["uncertainty"]
    unc["magnitude"] = None
    unc["interval"] = {"witness": source.witness("[4, 12]"), "lower_start": 1,
        "lower_end": 2, "upper_start": 4, "upper_end": 6}
    unc["confidence_level"] = source.witness("95%")
    result = read_kinetic_inputs(selection, read_source=source.read)
    value = result["calculation_inputs"]["numerator"]["uncertainty"]
    assert value["interval"] == [4, 12] and value["confidence_level"] == .95
    assert value["magnitude"] is None
    assert populate_kinetic_contrast(result["calculation_inputs"])["cells"]["source_profile_log_ratio"]["value"] is None


def test_uncertainty_unknown_unit_preserves_native_spread():
    source, selection = uncertainty_fixture()
    unc = selection["numerator"]["uncertainty"]
    unc["unit_relationship"] = {"value": "unknown", "witnesses": []}
    result = read_kinetic_inputs(selection, read_source=source.read)
    retained = result["operands"]["numerator"]["uncertainty"]
    assert retained["magnitude"]["value"] == 1
    assert retained["canonical"]["magnitude"] is None
    assert retained["unavailable_reason"] == "source_uncertainty_unit_unavailable"


@pytest.mark.parametrize("bad", ["3.0", "-3", "0", ">3", "about 3"])
def test_count_is_exact_only_for_plain_positive_integer(bad):
    extra = f"spread ± 1 uM; n={bad}; technical measurements"
    source, selection = uncertainty_fixture(extra=extra)
    selection["numerator"]["uncertainty"]["count"] = source.number(extra, "3" if bad != "0" else "0")
    if bad in ("3.0", "-3"):
        # Selecting only3 clips the decimal/sign and remains a caller error.
        with pytest.raises(ExperimentalContractError):
            read_kinetic_inputs(selection, read_source=source.read)
    else:
        result = read_kinetic_inputs(selection, read_source=source.read)
        uncertainty = result["operands"]["numerator"]["uncertainty"]
        assert uncertainty["canonical"]["count"] is None
        assert uncertainty["count"]["status"] == ("not_positive" if bad == "0" else "qualified")
        assert result["calculation_inputs"]["numerator"]["value"] == 8


@pytest.mark.parametrize("bad", ["8e3", "18", "-8", ".8", "8.5"])
def test_clipped_numeric_tokens_reject(bad):
    source, selection = fixture(n=bad)
    ns = selection["numerator"]["measurement"]["number"]
    ns["witness"] = source.witness("8")
    ns["number_start"], ns["number_end"] = 0, 1
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("bad", ["8%", "SD 8", "SEM 8", "± 8", "between 8 and 9", "8 × 10^3", "8/2", "n=8", "8 independent experiments"])
def test_wrong_parameter_numeric_role_cannot_be_point(bad):
    source, selection = fixture(n=bad)
    ns = selection["numerator"]["measurement"]["number"]
    ns["witness"] = source.witness("8")
    ns["number_start"], ns["number_end"] = 0, 1
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("badunit,selected", [("uM/min", "uM"), ("mM^-1min^-1", "mM"),
    ("M^-1s^-1", "M^-1"), ("uM^-1min^-1/mg", "uM^-1min^-1")])
def test_clipped_units_reject(badunit, selected):
    source, selection = fixture("Km" if selected in ("uM", "mM") else "catalytic_efficiency", badunit)
    selection["numerator"]["measurement"]["unit"] = source.witness(selected)
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


def test_remote_header_cannot_mask_explicit_point_unit():
    source, selection = fixture("Km", "mM", extra="header uM")
    selection["numerator"]["measurement"]["unit"] = source.witness("uM")
    with pytest.raises(ExperimentalContractError, match="source_kinetic_unit_mismatch"):
        read_kinetic_inputs(selection, read_source=source.read)


def test_remote_header_cannot_mask_plusminus_common_unit():
    source, selection = fixture("Km", "mM", "8 ± 1", extra="header uM")
    selection["numerator"]["measurement"]["number"] = source.number("numerator 8 ± 1 mM", "8")
    selection["numerator"]["measurement"]["unit"] = source.witness("uM")
    with pytest.raises(ExperimentalContractError, match="source_kinetic_unit_mismatch"):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("badunit", ["uMfoo", "UM", "MAU"])
def test_remote_header_cannot_mask_unsupported_explicit_unit(badunit):
    source, selection = fixture("Km", badunit, extra="header uM")
    unit = source.witness("header uM")
    unit.update(start=unit["start"] + len("header "), quote="uM")
    selection["numerator"]["measurement"]["unit"] = unit
    with pytest.raises(ExperimentalContractError, match="unsupported_explicit_kinetic_unit"):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("compound,clipped", [("M^-1 s^-1", "s^-1"), ("1/(uM min)", "uM"), ("uM min^-1", "min^-1")])
def test_last_factor_of_compound_cannot_masquerade_as_unit(compound, clipped):
    source, selection = fixture("kcat" if "-1" in clipped else "Km", compound)
    selection["numerator"]["measurement"]["unit"] = source.witness(clipped)
    with pytest.raises(ExperimentalContractError, match="partial_source_kinetic_unit"):
        read_kinetic_inputs(selection, read_source=source.read)


def test_remote_header_cannot_mask_explicit_ci_unit():
    source, selection = uncertainty_fixture("ci", extra="CI [4, 12] mM; header uM")
    unc = selection["numerator"]["uncertainty"]
    unc["magnitude"] = None
    unc["interval"] = {"witness": source.witness("[4, 12]"), "lower_start": 1,
        "lower_end": 2, "upper_start": 4, "upper_end": 6}
    with pytest.raises(ExperimentalContractError, match="source_kinetic_unit_mismatch"):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("response", [{"artifact_ref": "artifact", "content": "not bytes"},
    {"artifact_ref": "artifact", "content": b"", "unexpected": True}])
def test_source_callback_contract_is_validated(response):
    source, selection = fixture()
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=lambda *_: response)


def test_converted_extreme_cannot_manufacture_zero_or_infinity():
    source, selection = fixture("kcat", "s^-1", "1e308")
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert result["operands"]["numerator"]["number"]["value"] == 1e308
    assert result["calculation_inputs"]["numerator"]["value"] is None
    assert result["calculation_inputs"]["numerator"]["unavailable_reason"] == "source_numeric_range"
    json.dumps(result, allow_nan=False)


def test_authorization_is_caller_owned_and_denial_propagates():
    source, selection = fixture()
    selection["numerator"]["subject"]["molecule"]["source_ref"] = FORBIDDEN_REF
    with pytest.raises(ExperimentalContractError, match="fixture_scope_denied"):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("change", ["quote", "end", "utf8"])
def test_exact_source_custody_rejects_mismatch(change):
    source, selection = fixture()
    witness = selection["numerator"]["subject"]["molecule"]
    if change == "quote":
        witness["quote"] = "different"
    elif change == "end":
        witness["end"] = 100000
    else:
        witness.update(start=4, end=5, quote="π")
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("field", ["extra_number", "source_kind", "number_start_bool", "bad_interpretation"])
def test_closed_shape_rejects_scientific_number_arguments(field):
    source, selection = fixture()
    if field == "extra_number":
        selection["numerator"]["measurement"]["value"] = 8
    elif field == "source_kind":
        selection["source_kind"] = "unverified_graph"
    elif field == "number_start_bool":
        selection["numerator"]["measurement"]["number"]["number_start"] = True
    else:
        selection["comparison"]["subject_relationship"]["value"] = True
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


def test_known_interpretation_needs_witness_but_unknown_does_not():
    source, selection = fixture()
    selection["comparison"]["subject_relationship"]["witnesses"] = []
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        read_kinetic_inputs(selection, read_source=source.read)
    selection["comparison"]["subject_relationship"]["value"] = "unknown"
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert populate_kinetic_contrast(result["calculation_inputs"])["cells"]["parameter_ratio"]["unavailable_reason"] == "subject_relationship_unknown"


def test_negative_noisy_parameter_retained_but_log_unavailable():
    source, selection = fixture("Km", "uM", "-2", "1")
    result = read_kinetic_inputs(selection, read_source=source.read)
    sheet = populate_kinetic_contrast(result["calculation_inputs"])
    assert sheet["cells"]["numerator_parameter"]["value"] == -2
    assert sheet["cells"]["parameter_ratio"]["value"] == -2
    assert sheet["cells"]["log_parameter_contrast"]["value"] is None


def test_primary_reported_origin_and_calculated_unit_conversion_are_distinct():
    source, selection = fixture("kcat", "s^-1")
    selection["source_kind"] = "primary_source"
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert result["operands"]["numerator"]["source_origin"] == "reported"
    assert result["calculation_inputs"]["numerator"]["origin"] == "calculated"
    assert result["operands"]["numerator"]["number"]["raw_number"] == "8"
    assert result["calculation_inputs"]["numerator"]["value"] == 480


def test_absent_measurement_retains_context_without_physical_observation():
    source, selection = fixture()
    selection["numerator"]["measurement"] = None
    result = read_kinetic_inputs(selection, read_source=source.read)
    operand = result["calculation_inputs"]["numerator"]
    assert operand["measurement_id"].startswith("kinetic_unavailable_record_")
    assert operand["value"] is None and operand["physical_measurement_id"] is None
    assert operand["subject"]["molecule"] == "ProteinFixture"
    assert operand["unavailable_reason"] == "source_measurement_unreported"


def test_independent_header_unit_is_allowed_without_adjacent_conflict():
    source, selection = fixture("Km", "uM")
    source.raw += b"<p>header uM</p><p>plain value 8</p>"
    selection["numerator"]["measurement"]["number"] = source.number("plain value 8", "8")
    witness = source.witness("header uM")
    witness.update(start=witness["start"] + len("header "), quote="uM")
    selection["numerator"]["measurement"]["unit"] = witness
    result = read_kinetic_inputs(selection, read_source=source.read)
    assert result["calculation_inputs"]["numerator"]["value"] == 8


def test_conflicting_interpretation_requires_distinct_witnesses():
    source, selection = fixture()
    witness = source.witness("ProteinFixture")
    selection["comparison"]["comparison_scope"] = {"value": "conflicting", "witnesses": [witness, deepcopy(witness)]}
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("level", ["0%", "100%", "-5%", "1e99999%", "0.95"])
def test_confidence_level_has_no_default_or_probability_guess(level):
    source, selection = uncertainty_fixture("ci", extra="CI [4, 12] uM; confidence " + level)
    unc = selection["numerator"]["uncertainty"]
    unc["magnitude"] = None
    unc["interval"] = {"witness": source.witness("[4, 12]"), "lower_start": 1,
        "lower_end": 2, "upper_start": 4, "upper_end": 6}
    unc["confidence_level"] = source.witness(level)
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("qualified", ["<95%", "≤95%", "&gt;95%", "about 95%", "~95%", "approximately 95%", "95% or more"])
def test_outside_witness_qualified_confidence_cannot_be_exact(qualified):
    source, selection = uncertainty_fixture("ci", extra="CI [4, 12] uM; confidence " + qualified)
    unc = selection["numerator"]["uncertainty"]
    unc["magnitude"] = None
    unc["interval"] = {"witness": source.witness("[4, 12]"), "lower_start": 1,
        "lower_end": 2, "upper_start": 4, "upper_end": 6}
    unc["confidence_level"] = source.witness("95%")
    before = deepcopy(unc["confidence_level"])
    with pytest.raises(ExperimentalContractError, match="qualified_source_confidence_unsupported") as error:
        read_kinetic_inputs(selection, read_source=source.read)
    assert error.value.detail["witness"]["quote"] == "95%"
    assert unc["confidence_level"] == before


def test_reversed_ci_cannot_hide_in_float_rounding():
    literal = "[1.00000000000000001, 1.0]"
    source, selection = uncertainty_fixture("ci", extra="CI " + literal + " uM")
    unc = selection["numerator"]["uncertainty"]
    unc["magnitude"] = None
    unc["interval"] = {"witness": source.witness(literal), "lower_start": 1,
        "lower_end": 20, "upper_start": 22, "upper_end": 25}
    # Compute exact selector endpoints so the check reaches interval ordering.
    unc["interval"].update(lower_end=literal.index(","), upper_start=literal.index("1.0", 2), upper_end=len(literal) - 1)
    with pytest.raises(ExperimentalContractError, match="ordered_ci_interval_required"):
        read_kinetic_inputs(selection, read_source=source.read)


def test_distinct_ci_endpoints_cannot_round_to_false_zero_width():
    literal = "[1.00000000000000001, 1.00000000000000002]"
    source, selection = uncertainty_fixture("ci", extra="CI " + literal + " uM")
    unc = selection["numerator"]["uncertainty"]
    unc["magnitude"] = None
    unc["interval"] = {"witness": source.witness(literal), "lower_start": 1,
        "lower_end": literal.index(","), "upper_start": literal.index("1.0", 2), "upper_end": len(literal) - 1}
    result = read_kinetic_inputs(selection, read_source=source.read)
    retained = result["operands"]["numerator"]["uncertainty"]
    assert retained["canonical"]["interval"] is None
    assert retained["unavailable_reason"] == "source_numeric_range"
    assert retained["interval"]["selector"]["witness"]["quote"] == literal
