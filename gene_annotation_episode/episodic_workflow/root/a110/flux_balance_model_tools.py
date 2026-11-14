"""Selected, Store-free Cobra model inspection and editing; never optimize.

The host authenticates received Files and optional Source references before
dispatch. These records validate shape and native readback, not that custody or
the biological correctness of a caller's proposed reaction. Full captures stay
private; the projector copies one explicitly selected native collection.
"""
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import re
import sys
import traceback

from .execution_contracts import canonical
from .flux_balance_contracts import (ISSUE_CODES, _bounds as _native_bounds, _join, _terms,
    flux_balance_schema, validate_flux_balance_record)
from .flux_balance_result_contracts import _checked, _props, _shared, fba_result_schema
from .flux_balance_readers import parse_cobra_glpk_model_capture, parse_cobra_glpk_problem_capture
from .native_flux_balance_contracts import validate_flux_balance_software
from .native_flux_balance_storage import directory, immutable_bytes, read_bytes


REQUEST_VERSION = "flux_balance_model_request_v1"
RESULT_VERSION = "ordinary_fba_model_result_v1"
VIEW_VERSION = "flux_balance_model_view_v1"
_TEXT = deepcopy(flux_balance_schema("Reaction")["properties"]["id"])
_UINT = {"type": "integer", "minimum": 0}
_SOURCE = {"type": "string", "pattern": r"source_[a-f0-9]{24,64}"}


def _obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def _arr(item):
    return {"type": "array", "items": item}


def _nullable(item):
    return {"anyOf": [item, {"type": "null"}]}


_REFS = {**_arr(_SOURCE), "uniqueItems": True}
_BOUND = _obj(kind={"enum": ["finite", "negative_infinity", "positive_infinity"]},
    value=_nullable({"type": "number"}))
_MET = _obj(id=_TEXT, name={"type": "string"}, compartment_id=_TEXT,
    formula=_nullable({"type": "string"}), charge=_nullable({"type": "number"}), source_refs=_REFS)
_RXN = _obj(id=_TEXT, name={"type": "string"},
    stoichiometry={**_arr(_obj(metabolite_id=_TEXT, coefficient={"type": "number"})), "minItems": 1},
    lower=_BOUND, upper=_BOUND, source_refs=_REFS)
_CHANGE = _obj(reaction_id=_TEXT, lower=_BOUND, upper=_BOUND, source_refs=_REFS)
_OBJECTIVE = {"oneOf": [_obj(kind={"const": "preserve"}), _obj(kind={"const": "single_reaction"},
    reaction_id=_TEXT, direction={"enum": ["preserve", "min", "max"]}, source_refs=_REFS)]}
_EDITS = _obj(output_format={"enum": ["sbml", "cobra_json"]}, add_metabolites=_arr(_MET),
    add_reactions=_arr(_RXN), bounds=_arr(_CHANGE), objective=_OBJECTIVE)
_FILE = flux_balance_schema("File")
_FILE["properties"]["format"] = {"enum": ["sbml", "cobra_json"]}
_REQUEST = {"oneOf": [_obj(version={"const": REQUEST_VERSION}, mode={"const": mode},
    model_file=_FILE, edits={"type": "null"} if mode == "inspect" else _EDITS)
    for mode in ("inspect", "edit")]}
_COLLECTIONS = ("model", "compartments", "metabolites", "reactions", "genes", "groups", "stoichiometry", "objective")
_SELECTOR = _obj(snapshot_phase={"enum": ["loaded_original", "effective"]}, collection={"enum": list(_COLLECTIONS)},
    ordinals=_nullable(_arr(_UINT)), row_window=_obj(offset=_UINT, limit={"type": "integer", "minimum": 1}))
_DECLARATION = _obj(role={"enum": ["original_model", "effective_model", "effective_problem", "edited_model"]},
    relative_path=_TEXT, file=flux_balance_schema("File"))
_EDIT_RESULT = _obj(collection={"enum": ["add_metabolites", "add_reactions", "bounds", "objective"]}, ordinal=_UINT,
    state={"enum": ["not_attempted", "applied", "rejected", "unknown"]},
    issue_code=_nullable({"enum": sorted(ISSUE_CODES)}))
