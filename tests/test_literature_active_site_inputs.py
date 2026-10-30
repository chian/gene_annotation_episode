"""Synthetic metrology contrasts; these are not primary-paper measurements."""
from copy import deepcopy
from fractions import Fraction

import pytest

from gene_annotation_episode.literature_active_site_inputs import (
    LITERAL_FIELDS, INTERPRETATIONS, read_active_site_inputs, validate_active_site_extraction)
from gene_annotation_episode.literature_active_site_calculations import populate_active_site_components
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

SOURCE = "source_" + "1" * 24
ARTIFACT = "artifact_" + "2" * 64
TEXT = ("Synthetic subject enzyme from organism X, construct tagged, preparation stock A; assay titration at 55 C. "
    "Mass 4 ng/uL; monomer molecular weight assumed 40 kDa; active sites 60 ± 3 nM; reported active fraction 60%. "
    "Same preparation and assay. Nominal titrant; one-to-one titrant site design; one site per monomer. "
    "Rate already active normalized. Regression SD; repeated aliquots from same preparation. Purification also changed.")


def witness(text, quote, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"source_ref": SOURCE, "representation": "original", "start": len(text[:start].encode()),
        "end": len(text[:start + len(quote)].encode()), "quote": quote}


def fixture(text=TEXT, mass=("4 ng/uL", "4", "ng/uL"), mw=("40 kDa", "40", "kDa"),
        active=("60 ± 3 nM", "60", "nM"), reported=("60%", "60", "%")):
    w = lambda quote: witness(text, quote)
    def meaning(value, quote="Same preparation and assay"):
        return {"value": value, "witnesses": [] if value in ("unknown", "unreported") else [w(quote)]}
    def measurement(item):
        quote, token, unit = item
        broad = w(quote)
        unit_start = text.index(quote) + quote.rindex(unit)
        return {"number": {"witness": broad, "number_start": quote.rindex(token) if token == "3" else quote.index(token), "number_end": (quote.rindex(token) if token == "3" else quote.index(token)) + len(token)},
            "unit": {**broad, "start": len(text[:unit_start].encode()), "end": len(text[:unit_start + len(unit)].encode()), "quote": unit}}
    def quantity(item):
        return {**dict.fromkeys(LITERAL_FIELDS), "subject": w("subject enzyme"), "organism": w("organism X"),
            "construct": w("construct tagged"), "preparation": w("preparation stock A"), "assay": w("assay titration"),
            "condition": w("55 C"), "endpoint": w("active sites"), "measurement": measurement(item),
            "qualification": meaning("reported_point"),
            "reported_uncertainty": {"kind": meaning("unreported"), "measurement": None,
                "sampling_basis": meaning("unknown"), "statement": None}}
    values = {"molecular_basis": "per_monomer", "amount_linkage": "same_preparation_and_assay",
        "active_estimate_meaning": "titrated_active_sites", "titrant_concentration_basis": "nominal_reported",
        "titrant_to_site_stoichiometry": "reported_one_to_one", "site_stoichiometry": "one_site_per_monomer", "normalization_stage": "active_sites"}
    args = {"source_ref": SOURCE, "source_kind": "synthetic_fixture", "experiment": w("assay titration"),
        "intended_change": w("construct tagged"), "other_changes": [w("Purification also changed")],
        "interpretations": {field: meaning(values[field]) for field in INTERPRETATIONS},
        "quantities": {role: quantity(item) for role, item in zip(("protein_mass_concentration", "assumed_molecular_weight", "active_site_concentration", "reported_active_fraction"), (mass, mw, active, reported))}}
    args["quantities"]["active_site_concentration"]["reported_uncertainty"] = {"kind": meaning("regression_sd", "Regression SD"),
        "measurement": measurement((active[0], "3", active[2])), "sampling_basis": meaning("same_preparation_aliquots", "repeated aliquots from same preparation"),
        "statement": w("Regression SD; repeated aliquots from same preparation")}
    sources = {SOURCE: {"artifact_ref": ARTIFACT, "content": text.encode()}}
    return args, sources, lambda reference, representation: deepcopy(sources[reference])


