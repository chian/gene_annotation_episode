"""Synthetic source witnesses exercise amount meanings, units and covariance."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.literature_amount_inputs import read_amount_inputs, LITERAL_FIELDS
from gene_annotation_episode.literature_amount_calculations import populate_amount_components
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


SOURCE = "source_" + "1" * 24
COV_SOURCE = "source_" + "2" * 24
ARTIFACT = "artifact_" + "1" * 24
TEXT = ("The same unnamed stock: target estimated by band intensity at an approximate concentration of 5 mg/ml; "
        "total protein estimated by Bradford analysis at 7 mg/ml. Separate nominal arms use 8.4 uM HFP and 8.8 uM IMP.")


def witness(text, quote, *, reference=SOURCE, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"source_ref": reference, "representation": "original", "start": len(text[:start].encode()),
        "end": len(text[:start + len(quote)].encode()), "quote": quote}


def meaning(value, text=TEXT, quote="same unnamed stock"):
    return {"value": value, "witnesses": [] if value in ("unknown", "unreported") else [witness(text, quote)]}


def selected(text, quote, number, unit, role, *, qualification="reported_point"):
    return {**dict.fromkeys(LITERAL_FIELDS),
        "measurement": {"number": {"witness": witness(text, quote), "number_start": quote.index(number),
            "number_end": quote.index(number) + len(number)},
            "unit": witness(text, unit, occurrence=text[:text.index(quote)].count(unit)) if unit else None},
        "amount_role": meaning(role, text, quote), "amount_kind": meaning("estimated", text, quote),
        "qualification": meaning(qualification, text, quote), "basis_status": meaning("supported", text, quote),
        "reported_uncertainty": {"kind": meaning("unreported"), "statement": None}}


def fixture(text=TEXT, first="5 mg/ml", second="7 mg/ml", n="5", d="7", nunit="mg/ml", dunit="mg/ml"):
    args = {"source_ref": SOURCE, "source_kind": "synthetic_fixture", "experiment": None, "intended_change": None,
        "comparison_kind": meaning("stock_target_mass_estimate_over_total_mass_estimate", text, first),
        "pair_relationship": meaning("supported", text, first), "stock_relationship": meaning("same", text, first),
        "quantities": {
            "numerator": selected(text, first, n, nunit, "target_mass_estimate"),
            "denominator": selected(text, second, d, dunit, "total_protein_mass_estimate")},
        "covariance_source_ref": None}
    sources = {SOURCE: {"artifact_ref": ARTIFACT, "content": text.encode()}}
    def reader(reference, representation):
        assert representation in ("original", "text")
        return deepcopy(sources[reference])
    return args, sources, reader


def add_covariance(args, sources, reader, matrix=((.25, .1), (.1, .49))):
    first = read_amount_inputs(args, read_source=reader)
    quantities = first["quantities"]
    data = {"version": "a105_amount_covariance_v1", "quantity_order": ["numerator", "denominator"],
        "quantity_measurement_keys": [quantities[role]["measurement_key"] for role in quantities],
        "quantity_physical_observation_keys": [quantities[role]["physical_observation_key"] for role in quantities],
        "quantity_owner_keys": [quantities[role]["owner_key"] for role in quantities],
        "quantity_units": [quantities[role]["unit"]["raw_unit"] for role in quantities],
        "covariance": [list(row) for row in matrix], "origin": "synthetic", "variance_status": "estimated"}
    sources[COV_SOURCE] = {"artifact_ref": "artifact_" + "2" * 24, "content": json.dumps(data).encode()}
    args["covariance_source_ref"] = COV_SOURCE
    return data


def test_nonadjacent_prose_approximation_is_source_qualified_without_erasing_literal():
    args, _, reader = fixture()
    q = args["quantities"]["numerator"]
    q["qualification"] = meaning("source_qualified_approximate", TEXT, "an approximate concentration of 5 mg/ml")
    result = read_amount_inputs(args, read_source=reader)
    assert result["quantities"]["numerator"]["number"]["raw_number"] == "5"
    assert result["quantities"]["numerator"]["number"]["approximate"] is False
    assert result["quantities"]["numerator"]["approximate"]
    sheet = populate_amount_components(result["calculation_inputs"])
    assert sheet["cells"]["amount_ratio"]["value"] == 5 / 7
    assert sheet["cells"]["amount_ratio"]["approximate"]
    assert result["calculation_inputs"]["covariance"] is None


def test_actual_relationships_need_witnesses_but_no_public_subject_name_or_stock_name():
    args, _, reader = fixture()
    result = read_amount_inputs(args, read_source=reader)
    assert result["quantities"]["numerator"]["meanings"]["subject"] is None
    assert result["quantities"]["numerator"]["meanings"]["stock"] is None
    assert populate_amount_components(result["calculation_inputs"])["cells"]["amount_ratio"]["value"] == 5 / 7
    args["pair_relationship"]["witnesses"] = []
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        read_amount_inputs(args, read_source=reader)


@pytest.mark.parametrize("prefix,bound,approximate", [("<", "lt", False), (">=", "ge", False),
    ("approximately ", "none", True), ("about >", "gt", True), ("&lt;", "lt", False)])
def test_lexical_bounds_or_approximation_survive_reported_point_selection(prefix, bound, approximate):
    text = f"Stock target {prefix}5 mg/ml; total 7 mg/ml."
    args, _, reader = fixture(text)
    result = read_amount_inputs(args, read_source=reader)
    row = result["quantities"]["numerator"]
    assert row["bound"] == bound
    assert row["approximate"] is approximate
    assert row["qualification"]["value"] == "reported_point"
    cell = populate_amount_components(result["calculation_inputs"])["cells"]["amount_ratio"]
    assert (cell["value"] is None) == (bound != "none")


@pytest.mark.parametrize("text,first,n,unit,error", [
    ("Stock target 15 mg/ml; total 7 mg/ml.", "5 mg/ml", "5", "mg/ml", "partial_source_numeric_token"),
    ("Stock target 1/5 mg/ml; total 7 mg/ml.", "5 mg/ml", "5", "mg/ml", "source_arithmetic_expression_unsupported"),
    ("Stock target 5 × 10 mg/ml; total 7 mg/ml.", "5 × 10 mg/ml", "5", "mg/ml", "source_arithmetic_expression_unsupported"),
    ("Stock target 5% mg/ml; total 7 mg/ml.", "5% mg/ml", "5", "mg/ml", "source_number_unit_role_mismatch"),
    ("Stock target 5 ± 1 mg/ml; total 7 mg/ml.", "1 mg/ml", "1", "mg/ml", "uncertainty_is_not_rate_point"),
    ("Stock target 5 mg/ml/min; total 7 mg/ml.", "5 mg/ml/min", "5", "mg/ml", "partial_source_amount_unit"),
])
def test_amount_adapter_keeps_released_lexical_guards_and_owns_dimensional_guards(text, first, n, unit, error):
    args, _, reader = fixture(text, first=first, n=n, nunit=unit)
    with pytest.raises(ExperimentalContractError, match=error):
        read_amount_inputs(args, read_source=reader)


@pytest.mark.parametrize("raw,number,unit,expected", [
    ("5000 ug/ml", "5000", "ug/ml", 5), ("5 g/L", "5", "g/L", 5),
    ("5000 mg/L", "5000", "mg/L", 5), ("5 mg ml−1", "5", "mg ml−1", 5),
])
def test_amount_specific_mass_scale_conversion(raw, number, unit, expected):
    text = f"Stock target {raw}; total 7 mg/ml."
    args, _, reader = fixture(text, first=raw, n=number, nunit=unit)
    result = read_amount_inputs(args, read_source=reader)
    assert result["calculation_inputs"]["quantities"]["numerator"]["value"] == expected
    assert result["calculation_inputs"]["quantities"]["numerator"]["unit"] == "mg/ml"
    row = result["quantities"]["numerator"]
    assert row["source_origin"] == "synthetic"
    assert row["origin"] == ("derived" if row["unit"]["multiplier"] != 1 else "synthetic")
    assert populate_amount_components(result["calculation_inputs"])["cells"]["numerator_amount"]["origin"] == row["origin"]


def test_amount_units_cannot_be_borrowed_from_a_differently_dimensioned_number():
    text = "Stock target 5 uM; total 7 mg/ml."
    args, _, reader = fixture(text, first="5 uM", nunit="mg/ml")
    with pytest.raises(ExperimentalContractError, match="source_amount_unit_mismatch"):
        read_amount_inputs(args, read_source=reader)


def test_per_measurement_method_is_not_a_hidden_physical_denominator():
    text = "Stock target 5 mg/ml; total 7 mg/ml per Bradford analysis."
    args, _, reader = fixture(text)
    assert read_amount_inputs(args, read_source=reader)["quantities"]["denominator"]["value"] == 7
    text = "Stock target 5 mg/ml per min; total 7 mg/ml."
    args, _, reader = fixture(text)
    with pytest.raises(ExperimentalContractError, match="partial_source_amount_unit"):
        read_amount_inputs(args, read_source=reader)


def test_unknown_unit_retains_raw_number_and_other_amount_without_fabricating_conversion():
    text = "Stock target 5 arbitrary; total 7 mg/ml."
    args, _, reader = fixture(text, first="5 arbitrary", nunit="arbitrary")
    result = read_amount_inputs(args, read_source=reader)
    assert result["quantities"]["numerator"]["number"]["value"] == 5
    assert result["quantities"]["numerator"]["value"] is None
    cells = populate_amount_components(result["calculation_inputs"])["cells"]
    assert cells["denominator_amount"]["value"] == 7
    assert cells["numerator_amount"]["unavailable_reason"] == "unsupported_source_amount_unit"


def test_unknown_unit_preserves_known_inequality_without_canonical_threshold():
    from gene_annotation_episode.literature_amount_inputs import validate_amount_extraction
    text = "Stock target <5 arbitrary; total 7 mg/ml."
    args, _, reader = fixture(text, first="5 arbitrary", nunit="arbitrary")
    result = read_amount_inputs(args, read_source=reader)
    validate_amount_extraction(result)
    row = result["quantities"]["numerator"]
    assert row["bound"] == "lt" and row["status"] == "unavailable"
    cell = populate_amount_components(result["calculation_inputs"])["cells"]["numerator_amount"]
    assert cell["bound"] == "lt"
    assert cell["value"] is cell["threshold"] is cell["unit"] is None


def test_covariance_scales_both_axes_and_matches_number_and_scientific_owners():
    text = "Stock target 5000 ug/ml; total 7 mg/ml."
    args, sources, reader = fixture(text, first="5000 ug/ml", n="5000", nunit="ug/ml")
    data = add_covariance(args, sources, reader, ((250000, 100), (100, .49)))
    result = read_amount_inputs(args, read_source=reader)
    assert result["calculation_inputs"]["covariance"] == [[.25, .1], [.1, .49]]
    assert result["calculation_inputs"]["variance_status"] == "estimated"
    assert result["source_refs"] == [SOURCE, COV_SOURCE]
    cells = populate_amount_components(result["calculation_inputs"])["cells"]
    assert cells["amount_difference_variance"]["value"] == pytest.approx(.54)
    assert cells["reciprocal_amount_ratio_variance"]["value"] == pytest.approx(.028)
    # Same numeric token with a changed source-subject assertion is a different
    # scientific owner; it cannot inherit another quantity's covariance.
    args["quantities"]["numerator"]["subject"] = witness(text, "target")
    with pytest.raises(ExperimentalContractError, match="amount_covariance_owner_or_unit_mismatch"):
        read_amount_inputs(args, read_source=reader)


@pytest.mark.parametrize("field", ["quantity_order", "quantity_measurement_keys", "quantity_physical_observation_keys",
    "quantity_owner_keys", "quantity_units"])
def test_covariance_order_unit_and_physical_owner_mismatches_are_rejected(field):
    args, sources, reader = fixture()
    data = add_covariance(args, sources, reader)
    data[field][0] = "wrong"
    sources[COV_SOURCE]["content"] = json.dumps(data).encode()
    with pytest.raises(ExperimentalContractError, match="amount_covariance_owner_or_unit_mismatch"):
        read_amount_inputs(args, read_source=reader)


def test_original_and_text_alias_of_same_artifact_have_one_source_token_identity():
    args, _, reader = fixture()
    args["quantities"]["denominator"] = deepcopy(args["quantities"]["numerator"])
    args["quantities"]["denominator"]["measurement"]["number"]["witness"]["representation"] = "text"
    result = read_amount_inputs(args, read_source=reader)
    rows = result["quantities"]
    assert rows["numerator"]["measurement_key"] == rows["denominator"]["measurement_key"]
    assert populate_amount_components(result["calculation_inputs"])["cells"]["amount_ratio"]["unavailable_reason"] == "reused_source_observation"


def test_structural_html_cells_bound_lexical_context_while_inline_tags_do_not():
    text = "<table><tr><td>5</td><td>target</td><td>7</td></tr></table><p>mg/ml</p>"
    args, _, reader = fixture(text, first="5", second="7", nunit="mg/ml", dunit="mg/ml")
    result = read_amount_inputs(args, read_source=reader)
    assert result["quantities"]["numerator"]["value"] == 5
    text = "<p>target 1<i>5</i> mg/ml; total 7 mg/ml.</p>"
    args, _, reader = fixture(text, first="5</i> mg/ml")
    with pytest.raises(ExperimentalContractError, match="partial_source_numeric_token"):
        read_amount_inputs(args, read_source=reader)
