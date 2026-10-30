"""Engineering physical/partial-input controls; no fit or native source calls."""
from copy import deepcopy
import math

import pytest

from gene_annotation_episode import itc_binding_contracts as contracts
from gene_annotation_episode import itc_binding_measurements as measurements


def quantity(value, unit, *, raw_unit=None, factor=1.):
    return dict(value=value, unit=unit if raw_unit is None else raw_unit, canonical_unit=unit,
        to_canonical_factor=factor, source_ref=None, source_pointer=None)


def supplied(*, count=1):
    """Explicit numerical example, not measured laboratory/provenance data."""
    return dict(version=contracts.SUPPLIED_VERSION, model="physical_one_site", kd_zero_convention=None,
        injection_convention="ordinary_discrete_displacement", history_complete=True,
        context=dict(macromolecule_ref=None, ligand_ref=None, macromolecule_concentration_basis="macromolecule_molecules"),
        cell=dict(volume=quantity(1., "L"), macromolecule_concentration=quantity(2., "mol/L"),
            ligand_concentration=quantity(0., "mol/L")),
        heat_processing=dict(input_state="already_corrected", sign=1, blank="not_applied", offset="not_applied"),
        injections=[dict(injection_id="injection_"+str(i), volume=quantity(.5, "L"),
            syringe_ligand_concentration=quantity(4., "mol/L"), heat=quantity(0., "J"), blank_heat=None, offset_heat=None)
            for i in range(count)], temperature=quantity(None, "K"))


def parameters(*, kd=1., n=1., delta_h=3.):
    return dict(kd=kd, n=n, delta_h=delta_h)


def fit_selection(ids):
    return dict(version=contracts.FIT_SELECTION_VERSION, residual_injection_ids=list(ids),
        initial_parameters=parameters(), bounds=dict(kd=dict(lower=0., upper=100.),
            n=dict(lower=0., upper=10.), delta_h=dict(lower=-100., upper=100.)),
        solver=dict(method="trf", jacobian="2-point", ftol=1e-10, xtol=1e-10, gtol=1e-10,
            max_nfev=1000, x_scale=[1., 1., 1.], diff_step=[1e-5, 1e-5, 1e-5]),
        weighting=dict(kind="unweighted", independent_error_assumption=None, absolute_sigma=False, sigma_heat=[]))


def calculation_selection(ids, *, source="selected_parameters", values=None):
    return dict(version=contracts.SELECTION_VERSION, parameter_source=source,
        parameters=(parameters() if values is None else values) if source == "selected_parameters" else None,
        injection_ids=list(ids), fit_diagnostics=True)


def predict(value, values=None):
    return measurements.predict_itc_binding_heats(measurements.build_itc_binding_sheet(value),
        parameters=parameters() if values is None else values)


def test_independent_one_injection_mass_balance_and_n_is_not_an_amplitude_factor():
    value = supplied()
    one = predict(value)["history"][0]
    assert one["macromolecule_concentration"]["value"] == 1.
    assert one["ligand_concentration"]["value"] == 2.
    assert one["bound_complex_concentration"]["value"] == pytest.approx(2-math.sqrt(2))
    assert one["predicted_heat"]["value"] == pytest.approx(3*(2-math.sqrt(2)))
    two = predict(value, parameters(n=2.))["history"][0]
    assert two["bound_complex_concentration"]["value"] == pytest.approx(1.)
    assert two["predicted_heat"]["value"] == pytest.approx(3.)
    assert two["predicted_heat"]["value"] != pytest.approx(2*one["predicted_heat"]["value"])


def test_nonzero_initial_ligand_uses_displaced_initial_bound_heat():
    value = supplied(); value["cell"]["ligand_concentration"] = quantity(1., "mol/L")
    value["injections"][0]["volume"] = quantity(.25, "L")
    result = predict(value)
    assert result["initial_state"]["bound_complex_concentration"]["value"] == pytest.approx(2-math.sqrt(2))
    # M_end=1.5, X_end=1.75, discriminant=7.5625, B_end=.75.
    expected = 3*(.75-.75*(2-math.sqrt(2)))
    assert result["history"][0]["predicted_heat"]["value"] == pytest.approx(expected)