_RESULT = _obj(version={"const": RESULT_VERSION}, request=_REQUEST, models={}, problems={},
    edit_results=_arr(_EDIT_RESULT), edit_state={"enum": ["not_requested", "exact", "rejected", "partial", "unknown"]},
    edited_model=_nullable(_DECLARATION), files=_arr(_DECLARATION),
    model_optimize_call_count={"const": 0}, issues=_arr({}))


def _view_values_schema(collection):
    if collection == "model":
        return _obj(**_props("ModelSnapshot", "model_id", "model_name", "population", "medium_state", "medium_basis"))
    kind = {"compartments": "Compartment", "metabolites": "Metabolite", "reactions": "Reaction",
        "genes": "Gene", "groups": "Group", "stoichiometry": "Stoichiometry", "objective": "Objective"}[collection]
    schema = _shared(kind)
    omitted = {"source", "annotation_pointer", "notes_pointer", "gpr_source_pointer", "boundary_source",
        "native_expression_pointer", "flux_expression_pointer"}
    schema["properties"] = {key: value for key, value in schema["properties"].items() if key not in omitted}
    schema["required"] = [key for key in schema["required"] if key not in omitted]
    return schema


def _view_schema():
    feature = _shared("SourceFeature")
    feature["properties"].pop("source")
    feature["required"].remove("source")
    alternatives = []
    for collection in _COLLECTIONS:
        selection = deepcopy(_SELECTOR)
        selection["properties"]["collection"] = {"const": collection}
        row = {"oneOf": [_obj(ordinal=_UINT, availability={"const": "present"}, values=_view_values_schema(collection)),
            _obj(ordinal=_UINT, availability={"const": "unavailable"}, values={"type": "null"})]}
        alternatives.append(_obj(version={"const": VIEW_VERSION}, selector=selection,
            population=_obj(basis={"const": "captured_loaded_native_collection"}, expected_count=_nullable(_UINT),
                retained_count=_UINT, snapshot_available={"type": "boolean"}),
            page=_obj(selected_row_count=_UINT, offset=_UINT, returned_row_count=_UINT, has_more={"type": "boolean"}),
            rows=_arr(row), edit_state=deepcopy(_RESULT["properties"]["edit_state"]),
            source_features=_arr(feature), issues=_arr(fba_result_schema("FBAResultIssue"))))
    return {"oneOf": alternatives}


_VIEW = _view_schema()


def flux_balance_model_schema(kind):
    return deepcopy({"Request": _REQUEST, "Edits": _EDITS, "ViewSelector": _SELECTOR, "Result": _RESULT, "View": _VIEW}[kind])


def _require(value, code, field=""):
    if not value:
        raise ValueError("fba_model_" + code + (":" + field if field else ""))


def _unique(rows, key, field):
    values = [row[key] for row in rows]
    _require(len(values) == len(set(values)), "duplicate_id", field)


def _bounds(lower, upper):
    for value, wrong in ((lower, "positive_infinity"), (upper, "negative_infinity")):
        _require((value["kind"] == "finite") == (value["value"] is not None)
            and value["kind"] != wrong, "bound_invalid")
    if lower["value"] is not None and upper["value"] is not None:
        _require(lower["value"] <= upper["value"], "bound_invalid")


def validate_flux_balance_model_request(value):
    value = _checked(value, _REQUEST, "fba_model_request_invalid")
    file = validate_flux_balance_record("File", value["model_file"])
    _require(file["artifact_ref"] == "artifact_" + file["sha256"], "input_identity_conflict")
    if value["mode"] == "edit":
        edits = value["edits"]
        for key in ("add_metabolites", "add_reactions"):
            _unique(edits[key], "id", "/edits/" + key)
        _unique(edits["bounds"], "reaction_id", "/edits/bounds")
        _require(not ({row["id"] for row in edits["add_reactions"]}
            & {row["reaction_id"] for row in edits["bounds"]}), "conflicting_bounds")
        for reaction in edits["add_reactions"]:
            _unique(reaction["stoichiometry"], "metabolite_id", "/edits/add_reactions/stoichiometry")
            _bounds(reaction["lower"], reaction["upper"])
        for row in edits["bounds"]:
            _bounds(row["lower"], row["upper"])
    return value


def _file(raw, format_):
    sha = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "size_bytes": len(raw), "format": format_}


