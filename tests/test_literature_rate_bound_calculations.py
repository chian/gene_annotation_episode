"""Reported-constraint arithmetic on constructed finite table inputs."""
from copy import deepcopy
import csv
from fractions import Fraction
import io
import json

import pytest

from gene_annotation_episode.literature_experimental_contracts import HEADERS, ExperimentalContractError
from gene_annotation_episode.literature_rate_reader import read_rate_table
from gene_annotation_episode.literature_rate_bound_calculations import populate_rate_table_bounds


def extraction(a="7", b="<.01", *, changes=None, extra=()):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(HEADERS)
    rows = [{"arm": "complete", "condition": "with substrate", "value": a},
            {"arm": "omitted", "condition": "without substrate", "value": b, **(changes or {})}, *extra]
    for changes in rows:
        row = dict(zip(HEADERS, ("Constructed complex", "assay", "complete", "with substrate",
            "NADH oxidation", "per mg preparation", "7", "umol/min/mg", "unreported", "", "", "unspecified", "synthetic")))
        row.update(changes)
        writer.writerow([row[name] for name in HEADERS])
    return read_rate_table({"source_ref": "source_fixture", "artifact_ref": "artifact_fixture",
        "representation": "synthetic_fixture", "delimiter": "\t", "text": stream.getvalue()},
        expected_subject="Constructed complex", expected_experiment="assay")


def calculate(data=None):
    return populate_rate_table_bounds(extraction() if data is None else data,
        reference_arm="complete", test_arm="omitted", reference_condition="with substrate",
        test_condition="without substrate")


def bounds(cell):
    return cell["lower"], cell["upper"], cell["lower_closed"], cell["upper_closed"]


def test_one_sided_detection_limit_remains_strict_through_actual_numeric_contrasts():
    data = extraction(); before = deepcopy(data)
    result = calculate(data); cells = result["cells"]
    assert cells["reference_rate"]["value"] == 7
    assert bounds(cells["test_rate"]) == (None, .01, False, False)
    assert cells["rate_difference"]["lower"] == pytest.approx(6.99)
    assert cells["rate_difference"]["upper"] is None and not cells["rate_difference"]["lower_closed"]
    assert cells["retained_fraction"]["upper"] == pytest.approx(1/700)
    assert cells["retained_fraction"]["lower"] is None and not cells["retained_fraction"]["upper_closed"]
    assert cells["fractional_decrease"]["lower"] == pytest.approx(699/700)
    assert cells["fractional_decrease"]["upper"] is None and not cells["fractional_decrease"]["lower_closed"]
    assert cells["fractional_decrease"]["exact_lower"] == {"numerator": "699", "denominator": "700"}
    assert cells["fractional_decrease"]["value"] is None
    assert cells["fractional_decrease"]["status"] == "bounded"
    assert cells["fractional_decrease"]["bound_kind"] == "reported_constraint_image_outer_bound"
    assert result["sampling_confidence_interval"] is result["assay_error_probability"] is result["annotation_credit"] is None
    assert result["source_uncertainty"]["reference"]["count"] is None
    assert data == before
    assert calculate(json.loads(json.dumps(data))) == result


def test_point_comparison_is_a_point_and_does_not_invent_uncertainty():
    cells = calculate(extraction("12", ".6"))["cells"]
    assert cells["retained_fraction"]["value"] == pytest.approx(.05)
    assert cells["fractional_decrease"]["value"] == pytest.approx(.95)
    assert cells["rate_difference"]["value"] == pytest.approx(11.4)
    assert bounds(cells["fractional_decrease"]) == (.95, .95, True, True)


@pytest.mark.parametrize("a,b,expected", (
    (">=2", "<=4", (None, 2, False, True)),
    (">2", ">=1", (0, None, False, False)),
    ("<-2", ">=1", (None, 0, False, False)),
    ("<0", "0", (0, 0, True, True)),
    (">0", "<0", (None, 0, False, False)),
    (">=2", "-1", (-.5, 0, True, False)),
    ("-4", "-2", (.5, .5, True, True)),
    ("<=-2", ">=0", (None, 0, False, True)),
    (">2", "0", (0, 0, True, True)),
))
def test_interval_division_preserves_sign_unboundedness_and_attainable_zero(a, b, expected):
    assert bounds(calculate(extraction(a, b))["cells"]["retained_fraction"]) == expected


@pytest.mark.parametrize("reference", ("0", ">=-1", "<=1", ">=0", "<=0"))
def test_denominator_admitting_zero_does_not_fabricate_a_contiguous_ratio(reference):
    cells = calculate(extraction(reference, "2"))["cells"]
    assert cells["rate_difference"]["status"] != "unavailable"
    assert cells["retained_fraction"]["unavailable_reason"] == "reference_domain_includes_zero"
    assert cells["reference_rate"]["status"] != "unavailable"


@pytest.mark.parametrize("change,reason", (({"endpoint": "TTC reduction"}, "endpoint_mismatch"),
    ({"normalization": "per enzyme molecule"}, "normalization_mismatch"),
    ({"unit": "uM/min"}, "incompatible_rate_dimensions")))