@pytest.mark.parametrize("zero_pool", ["n", "macromolecule", "ligand"])
def test_exact_zero_pools_are_valid_without_positive_epsilon(zero_pool):
    value = supplied(); values = parameters(kd=0.)
    if zero_pool == "n": values["n"] = 0.
    elif zero_pool == "macromolecule": value["cell"]["macromolecule_concentration"] = quantity(0., "mol/L")
    else: value["injections"][0]["syringe_ligand_concentration"] = quantity(0., "mol/L")
    row = predict(value, values)["history"][0]
    assert row["bound_complex_concentration"] == dict(state="present", value=0., unit="mol/L", reason=None)
    assert row["predicted_heat"]["value"] == 0.


def test_kd_zero_requires_explicit_stoichiometric_limit_for_nonzero_pools():
    value = supplied()
    missing = predict(value, parameters(kd=0.))["history"][0]
    assert missing["predicted_heat"]["reason"] == "kd_zero_convention_unavailable"
    value["kd_zero_convention"] = "stoichiometric_limit"
    selected = predict(value, parameters(kd=0.))["history"][0]
    assert selected["bound_complex_concentration"]["value"] == 1.
    assert selected["predicted_heat"]["value"] == 3.


@pytest.mark.parametrize("name", ["kd", "n"])
def test_negative_physical_parameter_does_not_become_zero_heat(name):
    selected = parameters(); selected[name] = -1.
    result = predict(supplied(), selected)
    assert result["history"][0]["predicted_heat"]["value"] is None
    assert result["history"][0]["corrected_heat"]["value"] == 0.
    assert "invalid_parameters" in result["input_reasons"]


@pytest.mark.parametrize("bad", [None, -1., 2.])
def test_later_bad_volume_preserves_prefix_and_blocks_later_physical_states(bad):
    value = supplied(count=3)
    original = predict(value)
    value["injections"][1]["volume"] = quantity(bad, "L")
    result = predict(value)
    assert result["history"][0] == original["history"][0]
    assert all(row["predicted_heat"]["value"] is None for row in result["history"][1:])
    assert all(row["corrected_heat"]["value"] == 0. for row in result["history"])
    selected = fit_selection(["injection_0"])
    prepared = measurements._prepare_fit_inputs(measurements.build_itc_binding_sheet(value), selection=selected)
    assert prepared["data"]["injection_ids"] == ["injection_0"]
    assert "later_unavailable_history_not_in_objective" in prepared["qualifications"]
    assert "underdetermined_selected_population" in prepared["qualifications"]


def test_missing_heat_does_not_remove_a_delivered_injection_from_history():
    value = supplied(count=2)
    original = predict(value)
    value["injections"][0]["heat"]["value"] = None
    result = predict(value)
    assert result["history"][0]["corrected_heat"]["reason"] == "missing_value"
    assert result["history"][1]["predicted_heat"] == original["history"][1]["predicted_heat"]
    sheet = measurements.build_itc_binding_sheet(value)
    assert measurements._prepare_fit_inputs(sheet, selection=fit_selection(["injection_1"]))["data"]["injection_ids"] == ["injection_1"]
    with pytest.raises(ValueError, match="selected_objective_unavailable"):
        measurements._prepare_fit_inputs(sheet, selection=fit_selection(["injection_0"]))


