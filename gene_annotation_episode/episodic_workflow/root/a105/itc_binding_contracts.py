"""Closed numerical ITC documents; shape is not experimental or job authority.

The physical model is one set of sites, with n in the binding balance. Only
explicit ordinary discrete displacement is interpreted. Source references and
in-process software observations are retained assertions, not receipt grants.
"""
from copy import deepcopy
import hashlib
import json
import math


SUPPLIED_VERSION = "itc_binding_supplied_v1"
SHEET_VERSION = "itc_binding_sheet_v1"
FIT_SELECTION_VERSION = "itc_binding_fit_selection_v1"
FIT_OBSERVATION_VERSION = "itc_binding_fit_observation_v1"
SELECTION_VERSION = "itc_binding_selection_v1"
PREDICTION_VERSION = "itc_binding_prediction_v1"
COMPONENTS_VERSION = "itc_binding_components_v1"
PARAMETERS = ("kd", "n", "delta_h")
PARAMETER_UNITS = {"kd": "mol/L", "n": "sites_per_macromolecule", "delta_h": "J/mol"}
QUANTITY_FIELDS = ("value", "unit", "canonical_unit", "to_canonical_factor", "source_ref", "source_pointer")
REASONS = (
    "missing_value", "conversion_unavailable", "invalid_conversion", "negative_quantity",
    "nonpositive_quantity", "numeric_overflow", "nonzero_underflow", "numerical_range",
    "unsupported_model", "unsupported_injection_convention", "history_not_declared_complete",
    "concentration_basis_unavailable", "missing_injection_history", "invalid_parameters",
    "injection_exceeds_cell_volume", "prior_state_unavailable", "heat_processing_unavailable",
    "already_corrected_heat_with_subtraction", "fit_unavailable", "native_parameter_unavailable",
    "native_covariance_unavailable", "residual_not_selected", "input_unavailable",
    "unit_mismatch", "kd_zero_convention_unavailable",
)


def require(condition, message="invalid_document"):
    if not condition:
        raise ValueError("itc_binding_" + message)


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), "closed_fields_required")


def number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value))
    except (ValueError, OverflowError):
        return False


def text(value):
    return type(value) is str and bool(value) and not any(c in value for c in "\0\r\n")


def copy_json(value):
    def check(item):
        if item is None or type(item) is bool:
            return
        if type(item) in (int, float):
            require(number(item), "finite_binary64_number_required")
        elif type(item) is str:
            item.encode("utf-8", errors="strict")
        elif type(item) is list:
            for child in item: check(child)
        elif type(item) is dict:
            require(all(type(key) is str for key in item))
            for key, child in item.items(): check(key); check(child)
        else:
            require(False, "finite_json_required")
    try:
        check(value)
        return deepcopy(value)
    except (UnicodeError, RecursionError) as error:
        raise ValueError("itc_binding_finite_json_required") from error


def digest(value):
    value = copy_json(value)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def quantity(value, unit=None):
    closed(value, QUANTITY_FIELDS)
    require(value["value"] is None or number(value["value"]))
    require(value["unit"] is None or text(value["unit"]))
    require(value["canonical_unit"] in ("mol/L", "L", "J", "K"))
    require(unit is None or value["canonical_unit"] == unit)
    require(value["to_canonical_factor"] is None or number(value["to_canonical_factor"]))
    require(all(value[key] is None or text(value[key]) for key in ("source_ref", "source_pointer")))


def parameter_values(value):
    closed(value, PARAMETERS)
    require(all(number(item) for item in value.values()), "finite_parameters_required")


