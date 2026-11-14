"""One pure physical ITC forward/calculation authority; never fits or reads files."""
from fractions import Fraction
import math

from .bivariate_covariance import assess_bivariate_covariance
from .itc_binding_contracts import (
    SHEET_VERSION, PREDICTION_VERSION, COMPONENTS_VERSION, PARAMETERS, PARAMETER_UNITS,
    copy_json, number, require, validate_itc_binding_supplied, validate_itc_binding_sheet,
    validate_itc_binding_selection, validate_itc_binding_fit_selection, parameter_values,
    validate_itc_binding_prediction, validate_itc_binding_components_shape,
)


def build_itc_binding_sheet(supplied, *, fit_observation=None):
    """Retain supplied facts/observations; this supplies no receipt authority."""
    return validate_itc_binding_sheet(dict(version=SHEET_VERSION,
        supplied=validate_itc_binding_supplied(supplied), fit_observation=fit_observation))


def _cell(value, unit, reason=None):
    return dict(state="present" if reason is None else "unavailable", value=value if reason is None else None,
        unit=unit, reason=reason)


def _fraction_cell(value, unit):
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return _cell(None, unit, "numeric_overflow")
    if not math.isfinite(result): return _cell(None, unit, "numeric_overflow")
    if value != 0 and result == 0: return _cell(None, unit, "nonzero_underflow")
    return _cell(result, unit)


def _quantity(value, unit, *, nonnegative=False, positive=False):
    if value is None or value["value"] is None: return _cell(None, unit, "missing_value")
    if value["unit"] is None or value["to_canonical_factor"] is None:
        return _cell(None, unit, "conversion_unavailable")
    if value["unit"] in ("mol/L", "L", "J", "K") and value["unit"] != unit:
        return _cell(None, unit, "unit_mismatch")
    factor = value["to_canonical_factor"]
    if factor <= 0: return _cell(None, unit, "invalid_conversion")
    result = _fraction_cell(Fraction(value["value"]) * Fraction(factor), unit)
    if result["state"] == "present":
        if positive and result["value"] <= 0: return _cell(None, unit, "nonpositive_quantity")
        if nonnegative and result["value"] < 0: return _cell(None, unit, "negative_quantity")
    return result


def _bound(macro, ligand, kd, n, zero_convention):
    if macro == 0 or ligand == 0 or n == 0: return _cell(0., "mol/L")
    capacity = _fraction_cell(Fraction(n) * Fraction(macro), "mol/L")
    if capacity["state"] != "present": return capacity
    sites = capacity["value"]
    if sites == 0 or ligand == 0: return _cell(0., "mol/L")
    if kd == 0:
        return (_cell(min(sites, ligand), "mol/L") if zero_convention == "stoichiometric_limit"
            else _cell(None, "mol/L", "kd_zero_convention_unavailable"))
    # Multiplying the original smaller pool by a scaled ratio avoids both the
    # 2*S*X overflow and loss of a tiny representable smaller pool on scaling.
    larger, smaller = max(sites, ligand), min(sites, ligand)
    scale = max(larger, kd)
    a, b, k = larger / scale, smaller / scale, kd / scale
    discriminant = (a - b) ** 2 + 2 * k * (a + b) + k * k
    ratio = 2 * a / (a + b + k + math.sqrt(discriminant))
    if ratio == 0: return _cell(None, "mol/L", "nonzero_underflow")
    return _fraction_cell(Fraction(smaller) * Fraction(ratio), "mol/L")


def _corrected_heat(supplied, row):
    processing = supplied["heat_processing"]
    if any(processing[k] is None for k in ("input_state", "sign", "blank", "offset")):
        return _cell(None, "J", "heat_processing_unavailable")
    if processing["input_state"] == "already_corrected" and any(
            processing[k] == "subtract_supplied" for k in ("blank", "offset")):
        return _cell(None, "J", "already_corrected_heat_with_subtraction")
    heat = _quantity(row["heat"], "J")
    if heat["state"] != "present": return heat
    exact = Fraction(heat["value"])
    for kind in ("blank", "offset"):
        if processing[kind] == "subtract_supplied":
            correction = _quantity(row[kind + "_heat"], "J")
            if correction["state"] != "present": return correction
            exact -= Fraction(correction["value"])
    return _fraction_cell(exact * processing["sign"], "J")