def _write(root, name, raw, format_, role):
    immutable_bytes(root / name, raw)
    return {"role": role, "relative_path": name, "file": _file(raw, format_)}


def _issue(code, stage, field):
    return {"code": code, "stage": stage, "field": field, "source_row_index": None,
        "reaction_position": None, "metabolite_position": None, "variable_position": None,
        "constraint_position": None, "detail_file": None}


def _edit_rows(edits):
    return [{"collection": key, "ordinal": i, "state": "not_attempted", "issue_code": None}
        for key in ("add_metabolites", "add_reactions", "bounds", "objective")
        for i in range((int(edits["objective"]["kind"] != "preserve") if key == "objective" else len(edits[key])))]


def _supported(context, model):
    info = context["source_information"]
    _require(not info["unsupported"] and not info["missing_bounds"] and not info["missing_objective"]
        and not any(row["kind"] in {"annotation_qualifier_loss", "boundary_exchange_creation"}
            or row["disposition"] in {"unsupported", "unknown"} for row in info["features"])
        and all(row["state"] == "mapped" for row in info["joins"]), "source_semantics_unsupported")
    declared = {row["loaded_id"] for row in info["joins"] if row["kind"] == "compartment" and row["state"] == "mapped"}
    _require(all(met.compartment in declared for met in model.metabolites), "source_semantics_unsupported")
    _require(model.solver.interface.__name__ == "optlang.glpk_interface", "solver_unavailable")


def _preflight(model, edits):
    metabolites = {m.id for m in model.metabolites}
    reactions = {r.id for r in model.reactions}
    compartments = set(model._compartments)
    _require(not metabolites.intersection(row["id"] for row in edits["add_metabolites"]), "metabolite_id_exists")
    _require(not reactions.intersection(row["id"] for row in edits["add_reactions"]), "reaction_id_exists")
    for row in edits["add_metabolites"]:
        _require(row["compartment_id"] in compartments, "compartment_id_unknown")
    metabolites.update(row["id"] for row in edits["add_metabolites"])
    for row in edits["add_reactions"]:
        _require(all(term["metabolite_id"] in metabolites for term in row["stoichiometry"]), "metabolite_id_unknown")
    _require(all(row["reaction_id"] in reactions for row in edits["bounds"]), "reaction_id_unknown")
    reactions.update(row["id"] for row in edits["add_reactions"])
    if edits["objective"]["kind"] == "single_reaction":
        _require(edits["objective"]["reaction_id"] in reactions, "reaction_id_unknown")


def _bound_value(value):
    return value["value"] if value["kind"] == "finite" else (-math.inf if value["kind"] == "negative_infinity" else math.inf)


def _apply(model, edits, records):
    import cobra
    by_key = {(row["collection"], row["ordinal"]): row for row in records}
    for key in ("add_metabolites", "add_reactions", "bounds", "objective"):
        rows = [edits[key]] if key == "objective" and edits[key]["kind"] != "preserve" else [] if key == "objective" else edits[key]
        for i, row in enumerate(rows):
            record = by_key[key, i]
            record["state"] = "unknown"
            if key == "add_metabolites":
                met = cobra.Metabolite(row["id"], name=row["name"], compartment=row["compartment_id"],
                    formula=row["formula"], charge=row["charge"])
                model.add_metabolites([met])
                actual = model.metabolites.get_by_id(row["id"])
                _require((actual.id, actual.name, actual.compartment, actual.formula, actual.charge) ==
                    (row["id"], row["name"], row["compartment_id"], row["formula"], row["charge"]),
                    "request_effective_mismatch")
            elif key == "add_reactions":
                reaction = cobra.Reaction(row["id"], name=row["name"],
                    lower_bound=_bound_value(row["lower"]), upper_bound=_bound_value(row["upper"]))
                reaction.add_metabolites({model.metabolites.get_by_id(term["metabolite_id"]): term["coefficient"]
                    for term in row["stoichiometry"]})
                model.add_reactions([reaction])
                actual = model.reactions.get_by_id(row["id"])
                _require(actual.name == row["name"] and actual.bounds ==
                    (_bound_value(row["lower"]), _bound_value(row["upper"]))
                    and {met.id: coefficient for met, coefficient in actual.metabolites.items()} ==
                        {term["metabolite_id"]: term["coefficient"] for term in row["stoichiometry"] if term["coefficient"] != 0},
                    "request_effective_mismatch")
            elif key == "bounds":
                model.reactions.get_by_id(row["reaction_id"]).bounds = (_bound_value(row["lower"]), _bound_value(row["upper"]))
                _require(model.reactions.get_by_id(row["reaction_id"]).bounds ==
                    (_bound_value(row["lower"]), _bound_value(row["upper"])), "request_effective_mismatch")
            else:
                direction = model.objective.direction if row["direction"] == "preserve" else row["direction"]
                model.objective = model.reactions.get_by_id(row["reaction_id"])
                model.objective.direction = direction
                from cobra.util.solver import linear_reaction_coefficients
                _require(model.objective.direction == direction and
                    {reaction.id: coefficient for reaction, coefficient in linear_reaction_coefficients(model).items()} ==
                        {row["reaction_id"]: 1}, "request_effective_mismatch")
            record["state"] = "applied"
    model.solver.update()


