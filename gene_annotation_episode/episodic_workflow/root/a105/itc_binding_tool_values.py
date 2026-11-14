"""A105 private original ITC request, worker values and literal return contracts.

Retained callable behavior only; not registered as an episode tool.
"""
from copy import deepcopy
import json
from .domain import REF, canonical, obj
from gene_annotation_episode.domain import ContractError
from .itc_binding_contracts import (
    FIT_SELECTION_VERSION, PARAMETERS, REASONS, SELECTION_VERSION, SHEET_VERSION, copy_json, number,
    validate_itc_binding_components_shape, validate_itc_binding_fit_selection,
    validate_itc_binding_selection, validate_itc_binding_sheet, validate_itc_binding_supplied,
)

ITC_TOOL = "analyze_itc_binding_thermodynamics"
REQUEST_VERSION = "ordinary_itc_request_v1"
RESULT_VERSION = "ordinary_itc_result_v1"
ROW_FIELDS = ("injection_volume", "syringe_ligand_concentration", "retained_cell_fraction",
    "macromolecule_concentration", "ligand_concentration", "bound_complex_concentration",
    "predicted_heat", "corrected_heat", "residual")
UNIT_CODES = {"L": "litre", "mol/L": "mol_per_litre", "J": "joule", "K": "kelvin",
    "fraction": "fraction", "J/mol": "joule_per_mole", "J^2": "joule_squared",
    "dimensionless": "dimensionless", "sites_per_macromolecule": "sites_per_macromolecule"}

def itc_tool_contract():
    """One local operation; modes do not imply a child or another model call."""
    numeric = {"type": "number"}
    nullable = {"anyOf": [numeric, {"type": "null"}]}
    parameters = obj({name: numeric for name in PARAMETERS})
    ordinals = {"type": "array", "items": {"type": "integer", "minimum": 0}, "uniqueItems": True}
    triple = {"type": "array", "items": {"type": "number", "exclusiveMinimum": 0},
        "minItems": 3, "maxItems": 3}
    positive = {"type": "number", "exclusiveMinimum": 0}
    fit = obj(dict(mode={"const": "fit"},
        input=obj(dict(namespace={"enum": ["source", "artifact"]}, reference=REF)),
        residual_injection_ordinals=ordinals, initial_parameters=parameters,
        bounds=obj({name: obj(dict(lower=nullable, upper=nullable)) for name in PARAMETERS}),
        solver=obj(dict(method={"const": "trf"}, jacobian={"const": "two_point"},
            ftol=positive, xtol=positive, gtol=positive,
            max_nfev={"type": "integer", "minimum": 1}, x_scale=triple, diff_step=triple)),
        weighting=obj(dict(kind={"enum": ["unweighted", "diagonal_sigma"]},
            independent_error_assumption={"enum": [None, True]}, absolute_sigma={"type": "boolean"},
            sigma_heat_joule={"type": "array", "items": positive}))))
    saved = obj(dict(mode={"const": "calculate_saved"}, result_ref=REF,
        parameter_source={"enum": ["fit_observation", "selected_parameters"]},
        parameters={"anyOf": [parameters, {"type": "null"}]},
        injection_ordinals=ordinals, fit_diagnostics={"type": "boolean"}))
    read = obj(dict(mode={"const": "read_stored"}, result_ref=REF, injection_ordinals=ordinals,
        fields={"type": "array", "items": {"enum": list(ROW_FIELDS)}, "uniqueItems": True}))
    return dict(resources="local", description=(
        "Fit the physical one-site ITC model, with stoichiometry n in the binding balance, to an explicitly "
        "received ITC JSON File using your selected injection residuals, bounds, solver and error assumption. "
        "Retain Kd (mol/L), n (sites/macromolecule), enthalpy (J/mol), full injection history, residuals "
        "and the native covariance estimate with its qualifications. Supplied heat/volume/concentration "
        "calibration remains an assertion. Alternatively calculate from the retained sheet with explicitly "
        "selected parameters, or read stored cells without fitting. SSE, objective and covariance still "
        "describe the retained original fitted vector and residual population when you select different "
        "forward parameters. This ordinary tool runs within the "
        "current episode; choose subsequent investigation actions from the returned results."),
        input_schema={"anyOf": [fit, saved, read]})



def _ids(supplied, ordinals):
    rows = supplied["injections"] or []
    if (type(ordinals) is not list or any(type(i) is not int or i < 0 or i >= len(rows) for i in ordinals)
            or len(ordinals) != len(set(ordinals))):
        raise ContractError("itc_binding_injection_ordinal_invalid")
    return [rows[i]["injection_id"] for i in ordinals]