def validate_itc_binding_supplied(value):
    value = copy_json(value)
    closed(value, ("version", "model", "kd_zero_convention", "injection_convention", "history_complete", "context",
        "cell", "heat_processing", "injections", "temperature"))
    require(value["version"] == SUPPLIED_VERSION)
    require(value["model"] is None or text(value["model"]))
    require(value["kd_zero_convention"] in (None, "stoichiometric_limit"))
    require(value["injection_convention"] is None or text(value["injection_convention"]))
    require(value["history_complete"] is None or type(value["history_complete"]) is bool)
    closed(value["context"], ("macromolecule_ref", "ligand_ref", "macromolecule_concentration_basis"))
    require(all(item is None or text(item) for item in value["context"].values()))
    closed(value["cell"], ("volume", "macromolecule_concentration", "ligand_concentration"))
    for key, item in value["cell"].items(): quantity(item, "L" if key == "volume" else "mol/L")
    closed(value["heat_processing"], ("input_state", "sign", "blank", "offset"))
    processing = value["heat_processing"]
    require(processing["input_state"] in (None, "uncorrected", "already_corrected"))
    require(processing["sign"] is None or type(processing["sign"]) is int and processing["sign"] in (-1, 1))
    require(all(processing[k] in (None, "not_applied", "subtract_supplied") for k in ("blank", "offset")))
    rows = value["injections"]
    require(rows is None or type(rows) is list)
    if rows is not None:
        ids = []
        for row in rows:
            closed(row, ("injection_id", "volume", "syringe_ligand_concentration", "heat", "blank_heat", "offset_heat"))
            require(text(row["injection_id"])); ids.append(row["injection_id"])
            for key in ("volume", "syringe_ligand_concentration", "heat"):
                quantity(row[key], {"volume": "L", "syringe_ligand_concentration": "mol/L", "heat": "J"}[key])
            for key in ("blank_heat", "offset_heat"):
                if row[key] is not None: quantity(row[key], "J")
        require(len(ids) == len(set(ids)), "unique_injection_ids_required")
    quantity(value["temperature"], "K")
    return value


def validate_itc_binding_fit_selection(value):
    value = copy_json(value)
    closed(value, ("version", "residual_injection_ids", "initial_parameters", "bounds", "solver", "weighting"))
    require(value["version"] == FIT_SELECTION_VERSION)
    ids = value["residual_injection_ids"]
    require(type(ids) is list and all(text(item) for item in ids) and len(ids) == len(set(ids)))
    parameter_values(value["initial_parameters"])
    closed(value["bounds"], PARAMETERS)
    for bounds in value["bounds"].values():
        closed(bounds, ("lower", "upper"))
        require(all(item is None or number(item) for item in bounds.values()))
    solver = value["solver"]
    closed(solver, ("method", "jacobian", "ftol", "xtol", "gtol", "max_nfev", "x_scale", "diff_step"))
    require(solver["method"] == "trf" and solver["jacobian"] == "2-point")
    require(all(number(solver[k]) and solver[k] > 0 for k in ("ftol", "xtol", "gtol")))
    require(type(solver["max_nfev"]) is int and solver["max_nfev"] > 0)
    for key in ("x_scale", "diff_step"):
        require(type(solver[key]) is list and len(solver[key]) == 3
            and all(number(item) and item > 0 for item in solver[key]))
    weights = value["weighting"]
    closed(weights, ("kind", "independent_error_assumption", "absolute_sigma", "sigma_heat"))
    require(weights["kind"] in ("unweighted", "diagonal_sigma") and type(weights["absolute_sigma"]) is bool)
    require(type(weights["sigma_heat"]) is list)
    if weights["kind"] == "unweighted":
        require(weights["independent_error_assumption"] is None and weights["sigma_heat"] == [])
    else:
        require(weights["independent_error_assumption"] is True, "independent_error_assumption_required")
        require(all(type(row) is dict for row in weights["sigma_heat"]))
        require([row.get("injection_id") for row in weights["sigma_heat"]] == ids, "selected_sigma_population_required")
        for row in weights["sigma_heat"]:
            closed(row, ("injection_id", "sigma")); quantity(row["sigma"], "J")
    return value


