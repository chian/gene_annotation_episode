"""One actual engineered physical fit; other cases are pure/pre-call controls."""
import builtins
from copy import deepcopy
from decimal import Decimal, localcontext
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode import itc_binding_contracts as contracts
from gene_annotation_episode import itc_binding_fit as fitting
from gene_annotation_episode import itc_binding_measurements as measurements
from tests.test_itc_binding_measurements import supplied, quantity, parameters, fit_selection, calculation_selection


def independent_engineering_dataset():
    """Decimal direct quadratic roots, independent of the production forward."""
    value = supplied(count=32)
    value["cell"] = dict(volume=quantity(.001, "L"), macromolecule_concentration=quantity(30e-6, "mol/L"),
        ligand_concentration=quantity(0., "mol/L"))
    expected = dict(kd=3e-6, n=1.4, delta_h=-28000.)
    with localcontext() as ctx:
        ctx.prec = 60
        volume, macro, ligand = Decimal('.001'), Decimal('30e-6'), Decimal(0)
        kd, n, dh = Decimal('3e-6'), Decimal('1.4'), Decimal('-28000')
        bound = Decimal(0)
        for row in value["injections"]:
            injection, syringe = Decimal('5e-6'), Decimal('500e-6')
            retained = 1-injection/volume
            macro, ligand = retained*macro, retained*ligand+(injection/volume)*syringe
            sites = n*macro
            total = sites+ligand+kd
            end_bound = (total-(total*total-4*sites*ligand).sqrt())/2
            heat = volume*dh*(end_bound-retained*bound)
            row.update(volume=quantity(float(injection), "L"), syringe_ligand_concentration=quantity(float(syringe), "mol/L"),
                heat=quantity(float(heat), "J"))
            bound = end_bound
    selection = fit_selection([row["injection_id"] for row in value["injections"]])
    selection["initial_parameters"] = dict(kd=6e-6, n=.9, delta_h=-20000.)
    selection["bounds"] = dict(kd=dict(lower=1e-9, upper=1e-3), n=dict(lower=0., upper=5.), delta_h=dict(lower=-1e6, upper=-1.))
    selection["solver"] = dict(method="trf", jacobian="2-point", ftol=1e-12, xtol=1e-12, gtol=1e-12,
        max_nfev=2000, x_scale=[3e-6, 1., 30000.], diff_step=[1e-5, 1e-5, 1e-5])
    selection["weighting"] = dict(kind="diagonal_sigma", independent_error_assumption=True, absolute_sigma=True,
        sigma_heat=[dict(injection_id=row["injection_id"], sigma=quantity(1e-8, "J")) for row in value["injections"]])
    return value, selection, expected