def _semantic(value):
    """Remove source addresses/lexical encodings only for native readback."""
    if type(value) is list:
        return [_semantic(item) for item in value]
    if type(value) is not dict:
        return value
    if {"state", "value", "native_token", "float_hex"} <= set(value):
        return {"state": value["state"], "value": value["value"]}
    if {"kind", "value", "native_token", "float_hex"} <= set(value):
        return {"kind": value["kind"], "value": value["value"]}
    omitted = {"source", "native_expression_pointer", "flux_expression_pointer", "native_capture_evidence"}
    return {key: _semantic(item) for key, item in value.items() if key not in omitted}


def _native_equal(left, right):
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right and (left != 0 or math.copysign(1, left) == math.copysign(1, right))
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_native_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_native_equal(a, b) for a, b in zip(left, right))
    return left == right


def _readback(model, context, path, format_, root, diagnostics):
    import cobra
    from . import native_flux_balance_cobra_glpk as capture
    expected = cobra.io.model_to_dict(model, sort=False)
    before_model = capture.capture_cobra_glpk_model(model, phase="effective", source_audit=context["source_audit"])
    before_problem = capture.capture_cobra_glpk_problem(model, phase="effective")
    if format_ == "sbml":
        cobra.io.write_sbml_model(model, str(path))
    else:
        cobra.io.save_json_model(model, str(path), sort=False)
    raw = read_bytes(path)
    reloaded_context = capture._load_model(path, profile=format_, raw=raw, scratch_directory=root / "tmp", diagnostics=diagnostics)
    reloaded = capture._load_audited_model(path, reloaded_context)
    reloaded.solver.update()
    after_model = capture.capture_cobra_glpk_model(reloaded, phase="effective", source_audit=reloaded_context["source_audit"])
    after_problem = capture.capture_cobra_glpk_problem(reloaded, phase="effective")
    _require(_native_equal(expected, cobra.io.model_to_dict(reloaded, sort=False))
        and _native_equal(before_model["compartments"], after_model["compartments"])
        and _native_equal(before_model["groups"], after_model["groups"])
        and _native_equal([_semantic(row["flux_unit"]) for row in before_model["reactions"]],
            [_semantic(row["flux_unit"]) for row in after_model["reactions"]])
        and _native_equal(_semantic({k: before_problem[k] for k in ("variables", "constraints", "objective", "reaction_variables", "representation")}),
            _semantic({k: after_problem[k] for k in ("variables", "constraints", "objective", "reaction_variables", "representation")})),
        "readback_mismatch")
    return raw


