"""Read the pinned live Cobra/GLPK objects around one original invocation.

Scientific imports occur only when these helpers are called in the selected
bounded process. This module captures source operands and native observations;
it contains no feasibility, residual, objective or annotation-score calculator.
"""
from contextlib import contextmanager
from copy import deepcopy
import io
import json
import math
import os
from pathlib import Path
import tempfile
import traceback
import xml.etree.ElementTree as ET
from xml.parsers import expat

from .execution_contracts import canonical, digest
from .flux_balance_contracts import flux_balance_schema
from .native_flux_balance_contracts import require
from .native_flux_balance_storage import decode_json, directory, read_bytes


def location(role, pointer):
    return {"role": role, "pointer": pointer}


def issue(code, stage, field=None, **positions):
    row = {"code": code, "stage": stage, "field": field, "source_row_index": None,
           "reaction_position": None, "metabolite_position": None, "variable_position": None,
           "constraint_position": None, "detail_file": None}
    row.update(positions)
    return row


def exception(error, stage, operation):
    return {"stage": stage, "operation": operation, "exception_module": type(error).__module__,
            "exception_class": type(error).__name__, "message": str(error),
            "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__))}


def observation(value):
    if value is None:
        return {"state": "missing", "value": None, "native_token": None, "float_hex": None}
    if type(value) is int:
        return {"state": "present", "value": value, "native_token": str(value), "float_hex": None}
    number = float(value)
    return {"state": "present" if math.isfinite(number) else "nonfinite",
            "value": number if math.isfinite(number) else None,
            "native_token": repr(number), "float_hex": number.hex() if math.isfinite(number) else None}


def number(value=None, *, role, pointer, missing_reason="unavailable_source"):
    raw = observation(value)
    return {**raw, "precision": "full_native" if raw["state"] == "present" else "unknown",
            "source": location(role, pointer) if value is not None else None,
            "missing_reason": missing_reason if value is None else None}


def _number_observed(raw, *, role, pointer, established=True, missing_reason="primal_not_established"):
    if not established or raw is None or raw.get("state") == "missing":
        return number(role=role, pointer=pointer, missing_reason=missing_reason if not established else "not_returned")
    return {k: raw[k] for k in ("state", "value", "native_token", "float_hex")} | {
        "precision": "full_native" if raw["state"] == "present" else "unknown",
        "source": location(role, pointer), "missing_reason": None}


def bound(value, *, role, pointer):
    value = float(value)
    if math.isfinite(value):
        return {"kind": "finite", "value": value, "native_token": repr(value), "float_hex": value.hex(),
                "source": location(role, pointer)}
    return {"kind": "negative_infinity" if value == -math.inf else "positive_infinity" if value == math.inf else "invalid",
            "value": None, "native_token": repr(value), "float_hex": None, "source": location(role, pointer)}


def unknown_unit():
    return {"native_text": None, "basis": "unknown", "source": None}


def _name(value):
    return value if type(value) is str and value else None


def _escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _xml_name(value):
    if value.startswith("{"):
        namespace, name = value[1:].split("}", 1)
        return {"namespace_uri": namespace, "local_name": name}
    return {"namespace_uri": None, "local_name": value}


def _source_audit(raw, profile):
    audit = {"version": "cobra_fba_source_audit_v1", "input_profile": profile,
             "original_model": location("original_model", ""), "xml_elements": None, "issues": []}
    if profile == "cobra_json":
        return audit, decode_json(raw)
    # No DTD or external entity resolution; preserve original bytes separately.
    parser = expat.ParserCreate()
    def forbidden(*_):
        raise ValueError("source_semantics_unsupported:doctype_or_entity")
    parser.StartDoctypeDeclHandler = forbidden
    parser.ExternalEntityRefHandler = forbidden
    parser.Parse(raw, True)
    rows, stack, namespaces, siblings, elements = [], [], [], {}, []
    for event, item in ET.iterparse(io.BytesIO(raw), events=("start-ns", "start", "end")):
        if event == "start-ns":
            namespaces.append({"prefix": item[0], "uri": item[1]})
        elif event == "start":
            parent = stack[-1][0] if stack else None
            name = _xml_name(item.tag)
            key = (parent, item.tag)
            ordinal = siblings.get(key, 0)
            siblings[key] = ordinal + 1
            index = len(rows)
            path = (deepcopy(rows[parent]["path"]) if parent is not None else []) + [{"name": name, "sibling_ordinal": ordinal}]
            rows.append({"source_record_index": index, "path": path, "parent_source_record_index": parent,
                         "child_source_record_indices": [], "namespace_declarations": namespaces,
                         "attributes": [{"name": _xml_name(k), "value": v} for k, v in item.attrib.items()],
                         "text": None, "tail": None})
            elements.append(item)
            namespaces = []
            if parent is not None:
                rows[parent]["child_source_record_indices"].append(index)
            stack.append((index, item))
        else:
            index, _ = stack.pop()
    # Tails can finish after an end event at an incremental parser boundary.
    for row, element in zip(rows, elements):
        row["text"], row["tail"] = element.text, element.tail
    audit["xml_elements"] = rows
    return audit, None


def _attribute(row, name, *, namespace=None):
    for index, attr in enumerate(row["attributes"]):
        if attr["name"]["local_name"] == name and (namespace is None or attr["name"]["namespace_uri"] == namespace):
            return attr["value"], f"/source_audit/xml_elements/{row['source_record_index']}/attributes/{index}/value"
    return None, None


def _source_information(audit, original_json, model=None):
    """Source-ID joins and declared transformations; no biological inference."""
    from cobra.io import sbml
    entries, features, source_reactions, missing_bounds = [], [], {}, set()
    unsupported = False
    has_objective = False
    axes = {"compartment": "compartments", "gene": "genes", "metabolite": "metabolites", "reaction": "reactions", "group": "groups"}
    if audit["input_profile"] == "cobra_json":
        require(type(original_json) is dict, "source_semantics_unsupported")
        entries.append(("model", None, original_json.get("id"), original_json.get("id"), location("original_model", "/id") if "id" in original_json else location("original_model", "")))
        for kind, axis in axes.items():
            values = original_json.get(axis, {} if kind == "compartment" else [])
            iterator = list(values.items()) if kind == "compartment" and isinstance(values, dict) else enumerate(values)
            for i, (key, value) in enumerate(iterator):
                sid = key if kind == "compartment" else value.get("id")
                pointer = f"/{axis}/{_escape(key)}" if kind == "compartment" else f"/{axis}/{i}/id"
                entries.append((kind, i, sid, sid, location("original_model", pointer)))
                if kind == "reaction":
                    source_reactions[sid] = {"gpr_native": value.get("gene_reaction_rule"), "gpr_pointer": None, "flux_unit": unknown_unit(),
                                              "json_source": deepcopy(value), "source_index": i}
                    if "lower_bound" not in value or "upper_bound" not in value:
                        missing_bounds.add(sid)
                        features.append({"kind": "default_bound", "source": location("original_model", f"/reactions/{i}"), "disposition": "transformed"})
                    has_objective |= "objective_coefficient" in value
        recognized = {"id", "name", "notes", "annotation", "compartments", "metabolites", "reactions", "genes", "version"}
        for key in original_json.keys() - recognized:
            features.append({"kind": "ignored_json_field", "source": location("original_model", "/" + _escape(key)), "disposition": "unsupported"})
            unsupported = True
    else:
        rows = audit["xml_elements"]
        parameters = {_attribute(r, "id")[0]: r for r in rows if r["path"][-1]["name"]["local_name"] == "parameter"}
        mapping = {"model": ("model", None), "compartment": ("compartment", None),
                   "species": ("metabolite", sbml.F_SPECIE), "geneProduct": ("gene", sbml.F_GENE),
                   "reaction": ("reaction", sbml.F_REACTION), "group": ("group", sbml.F_GROUP)}
        active_ids = {_attribute(row, "activeObjective")[0] for row in rows if row["path"][-1]["name"]["local_name"] == "listOfObjectives"}
        for row in rows:
            tag = row["path"][-1]["name"]["local_name"]
            source = location("effective_model", f"/source_audit/xml_elements/{row['source_record_index']}")
            if tag in mapping:
                kind, replacement = mapping[tag]
                sid, ptr = _attribute(row, "id")
                loaded = sbml.F_REPLACE[replacement](sid) if sid is not None and replacement else sid
                entries.append((kind, row["source_record_index"], sid, loaded,
                                location("effective_model", ptr) if ptr else source))
                if kind == "reaction":
                    gpr = next((i for i in row["child_source_record_indices"] if rows[i]["path"][-1]["name"]["local_name"] == "geneProductAssociation"), None)
                    units = []
                    for side in ("lowerFluxBound", "upperFluxBound"):
                        parameter = parameters.get(_attribute(row, side)[0])
                        units.append(_attribute(parameter, "units") if parameter is not None else (None, None))
                    unit = {"native_text": units[0][0], "basis": "supplied", "source": location("effective_model", units[0][1])} if (
                        units[0][0] and units[0][0] == units[1][0]) else unknown_unit()
                    source_reactions[loaded] = {"gpr_native": None, "flux_unit": unit,
                        "gpr_pointer": None if gpr is None else f"/source_audit/xml_elements/{gpr}", "json_source": None,
                        "source_index": row["source_record_index"]}
                    if any(_attribute(row, side)[0] is None for side in ("lowerFluxBound", "upperFluxBound")):
                        missing_bounds.add(loaded)
                        features.append({"kind": "default_bound", "source": source, "disposition": "transformed"})
                if kind == "metabolite" and _attribute(row, "boundaryCondition")[0] in {"true", "1"}:
                    features.append({"kind": "boundary_exchange_creation", "source": source, "disposition": "transformed"})
                    # This exact ID rule is from the selected loader, not a guessed join.
                    missing_bounds.add("EX_" + loaded)
            if tag == "objective" and _attribute(row, "id")[0] in active_ids:
                has_objective = any(rows[i]["path"][-1]["name"]["local_name"] == "listOfFluxObjectives"
                                    and bool(rows[i]["child_source_record_indices"]) for i in row["child_source_record_indices"])
            feature = {"assignmentRule": "dynamic_rule", "rateRule": "dynamic_rule", "algebraicRule": "dynamic_rule",
                       "event": "event", "initialAssignment": "initial_assignment", "stoichiometryMath": "nonconstant_stoichiometry",
                       "kineticLaw": "dynamic_rule"}.get(tag)
            if tag == "speciesReference" and (_attribute(row, "constant")[0] in {"false", "0"} or _attribute(row, "stoichiometry")[0] is None):
                feature = "nonconstant_stoichiometry"
            if feature:
                features.append({"kind": feature, "source": source, "disposition": "unsupported"})
                unsupported = True
            if tag == "annotation":
                features.append({"kind": "annotation_qualifier_loss", "source": source, "disposition": "transformed"})
            for ns in row["namespace_declarations"]:
                uri = ns["uri"]
                if "/sbml/" in uri and ("/fbc/" in uri or "/groups/" in uri or uri.count("/") > 7):
                    supported = uri.endswith("/fbc/version2") or uri.endswith("/groups/version1") or uri.endswith("/core")
                    features.append({"kind": "sbml_package", "source": source,
                                     "disposition": "preserved" if supported else "unsupported"})
                    unsupported |= not supported
    if not has_objective:
        features.append({"kind": "missing_objective", "source": location("original_model", ""), "disposition": "unknown"})
    seen = set()
    joins = []
    mapped = set()
    positions_by_kind = {}
    if model is not None:
        for kind, axis in axes.items():
            ids = list(model._compartments) if kind == "compartment" else [r.id for r in getattr(model, axis)]
            positions_by_kind[kind] = {identifier: position for position, identifier in enumerate(ids)}
    for kind, index, sid, loaded, source in entries:
        key = kind, loaded
        if key in seen:
            features.append({"kind": "id_collision", "source": source, "disposition": "unsupported"})
            unsupported = True
        seen.add(key)
        position = None
        if model is not None:
            if kind == "model":
                position = 0 if model.id == loaded else None
            else:
                position = positions_by_kind[kind].get(loaded)
        state = "mapped" if position is not None else "unmapped"
        joins.append({"kind": kind, "source_record_index": index, "source_id": sid, "loaded_id": loaded,
                      "loaded_position": position, "state": state, "source": source})
        if position is not None:
            mapped.add((kind, loaded))
    if model is not None:
        for kind, axis in axes.items():
            ids = list(model._compartments) if kind == "compartment" else [r.id for r in getattr(model, axis)]
            for position, identifier in enumerate(ids):
                if (kind, identifier) not in mapped:
                    joins.append({"kind": kind, "source_record_index": None, "source_id": None, "loaded_id": identifier,
                                  "loaded_position": position, "state": "loader_created", "source": location("original_model", "")})
    return {"joins": joins, "features": features, "reactions": source_reactions,
            "missing_bounds": missing_bounds, "missing_objective": not has_objective, "unsupported": unsupported}


def _source_information_guarded(audit, original_json, diagnostics, model=None):
    try:
        return _source_information(audit, original_json, model)
    except Exception as error:
        diagnostics["exceptions"].append(exception(error, "load", "source_information"))
        audit["issues"].append(issue("source_semantics_unsupported", "load", "/source_audit"))
        # The decoded original source remains valid evidence even when its
        # scientific interpretation cannot be represented by this loader.
        return {"joins": [], "features": [], "reactions": {}, "missing_bounds": set(),
                "missing_objective": True, "unsupported": True}


def _load_model(path, *, profile, raw, scratch_directory, diagnostics):
    import cobra
    import libsbml
    cobra.Configuration().solver = "glpk"
    config = cobra.Configuration()
    load_config = {"solver_interface": config.solver.__name__, "lower_bound": observation(config.lower_bound),
                   "upper_bound": observation(config.upper_bound), "tolerance": observation(config.tolerance)}
    audit, original_json = _source_audit(raw, profile)
    preliminary = _source_information_guarded(audit, original_json, diagnostics)
    loader_diagnostics = []
    if profile == "sbml":
        doc = libsbml.readSBMLFromFile(str(path))
        for i in range(doc.getNumErrors()):
            e = doc.getError(i)
            loader_diagnostics.append({"stage": "load", "producer": "libsbml", "code": e.getErrorId(),
                "severity": e.getSeverity(), "message": e.getMessage(), "line": e.getLine(), "column": e.getColumn()})
    context = {"source_audit": audit, "source_json": original_json, "source_information": preliminary,
               "load_configuration": load_config, "loader_diagnostics": loader_diagnostics,
               "scratch_directory": str(directory(scratch_directory)), "diagnostics": diagnostics}
    return context


def _load_audited_model(path, context):
    import cobra
    profile = context["source_audit"]["input_profile"]
    model = cobra.io.read_sbml_model(str(path), number=float, f_replace=cobra.io.sbml.F_REPLACE) if profile == "sbml" else cobra.io.load_json_model(str(path))
    require(model.solver.interface.__name__ == "optlang.glpk_interface", "solver_unavailable")
    context["source_information"] = _source_information_guarded(context["source_audit"], context["source_json"], context["diagnostics"], model)
    model._fba_capture_context = context
    return model


def _context(model):
    return getattr(model, "_fba_capture_context", {})


def _associations(annotation, pointer):
    rows = []
    for database, values in annotation.items():
        values = values if isinstance(values, list) else [values]
        for index, accession in enumerate(values):
            if type(accession) is str and accession:
                rows.append({"database": _name(database), "accession": accession,
                    "source": location("effective_model", pointer + "/" + _escape(database) + (f"/{index}" if isinstance(annotation[database], list) else ""))})
    return rows


def capture_cobra_glpk_model(model, *, phase, source_audit):
    import cobra
    require(phase in {"loaded_original", "effective"}, "schema_invalid")
    base = "/" + phase
    ctx = _context(model)
    metadata = {axis: [] for axis in ("compartments", "genes", "metabolites", "reactions", "groups")}
    failures = []
    source_reactions = ctx.get("source_information", {}).get("reactions", {})
    compartment_ids = list(model._compartments)
    for met in model.metabolites:
        if met.compartment and met.compartment not in compartment_ids:
            compartment_ids.append(met.compartment)
    compartments = [{"position": i, "id": identifier, "name": _name(model._compartments.get(identifier))}
                    for i, identifier in enumerate(compartment_ids)]
    metadata["compartments"] = [{"id": key, "name": value} for key, value in model._compartments.items()]
    genes, metabolites, reactions, groups, stoichiometry = [], [], [], [], []
    gene_pos = {gene: i for i, gene in enumerate(model.genes)}
    met_pos = {met: i for i, met in enumerate(model.metabolites)}
    rxn_pos = {rxn: i for i, rxn in enumerate(model.reactions)}
    def metadata_row(axis, obj):
        i = len(metadata[axis])
        row = {"id": obj.id, "name": obj.name, "annotation": deepcopy(obj.annotation), "notes": deepcopy(obj.notes)}
        metadata[axis].append(row)
        return row, f"{base}/native_capture_evidence/loaded_metadata/{axis}/{i}"
    for i, gene in enumerate(model.genes):
        raw, ptr = metadata_row("genes", gene)
        genes.append({"position": i, "id": gene.id, "name": _name(gene.name), "associations": _associations(raw["annotation"], ptr + "/annotation"),
            "supplied_target_refs": [], "annotation_pointer": ptr + "/annotation", "notes_pointer": ptr + "/notes"})
    for i, met in enumerate(model.metabolites):
        raw, ptr = metadata_row("metabolites", met)
        raw.update(formula=met.formula, charge=observation(met.charge), compartment=met.compartment)
        metabolites.append({"position": i, "id": met.id, "name": _name(met.name),
            "compartment_position": compartment_ids.index(met.compartment) if met.compartment in compartment_ids else None,
            "formula": _name(met.formula), "charge": number(met.charge, role="effective_model", pointer=f"{base}/metabolites/{i}/charge/value"),
            "associations": _associations(raw["annotation"], ptr + "/annotation"), "annotation_pointer": ptr + "/annotation", "notes_pointer": ptr + "/notes"})
    for i, rxn in enumerate(model.reactions):
        raw, ptr = metadata_row("reactions", rxn)
        original = source_reactions.get(rxn.id, {})
        raw["source_gene_reaction_rule"] = original.get("gpr_native")
        raw["gene_reaction_rule"] = rxn.gene_reaction_rule
        raw["boundary"] = rxn.boundary
        gpr_ptr = original.get("gpr_pointer")
        if original.get("gpr_native") is not None:
            gpr_ptr = ptr + "/source_gene_reaction_rule"
        reactions.append({"position": i, "id": rxn.id, "name": _name(rxn.name),
            "lower": bound(rxn.lower_bound, role="effective_model", pointer=f"{base}/reactions/{i}/lower/value"),
            "upper": bound(rxn.upper_bound, role="effective_model", pointer=f"{base}/reactions/{i}/upper/value"),
            "flux_unit": deepcopy(original.get("flux_unit", unknown_unit())), "boundary_kind": "unknown" if rxn.boundary else "internal",
            "boundary_source": location("effective_model", ptr + "/boundary"),
            "gpr_native": original.get("gpr_native"), "gpr_loaded": rxn.gene_reaction_rule,
            "gpr_source_pointer": gpr_ptr, "gene_positions": sorted(gene_pos[g] for g in rxn.genes),
            "associations": _associations(raw["annotation"], ptr + "/annotation"),
            "annotation_pointer": ptr + "/annotation", "notes_pointer": ptr + "/notes"})
        for met, coefficient in rxn.metabolites.items():
            index = len(stoichiometry)
            stoichiometry.append({"metabolite_position": met_pos[met], "reaction_position": i,
                "coefficient": number(coefficient, role="effective_model", pointer=f"{base}/stoichiometry/{index}/coefficient/value"),
                "coefficient_unit": unknown_unit()})
    for i, group in enumerate(model.groups):
        raw, ptr = metadata_row("groups", group)
        members = []
        raw["members"] = [{"type": type(m).__name__, "id": getattr(m, "id", None)} for m in group.members]
        for member in group.members:
            for kind, positions in (("gene", gene_pos), ("metabolite", met_pos), ("reaction", rxn_pos)):
                if member in positions:
                    members.append({"kind": kind, "position": positions[member], "id": member.id})
                    break
            else:
                failures.append(exception(ValueError("unsupported group member"), "capture", "group.members"))
        groups.append({"position": i, "id": group.id, "name": _name(group.name),
                       "kind": group.kind if group.kind in {"classification", "partonomy", "collection"} else "unknown",
                       "members": sorted(members, key=lambda m: (m["kind"], m["position"])),
                       "annotation_pointer": ptr + "/annotation", "notes_pointer": ptr + "/notes"})
    native_json = None
    try:
        native_json = decode_json(cobra.io.to_json(model, sort=False))
    except Exception as error:
        failures.append(exception(error, "capture", "cobra.io.to_json"))
    medium, medium_state = [], "observed"
    try:
        for identifier, value in model.medium.items():
            index = len(medium)
            source = location("effective_model", f"{base}/medium/{index}/native_value/value")
            medium.append({"reaction_position": rxn_pos[model.reactions.get_by_id(identifier)],
                           "native_value": number(value, role="effective_model", pointer=source["pointer"]),
                           "native_meaning": "cobra_medium_entry", "source": source})
    except Exception as error:
        medium_state = "unavailable"
        failures.append(exception(error, "capture", "model.medium"))
    return {"model_id": _name(model.id), "model_name": _name(model.name), "compartments": compartments,
            "genes": genes, "metabolites": metabolites, "reactions": reactions, "stoichiometry": stoichiometry, "groups": groups,
            "annotations": deepcopy(model.annotation), "notes": deepcopy(model.notes), "sbml_metadata": deepcopy(getattr(model, "_sbml", None)),
            "native_cobra_json": native_json, "native_sbml_export": None, "medium": medium, "medium_state": medium_state,
            "medium_basis": "cobra_exchange_heuristic", "population": {"compartments": len(compartments), "genes": len(model.genes),
                "metabolites": len(model.metabolites), "reactions": len(model.reactions), "groups": len(model.groups), "completeness": "complete"},
            "native_capture_evidence": {"version": "cobra_model_native_evidence_v1", "load_configuration": ctx.get("load_configuration"),
                "loaded_metadata": metadata, "warnings": deepcopy(ctx.get("diagnostics", {}).get("warnings", [])),
                "loader_diagnostics": deepcopy(ctx.get("loader_diagnostics", [])), "capture_failures": failures}}


def _controls(control, failures, operation):
    values = {}
    for key in dir(type(control)):
        if key.startswith("_") or key in {"this", "thisown"}:
            continue
        descriptor = getattr(type(control), key)
        if not isinstance(descriptor, property):
            continue
        native_type = None
        try:
            value = getattr(control, key)
            native_type = type(value).__module__ + "." + type(value).__name__
            if value is None or type(value) in (str, int, bool):
                values[key] = value
            elif isinstance(value, float) and math.isfinite(value):
                values[key] = float(value)
            else:
                raise TypeError("native_control_not_primitive:" + native_type)
        except Exception as error:
            values[key] = {"state": "unavailable", "type": native_type}
            failures.append(exception(error, "capture", operation + "/" + key))
    return values


def capture_cobra_glpk_configuration(model, *, role, pointer):
    import cobra
    import optlang
    import swiglpk as glp
    import importlib.metadata
    config = model.solver.configuration
    fields = flux_balance_schema("SolverConfiguration")["properties"]["simplex_controls"]["properties"]
    after = role == "solution"
    result = {"interface": model.solver.interface.__name__, "glpk_version": glp.glp_version(), "cobra_version": cobra.__version__,
        "optlang_version": optlang.__version__, "swiglpk_version": importlib.metadata.version("swiglpk"),
        "model_tolerance": number(model.tolerance, role=role, pointer=pointer + "/model_tolerance/value"),
        "presolve": config.presolve, "verbosity": config.verbosity, "timeout_seconds": config.timeout,
        "feasibility_tolerance": number(config.tolerances.feasibility, role=role, pointer=pointer + "/feasibility_tolerance/value"),
        "integrality_tolerance": number(config.tolerances.integrality, role=role, pointer=pointer + "/integrality_tolerance/value"),
        "optimality_tolerance": number(role=role, pointer=pointer + "/optimality_tolerance/value", missing_reason="unsupported_api"),
        "simplex_controls": {key: getattr(config._smcp, key) for key in fields},
        "integer_controls_pointer": "/native_capture_evidence/configuration_after_solve/integer_controls" if after else
            "/effective/native_capture_evidence/configuration/integer_controls"}
    return result


def _native_bounds(kind, lower, upper, *, role, pointer):
    import swiglpk as glp
    require(kind in {glp.GLP_FR, glp.GLP_LO, glp.GLP_UP, glp.GLP_DB, glp.GLP_FX}, "bound_invalid")
    return (bound(lower if kind in {glp.GLP_LO, glp.GLP_DB, glp.GLP_FX} else -math.inf, role=role, pointer=pointer + "/lower/value"),
            bound(upper if kind in {glp.GLP_UP, glp.GLP_DB, glp.GLP_FX} else math.inf, role=role, pointer=pointer + "/upper/value"))


def _native_structure(model):
    """An identity of actual native operands, never a scientific diagnostic."""
    import swiglpk as glp
    problem = model.solver.problem
    cols, rows = glp.glp_get_num_cols(problem), glp.glp_get_num_rows(problem)
    indices, values = glp.intArray(cols + 1), glp.doubleArray(cols + 1)
    columns, constraints = [], []
    for i in range(1, cols + 1):
        columns.append([i, glp.glp_get_col_name(problem, i), glp.glp_get_col_kind(problem, i), glp.glp_get_col_type(problem, i),
                        observation(glp.glp_get_col_lb(problem, i)), observation(glp.glp_get_col_ub(problem, i)), observation(glp.glp_get_obj_coef(problem, i))])
    for i in range(1, rows + 1):
        nnz = glp.glp_get_mat_row(problem, i, indices, values)
        constraints.append([i, glp.glp_get_row_name(problem, i), glp.glp_get_row_type(problem, i),
                            observation(glp.glp_get_row_lb(problem, i)), observation(glp.glp_get_row_ub(problem, i)),
                            [[indices[j], observation(values[j])] for j in range(1, nnz + 1)]])
    return {"columns": columns, "rows": constraints, "objective_direction": glp.glp_get_obj_dir(problem),
            "objective_constant": observation(glp.glp_get_obj_coef(problem, 0)),
            "interface_offset": observation(model.solver._objective_offset)}


def capture_cobra_glpk_problem(model, *, phase):
    import swiglpk as glp
    from optlang.util import expr_to_json
    from optlang.expression_parsing import parse_optimization_expression
    require(phase in {"loaded_original", "effective"}, "schema_invalid")
    solver, problem = model.solver, model.solver.problem
    base = "/" + phase
    cols, rows = glp.glp_get_num_cols(problem), glp.glp_get_num_rows(problem)
    variables, constraints, joins, problems, failures = [], [], [], [], []
    raw_vars, raw_rows, expressions = [], [], []
    opt_vars = {v.name: (i, v) for i, v in enumerate(solver.variables)}
    opt_rows = {c.name: (i, c) for i, c in enumerate(solver.constraints)}
    met_constraints = {model.constraints[m.id]: i for i, m in enumerate(model.metabolites) if m.id in model.constraints}
    native_json = None
    try:
        native_json = solver.to_json()
        canonical(native_json)
    except Exception as error:
        failures.append(exception(error, "capture", "solver.to_json"))
    for i in range(1, cols + 1):
        pointer = f"{base}/variables/{len(variables)}"
        try:
            identifier, kind, bound_type = glp.glp_get_col_name(problem, i), glp.glp_get_col_kind(problem, i), glp.glp_get_col_type(problem, i)
            lo, hi = glp.glp_get_col_lb(problem, i), glp.glp_get_col_ub(problem, i)
            opt_position, variable = opt_vars[identifier]
            require(variable._index == i, "variable_identity_conflict")
            lower, upper = _native_bounds(bound_type, lo, hi, role="effective_problem", pointer=pointer)
            raw_vars.append({"native_index": i, "name": identifier, "kind_code": kind, "bound_type_code": bound_type,
                "lower": observation(lo), "upper": observation(hi), "optlang_position": opt_position,
                "optlang_lower": observation(variable.lb), "optlang_upper": observation(variable.ub), "optlang_type": variable.type,
                "lower_qualification": lower["kind"], "upper_qualification": upper["kind"]})
            variables.append({"position": i - 1, "native_index": i, "optlang_position": opt_position, "id": identifier,
                "kind": {glp.GLP_CV: "continuous", glp.GLP_IV: "integer", glp.GLP_BV: "binary"}.get(kind, "unknown"),
                "native_kind_code": kind, "native_bound_type_code": bound_type, "lower": lower, "upper": upper,
                "unit": unknown_unit(), "source": location("effective_problem", pointer)})
        except Exception as error:
            failures.append(exception(error, "capture", f"native_column/{i}"))
            problems.append(issue("variable_identity_conflict", "capture", pointer, variable_position=i - 1))
    indices, coefficients = glp.intArray(cols + 1), glp.doubleArray(cols + 1)
    for i in range(1, rows + 1):
        pointer = f"{base}/constraints/{len(constraints)}"
        try:
            identifier = glp.glp_get_row_name(problem, i)
            opt_position, constraint = opt_rows[identifier]
            require(constraint._index == i, "constraint_identity_conflict")
            bound_type, lo, hi = glp.glp_get_row_type(problem, i), glp.glp_get_row_lb(problem, i), glp.glp_get_row_ub(problem, i)
            lower, upper = _native_bounds(bound_type, lo, hi, role="effective_problem", pointer=pointer)
            nnz = glp.glp_get_mat_row(problem, i, indices, coefficients)
            native_entries = [{"column_index": indices[j], "coefficient": observation(coefficients[j])} for j in range(1, nnz + 1)]
            terms = []
            for entry in sorted(native_entries, key=lambda e: e["column_index"]):
                require(1 <= entry["column_index"] <= cols, "variable_identity_conflict")
                terms.append({"variable_position": entry["column_index"] - 1,
                    "coefficient": _number_observed(entry["coefficient"], role="effective_problem", pointer=f"{pointer}/terms/{len(terms)}/coefficient/value")})
            raw_rows.append({"native_index": i, "name": identifier, "bound_type_code": bound_type,
                             "lower": observation(lo), "upper": observation(hi), "nnz": nnz, "entries": native_entries,
                             "lower_qualification": lower["kind"], "upper_qualification": upper["kind"]})
            met_position = met_constraints.get(constraint)
            constraints.append({"position": i - 1, "native_index": i, "optlang_position": opt_position, "id": identifier,
                "kind": "metabolite_balance" if met_position is not None else "additional_linear", "metabolite_position": met_position,
                "constant": number(0, role="effective_problem", pointer=pointer + "/constant/value"), "terms": terms, "terms_complete": True,
                "lower": lower, "upper": upper, "native_bound_type_code": bound_type, "indicator_variable_position": None,
                "active_when": None, "expression_kind": "linear" if constraint.is_Linear else "nonlinear",
                "native_expression_pointer": f"{base}/native_optlang_json/constraints/{opt_position}/expression" if native_json is not None else
                    f"{base}/native_capture_evidence/native_rows/{len(raw_rows)-1}/entries",
                "unit": unknown_unit(), "source": location("effective_problem", pointer)})
        except Exception as error:
            failures.append(exception(error, "capture", f"native_row/{i}"))
            problems.append(issue("constraint_unavailable", "capture", pointer, constraint_position=i - 1))
    objective_ptr = base + "/objective"
    objective_terms, complete = [], True
    for i in range(1, cols + 1):
        try:
            coefficient = glp.glp_get_obj_coef(problem, i)
            if coefficient != 0:
                objective_terms.append({"variable_position": i - 1, "coefficient": number(coefficient, role="effective_problem",
                    pointer=f"{objective_ptr}/terms/{len(objective_terms)}/coefficient/value")})
        except Exception as error:
            complete = False
            failures.append(exception(error, "capture", f"objective_coefficient/{i}"))
    linear = solver.objective.is_Linear
    symbolic_constant = parse_optimization_expression(solver.objective, linear=False)[0] if linear else None
    direction = glp.glp_get_obj_dir(problem)
    objective = {"direction": {glp.GLP_MIN: "min", glp.GLP_MAX: "max"}.get(direction, "unknown"), "native_direction_code": direction,
        "native_constant": number(glp.glp_get_obj_coef(problem, 0), role="effective_problem", pointer=objective_ptr + "/native_constant/value"),
        "interface_offset": number(solver._objective_offset, role="effective_problem", pointer=objective_ptr + "/interface_offset/value"),
        "symbolic_constant": number(symbolic_constant, role="effective_problem", pointer=objective_ptr + "/symbolic_constant/value"),
        "terms": objective_terms, "terms_complete": complete, "expression_kind": "linear" if linear else "nonlinear",
        "native_expression_pointer": base + "/native_optlang_json/objective/expression" if native_json is not None else objective_ptr + "/terms",
        "unit": unknown_unit(), "source": location("effective_problem", objective_ptr)}
    native_positions = {row["id"]: row["position"] for row in variables}
    for i, rxn in enumerate(model.reactions):
        try:
            forward, reverse = rxn.forward_variable, rxn.reverse_variable
            expressions.append({"reaction_position": i, "reaction_id": rxn.id, "expression": expr_to_json(rxn.flux_expression)})
            joins.append({"reaction_position": i, "reaction_id": rxn.id, "forward_variable_position": native_positions[forward.name],
                          "forward_variable_id": forward.name, "reverse_variable_position": native_positions[reverse.name],
                          "reverse_variable_id": reverse.name,
                          "flux_expression_pointer": f"{base}/native_capture_evidence/reaction_flux_expressions/{len(expressions)-1}/expression"})
        except Exception as error:
            failures.append(exception(error, "capture", f"reaction_variables/{i}"))
            problems.append(issue("flux_identity_conflict", "capture", f"{base}/reaction_variables", reaction_position=i))
    text = {"native_lp_text": None, "native_glpk_text": None}
    scratch = _context(model).get("scratch_directory") or os.environ.get("TMPDIR")
    require(scratch is not None, "fba_bounded_temporary_directory_required")
    directory(scratch)
    for key, writer in (("native_lp_text", glp.glp_write_lp), ("native_glpk_text", glp.glp_write_prob)):
        try:
            with tempfile.NamedTemporaryFile(dir=scratch, prefix="fba-native-", suffix=".txt") as temporary:
                rc = writer(problem, None if key == "native_lp_text" else 0, temporary.name)
                require(rc == 0, "artifact_missing")
                text[key] = read_bytes(temporary.name).decode("utf-8")
        except Exception as error:
            failures.append(exception(error, "capture", key))
    representation = "complete_continuous_linear" if all(r["kind"] == "continuous" for r in variables) else "complete_mixed_integer_linear"
    if problems or not complete:
        representation = "partial"
    elif not linear or any(row["expression_kind"] != "linear" for row in constraints):
        representation = "unsupported"
    return {"version": "cobra_glpk_problem_snapshot_v1", "phase": phase, "variable_count": cols, "constraint_count": rows,
        "variables": variables, "constraints": constraints, "objective": objective, "reaction_variables": joins,
        "representation": representation, "native_optlang_json": native_json, **text, "issues": problems,
        "native_capture_evidence": {"version": "cobra_glpk_problem_evidence_v1", "native_variables": raw_vars, "native_rows": raw_rows,
            "reaction_flux_expressions": expressions, "configuration": {"integer_controls": _controls(solver.configuration._iocp, failures, "integer_controls")},
            "capture_failures": failures}}


def _safe_get(call, failures, operation):
    try:
        return call()
    except Exception as error:
        failures.append(exception(error, "capture", operation))
        return None


def _raw_point(model):
    import swiglpk as glp
    problem, failures = model.solver.problem, []
    def get(name, *args):
        return _safe_get(lambda: getattr(glp, name)(problem, *args), failures, name + ("/" + str(args[0]) if args else ""))
    cols, rows = get("glp_get_num_cols"), get("glp_get_num_rows")
    variables, constraints = [], []
    for i in range(1, (cols or 0) + 1):
        variables.append({"native_index": i, "id": get("glp_get_col_name", i), "kind_code": get("glp_get_col_kind", i),
                          "primal": observation(get("glp_get_col_prim", i)), "reduced_cost": observation(get("glp_get_col_dual", i))})
    for i in range(1, (rows or 0) + 1):
        constraints.append({"native_index": i, "id": get("glp_get_row_name", i), "activity": observation(get("glp_get_row_prim", i)),
                            "shadow_price": observation(get("glp_get_row_dual", i))})
    structure = _safe_get(lambda: digest(_native_structure(model)), failures, "native_problem_identity")
    return {"variable_count": cols, "constraint_count": rows, "variables": variables, "constraints": constraints,
        "glpk_status_code": get("glp_get_status"), "glpk_primal_status_code": get("glp_get_prim_stat"),
        "glpk_dual_status_code": get("glp_get_dual_stat"), "glpk_objective": observation(get("glp_get_obj_val")),
        "optlang_objective": observation(_safe_get(lambda: model.solver.objective.value, failures, "optlang_objective")),
        "problem_identity": structure, "capture_failures": failures}


def _established_return(return_code, primal_status, status=None, dual_status=None):
    """008's native source predicate; this is point custody, not feasibility."""
    if type(return_code) is not int or type(primal_status) is not int:
        return False
    if status is not None and (type(status) is not int or status not in {1, 2, 3, 4, 5, 6}):
        return False
    if dual_status is not None and (type(dual_status) is not int or dual_status not in {1, 2, 3, 4}):
        return False
    valid = (return_code == 0 and primal_status in {2, 3, 4}) or (return_code in {6, 7, 8, 9} and primal_status in {2, 3})
    if not valid:
        return False
    if status is not None:
        permitted = {2, 5, 6} if primal_status == 2 else {primal_status}
        if status not in permitted:
            return False
        if dual_status is not None and primal_status == 2:
            expected = 5 if dual_status == 2 else 6 if dual_status == 4 else 2 if dual_status in {1, 3} else None
            if status != expected:
                return False
    if return_code in {6, 7} and dual_status is not None and dual_status != 2:
        return False
    return True


@contextmanager
def _observe_native_passes(model, effective_problem_sha256):
    import optlang.glpk_interface as interface
    original_problem = model.solver.problem
    original_identity = digest(_native_structure(model))
    events = []
    originals = {name: getattr(interface, name) for name in ("glp_simplex", "glp_intopt")}
    def wrap(name):
        def observe(problem, controls):
            position = len(events)
            failures = []
            parameters = _safe_get(lambda: _controls(controls, failures, name + "/parameters"), failures, name + "/parameters")
            before = _safe_get(lambda: digest(_native_structure(model)), failures, "native_problem_identity_before")
            event = {"typed": {"position": position, "routine": name, "return_code": None, "raw_status_code": None,
                "primal_status_code": None, "dual_status_code": None,
                "parameters_pointer": f"/native_capture_evidence/native_passes/{position}/parameters", "exception_pointer": None},
                "evidence": {"parameters": parameters, "exception": None, "effective_problem_sha256": effective_problem_sha256,
                    "raw_status_after": {"entered": True, "returned": False, "same_original_problem": problem is original_problem,
                        "problem_identity_before": before, "original_problem_identity": original_identity}, "raw_getters": None}}
            events.append(event)
            try:
                result = originals[name](problem, controls)
            except BaseException as error:
                event["evidence"]["exception"] = exception(error, "solve", name)
                event["typed"]["exception_pointer"] = f"/native_capture_evidence/native_passes/{position}/exception"
                raise
            else:
                event["typed"]["return_code"] = result
                event["evidence"]["raw_status_after"]["returned"] = True
                return result
            finally:
                raw = _safe_get(lambda: _raw_point(model), failures, name + "/raw_getters")
                event["evidence"]["raw_getters"] = raw
                if raw is not None:
                    event["typed"].update(raw_status_code=raw["glpk_status_code"], primal_status_code=raw["glpk_primal_status_code"], dual_status_code=raw["glpk_dual_status_code"])
                event["evidence"]["raw_status_after"].update(return_code=event["typed"]["return_code"],
                    raw_status_code=event["typed"]["raw_status_code"], primal_status_code=event["typed"]["primal_status_code"],
                    dual_status_code=event["typed"]["dual_status_code"], capture_failures=failures)
        return observe
    try:
        for name in originals:
            setattr(interface, name, wrap(name))
        yield events
    finally:
        for name, original in originals.items():
            setattr(interface, name, original)


def _point_unchanged(previous, final):
    if previous is None or final is None or previous["problem_identity"] is None or previous["problem_identity"] != final["problem_identity"]:
        return False
    for key in ("variable_count", "constraint_count", "glpk_status_code", "glpk_primal_status_code", "glpk_dual_status_code"):
        if previous[key] is not None and final[key] is not None and previous[key] != final[key]:
            return False
    for axis, fields in (("variables", ("primal", "reduced_cost")), ("constraints", ("activity", "shadow_price"))):
        if len(previous[axis]) != len(final[axis]):
            return False
        for before, after in zip(previous[axis], final[axis]):
            if before["native_index"] != after["native_index"]:
                return False
            if _name(before["id"]) is not None and _name(after["id"]) is not None and before["id"] != after["id"]:
                return False
            for field in fields:
                if before[field]["state"] == "present" and after[field]["state"] == "present" and before[field] != after[field]:
                    return False
    for field in ("glpk_objective", "optlang_objective"):
        if previous[field]["state"] == "present" and final[field]["state"] == "present" and previous[field] != final[field]:
            return False
    return True


def _series(series, failures, name):
    if series is None:
        return None
    return _safe_get(lambda: [{"position": i, "id": str(identifier), "value": observation(value)}
        for i, (identifier, value) in enumerate(series.items())], failures, name)


def _request_application(job):
    prefix = "/requested_job/native_flux_balance"
    changes = []
    for i, row in enumerate(job["constraints"] or []):
        changes.append({"reaction_id": row["reaction_id"],
            "requested_lower": deepcopy(row["lower"]) | {"source": location("selected_request", f"{prefix}/constraints/{i}/lower")},
            "requested_upper": deepcopy(row["upper"]) | {"source": location("selected_request", f"{prefix}/constraints/{i}/upper")},
            "effective_reaction_position": None, "application": "not_attempted", "issue_code": None})
    return {"version": "cobra_fba_request_application_v1", "selected_request": location("selected_request", "/requested_job"),
        "constraint_changes": changes, "objective_request": deepcopy(job["objective"]), "objective_application": "not_attempted",
        "objective_requested_source": location("selected_request", prefix + "/objective"), "objective_effective_source": None,
        "solver_option_applications": [{"name": key, "application": "not_requested" if job["solver_options"][key] is None else "not_attempted",
            "requested_source": location("selected_request", prefix + "/solver_options/" + key), "effective_source": None, "issue_code": None}
            for key in ("feasibility_tolerance", "optimality_tolerance", "integrality_tolerance")],
        "request_realization": "unknown", "issues": []}


def _bound_operand(record):
    require(record["kind"] in {"finite", "negative_infinity", "positive_infinity"}, "bound_invalid")
    return record["value"] if record["kind"] == "finite" else -math.inf if record["kind"] == "negative_infinity" else math.inf


def _apply_request(model, job, application, diagnostics):
    """Validate all selections first; retain partial setters without rollback."""
    positions = {r.id: i for i, r in enumerate(model.reactions)}
    errors = application["issues"]
    for i, change in enumerate(application["constraint_changes"]):
        change["effective_reaction_position"] = positions.get(change["reaction_id"])
        code = None
        if change["reaction_id"] not in positions:
            code = "reaction_id_unknown"
        else:
            try:
                lo, hi = _bound_operand(change["requested_lower"]), _bound_operand(change["requested_upper"])
                require(lo != math.inf and hi != -math.inf and lo <= hi, "bound_invalid")
            except (ValueError, OverflowError):
                code = "bound_invalid"
        if code:
            change.update(application="rejected", issue_code=code)
            errors.append(issue(code, "apply", f"/constraint_changes/{i}"))
    if job["objective"]["kind"] == "single_reaction" and job["objective"]["reaction_id"] not in positions:
        application["objective_application"] = "rejected"
        errors.append(issue("objective_rejected", "apply", "/objective_request"))
    for row in application["solver_option_applications"]:
        requested = job["solver_options"][row["name"]]
        if requested is None:
            continue
        try:
            valid = type(requested) in {int, float} and math.isfinite(float(requested)) and 0 < float(requested) < 1
        except (OverflowError, ValueError):
            valid = False
        if row["name"] == "optimality_tolerance" or not valid:
            row.update(application="rejected", issue_code="solver_option_unsupported")
            errors.append(issue("solver_option_unsupported", "apply", "/solver_options/" + row["name"]))
    source = _context(model).get("source_information", {})
    selected_ids = {r["reaction_id"] for r in application["constraint_changes"]}
    if source.get("unsupported") or any(d["severity"] >= 2 for d in _context(model).get("loader_diagnostics", [])):
        errors.append(issue("source_semantics_unsupported", "load", "/source_feature_audit"))
    if source.get("missing_bounds", set()) - selected_ids:
        errors.append(issue("loader_default_applied", "load", "/source_feature_audit"))
    if source.get("missing_objective") and job["objective"]["kind"] == "model_default":
        errors.append(issue("objective_unavailable", "load", "/source_feature_audit"))
    if errors:
        application["request_realization"] = "mismatch"
        return False
    for i, change in enumerate(application["constraint_changes"]):
        try:
            reaction = model.reactions.get_by_id(change["reaction_id"])
            selected = (_bound_operand(change["requested_lower"]), _bound_operand(change["requested_upper"]))
            reaction.bounds = selected
            require(reaction.bounds == selected, "request_effective_mismatch")
            change["application"] = "applied"
        except Exception as error:
            diagnostics["exceptions"].append(exception(error, "apply", f"constraints/{i}"))
            change.update(application="rejected", issue_code="constraint_rejected")
            errors.append(issue("constraint_rejected", "apply", f"/constraint_changes/{i}"))
            application["request_realization"] = "mismatch"
            return False
    try:
        if job["objective"]["kind"] == "single_reaction":
            model.objective = job["objective"]["reaction_id"]
            application["objective_application"] = "applied"
        else:
            application["objective_application"] = "model_default"
    except Exception as error:
        diagnostics["exceptions"].append(exception(error, "apply", "objective"))
        application["objective_application"] = "rejected"
        errors.append(issue("objective_rejected", "apply", "/objective_request"))
        application["request_realization"] = "mismatch"
        return False
    for row in application["solver_option_applications"]:
        value = job["solver_options"][row["name"]]
        if value is None:
            continue
        try:
            field = row["name"].removesuffix("_tolerance")
            setattr(model.solver.configuration.tolerances, field, value)
            require(getattr(model.solver.configuration.tolerances, field) == float(value), "request_effective_mismatch")
            row["application"] = "applied"
        except Exception as error:
            diagnostics["exceptions"].append(exception(error, "apply", "solver_options/" + row["name"]))
            row.update(application="rejected", issue_code="solver_option_unsupported")
            errors.append(issue("solver_option_unsupported", "apply", "/solver_options/" + row["name"]))
            application["request_realization"] = "mismatch"
            return False
    return True


def _confirm_application(application, model_payload, problem_payload):
    """Only affirm outcomes with the emitted readbacks available to the reader."""
    effective = problem_payload.get("effective")
    if effective is None or model_payload.get("effective") is None:
        application["request_realization"] = "unknown"
        return False
    application["objective_effective_source"] = location("effective_problem", "/effective/objective")
    configuration = problem_payload.get("configuration_before_solve")
    if configuration is not None:
        for row in application["solver_option_applications"]:
            row["effective_source"] = location("effective_problem", "/configuration_before_solve/" + row["name"])
    if application["issues"]:
        return False
    if effective["representation"] != "complete_continuous_linear":
        application["issues"].append(issue("unsupported_problem_form", "apply", "/effective/representation"))
        application["request_realization"] = "mismatch"
        return False
    # Setters were read back above. Exact sparse identity is available to the
    # independent reader; no scientific residual or confidence is computed here.
    application["request_realization"] = "exact" if configuration is not None else "unknown"
    return configuration is not None


def capture_cobra_glpk_solution(model, solution, *, optimize_call_count, native_passes, diagnostics):
    failures, problems = [], []
    raw = _raw_point(model)
    returned = None
    if solution is not None:
        returned = {"status": _safe_get(lambda: solution.status, failures, "solution.status"),
            "objective": observation(_safe_get(lambda: solution.objective_value, failures, "solution.objective_value")),
            **{field: _series(_safe_get(lambda: getattr(solution, field), failures, "solution." + field), failures, field)
               for field in ("fluxes", "reduced_costs", "shadow_prices")}}
    last = native_passes[-1] if native_passes else None
    established = False
    if optimize_call_count == 1 and last is not None:
        typed, evidence = last["typed"], last["evidence"]
        state = evidence["raw_status_after"]
        point = evidence["raw_getters"]
        established = (typed["routine"] == "glp_simplex" and state.get("returned") is True
            and state.get("same_original_problem") is True and state.get("problem_identity_before") == state.get("original_problem_identity")
            and point is not None and point["problem_identity"] == state.get("original_problem_identity")
            and all(r["kind_code"] == 1 for r in raw["variables"])
            and _established_return(typed["return_code"], typed["primal_status_code"], typed["raw_status_code"], typed["dual_status_code"])
            and _point_unchanged(point, raw))
    reason = "primal_not_established" if optimize_call_count else "not_executed"
    if not established:
        problems.append(issue("primal_not_established", "capture", "/point_state"))
    variables, constraints, reactions = [], [], []
    def candidate(value, pointer):
        result = _number_observed(value, role="solution", pointer=pointer, established=established, missing_reason=reason)
        if established and result["state"] in {"missing", "nonfinite"}:
            problems.append(issue("variable_nonfinite" if result["state"] == "nonfinite" else "variable_missing", "capture", pointer))
        return result
    for i, row in enumerate(raw["variables"]):
        if _name(row["id"]) is None:
            problems.append(issue("variable_identity_conflict", "capture",
                f"/native_capture_evidence/raw_getters/variables/{i}/id", variable_position=row["native_index"] - 1))
            continue
        pointer = f"/variable_values/{len(variables)}"
        variables.append({"variable_position": row["native_index"] - 1, "variable_id": row["id"],
            "primal": candidate(row["primal"], pointer + "/primal/value"),
            "reduced_cost": candidate(row["reduced_cost"], pointer + "/reduced_cost/value")})
    for i, row in enumerate(raw["constraints"]):
        if _name(row["id"]) is None:
            problems.append(issue("constraint_identity_conflict", "capture",
                f"/native_capture_evidence/raw_getters/constraints/{i}/id", constraint_position=row["native_index"] - 1))
            continue
        pointer = f"/constraint_values/{len(constraints)}"
        constraints.append({"constraint_position": row["native_index"] - 1, "constraint_id": row["id"],
            "activity": candidate(row["activity"], pointer + "/activity/value"),
            "shadow_price": candidate(row["shadow_price"], pointer + "/shadow_price/value")})
    for i, rxn in enumerate(model.reactions):
        values = {}
        for field in ("fluxes", "reduced_costs"):
            matched = [r for r in (returned.get(field) or []) if r["id"] == rxn.id] if returned else []
            values[field] = matched[0]["value"] if len(matched) == 1 else None
            if len(matched) > 1:
                problems.append(issue("flux_identity_conflict", "capture", "/native_capture_evidence/cobra_return/" + field, reaction_position=i))
        reactions.append({"reaction_position": i, "reaction_id": rxn.id,
            "flux": candidate(values["fluxes"], f"/reaction_values/{i}/flux/value"),
            "reduced_cost": candidate(values["reduced_costs"], f"/reaction_values/{i}/reduced_cost/value")})
    config = _safe_get(lambda: capture_cobra_glpk_configuration(model, role="solution", pointer="/configuration_after_solve"), failures, "configuration_after_solve")
    controls = _safe_get(lambda: _controls(model.solver.configuration._iocp, failures, "integer_controls_after_solve"), failures, "integer_controls_after_solve")
    return {"version": "cobra_glpk_solution_capture_v1", "model_optimize_call_count": optimize_call_count,
        "native_passes": [deepcopy(event["typed"]) for event in native_passes],
        "solution_object_state": "returned" if solution is not None else "not_returned" if optimize_call_count else "not_executed",
        "optlang_status": _safe_get(lambda: model.solver.status, failures, "optlang.status"),
        "cobra_solution_status": returned["status"] if returned else None,
        "glpk_status_code": raw["glpk_status_code"], "glpk_primal_status_code": raw["glpk_primal_status_code"],
        "glpk_dual_status_code": raw["glpk_dual_status_code"], "point_state": "basic_solution" if established else "not_established",
        "native_glpk_objective": candidate(raw["glpk_objective"], "/native_glpk_objective/value"),
        "native_optlang_objective": candidate(raw["optlang_objective"], "/native_optlang_objective/value"),
        "native_cobra_objective": candidate(returned["objective"] if returned else None, "/native_cobra_objective/value"),
        "variable_values": variables, "constraint_values": constraints, "reaction_values": reactions,
        "configuration_after_solve": config, "diagnostics_pointer": "/native_capture_evidence/diagnostics", "issues": problems,
        "native_capture_evidence": {"version": "cobra_glpk_solution_evidence_v1", "native_passes": [deepcopy(e["evidence"]) for e in native_passes],
            "configuration_after_solve": {"integer_controls": controls}, "raw_getters": raw, "cobra_return": returned,
            "diagnostics": {"warnings": deepcopy(diagnostics["warnings"]), "logging": deepcopy(diagnostics["logging"]),
                            "exceptions": deepcopy(diagnostics["exceptions"]) + failures}}}