def populated(args, reader):
    extraction = read_active_site_inputs(args, read_source=reader)
    validate_active_site_extraction(extraction)
    return extraction, populate_active_site_components(extraction)


def test_source_physical_denominator_components_separate_rounded_fraction_uncertainty_and_rate():
    args, _, reader = fixture()
    extraction, sheet = populated(args, reader)
    cells = sheet["cells"]
    assert cells["protein_mass_concentration"]["value"] == .004
    assert cells["total_monomer_concentration"]["value"] == 100
    assert cells["sites_per_total_monomer"]["value"] == .6
    factor = cells["conditional_nominal_to_active_denominator_factor"]
    assert factor["value"] == float(Fraction(5, 3))
    assert Fraction(factor["reported_domain"]["lower"]) <= Fraction(5, 3) <= Fraction(factor["reported_domain"]["upper"])
    assert cells["derived_minus_reported_fraction"]["value"] == 0
    assert extraction["quantities"]["active_site_concentration"]["reported_uncertainty"]["kind"]["value"] == "regression_sd"
    assert sheet["fraction_uncertainty"]["reason"] == "full_joint_covariance_propagation_not_implemented"
    assert not sheet["rate_factor_applied"] and sheet["independent_preparation_count"] is None
    assert sheet["annotation_credit"] is None


@pytest.mark.parametrize("field", ["amount_linkage", "molecular_basis", "active_estimate_meaning", "titrant_to_site_stoichiometry", "titrant_concentration_basis"])
def test_unknown_interpretation_keeps_individual_estimates_without_invented_defaults(field):
    args, _, reader = fixture()
    args["interpretations"][field] = {"value": "unknown", "witnesses": []}
    _, sheet = populated(args, reader)
    assert sheet["cells"]["active_site_concentration"]["value"] == 60
    assert sheet["cells"]["protein_mass_concentration"]["value"] == .004
    assert sheet["cells"]["conditional_nominal_to_active_denominator_factor"]["unavailable_reason"] == field + "_unknown"


def test_unknown_sites_per_monomer_keeps_density_and_factor():
    args, _, reader = fixture()
    args["interpretations"]["site_stoichiometry"] = {"value": "unknown", "witnesses": []}
    _, sheet = populated(args, reader)
    assert sheet["cells"]["sites_per_total_monomer"]["value"] == .6
    assert sheet["cells"]["conditional_active_monomer_fraction"]["unavailable_reason"] == "site_stoichiometry_unknown"
    assert sheet["cells"]["conditional_nominal_to_active_denominator_factor"]["value"] == float(Fraction(5, 3))


@pytest.mark.parametrize("role,unit", [("protein_mass_concentration", "nM"), ("assumed_molecular_weight", "ng/uL"), ("active_site_concentration", "kDa")])
def test_borrowed_units_are_rejected(role, unit):
    args, _, reader = fixture()
    args["quantities"][role]["measurement"]["unit"] = witness(TEXT, unit)
    with pytest.raises(ExperimentalContractError, match="source_active_site_unit_mismatch"):
        populated(args, reader)


@pytest.mark.parametrize("role,unit", [("protein_mass_concentration", "g/uL"), ("assumed_molecular_weight", "Da"), ("active_site_concentration", "M")])
def test_unit_substrings_cannot_hide_prefixes(role, unit):
    args, _, reader = fixture()
    args["quantities"][role]["measurement"]["unit"] = witness(TEXT, unit)
    with pytest.raises(ExperimentalContractError, match="partial_source_active_site_unit"):
        populated(args, reader)


def test_unknown_unit_and_missing_input_leave_usable_partial_results():
    args, _, reader = fixture()
    args["quantities"]["assumed_molecular_weight"]["measurement"]["unit"] = None
    _, sheet = populated(args, reader)
    assert sheet["cells"]["total_monomer_concentration"]["unavailable_reason"] == "source_unit_unreported"
    assert sheet["cells"]["active_site_concentration"]["value"] == 60
    args["quantities"]["protein_mass_concentration"] = None
    _, sheet = populated(args, reader)
    assert sheet["cells"]["protein_mass_concentration"]["value"] is None
    assert sheet["cells"]["reported_active_fraction"]["value"] == .6


