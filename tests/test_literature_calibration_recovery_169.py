"""Synthetic only: exact source selection and recovery component meanings.

No fixture is an original paper, real experiment, model response or evidence of
A105 adequacy. Tables imitate supported JATS representations for parser checks.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_calibration_recovery_inputs import (
    calibration_recovery_population_schema, read_calibration_recovery_inputs,
)
from gene_annotation_episode.literature_calibration_recovery_calculations import (
    COMPONENTS, populate_calibration_recovery,
)
from gene_annotation_episode.literature_calibration_recovery_prompt import CALIBRATION_RECOVERY_TASK


class Source:
    def __init__(self, *, nominal="10", measured="9.8", spread="0.2", unit="nmol", recovery="98", recovery_unit="%", prefix="", suffix=""):
        self.reference = "source_" + "1" * 24
        self.prefix, self.suffix = prefix, suffix
        self.text = ("<article><p>Illustrative standard in buffer, optical reporter, no-reaction blank. "
                     "Nominal stock amount. SD; enzyme activity spike; incompatible statement.</p>"
                     "<table-wrap><table><thead><tr><th>Prepared</th><th>Measured (" + unit + ")</th>"
                     "<th>Recovery (" + recovery_unit + ")</th></tr></thead><tbody><tr>"
                     "<td>" + prefix + nominal + suffix + "</td><td>" + measured + " ± " + spread + "</td>"
                     "<td>" + recovery + "</td></tr></tbody></table></table-wrap></article>")
        self.content = self.text.encode("utf-8")
        self.artifact = "artifact_" + hashlib.sha256(self.content).hexdigest()
        self.calls = []

    def witness(self, token, *, occurrence=0):
        start = -1
        for _ in range(occurrence + 1):
            start = self.text.index(token, start + 1)
        return {"source_ref": self.reference, "representation": "original",
                "start": len(self.text[:start].encode("utf-8")),
                "end": len(self.text[:start + len(token)].encode("utf-8")), "quote": token}

    def number(self, token, *, occurrence=0):
        return {"witness": self.witness(token, occurrence=occurrence), "number_start": 0, "number_end": len(token)}

    def number_in(self, token, container):
        start = container.index(token)
        return {"witness": self.witness(container), "number_start": start, "number_end": start + len(token)}

    def interpretation(self, value, quote=None):
        return {"value": value, "witnesses": [] if quote is None else [self.witness(quote)]}

    def args(self, *, nominal="10", measured="9.8", spread="0.2", unit="nmol", recovery="98", recovery_unit="%"):
        return {"source_ref": self.reference, "source_kind": "synthetic_fixture",
                "experiment": self.witness("Illustrative standard"), "analyte": None,
                "matrix": self.witness("buffer"), "endpoint": self.witness("optical reporter"),
                "blank_treatment": self.witness("no-reaction blank"),
                "expected_quantity_basis": self.witness("Nominal stock amount"),
                "control_kind": self.interpretation("reporter_standard", "Illustrative standard"),
                "applicability": self.interpretation("unknown"),
                "nominal": self.number_in(nominal, "<td>" + self.prefix + nominal + self.suffix + "</td>"),
                "measured": self.number_in(measured, "<td>" + measured + " ± " + spread + "</td>"),
                "measured_spread": self.number_in(spread, "<td>" + measured + " ± " + spread + "</td>"),
                "shared_unit": self.witness(unit),
                "spread_kind": self.interpretation("SD", "SD"),
                "reported_recovery": self.number_in(recovery, "<td>" + recovery + "</td>"),
                "reported_recovery_unit": {"value": "percent" if recovery_unit == "%" else "fraction",
                                           "witness": self.witness(recovery_unit)}}

    def read(self, reference, representation):
        assert reference == self.reference and representation == "original"
        self.calls.append((reference, representation))
        return {"artifact_ref": self.artifact, "content": self.content}


def run(source, args=None):
    extracted = read_calibration_recovery_inputs(source.args() if args is None else args, read_source=source.read)
    return extracted, populate_calibration_recovery(extracted)


def test_exact_source_pair_populates_numerical_components():
    source = Source()
    extracted, sheet = run(source)
    cells = sheet["cells"]
    assert set(cells) == set(COMPONENTS)
    assert cells["recovery"]["exact_value"] == {"numerator": "49", "denominator": "50"}
    assert cells["signed_difference"]["value"] == -.2
    assert cells["relative_bias"]["value"] == -.02
    assert cells["percent_bias"]["value"] == -2
    assert cells["inverse_recovery"]["value"] == pytest.approx(50/49)
    assert cells["measured_sd"]["value"] == .2
    assert cells["measured_cv"]["value"] == pytest.approx(1/49)
    assert cells["reported_recovery"]["value"] == .98
    assert cells["displayed_minus_reported_recovery"]["value"] == 0
    assert cells["correction_for_other_measurement"]["value"] is None
    assert cells["recovery_variance"]["value"] is None
    assert sheet["section"] == "calibration_validity"
    assert source.calls == [(source.reference, "original")]
    assert extracted["source_kind"] == "synthetic_fixture"
    assert extracted["input_origins"] == ["synthetic"]
    assert all(c["input_origins"] == ["synthetic"] for c in cells.values())
    assert cells["nominal"]["origin"] == "synthetic"
    assert cells["recovery"]["origin"] == "derived"


@pytest.mark.parametrize("unit,factor", [("pmol", Fraction(1,1000)), ("nmol", Fraction(1)),
                                         ("umol", Fraction(1000)), ("µmol", Fraction(1000)),
                                         ("μmol", Fraction(1000))])
def test_exact_amount_scale_and_unicode(unit, factor):
    source = Source(unit=unit)
    args = source.args(unit=unit)
    extracted, sheet = run(source, args)
    assert sheet["cells"]["nominal"]["value"] == float(10*factor)
    assert sheet["cells"]["recovery"]["value"] == .98
    assert extracted["shared_unit"]["unit"] == "nmol"


@pytest.mark.parametrize("unit", ["pmol/min", "nmol/min", "µmol/min", "nmol min−1", "nmol min<sup>−1</sup>"])
def test_enzyme_activity_spike_is_distinct_control(unit):
    source = Source(unit=unit)
    args = source.args(unit=unit)
    args["control_kind"] = source.interpretation("enzyme_activity_spike", "enzyme activity spike")
    _, sheet = run(source, args)
    assert sheet["section"] == "matrix_activity_response"
    assert sheet["cells"]["nominal"]["unit"] == "nmol/min"
    assert sheet["cells"]["recovery"]["value"] == .98
    assert sheet["cells"]["correction_for_other_measurement"]["unavailable_reason"] == "no_target_measurement_supplied"


def test_unknown_control_preserves_descriptive_pair_without_role_inference():
    source = Source()
    args = source.args()
    args["control_kind"] = source.interpretation("unknown")
    _, sheet = run(source, args)
    assert sheet["cells"]["recovery"]["value"] == .98
    assert sheet["interpretation_scope_unavailable_reason"] == "control_kind_unknown"
    assert sheet["section"] == "recovery_control_role_unresolved"


def test_conflicting_role_requires_distinct_witnesses_but_keeps_pair():
    source = Source()
    args = source.args()
    args["control_kind"] = {"value": "conflicting", "witnesses": [source.witness("Illustrative standard")]*2}
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        run(source, args)
    args["control_kind"]["witnesses"][1] = source.witness("incompatible statement")
    _, sheet = run(source, args)
    assert sheet["cells"]["recovery"]["value"] == .98
    assert sheet["interpretation_scope_unavailable_reason"] == "control_kind_conflicting"


def test_known_control_dimension_mismatch_retains_raw_partials():
    source = Source(unit="nmol/min")
    extracted, sheet = run(source, source.args(unit="nmol/min"))
    assert extracted["observations"]["measured"]["value"] == 9.8
    assert sheet["cells"]["measured"]["value"] == 9.8
    assert sheet["cells"]["signed_difference"]["value"] == -.2
    assert sheet["cells"]["recovery"]["value"] is None
    assert sheet["cells"]["recovery"]["unavailable_reason"] == "control_dimension_mismatch"


@pytest.mark.parametrize("kind", ["SEM", "unspecified", "unknown"])
def test_spread_is_not_promoted_to_sd_or_cv(kind):
    source = Source()
    args = source.args()
    args["spread_kind"] = source.interpretation(kind, None if kind == "unknown" else "SD")
    extracted, sheet = run(source, args)
    assert extracted["observations"]["measured_spread"]["native_value"] == .2
    assert sheet["cells"]["reported_measured_spread"]["value"] == .2
    assert sheet["cells"]["measured_sd"]["value"] is None
    assert sheet["cells"]["measured_cv"]["unavailable_reason"] == "spread_kind_not_SD"


def test_missing_nominal_preserves_measured_and_sd():
    source = Source()
    args = source.args(); args["nominal"] = None
    _, sheet = run(source, args)
    assert sheet["cells"]["recovery"]["unavailable_reason"] == "nominal_not_supplied"
    assert sheet["cells"]["measured"]["value"] == 9.8
    assert sheet["cells"]["measured_sd"]["value"] == .2
    assert sheet["cells"]["measured_cv"]["value"] == pytest.approx(1/49)


def test_missing_shared_unit_retains_native_source_literals():
    source = Source()
    args = source.args(); args["shared_unit"] = None
    extracted, sheet = run(source, args)
    assert extracted["observations"]["measured"]["native_value"] == 9.8
    assert extracted["observations"]["measured"]["value"] is None
    assert sheet["cells"]["recovery"]["unavailable_reason"] == "shared_unit_not_supplied"
    assert sheet["cells"]["reported_recovery"]["value"] == .98


def test_zero_nominal_does_not_become_infinite_recovery():
    source = Source(nominal="0")
    _, sheet = run(source, source.args(nominal="0"))
    assert sheet["cells"]["nominal"]["value"] == 0
    assert sheet["cells"]["signed_difference"]["value"] == 9.8
    assert sheet["cells"]["recovery"]["unavailable_reason"] == "nonpositive_nominal"


@pytest.mark.parametrize("measured", ["0", "-2"])
def test_nonpositive_measured_preserved_with_no_inverse_or_cv(measured):
    source = Source(measured=measured)
    _, sheet = run(source, source.args(measured=measured))
    assert sheet["cells"]["measured"]["value"] == float(measured)
    assert sheet["cells"]["recovery"]["value"] == float(measured)/10
    assert sheet["cells"]["inverse_recovery"]["unavailable_reason"] == "nonpositive_measured"
    assert sheet["cells"]["measured_cv"]["unavailable_reason"] == "nonpositive_measured"


def test_shared_original_operand_keys_survive_all_derivatives():
    source = Source()
    args = source.args(); args["measured"] = deepcopy(args["nominal"])
    extracted, sheet = run(source, args)
    assert extracted["observations"]["nominal"]["measurement_key"] == extracted["observations"]["measured"]["measurement_key"]
    assert len(sheet["cells"]["recovery"]["input_measurement_keys"]) == 1
    assert sheet["cells"]["recovery"]["value"] == 1
    assert sheet["cells"]["recovery_variance"]["value"] is None


def test_equal_values_at_different_positions_have_distinct_keys():
    source = Source(measured="10")
    args = source.args(measured="10")
    args["measured"] = source.number("10", occurrence=1)
    extracted, sheet = run(source, args)
    assert extracted["observations"]["nominal"]["measurement_key"] != extracted["observations"]["measured"]["measurement_key"]
    assert len(sheet["cells"]["recovery"]["input_measurement_keys"]) == 2


def test_displayed_and_reported_recovery_are_both_preserved():
    source = Source(recovery="97.5")
    _, sheet = run(source, source.args(recovery="97.5"))
    assert sheet["cells"]["reported_recovery"]["value"] == .975
    assert sheet["cells"]["recovery"]["value"] == .98
    assert sheet["cells"]["displayed_minus_reported_recovery"]["value"] == .005


@pytest.mark.parametrize("prefix,suffix", [("&lt;", ""), ("≥", ""), ("approximately ", ""), ("", " or less"), ("", "–12")])
def test_censoring_and_approximations_are_not_point_operands(prefix, suffix):
    source = Source(prefix=prefix, suffix=suffix)
    with pytest.raises(ExperimentalContractError):
        run(source)


@pytest.mark.parametrize("unit", ["nmol/min/mg", "mM", "nmol/s", "mmol", "nmol</th><th>/min"])
def test_unsupported_or_cross_field_units_rejected(unit):
    source = Source(unit=unit)
    with pytest.raises(ExperimentalContractError):
        run(source, source.args(unit=unit))


def test_clipped_numeric_token_rejected():
    source = Source(nominal="110")
    args = source.args(nominal="110")
    args["nominal"]["number_start"] += 1
    with pytest.raises(ExperimentalContractError, match="partial_source_numeric_token"):
        run(source, args)


def test_clipped_compound_unit_rejected():
    source = Source(unit="nmol/min")
    args = source.args(unit="nmol/min"); args["shared_unit"] = source.witness("nmol")
    with pytest.raises(ExperimentalContractError, match="partial_source_unit"):
        run(source, args)


def test_no_entered_scientific_values_in_arguments():
    source = Source()
    args = source.args(); args["measured"]["value"] = 9.8
    with pytest.raises(ContractError):
        validate_schema(args, calibration_recovery_population_schema())


def test_mutated_normalized_or_identity_record_rejected():
    source = Source()
    extraction, _ = run(source)
    wrong = deepcopy(extraction); wrong["observations"]["measured"]["value"] = 17
    with pytest.raises(ExperimentalContractError, match="calibration_conversion_record_mismatch"):
        populate_calibration_recovery(wrong)
    wrong = deepcopy(extraction); wrong["observations"]["measured"]["measurement_key"] = "literature_measurement_" + "2"*24
    with pytest.raises(ExperimentalContractError, match="calibration_measurement_binding_mismatch"):
        populate_calibration_recovery(wrong)


def test_calculator_leaves_inputs_unchanged_and_has_no_scientific_io():
    source = Source()
    extraction, _ = run(source)
    snapshot = deepcopy(extraction); previous_calls = list(source.calls)
    assert populate_calibration_recovery(extraction)["cells"]["recovery"]["value"] == .98
    assert extraction == snapshot and source.calls == previous_calls


def test_prompt_preserves_the_three_proposed_paragraphs():
    assert len(CALIBRATION_RECOVERY_TASK.split("\n\n")) == 3
    assert CALIBRATION_RECOVERY_TASK.startswith("Evaluate the selected recovery experiment supporting the reference molecule’s assay.")
    assert CALIBRATION_RECOVERY_TASK.endswith("do not produce a probability of function or annotation credit.")
    assert "Have the deterministic calculator populate recovery, signed difference and relative bias from the supported pair." in CALIBRATION_RECOVERY_TASK
    assert "source_ref" not in CALIBRATION_RECOVERY_TASK


def test_applicability_claim_without_target_never_populates_other_correction():
    source = Source()
    args = source.args()
    args["applicability"] = source.interpretation("same_matrix_same_endpoint_supported", "buffer, optical reporter")
    _, sheet = run(source, args)
    assert sheet["cells"]["inverse_recovery"]["value"] == pytest.approx(50/49)
    assert sheet["cells"]["correction_for_other_measurement"]["value"] is None
    assert sheet["cells"]["correction_for_other_measurement"]["unavailable_reason"] == "no_target_measurement_supplied"


def test_source_aliases_of_identical_artifact_span_share_measurement_key():
    source = Source()
    args = source.args()
    args["measured"] = deepcopy(args["nominal"])
    alias = "source_" + "2"*24
    args["measured"]["witness"]["source_ref"] = alias
    def authorized(reference, representation):
        assert reference in (source.reference, alias) and representation == "original"
        return {"artifact_ref": source.artifact, "content": source.content}
    extracted = read_calibration_recovery_inputs(args, read_source=authorized)
    assert len(extracted["source_refs"]) == 2
    sheet = populate_calibration_recovery(extracted)
    assert len(sheet["cells"]["recovery"]["input_measurement_keys"]) == 1
    assert sheet["cells"]["recovery"]["value"] == 1


def test_ratio_underflow_is_not_silent_zero_and_partial_values_survive():
    source = Source(nominal="1e300", measured="1e-300", recovery="0")
    _, sheet = run(source, source.args(nominal="1e300", measured="1e-300", recovery="0"))
    assert sheet["cells"]["nominal"]["value"] == 1e300
    assert sheet["cells"]["measured"]["value"] == 1e-300
    assert sheet["cells"]["recovery"]["value"] is None
    assert sheet["cells"]["recovery"]["unavailable_reason"] == "numerical_model_range"
    assert sheet["cells"]["inverse_recovery"]["unavailable_reason"] == "numerical_model_range"


def test_missing_recovery_unit_keeps_literal_reported_number():
    source = Source()
    args = source.args(); args["reported_recovery_unit"] = None
    extracted, sheet = run(source, args)
    assert extracted["observations"]["reported_recovery"]["native_value"] == 98
    assert sheet["cells"]["reported_recovery"]["value"] is None
    assert sheet["cells"]["reported_recovery"]["unavailable_reason"] == "reported_recovery_unit_not_supplied"


def test_reported_fraction_recovery_remains_fraction():
    source = Source(recovery="0.98", recovery_unit="fraction")
    _, sheet = run(source, source.args(recovery="0.98", recovery_unit="fraction"))
    assert sheet["cells"]["reported_recovery"]["value"] == .98


def test_wrong_unit_multiplier_rejected_before_arithmetic():
    source = Source()
    extraction, _ = run(source)
    extraction["shared_unit"]["multiplier"] = {"numerator": "1000", "denominator": "1"}
    with pytest.raises(ExperimentalContractError, match="calibration_unit_record_mismatch"):
        populate_calibration_recovery(extraction)


def test_dimensionless_one_unit_cannot_be_cut_from_larger_number():
    source = Source(nominal="11")
    args = source.args(nominal="11")
    args["reported_recovery_unit"] = {"value": "fraction", "witness": source.witness("1", occurrence=1)}
    with pytest.raises(ExperimentalContractError, match="partial_source_unit"):
        run(source, args)


@pytest.mark.parametrize("printed", ["0.1", "1.2", "-1", "+1", "−1", "1e2", "2e1", "1+2", "1-2"])
def test_dimensionless_one_unit_requires_complete_numeric_token(printed):
    source = Source(recovery_unit=printed)
    args = source.args(recovery_unit=printed)
    args["reported_recovery_unit"] = {"value": "fraction", "witness": source.witness("1")}
    with pytest.raises(ExperimentalContractError, match="partial_source_unit"):
        run(source, args)


@pytest.mark.parametrize("printed", ["fraction", "dimensionless", "1"])
def test_complete_dimensionless_unit_tokens(printed):
    source = Source(recovery="0.98", recovery_unit=printed)
    _, sheet = run(source, source.args(recovery="0.98", recovery_unit=printed))
    assert sheet["cells"]["reported_recovery"]["value"] == .98


@pytest.mark.parametrize("printed,selected", [("nonfraction", "fraction"), ("dimensionlessness", "dimensionless")])
def test_word_dimensionless_units_cannot_be_clipped(printed, selected):
    source = Source(recovery_unit=printed)
    args = source.args(recovery_unit=printed)
    args["reported_recovery_unit"] = {"value": "fraction", "witness": source.witness(selected)}
    with pytest.raises(ExperimentalContractError, match="partial_source_unit"):
        run(source, args)


@pytest.mark.parametrize("printed", ["-<br/>1", ".<br/>1", "1<br/>.2", "2e<br/>1"])
def test_dimensionless_one_unit_preserves_soft_break_numeric_context(printed):
    source = Source(recovery_unit=printed)
    args = source.args(recovery_unit=printed)
    args["reported_recovery_unit"] = {"value": "fraction", "witness": source.witness("1")}
    with pytest.raises(ExperimentalContractError, match="partial_source_unit"):
        run(source, args)


@pytest.mark.parametrize("printed", ["unit: 1", "unit: <br/>1", " 1 "])
def test_separate_same_field_dimensionless_one_unit_remains_supported(printed):
    source = Source(recovery="0.98", recovery_unit=printed)
    args = source.args(recovery="0.98", recovery_unit=printed)
    args["reported_recovery_unit"] = {"value": "fraction", "witness": source.witness("1")}
    _, sheet = run(source, args)
    assert sheet["cells"]["reported_recovery"]["value"] == .98


def test_adjacent_amount_and_unit_without_space_remains_supported():
    source = Source()
    source.text = source.text.replace("<td>9.8 ± 0.2</td>", "<td>9.8nmol ± 0.2nmol</td>")
    source.content = source.text.encode("utf-8")
    source.artifact = "artifact_" + hashlib.sha256(source.content).hexdigest()
    args = Source().args()
    args["measured"] = source.number("9.8")
    args["measured_spread"] = source.number("0.2")
    args["reported_recovery"] = source.number("98")
    _, sheet = run(source, args)
    assert sheet["cells"]["measured"]["value"] == 9.8
    assert sheet["cells"]["measured_sd"]["value"] == .2


@pytest.mark.parametrize('unit,factor', [('pmole', Fraction(1,1000)), ('nmole', Fraction(1)),
    ('umole', Fraction(1000)), ('µmole', Fraction(1000)), ('μmole', Fraction(1000))])
def test_complete_legacy_amount_unit_spelling_preserves_source_and_scale(unit, factor):
    source = Source(unit=unit)
    extracted, sheet = run(source, source.args(unit=unit))
    assert extracted['shared_unit']['raw_unit'] == unit
    assert extracted['shared_unit']['unit'] == 'nmol'
    assert Fraction(int(extracted['observations']['nominal']['exact_value']['numerator']),
        int(extracted['observations']['nominal']['exact_value']['denominator'])) == 10*factor
    assert sheet['cells']['recovery']['value'] == .98


@pytest.mark.parametrize('unit', ['pmole/min', 'nmole/min', 'umole/min', 'µmole/min', 'μmole/min',
    'nmole min−1', 'nmole min<sup>−1</sup>'])
def test_complete_legacy_activity_unit_spelling(unit):
    source = Source(unit=unit); args = source.args(unit=unit)
    args['control_kind'] = source.interpretation('enzyme_activity_spike', 'enzyme activity spike')
    extracted, sheet = run(source, args)
    assert extracted['shared_unit']['raw_unit'] == unit
    assert extracted['shared_unit']['unit'] == 'nmol/min'
    assert sheet['section'] == 'matrix_activity_response' and sheet['cells']['recovery']['value'] == .98


@pytest.mark.parametrize('unit', ['nmole', 'µmole/min'])
def test_adjacent_explicit_legacy_unit_matches_header(unit):
    source = Source(measured='9.8'+unit, unit=unit)
    args = source.args(measured='9.8'+unit, unit=unit)
    args['measured'] = source.number_in('9.8', '<td>9.8'+unit+' ± 0.2</td>')
    if '/min' in unit:
        args['control_kind'] = source.interpretation('enzyme_activity_spike', 'enzyme activity spike')
    extracted, sheet = run(source, args)
    assert extracted['observations']['measured']['raw_number'] == '9.8'
    assert sheet['cells']['recovery']['value'] == .98


def test_legacy_amount_unit_cannot_be_clipped_to_modern_spelling():
    source = Source(unit='nmole'); args = source.args(unit='nmole')
    args['shared_unit'] = source.witness('nmol')
    with pytest.raises(ExperimentalContractError, match='partial_source_unit'):
        run(source, args)


@pytest.mark.parametrize('unit', ['nmole/min/mg', 'nmolesterol', 'nmole/minute'])
def test_legacy_units_preserve_compound_and_word_rejections(unit):
    source = Source(unit=unit)
    with pytest.raises(ExperimentalContractError, match='unsupported_calibration_unit'):
        run(source, source.args(unit=unit))


@pytest.mark.parametrize('unit', ['nmole', 'nmole/min', 'µmole', 'μmole/min',
    'pmole', 'mmole', 'nmole min−1', 'nmol'])
def test_dimensional_legacy_units_cannot_be_reported_dimensionless_recovery(unit):
    source = Source(recovery='98'+unit)
    args = source.args(recovery='98'+unit)
    args['reported_recovery'] = source.number_in('98', '<td>98'+unit+'</td>')
    with pytest.raises(ExperimentalContractError, match='explicit_recovery_unit_mismatch'):
        run(source, args)
