"""Closed, source-preserving records for the shared continuous FBA analysis.

This module validates supplied data only. It does not decode native files, load
models, run a solver, or calculate scientific diagnostics. The sole Python-bytes
exception is FBAArtifactPayloads, the explicit parser call boundary.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import math
import re


__all__ = ["ISSUE_CODES", "flux_balance_schema", "validate_flux_balance_record", "validate_fba_artifact_payloads",
           "normalize_fba_solver_status"]

ISSUE_CODES = frozenset("""
input_missing unsupported_model_format model_load_failed model_identity_conflict
reaction_id_unknown duplicate_reaction_id bound_invalid constraint_rejected
objective_rejected request_effective_mismatch solver_unavailable solver_exception
status_unrecognized flux_missing flux_nonfinite artifact_missing artifact_truncated
artifact_identity_conflict schema_invalid unsupported_problem_form unknown_units
native_derived_conflict missing_parameters writer_not_closed projection_invalid
saved_sheet_not_received binding_unavailable numeric_overflow objective_unavailable
constraint_unavailable zero_denominator primal_not_established solver_option_unsupported
loader_default_applied source_semantics_unsupported variable_identity_conflict
constraint_identity_conflict variable_missing variable_nonfinite duplicate_variable_id
duplicate_constraint_id coefficient_nonfinite term_population_incomplete
flux_identity_conflict unit_incompatible partial_population source_precision_unknown
""".split())


def _enum(values):
    return {"enum": list(values.split()) if isinstance(values, str) else list(values)}


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def _array(schema):
    return {"type": "array", "items": schema}


def _object(**fields):
    return {"type": "object", "properties": fields,
            "required": list(fields), "additionalProperties": False}


_TEXT = {"type": "string", "minLength": 1, "maxLength": 1048576,
         "pattern": r"^[^\x00-\x1f\x7f]+$"}
_RAW = {"type": "string"}
_POINTER = {"type": "string", "pattern": r"^(?:/(?:[^~]|~[01])*)*$"}
_REAL = {"type": "number"}
_UINT = {"type": "integer", "minimum": 0}
_INT = {"type": "integer"}
_POS = {"type": "integer", "minimum": 1}
_BOOL = {"type": "boolean"}
_SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_JSON_OBJECT = {"type": "object", "additionalProperties": True}
_S = {}


def _record(record_name, **fields):
    _S[record_name] = _object(**fields)
    _S[record_name]["x-fba-record"] = record_name
    return _S[record_name]


def _optional(schema, **fields):
    """Declare additions without weakening any previously required property."""
    schema["properties"].update(fields)
    return schema


_ROLE = _enum("original_model selected_request effective_model effective_problem solution flux_csv native_log manifest")
_STATUS = _enum("optimal feasible infeasible unbounded infeasible_or_unbounded time_limit iteration_limit numerical_failure error unknown")
_COMPARISON = _enum("passes fails unknown")
_AGREEMENT = _enum("agrees conflicts unknown")
_OUTCOME = _enum("completed partial failed not_executed")
_REALIZATION = _enum("exact mismatch unknown")
_MULTIPLICITY = _enum("not_assessed reported_alternate reported_unique conflicting")
_STATE = _enum("present absent truncated incompatible")
_ISSUE_CODE = _enum(sorted(ISSUE_CODES))
_IDENTITY = _record("ArtifactIdentity", sha256=_SHA, size_bytes=_UINT)
_FILE = _record("File", artifact_ref=_TEXT, sha256=_SHA, size_bytes=_UINT, format=_TEXT)
_LOCATION = _record("SourceLocation", file=_FILE, pointer=_POINTER)
_UNIT = _record("Unit", native_text=_nullable(_TEXT), basis=_enum("supplied native_model unknown"), source=_nullable(_LOCATION))
_NUMBER = _record("Number", value=_nullable(_REAL), state=_enum("present missing nonfinite invalid"),
    native_token=_nullable(_RAW), float_hex=_nullable(_TEXT),
    precision=_enum("full_native formatted_6dp unknown"), source=_nullable(_LOCATION),
    missing_reason=_nullable(_enum("not_returned not_executed unsupported_api unavailable_source primal_not_established decode_failed")))
_BOUND = _record("Bound", kind=_enum("finite negative_infinity positive_infinity missing invalid"),
    value=_nullable(_REAL), native_token=_nullable(_RAW), float_hex=_nullable(_TEXT), source=_nullable(_LOCATION))
_ISSUE = _record("Issue", code=_ISSUE_CODE,
    stage=_enum("selection load apply solve capture parse calculate project return"), field=_nullable(_TEXT),
    source_row_index=_nullable(_UINT), reaction_position=_nullable(_UINT), metabolite_position=_nullable(_UINT),
    variable_position=_nullable(_UINT), constraint_position=_nullable(_UINT), detail_file=_nullable(_FILE))
_XML_NAME = _record("FBAXmlName", namespace_uri=_nullable(_RAW), local_name={"type": "string", "minLength": 1})
_XML_STEP = _record("FBAXmlPathStep", name=_XML_NAME, sibling_ordinal=_UINT)
_XML_ATTRIBUTE = _record("FBAXmlAttribute", name=_XML_NAME, value=_RAW)
_XML_NAMESPACE = _record("FBAXmlNamespace", prefix=_RAW, uri=_RAW)
_XML_ELEMENT = _record("FBAXmlSourceElement", source_record_index=_UINT,
    path={**_array(_XML_STEP), "minItems": 1}, parent_source_record_index=_nullable(_UINT),
    child_source_record_indices=_array(_UINT), namespace_declarations=_array(_XML_NAMESPACE),
    attributes=_array(_XML_ATTRIBUTE), text=_nullable(_RAW), tail=_nullable(_RAW))
_SOURCE_AUDIT = _record("FBASourceAudit", version=_enum("cobra_fba_source_audit_v1"),
    input_profile=_enum("sbml cobra_json"), original_model=_LOCATION,
    xml_elements=_nullable(_array(_XML_ELEMENT)), issues=_array(_ISSUE))
_ASSOCIATION = _record("Association", database=_nullable(_TEXT), accession=_TEXT, source=_LOCATION)
_COMPARTMENT = _record("Compartment", position=_UINT, id=_TEXT, name=_nullable(_TEXT))
_GENE = _record("Gene", position=_UINT, id=_TEXT, name=_nullable(_TEXT),
    associations=_array(_ASSOCIATION), supplied_target_refs=_array(_TEXT),
    annotation_pointer=_nullable(_POINTER), notes_pointer=_nullable(_POINTER))
_METABOLITE = _record("Metabolite", position=_UINT, id=_TEXT, name=_nullable(_TEXT),
    compartment_position=_nullable(_UINT), formula=_nullable(_TEXT), charge=_NUMBER,
    associations=_array(_ASSOCIATION), annotation_pointer=_nullable(_POINTER), notes_pointer=_nullable(_POINTER))
_REACTION = _record("Reaction", position=_UINT, id=_TEXT, name=_nullable(_TEXT), lower=_BOUND, upper=_BOUND,
    flux_unit=_UNIT, boundary_kind=_enum("exchange demand sink internal unknown"), boundary_source=_nullable(_LOCATION),
    gpr_native=_nullable(_RAW), gene_positions=_array(_UINT), associations=_array(_ASSOCIATION),
    annotation_pointer=_nullable(_POINTER), notes_pointer=_nullable(_POINTER),
    gpr_source_pointer=_nullable(_POINTER), gpr_loaded=_nullable(_RAW))
_STOICH = _record("Stoichiometry", metabolite_position=_UINT, reaction_position=_UINT, coefficient=_NUMBER, coefficient_unit=_UNIT)
_MEDIUM = _record("MediumEntry", reaction_position=_UINT, native_value=_NUMBER,
    native_meaning=_enum("cobra_medium_entry supplied_exchange_bound unknown"), source=_LOCATION)
_CHANGE = _record("ConstraintChange", reaction_id=_TEXT, requested_lower=_BOUND, requested_upper=_BOUND,
    effective_reaction_position=_nullable(_UINT), application=_enum("applied rejected not_attempted unknown"), issue_code=_nullable(_ISSUE_CODE))
_REQUEST = _record("ObjectiveRequest", kind=_enum("model_default single_reaction"), reaction_id=_nullable(_TEXT))
_OPTION_NAMES = ("feasibility_tolerance", "optimality_tolerance", "integrality_tolerance")
_OPTION_APPLICATION = _record("FBASolverOptionApplication", name=_enum(_OPTION_NAMES),
    application=_enum("applied not_requested rejected not_attempted unknown"),
    requested_source=_LOCATION, effective_source=_nullable(_LOCATION), issue_code=_nullable(_ISSUE_CODE))
_REQUEST_APPLICATION = _record("FBARequestApplication", version=_enum("cobra_fba_request_application_v1"),
    selected_request=_LOCATION, constraint_changes=_nullable(_array(_CHANGE)), objective_request=_REQUEST,
    objective_application=_enum("applied model_default rejected not_attempted unknown"),
    objective_requested_source=_LOCATION, objective_effective_source=_nullable(_LOCATION),
    solver_option_applications=_array(_OPTION_APPLICATION), request_realization=_REALIZATION, issues=_array(_ISSUE))
_SOLVER = _record("Solver", interface=_nullable(_TEXT), name=_nullable(_TEXT), version=_nullable(_TEXT),
    cobra_version=_nullable(_TEXT), optlang_version=_nullable(_TEXT), raw_status=_nullable(_RAW), status=_STATUS,
    feasibility_tolerance=_NUMBER, optimality_tolerance=_NUMBER, integrality_tolerance=_NUMBER,
    raw_parameters_file=_nullable(_FILE), diagnostic_file=_nullable(_FILE), alternate_optimum_claim=_MULTIPLICITY,
    alternate_claim_source=_nullable(_LOCATION))
_FLUX = _record("FluxRow", source_row_index=_UINT, reaction_id=_TEXT, reaction_position=_nullable(_UINT),
    reaction_name=_nullable(_TEXT), flux=_NUMBER, csv_lower=_BOUND, csv_upper=_BOUND,
    association=_enum("matched unknown duplicate conflicting"))
_NATIVE = _record("NativeFBAResult", version=_enum("native_fba_result_v1"), solver=_SOLVER, objective=_NUMBER,
    flux_rows=_array(_FLUX), solve_call_count=_nullable(_UINT), constraint_changes=_nullable(_array(_CHANGE)), objective_request=_nullable(_REQUEST),
    objective_application=_enum("applied model_default rejected not_attempted unknown"), request_realization=_REALIZATION,
    execution_outcome=_enum("completed partial failed not_executed unknown"), source_active_count=_nullable(_UINT), source_active_threshold=_NUMBER,
    source_log_file=_nullable(_FILE), issues=_array(_ISSUE))
_VARIABLE = _record("Variable", position=_UINT, native_index=_POS, optlang_position=_UINT,
    id=_TEXT, kind=_enum("continuous integer binary unknown"), native_kind_code=_INT, native_bound_type_code=_INT,
    lower=_BOUND, upper=_BOUND, unit=_UNIT, source=_LOCATION)
_TERM = _record("Term", variable_position=_UINT, coefficient=_NUMBER)
_CONSTRAINT = _record("Constraint", position=_UINT, native_index=_POS, optlang_position=_UINT,
    id=_TEXT, kind=_enum("metabolite_balance additional_linear"), metabolite_position=_nullable(_UINT),
    constant=_NUMBER, terms=_array(_TERM), terms_complete=_BOOL, lower=_BOUND, upper=_BOUND,
    native_bound_type_code=_INT, indicator_variable_position=_nullable(_UINT), active_when=_nullable(_INT),
    expression_kind=_enum("linear quadratic nonlinear unknown"), native_expression_pointer=_POINTER, unit=_UNIT, source=_LOCATION)
_OBJECTIVE = _record("Objective", direction=_enum("min max unknown"), native_direction_code=_nullable(_INT),
    native_constant=_NUMBER, interface_offset=_NUMBER, symbolic_constant=_NUMBER, terms=_array(_TERM), terms_complete=_BOOL,
    expression_kind=_enum("linear quadratic nonlinear unknown"), native_expression_pointer=_POINTER, unit=_UNIT, source=_LOCATION)
_REACTION_VARIABLES = _record("ReactionVariables", reaction_position=_UINT, reaction_id=_TEXT,
    forward_variable_position=_UINT, forward_variable_id=_TEXT, reverse_variable_position=_UINT, reverse_variable_id=_TEXT,
    flux_expression_pointer=_POINTER)
_PROBLEM = _record("ProblemSnapshot", version=_enum("cobra_glpk_problem_snapshot_v1"), phase=_enum("loaded_original effective"),
    variable_count=_UINT, constraint_count=_UINT, variables=_array(_VARIABLE), constraints=_array(_CONSTRAINT), objective=_OBJECTIVE,
    reaction_variables=_array(_REACTION_VARIABLES),
    representation=_enum("complete_continuous_linear complete_mixed_integer_linear partial unsupported"),
    native_optlang_json=_nullable(_JSON_OBJECT), native_glpk_text=_nullable(_RAW), native_lp_text=_nullable(_RAW), issues=_array(_ISSUE))
_optional(_PROBLEM, native_capture_evidence=_nullable(_JSON_OBJECT))
_CONTROLS = _object(**{key: (_REAL if key in {"obj_ll", "obj_ul", "tol_bnd", "tol_dj", "tol_piv"} else _INT)
    for key in "aorn excl it_lim meth msg_lev obj_ll obj_ul out_dly out_frq presolve pricing r_test shift tm_lim tol_bnd tol_dj tol_piv".split()})
_CONFIG = _record("SolverConfiguration", interface=_enum("optlang.glpk_interface"), glpk_version=_TEXT,
    cobra_version=_TEXT, optlang_version=_TEXT, swiglpk_version=_TEXT, model_tolerance=_NUMBER,
    presolve=_enum([False, True, "auto"]), verbosity=_INT, timeout_seconds=_nullable(_UINT),
    feasibility_tolerance=_NUMBER, integrality_tolerance=_NUMBER, optimality_tolerance=_NUMBER,
    simplex_controls=_CONTROLS, integer_controls_pointer=_POINTER)
_PROBLEM_PAYLOAD = _record("EffectiveProblemPayload", version=_enum("cobra_glpk_problem_capture_v1"),
    loaded_original=_nullable(_PROBLEM), effective=_nullable(_PROBLEM), configuration_before_solve=_nullable(_CONFIG), issues=_array(_ISSUE))
_ID_JOIN = _record("SourceIdJoin", kind=_enum("model compartment gene metabolite reaction group"),
    source_record_index=_nullable(_UINT), source_id=_nullable(_TEXT), loaded_id=_nullable(_TEXT), loaded_position=_nullable(_UINT),
    state=_enum("mapped loader_created rejected unmapped"), source=_LOCATION)
_FEATURE = _record("SourceFeature", kind=_enum("sbml_package dynamic_rule event initial_assignment nonconstant_stoichiometry boundary_exchange_creation default_bound missing_objective ignored_json_field id_collision annotation_qualifier_loss"),
    source=_LOCATION, disposition=_enum("preserved transformed unsupported unknown"))
_GROUP = _record("Group", position=_UINT, id=_TEXT, name=_nullable(_TEXT), kind=_enum("classification partonomy collection unknown"),
    members=_array(_object(kind=_enum("gene metabolite reaction"), position=_UINT, id=_TEXT)),
    annotation_pointer=_nullable(_POINTER), notes_pointer=_nullable(_POINTER))
_POPULATION = _object(**{axis: _nullable(_UINT) for axis in ("compartments", "genes", "metabolites", "reactions", "groups")},
    completeness=_enum("complete partial unknown"))
_MODEL = _record("ModelSnapshot", model_id=_nullable(_TEXT), model_name=_nullable(_TEXT),
    compartments=_array(_COMPARTMENT), genes=_array(_GENE), metabolites=_array(_METABOLITE), reactions=_array(_REACTION),
    stoichiometry=_array(_STOICH), groups=_array(_GROUP), annotations=_JSON_OBJECT, notes=_JSON_OBJECT,
    sbml_metadata=_nullable(_JSON_OBJECT), native_cobra_json=_nullable(_JSON_OBJECT), native_sbml_export=_nullable(_RAW),
    medium=_array(_MEDIUM), medium_state=_enum("observed not_retained unavailable"),
    medium_basis=_enum("cobra_exchange_heuristic explicit_source unknown"), population=_POPULATION)
_optional(_MODEL, native_capture_evidence=_nullable(_JSON_OBJECT))
_LOADER = _object(name=_enum("read_sbml_model load_json_model"), cobra_version=_TEXT,
    number_type=_enum("float64"), id_replacement=_enum("cobra_F_REPLACE none"))
_MODEL_PAYLOAD = _record("EffectiveModelPayload", version=_enum("cobra_model_capture_v1"),
    loaded_original=_nullable(_MODEL), effective=_nullable(_MODEL), input_profile=_enum("sbml cobra_json"), loader=_LOADER,
    source_to_loaded_ids=_array(_ID_JOIN), source_feature_audit=_array(_FEATURE), issues=_array(_ISSUE))
_optional(_MODEL_PAYLOAD, source_audit=_nullable(_SOURCE_AUDIT))
_VARIABLE_VALUE = _record("VariableValue", variable_position=_UINT, variable_id=_TEXT, primal=_NUMBER, reduced_cost=_NUMBER)
_CONSTRAINT_VALUE = _record("ConstraintValue", constraint_position=_UINT, constraint_id=_TEXT, activity=_NUMBER, shadow_price=_NUMBER)
_REACTION_VALUE = _record("ReactionValue", reaction_position=_UINT, reaction_id=_TEXT, flux=_NUMBER, reduced_cost=_NUMBER)
_PASS = _record("NativePass", position=_UINT, routine=_enum("glp_simplex glp_intopt"), return_code=_nullable(_INT),
    raw_status_code=_nullable(_INT), primal_status_code=_nullable(_INT), dual_status_code=_nullable(_INT),
    parameters_pointer=_POINTER, exception_pointer=_nullable(_POINTER))
_SOLUTION = _record("SolutionPayload", version=_enum("cobra_glpk_solution_capture_v1"), model_optimize_call_count=_UINT,
    native_passes=_array(_PASS), solution_object_state=_enum("returned not_returned not_executed"),
    optlang_status=_nullable(_RAW), cobra_solution_status=_nullable(_RAW), glpk_status_code=_nullable(_INT),
    glpk_primal_status_code=_nullable(_INT), glpk_dual_status_code=_nullable(_INT),
    point_state=_enum("basic_solution mip_solution not_established"), native_glpk_objective=_NUMBER,
    native_optlang_objective=_NUMBER, native_cobra_objective=_NUMBER, variable_values=_array(_VARIABLE_VALUE),
    constraint_values=_array(_CONSTRAINT_VALUE), reaction_values=_array(_REACTION_VALUE),
    configuration_after_solve=_nullable(_CONFIG), diagnostics_pointer=_POINTER, issues=_array(_ISSUE))
_optional(_SOLUTION, native_capture_evidence=_nullable(_JSON_OBJECT))
_MODELS = _record("ParsedModelSnapshots", loaded_original=_nullable(_MODEL), effective=_nullable(_MODEL), source=_nullable(_FILE),
    input_profile=_enum("sbml cobra_json unknown"), loader=_nullable(_LOADER),
    source_to_loaded_ids=_array(_ID_JOIN), source_feature_audit=_array(_FEATURE), issues=_array(_ISSUE))
_optional(_MODELS, source_audit=_nullable(_SOURCE_AUDIT))
_PROBLEMS = _record("ParsedProblemSnapshots", loaded_original=_nullable(_PROBLEM), effective=_nullable(_PROBLEM),
    source=_nullable(_FILE), configuration_before_solve=_nullable(_CONFIG), issues=_array(_ISSUE))
_NATIVE_SOLUTION = _record("ParsedNativeSolution", native=_nullable(_SOLUTION), source=_nullable(_FILE), issues=_array(_ISSUE))
_PARSED_ROWS = _record("ParsedFluxRows", rows=_array(_FLUX), issues=_array(_ISSUE))
_BUNDLE_FIELDS = dict(models=_MODELS, problems=_PROBLEMS, native_solution=_NATIVE_SOLUTION, native=_NATIVE,
    original_request_file=_nullable(_FILE), native_manifest_file=_nullable(_FILE), retained_files=_array(_FILE), issues=_array(_ISSUE))
_record("ParsedFBABundle", **_BUNDLE_FIELDS)
_record("FluxBalanceSheet", version=_enum("flux_balance_sheet_v1"), operation=_enum("perform_flux_balance_analysis"),
    mode=_enum("steady_state_linear_fba"), **_BUNDLE_FIELDS)
_TOLERANCE = _record("Tolerance", subject_id=_TEXT, value={"type": "number", "minimum": 0}, unit=_UNIT)
_PARAMETERS = _record("FBACalculationParameters", version=_enum("fba_calculation_parameters_v1"),
    reaction_bound_tolerances=_array(_TOLERANCE), constraint_tolerances=_array(_TOLERANCE), active_flux_thresholds=_array(_TOLERANCE),
    objective_absolute_tolerance=_nullable({"type": "number", "minimum": 0}), variable_bound_tolerances=_array(_TOLERANCE),
    reaction_flux_tolerances=_array(_TOLERANCE), constraint_activity_tolerances=_array(_TOLERANCE))
_CELL = _record("Cell", value=_nullable(_REAL), state=_enum("calculated native missing invalid incompatible not_applicable overflow"),
    unit=_UNIT, issue_codes=_array(_ISSUE_CODE))
_BOUND_CELLS = dict(lower_slack=_CELL, upper_slack=_CELL, lower_violation=_CELL, upper_violation=_CELL)
_REACTION_CHECK = _record("ReactionCheck", reaction_position=_UINT, flux=_NUMBER, **_BOUND_CELLS,
    bound_comparison=_COMPARISON, active=_nullable(_BOOL), flux_basis=_enum("native_solution flux_csv unavailable"),
    csv_flux=_NUMBER, csv_minus_flux=_CELL, csv_flux_comparison=_AGREEMENT,
    variable_net_flux=_CELL, native_minus_variable_net_flux=_CELL, variable_net_comparison=_AGREEMENT)
_VARIABLE_CHECK = _record("VariableCheck", variable_position=_UINT, variable_id=_TEXT, primal=_NUMBER,
    **_BOUND_CELLS, bound_comparison=_COMPARISON)
_CONSTRAINT_CHECK = _record("ConstraintCheck", constraint_id=_TEXT, constraint_position=_UINT,
    metabolite_position=_nullable(_UINT), activity=_CELL, equality_residual=_CELL, **_BOUND_CELLS, comparison=_COMPARISON,
    expected_term_count=_nullable(_UINT), available_term_count=_UINT, native_activity=_NUMBER,
    native_minus_calculated_activity=_CELL, native_activity_comparison=_AGREEMENT)
_OBJECTIVE_CHECK = _record("ObjectiveCheck", native_basis_calculated=_CELL, full_calculated=_CELL,
    native_glpk=_NUMBER, native_optlang=_NUMBER, native_cobra=_NUMBER, native_legacy=_NUMBER,
    glpk_minus_calculated=_CELL, optlang_minus_calculated=_CELL, cobra_minus_calculated=_CELL, legacy_minus_calculated=_CELL,
    glpk_comparison=_AGREEMENT, optlang_comparison=_AGREEMENT, cobra_comparison=_AGREEMENT, legacy_comparison=_AGREEMENT)
_record("FluxBalanceCalculations", version=_enum("flux_balance_calculations_v1"), sheet_sha256=_SHA, parameters=_PARAMETERS,
    reaction_checks=_array(_REACTION_CHECK), constraint_checks=_array(_CONSTRAINT_CHECK), variable_checks=_array(_VARIABLE_CHECK),
    objective=_OBJECTIVE_CHECK, expected_reaction_count=_nullable(_UINT), valid_flux_count=_nullable(_UINT), flux_coverage_fraction=_CELL,
    expected_variable_count=_nullable(_UINT), valid_variable_count=_nullable(_UINT), variable_coverage_fraction=_CELL,
    evaluated_variable_bound_count=_UINT, violated_variable_bound_count=_UINT, variable_bound_comparison_unknown_count=_UINT,
    evaluated_constraint_count=_UINT, expected_constraint_count=_nullable(_UINT), violated_constraint_count=_UINT,
    constraint_comparison_unknown_count=_UINT, evaluated_reaction_bound_count=_UINT, violated_reaction_bound_count=_UINT,
    active_count=_nullable(_UINT), active_population_count=_UINT, max_abs_balance_residual=_CELL,
    candidate_feasibility=_enum("passes_recorded_checks fails_recorded_checks partial_checks unknown"), native_solver_status=_STATUS,
    optimum_multiplicity=_MULTIPLICITY, issues=_array(_ISSUE))
_ATTEMPT = _record("FBAAttemptIdentity", run_id=_TEXT, episode_id=_TEXT, resource_id=_TEXT, execution_id=_TEXT,
    attempt_id=_TEXT, operation_key=_TEXT, requested_job_sha256=_SHA, assignment_sha256=_SHA)
_DISTRIBUTION = _record("Distribution", name=_TEXT, version=_TEXT)
_ABS_PATH = {**_TEXT, "pattern": r"^/[^\x00-\x1f\x7f]+$"}
_FILE_PIN = _record("FilePin", path=_ABS_PATH, sha256=_SHA, size_bytes=_UINT)
_SOFTWARE = _record("FBASoftware", version=_enum("fba_software_v1"), python=_FILE_PIN, python_version=_TEXT,
    python_home=_ABS_PATH, module_root=_ABS_PATH, dependency_roots=_array(_ABS_PATH),
    implementation_files=_array(_FILE_PIN), runtime_files=_array(_FILE_PIN), distributions=_array(_DISTRIBUTION),
    solver_interface=_TEXT, solver_runtime_files=_array(_FILE_PIN))
_REQUESTED_CHANGE = _record("RequestedBoundChange", reaction_id=_TEXT, lower=_BOUND, upper=_BOUND)
_OPTIONS = _record("RequestedSolverOptions", feasibility_tolerance=_nullable(_REAL),
    optimality_tolerance=_nullable(_REAL), integrality_tolerance=_nullable(_REAL))
_JOB = _record("FBAJob", version=_enum("native_flux_balance_job_v1"), operation=_enum("perform_flux_balance_analysis"),
    mode=_enum("steady_state_linear_fba"), source_alias=_enum("biomni.tool.systems_biology.perform_flux_balance_analysis"),
    model_input=_object(file=_FILE_PIN, artifact_ref=_nullable(_TEXT), format=_enum("sbml cobra_json"),
        original_loader_selection=_enum("sbml_file json_file repository_identifier"), repository_identifier=_nullable(_TEXT),
        acquisition_receipt_file=_nullable(_FILE)), constraints=_nullable(_array(_REQUESTED_CHANGE)), objective=_REQUEST,
    solver_options=_OPTIONS, software=_SOFTWARE, output_prefix=_TEXT, flux_output_name=_TEXT, source_function_sha256=_SHA)
_REQUESTED_JOB = _record("FBARequestedJob", argv=_array(_TEXT),
    environment={"type": "object", "propertyNames": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
        "additionalProperties": _RAW}, native_flux_balance=_JOB)
_record("SelectedRequestPayload", version=_enum("flux_balance_selected_request_v1"), attempt=_ATTEMPT, requested_job=_REQUESTED_JOB)
_MANIFEST_FILE = _record("ManifestFile", role=_enum("original_model selected_request effective_model effective_problem solution flux_csv native_log"),
    relative_path=_TEXT, format=_TEXT, state=_STATE, identity=_nullable(_IDENTITY))
_MANIFEST = _record("FBANativeManifest", version=_enum("flux_balance_native_manifest_v1"), sealed=_BOOL, attempt=_ATTEMPT,
    software_sha256=_SHA, model_identity=_IDENTITY, actual_distributions=_array(_DISTRIBUTION), actual_solver=_SOLVER,
    source_function_sha256=_SHA, effective_problem_sha256=_nullable(_SHA), files=_array(_MANIFEST_FILE),
    solve_call_count=_UINT, execution_outcome=_OUTCOME, request_realization=_REALIZATION, issues=_array(_ISSUE))
_optional(_MANIFEST, request_application=_nullable(_REQUEST_APPLICATION))
_PAYLOADS = _object(**{role: _object(file=_nullable(_FILE), bytes=_nullable({"type": "bytes"}), state=_STATE)
    for role in _ROLE["enum"]})


def _fail(code, path):
    raise ValueError(f"{code}:{path}")


def _finite_json(value, path, *, bytes_allowed=False):
    if value is None or type(value) in (str, bool):
        return
    if type(value) in (int, float):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            _fail("schema_invalid", path)
    elif type(value) is list:
        for i, item in enumerate(value):
            _finite_json(item, f"{path}/{i}", bytes_allowed=bytes_allowed)
    elif type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail("schema_invalid", path)
            _finite_json(item, path + "/" + key.replace("~", "~0").replace("/", "~1"), bytes_allowed=bytes_allowed)
    elif not (bytes_allowed and type(value) is bytes):
        _fail("schema_invalid", path)


def _shape(value, schema, path):
    if "anyOf" in schema:
        for alternative in schema["anyOf"]:
            try:
                _shape(value, alternative, path)
                return
            except ValueError:
                pass
        _fail("schema_invalid", path)
    if "enum" in schema and not any(type(value) is type(item) and value == item for item in schema["enum"]):
        _fail("schema_invalid", path)
    kind = schema.get("type")
    accepted = {"null": value is None, "string": type(value) is str, "number": type(value) in (int, float),
        "integer": type(value) is int, "boolean": type(value) is bool, "array": type(value) is list,
        "object": type(value) is dict, "bytes": type(value) is bytes}
    if kind and not accepted[kind]:
        _fail("schema_invalid", path)
    if kind == "string":
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            _fail("schema_invalid", path)
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            _fail("schema_invalid", path)
    if kind in ("integer", "number") and value < schema.get("minimum", value):
        _fail("schema_invalid", path)
    if kind == "array":
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            _fail("schema_invalid", path)
        for index, item in enumerate(value):
            _shape(item, schema["items"], f"{path}/{index}")
    if kind == "object" and "properties" in schema:
        if not set(schema["required"]) <= set(value) or not set(value) <= set(schema["properties"]):
            _fail("schema_invalid", path)
        for key, item in value.items():
            _shape(item, schema["properties"][key], path + "/" + key)
    elif kind == "object" and isinstance(schema.get("additionalProperties"), dict):
        for key, item in value.items():
            if "propertyNames" in schema:
                _shape(key, schema["propertyNames"], path + "/" + key)
            _shape(item, schema["additionalProperties"], path + "/" + key)
    if "x-fba-record" in schema:
        _relationships(schema["x-fba-record"], value, path)


def _unique(rows, key, code, path):
    seen = set()
    for index, row in enumerate(rows):
        item = row[key]
        if item in seen:
            _fail(code, f"{path}/{index}/{key}")
        seen.add(item)


def _population(rows, count, complete, code, path):
    _unique(rows, "position", code, path)
    _unique(rows, "id", code, path)
    positions = [row["position"] for row in rows]
    if count is not None and any(position >= count for position in positions):
        _fail(code, path)
    if positions != sorted(positions):
        _fail(code, path)
    if complete and (count is None or positions != list(range(count))):
        _fail("partial_population", path)


def _join(rows, position, identifier, partial, code, path, count=None):
    found = next((row for row in rows if row["position"] == position), None)
    if found is None:
        if identifier is not None and any(row["id"] == identifier for row in rows):
            _fail(code, path)
        if not partial or (count is not None and position >= count):
            _fail(code, path)
    elif identifier is not None and found["id"] != identifier:
        _fail(code, path)


def _bounds(value, path):
    lower, upper = value["lower"], value["upper"]
    if lower["kind"] == "positive_infinity" or upper["kind"] == "negative_infinity":
        _fail("bound_invalid", path)
    if lower["kind"] == upper["kind"] == "finite" and lower["value"] > upper["value"]:
        _fail("bound_invalid", path)


_XML_URI = "http://www.w3.org/XML/1998/namespace"
_XMLNS_URI = "http://www.w3.org/2000/xmlns/"
# XML expanded local names and declaration prefixes are NCNames, not XPath or
# QName spellings. Keep the full XML name character ranges, including Unicode.
_XML_START = ("A-Z_a-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u02ff\u0370-\u037d"
    "\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff"
    "\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000effff")
_XML_NCNAME = re.compile(f"[{_XML_START}][{_XML_START}0-9.\\-\u00b7\u0300-\u036f\u203f-\u2040]*")


def _expanded_name(name):
    return name["namespace_uri"], name["local_name"]


def _xml_element_relationships(value, path):
    index, parent = value["source_record_index"], value["parent_source_record_index"]
    steps = value["path"]
    if index == 0:
        if parent is not None or len(steps) != 1 or steps[0]["sibling_ordinal"] != 0:
            _fail("model_identity_conflict", path + "/path")
    elif parent is None or parent >= index or len(steps) < 2 or steps[0]["sibling_ordinal"] != 0:
        _fail("model_identity_conflict", path + "/parent_source_record_index")
    children = value["child_source_record_indices"]
    if children != sorted(set(children)) or any(child <= index for child in children):
        _fail("model_identity_conflict", path + "/child_source_record_indices")
    _unique(value["namespace_declarations"], "prefix", "schema_invalid", path + "/namespace_declarations")
    names = [_expanded_name(attribute["name"]) for attribute in value["attributes"]]
    if len(set(names)) != len(names):
        _fail("schema_invalid", path + "/attributes")


def _source_audit_relationships(value, path):
    source = value["original_model"]
    if source["pointer"] != "" or source["file"]["format"] != value["input_profile"]:
        _fail("model_identity_conflict", path + "/original_model")
    elements = value["xml_elements"]
    if value["input_profile"] == "cobra_json":
        if elements is not None:
            _fail("model_identity_conflict", path + "/xml_elements")
        return
    if not elements:
        _fail("model_identity_conflict", path + "/xml_elements")
    contexts = []
    for index, element in enumerate(elements):
        where = f"{path}/xml_elements/{index}"
        if element["source_record_index"] != index:
            _fail("model_identity_conflict", where + "/source_record_index")
        parent = element["parent_source_record_index"]
        if parent is not None:
            if (element["path"][:-1] != elements[parent]["path"]
                    or index not in elements[parent]["child_source_record_indices"]):
                _fail("model_identity_conflict", where + "/path")
        ordinals = {}
        for child in element["child_source_record_indices"]:
            if child >= len(elements) or elements[child]["parent_source_record_index"] != index:
                _fail("model_identity_conflict", where + "/child_source_record_indices")
            step = elements[child]["path"][-1]
            name = _expanded_name(step["name"])
            ordinal = ordinals.get(name, 0)
            if step["sibling_ordinal"] != ordinal:
                _fail("model_identity_conflict", f"{path}/xml_elements/{child}/path")
            ordinals[name] = ordinal + 1
        context = dict(contexts[parent]) if parent is not None else {"xml": _XML_URI}
        for declaration in element["namespace_declarations"]:
            if declaration["uri"]:
                context[declaration["prefix"]] = declaration["uri"]
            else:
                context.pop(declaration["prefix"], None)
        contexts.append(context)
        namespace = element["path"][-1]["name"]["namespace_uri"]
        if ((namespace is None and context.get("") is not None)
                or (namespace is not None and namespace not in context.values())):
            _fail("model_identity_conflict", where + "/path")
        for attribute_index, attribute in enumerate(element["attributes"]):
            namespace = attribute["name"]["namespace_uri"]
            if namespace is not None and not any(prefix and uri == namespace for prefix, uri in context.items()):
                _fail("model_identity_conflict", f"{where}/attributes/{attribute_index}/name")
    # Parent/child agreement alone also permits breadth-first numbering. The
    # source array must retain document preorder, including every descendant.
    stack, expected = [0], 0
    while stack:
        index = stack.pop()
        if index != expected:
            _fail("model_identity_conflict", path + "/xml_elements")
        expected += 1
        stack.extend(reversed(elements[index]["child_source_record_indices"]))
    if expected != len(elements):
        _fail("model_identity_conflict", path + "/xml_elements")


def _application_source(location, format_name, pointer, path, *, file=None):
    if location["pointer"] != pointer or location["file"]["format"] != format_name:
        _fail("request_effective_mismatch", path)
    if file is not None and location["file"] != file:
        _fail("artifact_identity_conflict", path + "/file")


def _option_application_relationships(value, path):
    name, application = value["name"], value["application"]
    _application_source(value["requested_source"], "flux_balance_selected_request_v1",
        "/requested_job/native_flux_balance/solver_options/" + name, path + "/requested_source")
    effective = value["effective_source"]
    if effective is not None:
        _application_source(effective, "cobra_glpk_problem_capture_v1",
            "/configuration_before_solve/" + name, path + "/effective_source")
    if application == "applied" and (effective is None or name == "optimality_tolerance"):
        _fail("request_effective_mismatch", path + "/application")
    if application == "rejected" and (value["issue_code"] is None or
            (name == "optimality_tolerance" and value["issue_code"] != "solver_option_unsupported")):
        _fail("request_effective_mismatch", path + "/issue_code")


def _application_states(value):
    return [value["objective_application"],
        *(row["application"] for row in value["constraint_changes"] or []),
        *(row["application"] for row in value["solver_option_applications"])]


def _request_application_relationships(value, path):
    selected = value["selected_request"]
    _application_source(selected, "flux_balance_selected_request_v1", "/requested_job", path + "/selected_request")
    _application_source(value["objective_requested_source"], "flux_balance_selected_request_v1",
        "/requested_job/native_flux_balance/objective", path + "/objective_requested_source", file=selected["file"])
    effective = value["objective_effective_source"]
    if effective is not None:
        _application_source(effective, "cobra_glpk_problem_capture_v1", "/effective/objective", path + "/objective_effective_source")
    objective = value["objective_application"]
    if objective in {"applied", "model_default"} and (effective is None or
            (objective == "model_default") != (value["objective_request"]["kind"] == "model_default")):
        _fail("request_effective_mismatch", path + "/objective_application")
    rows = value["solver_option_applications"]
    if [row["name"] for row in rows] != list(_OPTION_NAMES):
        _fail("request_effective_mismatch", path + "/solver_option_applications")
    effective_file = effective["file"] if effective else None
    for index, row in enumerate(rows):
        where = f"{path}/solver_option_applications/{index}"
        if row["requested_source"]["file"] != selected["file"]:
            _fail("artifact_identity_conflict", where + "/requested_source/file")
        if row["effective_source"] is not None:
            if effective_file is not None and row["effective_source"]["file"] != effective_file:
                _fail("artifact_identity_conflict", where + "/effective_source/file")
            effective_file = row["effective_source"]["file"]
    changes = value["constraint_changes"]
    if changes is not None:
        _unique(changes, "reaction_id", "duplicate_reaction_id", path + "/constraint_changes")
        _unique([row for row in changes if row["effective_reaction_position"] is not None],
            "effective_reaction_position", "model_identity_conflict", path + "/constraint_changes")
        for index, change in enumerate(changes):
            where = f"{path}/constraint_changes/{index}"
            for side in ("lower", "upper"):
                source = change["requested_" + side]["source"]
                if source is None:
                    _fail("request_effective_mismatch", where + "/requested_" + side + "/source")
                _application_source(source, "flux_balance_selected_request_v1",
                    f"/requested_job/native_flux_balance/constraints/{index}/{side}",
                    where + "/requested_" + side + "/source", file=selected["file"])
            if change["application"] == "applied":
                if (change["effective_reaction_position"] is None or
                        change["requested_lower"]["kind"] not in {"finite", "negative_infinity"} or
                        change["requested_upper"]["kind"] not in {"finite", "positive_infinity"}):
                    _fail("request_effective_mismatch", where + "/application")
                _bounds({"lower": change["requested_lower"], "upper": change["requested_upper"]}, where)
            if change["application"] == "rejected" and change["issue_code"] is None:
                _fail("request_effective_mismatch", where + "/issue_code")
    states = _application_states(value)
    contradictory = "rejected" in states or any(issue["code"] == "request_effective_mismatch" for issue in value["issues"])
    contradictory |= any(row["issue_code"] == "request_effective_mismatch" for row in [*rows, *(changes or [])])
    realization = value["request_realization"]
    if (realization == "exact" and (changes is None or contradictory or
            any(state not in {"applied", "model_default", "not_requested"} for state in states))):
        _fail("request_effective_mismatch", path + "/request_realization")
    if (realization == "mismatch" and not contradictory) or (contradictory and realization != "mismatch"):
        _fail("request_effective_mismatch", path + "/request_realization")


def _manifest_application_relationships(value, path):
    application = value["request_application"]
    if value["request_realization"] != application["request_realization"]:
        _fail("request_effective_mismatch", path + "/request_realization")
    if value["solve_call_count"] and any(state in {"rejected", "not_attempted"} for state in _application_states(application)):
        _fail("request_effective_mismatch", path + "/solve_call_count")
    files = {row["role"]: row for row in value["files"]}
    locations = [("selected_request", application["selected_request"])]
    if application["objective_effective_source"] is not None:
        locations.append(("effective_problem", application["objective_effective_source"]))
    locations.extend(("effective_problem", row["effective_source"])
        for row in application["solver_option_applications"] if row["effective_source"] is not None)
    for role, location in locations:
        row, file = files[role], location["file"]
        if (row["state"] not in {"present", "truncated"} or row["format"] != file["format"]
                or row["identity"] != {key: file[key] for key in ("sha256", "size_bytes")}):
            _fail("artifact_identity_conflict", path + "/request_application/" + role)


def _relationships(kind, value, path):
    if kind in {"Number", "Bound"}:
        state = value["state"] if kind == "Number" else value["kind"]
        present = state == ("present" if kind == "Number" else "finite")
        if present != (value["value"] is not None) or (not present and value["float_hex"] is not None):
            _fail("schema_invalid", path + "/value")
        if kind == "Number" and value["source"] is None and (present or value["native_token"] is not None):
            _fail("schema_invalid", path + "/source")
        if value["float_hex"] is not None:
            try:
                encoded = float.fromhex(value["float_hex"])
            except (ValueError, OverflowError):
                _fail("schema_invalid", path + "/float_hex")
            if not math.isfinite(encoded) or encoded != value["value"] or (
                encoded == 0 and math.copysign(1, encoded) != math.copysign(1, value["value"])):
                _fail("schema_invalid", path + "/float_hex")
        if present and value["native_token"] is not None:
            try:
                token = Decimal(value["native_token"]) if type(value["value"]) is int else float(value["native_token"])
                matches = token == value["value"] and (value["value"] != 0 or
                    math.copysign(1, float(token)) == math.copysign(1, value["value"]))
            except (ValueError, OverflowError, InvalidOperation):
                matches = False
            if not matches:
                _fail("schema_invalid", path + "/native_token")
        if kind == "Number":
            if (state == "missing") != (value["missing_reason"] is not None):
                _fail("schema_invalid", path + "/missing_reason")
            if state in {"invalid", "nonfinite"} and value["source"] is None:
                _fail("schema_invalid", path + "/source")
            if state == "nonfinite":
                try:
                    token = float(value["native_token"])
                except (ValueError, TypeError, OverflowError):
                    _fail("schema_invalid", path + "/native_token")
                if math.isfinite(token):
                    _fail("schema_invalid", path + "/native_token")
    elif kind == "Unit":
        if value["basis"] != "unknown" and value["native_text"] is None:
            _fail("unknown_units", path)
    elif kind in {"Reaction", "Variable", "Constraint"}:
        _bounds(value, path)
        if kind in {"Variable", "Constraint"} and value["native_index"] != value["position"] + 1:
            _fail("variable_identity_conflict" if kind == "Variable" else "constraint_identity_conflict", path)
        if kind == "Reaction" and len(set(value["gene_positions"])) != len(value["gene_positions"]):
            _fail("model_identity_conflict", path + "/gene_positions")
        if kind == "Constraint":
            _terms(value, path)
            if value["indicator_variable_position"] is not None and value["active_when"] is None:
                _fail("schema_invalid", path + "/active_when")
    elif kind == "Objective":
        _terms(value, path)
    elif kind == "ObjectiveRequest":
        if (value["kind"] == "single_reaction") != (value["reaction_id"] is not None):
            _fail("schema_invalid", path + "/reaction_id")
    elif kind == "FBAXmlName":
        if not _XML_NCNAME.fullmatch(value["local_name"]) or value["namespace_uri"] == "":
            _fail("schema_invalid", path)
    elif kind == "FBAXmlNamespace":
        if ((value["prefix"] and not _XML_NCNAME.fullmatch(value["prefix"]))
                or value["prefix"] == "xmlns" or value["uri"] == _XMLNS_URI
                or (value["prefix"] == "xml") != (value["uri"] == _XML_URI)):
            _fail("schema_invalid", path)
    elif kind == "FBAXmlAttribute":
        if value["name"]["namespace_uri"] == _XMLNS_URI:
            _fail("schema_invalid", path + "/name")
    elif kind == "FBAXmlSourceElement":
        _xml_element_relationships(value, path)
    elif kind == "FBASourceAudit":
        _source_audit_relationships(value, path)
    elif kind == "FBASolverOptionApplication":
        _option_application_relationships(value, path)
    elif kind == "FBARequestApplication":
        _request_application_relationships(value, path)
    elif kind == "FluxRow":
        if value["association"] == "matched" and value["reaction_position"] is None:
            _fail("flux_identity_conflict", path)
    elif kind == "ModelSnapshot":
        _model_relationships(value, path)
    elif kind == "ProblemSnapshot":
        _problem_relationships(value, path)
    elif kind in {"EffectiveProblemPayload", "ParsedProblemSnapshots"}:
        for phase in ("loaded_original", "effective"):
            if value[phase] is not None and value[phase]["phase"] != phase:
                _fail("model_identity_conflict", path + "/" + phase + "/phase")
    elif kind in {"EffectiveModelPayload", "ParsedModelSnapshots"}:
        _model_capture_relationships(value, path)
    elif kind == "SolutionPayload":
        _unique(value["native_passes"], "position", "schema_invalid", path + "/native_passes")
        if value["point_state"] == "not_established":
            for axis, field in (("variable_values", "primal"), ("reaction_values", "flux"), ("constraint_values", "activity")):
                if any(row[field]["state"] == "present" for row in value[axis]):
                    _fail("primal_not_established", path + "/" + axis)
    elif kind in {"ParsedFBABundle", "FluxBalanceSheet"}:
        _bundle_relationships(value, path)
    elif kind == "FBACalculationParameters":
        for key, rows in value.items():
            if isinstance(rows, list):
                _unique(rows, "subject_id", "missing_parameters", path + "/" + key)
    elif kind == "Cell":
        if (value["state"] in {"calculated", "native"}) != (value["value"] is not None):
            _fail("schema_invalid", path + "/value")
    elif kind == "ConstraintCheck":
        if value["expected_term_count"] is not None and value["available_term_count"] > value["expected_term_count"]:
            _fail("schema_invalid", path + "/available_term_count")
    elif kind == "ManifestFile":
        if value["state"] in {"present", "truncated"} and value["identity"] is None:
            _fail("artifact_identity_conflict", path)
        _relative_path(value["relative_path"], path + "/relative_path")
    elif kind == "FBANativeManifest":
        _unique(value["files"], "role", "artifact_identity_conflict", path + "/files")
        _unique(value["files"], "relative_path", "artifact_identity_conflict", path + "/files")
        if set(row["role"] for row in value["files"]) != set(_ROLE["enum"]) - {"manifest"}:
            _fail("artifact_missing", path + "/files")
        if value.get("request_application") is not None:
            _manifest_application_relationships(value, path)
    elif kind == "FBAArtifactPayloads":
        for role, payload in value.items():
            if (payload["file"] is None) != (payload["bytes"] is None):
                _fail("artifact_identity_conflict", path + "/" + role)
            if payload["state"] == "present" and payload["file"] is None:
                _fail("artifact_missing", path + "/" + role)
            if payload["state"] == "absent" and payload["file"] is not None:
                _fail("artifact_identity_conflict", path + "/" + role)
    elif kind == "RequestedBoundChange":
        _bounds(value, path)
    elif kind == "RequestedSolverOptions":
        if any(item is not None and item < 0 for item in value.values()):
            _fail("solver_option_unsupported", path)
    elif kind == "FBAJob":
        _relative_path(value["output_prefix"], path + "/output_prefix")
        _relative_path(value["flux_output_name"], path + "/flux_output_name")
        selected = value["model_input"]
        if selected["original_loader_selection"] == "repository_identifier":
            if selected["repository_identifier"] is None or selected["acquisition_receipt_file"] is None:
                _fail("input_missing", path + "/model_input")
        elif (selected["original_loader_selection"] == "sbml_file") != (selected["format"] == "sbml"):
            _fail("unsupported_model_format", path + "/model_input")
        if value["constraints"] is not None:
            _unique(value["constraints"], "reaction_id", "duplicate_reaction_id", path + "/constraints")


def _relative_path(value, path):
    if value.startswith("/") or "\\" in value or any(part in {"", ".", ".."} for part in value.split("/")):
        _fail("artifact_identity_conflict", path)


def _terms(value, path):
    _unique(value["terms"], "variable_position", "variable_identity_conflict", path + "/terms")


def _model_relationships(value, path):
    population = value["population"]
    partial = population["completeness"] != "complete"
    for axis in ("compartments", "genes", "metabolites", "reactions", "groups"):
        _population(value[axis], population[axis], not partial,
            "duplicate_reaction_id" if axis == "reactions" else "model_identity_conflict", path + "/" + axis)
    def join(axis, position, identifier=None):
        _join(value[axis], position, identifier, partial, "model_identity_conflict", path + "/" + axis, population[axis])
    for metabolite in value["metabolites"]:
        if metabolite["compartment_position"] is not None:
            join("compartments", metabolite["compartment_position"])
    for reaction in value["reactions"]:
        for position in reaction["gene_positions"]:
            join("genes", position)
    stoichiometry_pairs = set()
    for row in value["stoichiometry"]:
        pair = row["metabolite_position"], row["reaction_position"]
        if pair in stoichiometry_pairs:
            _fail("model_identity_conflict", path + "/stoichiometry")
        stoichiometry_pairs.add(pair)
        join("metabolites", pair[0]); join("reactions", pair[1])
    for row in value["medium"]:
        join("reactions", row["reaction_position"])
    for group in value["groups"]:
        for member in group["members"]:
            join(member["kind"] + "s", member["position"], member["id"])


def _problem_relationships(value, path):
    complete = value["representation"].startswith("complete_")
    for axis, code in (("variables", "duplicate_variable_id"), ("constraints", "duplicate_constraint_id")):
        _population(value[axis], value[axis[:-1] + "_count"], complete, code, path + "/" + axis)
        _unique(value[axis], "optlang_position", code, path + "/" + axis)
    def variable(position, identifier=None):
        _join(value["variables"], position, identifier, not complete, "variable_identity_conflict", path, value["variable_count"])
    for expression in [*value["constraints"], value["objective"]]:
        for term in expression["terms"]:
            variable(term["variable_position"])
        if complete and not expression["terms_complete"]:
            _fail("term_population_incomplete", path)
        if complete and expression["expression_kind"] != "linear":
            _fail("unsupported_problem_form", path)
    if value["representation"] == "complete_continuous_linear" and any(row["kind"] != "continuous" for row in value["variables"]):
        _fail("unsupported_problem_form", path + "/variables")
    _unique(value["reaction_variables"], "reaction_position", "flux_identity_conflict", path + "/reaction_variables")
    _unique(value["reaction_variables"], "reaction_id", "flux_identity_conflict", path + "/reaction_variables")
    for row in value["reaction_variables"]:
        variable(row["forward_variable_position"], row["forward_variable_id"])
        variable(row["reverse_variable_position"], row["reverse_variable_id"])
        if row["forward_variable_position"] == row["reverse_variable_position"]:
            _fail("flux_identity_conflict", path + "/reaction_variables")
    for row in value["constraints"]:
        if row["indicator_variable_position"] is not None:
            variable(row["indicator_variable_position"])
            if complete:
                _fail("unsupported_problem_form", path + "/constraints")


def _model_capture_relationships(value, path):
    audit = value.get("source_audit")
    if audit is not None and audit["input_profile"] != value["input_profile"]:
        _fail("model_identity_conflict", path + "/source_audit/input_profile")
    loader = value["loader"]
    if loader is not None:
        expected = {"sbml": ("read_sbml_model", "cobra_F_REPLACE"), "cobra_json": ("load_json_model", "none")}.get(value["input_profile"])
        if expected != (loader["name"], loader["id_replacement"]):
            _fail("model_identity_conflict", path + "/loader")
    model = value["loaded_original"]
    if model is None:
        return
    for row in value["source_to_loaded_ids"]:
        if row["loaded_position"] is None:
            continue
        if row["kind"] == "model":
            if row["loaded_id"] != model["model_id"]:
                _fail("model_identity_conflict", path + "/source_to_loaded_ids")
        else:
            axis = row["kind"] + "s"
            _join(model[axis], row["loaded_position"], row["loaded_id"], model["population"]["completeness"] != "complete",
                "model_identity_conflict", path + "/source_to_loaded_ids", model["population"][axis])


def _bundle_relationships(value, path):
    models, problems = value["models"], value["problems"]
    for phase in ("loaded_original", "effective"):
        model, problem = models[phase], problems[phase]
        if model is not None and problem is not None:
            partial = model["population"]["completeness"] != "complete"
            for row in problem["reaction_variables"]:
                _join(model["reactions"], row["reaction_position"], row["reaction_id"], partial,
                    "flux_identity_conflict", path + "/problems/" + phase, model["population"]["reactions"])
            for row in problem["constraints"]:
                if row["metabolite_position"] is not None:
                    _join(model["metabolites"], row["metabolite_position"], None, partial,
                        "constraint_identity_conflict", path + "/problems/" + phase, model["population"]["metabolites"])
    model, problem = models["effective"], problems["effective"]
    solution = value["native_solution"]["native"]
    if solution is not None and problem is not None:
        for axis, entity, key, code in (("variable_values", "variables", "variable", "variable_identity_conflict"),
                ("constraint_values", "constraints", "constraint", "constraint_identity_conflict")):
            for row in solution[axis]:
                _join(problem[entity], row[key + "_position"], row[key + "_id"], not problem["representation"].startswith("complete_"),
                    code, path + "/native_solution/" + axis, problem[key + "_count"])
    if model is not None:
        partial = model["population"]["completeness"] != "complete"
        rows = list(value["native"]["flux_rows"])
        if solution:
            rows += solution["reaction_values"]
        for row in rows:
            if row["reaction_position"] is not None:
                _join(model["reactions"], row["reaction_position"], row["reaction_id"], partial,
                    "flux_identity_conflict", path + "/native/reaction_values", model["population"]["reactions"])
    files = {row["artifact_ref"]: row for row in value["retained_files"]}
    if len(files) != len(value["retained_files"]):
        _fail("artifact_identity_conflict", path + "/retained_files")
    def visit(item, current):
        if isinstance(item, dict):
            if set(item) == set(_FILE["properties"]):
                if files.get(item["artifact_ref"]) != item:
                    _fail("artifact_identity_conflict", current)
            else:
                for key, child in item.items():
                    # Raw native evidence may coincidentally resemble a File.
                    if key not in {"annotations", "notes", "sbml_metadata", "native_cobra_json", "native_optlang_json", "native_capture_evidence"}:
                        visit(child, current + "/" + key)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{current}/{index}")
    visit(value, path)


def normalize_fba_solver_status(raw: str | None) -> str:
    """Normalize the retained status with the existing case-sensitive mapping."""
    if raw is not None and type(raw) is not str:
        _fail("schema_invalid", "/raw_status")
    return {"optimal": "optimal", "feasible": "feasible", "infeasible": "infeasible",
        "unbounded": "unbounded", "infeasible_or_unbounded": "infeasible_or_unbounded",
        "time_limit": "time_limit", "iteration_limit": "iteration_limit",
        "numeric": "numerical_failure"}.get(raw, "unknown")


def flux_balance_schema(kind: str) -> dict:
    """Return a detached, self-contained schema for the named frozen record."""
    if kind == "FBAArtifactPayloads":
        raise ValueError("unsupported_host_schema:/kind")
    if type(kind) is not str or kind not in _S:
        _fail("schema_invalid", "/kind")
    return deepcopy(_S[kind])


def validate_flux_balance_record(kind: str, value: dict) -> dict:
    """Validate shape and available joins; errors start with a stable IssueCode.

    Complete model/problem populations require contiguous original positions.
    Explicit partial populations may retain gaps. Invalid numerical source states
    are records, not malformed JSON; they are retained for the calculator.
    """
    schema = flux_balance_schema(kind)
    _finite_json(value, "")
    _shape(value, schema, "")
    return deepcopy(value)


def validate_fba_artifact_payloads(payloads: dict) -> dict:
    """Validate the eight-role Python call boundary, retaining immutable bytes.

    This is deliberately separate from the finite JSON record/schema API. Byte
    identity comparison before decoding belongs to the source reader.
    """
    _finite_json(payloads, "", bytes_allowed=True)
    _shape(payloads, _PAYLOADS, "")
    _relationships("FBAArtifactPayloads", payloads, "")
    return deepcopy(payloads)
