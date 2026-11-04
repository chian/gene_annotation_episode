"""Source-supported scientific identities for the existing A110 operands.

Private keys align operands; they are never scientific labels. Missing meanings
add no numerical gate. Distinct unknown handles assert no chemical identity or
independent evidence. This helper does not add a score or numerical formula.
"""
from copy import deepcopy

from .domain import identity
from .literature_assay_inputs import _fail, _keys

INPUT_VERSION = "a110_reaction_inputs_v2"
DATA_VERSION = "a110_source_reaction_measurements_v2"
RECORD_VERSION = "literature_reaction_record_v3"
NAMESPACE = "literature_reaction_semantic_cells"
BASES = ("source_reported", "source_supported_inference", "conditional_assumption", "unresolved")
MODEL_FIELDS = {"definition": "reference", "reaction": "term", "function_relation": "term",
                "prediction_evidence": "reference"}
RESOURCE_FIELDS = {"definition": "reference", "entity": "term", "property": "term",
    "biological_setting": "context", "compartment": "context", "period": "context",
    "supply_evidence": "reference", "coefficient_evidence": "reference"}
DEMAND_FIELDS = {"definition": "reference", "process": "term", "biological_setting": "context",
                 "compartment": "context", "period": "context", "evidence": "reference"}


def _meaning(entry, fields, bases, sources, path):
    _keys(entry, (*fields, *bases), path)
    result = {field: None if entry[field] is None else sources.witness(entry[field], path + "." + field)
              for field in fields}
    for basis in bases:
        if not isinstance(entry[basis], str) or entry[basis] not in BASES:
            _fail("unsupported_interpretation_basis", path + "." + basis)
        result[basis] = entry[basis]
    return result


def _roster(entries, roster, key, fields, bases, sources, path):
    if not isinstance(entries, list) or len(entries) != len(roster):
        _fail("reaction_meaning_roster_mismatch", path)
    by_key = {}
    for index, entry in enumerate(entries):
        location = f"{path}[{index}]"
        _keys(entry, (key, *fields, *bases), location)
        name = entry[key]
        if not isinstance(name, str) or name in by_key:
            _fail("reaction_meaning_roster_mismatch", location + "." + key)
        by_key[name] = {key: name, **_meaning({k: v for k, v in entry.items() if k != key},
            fields, bases, sources, location)}
    if set(by_key) != {row[key] for row in roster}:
        _fail("reaction_meaning_roster_mismatch", path)
    return [by_key[row[key]] for row in roster]


def read_meanings(value, raw, sources):
    """Read actual selected witness sources and align exact raw operand rosters."""
    _keys(value, ("ratio", "budget"), "meanings")
    result = {}
    for kind in ("ratio", "budget"):
        if raw[kind] is None:
            if value[kind] is not None:
                _fail("reaction_meaning_roster_mismatch", "meanings." + kind)
            result[kind] = None
            continue
        entry = value[kind]
        if kind == "ratio":
            _keys(entry, ("claim", "alternatives"), "meanings.ratio")
            result[kind] = {"claim": _meaning(entry["claim"], MODEL_FIELDS,
                ("prediction_basis",), sources, "meanings.ratio.claim"),
                "alternatives": _roster(entry["alternatives"], raw[kind]["alternatives"], "key",
                    MODEL_FIELDS, ("prediction_basis",), sources, "meanings.ratio.alternatives")}
        else:
            _keys(entry, ("resources", "demand"), "meanings.budget")
            result[kind] = {"resources": _roster(entry["resources"], raw[kind]["resources"],
                "resource_key", RESOURCE_FIELDS, ("supply_basis", "coefficient_basis"),
                sources, "meanings.budget.resources"),
                "demand": _meaning(entry["demand"], DEMAND_FIELDS, ("demand_basis",),
                    sources, "meanings.budget.demand")}
    return result


def _entries(meanings):
    ratio, budget = meanings["ratio"], meanings["budget"]
    if ratio is not None:
        yield "model", "claim", None, ratio["claim"], MODEL_FIELDS, ("prediction_basis",)
        for row in ratio["alternatives"]:
            yield "model", "alternative", row["key"], row, MODEL_FIELDS, ("prediction_basis",)
    if budget is not None:
        yield "demand", "demand", None, budget["demand"], DEMAND_FIELDS, ("demand_basis",)
        for row in budget["resources"]:
            yield "resource", "resource", row["resource_key"], row, RESOURCE_FIELDS, ("supply_basis", "coefficient_basis")