def validate_itc_binding_selection(value):
    value = copy_json(value)
    closed(value, ("version", "parameter_source", "parameters", "injection_ids", "fit_diagnostics"))
    require(value["version"] == SELECTION_VERSION and value["parameter_source"] in ("fit_observation", "selected_parameters"))
    if value["parameter_source"] == "selected_parameters": parameter_values(value["parameters"])
    else: require(value["parameters"] is None)
    ids = value["injection_ids"]
    require(type(ids) is list and all(text(item) for item in ids) and len(ids) == len(set(ids)))
    require(type(value["fit_diagnostics"]) is bool)
    return value


def observed_number(value):
    closed(value, ("state", "value"))
    require(value["state"] in ("finite", "nan", "positive_infinity", "negative_infinity"))
    require(number(value["value"]) if value["state"] == "finite" else value["value"] is None)


def itc_binding_covariance_metadata(weighting):
    """Native estimator meaning and unit products, without covariance math.

    Each entry has the product of its row and column parameter units. The
    matrix is SciPy's returned local linearization estimate, not an established
    experimental covariance or proof of parameter identifiability.
    """
    return dict(parameter_order=list(PARAMETERS), parameter_units=[PARAMETER_UNITS[name] for name in PARAMETERS],
        entry_unit_products=[[dict(row_unit=PARAMETER_UNITS[row], column_unit=PARAMETER_UNITS[column])
            for column in PARAMETERS] for row in PARAMETERS],
        estimator="scipy.optimize.curve_fit", method="trf",
        construction="native_local_jacobian_pseudoinverse_estimate",
        weighting=weighting["kind"], absolute_sigma=weighting["absolute_sigma"],
        scaling="native_absolute_sigma_true" if weighting["absolute_sigma"] else "native_reduced_chisquare_rescaling",
        conditional_on="selected_model_inputs_and_error_assumption",
        statistical_validity="not_assessed", identifiability="not_assessed")


