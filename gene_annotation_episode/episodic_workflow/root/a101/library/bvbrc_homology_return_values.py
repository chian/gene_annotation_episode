"""Pure requested Homology values; the custody host authenticates publication ownership."""
from __future__ import annotations

from copy import deepcopy
import re
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import _finite_json
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import _Validator
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import contract_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a101.bvbrc_appservice_publication import RESULT_VERSION
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import _same

FACT_SOURCES = (
    "bvbrc_homology_measurements",
    "bvbrc_homology_function_weights",
    "bvbrc_homology_requirements",
)

IDENTIFIER_NAMESPACES = (
    "bvbrc_homology_field", "bvbrc_homology_function",
    "bvbrc_homology_requirement", "bvbrc_homology_role", "bvbrc_homology_reason",
)

_DISTRIBUTIONS = {"conditional_function_weights", "representation_adjusted_function_weights"}

_SOURCE_ID = re.compile(r"source_[a-f0-9]{24,64}\Z")

_PREFIX = "bvbrc_homology_return_"

def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}

def _identifier(namespace, *, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "format": "identifier",
            "x-reference-namespace": namespace}

def homology_fact_sources():
    """Closed report declarations; every semantic identifier needs resolution."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
    field = _identifier("bvbrc_homology_field")
    weight = _object({"function": _identifier("bvbrc_homology_function"),
                      "weight": {"type": "number", "minimum": 0, "maximum": 1}})
    kinds = contract_schema("AcquisitionRequirement")["$defs"]["AcquisitionRequirement"]["properties"]["kind"]["enum"]
    requirement = _object({
        "requirement_id": _identifier("bvbrc_homology_requirement"),
        "kind": {"type": "string", "enum": kinds},
        "role": _identifier("bvbrc_homology_role", nullable=True),
        "source_refs": {"type": "array", "uniqueItems": True, "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "source"}},
        "reason_code": _identifier("bvbrc_homology_reason"),
    })
    rows = (
        _object({"source_ref": source, "field": field, "value": {"type": ["number", "null"]}}),
        _object({"source_ref": source, "field": field,
                 "weights": {"type": ["array", "null"], "items": weight}}),
        _object({"source_ref": source, "field": field,
                 "requirements": {"type": "array", "items": requirement}}),
    )
    meanings = (
        "Saved requested Homology scalar measurements; original field selectors retain the quantity, population, units and missing-input meaning.",
        "Saved requested conditional function weights and their exact source-derived function labels; these are not calibrated annotation probabilities. Null and an empty candidate population differ.",
        "Only the explicitly requested saved missing_requirements projection; source identities and requirement meanings retain their original associations.",
    )
    return deepcopy({name: {"type": "array", "meaning": meaning,
        "report_schema": {"type": "array", "items": row, "x-source": name}}
        for name, row, meaning in zip(FACT_SOURCES, rows, meanings)})

def requested_sources(schema):
    return tuple(dict.fromkeys(node["x-source"] for node in plain(schema).get("properties", {}).values()
        if node.get("x-source") in FACT_SOURCES))

def _require(condition, code):
    if not condition:
        raise ValueError(_PREFIX + code)

def _saved_facts(body):
    """Validate saved return associations, without importing a scientific grader.

    Hashes, native/source relationships and completed-action custody are checked
    by AppServicePublications.read before this supplied-value projection.
    """
    _require(type(body) is dict and body.get("version") == RESULT_VERSION, "publication_required")
    source = body.get("source_ref")
    _require(type(source) is str and _SOURCE_ID.fullmatch(source) is not None
        and body.get("reference") == source, "result_source_conflict")
    publication, inputs = body.get("publication"), body.get("publication_inputs")
    _require(type(publication) is dict and type(inputs) is dict, "publication_required")
    _require(publication.get("bundle_content", {}).get("source_ref") == source
        and source in publication.get("result_record_refs", [])
        and source in body.get("record_refs", []), "result_source_conflict")
    saved = validate_contract("AdapterResult", publication.get("adapter_result"))
    _require(saved["adapter_id"] == "bvbrc_homology" and saved["adapter_version"] == "1",
        "homology_adapter_required")
    selector = inputs.get("selector")
    _require(type(selector) is dict and type(selector.get("adapter")) is dict
        and all(selector["adapter"].get(key) == saved[key] for key in ("adapter_id", "adapter_version"))
        and _same(inputs.get("adapter"), selector["adapter"]),
        "original_adapter_conflict")
    schema = selector.get("requested_schema")
    _finite_json(schema)
    _require(type(schema) is dict and schema.get("type") == "object"
        and schema.get("additionalProperties") is False and type(schema.get("properties")) is dict,
        "requested_schema_invalid")
    properties, required = schema["properties"], schema.get("required")
    _require(type(required) is list and all(type(name) is str for name in required)
        and len(required) == len(set(required)) and set(required) == set(properties), "requested_schema_invalid")
    facts = saved["facts"]
    _require(set(facts) <= set(properties), "unrequested_saved_fact")
    if saved["status"] in {"ok", "partial"}:
        _require(set(facts) == set(properties), "requested_saved_fact_missing")
    rows = {name: [] for name in FACT_SOURCES}
    for field, node in properties.items():
        if field not in facts:
            continue  # A failed adapter's absent cell is not a fabricated null.
        _require(type(field) is str and bool(field.strip()) and type(node) is dict,
            "requested_field_invalid")
        selection = node.get("x-homology-fact")
        _require(type(selection) is dict and type(selection.get("metric")) is str,
            "original_fact_selector_required")
        value = facts[field]
        _require(_Validator(node).is_valid(value), "saved_fact_type_conflict")
        metric = selection["metric"]
        if metric == "missing_requirements":
            _require(selection == {"metric": "missing_requirements"} and type(value) is list
                and _same(value, saved["missing_requirements"]), "saved_requirement_conflict")
            for requirement in value:
                validate_contract("AcquisitionRequirement", requirement)
            group, name = FACT_SOURCES[2], "requirements"
        elif metric in _DISTRIBUTIONS:
            _require(node.get("type") == ["array", "null"] and (value is None or type(value) is list),
                "saved_weights_type_conflict")
            labels = []
            for weight in value or []:
                _require(type(weight) is dict and set(weight) == {"function", "weight"}
                    and type(weight["function"]) is str and bool(weight["function"].strip())
                    and type(weight["weight"]) in (int, float) and 0 <= weight["weight"] <= 1,
                    "saved_weight_conflict")
                labels.append(weight["function"])
            _require(len(labels) == len(set(labels)), "saved_function_assignment_conflict")
            group, name = FACT_SOURCES[1], "weights"
        else:
            _require(node.get("type") in (["integer", "null"], ["number", "null"])
                and (value is None or type(value) in (int, float)), "saved_measurement_type_conflict")
            group, name = FACT_SOURCES[0], "value"
        rows[group].append({"source_ref": source, "field": field, name: deepcopy(value)})
    return rows

def project_homology_facts(body, *, requested_sources):
    """Pure projection of one host-authenticated cumulative publication.

    This is intentionally not a custody authenticator. The host methods below
    obtain the body through the existing authenticated publication reader.
    """
    _require(type(requested_sources) in (tuple, list, set, frozenset)
        and all(type(name) is str and name in FACT_SOURCES for name in requested_sources)
        and len(set(requested_sources)) == len(requested_sources), "requested_sources_invalid")
    rows = _saved_facts(body)
    return {name: rows[name] for name in requested_sources}