def test_projection_cannot_hide_an_earlier_delivered_injection():
    value = supplied(count=2)
    sheet = measurements.build_itc_binding_sheet(value)
    result = measurements.calculate_itc_binding_components(sheet, selection=calculation_selection(["injection_1"]))
    assert len(result["rows"]) == 1 and len(result["full_prediction"]["history"]) == 2
    assert result["rows"][0]["predicted_heat"] == predict(value)["history"][1]["predicted_heat"]
    erased = deepcopy(value); erased["injections"] = erased["injections"][1:]
    assert result["rows"][0]["predicted_heat"]["value"] != pytest.approx(predict(erased)["history"][0]["predicted_heat"]["value"])


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_selected_objective_has_no_minimum_observation_gate(count):
    value = supplied(count=count)
    ids = [row["injection_id"] for row in value["injections"]]
    prepared = measurements._prepare_fit_inputs(measurements.build_itc_binding_sheet(value), selection=fit_selection(ids))
    assert prepared["data"]["injection_ids"] == ids
    assert ("underdetermined_selected_population" in prepared["qualifications"]) == (count<3)


def test_selected_zero_n_boundary_is_a_defined_objective_not_a_pre_fit_rejection():
    selected = fit_selection(["injection_0"]); selected["initial_parameters"]["n"] = 0.
    prepared = measurements._prepare_fit_inputs(measurements.build_itc_binding_sheet(supplied()), selection=selected)
    assert prepared["selection"]["initial_parameters"]["n"] == 0.
    assert prepared["prediction"]["history"][0]["predicted_heat"]["value"] == 0.


def test_explicit_blank_offset_sign_and_units_are_applied_in_selected_order():
    value = supplied()
    value["heat_processing"] = dict(input_state="uncorrected", sign=-1, blank="subtract_supplied", offset="subtract_supplied")
    row = value["injections"][0]
    row["heat"] = quantity(23., "J", raw_unit="declared_instrument_unit", factor=.5)
    row["blank_heat"] = quantity(3., "J", raw_unit="declared_instrument_unit", factor=.5)
    row["offset_heat"] = quantity(2., "J")
    assert predict(value)["history"][0]["corrected_heat"]["value"] == -8.
    assert value["injections"][0]["heat"]["value"] == 23.
    value["heat_processing"]["input_state"] = "already_corrected"
    assert predict(value)["history"][0]["corrected_heat"]["reason"] == "already_corrected_heat_with_subtraction"


@pytest.mark.parametrize("change,reason", [("missing_factor", "conversion_unavailable"),
    ("negative_factor", "invalid_conversion"), ("wrong_unit", "unit_mismatch"), ("missing_heat", "missing_value")])
def test_unusable_heat_conversion_preserves_defined_physical_prediction(change, reason):
    value = supplied(); original = predict(value)["history"][0]["predicted_heat"]
    heat = value["injections"][0]["heat"]
    if change == "missing_factor": heat["to_canonical_factor"] = None
    elif change == "negative_factor": heat["to_canonical_factor"] = -1.
    elif change == "wrong_unit": heat["unit"] = "L"
    else: heat["value"] = None
    row = predict(value)["history"][0]
    assert row["predicted_heat"] == original and row["corrected_heat"]["reason"] == reason


def test_tiny_representable_binding_pool_survives_large_pool_scaling():
    value = supplied()
    value["cell"]["macromolecule_concentration"] = quantity(1e-300, "mol/L")
    value["cell"]["ligand_concentration"] = quantity(1e300, "mol/L")
    value["injections"][0]["volume"] = quantity(0., "L")
    result = predict(value)
    assert result["initial_state"]["bound_complex_concentration"]["value"] == pytest.approx(1e-300, rel=1e-14, abs=0.)
    assert result["history"][0]["predicted_heat"]["value"] == 0.


@pytest.mark.parametrize("raw,factor,reason", [(1e308, 1e308, "numeric_overflow"), (1e-300, 1e-300, "nonzero_underflow")])
def test_nonrepresentable_conversion_is_qualified_not_zero(raw, factor, reason):
    value = supplied(); value["injections"][0]["heat"] = quantity(raw, "J", factor=factor)
    row = predict(value)["history"][0]
    assert row["corrected_heat"]["value"] is None and row["corrected_heat"]["reason"] == reason
    assert row["predicted_heat"]["state"] == "present"