def validate_itc_binding_fit_observation(value):
    value = copy_json(value)
    closed(value, ("version", "supplied_sha256", "selection", "call_state", "call_count", "software",
        "effective_arguments", "prepared_data", "native_parameters", "native_covariance", "covariance_metadata", "warnings", "qualifications", "failure"))
    require(value["version"] == FIT_OBSERVATION_VERSION and text(value["supplied_sha256"]))
    require(len(value["supplied_sha256"]) == 64 and all(c in "0123456789abcdef" for c in value["supplied_sha256"]))
    validate_itc_binding_fit_selection(value["selection"])
    require(type(value["covariance_metadata"]) is dict and type(value["covariance_metadata"].get("absolute_sigma")) is bool)
    require(value["covariance_metadata"] == itc_binding_covariance_metadata(value["selection"]["weighting"]), "covariance_metadata_conflict")
    require(value["call_state"] in ("not_started", "returned", "raised", "uncertain"))
    require(value["call_count"] is None or type(value["call_count"]) is int and value["call_count"] in (0, 1))
    require((value["call_state"], value["call_count"]) in (("not_started", 0), ("returned", 1), ("raised", 1), ("uncertain", None)))
    require(type(value["warnings"]) is list)
    require(type(value["qualifications"]) is list and all(item in (
        "underdetermined_selected_population", "nonpositive_residual_degrees_of_freedom",
        "later_unavailable_history_not_in_objective", "fit_does_not_establish_identifiability",
        "in_process_software_observation_is_not_host_commission") for item in value["qualifications"]))
    for warning in value["warnings"]:
        closed(warning, ("category", "message")); require(all(type(item) is str for item in warning.values()))
    if value["software"] is not None:
        closed(value["software"], ("authority", "python_executable", "python_version", "scipy_version", "numpy_version", "callable", "implementation_files"))
        require(value["software"]["authority"] == "observed_in_process_not_host_commission")
        require(text(value["software"]["python_executable"]))
        for key in ("python_version", "scipy_version", "numpy_version"):
            require(type(value["software"][key]) is str and bool(value["software"][key]))
        closed(value["software"]["callable"], ("module", "qualname", "file"))
        for key in ("module", "qualname"): require(text(value["software"]["callable"][key]))
        require(type(value["software"]["implementation_files"]) is list)
        files = [value["software"]["callable"]["file"], *value["software"]["implementation_files"]]
        for file in files:
            closed(file, ("path", "sha256", "size_bytes"))
            require(text(file["path"]) and text(file["sha256"]) and type(file["size_bytes"]) is int and file["size_bytes"] >= 0)
            require(len(file["sha256"]) == 64 and all(c in "0123456789abcdef" for c in file["sha256"]))
    if value["effective_arguments"] is not None:
        args = value["effective_arguments"]
        closed(args, ("p0", "lower_bounds", "upper_bounds", "sigma", "absolute_sigma", "method", "jac",
            "ftol", "xtol", "gtol", "max_nfev", "x_scale", "diff_step"))
        for key in ("p0", "x_scale", "diff_step"):
            require(type(args[key]) is list and len(args[key]) == 3 and all(number(item) for item in args[key]))
        require(all(number(args[key]) and args[key] > 0 for key in ("ftol", "xtol", "gtol")))
        require(type(args["max_nfev"]) is int and args["max_nfev"] > 0)
        for key in ("lower_bounds", "upper_bounds"):
            require(type(args[key]) is list and len(args[key]) == 3)
            for item in args[key]: observed_number(item)
        require(args["sigma"] is None or type(args["sigma"]) is list and all(number(item) and item > 0 for item in args["sigma"]))
        solver, weights = value["selection"]["solver"], value["selection"]["weighting"]
        require(args["p0"] == [float(value["selection"]["initial_parameters"][name]) for name in PARAMETERS])
        require(all(args[key] == solver[key] for key in ("method", "ftol", "xtol", "gtol", "max_nfev", "x_scale", "diff_step")))
        require(args["jac"] == solver["jacobian"] and args["absolute_sigma"] is weights["absolute_sigma"])
        for key, side, infinity in (("lower_bounds", "lower", "negative_infinity"), ("upper_bounds", "upper", "positive_infinity")):
            for name, cell in zip(PARAMETERS, args[key]):
                bound = value["selection"]["bounds"][name][side]
                require(cell == (dict(state=infinity, value=None) if bound is None else dict(state="finite", value=float(bound))))
    if value["prepared_data"] is not None:
        closed(value["prepared_data"], ("injection_ids", "heats_joule", "sigma_joule"))
        data = value["prepared_data"]
        require(data["injection_ids"] == value["selection"]["residual_injection_ids"] and type(data["heats_joule"]) is list)
        require(len(data["heats_joule"]) == len(data["injection_ids"]) and all(number(item) for item in data["heats_joule"]))
        require(data["sigma_joule"] is None or type(data["sigma_joule"]) is list
            and len(data["sigma_joule"]) == len(data["injection_ids"]) and all(number(item) and item > 0 for item in data["sigma_joule"]))
        require((data["sigma_joule"] is None) == (value["selection"]["weighting"]["kind"] == "unweighted"))
        if value["effective_arguments"] is not None: require(value["effective_arguments"]["sigma"] == data["sigma_joule"])
    if value["native_parameters"] is not None:
        require(type(value["native_parameters"]) is list)
        for item in value["native_parameters"]: observed_number(item)
    if value["native_covariance"] is not None:
        require(type(value["native_covariance"]) is list)
        for row in value["native_covariance"]:
            require(type(row) is list)
            for item in row: observed_number(item)
    if value["failure"] is not None:
        closed(value["failure"], ("stage", "code", "exception_type", "message"))
        require(value["failure"]["stage"] in ("input", "software", "fit", "serialization"))
        require(text(value["failure"]["code"]))
        require(all(value["failure"][key] is None or type(value["failure"][key]) is str for key in ("exception_type", "message")))
    if value["call_count"] == 1: require(value["software"] is not None and value["prepared_data"] is not None)
    if value["call_count"] == 1: require(value["effective_arguments"] is not None)
    if value["call_state"] != "returned": require(value["native_parameters"] is None and value["native_covariance"] is None)
    if value["failure"] is None: require(value["call_state"] == "returned")
    elif value["call_state"] == "returned": require(value["failure"]["stage"] == "serialization")
    if value["call_state"] == "returned" and value["failure"] is None:
        require(value["native_parameters"] is not None and value["native_covariance"] is not None)
    return value


