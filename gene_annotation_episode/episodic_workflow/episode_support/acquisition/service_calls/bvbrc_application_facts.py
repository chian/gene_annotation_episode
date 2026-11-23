"""Original selected application observations through existing typed returns.

The A106 AppService publication records its intervention adapters. It performs no acquisition, native parsing or calculation. Original
selected values are authenticated against saved Source-backed documents; only
the top publication Source implies custody. Nested native identifiers are data.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import re
from urllib.parse import quote, unquote

from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation import bvbrc_intervention_bundle_adapter as intervention
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.perturbation_evidence.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import canonical as _canonical


def _same(left, right):
    """Strict typed equality of two JSON trees (keys, element types and values)."""
    return _canonical(plain(left)) == _canonical(plain(right))
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.execution_contracts import canonical, digest


RESULT_VERSION = "bvbrc_appservice_acquired_bundle"
FACT_SOURCE = "bvbrc_application_outcomes"
FACT_SOURCES = (FACT_SOURCE,)
IDENTIFIER_NAMESPACE = "bvbrc_application_field"
IDENTIFIER_NAMESPACES = (IDENTIFIER_NAMESPACE,)
_ADAPTERS = ("bvbrc_tnseq", "bvbrc_rnaseq")
_PREFIX = "bvbrc_application_return_"
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z")


def _require(condition, code):
    if not condition:
        raise ValueError(_PREFIX + code)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def encode_field(analysis_id, field):
    _require(all(type(value) is str and value for value in (analysis_id, field)), "field_identity_invalid")
    return IDENTIFIER_NAMESPACE + ":" + quote(analysis_id, safe="") + "/" + quote(field, safe="")


def application_fact_sources():
    value = intervention.selected_field_schema()
    definitions = value.pop("$defs")
    schema = {"type": "array", "items": _object({
        "source_ref": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        "field": {"type": "string", "format": "identifier", "x-reference-namespace": IDENTIFIER_NAMESPACE},
        "value": value}), "$defs": definitions, "x-source": FACT_SOURCE}
    return {FACT_SOURCE: {"type": "array", "meaning": "Literal original selected BV-BRC intervention observations and calculated components.",
        "report_schema": schema}}


def requested_sources(schema):
    return tuple(dict.fromkeys(node.get("x-source") for node in plain(schema).get("properties", {}).values()
        if node.get("x-source") in FACT_SOURCES))


def validate_application_rows(rows):
    """Closed whole-row validation; this grants no Source or nested identifier."""
    _require(type(rows) is list, "returned_facts_invalid")
    result = []
    for row in rows:
        _require(type(row) is dict and set(row) == {"source_ref", "field", "value"}
            and type(row["source_ref"]) is str and _SOURCE.fullmatch(row["source_ref"]) is not None
            and type(row["field"]) is str and row["field"].startswith(IDENTIFIER_NAMESPACE + ":"), "returned_facts_invalid")
        candidate = row["value"]
        _require(type(candidate) is dict and candidate.get("version") == intervention.VALUE_VERSION,
            "returned_facts_invalid")
        value = intervention.validate_selected_field(candidate)
        parts = row["field"][len(IDENTIFIER_NAMESPACE) + 1:].split("/")
        _require(type(value["context"]) is dict and len(parts) == 2 and all(parts)
            and value["context"].get("analysis_id") == unquote(parts[0])
            and row["field"] == encode_field(unquote(parts[0]), unquote(parts[1])), "returned_facts_invalid")
        result.append(deepcopy(row))
    return result


def select_application_execution_values(value):
    """Present declared selected values without interpreting native JSON keys.

    Only the adapter's context fields imply custody. Native identifiers and
    member names remain literal, including strings resembling Source handles.
    """
    if not isinstance(value, Mapping):
        return None
    if set(value) == {"source_ref", "field", "value"} and isinstance(value.get("value"), Mapping):
        selected = select_application_execution_values(value["value"])
        field = value.get("field")
        if selected is not None and isinstance(field, str) and field.startswith(IDENTIFIER_NAMESPACE + ":"):
            return {"field": unquote(field.rsplit("/", 1)[-1]), "value": selected}
        return None
    if (value.get("version") != intervention.VALUE_VERSION or set(value) != {
            "version", "selection", "records", "record_accounting", "context", "issues"}
            or not isinstance(value.get("selection"), Mapping)
            or not isinstance(value.get("records"), (list, tuple))):
        return None
    result = plain(value)
    context = result.get("context")
    if isinstance(context, dict):
        context.pop("original_task", None)
        context.pop("content", None)
        identity = context.get("native_task_identity")
        if isinstance(identity, dict):
            identity.pop("observed_task_id", None)
    if result["selection"].get("kind") == "components":
        for row in result["records"]:
            if isinstance(row.get("value"), dict):
                row["value"].pop("document_sha256", None)
    return result


def _saved_content(value, binding, name):
    _require((value is None) == (binding is None), "saved_" + name + "_binding_conflict")
    if binding is not None:
        _require(binding["sha256"] == digest(value)
            and binding["byte_count"] == len(canonical(value).encode("utf-8")), "saved_" + name + "_content_conflict")


def project_application_facts(body, *, sheet, components):
    """Project the original publication selection, never today's latest values.

    The caller authenticates this actual publication and both ContentBindings.
    Content digests here are data equality checks, not substitute File custody.
    """
    _require(type(body) is dict and body.get("version") == RESULT_VERSION, "publication_required")
    reference = body.get("source_ref")
    _require(type(reference) is str and _SOURCE.fullmatch(reference) is not None
        and body.get("reference") == reference, "result_source_conflict")
    publication, inputs = body.get("publication"), body.get("publication_inputs")
    _require(type(publication) is dict and type(inputs) is dict, "publication_required")
    content = publication.get("bundle_content")
    _require(type(content) is dict and content.get("source_ref") == reference
        and reference in publication.get("result_record_refs", []) and reference in body.get("record_refs", []), "result_source_conflict")
    saved = validate_contract("AdapterResult", publication.get("adapter_result"))
    _require(saved["adapter_id"] in _ADAPTERS and saved["adapter_version"] == "1", "application_adapter_required")
    selector = validate_contract("ResultSelector", inputs.get("selector"))
    selected = selector["adapter"]
    _require(type(selected) is dict and all(selected[key] == saved[key] for key in ("adapter_id", "adapter_version"))
        and _same(inputs.get("adapter"), selected), "original_adapter_conflict")
    assignment = body.get("assignment")
    _require(type(assignment) is dict and _same(assignment.get("selector"), selector), "original_selector_conflict")
    parameter_reader, form_reader = intervention.validate_parameters, intervention.validate_requested_form
    saved_reader, status_reader = intervention.validate_saved_intervention_facts, intervention.intervention_projection_status
    parameters = parameter_reader(selected["parameters"])
    _require(intervention.APPLICATION_ADAPTERS[parameters["application_id"]] == saved["adapter_id"],
        "original_adapter_application_conflict")
    form = form_reader(selector["requested_schema"])
    _saved_content(sheet, saved["sheet_content"], "sheet")
    _saved_content(components, saved["components_content"], "components")
    if saved["status"] == "invalid" and sheet is None and components is None and saved["facts"] == {}:
        return {FACT_SOURCE: []}
    _require(type(body.get("bundle")) is dict and type(sheet) is dict
        and _same(sheet.get("original_task"), body["bundle"].get("original_task")), "original_task_conflict")
    facts = saved_reader(saved["facts"], sheet=sheet, components=components,
        parameters=parameters, requested_form=form)
    _require(saved["status"] == status_reader(bundle_status=body["bundle"]["status"],
        missing_requirements=saved["missing_requirements"], diagnostics=saved["diagnostics"], facts=facts), "saved_status_conflict")
    rows = [{"source_ref": reference, "field": encode_field(parameters["analysis_id"], name), "value": deepcopy(facts[name])}
        for name in form["required"]]
    return {FACT_SOURCE: validate_application_rows(rows)}


