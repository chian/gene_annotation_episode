"""Independent synthetic metrology audit; no paper facts or model execution.

The controlled selections below are explicit fixtures. Their custody is real
in-memory UTF-8 text; their scientific interpretation is not an actual model
response and supplies no experimental evidence.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.literature_active_site_inputs import (
    INTERPRETATIONS, LITERAL_FIELDS, ROLES, read_active_site_inputs,
    validate_active_site_extraction,
)
from gene_annotation_episode.literature_active_site_calculations import populate_active_site_components


def synthetic_case(*, alternate_units=False, active="2", molecular_basis="per_monomer",
                   site_stoichiometry="one_site_per_monomer", missing_mw=False,
                   mass="0.3", normalization_stage="total_monomer", reported_fraction="20"):
    """Create source witnesses independently of production test helpers."""
    source_ref = "source_" + "a" * 24
    artifact_ref = "artifact_" + "b" * 24
    tokens = {
        "subject": "synthetic enzyme", "preparation": "synthetic preparation P",
        "assay": "synthetic assay Q", "context": "synthetic context witness",
        "rho_identity": "protein mass observation", "mw_identity": "molecular mass observation",
        "active_identity": "titrated site observation", "fraction_identity": "fraction observation",
        "rho": f"{('300' if alternate_units and mass == '0.3' else mass)} {'ng/uL' if alternate_units else 'mg/mL'}",
        "mw": "30000 Da" if alternate_units else "30 kDa",
        "active": f"{str(float(active) * 1000).removesuffix('.0') if alternate_units else active} {'nM' if alternate_units else 'uM'}",
        "fraction": f"{reported_fraction} %", "spread": "0.1 uM", "spread_meaning": "regression standard deviation",
    }
    text = "\n".join(f"<p>{token}</p>" for token in tokens.values())
    raw = text.encode("utf-8")

    def witness(token):
        offset = raw.index(token.encode("utf-8"))
        return {"source_ref": source_ref, "representation": "original", "start": offset,
                "end": offset + len(token.encode("utf-8")), "quote": token}

    def interpretation(value):
        return {"value": value, "witnesses": [] if value == "unknown" else [witness(tokens["context"])]}

    def measurement(token):
        number, unit = token.split(" ", 1)
        return {"number": {"witness": witness(token), "number_start": 0, "number_end": len(number)},
                "unit": witness(unit)}

    selected_interpretations = {
        "molecular_basis": molecular_basis,
        "amount_linkage": "same_preparation_and_assay",
        "active_estimate_meaning": "titrated_active_sites",
        "titrant_to_site_stoichiometry": "reported_one_to_one",
        "titrant_concentration_basis": "nominal_reported",
        "site_stoichiometry": site_stoichiometry,
        "normalization_stage": normalization_stage,
    }
    # An interface change must fail visibly, rather than silently constructing
    # an interpretation meaning different from the reviewed audit contract.
    assert set(selected_interpretations) == set(INTERPRETATIONS)
    quantities = {}
    for role, token, identity in zip(ROLES, ("rho", "mw", "active", "fraction"),
                                   ("rho_identity", "mw_identity", "active_identity", "fraction_identity")):
        row = {field: None for field in LITERAL_FIELDS}
        row.update({field: witness(tokens[field]) for field in ("subject", "preparation", "assay")})
        row.update(measurement_identity=witness(tokens[identity]), measurement=measurement(tokens[token]),
                   qualification=interpretation("reported_point"),
                   reported_uncertainty={"kind": interpretation("unreported"), "measurement": None,
                       "sampling_basis": interpretation("unknown"), "statement": None})
        if role == "active_site_concentration":
            row["reported_uncertainty"] = {"kind": {"value": "regression_sd", "witnesses": [witness(tokens["spread_meaning"])]},
                "measurement": measurement(tokens["spread"]), "sampling_basis": interpretation("same_preparation_aliquots"),
                "statement": witness(tokens["spread_meaning"])}
        quantities[role] = row
    if missing_mw:
        quantities["assumed_molecular_weight"] = None
    selection = {"source_ref": source_ref, "source_kind": "synthetic_fixture", "experiment": None,
        "intended_change": None, "other_changes": [], "quantities": quantities,
        "interpretations": {field: interpretation(value) for field, value in selected_interpretations.items()}}
    calls = []

    def read_source(reference, representation):
        assert (reference, representation) == (source_ref, "original")
        calls.append((reference, representation))
        return {"artifact_ref": artifact_ref, "content": raw}

    return selection, read_source, calls


def calculate(**options):
    selection, read_source, calls = synthetic_case(**options)
    extraction = read_active_site_inputs(selection, read_source=read_source)
    assert len(calls) == 1  # reader caches source bytes, not independent evidence
    return extraction, populate_active_site_components(extraction)


def test_equivalent_units_preserve_conditional_denominator_and_uncertainty_meanings():
    baseline_extraction, baseline = calculate()
    alternate_extraction, alternate = calculate(alternate_units=True)
    expected = {"protein_mass_concentration": 0.3, "assumed_molecular_weight": 30,
        "total_monomer_concentration": 10000, "active_site_concentration": 2000,
        "sites_per_total_monomer": 0.2, "conditional_active_monomer_fraction": 0.2,
        "conditional_nominal_to_active_denominator_factor": 5}
    for component, value in expected.items():
        assert baseline["cells"][component]["value"] == pytest.approx(value)
        assert alternate["cells"][component]["value"] == pytest.approx(value)
        assert baseline["cells"][component]["exact_domain"] == alternate["cells"][component]["exact_domain"]
    assert baseline["independent_preparation_count"] is None
    assert alternate["independent_preparation_count"] is None
    assert baseline["rate_factor_applied"] is False
    assert baseline["annotation_credit"] is None
    assert baseline["fraction_uncertainty"]["value"] is None
    spread = baseline_extraction["quantities"]["active_site_concentration"]["reported_uncertainty"]
    assert spread["kind"]["value"] == "regression_sd"
    assert spread["number"]["value"] == 0.1
    assert "active_normalized_rates_must_not_be_corrected_again" in baseline["interpretation_limits"]
    _, already_normalized = calculate(normalization_stage="active_sites")
    assert already_normalized["rate_factor_applied"] is False
    # Saved validation and recomputation consume committed selections only.
    assert validate_active_site_extraction(deepcopy(baseline_extraction)) == baseline_extraction
    assert populate_active_site_components(deepcopy(alternate_extraction)) == alternate


def test_sites_per_monomer_above_one_is_preserved_without_claiming_a_fraction():
    _, result = calculate(active="16", site_stoichiometry="other")
    cells = result["cells"]
    assert cells["sites_per_total_monomer"]["value"] == pytest.approx(1.6)
    assert cells["conditional_active_monomer_fraction"]["value"] is None
    assert cells["conditional_active_monomer_fraction"]["unavailable_reason"] == "site_stoichiometry_other"
    assert cells["conditional_nominal_to_active_denominator_factor"]["value"] == pytest.approx(0.625)
    assert result["fraction_uncertainty"]["value"] is None
    # A source-backed one-site interpretation does not justify clamping the
    # measured density. Its physical fraction interpretation becomes undefined.
    _, one_site = calculate(active="16")
    assert one_site["cells"]["sites_per_total_monomer"]["value"] == pytest.approx(1.6)
    assert one_site["cells"]["conditional_active_monomer_fraction"]["value"] is None
    assert one_site["cells"]["conditional_active_monomer_fraction"]["unavailable_reason"] == "active_fraction_exceeds_one"
    assert one_site["annotation_credit"] is None


def test_missing_monomer_basis_and_zero_denominators_preserve_partial_amounts():
    for options, reason in (({"molecular_basis": "per_dimer"}, "molecular_basis_per_dimer_coefficient_unimplemented"),
                            ({"missing_mw": True}, "source_measurement_unavailable")):
        _, result = calculate(**options)
        assert result["cells"]["active_site_concentration"]["value"] == 2000
        assert result["cells"]["total_monomer_concentration"]["value"] is None
        assert result["cells"]["total_monomer_concentration"]["unavailable_reason"] == reason
        assert result["cells"]["conditional_active_monomer_fraction"]["value"] is None
    _, zero_active = calculate(active="0", reported_fraction="0")
    assert zero_active["cells"]["active_site_concentration"]["value"] == 0
    assert zero_active["cells"]["conditional_active_monomer_fraction"]["value"] == 0
    assert zero_active["cells"]["reported_active_fraction"]["value"] == 0
    inverse = zero_active["cells"]["conditional_nominal_to_active_denominator_factor"]
    assert inverse["value"] is None
    assert inverse["unavailable_reason"] == "zero_active_site_concentration"
    _, zero_total = calculate(mass="0")
    assert zero_total["cells"]["active_site_concentration"]["value"] == 2000
    assert zero_total["cells"]["sites_per_total_monomer"]["value"] is None
    assert zero_total["cells"]["sites_per_total_monomer"]["unavailable_reason"] == "zero_total_monomer_concentration"