def direct_references(extraction, initial):
    refs = list(initial)
    if extraction.get("version") == INPUT_VERSION:
        for _, _, _, entry, fields, _ in _entries(extraction["meanings"]):
            refs.extend(entry[field]["source_ref"] for field in fields if entry[field] is not None)
    return list(dict.fromkeys(refs))


def publish_meanings(extraction, publish):
    """Create anchored facts and scoped handles, without scientific inference."""
    result = {"models": [], "resources": [], "demand": None}
    data_ref = extraction["arguments"]["data_source_ref"]
    for kind, role, key, entry, fields, bases in _entries(extraction["meanings"]):
        scoped = {"data_source_ref": data_ref, "kind": kind, "role": role, "key": key}
        row = {basis: entry[basis] for basis in bases}
        if kind == "model":
            row["role"] = role
        terms, contexts = [], []
        for field, namespace in fields.items():
            if field == "definition":
                continue
            witness = entry[field]
            if witness is None:
                row[field + "_ref"] = None
                continue
            anchor = {k: witness[k] for k in ("source_ref", "artifact_ref", "start", "end", "quote")}
            common = {"source_ref": witness["source_ref"], "anchor": anchor}
            accession = identity("reaction_literal", {**scoped, "field": field, **anchor})
            if namespace == "term":
                record = {**common, "namespace": "literature_reaction_" + field,
                    "accession": accession, "label": witness["quote"], "term_type": "other"}
            elif namespace == "context":
                record = {**common, "context_type": "assay_condition", "name": witness["quote"],
                          "attributes": [], "related_refs": []}
            else:
                record = {**common, "reference_type": "literature_result", "accession": accession,
                    "label": witness["quote"], "sequence_ref": None, "molecule": None,
                    "length": None, "term_refs": [], "context_refs": []}
            reference = publish(namespace, record)
            row[field + "_ref"] = reference
            if namespace == "term": terms.append(reference)
            if namespace == "context": contexts.append(reference)
        witness = entry["definition"]
        anchor = None if witness is None else {k: witness[k] for k in (
            "source_ref", "artifact_ref", "start", "end", "quote")}
        row[kind + "_ref"] = publish("reference", {
            "reference_type": "literature_result", "source_ref": data_ref if witness is None else witness["source_ref"],
            "accession": identity("reaction_literal", {**scoped, "field": "definition"}),
            "label": "Unreported " + kind + " definition" if witness is None else witness["quote"],
            "sequence_ref": None, "molecule": None, "length": None,
            "term_refs": list(dict.fromkeys(terms)), "context_refs": list(dict.fromkeys(contexts)), "anchor": anchor})
        row["definition_reported"] = witness is not None
        if kind == "demand": result["demand"] = row
        else: result["models" if kind == "model" else "resources"].append(row)
    return result


def semantic_metadata(metadata, bindings, inputs, sheet):
    result = deepcopy(metadata)
    ratio, budget = inputs["ratio"], inputs["budget"]
    predictions = [] if ratio is None else [ratio["claim"], *(r["prediction"] for r in ratio["alternatives"])]
    result["model_definitions"] = [{**deepcopy(row), "prediction": prediction,
        "unit": ratio["unit"]} for row, prediction in zip(bindings["models"], predictions)]
    result["comparison_member_refs"] = [row["model_ref"] for row in bindings["models"] if row["role"] == "alternative"]
    result["comparison_reduction"] = "minimum_over_declared_alternatives"
    result["resource_definitions"] = []
    if budget is not None:
        for row, operand in zip(bindings["resources"], budget["resources"]):
            result["resource_definitions"].append({**deepcopy(row), "coefficient": operand["coefficient"],
                "coefficient_role": "resource_unit_per_demand_unit",
                "coefficient_demand_ref": bindings["demand"]["demand_ref"]})
    result["demand_definition"] = (None if budget is None else {**deepcopy(bindings["demand"]),
        "value": budget["demand"], "unit": budget["unit"]})
    resources = {} if budget is None else {operand["resource_key"]: row["resource_ref"]
        for operand, row in zip(budget["resources"], bindings["resources"])}
    result["nominal_limiting_resource_refs"] = [resources[key]
        for key in sheet["budget_details"]["limiting_resource_keys"]]
    return result


def binding_references(bindings):
    return list(dict.fromkeys(value for group in (bindings["models"], bindings["resources"],
        [bindings["demand"]] if bindings["demand"] is not None else []) for row in group
        for field, value in row.items() if field.endswith("_ref") and value is not None))