def test_source_rounding_is_not_silently_reconciled_and_bound_is_not_point():
    text = TEXT.replace("reported active fraction 60%", "reported active fraction 61%")
    args, _, reader = fixture(text, reported=("61%", "61", "%"))
    _, sheet = populated(args, reader)
    assert sheet["cells"]["reported_active_fraction"]["value"] == .61
    assert sheet["cells"]["derived_minus_reported_fraction"]["value"] == -.01
    text = TEXT.replace("active sites 60 ± 3 nM", "active sites >60 ± 3 nM")
    args, _, reader = fixture(text)
    _, sheet = populated(args, reader)
    assert sheet["cells"]["sites_per_total_monomer"]["value"] is None
    assert sheet["cells"]["sites_per_total_monomer"]["reported_domain"]["lower"] <= .6
    assert not sheet["cells"]["sites_per_total_monomer"]["exact_domain"]["lower_inclusive"]


def test_biological_fraction_intersection_is_explicit_and_strict_impossible_edge_unavailable():
    text = TEXT.replace("active sites 60 ± 3 nM", "active sites >100 ± 3 nM")
    args, _, reader = fixture(text, active=("100 ± 3 nM", "100", "nM"))
    _, sheet = populated(args, reader)
    assert sheet["cells"]["sites_per_total_monomer"]["exact_domain"]["lower"] == {"numerator": "1", "denominator": "1"}
    assert not sheet["cells"]["sites_per_total_monomer"]["exact_domain"]["lower_inclusive"]
    assert sheet["cells"]["conditional_active_monomer_fraction"]["unavailable_reason"] == "active_fraction_exceeds_one"
    text = TEXT.replace("active sites 60 ± 3 nM", "active sites <160 ± 3 nM")
    args, _, reader = fixture(text, active=("160 ± 3 nM", "160", "nM"))
    _, sheet = populated(args, reader)
    assert sheet["cells"]["sites_per_total_monomer"]["exact_domain"]["upper"] == {"numerator": "8", "denominator": "5"}
    fraction = sheet["cells"]["conditional_active_monomer_fraction"]
    assert fraction["exact_domain"]["upper"] == {"numerator": "1", "denominator": "1"}
    assert fraction["exact_domain"]["upper_inclusive"]
    assert "physical_one_site_fraction_in_unit_interval" in fraction["conditional_on"]


def test_unsupported_complete_source_unit_is_reader_partial_not_claimed_paper_omission():
    text = TEXT.replace("4 ng/uL", "4 mg/L")
    args, _, reader = fixture(text, mass=("4 mg/L", "4", "mg/L"))
    _, sheet = populated(args, reader)
    assert sheet["cells"]["protein_mass_concentration"]["unavailable_reason"] == "unsupported_source_unit"
    assert sheet["cells"]["total_monomer_concentration"]["unavailable_reason"] == "unsupported_source_unit"
    assert sheet["cells"]["active_site_concentration"]["value"] == 60


@pytest.mark.parametrize("token,unit", [("60", "nmol/L"), ("0.060", "µmol/L"), ("0.000060", "mmol/L"), ("0.000000060", "mol/L")])
def test_active_concentration_amount_per_litre_units_keep_original_source(token, unit):
    raw = token + " ± 3 " + unit
    text = TEXT.replace("60 ± 3 nM", raw)
    args, _, reader = fixture(text, active=(raw, token, unit))
    extraction, sheet = populated(args, reader)
    assert extraction["quantities"]["active_site_concentration"]["unit"]["raw_unit"] == unit
    assert sheet["cells"]["active_site_concentration"]["value"] == 60
    assert sheet["cells"]["sites_per_total_monomer"]["value"] == .6


def test_amount_per_litre_unit_cannot_be_clipped_or_borrowed():
    text = TEXT.replace("60 ± 3 nM", "60 ± 3 nmol/L")
    args, _, reader = fixture(text, active=("60 ± 3 nmol/L", "60", "nmol/L"))
    args["quantities"]["active_site_concentration"]["measurement"]["unit"] = witness(text, "mol/L")
    with pytest.raises(ExperimentalContractError, match="partial_source_active_site_unit"):
        populated(args, reader)