def prepare_itc_tool_request(arguments, *, received_input, invocation, original=None):
    """Retain the exact selected ordinal→native-ID mapping, without provenance invention."""
    mode = arguments["mode"]
    supplied = validate_itc_binding_supplied(received_input["content"]["value"] if mode == "fit"
        else original["sheet"]["supplied"])
    ids = _ids(supplied, arguments["residual_injection_ordinals"] if mode == "fit" else arguments["injection_ordinals"])
    fit_selection = None
    if mode == "fit":
        weighting = deepcopy(arguments["weighting"])
        sigmas = weighting.pop("sigma_heat_joule")
        if weighting["kind"] == "unweighted" and sigmas or weighting["kind"] == "diagonal_sigma" and len(sigmas) != len(ids):
            raise ContractError("itc_binding_selected_sigma_population_required")
        weighting["sigma_heat"] = [dict(injection_id=key, sigma=dict(value=value,
            unit="J", canonical_unit="J", to_canonical_factor=1, source_ref=None, source_pointer=None))
            for key, value in zip(ids, sigmas)]
        solver = deepcopy(arguments["solver"]); solver["jacobian"] = "2-point"
        fit_selection = validate_itc_binding_fit_selection(dict(version=FIT_SELECTION_VERSION,
            residual_injection_ids=ids, initial_parameters=arguments["initial_parameters"],
            bounds=arguments["bounds"], solver=solver, weighting=weighting))
        selection = dict(version=SELECTION_VERSION, parameter_source="fit_observation", parameters=None,
            injection_ids=ids, fit_diagnostics=True)
        sheet = dict(version=SHEET_VERSION, supplied=supplied, fit_observation=None)
    else:
        selection = dict(version=SELECTION_VERSION, parameter_source=arguments["parameter_source"],
            parameters=arguments["parameters"], injection_ids=ids, fit_diagnostics=arguments["fit_diagnostics"])
        sheet = original["sheet"]
    return dict(version=REQUEST_VERSION, invocation=deepcopy(invocation), arguments=deepcopy(arguments),
        received_input=deepcopy(received_input), sheet=validate_itc_binding_sheet(sheet),
        fit_selection=fit_selection, selection=validate_itc_binding_selection(selection))



def run_itc_tool_request(request, *, output_directory):
    """Store-free worker: exactly one fit in fit mode; saved mode never imports it."""
    if request.get("version") != REQUEST_VERSION or request["arguments"]["mode"] not in ("fit", "calculate_saved"):
        raise ValueError("ordinary_itc_request_invalid")
    from .itc_binding_measurements import calculate_itc_binding_components
    sheet = validate_itc_binding_sheet(request["sheet"])
    if request["arguments"]["mode"] == "fit":
        from .itc_binding_fit import fit_itc_binding_measurements
        sheet["fit_observation"] = fit_itc_binding_measurements(sheet, selection=request["fit_selection"])
    components = calculate_itc_binding_components(sheet, selection=request["selection"])
    return dict(version=RESULT_VERSION, request=deepcopy(request), sheet=sheet, components=components)



def _worker_request(request):
    """Only scientific operands enter the worker/native scientific result.

    Receiver lineage, run/action identity and admission evidence stay in the
    separately retained host control, rather than source-readable result data.
    """
    return {**{key: deepcopy(request[key]) for key in
        ("version", "arguments", "sheet", "fit_selection", "selection")},
        "input_file": deepcopy(request["received_input"]["file"])}



def _validate_result(value, request=None):
    if (type(value) is not dict or set(value) != {"version", "request", "sheet", "components"}
            or value["version"] != RESULT_VERSION or value["request"].get("version") != REQUEST_VERSION
            or request is not None and canonical(value["request"]) != canonical(request)):
        raise ContractError("ordinary_itc_result_conflict")
    validate_itc_binding_sheet(value["sheet"])
    validate_itc_binding_components_shape(value["components"])
    if (canonical(value["components"]["sheet"]) != canonical(value["sheet"])
            or canonical(value["components"]["selection"]) != canonical(value["request"]["selection"])
            or canonical(value["sheet"]["supplied"]) != canonical(value["request"]["sheet"]["supplied"])):
        raise ContractError("ordinary_itc_result_conflict")
    observation = value["sheet"]["fit_observation"]
    if value["request"]["arguments"]["mode"] == "fit":
        if observation is None or canonical(observation["selection"]) != canonical(value["request"]["fit_selection"]):
            raise ContractError("ordinary_itc_fit_selection_conflict")
    elif canonical(value["sheet"]) != canonical(value["request"]["sheet"]):
        raise ContractError("ordinary_itc_saved_sheet_conflict")
    return value



def _cell(value):
    return {**deepcopy(value), "unit": UNIT_CODES[value["unit"]]}