def run_flux_balance_model_request(request, *, model_path, output_directory, software):
    """Inspect/edit under explicit selected software; never solve or use Store."""
    request = validate_flux_balance_model_request(request)
    software = validate_flux_balance_software(software)
    _require(str(Path(__file__).resolve()) in {pin["path"] for pin in software["implementation_files"]}, "worker_source_unbound")
    from .native_flux_balance_driver import _verify_software
    _verify_software(software)
    from . import native_flux_balance_cobra_glpk as capture
    root = directory(output_directory, create=True)
    _require(not any(root.iterdir()), "output_not_empty")
    model_path = Path(model_path)
    _require(not model_path.resolve().is_relative_to(root.resolve()), "input_output_overlap")
    result = {"version": RESULT_VERSION, "request": request, "models": None, "problems": None,
        "edit_results": [] if request["mode"] == "inspect" else _edit_rows(request["edits"]),
        "edit_state": "not_requested" if request["mode"] == "inspect" else "unknown", "edited_model": None,
        "files": [], "model_optimize_call_count": 0, "issues": []}
    diagnostics = {"warnings": [], "logging": [], "exceptions": []}
    context, model, stage = None, None, "load"
    model_payload = {"version": "cobra_model_capture_v1", "loaded_original": None, "effective": None,
        "input_profile": request["model_file"]["format"], "loader": {"name": "read_sbml_model" if request["model_file"]["format"] == "sbml" else "load_json_model",
            "cobra_version": "0.32.1", "number_type": "float64", "id_replacement": "cobra_F_REPLACE" if request["model_file"]["format"] == "sbml" else "none"},
        "source_to_loaded_ids": [], "source_feature_audit": [], "source_audit": None, "issues": []}
    problem_payload = {"version": "cobra_glpk_problem_capture_v1", "loaded_original": None, "effective": None,
        "configuration_before_solve": None, "issues": []}
    try:
        raw = read_bytes(model_path)
        _require(_file(raw, request["model_file"]["format"]) == request["model_file"], "input_identity_conflict")
        name = "original-model.xml" if request["model_file"]["format"] == "sbml" else "original-model.json"
        original = _write(root, name, raw, request["model_file"]["format"], "original_model")
        result["files"].append(original)
        directory(root / "tmp", create=True)
        context = capture._load_model(root / name, profile=request["model_file"]["format"], raw=raw,
            scratch_directory=root / "tmp", diagnostics=diagnostics)
        model_payload["source_audit"] = context["source_audit"]
        model_payload["source_feature_audit"] = context["source_information"]["features"]
        model = capture._load_audited_model(root / name, context)
        model.solver.update()
        model_payload["source_to_loaded_ids"] = context["source_information"]["joins"]
        model_payload["source_feature_audit"] = context["source_information"]["features"]
        model_payload["loaded_original"] = capture.capture_cobra_glpk_model(model, phase="loaded_original", source_audit=context["source_audit"])
        problem_payload["loaded_original"] = capture.capture_cobra_glpk_problem(model, phase="loaded_original")
        if request["mode"] == "edit":
            stage = "apply"
            _supported(context, model)
            _preflight(model, request["edits"])
            _apply(model, request["edits"], result["edit_results"])
            stage = "capture"
            format_ = request["edits"]["output_format"]
            edited_name = "edited-model.xml" if format_ == "sbml" else "edited-model.json"
            edited_raw = _readback(model, context, root / edited_name, format_, root, diagnostics)
            result["edited_model"] = {"role": "edited_model", "relative_path": edited_name, "file": _file(edited_raw, format_)}
            result["files"].append(result["edited_model"])
            result["edit_state"] = "exact"
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        code = str(error).split(":", 1)[0].removeprefix("fba_model_")
        code = {"input_identity_conflict": "model_identity_conflict", "readback_mismatch": "request_effective_mismatch"}.get(code, code)
        if isinstance(error, OSError):
            code = "artifact_missing"
        code = code if code in ISSUE_CODES else {"load": "model_load_failed", "apply": "constraint_rejected", "capture": "artifact_identity_conflict"}[stage]
        result["issues"].append(_issue(code, stage, "/model" if stage == "load" else "/edits"))
        if request["mode"] == "edit":
            result["edit_state"] = "partial" if any(row["state"] == "applied" for row in result["edit_results"]) else "rejected"
            for row in result["edit_results"]:
                if row["state"] == "unknown":
                    row["issue_code"] = code
    finally:
        if context is not None:
            try:
                if model is not None:
                    model_payload["effective"] = capture.capture_cobra_glpk_model(model, phase="effective", source_audit=context["source_audit"])
                    problem_payload["effective"] = capture.capture_cobra_glpk_problem(model, phase="effective")
                mf = _write(root, "model-capture.json", canonical(model_payload).encode(), "cobra_model_capture_v1", "effective_model")
                result["files"].append(mf)
                result["models"] = parse_cobra_glpk_model_capture(read_bytes(root / "model-capture.json"), source=mf["file"], original_model=request["model_file"])
                pf = _write(root, "problem-capture.json", canonical(problem_payload).encode(), "cobra_glpk_problem_capture_v1", "effective_problem")
                result["files"].append(pf)
                result["problems"] = parse_cobra_glpk_problem_capture(read_bytes(root / "problem-capture.json"), source=pf["file"], models=result["models"])
                for key in ("models", "problems"):
                    result["issues"].extend(deepcopy(result[key]["issues"]))
                if result["edit_state"] == "exact" and (result["models"]["effective"] is None
                        or result["problems"]["effective"] is None
                        or result["models"]["effective"]["population"]["completeness"] != "complete"
                        or result["models"]["issues"] or result["problems"]["issues"]):
                    result["edit_state"], result["edited_model"] = "partial", None
                    result["files"] = [row for row in result["files"] if row["role"] != "edited_model"]
            except Exception:
                traceback.print_exc(file=sys.stderr)
                result["issues"].append(_issue("artifact_missing", "capture", "/snapshots"))
                if result["edit_state"] == "exact":
                    result["edit_state"], result["edited_model"] = "partial", None
                    result["files"] = [row for row in result["files"] if row["role"] != "edited_model"]
    try:
        _require(_file(read_bytes(model_path), request["model_file"]["format"]) == request["model_file"], "input_identity_conflict")
    except (OSError, ValueError) as error:
        traceback.print_exc(file=sys.stderr)
        result["issues"].append(_issue("artifact_missing" if isinstance(error, OSError) else "model_identity_conflict", "capture", "/original_model"))
        if result["edit_state"] == "exact":
            result["edit_state"], result["edited_model"] = "partial", None
            result["files"] = [row for row in result["files"] if row["role"] != "edited_model"]
    _verify_software(software, native_loaded=model is not None)
    return validate_flux_balance_model_result(result)