def validate_itc_binding_sheet(value):
    value = copy_json(value); closed(value, ("version", "supplied", "fit_observation"))
    require(value["version"] == SHEET_VERSION)
    validate_itc_binding_supplied(value["supplied"])
    if value["fit_observation"] is not None:
        validate_itc_binding_fit_observation(value["fit_observation"])
        require(value["fit_observation"]["supplied_sha256"] == digest(value["supplied"]), "fit_input_conflict")
    return value


def _cell(value, unit):
    closed(value, ("state", "value", "unit", "reason"))
    require(value["unit"] == unit and value["state"] in ("present", "unavailable"))
    require((number(value["value"]) and value["reason"] is None) if value["state"] == "present" else
        (value["value"] is None and value["reason"] in REASONS))


def _prediction_row(value, *, residual=False):
    units = dict(injection_volume="L", syringe_ligand_concentration="mol/L", retained_cell_fraction="fraction",
        macromolecule_concentration="mol/L", ligand_concentration="mol/L", bound_complex_concentration="mol/L",
        predicted_heat="J", corrected_heat="J")
    if residual: units["residual"] = "J"
    closed(value, ("injection_id", "delivered_ordinal", *units))
    require(text(value["injection_id"]) and type(value["delivered_ordinal"]) is int and value["delivered_ordinal"] >= 0)
    for name, unit in units.items(): _cell(value[name], unit)


def validate_itc_binding_prediction(value):
    value = copy_json(value)
    closed(value, ("version", "parameters", "initial_state", "history", "input_reasons", "qualifications"))
    require(value["version"] == PREDICTION_VERSION); parameter_values(value["parameters"])
    units = dict(volume="L", macromolecule_concentration="mol/L", ligand_concentration="mol/L", bound_complex_concentration="mol/L")
    closed(value["initial_state"], units)
    for name, unit in units.items(): _cell(value["initial_state"][name], unit)
    require(value["history"] is None or type(value["history"]) is list)
    for row in value["history"] or []: _prediction_row(row)
    require(type(value["input_reasons"]) is list and all(reason in REASONS for reason in value["input_reasons"]))
    require(value["qualifications"] == ["supplied_history_completeness_is_an_assertion", "unit_conversions_are_supplied_assertions",
        "binary64_equilibrium_evaluation", "n_is_effective_sites_per_declared_macromolecule"])
    return value