def project_itc_tool_result(stored, *, selection, source_ref, artifact_ref, grading_ref):
    """Select literal stored cells; no fitting or numerical reconstruction."""
    components = stored["components"]
    ordinals = selection.get("injection_ordinals", selection.get("residual_injection_ordinals", []))
    _ids(stored["sheet"]["supplied"], ordinals)
    fields = selection.get("fields", ROW_FIELDS)
    rows = {row["delivered_ordinal"]: row for row in components["rows"]}
    if any(i not in rows for i in ordinals):
        raise ContractError("ordinary_itc_cells_not_stored")
    observation = stored["sheet"]["fit_observation"]
    diagnostics = components["fit_diagnostics"]
    return dict(version="ordinary_itc_values_v1", mode=selection["mode"], source_ref=source_ref,
        native_file=dict(artifact_ref=artifact_ref, format="json"), grading_ref=grading_ref,
        parameters={name: _cell(value) for name, value in components["parameter_values"].items()},
        rows=[dict(injection_ordinal=i, **{name: _cell(rows[i][name]) for name in fields}) for i in ordinals],
        fit_call_state=observation["call_state"] if observation else "not_started",
        fit_call_count=observation["call_count"] if observation else 0,
        fit_call_scope="retained_fit_observation", this_operation_fit=selection["mode"] == "fit",
        parameter_source=components["selection"]["parameter_source"],
        residual_population_count=None if diagnostics is None else diagnostics["observation_count"],
        residual_degrees_of_freedom=None if diagnostics is None else diagnostics["residual_degrees_of_freedom"],
        sse=None if diagnostics is None else _cell(diagnostics["sse"]),
        selected_objective=None if diagnostics is None else _cell(diagnostics["selected_objective"]),
        covariance_estimate=None if observation is None else deepcopy(observation["native_covariance"]),
        fit_diagnostics_scope=None if diagnostics is None else "retained_original_fit_vector_and_residual_population",
        covariance_scope=None if observation is None or observation['native_covariance'] is None else
            "retained_original_fit_vector_and_residual_population",
        covariance_parameter_order=list(PARAMETERS),
        covariance_parameter_units=["mol_per_litre", "sites_per_macromolecule", "joule_per_mole"],
        covariance_validity="not_assessed", identifiability="not_assessed",
        weighting=None if observation is None else observation["selection"]["weighting"]["kind"],
        independent_error_assumption=None if observation is None else
            observation["selection"]["weighting"]["independent_error_assumption"],
        absolute_sigma=None if observation is None else observation["selection"]["weighting"]["absolute_sigma"],
        warning_locations=[] if observation is None else [dict(source_ref=source_ref,
            location="fit_warning", occurrence=i) for i in range(len(observation["warnings"]))],
        failure_location=None if observation is None or observation["failure"] is None else
            dict(source_ref=source_ref, location="fit_failure", occurrence=0))


ITC_PARAMETER_SOURCE = "itc_binding_parameters"
_FIT_QUALIFICATIONS = ("underdetermined_selected_population", "nonpositive_residual_degrees_of_freedom",
    "later_unavailable_history_not_in_objective", "fit_does_not_establish_identifiability",
    "in_process_software_observation_is_not_host_commission")
_PREDICTION_QUALIFICATIONS = ("supplied_history_completeness_is_an_assertion",
    "unit_conversions_are_supplied_assertions", "binary64_equilibrium_evaluation",
    "n_is_effective_sites_per_declared_macromolecule")
_ORIGINAL_FIT_SCOPE = "retained_original_fit_vector_and_residual_population"