def validate_flux_balance_model_result(value):
    """Check saved shape/identity; no File, source, native or custody reads."""
    value = _checked(value, _RESULT, "fba_model_result_invalid")
    request = validate_flux_balance_model_request(value["request"])
    for key, kind in (("models", "ParsedModelSnapshots"), ("problems", "ParsedProblemSnapshots")):
        if value[key] is not None:
            validate_flux_balance_record(kind, value[key])
    for issue in value["issues"]:
        validate_flux_balance_record("Issue", issue)
    _require(value["model_optimize_call_count"] == 0, "result_invalid")
    _unique(value["files"], "role", "/files")
    for row in value["files"]:
        file = validate_flux_balance_record("File", row["file"])
        names = {"original_model": ("original-model.xml" if request["model_file"]["format"] == "sbml" else "original-model.json", request["model_file"]["format"]),
            "effective_model": ("model-capture.json", "cobra_model_capture_v1"),
            "effective_problem": ("problem-capture.json", "cobra_glpk_problem_capture_v1"),
            "edited_model": (("edited-model.xml" if request["edits"] and request["edits"]["output_format"] == "sbml" else "edited-model.json"),
                request["edits"]["output_format"] if request["edits"] else None)}
        _require(file["artifact_ref"] == "artifact_" + file["sha256"]
            and (row["relative_path"], file["format"]) == names[row["role"]], "result_invalid")
    by_role = {row["role"]: row for row in value["files"]}
    if "original_model" in by_role:
        _require(by_role["original_model"]["file"] == request["model_file"], "result_identity_conflict")
    for key, role in (("models", "effective_model"), ("problems", "effective_problem")):
        if value[key] is not None:
            _require("original_model" in by_role and role in by_role
                and (value[key]["source"] == by_role[role]["file"] or
                    value[key]["source"] is None and value[key]["loaded_original"] is None
                    and value[key]["effective"] is None and bool(value[key]["issues"])), "result_identity_conflict")
    if value["models"] is not None:
        _require(value["models"]["input_profile"] == request["model_file"]["format"] or
            value["models"]["input_profile"] == "unknown" and value["models"]["loaded_original"] is None
            and value["models"]["effective"] is None and bool(value["models"]["issues"]), "result_identity_conflict")
        audit = value["models"].get("source_audit")
        if audit is not None:
            _require(canonical(audit["original_model"]["file"]) == canonical(request["model_file"]),
                "result_identity_conflict")
    if value["models"] is not None and value["problems"] is not None:
        for phase in ("loaded_original", "effective"):
            model, problem = value["models"][phase], value["problems"][phase]
            if model is None or problem is None:
                continue
            partial = model["population"]["completeness"] != "complete"
            for index, row in enumerate(problem["reaction_variables"]):
                _join(model["reactions"], row["reaction_position"], row["reaction_id"], partial,
                    "flux_identity_conflict", f"/problems/{phase}/reaction_variables/{index}", model["population"]["reactions"])
            for index, row in enumerate(problem["constraints"]):
                if row["metabolite_position"] is not None:
                    _join(model["metabolites"], row["metabolite_position"], None, partial,
                        "constraint_identity_conflict", f"/problems/{phase}/constraints/{index}", model["population"]["metabolites"])
    if request["mode"] == "inspect":
        _require(value["edit_state"] == "not_requested" and not value["edit_results"] and value["edited_model"] is None,
            "result_invalid")
    else:
        _require(value["edit_state"] != "not_requested", "result_invalid")
        _require([(r["collection"], r["ordinal"]) for r in value["edit_results"]] ==
            [(r["collection"], r["ordinal"]) for r in _edit_rows(request["edits"])], "result_identity_conflict")
    if value["edited_model"] is not None:
        _require(request["mode"] == "edit" and value["edit_state"] == "exact"
            and value["edited_model"] == by_role.get("edited_model")
            and value["edited_model"]["file"]["format"] == request["edits"]["output_format"]
            and all(row["state"] == "applied" for row in value["edit_results"]), "result_invalid")
    if value["edit_state"] == "exact":
        _require(value["models"] is not None and value["problems"] is not None
            and all(value[key][phase] is not None for key in ("models", "problems")
                for phase in ("loaded_original", "effective"))
            and value["models"]["effective"]["population"]["completeness"] == "complete"
            and not value["models"]["issues"] and not value["problems"]["issues"]
            and not value["issues"], "exact_capture_required")
    _require((value["edit_state"] == "exact") == (value["edited_model"] is not None)
        and ("edited_model" in by_role) == (value["edited_model"] is not None), "result_invalid")
    return value