def test_scaled_equilibrium_avoids_discriminant_overflow_for_finite_populations():
    value = supplied()
    value["cell"]["macromolecule_concentration"] = quantity(1e308, "mol/L")
    value["cell"]["ligand_concentration"] = quantity(1e308, "mol/L")
    value["injections"][0]["volume"] = quantity(0., "L")
    result = predict(value, parameters(kd=1e308))
    assert result["initial_state"]["bound_complex_concentration"]["value"] == pytest.approx(1e308*(3-math.sqrt(5))/2, rel=1e-14)
    assert result["history"][0]["predicted_heat"]["value"] == 0.


@pytest.mark.parametrize("field", ["model", "injection_convention", "basis", "history"])
def test_missing_physical_convention_is_unavailable_without_erasing_observed_heat(field):
    value = supplied()
    if field in ("model", "injection_convention"): value[field] = None
    elif field == "basis": value["context"]["macromolecule_concentration_basis"] = None
    else: value["history_complete"] = None
    row = predict(value)["history"][0]
    assert row["predicted_heat"]["value"] is None and row["corrected_heat"]["value"] == 0.


def test_missing_and_empty_history_remain_distinct():
    value = supplied(count=0); empty = predict(value)
    value["injections"] = None; missing = predict(value)
    assert empty["history"] == [] and missing["history"] is None
    assert "missing_injection_history" in missing["input_reasons"]


@pytest.mark.parametrize("assumption", [None, False])
def test_supplied_sigmas_do_not_invent_independent_errors(assumption):
    selected = fit_selection(["injection_0"])
    selected["weighting"] = dict(kind="diagonal_sigma", independent_error_assumption=assumption,
        absolute_sigma=True, sigma_heat=[dict(injection_id="injection_0", sigma=quantity(.1, "J"))])
    with pytest.raises(ValueError, match="independent_error_assumption_required"):
        contracts.validate_itc_binding_fit_selection(selected)


def test_literal_stored_component_validation_never_recalculates_or_upgrades_origin(monkeypatch):
    sheet = measurements.build_itc_binding_sheet(supplied())
    result = measurements.calculate_itc_binding_components(sheet, selection=calculation_selection(["injection_0"]))
    # Deliberately altered engineering stored value; shape admission is NOT a
    # calculator equality/producer-provenance assertion.
    result["rows"][0]["predicted_heat"]["value"] = 901.25
    monkeypatch.setattr(measurements, "predict_itc_binding_heats", lambda *a, **k: pytest.fail("stored read calculated"))
    monkeypatch.setattr(measurements, "calculate_itc_binding_components", lambda *a, **k: pytest.fail("stored read calculated"))
    admitted = contracts.validate_itc_binding_components_shape(result)
    assert admitted["rows"][0]["predicted_heat"]["value"] == 901.25
    assert admitted["scientific_provenance"] == "not_authenticated_by_numerical_document"


@pytest.mark.parametrize("bad", [True, float("inf"), float("nan"), 10**400])
def test_nonfinite_or_boolean_inputs_are_not_measurements(bad):
    value = supplied(); value["injections"][0]["heat"]["value"] = bad
    with pytest.raises(ValueError): measurements.build_itc_binding_sheet(value)


def test_supplied_sheet_references_and_unknown_fields_grant_nothing():
    value = supplied(); value["cell"]["volume"]["source_ref"] = "source_asserted_only"
    before = deepcopy(value); sheet = measurements.build_itc_binding_sheet(value)
    assert value == before and sheet["supplied"] == before
    assert sheet["fit_observation"] is None
    bad = deepcopy(value); bad["confidence"] = .99
    with pytest.raises(ValueError): measurements.build_itc_binding_sheet(bad)