def predict_itc_binding_heats(sheet, *, parameters):
    """Advance every delivered injection before any caller projection.

    Canonical concentrations are total mol/L, volume L, heat J and delta_h
    J/mol of binding events. n is effective sites/declared macromolecule.
    Kd=0 requires explicit stoichiometric-limit selection; no epsilon is used.
    """
    sheet = validate_itc_binding_sheet(sheet)
    parameters = copy_json(parameters)
    parameter_values(parameters)
    supplied = sheet["supplied"]
    invalid = not all(number(value) for value in parameters.values()) or parameters["kd"] < 0 or parameters["n"] < 0
    reasons = []
    if invalid: reasons.append("invalid_parameters")
    if supplied["model"] != "physical_one_site": reasons.append("unsupported_model")
    if supplied["injection_convention"] != "ordinary_discrete_displacement": reasons.append("unsupported_injection_convention")
    if supplied["history_complete"] is not True: reasons.append("history_not_declared_complete")
    if supplied["context"]["macromolecule_concentration_basis"] != "macromolecule_molecules":
        reasons.append("concentration_basis_unavailable")
    cell = supplied["cell"]
    volume = _quantity(cell["volume"], "L", positive=True)
    macro = _quantity(cell["macromolecule_concentration"], "mol/L", nonnegative=True)
    ligand = _quantity(cell["ligand_concentration"], "mol/L", nonnegative=True)
    initial = dict(volume=volume, macromolecule_concentration=macro, ligand_concentration=ligand)
    for value in initial.values():
        if value["reason"] is not None: reasons.append(value["reason"])
    history, rows = supplied["injections"], []
    if history is None: reasons.append("missing_injection_history")
    prior_ok = not reasons
    bound = (_bound(macro["value"], ligand["value"], parameters["kd"], parameters["n"], supplied["kd_zero_convention"])
        if prior_ok else _cell(None, "mol/L", reasons[0]))
    if bound["state"] != "present":
        prior_ok = False
        if bound["reason"] not in reasons: reasons.append(bound["reason"])
    initial["bound_complex_concentration"] = bound
    for ordinal, row in enumerate(history or []):
        injection_volume = _quantity(row["volume"], "L", nonnegative=True)
        syringe = _quantity(row["syringe_ligand_concentration"], "mol/L", nonnegative=True)
        corrected = _corrected_heat(supplied, row)
        reason = (reasons[0] if reasons else "prior_state_unavailable") if not prior_ok else None
        if reason is None:
            reason = injection_volume["reason"] or syringe["reason"]
        if reason is None and injection_volume["value"] > volume["value"]: reason = "injection_exceeds_cell_volume"
        if reason is None:
            displacement = Fraction(injection_volume["value"]) / Fraction(volume["value"])
            retained = 1 - displacement
            end_macro = _fraction_cell(retained * Fraction(macro["value"]), "mol/L")
            end_ligand = _fraction_cell(retained * Fraction(ligand["value"]) + displacement * Fraction(syringe["value"]), "mol/L")
            end_bound = (_bound(end_macro["value"], end_ligand["value"], parameters["kd"], parameters["n"], supplied["kd_zero_convention"])
                if end_macro["state"] == end_ligand["state"] == "present" else
                _cell(None, "mol/L", end_macro["reason"] or end_ligand["reason"]))
            if end_bound["state"] == "present":
                heat = _fraction_cell(Fraction(volume["value"]) * Fraction(parameters["delta_h"]) *
                    (Fraction(end_bound["value"]) - retained * Fraction(bound["value"])), "J")
            else: heat = _cell(None, "J", end_bound["reason"])
            retained_cell = _fraction_cell(retained, "fraction")
        else:
            end_macro, end_ligand, end_bound = (_cell(None, "mol/L", reason) for _ in range(3))
            heat, retained_cell = _cell(None, "J", reason), _cell(None, "fraction", reason)
        rows.append(dict(injection_id=row["injection_id"], delivered_ordinal=ordinal, injection_volume=injection_volume,
            syringe_ligand_concentration=syringe, retained_cell_fraction=retained_cell,
            macromolecule_concentration=end_macro, ligand_concentration=end_ligand,
            bound_complex_concentration=end_bound, predicted_heat=heat, corrected_heat=corrected))
        prior_ok = end_macro["state"] == end_ligand["state"] == end_bound["state"] == "present"
        macro, ligand, bound = end_macro, end_ligand, end_bound
    return validate_itc_binding_prediction(dict(version=PREDICTION_VERSION, parameters=parameters, initial_state=initial,
        history=None if history is None else rows, input_reasons=list(dict.fromkeys(reasons)),
        qualifications=["supplied_history_completeness_is_an_assertion", "unit_conversions_are_supplied_assertions",
            "binary64_equilibrium_evaluation", "n_is_effective_sites_per_declared_macromolecule"]))