def validate_itc_binding_components_shape(value):
    """Literal stored shape only; this neither fits nor recalculates values."""
    value = copy_json(value)
    closed(value, ("version", "sheet", "selection", "parameter_values", "delivered_injection_ids", "rows",
        "full_prediction", "fit_diagnostics", "temperature", "origin", "scientific_provenance", "identifiability"))
    require(value["version"] == COMPONENTS_VERSION)
    validate_itc_binding_sheet(value["sheet"]); validate_itc_binding_selection(value["selection"])
    closed(value["parameter_values"], PARAMETERS)
    for name, unit in PARAMETER_UNITS.items(): _cell(value["parameter_values"][name], unit)
    history = value["sheet"]["supplied"]["injections"]
    expected = None if history is None else [row["injection_id"] for row in history]
    require(value["delivered_injection_ids"] == expected and type(value["rows"]) is list)
    require(all(type(row) is dict for row in value["rows"]))
    require([row.get("injection_id") for row in value["rows"]] == value["selection"]["injection_ids"])
    for row in value["rows"]: _prediction_row(row, residual=True)
    if value["full_prediction"] is not None:
        validate_itc_binding_prediction(value["full_prediction"])
        prediction_history = value["full_prediction"]["history"]
        require((None if prediction_history is None else [row["injection_id"] for row in prediction_history]) == expected)
        require(prediction_history is None or [row["delivered_ordinal"] for row in prediction_history] == list(range(len(expected))))
    require(expected is not None or value["rows"] == [])
    require(all(row["injection_id"] in expected and row["delivered_ordinal"] == expected.index(row["injection_id"]) for row in value["rows"]))
    _cell(value["temperature"], "K")
    require(value["origin"] == "explicit_saved_calculation" and value["scientific_provenance"] == "not_authenticated_by_numerical_document"
        and value["identifiability"] == "not_assessed")
    diagnostics = value["fit_diagnostics"]
    if not value["selection"]["fit_diagnostics"]: require(diagnostics is None)
    if diagnostics is not None:
        closed(diagnostics, ("residual_injection_ids", "observation_count", "parameter_count", "residual_degrees_of_freedom",
            "underdetermined", "sse", "selected_objective", "residual_unavailable_ids", "raw_covariance", "covariance_metadata", "kd_delta_h_block_assessment",
            "covariance_scope", "statistical_covariance_validity", "identifiability", "parameter_bound_contacts", "absolute_sigma",
            "independent_error_assumption"))
        observation = value["sheet"]["fit_observation"]
        require(observation is not None and diagnostics["residual_injection_ids"] == observation["selection"]["residual_injection_ids"])
        count = len(diagnostics["residual_injection_ids"])
        require(type(diagnostics["observation_count"]) is int and diagnostics["observation_count"] == count
            and type(diagnostics["parameter_count"]) is int and diagnostics["parameter_count"] == 3
            and type(diagnostics["residual_degrees_of_freedom"]) is int and diagnostics["residual_degrees_of_freedom"] == count-3
            and type(diagnostics["underdetermined"]) is bool and diagnostics["underdetermined"] == (count<3))
        _cell(diagnostics["sse"], "J^2")
        _cell(diagnostics["selected_objective"], "dimensionless" if observation["selection"]["weighting"]["kind"] == "diagonal_sigma" else "J^2")
        require(type(diagnostics["residual_unavailable_ids"]) is list and all(item in diagnostics["residual_injection_ids"] for item in diagnostics["residual_unavailable_ids"]))
        require(diagnostics["raw_covariance"] == observation["native_covariance"])
        require(type(diagnostics["covariance_metadata"]) is dict and type(diagnostics["covariance_metadata"].get("absolute_sigma")) is bool)
        require(diagnostics["covariance_metadata"] == observation["covariance_metadata"])
        require(diagnostics["covariance_scope"] == "named_kd_delta_h_block_only" and diagnostics["statistical_covariance_validity"] == "not_assessed"
            and diagnostics["identifiability"] == "not_assessed")
        block = diagnostics["kd_delta_h_block_assessment"]
        if block is not None:
            closed(block, ("status", "symmetry", "symmetric_part_positive_semidefinite"))
            require(block["status"] in ("accepted", "shape_invalid", "entry_not_finite_binary64", "symmetric_part_indefinite")
                and block["symmetry"] in ("exact", "asymmetric", "unavailable")
                and (block["symmetric_part_positive_semidefinite"] is None or type(block["symmetric_part_positive_semidefinite"]) is bool))
        require(type(diagnostics["parameter_bound_contacts"]) is list)
        for contact in diagnostics["parameter_bound_contacts"]:
            closed(contact, ("parameter", "side")); require(contact["parameter"] in PARAMETERS and contact["side"] in ("lower", "upper"))
        weights = observation["selection"]["weighting"]
        require(diagnostics["absolute_sigma"] is weights["absolute_sigma"] and diagnostics["independent_error_assumption"] is weights["independent_error_assumption"])
    return value