def _public(value):
    if type(value) is list:
        return [_public(item) for item in value]
    if type(value) is not dict:
        return value
    omitted = {"source", "annotation_pointer", "notes_pointer", "gpr_source_pointer", "boundary_source",
        "native_expression_pointer", "flux_expression_pointer", "native_capture_evidence", "detail_file"}
    return {key: _public(item) for key, item in value.items() if key not in omitted}


def validate_flux_balance_model_view(value):
    """Check source-free scalar/page identities; confer no source authority."""
    value = _checked(value, _VIEW, "fba_model_view_invalid")
    selected, pop, page, rows = value["selector"], value["population"], value["page"], value["rows"]
    ordinals = selected["ordinals"]
    total = pop["retained_count"] if ordinals is None else len(ordinals)
    offset, limit = selected["row_window"]["offset"], selected["row_window"]["limit"]
    _require(page["selected_row_count"] == total and page["offset"] == offset
        and page["returned_row_count"] == len(rows) == min(limit, max(0, total - offset))
        and page["has_more"] == (offset + limit < total), "view_page_conflict")
    if not pop["snapshot_available"]:
        _require(pop["expected_count"] is None and pop["retained_count"] == 0
            and all(row["availability"] == "unavailable" for row in rows), "view_population_conflict")
    elif selected["collection"] in {"model", "objective"}:
        _require(pop["expected_count"] == pop["retained_count"] == 1, "view_population_conflict")
    if pop["expected_count"] is not None:
        _require(pop["retained_count"] <= pop["expected_count"]
            and all(index < pop["expected_count"] for index in
                ([row["ordinal"] for row in rows] if ordinals is None else ordinals)), "view_population_conflict")
        if selected["collection"] == "stoichiometry":
            _require(pop["retained_count"] == pop["expected_count"], "view_population_conflict")
    returned = [row["ordinal"] for row in rows]
    if ordinals is None:
        _require(all(row["availability"] == "present" for row in rows)
            and all(left < right for left, right in zip(returned, returned[1:])), "view_ordinal_conflict")
    else:
        _require(returned == ordinals[offset:offset + limit], "view_ordinal_conflict")
    _require(len({row["ordinal"] for row in rows if row["availability"] == "present"}) <= pop["retained_count"],
        "view_population_conflict")
    seen = {}
    for index, row in enumerate(rows):
        previous = seen.setdefault(row["ordinal"], row)
        _require(canonical(previous) == canonical(row), "view_ordinal_conflict")
        if row["availability"] == "unavailable":
            _require(not pop["snapshot_available"] or selected["collection"] not in {"model", "objective"},
                "view_population_conflict")
            continue
        _require(pop["snapshot_available"] and pop["retained_count"] > 0, "view_population_conflict")
        values, collection = row["values"], selected["collection"]
        if collection in {"model", "objective"}:
            _require(row["ordinal"] == 0, "view_ordinal_conflict")
        elif collection != "stoichiometry":
            _require(values["position"] == row["ordinal"], "view_ordinal_conflict")
        if collection == "model" and values["population"]["completeness"] == "complete":
            _require(all(values["population"][axis] is not None for axis in
                ("compartments", "genes", "metabolites", "reactions", "groups")), "view_population_conflict")
        elif collection == "reactions":
            _native_bounds(values, f"/rows/{index}/values")
        elif collection == "objective":
            _terms(values, f"/rows/{index}/values")
    return value