def assert_actual_itc_fit_and_saved_recalculation(*, supplied_input, selection, expected,
        observation, sheet, components, monkeypatch):
    """Check actual caller-retained results without acquiring or fitting data.

    The integration caller owns original action/File authority and pre/post
    input-byte checks. These assertions do not manufacture that association.
    """
    original_value, original_selection = deepcopy(supplied_input), deepcopy(selection)
    assert observation["call_state"] == "returned" and observation["call_count"] == 1 and observation["failure"] is None
    assert observation["selection"] == original_selection
    assert sheet == measurements.build_itc_binding_sheet(supplied_input, fit_observation=observation)
    assert components["sheet"] == sheet
    assert observation["software"]["authority"] == "observed_in_process_not_host_commission"
    assert observation["software"]["callable"]["qualname"] == "curve_fit"
    assert observation["software"]["callable"]["module"].startswith("scipy.optimize")
    assert {Path(row["path"]).name for row in observation["software"]["implementation_files"]} == {
        "itc_binding_fit.py", "itc_binding_contracts.py", "itc_binding_measurements.py", "bivariate_covariance.py"}
    assert observation["effective_arguments"]["method"] == "trf"
    assert observation["effective_arguments"]["absolute_sigma"] is True
    metadata = observation["covariance_metadata"]
    assert metadata["parameter_order"] == ["kd", "n", "delta_h"]
    assert metadata["parameter_units"] == ["mol/L", "sites_per_macromolecule", "J/mol"]
    assert metadata["entry_unit_products"][0][2] == dict(row_unit="mol/L", column_unit="J/mol")
    assert metadata["construction"] == "native_local_jacobian_pseudoinverse_estimate"
    assert metadata["scaling"] == "native_absolute_sigma_true" and metadata["statistical_validity"] == "not_assessed"
    fitted = dict(zip(contracts.PARAMETERS, (cell["value"] for cell in observation["native_parameters"])))
    for name in contracts.PARAMETERS: assert fitted[name] == pytest.approx(expected[name], rel=1e-4, abs=0.)
    assert len(observation["native_covariance"]) == 3 and all(len(row)==3 for row in observation["native_covariance"])
    # Adversarial copies exercise closed record consistency, not another fit or
    # a claim that the original fit used these substituted settings/units.
    bad = deepcopy(observation); bad["covariance_metadata"]["entry_unit_products"][0][2]["row_unit"] = "K"
    with pytest.raises(ValueError, match="covariance_metadata_conflict"):
        contracts.validate_itc_binding_fit_observation(bad)
    bad = deepcopy(observation); bad["covariance_metadata"]["absolute_sigma"] = 1
    with pytest.raises(ValueError): contracts.validate_itc_binding_fit_observation(bad)
    for field in ("ftol", "xtol", "gtol", "max_nfev"):
        bad = deepcopy(observation)
        bad["selection"]["solver"][field] = 1
        bad["effective_arguments"][field] = True
        with pytest.raises(ValueError): contracts.validate_itc_binding_fit_observation(bad)
    saved_sheet = json.loads(json.dumps(sheet, allow_nan=False))
    saved_bytes = json.dumps(saved_sheet, sort_keys=True, allow_nan=False)
    import_original = builtins.__import__
    def forbid_import(name, *args, **kwargs):
        if name.split('.')[0] in ('scipy', 'numpy'): pytest.fail("saved calculation imported fitter")
        return import_original(name, *args, **kwargs)
    def forbid(*args, **kwargs): pytest.fail("saved calculation performed fit or file I/O")
    request = calculation_selection([row["injection_id"] for row in supplied_input["injections"]], source="fit_observation")
    assert components["selection"] == request
    with monkeypatch.context() as guarded:
        guarded.setattr(builtins, "__import__", forbid_import)
        guarded.setattr(fitting, "fit_itc_binding_measurements", forbid)
        guarded.setattr(Path, "open", forbid)
        guarded.setattr(builtins, "open", forbid)
        guarded.setattr(os, "open", forbid)
        recalculated = measurements.calculate_itc_binding_components(saved_sheet, selection=request)
        assert recalculated == components
        assert contracts.validate_itc_binding_components_shape(components) == components
    assert all(abs(row["residual"]["value"]) < 1e-9 for row in components["rows"])
    assert components["temperature"]["value"] is None  # T is irrelevant to this fitted heat model.
    assert components["fit_diagnostics"]["raw_covariance"] == observation["native_covariance"]
    assert components["fit_diagnostics"]["observation_count"] == 32
    assert components["fit_diagnostics"]["residual_degrees_of_freedom"] == 29
    assert components["fit_diagnostics"]["identifiability"] == "not_assessed"
    assert components["fit_diagnostics"]["covariance_scope"] == "named_kd_delta_h_block_only"
    assert components["fit_diagnostics"]["covariance_metadata"] == metadata
    for field in ("parameter_count", "residual_degrees_of_freedom"):
        bad = deepcopy(components); bad["fit_diagnostics"][field] = float(bad["fit_diagnostics"][field])
        with pytest.raises(ValueError): contracts.validate_itc_binding_components_shape(bad)
    bad = deepcopy(components); bad["fit_diagnostics"]["covariance_metadata"]["absolute_sigma"] = 1
    with pytest.raises(ValueError): contracts.validate_itc_binding_components_shape(bad)
    assert contracts.validate_itc_binding_components_shape(components) == components
    assert json.dumps(saved_sheet, sort_keys=True, allow_nan=False) == saved_bytes
    assert supplied_input == original_value and selection == original_selection


@pytest.mark.parametrize("change", ["missing_selected_heat", "missing_selected_volume", "negative_n", "bounds_conflict", "zero_sigma"])
def test_undefined_selected_objective_fails_before_import_or_native_call(monkeypatch, change):
    value = supplied(); selection = fit_selection(["injection_0"])
    if change == "missing_selected_heat": value["injections"][0]["heat"]["value"] = None
    elif change == "missing_selected_volume": value["injections"][0]["volume"]["value"] = None
    elif change == "negative_n": selection["initial_parameters"]["n"] = -1.
    elif change == "bounds_conflict": selection["bounds"]["n"] = dict(lower=2., upper=1.)
    else:
        selection["weighting"] = dict(kind="diagonal_sigma", independent_error_assumption=True, absolute_sigma=True,
            sigma_heat=[dict(injection_id="injection_0", sigma=quantity(0., "J"))])
    original = builtins.__import__
    def forbid(name, *args, **kwargs):
        if name.split('.')[0] in ('scipy', 'numpy'): pytest.fail("invalid objective reached software import")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", forbid)
    result = fitting.fit_itc_binding_measurements(measurements.build_itc_binding_sheet(value), selection=selection)
    assert result["call_state"] == "not_started" and result["call_count"] == 0
    assert result["failure"]["stage"] == "input" and result["software"] is None
    assert result["native_parameters"] is None and result["native_covariance"] is None


@pytest.mark.parametrize("value,state", [(float('nan'), "nan"), (float('inf'), "positive_infinity"),
    (-float('inf'), "negative_infinity"), (0., "finite"), (-2., "finite")])
def test_native_scalar_encoding_retains_distinct_nonfinite_classifications(value, state):
    # Actual encoder used for every raw covariance entry; no invented fit is
    # being represented by these isolated transport controls.
    cell = fitting._observed(value)
    assert cell["state"] == state
    assert cell["value"] == value if state == "finite" else cell["value"] is None
    contracts.observed_number(cell)
    json.dumps(cell, allow_nan=False)


@pytest.mark.parametrize("value", [True, "1", None])
def test_native_scalar_encoder_does_not_coerce_boolean_or_text_into_measurements(value):
    with pytest.raises(ValueError, match="native_scalar_not_numeric"): fitting._observed(value)


def test_exception_entry_detection_distinguishes_call_from_pre_call_failure():
    def entered(): raise RuntimeError("engineering_call_boundary")
    try: entered()
    except RuntimeError as error:
        assert fitting._entered(error, entered.__code__)
        assert not fitting._entered(error, parameters.__code__)