def _fit_parameters(observation):
    if observation is None or observation["call_state"] != "returned": return None
    values = observation["native_parameters"]
    if values is None or len(values) != 3 or any(cell["state"] != "finite" for cell in values): return None
    return dict(zip(PARAMETERS, (cell["value"] for cell in values)))


def _prepare_fit_inputs(sheet, *, selection):
    """Pure definition of this selected objective; there is no N>=3 gate."""
    sheet = validate_itc_binding_sheet(sheet)
    selection = validate_itc_binding_fit_selection(selection)
    initial = selection["initial_parameters"]
    require(initial["kd"] >= 0 and initial["n"] >= 0, "nonnegative_kd_and_n_required")
    lower, upper = [], []
    for name in PARAMETERS:
        bounds = selection["bounds"][name]
        lo = -math.inf if bounds["lower"] is None else float(bounds["lower"])
        hi = math.inf if bounds["upper"] is None else float(bounds["upper"])
        require(lo < hi and lo <= initial[name] <= hi, "selected_bounds_conflict")
        if name in ("kd", "n"): require(lo >= 0, "physical_parameter_bounds_required")
        lower.append(lo); upper.append(hi)
    prediction = predict_itc_binding_heats(sheet, parameters=initial)
    require(not prediction["input_reasons"], "forward_inputs_unavailable")
    rows = {row["injection_id"]: row for row in prediction["history"] or []}
    ids = selection["residual_injection_ids"]
    require(all(item in rows for item in ids), "unknown_selected_injection")
    require(all(rows[item][key]["state"] == "present" for item in ids for key in ("predicted_heat", "corrected_heat")),
        "selected_objective_unavailable")
    sigma = None
    if selection["weighting"]["kind"] == "diagonal_sigma":
        values = [_quantity(row["sigma"], "J", positive=True) for row in selection["weighting"]["sigma_heat"]]
        require(all(value["state"] == "present" for value in values), "selected_sigmas_unavailable")
        sigma = [value["value"] for value in values]
    qualifications = ["fit_does_not_establish_identifiability", "in_process_software_observation_is_not_host_commission"]
    if len(ids) < 3: qualifications.append("underdetermined_selected_population")
    if len(ids) <= 3: qualifications.append("nonpositive_residual_degrees_of_freedom")
    if any(row["predicted_heat"]["state"] != "present" for key, row in rows.items() if key not in ids):
        qualifications.append("later_unavailable_history_not_in_objective")
    return dict(selection=selection, lower_bounds=lower, upper_bounds=upper,
        data=dict(injection_ids=ids, heats_joule=[rows[item]["corrected_heat"]["value"] for item in ids], sigma_joule=sigma),
        prediction=prediction, qualifications=qualifications)


def _fit_diagnostics(observation, prediction):
    if observation is None: return None
    selection = observation["selection"]
    ids = selection["residual_injection_ids"]
    by_id = {row["injection_id"]: row for row in prediction["history"] or []} if prediction is not None else {}
    residuals, failures = [], []
    for injection_id in ids:
        row = by_id.get(injection_id)
        if row is None or any(row[key]["state"] != "present" for key in ("corrected_heat", "predicted_heat")):
            failures.append(injection_id); continue
        residuals.append(Fraction(row["corrected_heat"]["value"]) - Fraction(row["predicted_heat"]["value"]))
    sse = (_fraction_cell(sum((value * value for value in residuals), Fraction(0)), "J^2")
        if not failures and prediction is not None else _cell(None, "J^2", "input_unavailable"))
    objective = sse
    if selection["weighting"]["kind"] == "diagonal_sigma":
        sigmas = [_quantity(row["sigma"], "J", positive=True) for row in selection["weighting"]["sigma_heat"]]
        objective = (_fraction_cell(sum(((residual / Fraction(sigma["value"])) ** 2
            for residual, sigma in zip(residuals, sigmas)), Fraction(0)), "dimensionless")
            if not failures and prediction is not None and all(sigma["state"] == "present" for sigma in sigmas) else
            _cell(None, "dimensionless", "input_unavailable"))
    covariance = observation["native_covariance"]
    block = None
    if covariance is not None and len(covariance) == 3 and all(len(row) == 3 for row in covariance):
        cells = [[covariance[i][j] for j in (0, 2)] for i in (0, 2)]
        if all(cell["state"] == "finite" for row in cells for cell in row):
            block = assess_bivariate_covariance([[cell["value"] for cell in row] for row in cells])
    parameters = _fit_parameters(observation)
    contacts = []
    if parameters is not None:
        for parameter in PARAMETERS:
            for side, bound in selection["bounds"][parameter].items():
                if bound is not None and parameters[parameter] == bound: contacts.append(dict(parameter=parameter, side=side))
    return dict(residual_injection_ids=ids, observation_count=len(ids), parameter_count=3,
        residual_degrees_of_freedom=len(ids)-3, underdetermined=len(ids)<3,
        sse=sse, selected_objective=objective, residual_unavailable_ids=failures,
        raw_covariance=covariance, covariance_metadata=observation["covariance_metadata"], kd_delta_h_block_assessment=block,
        covariance_scope="named_kd_delta_h_block_only", statistical_covariance_validity="not_assessed",
        identifiability="not_assessed", parameter_bound_contacts=contacts,
        absolute_sigma=selection["weighting"]["absolute_sigma"],
        independent_error_assumption=selection["weighting"]["independent_error_assumption"])