def project_flux_balance_model_result(result, *, selector):
    """Copy one original native collection/page; no parser, calculator or I/O."""
    result = validate_flux_balance_model_result(result)
    selected = _checked(selector, _SELECTOR, "fba_model_view_invalid")
    phase, collection = selected["snapshot_phase"], selected["collection"]
    model = None if result["models"] is None else result["models"][phase]
    problem = None if result["problems"] is None else result["problems"][phase]
    snapshot = problem if collection == "objective" else model
    expected, rows = None, []
    if snapshot is not None:
        if collection == "model":
            rows = [{"ordinal": 0, "values": {key: model[key] for key in
                ("model_id", "model_name", "population", "medium_state", "medium_basis")}}]
            expected = 1
        elif collection == "objective":
            rows = [{"ordinal": 0, "values": _public(problem["objective"])}]
            expected = 1
        else:
            for row in model[collection]:
                if collection == "stoichiometry":
                    source = row["coefficient"]["source"]
                    match = re.fullmatch(r"/" + phase + r"/stoichiometry/([0-9]+)/coefficient/value", source["pointer"] if source else "")
                    _require(match is not None, "view_identity_unavailable")
                    ordinal = int(match[1])
                else:
                    ordinal = row["position"]
                rows.append({"ordinal": ordinal, "values": _public(row)})
            expected = (len(rows) if model["population"]["completeness"] == "complete" else None) if collection == "stoichiometry" else model["population"][collection]
    by_ordinal = {row["ordinal"]: row for row in rows}
    ordinals = [row["ordinal"] for row in rows] if selected["ordinals"] is None else selected["ordinals"]
    if expected is not None:
        _require(all(index < expected for index in ordinals), "view_position_out_of_range")
    chosen = [{"ordinal": index, "availability": "present" if index in by_ordinal else "unavailable",
        "values": deepcopy(by_ordinal[index]["values"]) if index in by_ordinal else None} for index in ordinals]
    offset, limit = selected["row_window"]["offset"], selected["row_window"]["limit"]
    issues = {}
    for item in (result, result["models"], result["problems"]):
        if item is not None:
            for issue in item["issues"]:
                row = _public(issue)
                issues.setdefault(canonical(row), row)
    return validate_flux_balance_model_view({"version": VIEW_VERSION, "selector": selected,
        "population": {"basis": "captured_loaded_native_collection", "expected_count": expected,
            "retained_count": len(rows), "snapshot_available": snapshot is not None},
        "page": {"selected_row_count": len(chosen), "offset": offset,
            "returned_row_count": len(chosen[offset:offset + limit]), "has_more": offset + limit < len(chosen)},
        "rows": chosen[offset:offset + limit], "edit_state": result["edit_state"],
        "source_features": [] if result["models"] is None else
            [_public(row) for row in result["models"]["source_feature_audit"]],
        "issues": list(issues.values())})


__all__ = ["REQUEST_VERSION", "RESULT_VERSION", "VIEW_VERSION", "flux_balance_model_schema", "validate_flux_balance_model_request",
    "run_flux_balance_model_request", "validate_flux_balance_model_result", "validate_flux_balance_model_view",
    "project_flux_balance_model_result"]