def itc_parameter_fact_sources():
    """Describe literal parameter cells, without granting Files or fit authority."""
    def enum(values, nullable=False):
        return {"type": ["string", "null"] if nullable else "string",
            "enum": [*values, None] if nullable else list(values)}
    def cell(unit):
        return obj(dict(state=enum(("present", "unavailable")), value={"type": ["number", "null"]},
            unit={"const": unit, "type": "string"}, reason=enum(REASONS, True)))
    fields = dict(version={"const": "itc_parameter_return_v1", "type": "string"},
        source_ref={"type": "string", "format": "reference", "x-reference-namespace": "source"},
        parameter_source=enum(("fit_observation", "selected_parameters")),
        kd=cell("mol_per_litre"), n=cell("sites_per_macromolecule"), delta_h=cell("joule_per_mole"),
        cell_scope={"type": "string", "const": "retained_components_parameter_vector"},
        fit_call_state=enum(("not_started", "returned", "raised", "uncertain"), True),
        fit_call_count={"type": ["integer", "null"], "minimum": 0, "maximum": 1},
        fit_diagnostics_scope=enum((_ORIGINAL_FIT_SCOPE,), True),
        weighting=enum(("unweighted", "diagonal_sigma"), True),
        independent_error_assumption={"type": ["boolean", "null"]},
        absolute_sigma={"type": ["boolean", "null"]},
        fit_qualification_codes={"type": ["array", "null"], "items": enum(_FIT_QUALIFICATIONS)},
        prediction_qualification_codes={"type": ["array", "null"], "items": enum(_PREDICTION_QUALIFICATIONS)},
        calibration_authority={"type": "string", "const": "supplied_assertion"},
        n_meaning={"type": "string", "const": "effective_sites_per_declared_macromolecule"},
        identifiability={"type": "string", "const": "not_assessed"},
        statistical_covariance_validity={"type": "string", "const": "not_assessed"},
        warning_locations={"type": "array", "items": obj(dict(
            location_code={"type": "string", "const": "fit_warning"}, ordinal={"type": "integer", "minimum": 0}))},
        failure_location={**obj(dict(location_code={"type": "string", "const": "fit_failure"},
            ordinal={"type": "integer", "const": 0}, stage=enum(("input", "software", "fit", "serialization")))),
            "type": ["object", "null"]})
    return {ITC_PARAMETER_SOURCE: dict(type="array", meaning=(
        "Literal retained ITC parameter cells and original-fit qualifications; supplied calibration remains an assertion, "
        "and parameter identifiability and statistical covariance validity remain unassessed."),
        report_schema={"type": "array", "items": obj(fields), "x-source": ITC_PARAMETER_SOURCE})}

def validate_itc_parameter_return(value):
    """Validate closed public meaning only; this confers no source authority."""
    from jsonschema import Draft202012Validator
    import re
    value = copy_json(value)
    schema = itc_parameter_fact_sources()[ITC_PARAMETER_SOURCE]["report_schema"]["items"]
    if not Draft202012Validator(schema).is_valid(value):
        raise ContractError("itc_parameter_return_invalid")
    if re.fullmatch(r"source_[a-f0-9]{24,64}", value["source_ref"]) is None:
        raise ContractError("itc_parameter_return_source_invalid")
    for name in PARAMETERS:
        cell = value[name]
        if not ((cell["state"] == "present" and number(cell["value"]) and cell["reason"] is None)
                or (cell["state"] == "unavailable" and cell["value"] is None and cell["reason"] in REASONS)):
            raise ContractError("itc_parameter_return_cell_invalid")
    count = value["fit_call_count"]
    if (count is not None and type(count) is not int
            or (value["fit_call_state"], count) not in
                ((None, None), ("not_started", 0), ("returned", 1), ("raised", 1), ("uncertain", None))):
        raise ContractError("itc_parameter_return_call_conflict")
    if any(type(row["ordinal"]) is not int for row in value["warning_locations"]):
        raise ContractError("itc_parameter_return_location_invalid")
    failure = value["failure_location"]
    if failure is not None and type(failure["ordinal"]) is not int:
        raise ContractError("itc_parameter_return_location_invalid")
    return value

def project_itc_parameter_return(stored, *, source_ref):
    """Copy the retained parameter vector; do not calculate or read Files."""
    value = _validate_result(stored)
    components, observation = value["components"], value["sheet"]["fit_observation"]
    prediction = components["full_prediction"]
    weights = None if observation is None else observation["selection"]["weighting"]
    return validate_itc_parameter_return(dict(version="itc_parameter_return_v1", source_ref=source_ref,
        parameter_source=components["selection"]["parameter_source"],
        **{name: _cell(components["parameter_values"][name]) for name in PARAMETERS},
        cell_scope="retained_components_parameter_vector",
        fit_call_state=None if observation is None else observation["call_state"],
        fit_call_count=None if observation is None else observation["call_count"],
        fit_diagnostics_scope=None if components["fit_diagnostics"] is None else _ORIGINAL_FIT_SCOPE,
        weighting=None if weights is None else weights["kind"],
        independent_error_assumption=None if weights is None else weights["independent_error_assumption"],
        absolute_sigma=None if weights is None else weights["absolute_sigma"],
        fit_qualification_codes=None if observation is None else deepcopy(observation["qualifications"]),
        prediction_qualification_codes=None if prediction is None else deepcopy(prediction["qualifications"]),
        calibration_authority="supplied_assertion", n_meaning="effective_sites_per_declared_macromolecule",
        identifiability="not_assessed", statistical_covariance_validity="not_assessed",
        warning_locations=[] if observation is None else [dict(location_code="fit_warning", ordinal=i)
            for i in range(len(observation["warnings"]))],
        failure_location=None if observation is None or observation["failure"] is None else dict(
            location_code="fit_failure", ordinal=0, stage=observation["failure"]["stage"])))

