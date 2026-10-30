"""Closed, source-free FBA presentation records built from the shared schemas.

These are selected result shapes, not a second numerical sheet. No calculation,
artifact access or scientific interpretation takes place here.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import math
import re

from .flux_balance_contracts import flux_balance_schema

__all__ = ["fba_result_schema", "validate_fba_projection_selector",
           "validate_fba_projection", "validate_fba_saved_sheet_reference"]


def _obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def _arr(item):
    return {"type": "array", "items": item}


def _null(item):
    return {"anyOf": [item, {"type": "null"}]}


def _enum(values):
    return {"enum": values.split() if isinstance(values, str) else list(values)}


def _shared(kind):
    """Reduce only declared provenance fields; scalar definitions stay shared."""
    def reduce(node):
        if isinstance(node, list):
            return [reduce(v) for v in node]
        if not isinstance(node, dict):
            return node
        record = node.get("x-fba-record")
        removed = {
            "Unit": {"source"}, "Number": {"source"}, "Bound": {"source"},
            "Issue": {"detail_file"}, "Association": {"source"},
            "ReactionVariables": {"flux_expression_pointer"},
        }.get(record, set())
        result = {k: reduce(v) for k, v in node.items() if k != "x-fba-record"}
        if removed:
            result["properties"] = {k: v for k, v in result["properties"].items() if k not in removed}
            result["required"] = [k for k in result["required"] if k not in removed]
        if record in {"Unit", "Number", "Bound", "Cell"}:
            result["x-fba-result-record"] = record
        return result
    return reduce(flux_balance_schema(kind))


def _props(kind, *keys):
    source = _shared(kind)["properties"]
    return {k: source[k] for k in keys}


UINT = {"type": "integer", "minimum": 0}
BOOL = {"type": "boolean"}
NULL = {"type": "null"}
TEXT = _shared("Reaction")["properties"]["id"]
UNIT, NUMBER, BOUND, CELL, TOLERANCE, ISSUE = [_shared(k) for k in ("Unit", "Number", "Bound", "Cell", "Tolerance", "Issue")]
QUALIFICATION = _obj(scope=_enum("bundle selected_entity selected_csv_row"), issue=ISSUE)
SAVED = _shared("File")
SAVED["properties"]["artifact_ref"] = {"type": "string", "pattern": "^artifact_[0-9a-f]{64}$"}
SAVED["properties"]["format"] = {"const": "flux_balance_sheet_v1"}
SIDES = _props("VariableCheck", "lower_slack", "upper_slack", "lower_violation", "upper_violation")
MAPPING = _shared("ReactionVariables")
POINT = _null(_shared("SolutionPayload")["properties"]["point_state"])
ASSOCIATIONS = _arr(_shared("Association"))
OBJECTIVE_DEFINITION = _obj(**_props("Objective", "direction", "native_constant", "interface_offset",
    "symbolic_constant", "terms_complete", "expression_kind", "unit"))

RUN_FIELDS = {
    "native_run": _obj(**_props("NativeFBAResult", "execution_outcome", "solve_call_count"),
        solver_status=_shared("FluxBalanceCalculations")["properties"]["native_solver_status"],
        raw_solver_status=_shared("Solver")["properties"]["raw_status"],
        **{k: _null(v) for k, v in _props("SolutionPayload", "point_state", "solution_object_state",
            "model_optimize_call_count", "optlang_status", "cobra_solution_status", "glpk_status_code",
            "glpk_primal_status_code", "glpk_dual_status_code").items()}),
    "request": _obj(**_props("NativeFBAResult", "objective_request", "objective_application", "request_realization", "constraint_changes")),
    "objective": _obj(check=_shared("ObjectiveCheck"), definition=_null(OBJECTIVE_DEFINITION),
        absolute_tolerance=_shared("FBACalculationParameters")["properties"]["objective_absolute_tolerance"]),
    "original_objective_definition": _null(OBJECTIVE_DEFINITION),
    "reaction_population": _obj(**_props("FluxBalanceCalculations", "expected_reaction_count", "valid_flux_count", "flux_coverage_fraction")),
    "variable_population": _obj(**_props("FluxBalanceCalculations", "expected_variable_count", "valid_variable_count", "variable_coverage_fraction")),
    "constraint_population": _obj(**_props("FluxBalanceCalculations", "expected_constraint_count", "evaluated_constraint_count", "violated_constraint_count", "constraint_comparison_unknown_count")),
    "reaction_bound_counts": _obj(**_props("FluxBalanceCalculations", "evaluated_reaction_bound_count", "violated_reaction_bound_count", "expected_reaction_count")),
    "variable_bound_counts": _obj(**_props("FluxBalanceCalculations", "evaluated_variable_bound_count", "violated_variable_bound_count", "variable_bound_comparison_unknown_count", "expected_variable_count")),
    "active_population": _obj(**_props("FluxBalanceCalculations", "active_count", "active_population_count", "expected_reaction_count"), thresholds=_arr(TOLERANCE)),
    "balance_residual": _obj(**_props("FluxBalanceCalculations", "max_abs_balance_residual", "expected_constraint_count"),
        representation=_null(_shared("ProblemSnapshot")["properties"]["representation"])),
    "candidate_feasibility": _obj(**_props("FluxBalanceCalculations", "candidate_feasibility"),
        model_completeness=_null(_shared("ModelSnapshot")["properties"]["population"]["properties"]["completeness"]),
        problem_representation=_null(_shared("ProblemSnapshot")["properties"]["representation"]), point_state=POINT),
    "optimum_multiplicity": _obj(**_props("FluxBalanceCalculations", "optimum_multiplicity")),
}
_FLUX = _props("ReactionCheck", "flux", "flux_basis")
_BOUNDS = _props("Reaction", "lower", "upper")
_COUNTS = _props("ConstraintCheck", "expected_term_count", "available_term_count")
_REACTION_COMMON = {
    "name": _shared("Reaction")["properties"]["name"],
    "bounds": _obj(**_BOUNDS, unit=UNIT),
    "boundary_kind": _shared("Reaction")["properties"]["boundary_kind"],
    "associations": ASSOCIATIONS,
    "gpr": _obj(**_props("Reaction", "gpr_native", "gpr_loaded", "gene_positions"), source_gpr_retained=BOOL),
    "genes": _arr(_obj(gene_position=UINT, availability=_enum("present unavailable"),
        id=_null(TEXT), name=_shared("Gene")["properties"]["name"], associations=_null(ASSOCIATIONS))),
    "solver_variables": _null(MAPPING),
}
_REACTION_EFFECTIVE = {
    "flux": _obj(**_FLUX, unit=UNIT),
    "bound_check": _obj(**_FLUX, **_BOUNDS, unit=UNIT, **SIDES,
        **_props("ReactionCheck", "bound_comparison"), tolerance=_null(TOLERANCE)),
    "active": _obj(**_FLUX, unit=UNIT, **_props("ReactionCheck", "active"), threshold=_null(TOLERANCE)),
    "csv_comparison": _obj(**_FLUX, **_props("ReactionCheck", "csv_flux", "csv_minus_flux", "csv_flux_comparison"),
        unit=UNIT, tolerance=_null(TOLERANCE)),
    "variable_net_comparison": _obj(**_FLUX, **_props("ReactionCheck", "variable_net_flux", "native_minus_variable_net_flux", "variable_net_comparison"),
        unit=UNIT, tolerance=_null(TOLERANCE), solver_variables=_null(MAPPING)),
    "native_values": _obj(point_state=POINT, selected_flux=NUMBER, flux_basis=_FLUX["flux_basis"], flux_unit=UNIT,
        reduced_cost_unit=NULL, rows=_arr(_shared("ReactionValue"))),
}
_CONSTRAINT_COMMON = {
    "definition": _obj(**_props("Constraint", "kind", "metabolite_position", "constant", "terms_complete",
        "lower", "upper", "expression_kind", "indicator_variable_position", "active_when", "unit")),
    "terms": _arr(_obj(**_props("Term", "variable_position", "coefficient"), variable_id=_null(TEXT))),
    "metabolite": _null(_obj(metabolite_position=UINT, availability=_enum("present unavailable"), id=_null(TEXT),
        name=_shared("Metabolite")["properties"]["name"], compartment_position=_null(UINT))),
}
_CONSTRAINT_EFFECTIVE = {
    "activity": _obj(**_props("ConstraintCheck", "activity"), **_props("Constraint", "constant", "expression_kind", "terms_complete"), **_COUNTS),
    "equality_residual": _obj(**_props("ConstraintCheck", "activity", "equality_residual"), **_BOUNDS, **_COUNTS),
    "bound_check": _obj(**_props("ConstraintCheck", "activity", "comparison"), **_BOUNDS, **SIDES, **_COUNTS, tolerance=_null(TOLERANCE)),
    "native_activity_comparison": _obj(**_props("ConstraintCheck", "native_activity", "activity", "native_minus_calculated_activity", "native_activity_comparison"),
        unit=UNIT, **_COUNTS, tolerance=_null(TOLERANCE)),
    "native_values": _obj(point_state=POINT, selected_native_activity=NUMBER, activity_unit=UNIT,
        shadow_price_unit=NULL, rows=_arr(_shared("ConstraintValue"))),
}
_VARIABLE_COMMON = {"definition": _obj(**_props("Variable", "kind", "native_index", "optlang_position",
    "native_kind_code", "native_bound_type_code", "lower", "upper", "unit"))}
_VARIABLE_EFFECTIVE = {
    "primal": _obj(primal=NUMBER, unit=UNIT, point_state=POINT),
    "bound_check": _obj(primal=NUMBER, **_BOUNDS, unit=UNIT, **SIDES,
        **_props("VariableCheck", "bound_comparison"), tolerance=_null(TOLERANCE)),
    "native_values": _obj(point_state=POINT, selected_primal=NUMBER, primal_unit=UNIT,
        reduced_cost_unit=NULL, rows=_arr(_shared("VariableValue"))),
}
CSV_FIELDS = {
    "name": _shared("FluxRow")["properties"]["reaction_name"],
    "flux": _obj(flux=NUMBER, unit=NULL),
    "bounds": _obj(**_BOUNDS, unit=NULL),
    "model_association": _obj(**_props("FluxRow", "reaction_position", "association")),
}
FIELD_SCHEMAS = {
    "run_diagnostics": RUN_FIELDS, "csv_flux_rows": CSV_FIELDS,
    "reaction_fluxes": {**_REACTION_COMMON, **_REACTION_EFFECTIVE},
    "constraint_residuals": {**_CONSTRAINT_COMMON, **_CONSTRAINT_EFFECTIVE},
    "variable_bounds": {**_VARIABLE_COMMON, **_VARIABLE_EFFECTIVE},
}
ORIGINAL_FIELDS = {"reaction_fluxes": tuple(_REACTION_COMMON), "constraint_residuals": tuple(_CONSTRAINT_COMMON),
                   "variable_bounds": tuple(_VARIABLE_COMMON)}
POSITION_KEYS = {"reaction_fluxes": ("reaction_positions", "reaction_position", "reaction_id", "reactions"),
    "constraint_residuals": ("constraint_positions", "constraint_position", "constraint_id", "constraints"),
    "variable_bounds": ("variable_positions", "variable_position", "variable_id", "variables"),
    "csv_flux_rows": ("source_row_indices", "source_row_index", "reaction_id", "csv_source_rows")}
FILTER_PATHS = {"reaction_fluxes": {"flux": "flux", "variable_net_comparison": "variable_net_flux"},
    "constraint_residuals": {"activity": "activity", "equality_residual": "equality_residual"},
    "variable_bounds": {"primal": "primal"}, "csv_flux_rows": {"flux": "flux"}}


def _selector_schema(view, phase=None):
    fields = ORIGINAL_FIELDS[view] if phase == "loaded_original" else FIELD_SCHEMAS[view]
    result = _obj(version={"const": "flux_balance_projection_selector_v1"}, view={"const": view},
        fields={**_arr(_enum(fields)), "minItems": 1, "uniqueItems": True},
        row_window=_obj(offset=UINT, limit={"type": "integer", "minimum": 1}))
    if view != "run_diagnostics":
        result["properties"][POSITION_KEYS[view][0]] = {**_arr(UINT), "uniqueItems": True}
        result["required"].append(POSITION_KEYS[view][0])
        if phase is not None:
            result["properties"]["snapshot_phase"] = {"const": phase}
            result["required"].append("snapshot_phase")
        if phase != "loaded_original":
            result["properties"]["filter"] = _null(_obj(field=_enum(FILTER_PATHS[view]), minimum={"type": "number"}))
    return result


_VARIANTS = [(view, phase) for view in FIELD_SCHEMAS for phase in
    (("loaded_original", "effective") if view in ORIGINAL_FIELDS else (None,))]
SELECTOR = {"oneOf": [_selector_schema(view, phase) for view, phase in _VARIANTS]}
POPULATION = _obj(axis=_enum("run_fields reactions constraints variables csv_source_rows"),
    snapshot_phase=_null(_enum("loaded_original effective")), expected_count=_null(UINT),
    expected_count_basis=_enum("field_catalog model_population native_problem_count unknown_csv_population snapshot_unavailable"),
    retained_count=UINT, model_completeness=_null(_enum("complete partial unknown")),
    problem_representation=_null(_enum("complete_continuous_linear complete_mixed_integer_linear partial unsupported")))
PAGE = _obj(**{k: UINT for k in ("selected_row_count", "matched_row_count", "filter_unknown_row_count", "filtered_row_count", "row_offset", "returned_row_count")}, has_more=BOOL)


def _projection_schema():
    alternatives = []
    for view, phase in _VARIANTS:
        if view == "run_diagnostics":
            row = {"oneOf": [_obj(field={"const": k}, value=v) for k, v in RUN_FIELDS.items()]}
        else:
            fields = ORIGINAL_FIELDS[view] if phase == "loaded_original" else FIELD_SCHEMAS[view]
            values = _obj(**{k: _null(FIELD_SCHEMAS[view][k]) for k in fields})
            values["required"] = []  # exact keys come from the validated selector
            _, position, identifier, _ = POSITION_KEYS[view]
            row = _obj(**{position: UINT, identifier: _null(TEXT)},
                availability=_enum("present unavailable ambiguous" if view == "csv_flux_rows" else "present unavailable"),
                existence=_enum("present within_known_population unknown"),
                unavailable_reason=_null(_enum("snapshot_unavailable position_not_retained source_row_not_retained source_row_identity_conflict")),
                filter_match=_null(_enum("matches unknown")), values=values)
        alternatives.append(_obj(version={"const": "flux_balance_result_view_v1"}, selector=_selector_schema(view, phase),
            population=POPULATION, page=PAGE, rows=_arr(row), qualification_issues=_arr(QUALIFICATION)))
    return {"oneOf": alternatives}


_SCHEMAS = {"FBAProjectionSelector": SELECTOR, "FBAProjection": _projection_schema(),
    "FBAResultUnit": UNIT, "FBAResultNumber": NUMBER, "FBAResultBound": BOUND,
    "FBAResultCell": CELL, "FBAResultTolerance": TOLERANCE, "FBAResultIssue": ISSUE,
    "FBAResultQualification": QUALIFICATION, "FBASavedSheetReference": SAVED}


def _fail(code, path):
    raise ValueError(code + ":" + (path or "/"))


def _finite(value, code, path=""):
    if value is None or type(value) in (str, bool):
        return
    if type(value) in (int, float):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            _fail(code, path)
    elif type(value) is list:
        for i, row in enumerate(value):
            _finite(row, code, f"{path}/{i}")
    elif type(value) is dict:
        for k, v in value.items():
            if type(k) is not str:
                _fail(code, path)
            _finite(v, code, path + "/" + k.replace("~", "~0").replace("/", "~1"))
    else:
        _fail(code, path)


def _shape(value, schema, code, path=""):
    for union in ("oneOf", "anyOf"):
        if union in schema:
            valid = 0
            for alternative in schema[union]:
                try:
                    _shape(value, alternative, code, path)
                    valid += 1
                except ValueError:
                    pass
            if not valid or (union == "oneOf" and valid != 1):
                _fail(code, path)
            return
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        _fail(code, path)
    if "enum" in schema and not any(type(value) is type(v) and value == v for v in schema["enum"]):
        _fail(code, path)
    kind = schema.get("type")
    if kind and not {"null": value is None, "object": type(value) is dict, "array": type(value) is list,
        "number": type(value) in (int, float), "integer": type(value) is int,
        "string": type(value) is str, "boolean": type(value) is bool}[kind]:
        _fail(code, path)
    if kind == "object":
        if not set(schema["required"]) <= set(value) or not set(value) <= set(schema["properties"]):
            _fail(code, path)
        for k, v in value.items():
            _shape(v, schema["properties"][k], code, path + "/" + k)
    elif kind == "array":
        if len(value) < schema.get("minItems", 0):
            _fail(code, path)
        for i, v in enumerate(value):
            _shape(v, schema["items"], code, f"{path}/{i}")
        if schema.get("uniqueItems") and any(v in value[:i] for i, v in enumerate(value)):
            _fail(code, path)
    elif kind == "string":
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", len(value)):
            _fail(code, path)
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            _fail(code, path)
    elif kind in ("number", "integer") and value < schema.get("minimum", value):
        _fail(code, path)
    record = schema.get("x-fba-result-record")
    if record in {"Number", "Bound"}:
        state = value["state"] if record == "Number" else value["kind"]
        present = state == ("present" if record == "Number" else "finite")
        if present != (value["value"] is not None) or (not present and value["float_hex"] is not None):
            _fail(code, path + "/value")
        if value["float_hex"] is not None:
            try:
                token = float.fromhex(value["float_hex"])
                valid = math.isfinite(token) and token == value["value"] and (token != 0 or
                    math.copysign(1, token) == math.copysign(1, value["value"]))
            except (ValueError, OverflowError):
                valid = False
            if not valid:
                _fail(code, path + "/float_hex")
        if present and value["native_token"] is not None:
            try:
                token = Decimal(value["native_token"]) if type(value["value"]) is int else float(value["native_token"])
                valid = token == value["value"] and (value["value"] != 0 or
                    math.copysign(1, float(token)) == math.copysign(1, value["value"]))
            except (ValueError, OverflowError, InvalidOperation):
                valid = False
            if not valid:
                _fail(code, path + "/native_token")
        if record == "Number":
            if (state == "missing") != (value["missing_reason"] is not None):
                _fail(code, path + "/missing_reason")
            if state == "nonfinite":
                try:
                    valid = not math.isfinite(float(value["native_token"]))
                except (ValueError, OverflowError, TypeError):
                    valid = False
                if not valid:
                    _fail(code, path + "/native_token")
    elif record == "Unit" and value["basis"] != "unknown" and value["native_text"] is None:
        _fail(code, path + "/native_text")
    elif record == "Cell" and ((value["state"] in {"native", "calculated"}) != (value["value"] is not None)):
        _fail(code, path + "/value")


def _checked(value, schema, code):
    _finite(value, code)
    _shape(value, schema, code)
    return deepcopy(value)


def fba_result_schema(kind: str) -> dict:
    """Return a detached closed schema; no sheet/calculation policy is copied."""
    if type(kind) is not str or kind not in _SCHEMAS:
        _fail("fba_projection_shape_invalid", "/kind")
    return deepcopy(_SCHEMAS[kind])


def validate_fba_projection_selector(selector: dict) -> dict:
    code = "fba_projection_selector_invalid"
    _finite(selector, code, "/selector")
    if type(selector) is not dict or type(selector.get("view")) is not str or selector["view"] not in FIELD_SCHEMAS:
        _fail(code, "/selector/view")
    view = selector["view"]
    fields = selector.get("fields")
    allowed = ORIGINAL_FIELDS.get(view, ()) if selector.get("snapshot_phase") == "loaded_original" else FIELD_SCHEMAS[view]
    if type(fields) is not list or not fields or any(type(f) is not str or f not in allowed for f in fields) or len(set(fields)) != len(fields):
        _fail("fba_projection_field_invalid", "/selector/fields")
    if view in POSITION_KEYS:
        key = POSITION_KEYS[view][0]
        positions = selector.get(key)
        if type(positions) is list and all(type(p) is int for p in positions) and len(set(positions)) != len(positions):
            _fail("fba_projection_position_duplicate", "/selector/" + key)
    filtering = selector.get("filter")
    if filtering is not None:
        if (view == "run_diagnostics" or selector.get("snapshot_phase") == "loaded_original"
                or type(filtering) is not dict or set(filtering) != {"field", "minimum"}
                or type(filtering["field"]) is not str or filtering["field"] not in FILTER_PATHS[view]
                or filtering["field"] not in fields or type(filtering["minimum"]) not in (int, float)):
            _fail("fba_projection_filter_invalid", "/selector/filter")
    _shape(selector, SELECTOR, code, "/selector")
    return deepcopy(selector)


def validate_fba_saved_sheet_reference(value: dict) -> dict:
    result = _checked(value, SAVED, "fba_projection_shape_invalid")
    if result["artifact_ref"] != "artifact_" + result["sha256"]:
        _fail("fba_projection_selection_mismatch", "/artifact_ref")
    return result


def validate_fba_projection(projection: dict) -> dict:
    """Validate finite shape, source-free state meanings and selected page joins."""
    result = _checked(projection, _SCHEMAS["FBAProjection"], "fba_projection_shape_invalid")
    selector = validate_fba_projection_selector(result["selector"])
    view, page, pop, rows = selector["view"], result["page"], result["population"], result["rows"]
    code = "fba_projection_selection_mismatch"
    count = len(selector["fields"]) if view == "run_diagnostics" else len(selector[POSITION_KEYS[view][0]])
    expected_returned = min(selector["row_window"]["limit"], max(0, page["filtered_row_count"] - page["row_offset"]))
    if (page["selected_row_count"] != count or page["row_offset"] != selector["row_window"]["offset"]
            or page["returned_row_count"] != len(rows) or len(rows) != expected_returned
            or page["filtered_row_count"] > count
            or page["filtered_row_count"] != page["matched_row_count"] + page["filter_unknown_row_count"]
            or page["has_more"] != (page["row_offset"] + len(rows) < page["filtered_row_count"])):
        _fail(code, "/page")
    filtering = selector.get("filter")
    if filtering is None and (page["matched_row_count"] != count or page["filter_unknown_row_count"] != 0):
        _fail(code, "/page")
    if view == "run_diagnostics":
        if pop != {"axis": "run_fields", "snapshot_phase": None, "expected_count": len(RUN_FIELDS),
                "expected_count_basis": "field_catalog", "retained_count": len(RUN_FIELDS),
                "model_completeness": None, "problem_representation": None}:
            _fail(code, "/population")
        ordered = selector["fields"][page["row_offset"]:page["row_offset"] + len(rows)]
        if [r["field"] for r in rows] != ordered:
            _fail(code, "/rows")
    else:
        selected_key, position_key, id_key, axis = POSITION_KEYS[view]
        phase = selector.get("snapshot_phase")
        if pop["axis"] != axis or pop["snapshot_phase"] != phase:
            _fail(code, "/population")
        if view == "csv_flux_rows":
            if (pop["expected_count"] is not None or pop["expected_count_basis"] != "unknown_csv_population"
                    or pop["model_completeness"] is not None or pop["problem_representation"] is not None):
                _fail(code, "/population")
        elif (pop["expected_count_basis"] not in {"model_population" if view == "reaction_fluxes" else "native_problem_count", "snapshot_unavailable"}
                or (view == "reaction_fluxes" and pop["problem_representation"] is not None)
                or (view != "reaction_fluxes" and pop["model_completeness"] is not None)):
            _fail(code, "/population")
        if pop["expected_count_basis"] == "snapshot_unavailable" and (pop["expected_count"] is not None or pop["retained_count"] != 0):
            _fail(code, "/population")
        order = selector[selected_key]
        returned = [r[position_key] for r in rows]
        if len(set(returned)) != len(returned) or any(p not in order for p in returned) or [order.index(p) for p in returned] != sorted(order.index(p) for p in returned):
            _fail(code, "/rows")
        if filtering is None and returned != order[page["row_offset"]:page["row_offset"] + len(rows)]:
            _fail(code, "/rows")
        if pop["expected_count"] is not None and any(p >= pop["expected_count"] for p in order):
            _fail(code, "/population/expected_count")
        for i, row in enumerate(rows):
            if set(row["values"]) != set(selector["fields"]):
                _fail(code, f"/rows/{i}/values")
            if row["availability"] == "present":
                if row["existence"] != "present" or row["unavailable_reason"] is not None or row[id_key] is None:
                    _fail(code, f"/rows/{i}")
            else:
                if row[id_key] is not None or any(v is not None for v in row["values"].values()):
                    _fail(code, f"/rows/{i}")
                if row["availability"] == "ambiguous":
                    if row["existence"] != "present" or row["unavailable_reason"] != "source_row_identity_conflict":
                        _fail(code, f"/rows/{i}")
                elif (row["existence"] != ("within_known_population" if pop["expected_count"] is not None else "unknown")
                        or row["unavailable_reason"] != ("source_row_not_retained" if view == "csv_flux_rows" else
                            "snapshot_unavailable" if pop["expected_count_basis"] == "snapshot_unavailable" else "position_not_retained")):
                    _fail(code, f"/rows/{i}")
            if filtering is None:
                if row["filter_match"] is not None:
                    _fail(code, f"/rows/{i}/filter_match")
            else:
                group = row["values"][filtering["field"]]
                number = None if group is None else group[FILTER_PATHS[view][filtering["field"]]]
                known = number is not None and number["value"] is not None and number["state"] in {"present", "native", "calculated"}
                if row["filter_match"] != ("matches" if known else "unknown") or (known and number["value"] < filtering["minimum"]):
                    _fail(code, f"/rows/{i}/filter_match")
    return result
