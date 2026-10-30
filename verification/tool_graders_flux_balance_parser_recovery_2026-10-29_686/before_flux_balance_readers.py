"""Pure readers for retained Cobra/GLPK captures and Biomni's five-column CSV.

These readers decode supplied bytes.  They do not load an SBML model, evaluate
symbolic expressions, access files, solve a problem or calculate diagnostics.
The analytical types and all their validation belong to flux_balance_contracts.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import re

from .flux_balance_contracts import (
    ISSUE_CODES,
    flux_balance_schema,
    validate_fba_artifact_payloads,
    validate_flux_balance_record,
)
from .execution_contracts import digest

__all__ = [
    "parse_cobra_glpk_model_capture", "parse_cobra_glpk_problem_capture",
    "parse_cobra_glpk_solution_capture", "parse_biomni_fba_csv",
    "parse_fba_capture",
]

_CSV_COLUMNS = ["reaction_id", "reaction_name", "flux", "lower_bound", "upper_bound"]
_MODEL_ROWS = {
    "compartments": "Compartment", "genes": "Gene", "metabolites": "Metabolite",
    "reactions": "Reaction", "stoichiometry": "Stoichiometry", "groups": "Group",
    "medium": "MediumEntry",
}
_FORMATS = {
    "original_model": {"sbml", "cobra_json"},
    "selected_request": {"flux_balance_selected_request_v1"},
    "effective_model": {"cobra_model_capture_v1"},
    "effective_problem": {"cobra_glpk_problem_capture_v1"},
    "solution": {"cobra_glpk_solution_capture_v1"},
    "flux_csv": {"biomni_fba_csv_v1"},
    "native_log": {"utf8_text", "biomni_fba_log_v1"},
    "manifest": {"flux_balance_native_manifest_v1"},
}


class _SourceFiles(dict):
    """Per-call supplied JSON documents; never a file-opening registry."""
    def __init__(self, files, *, documents=None, current=None):
        super().__init__(files)
        self.documents = dict(getattr(files, "documents", {}))
        self.documents.update(documents or {})
        self.current = current


def _pointer(document, pointer):
    if type(pointer) is not str or (pointer and not pointer.startswith("/")):
        raise ValueError("schema_invalid:/pointer")
    if pointer == "":
        return document
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ValueError("schema_invalid:/pointer")
        token = token.replace("~1", "/").replace("~0", "~")
        if type(document) is dict and token in document:
            document = document[token]
        elif type(document) is list and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(document):
            document = document[int(token)]
        else:
            raise ValueError("schema_invalid:/pointer")
    return document


def _location(file, pointer, files):
    documents = getattr(files, "documents", {})
    if file["artifact_ref"] in documents:
        _pointer(documents[file["artifact_ref"]], pointer)
    return {"file": deepcopy(file), "pointer": pointer}


def _issue(code, source=None, pointer=None, *, index=None, reaction=None,
           metabolite=None, variable=None, constraint=None):
    return validate_flux_balance_record("Issue", {
        "code": code if code in ISSUE_CODES else "schema_invalid", "stage": "parse",
        "field": pointer or None, "source_row_index": index,
        "reaction_position": reaction, "metabolite_position": metabolite,
        "variable_position": variable, "constraint_position": constraint,
        "detail_file": source,
    })


def _error_issue(error, source, pointer):
    code, _, where = str(error).partition(":")
    return _issue(code, source, pointer + where)


def _row_issue(error, source, pointer, raw, index):
    issue = _error_issue(error, source, pointer)
    issue["source_row_index"] = index
    if type(raw) is dict:
        for key in ("reaction_position", "metabolite_position", "variable_position", "constraint_position"):
            if type(raw.get(key)) is int and raw[key] >= 0:
                issue[key] = raw[key]
    return issue


def _resolve_schema(schema, root):
    while "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError("schema_invalid:")
        schema = root
        for part in ref[2:].split("/"):
            schema = schema[part.replace("~1", "/").replace("~0", "~")]
    return schema


def _object_schema(schema, root):
    schema = _resolve_schema(schema, root)
    for branch in schema.get("anyOf", schema.get("oneOf", [])):
        candidate = _object_schema(branch, root)
        if "properties" in candidate:
            return candidate
    return schema


def _bind(value, schema, files, root=None):
    """Bind only typed source addresses, leaving raw native JSON untouched."""
    root = schema if root is None else root
    schema = _resolve_schema(schema, root)
    if type(value) is list:
        for branch in schema.get("anyOf", schema.get("oneOf", [])):
            candidate = _resolve_schema(branch, root)
            if candidate.get("type") == "array":
                schema = candidate
                break
    schema = _object_schema(schema, root)
    if value is None:
        return None
    properties = schema.get("properties", {})
    if set(properties) == {"file", "pointer"} and type(value) is dict:
        if set(value) == {"role", "pointer"}:
            if value["role"] not in files:
                raise ValueError("artifact_missing:")
            return _location(files[value["role"]], value["pointer"], files)
        if set(value) == {"file", "pointer"}:
            if value["file"] not in files.values():
                raise ValueError("artifact_identity_conflict:/file")
            return _location(value["file"], value["pointer"], files)
    if set(properties) == {"artifact_ref", "sha256", "size_bytes", "format"}:
        if type(value) is dict and set(value) == {"role", "identity"}:
            file = files.get(value["role"])
            if file is None:
                raise ValueError("artifact_missing:")
            if value["identity"] != {key: file[key] for key in ("sha256", "size_bytes")}:
                raise ValueError("artifact_identity_conflict:")
            return deepcopy(file)
        if value not in files.values():
            raise ValueError("artifact_identity_conflict:")
        return deepcopy(value)
    if type(value) is dict and properties:
        current = getattr(files, "current", None)
        if current is not None:
            for key, item in value.items():
                if key in properties and key.endswith("_pointer") and item is not None:
                    _pointer(files.documents[current], item)
        return {key: _bind(item, properties[key], files, root) if key in properties
                else deepcopy(item) for key, item in value.items()}
    if type(value) is list and "items" in schema:
        return [_bind(item, schema["items"], files, root) for item in value]
    return deepcopy(value)


def _record(kind, value, files):
    return validate_flux_balance_record(kind, _bind(value, flux_balance_schema(kind), files))


def _verify_bytes(raw, source, role=None):
    source = validate_flux_balance_record("File", source)
    if type(raw) is not bytes:
        raise ValueError("schema_invalid:/bytes")
    if len(raw) != source["size_bytes"] or hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError("artifact_identity_conflict:")
    if role is not None and source["format"] not in _FORMATS[role]:
        raise ValueError("unsupported_model_format:/format" if role == "original_model" else "schema_invalid:/format")
    return source


def _json(raw, source):
    _verify_bytes(raw, source)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("schema_invalid:")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("schema_invalid:")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("schema_invalid:") from error


def _keys(kind, value):
    schema = _object_schema(flux_balance_schema(kind), flux_balance_schema(kind))
    return type(value) is dict and set(value) == set(schema["properties"])


def _rows(kind, value, files, source, pointer, issues, *, distinct=(),
          duplicate_code="schema_invalid", source_indices=None, original_indices=None):
    if type(value) is not list:
        issues.append(_issue("schema_invalid", source, pointer))
        return [], True
    rows, changed = [], False
    for array_index, raw in enumerate(value):
        index = array_index if original_indices is None else original_indices[array_index]
        try:
            rows.append((index, _record(kind, raw, files)))
        except ValueError as error:
            issue = _row_issue(error, source, f"{pointer}/{index}", raw, index)
            field = {"Reaction": "reaction_position", "Metabolite": "metabolite_position",
                     "Variable": "variable_position", "Constraint": "constraint_position"}.get(kind)
            if field and type(raw) is dict and type(raw.get("position")) is int and raw["position"] >= 0:
                issue[field] = raw["position"]
            issues.append(issue)
            changed = True
    # Ambiguous entity identities cannot be repaired by selecting the first row.
    counts = {key: Counter(row[key] for _, row in rows) for key in distinct}
    retained = []
    for index, row in rows:
        if any(counts[key][row[key]] > 1 for key in distinct):
            issues.append(_issue(duplicate_code, source, f"{pointer}/{index}", index=index))
            changed = True
        else:
            retained.append(row)
            if source_indices is not None:
                source_indices.append(index)
    return retained, changed


def _model_snapshot(raw, files, source, pointer, issues):
    if raw is None:
        return None
    if not _keys("ModelSnapshot", raw):
        issues.append(_issue("schema_invalid", source, pointer))
        return None
    value = deepcopy(raw)
    partial = False
    for field, kind in _MODEL_ROWS.items():
        value[field], changed = _rows(kind, value[field], files, source,
            pointer + "/" + field, issues,
            distinct=("id", "position") if field in ("compartments", "genes", "metabolites", "reactions", "groups") else (),
            duplicate_code="duplicate_reaction_id" if field == "reactions" else "schema_invalid")
        partial |= changed
    if type(value.get("population")) is dict:
        for field in ("compartments", "genes", "metabolites", "reactions", "groups"):
            expected = value["population"].get(field)
            if type(expected) is int:
                kept = []
                for index, row in enumerate(value[field]):
                    if row["position"] >= expected:
                        issues.append(_issue("model_identity_conflict", source, f"{pointer}/{field}/{index}"))
                        partial = True
                    else:
                        kept.append(row)
                value[field] = kept
                if [row["position"] for row in kept] != list(range(expected)):
                    partial = True
            elif value["population"].get("completeness") == "complete":
                partial = True
        # Invalid metadata joins are not permission to replace an entity with
        # the entity at the same compacted array index.
        def in_population(axis, position):
            count = value["population"].get(axis)
            return count is None or (type(count) is int and position < count)
        for row in value["reactions"]:
            valid = [pos for pos in row["gene_positions"] if in_population("genes", pos)]
            if valid != row["gene_positions"]:
                row["gene_positions"] = valid
                partial = True
                issues.append(_issue("model_identity_conflict", source, pointer + "/reactions/gene_positions", reaction=row["position"]))
        for row in value["metabolites"]:
            pos = row["compartment_position"]
            if pos is not None and not in_population("compartments", pos):
                # Null would falsely mean genuinely absent; reject this row.
                partial = True
                issues.append(_issue("model_identity_conflict", source, pointer + "/metabolites/compartment_position", metabolite=row["position"]))
        value["metabolites"] = [row for row in value["metabolites"] if row["compartment_position"] is None or in_population("compartments", row["compartment_position"])]
        pairs = Counter((row["metabolite_position"], row["reaction_position"]) for row in value["stoichiometry"])
        kept = []
        for index, row in enumerate(value["stoichiometry"]):
            if (pairs[row["metabolite_position"], row["reaction_position"]] > 1 or
                    not in_population("metabolites", row["metabolite_position"]) or not in_population("reactions", row["reaction_position"])):
                partial = True
                issues.append(_issue("model_identity_conflict", source, f"{pointer}/stoichiometry/{index}",
                    reaction=row["reaction_position"], metabolite=row["metabolite_position"]))
            else:
                kept.append(row)
        value["stoichiometry"] = kept
        kept = []
        for index, row in enumerate(value["medium"]):
            if in_population("reactions", row["reaction_position"]):
                kept.append(row)
            else:
                partial = True
                issues.append(_issue("model_identity_conflict", source, f"{pointer}/medium/{index}", reaction=row["reaction_position"]))
        value["medium"] = kept
        for group in value["groups"]:
            members = []
            for index, member in enumerate(group["members"]):
                axis = member["kind"] + "s"
                present = next((row for row in value[axis] if row["position"] == member["position"]), None)
                if not in_population(axis, member["position"]) or (present and present["id"] != member["id"]):
                    partial = True
                    issues.append(_issue("model_identity_conflict", source, pointer + "/groups/members", index=index))
                else:
                    members.append(member)
            group["members"] = members
    if partial and type(value.get("population")) is dict:
        value["population"]["completeness"] = "partial"
        issues.append(_issue("partial_population", source, pointer))
    try:
        return _record("ModelSnapshot", value, files)
    except ValueError as error:
        issues.append(_error_issue(error, source, pointer))
        return None


def _empty_models(source=None):
    return {"loaded_original": None, "effective": None, "source": source,
            "input_profile": "unknown", "loader": None, "source_to_loaded_ids": [],
            "source_feature_audit": [], "issues": []}


def _model_capture(raw, source, original_model, files):
    result = _empty_models()
    try:
        _verify_bytes(raw, source, "effective_model")
        payload = _json(raw, source)
        files = _SourceFiles(files, documents={source["artifact_ref"]: payload}, current=source["artifact_ref"])
        result["source"] = source
        if not _keys("EffectiveModelPayload", payload):
            raise ValueError("schema_invalid:")
        # First validate the small container with snapshots/row populations absent.
        head = deepcopy(payload)
        head.update(loaded_original=None, effective=None, source_to_loaded_ids=[],
                    source_feature_audit=[], issues=[])
        head = _record("EffectiveModelPayload", head, files)
        expected = {"sbml": ("read_sbml_model", "cobra_F_REPLACE"),
                    "cobra_json": ("load_json_model", "none")}[head["input_profile"]]
        if (head["loader"]["name"], head["loader"]["id_replacement"]) != expected:
            raise ValueError("model_identity_conflict:/loader")
        if original_model is not None and original_model["format"] != head["input_profile"]:
            raise ValueError("model_identity_conflict:/input_profile")
        result.update(input_profile=head["input_profile"], loader=head["loader"])
        for phase in ("loaded_original", "effective"):
            result[phase] = _model_snapshot(payload[phase], files, source, "/" + phase, result["issues"])
        for field, kind in (("source_to_loaded_ids", "SourceIdJoin"),
                            ("source_feature_audit", "SourceFeature"), ("issues", "Issue")):
            rows, _ = _rows(kind, payload[field], files, source, "/" + field, result["issues"])
            if field == "issues":
                result["issues"].extend(rows)
            else:
                result[field] = rows
        joins = result["source_to_loaded_ids"]
        result["source_to_loaded_ids"] = []
        for index, row in enumerate(joins):
            trial = {**result, "source_to_loaded_ids": [row]}
            try:
                validate_flux_balance_record("ParsedModelSnapshots", trial)
                result["source_to_loaded_ids"].append(row)
            except ValueError as error:
                result["issues"].append(_row_issue(error, source, f"/source_to_loaded_ids/{index}", row, index))
        return validate_flux_balance_record("ParsedModelSnapshots", result)
    except ValueError as error:
        result["issues"].append(_error_issue(error, source, ""))
        # Head/metadata failure does not authorize interpreting either snapshot.
        if result["input_profile"] == "unknown":
            result["loaded_original"] = result["effective"] = None
        return result


def parse_cobra_glpk_model_capture(raw: bytes, *, source: dict, original_model: dict) -> dict:
    """Decode a normalized SBML or Cobra-JSON capture, without loading either model."""
    original_model = validate_flux_balance_record("File", original_model)
    source = validate_flux_balance_record("File", source)
    return _model_capture(raw, source, original_model,
                          {"effective_model": source, "original_model": original_model})


def _expression(raw, kind, files, source, pointer, issues):
    if not _keys(kind, raw):
        raise ValueError("schema_invalid:")
    value = deepcopy(raw)
    value["terms"], changed = _rows("Term", value["terms"], files, source,
        pointer + "/terms", issues, distinct=("variable_position",))
    if changed:
        value["terms_complete"] = False
        issues.append(_issue("term_population_incomplete", source, pointer + "/terms"))
    return _record(kind, value, files), changed


def _problem_snapshot(raw, files, source, phase, issues):
    if raw is None:
        return None
    pointer = "/" + phase
    if not _keys("ProblemSnapshot", raw):
        issues.append(_issue("schema_invalid", source, pointer))
        return None
    value = deepcopy(raw)
    try:
        if value["phase"] != phase:
            raise ValueError("model_identity_conflict:/phase")
        value["variables"], partial = _rows("Variable", value["variables"], files,
            source, pointer + "/variables", issues, distinct=("id", "position", "native_index", "optlang_position"),
            duplicate_code="duplicate_variable_id")
        if type(value["constraints"]) is not list:
            raise ValueError("schema_invalid:/constraints")
        constraints, constraint_indices = [], []
        for index, row in enumerate(value["constraints"]):
            try:
                row, changed = _expression(row, "Constraint", files, source,
                    f"{pointer}/constraints/{index}", issues)
                constraints.append(row)
                constraint_indices.append(index)
                partial |= changed
            except ValueError as error:
                issues.append(_error_issue(error, source, f"{pointer}/constraints/{index}"))
                partial = True
        value["constraints"], changed = _rows("Constraint", constraints, files, source,
            pointer + "/constraints", issues, distinct=("id", "position", "native_index", "optlang_position"),
            duplicate_code="duplicate_constraint_id", original_indices=constraint_indices)
        partial |= changed
        value["objective"], changed = _expression(value["objective"], "Objective", files,
            source, pointer + "/objective", issues)
        partial |= changed
        value["reaction_variables"], changed = _rows("ReactionVariables", value["reaction_variables"],
            files, source, pointer + "/reaction_variables", issues,
            distinct=("reaction_position", "reaction_id"), duplicate_code="flux_identity_conflict")
        partial |= changed
        value["issues"], _ = _rows("Issue", value["issues"], files, source, pointer + "/issues", issues)
        for axis, count_key in (("variables", "variable_count"), ("constraints", "constraint_count")):
            count = value[count_key]
            if type(count) is int:
                kept = [row for row in value[axis] if row["position"] < count]
                if len(kept) != len(value[axis]):
                    issues.append(_issue("schema_invalid", source, pointer + "/" + axis))
                value[axis] = kept
                partial |= [row["position"] for row in kept] != list(range(count))
        if type(value["variable_count"]) is int:
            variables = {row["position"]: row["id"] for row in value["variables"]}
            for expr_index, expression in enumerate([*value["constraints"], value["objective"]]):
                terms = [term for term in expression["terms"] if term["variable_position"] < value["variable_count"]]
                if len(terms) != len(expression["terms"]):
                    expression["terms"] = terms
                    expression["terms_complete"] = False
                    partial = True
                    issues.append(_issue("variable_identity_conflict", source, pointer + "/terms", index=expr_index))
            kept = []
            for index, row in enumerate(value["reaction_variables"]):
                conflict = row["forward_variable_position"] == row["reverse_variable_position"]
                for side in ("forward", "reverse"):
                    pos, identifier = row[side + "_variable_position"], row[side + "_variable_id"]
                    conflict |= pos >= value["variable_count"] or (pos in variables and variables[pos] != identifier)
                if conflict:
                    issues.append(_issue("variable_identity_conflict", source, f"{pointer}/reaction_variables/{index}", reaction=row["reaction_position"]))
                    partial = True
                else:
                    kept.append(row)
            value["reaction_variables"] = kept
        if partial:
            value["representation"] = "partial"
            issue = _issue("partial_population", source, pointer)
            issues.append(issue)
            value["issues"].append(issue)
        return _record("ProblemSnapshot", value, files)
    except ValueError as error:
        issues.append(_error_issue(error, source, pointer))
        return None


def _files_from(value):
    """Collect already validated retained addresses for standalone parser calls."""
    found = []
    if type(value) is dict:
        if set(value) == {"artifact_ref", "sha256", "size_bytes", "format"}:
            found.append(value)
        else:
            for field, child in value.items():
                if field not in {"annotations", "notes", "native_cobra_json", "sbml_metadata", "native_optlang_json"}:
                    found.extend(_files_from(child))
    elif type(value) is list:
        for child in value:
            found.extend(_files_from(child))
    return found


def _problem_capture(raw, source, models, files):
    result = {"loaded_original": None, "effective": None, "source": None,
              "configuration_before_solve": None, "issues": []}
    try:
        _verify_bytes(raw, source, "effective_problem")
        payload = _json(raw, source)
        files = _SourceFiles(files, documents={source["artifact_ref"]: payload}, current=source["artifact_ref"])
        result["source"] = source
        if not _keys("EffectiveProblemPayload", payload) or payload["version"] != "cobra_glpk_problem_capture_v1":
            raise ValueError("schema_invalid:")
        for phase in ("loaded_original", "effective"):
            result[phase] = _problem_snapshot(payload[phase], files, source, phase, result["issues"])
        if payload["configuration_before_solve"] is not None:
            try:
                result["configuration_before_solve"] = _record("SolverConfiguration",
                    payload["configuration_before_solve"], files)
            except ValueError as error:
                result["issues"].append(_error_issue(error, source, "/configuration_before_solve"))
        rows, _ = _rows("Issue", payload["issues"], files, source, "/issues", result["issues"])
        result["issues"].extend(rows)
        # Validate cross-model IDs without assuming a sorted or complete axis.
        for phase in ("loaded_original", "effective"):
            problem, model = result[phase], models[phase]
            if problem is None or model is None:
                continue
            reactions = {row["position"]: row for row in model["reactions"]}
            retained = []
            for index, row in enumerate(problem["reaction_variables"]):
                reaction = reactions.get(row["reaction_position"])
                count = model["population"]["reactions"]
                missing_conflict = reaction is None and (model["population"]["completeness"] == "complete" or
                    (count is not None and row["reaction_position"] >= count))
                if missing_conflict or (reaction is not None and reaction["id"] != row["reaction_id"]):
                    result["issues"].append(_issue("flux_identity_conflict", source,
                        f"/{phase}/reaction_variables/{index}", reaction=row["reaction_position"]))
                    problem["representation"] = "partial"
                else:
                    retained.append(row)
                    if reaction is None:
                        result["issues"].append(_issue("partial_population", source,
                            f"/{phase}/reaction_variables/{index}", reaction=row["reaction_position"]))
                        problem["representation"] = "partial"
            problem["reaction_variables"] = retained
            metabolites = {row["position"] for row in model["metabolites"]}
            count = model["population"]["metabolites"]
            constraints = []
            for index, row in enumerate(problem["constraints"]):
                pos = row["metabolite_position"]
                if pos is not None and pos not in metabolites and (model["population"]["completeness"] == "complete" or (count is not None and pos >= count)):
                    result["issues"].append(_issue("constraint_identity_conflict", source, f"/{phase}/constraints/{index}", constraint=row["position"], metabolite=pos))
                    problem["representation"] = "partial"
                else:
                    constraints.append(row)
            problem["constraints"] = constraints
        return validate_flux_balance_record("ParsedProblemSnapshots", result)
    except ValueError as error:
        result["issues"].append(_error_issue(error, source, ""))
        return result


def parse_cobra_glpk_problem_capture(raw: bytes, *, source: dict, models: dict) -> dict:
    source = validate_flux_balance_record("File", source)
    models = validate_flux_balance_record("ParsedModelSnapshots", models)
    files = {f"retained_{i}": file for i, file in enumerate(_files_from(models))}
    if models["source"] is not None:
        files["effective_model"] = models["source"]
    files["effective_problem"] = source
    return _problem_capture(raw, source, models, files)


def _solution_capture(raw, source, problem, files):
    result = {"native": None, "source": None, "issues": []}
    try:
        _verify_bytes(raw, source, "solution")
        payload = _json(raw, source)
        files = _SourceFiles(files, documents={source["artifact_ref"]: payload}, current=source["artifact_ref"])
        result["source"] = source
        if not _keys("SolutionPayload", payload):
            raise ValueError("schema_invalid:")
        value = deepcopy(payload)
        source_indices = {}
        for field, kind in (("variable_values", "VariableValue"), ("constraint_values", "ConstraintValue"),
                            ("reaction_values", "ReactionValue"), ("native_passes", "NativePass"), ("issues", "Issue")):
            source_indices[field] = []
            value[field], _ = _rows(kind, value[field], files, source, "/" + field, result["issues"],
                source_indices=source_indices[field], distinct=("position",) if kind == "NativePass" else ())
        if problem is not None:
            for field, axis, pos, id_key, code in (
                ("variable_values", "variables", "variable_position", "variable_id", "variable_identity_conflict"),
                ("constraint_values", "constraints", "constraint_position", "constraint_id", "constraint_identity_conflict"),
                ("reaction_values", "reaction_variables", "reaction_position", "reaction_id", "flux_identity_conflict"),
            ):
                expected = {row["position" if axis != "reaction_variables" else pos]:
                            row["id" if axis != "reaction_variables" else id_key] for row in problem[axis]}
                retained, indices = [], []
                for index, row in zip(source_indices[field], value[field]):
                    out_of_range = axis != "reaction_variables" and row[pos] >= problem[axis[:-1] + "_count"]
                    if out_of_range or (row[pos] in expected and expected[row[pos]] != row[id_key]):
                        issue = _issue(code, source, f"/{field}/{index}", index=index)
                        issue[pos] = row[pos]
                        result["issues"].append(issue)
                    else:
                        retained.append(row)
                        indices.append(index)
                        if row[pos] not in expected:
                            result["issues"].append(_issue("partial_population", source, f"/{field}/{index}"))
                value[field] = retained
                source_indices[field] = indices
        # Duplicate native values are evidence of ambiguity, never absence.
        for field, key, code in (("variable_values", "variable_position", "duplicate_variable_id"),
                                 ("constraint_values", "constraint_position", "duplicate_constraint_id"),
                                 ("reaction_values", "reaction_position", "duplicate_reaction_id")):
            counts = Counter(row[key] for row in value[field])
            ids = Counter(row[key.replace("position", "id")] for row in value[field])
            for index, row in zip(source_indices[field], value[field]):
                if counts[row[key]] > 1 or ids[row[key.replace("position", "id")]] > 1:
                    issue = _issue(code, source, f"/{field}/{index}", index=index)
                    issue[key] = row[key]
                    result["issues"].append(issue)
        if value["point_state"] == "not_established":
            for field, key, operand in (("variable_values", "variable_position", "primal"),
                                       ("constraint_values", "constraint_position", "activity"),
                                       ("reaction_values", "reaction_position", "flux")):
                kept = []
                for index, row in zip(source_indices[field], value[field]):
                    if row[operand]["state"] == "present":
                        issue = _issue("primal_not_established", source, f"/{field}/{index}/{operand}", index=index)
                        issue[key] = row[key]
                        result["issues"].append(issue)
                    else:
                        kept.append(row)
                value[field] = kept
        value["issues"].extend(result["issues"])
        result["native"] = _record("SolutionPayload", value, files)
        return validate_flux_balance_record("ParsedNativeSolution", result)
    except ValueError as error:
        result["issues"].append(_error_issue(error, source, ""))
        return result


def parse_cobra_glpk_solution_capture(raw: bytes, *, source: dict, problem: dict | None) -> dict:
    source = validate_flux_balance_record("File", source)
    if problem is not None:
        problem = validate_flux_balance_record("ProblemSnapshot", problem)
    files = {f"retained_{i}": file for i, file in enumerate(_files_from(problem))}
    files["solution"] = source
    return _solution_capture(raw, source, problem, files)


def _csv_number(token, source, pointer):
    value = {"value": None, "state": "invalid", "native_token": token,
             "float_hex": None, "source": {"file": source, "pointer": pointer},
             "precision": "unknown", "missing_reason": None}
    if not token.strip():
        value.update(state="missing", missing_reason="not_returned")
    else:
        try:
            decimal = Decimal(token)
            if not decimal.is_finite():
                if not math.isfinite(float(token)):
                    value["state"] = "nonfinite"
            else:
                number = float(decimal)
                if math.isfinite(number) and (number != 0 or decimal.is_zero()):
                    value.update(value=number, state="present")
        except (InvalidOperation, ValueError, OverflowError):
            pass
    return validate_flux_balance_record("Number", value)


def _csv_bound(token, source, pointer):
    number = _csv_number(token, source, pointer)
    kind = {"present": "finite", "missing": "missing"}.get(number["state"], "invalid")
    if number["state"] == "nonfinite":
        decimal = Decimal(token)
        if decimal.is_infinite():
            kind = "negative_infinity" if decimal.is_signed() else "positive_infinity"
    return validate_flux_balance_record("Bound", {
        "kind": kind, "value": number["value"], "native_token": token,
        "float_hex": None, "source": number["source"],
    })


def parse_biomni_fba_csv(raw: bytes, *, model: dict | None, source: dict) -> dict:
    """Read original row identities; CSV decimals do not certify native precision."""
    source = validate_flux_balance_record("File", source)
    if model is not None:
        model = validate_flux_balance_record("ModelSnapshot", model)
    result = {"rows": [], "issues": []}
    try:
        _verify_bytes(raw, source, "flux_csv")
        text = raw.decode("utf-8-sig")
    except (ValueError, UnicodeError) as error:
        result["issues"].append(_error_issue(error, source, ""))
        return result
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        if next(reader, None) != _CSV_COLUMNS:
            raise ValueError("schema_invalid:/columns")
    except (ValueError, csv.Error) as error:
        result["issues"].append(_error_issue(error, source, ""))
        return result
    reactions = {} if model is None else {row["id"]: row for row in model["reactions"]}
    counts = Counter()
    index = 0
    while True:
        try:
            values = next(reader)
        except StopIteration:
            break
        except csv.Error:
            result["issues"].append(_issue("schema_invalid", source, f"/rows/{index}", index=index))
            break  # Unclosed quoting makes all later logical row identities unknowable.
        pointer = f"/rows/{index}"
        if values and values[0]:
            counts[values[0]] += 1
        if len(values) != len(_CSV_COLUMNS) or not values[0]:
            result["issues"].append(_issue("schema_invalid", source, pointer, index=index))
            index += 1
            continue
        reaction = reactions.get(values[0])
        row = {"source_row_index": index, "reaction_id": values[0],
               "reaction_position": reaction["position"] if reaction else None,
               "reaction_name": values[1] or None,
               "flux": _csv_number(values[2], source, pointer + "/flux"),
               "csv_lower": _csv_bound(values[3], source, pointer + "/lower_bound"),
               "csv_upper": _csv_bound(values[4], source, pointer + "/upper_bound"),
               "association": "matched" if reaction else "unknown"}
        if reaction is None and model is not None:
            result["issues"].append(_issue("reaction_id_unknown", source, pointer + "/reaction_id", index=index))
        if row["flux"]["state"] != "present":
            code = "flux_nonfinite" if row["flux"]["state"] == "nonfinite" else "flux_missing" if row["flux"]["state"] == "missing" else "schema_invalid"
            result["issues"].append(_issue(code, source, pointer + "/flux", index=index))
        result["issues"].append(_issue("source_precision_unknown", source, pointer + "/flux", index=index))
        for name, bound, effective in (("lower_bound", row["csv_lower"], "lower"), ("upper_bound", row["csv_upper"], "upper")):
            if bound["kind"] == "invalid" or (effective == "lower" and bound["kind"] == "positive_infinity") or (effective == "upper" and bound["kind"] == "negative_infinity"):
                result["issues"].append(_issue("bound_invalid", source, pointer + "/" + name, index=index))
            elif reaction and bound["kind"] not in ("missing", "invalid") and (bound["kind"], bound["value"]) != (reaction[effective]["kind"], reaction[effective]["value"]):
                row["association"] = "conflicting"
                result["issues"].append(_issue("request_effective_mismatch", source, pointer + "/" + name, index=index, reaction=reaction["position"]))
        try:
            result["rows"].append(validate_flux_balance_record("FluxRow", row))
        except ValueError as error:
            result["issues"].append(_error_issue(error, source, pointer))
        index += 1
    for row in result["rows"]:
        if counts[row["reaction_id"]] > 1:
            row["association"] = "duplicate"
            result["issues"].append(_issue("duplicate_reaction_id", source,
                f"/rows/{row['source_row_index']}/reaction_id", index=row["source_row_index"], reaction=row["reaction_position"]))
    return validate_flux_balance_record("ParsedFluxRows", result)


def _missing(reason="unavailable_source"):
    return {"value": None, "state": "missing", "native_token": None,
            "float_hex": None, "source": None, "precision": "unknown", "missing_reason": reason}


def _unknown_solver():
    return {"interface": None, "name": None, "version": None, "cobra_version": None,
            "optlang_version": None, "raw_status": None, "status": "unknown",
            "feasibility_tolerance": _missing(), "optimality_tolerance": _missing(),
            "integrality_tolerance": _missing(), "raw_parameters_file": None,
            "diagnostic_file": None, "alternate_optimum_claim": "not_assessed",
            "alternate_claim_source": None}


def _status(raw):
    return {"optimal": "optimal", "feasible": "feasible", "infeasible": "infeasible",
            "unbounded": "unbounded", "infeasible_or_unbounded": "infeasible_or_unbounded",
            "time_limit": "time_limit", "iteration_limit": "iteration_limit",
            "numeric": "numerical_failure"}.get(raw, "unknown")


def _legacy_log(raw, source, issues):
    """Extract only the exact grammar of the inspected four-argument wrapper."""
    result = {"objective": _missing(), "source_active_count": None,
              "source_active_threshold": _missing(), "raw_status": None}
    if source["format"] != "biomni_fba_log_v1":
        return result
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        issues.append(_issue("schema_invalid", source))
        return result
    if not text.startswith("# Flux Balance Analysis (FBA) Research Log\n\n"):
        issues.append(_issue("schema_invalid", source))
        return result
    patterns = {
        "objective": r"- Objective value: ([+-]?(?:[0-9]+\.[0-9]{6}|inf|nan))",
        "raw_status": r"- Optimization status: ([^\r\n]+)",
        "source_active_count": r"- Number of active reactions \(flux > 1e-6\): ([0-9]+)",
    }
    for field, pattern in patterns.items():
        found = [(index, re.fullmatch(pattern, line)) for index, line in enumerate(text.splitlines())]
        found = [(index, match.group(1)) for index, match in found if match is not None]
        if len(found) > 1:
            issues.append(_issue("schema_invalid", source, "/" + field))
        elif found:
            index, token = found[0]
            if field == "raw_status":
                result[field] = token
            elif field == "objective":
                value = _csv_number(token, source, f"/lines/{index}")
                value["precision"] = "formatted_6dp"
                result[field] = value
            else:
                result[field] = int(token)
                threshold = _csv_number("1e-6", source, f"/lines/{index}")
                result["source_active_threshold"] = threshold
    return result


def _selected_request(payloads, files, expected, issues):
    if "selected_request" not in files:
        issues.append(_issue("input_missing", pointer="/selected_request"))
        return None
    source = files["selected_request"]
    try:
        raw = _json(payloads["selected_request"]["bytes"], source)
        files = _SourceFiles(files, documents={source["artifact_ref"]: raw}, current=source["artifact_ref"])
        # Digest the exact selected job, before source-address binding changes it.
        value = _record("SelectedRequestPayload", raw, files)
        if value["attempt"] != expected or digest(raw["requested_job"]) != expected["requested_job_sha256"]:
            raise ValueError("artifact_identity_conflict:/attempt")
        model = value["requested_job"]["native_flux_balance"]["model_input"]
        if "original_model" in files and (model["format"] != files["original_model"]["format"] or
                any(model["file"][key] != files["original_model"][key] for key in ("sha256", "size_bytes"))):
            raise ValueError("model_identity_conflict:/requested_job/native_flux_balance/model_input")
        return value
    except ValueError as error:
        issues.append(_error_issue(error, source, "/selected_request"))
        return None


def _manifest(payloads, files, expected, selected, issues):
    if "manifest" not in files:
        return None
    source = files["manifest"]
    try:
        raw = _json(payloads["manifest"]["bytes"], source)
        files = _SourceFiles(files, documents={source["artifact_ref"]: raw}, current=source["artifact_ref"])
        value = _record("FBANativeManifest", raw, files)
        if not value["sealed"]:
            raise ValueError("writer_not_closed:/sealed")
        if value["attempt"] != expected:
            raise ValueError("artifact_identity_conflict:/attempt")
        for row in value["files"]:
            role = row["role"]
            actual = payloads[role]
            if row["format"] not in _FORMATS[role] or row["state"] != actual["state"]:
                raise ValueError("artifact_identity_conflict:/files/" + role)
            if actual["file"] is not None and (row["identity"] != {
                    key: actual["file"][key] for key in ("sha256", "size_bytes")}
                    or row["format"] != actual["file"]["format"]):
                raise ValueError("artifact_identity_conflict:/files/" + role)
            if actual["state"] == "present" and role not in files:
                raise ValueError("artifact_identity_conflict:/files/" + role)
        if "effective_problem" in files and value["effective_problem_sha256"] != files["effective_problem"]["sha256"]:
            raise ValueError("artifact_identity_conflict:/effective_problem_sha256")
        if selected is not None:
            job = selected["requested_job"]["native_flux_balance"]
            model = job["model_input"]
            if (value["software_sha256"] != digest(job["software"])
                    or value["source_function_sha256"] != job["source_function_sha256"]):
                raise ValueError("artifact_identity_conflict:/software_sha256")
            if value["model_identity"] != {key: model["file"][key] for key in ("sha256", "size_bytes")}:
                raise ValueError("model_identity_conflict:/model_identity")
            if "original_model" in files and (model["format"] != files["original_model"]["format"] or
                    value["model_identity"] != {key: files["original_model"][key] for key in ("sha256", "size_bytes")}):
                raise ValueError("model_identity_conflict:/model_identity")
            actual = {row["name"]: row["version"] for row in value["actual_distributions"]}
            if len(actual) != len(value["actual_distributions"]):
                raise ValueError("artifact_identity_conflict:/actual_distributions")
            for row in job["software"]["distributions"]:
                if actual.get(row["name"]) != row["version"]:
                    raise ValueError("artifact_identity_conflict:/actual_distributions")
            if value["actual_solver"]["interface"] != job["software"]["solver_interface"]:
                raise ValueError("artifact_identity_conflict:/actual_solver/interface")
        return value
    except ValueError as error:
        issues.append(_error_issue(error, source, "/manifest"))
        return None


def parse_fba_capture(payloads: dict, *, expected: dict) -> dict:
    """Decode an explicitly supplied eight-role capture; this is not runtime custody.

    Unavailable or mismatched roles cannot supply source-address authority.
    Independently usable records survive with explicit missing/conflict issues.
    """
    payloads = validate_fba_artifact_payloads(payloads)
    expected = validate_flux_balance_record("FBAAttemptIdentity", expected)
    issues, files, retained = [], {}, {}
    conflicts = set()
    for role, payload in payloads.items():
        source = payload["file"]
        if source is not None:
            try:
                _verify_bytes(payload["bytes"], source, role)
                old = retained.get(source["artifact_ref"])
                if old is not None and old != source:
                    conflicts.add(source["artifact_ref"])
                    raise ValueError("artifact_identity_conflict:")
                retained[source["artifact_ref"]] = source
                if payload["state"] in {"present", "truncated"}:
                    files[role] = source
            except ValueError as error:
                issues.append(_error_issue(error, None, "/" + role))
        if payload["state"] != "present":
            code = {"absent": "artifact_missing", "truncated": "artifact_truncated", "incompatible": "schema_invalid"}[payload["state"]]
            issues.append(_issue(code, source if source is not None and source["artifact_ref"] in retained else None, "/" + role))
    if conflicts:
        files = {role: file for role, file in files.items() if file["artifact_ref"] not in conflicts}
        for ref in conflicts:
            retained.pop(ref, None)
        for issue in issues:
            if issue["detail_file"] is not None and issue["detail_file"]["artifact_ref"] in conflicts:
                issue["detail_file"] = None
    # An incomplete JSON artifact is never decoded into an apparently complete
    # snapshot. CSV has independent complete logical rows and may remain useful.
    usable = {role: file for role, file in files.items()
              if payloads[role]["state"] == "present" or role == "flux_csv"}
    documents = {}
    for role, source in usable.items():
        if role not in {"flux_csv", "native_log"} and source["format"] != "sbml":
            try:
                documents[source["artifact_ref"]] = _json(payloads[role]["bytes"], source)
            except ValueError:
                pass  # The specific role parser records its located decode error.
    usable = _SourceFiles(usable, documents=documents)
    selected = _selected_request(payloads, usable, expected, issues)
    manifest = _manifest(payloads, usable, expected, selected, issues)
    models = _empty_models()
    if "effective_model" in usable:
        models = _model_capture(payloads["effective_model"]["bytes"], usable["effective_model"],
            usable.get("original_model"), usable)
    problems = {"loaded_original": None, "effective": None, "source": None,
                "configuration_before_solve": None, "issues": []}
    if "effective_problem" in usable:
        problems = _problem_capture(payloads["effective_problem"]["bytes"], usable["effective_problem"], models, usable)
    solution = {"native": None, "source": None, "issues": []}
    if "solution" in usable:
        solution = _solution_capture(payloads["solution"]["bytes"], usable["solution"], problems["effective"], usable)
    if solution["native"] is not None and models["effective"] is not None:
        model = models["effective"]
        reactions = {row["position"]: row["id"] for row in model["reactions"]}
        count = model["population"]["reactions"]
        kept = []
        for row in solution["native"]["reaction_values"]:
            pos = row["reaction_position"]
            invalid = (pos in reactions and reactions[pos] != row["reaction_id"]) or (
                pos not in reactions and (model["population"]["completeness"] == "complete" or (count is not None and pos >= count)))
            if invalid:
                loc = row["flux"]["source"]
                issue = _issue("flux_identity_conflict", usable["solution"], loc["pointer"] if loc else "/reaction_values", reaction=pos)
                solution["issues"].append(issue)
                solution["native"]["issues"].append(issue)
            else:
                kept.append(row)
        solution["native"]["reaction_values"] = kept
    csv_rows = {"rows": [], "issues": []}
    if "flux_csv" in usable:
        csv_rows = parse_biomni_fba_csv(payloads["flux_csv"]["bytes"], model=models["effective"], source=usable["flux_csv"])
    solver = deepcopy(manifest["actual_solver"]) if manifest else _unknown_solver()
    count = manifest["solve_call_count"] if manifest else None
    if solution["native"] is not None:
        native = solution["native"]
        if count is not None and count != native["model_optimize_call_count"]:
            issues.append(_issue("artifact_identity_conflict", usable.get("solution"), "/model_optimize_call_count"))
            count = None
        elif count is None:
            count = native["model_optimize_call_count"]
        if manifest is None:
            solver["raw_status"] = native["optlang_status"]
            solver["status"] = _status(native["optlang_status"])
            configuration = native["configuration_after_solve"] or problems["configuration_before_solve"]
            if configuration:
                solver.update(interface=configuration["interface"], name="GLPK", version=configuration["glpk_version"],
                              cobra_version=configuration["cobra_version"], optlang_version=configuration["optlang_version"])
                for key in ("feasibility_tolerance", "integrality_tolerance", "optimality_tolerance"):
                    solver[key] = deepcopy(configuration[key])
        elif solver["raw_status"] != native["optlang_status"]:
            issues.append(_issue("status_unrecognized", usable.get("solution"), "/optlang_status"))
    legacy = {"objective": _missing(), "source_active_count": None,
              "source_active_threshold": _missing(), "raw_status": None}
    if "native_log" in usable:
        legacy = _legacy_log(payloads["native_log"]["bytes"], usable["native_log"], issues)
    if solver["raw_status"] is None and legacy["raw_status"] is not None:
        solver["raw_status"] = legacy["raw_status"]
        solver["status"] = _status(legacy["raw_status"])
    if solver["raw_status"] is not None and solver["status"] == "unknown":
        issues.append(_issue("status_unrecognized", usable.get("solution") or usable.get("native_log"), "/raw_status"))
    objective_request = None
    changes = None
    if selected is not None:
        job = selected["requested_job"]["native_flux_balance"]
        objective_request = job["objective"]
        changes = []
        versions = {row["name"]: row["version"] for row in job["software"]["distributions"]}
        for cfg, role, pointer in ((problems["configuration_before_solve"], "effective_problem", "/configuration_before_solve"),
                (solution["native"]["configuration_after_solve"] if solution["native"] else None, "solution", "/configuration_after_solve")):
            if cfg is not None and (cfg["interface"] != job["software"]["solver_interface"] or
                    any(name in versions and cfg[name + "_version"] != versions[name]
                        for name in ("cobra", "optlang", "swiglpk"))):
                issues.append(_issue("artifact_identity_conflict", usable[role], pointer))
        if models["loader"] is not None and "cobra" in versions and models["loader"]["cobra_version"] != versions["cobra"]:
            issues.append(_issue("artifact_identity_conflict", usable["effective_model"], "/loader/cobra_version"))
        positions = {} if models["effective"] is None else {row["id"]: row["position"] for row in models["effective"]["reactions"]}
        for index, row in enumerate(job["constraints"] or []):
            bounds = {}
            for side in ("lower", "upper"):
                bounds[side] = deepcopy(row[side])
                if bounds[side]["source"] is None:
                    bounds[side]["source"] = {"file": usable["selected_request"],
                        "pointer": f"/requested_job/native_flux_balance/constraints/{index}/{side}"}
            changes.append({"reaction_id": row["reaction_id"], "requested_lower": bounds["lower"],
                "requested_upper": bounds["upper"], "effective_reaction_position": positions.get(row["reaction_id"]),
                "application": "unknown", "issue_code": None})
    realization = manifest["request_realization"] if manifest and selected else "unknown"
    if selected and manifest and any(issue["code"] in {"artifact_identity_conflict", "model_identity_conflict"} for issue in issues):
        realization = "mismatch"
    native = {"version": "native_fba_result_v1", "solver": solver,
        "objective": legacy["objective"], "flux_rows": csv_rows["rows"], "solve_call_count": count,
        "constraint_changes": changes, "objective_request": objective_request,
        "objective_application": "unknown", "request_realization": realization,
        "execution_outcome": manifest["execution_outcome"] if manifest else "unknown",
        "source_active_count": legacy["source_active_count"], "source_active_threshold": legacy["source_active_threshold"],
        "source_log_file": usable.get("native_log"), "issues": csv_rows["issues"]}
    return validate_flux_balance_record("ParsedFBABundle", {
        "models": models, "problems": problems, "native_solution": solution, "native": native,
        "original_request_file": usable.get("selected_request") if selected else None,
        "native_manifest_file": usable.get("manifest"), "retained_files": list(retained.values()), "issues": issues,
    })