def calculate_itc_binding_components(sheet, *, selection):
    """Explicit saved calculation; no native import, fit or source acquisition."""
    sheet = validate_itc_binding_sheet(sheet)
    selection = validate_itc_binding_selection(selection)
    observation = sheet["fit_observation"]
    parameters = selection["parameters"] if selection["parameter_source"] == "selected_parameters" else _fit_parameters(observation)
    history = sheet["supplied"]["injections"]
    ids = [] if history is None else [row["injection_id"] for row in history]
    require(all(item in ids for item in selection["injection_ids"]), "unknown_selected_injection")
    prediction = None if parameters is None else predict_itc_binding_heats(sheet, parameters=parameters)
    projected = []
    for injection_id in selection["injection_ids"]:
        if prediction is None:
            supplied_row = next(row for row in history if row["injection_id"] == injection_id)
            row = dict(injection_id=injection_id, delivered_ordinal=ids.index(injection_id),
                injection_volume=_quantity(supplied_row["volume"], "L", nonnegative=True),
                syringe_ligand_concentration=_quantity(supplied_row["syringe_ligand_concentration"], "mol/L", nonnegative=True),
                retained_cell_fraction=_cell(None, "fraction", "fit_unavailable"),
                macromolecule_concentration=_cell(None, "mol/L", "fit_unavailable"),
                ligand_concentration=_cell(None, "mol/L", "fit_unavailable"),
                bound_complex_concentration=_cell(None, "mol/L", "fit_unavailable"),
                predicted_heat=_cell(None, "J", "fit_unavailable"),
                corrected_heat=_corrected_heat(sheet["supplied"], supplied_row))
        else: row = next(row for row in prediction["history"] if row["injection_id"] == injection_id)
        row = copy_json(row)
        if row["corrected_heat"]["state"] == row["predicted_heat"]["state"] == "present":
            row["residual"] = _fraction_cell(Fraction(row["corrected_heat"]["value"]) - Fraction(row["predicted_heat"]["value"]), "J")
        else: row["residual"] = _cell(None, "J", "input_unavailable")
        projected.append(row)
    parameter_cells = {name: _cell(parameters[name], PARAMETER_UNITS[name]) if parameters is not None else
        _cell(None, PARAMETER_UNITS[name], "native_parameter_unavailable") for name in PARAMETERS}
    # Diagnostics always refer to the original fitted parameter vector and
    # population, even if a caller requests another forward parameter vector.
    fitted_parameters = _fit_parameters(observation)
    fitted_prediction = (predict_itc_binding_heats(sheet, parameters=fitted_parameters)
        if observation is not None and fitted_parameters is not None else None)
    return validate_itc_binding_components_shape(dict(version=COMPONENTS_VERSION, sheet=sheet, selection=selection,
        parameter_values=parameter_cells, delivered_injection_ids=None if history is None else ids,
        rows=projected, full_prediction=prediction,
        fit_diagnostics=_fit_diagnostics(observation, fitted_prediction) if selection["fit_diagnostics"] else None,
        temperature=_quantity(sheet["supplied"]["temperature"], "K", positive=True),
        origin="explicit_saved_calculation", scientific_provenance="not_authenticated_by_numerical_document",
        identifiability="not_assessed"))