def test_different_scientific_quantities_keep_individual_values_without_a_contrast(change, reason):
    cells = calculate(extraction(b="2", changes=change))["cells"]
    assert cells["reference_rate"]["value"] == 7
    assert cells["test_rate"]["value"] == 2
    assert cells["rate_difference"]["value"] is None
    assert cells["rate_difference"]["unavailable_reason"] == reason


def test_compatible_unit_conversion_applies_to_limits_and_points():
    cells = calculate(extraction(b="<10", changes={"unit": "nmol/min/mg"}))["cells"]
    assert cells["test_rate"]["upper"] == pytest.approx(.01)
    assert cells["rate_difference"]["lower"] == pytest.approx(6.99)
    assert cells["rate_difference"]["unit"] == "umol/min/mg"


def test_missing_is_unknown_and_approximation_is_visible():
    cells = calculate(extraction(b=""))["cells"]
    assert cells["reference_rate"]["value"] == 7
    assert cells["rate_difference"]["unavailable_reason"] == "source_measurement_unavailable"
    approximate = calculate(extraction(b="~<.01"))["cells"]["fractional_decrease"]
    assert approximate["approximate"] is True
    assert approximate["lower"] == pytest.approx(699/700)


def test_multiple_reported_summaries_are_not_averaged_as_replicates():
    cells = calculate(extraction(extra=({"arm": "complete", "value": "8"},)))["cells"]
    assert cells["reference_rate"]["unavailable_reason"] == "ambiguous_reference_arm"
    assert cells["test_rate"]["upper"] == pytest.approx(.01)


def test_unrepresentable_finite_bound_is_not_reported_as_unbounded_or_zero():
    cells = calculate(extraction("1e-320", "1e308"))["cells"]
    ratio = cells["retained_fraction"]
    assert ratio["status"] == "unavailable" and ratio["unavailable_reason"] == "numerical_model_range"
    assert ratio["exact_lower"] is not None and ratio["exact_upper"] is not None
    assert ratio["lower"] is ratio["upper"] is None


def test_constraint_images_contain_actual_maps_on_independent_finite_grid():
    # Independent check of containment over signed finite samples, including
    # source half-lines. These samples are not source observations or replicates.
    cases = ((">=2", "<=4", [2, 3, 10], [-5, 0, 4]),
             ("<-2", ">=1", [-20, -3], [1, 3, 20]),
             (">0", "<0", [Fraction(1,10), 1, 10], [-10, -1, Fraction(-1,10)]))
    for a, b, av, bv in cases:
        cells = calculate(extraction(a,b))["cells"]
        for x in av:
            for y in bv:
                for component, value in (("rate_difference", x-y), ("retained_fraction", y/x),
                                          ("fractional_decrease", 1-y/x)):
                    cell = cells[component]
                    assert cell["lower"] is None or value >= cell["lower"]
                    assert cell["upper"] is None or value <= cell["upper"]


def test_native_v2_is_an_explicit_unimplemented_binding_not_silent_conversion():
    with pytest.raises(ExperimentalContractError, match="table_v1_extraction_required"):
        calculate({"version": "a105_rate_extraction_v2"})


def test_exact_source_decimals_survive_rounded_float_projections():
    cells = calculate(extraction("10000000000000001", "10000000000000000"))["cells"]
    assert cells["reference_rate"]["value"] == cells["test_rate"]["value"] == 1e16
    assert cells["rate_difference"]["value"] == 1
    assert cells["rate_difference"]["exact_lower"] == {"numerator":"1", "denominator":"1"}


def test_tiny_source_threshold_is_not_silently_promoted_to_exact_zero():
    cells = calculate(extraction("1", "<1e-9999"))["cells"]
    assert cells["test_rate"]["status"] == "unavailable"
    assert cells["test_rate"]["unavailable_reason"] == "numerical_model_range"
    assert cells["test_rate"]["exact_upper"]["numerator"] == "1"
    assert cells["test_rate"]["exact_upper"]["denominator"].startswith("1"+"0"*100)
    # Its exact fractional decrease remains a valid source-derived bound even
    # when its float endpoint rounds to1. The exact rational is retained.
    assert cells["fractional_decrease"]["exact_lower"]["numerator"] != "1"


def test_unbounded_constraint_image_is_distinct_from_missing_input():
    cells = calculate(extraction("<2", "<4"))["cells"]
    assert cells["rate_difference"]["status"] == "unbounded"
    assert bounds(cells["rate_difference"]) == (None,None,False,False)
    assert cells["rate_difference"]["unavailable_reason"] is None


def test_edited_extraction_number_cannot_disagree_with_its_retained_literal_row():
    data = extraction();data["rows"][0]["value"] = 100
    with pytest.raises(ExperimentalContractError,match="source_operand_binding_mismatch"):
        calculate(data)


def test_projected_float_bounds_are_outward_images_of_exact_rationals():
    for cell in calculate()["cells"].values():
        if cell["status"] != "bounded":continue
        for side in ("lower","upper"):
            exact = cell['exact_'+side]
            if exact is None:continue
            rational = Fraction(int(exact['numerator']),int(exact['denominator']))
            if side == 'lower':assert Fraction(cell[side]) <= rational
            else:assert Fraction(cell[side]) >= rational
