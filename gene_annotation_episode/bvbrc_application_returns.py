"""Original selected application observations through existing typed returns.

One AppService publication/receipt owner serves the finite new application
adapters. It performs no acquisition, native parsing or calculation. Original
selected values are authenticated against saved Source-backed documents; only
the top publication Source implies custody. Nested native identifiers are data.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import re
from urllib.parse import quote, unquote

from .bvbrc_annotation_contracts import (
    VALUE_VERSION, selected_field_schema, validate_selected_field, validate_parameters, validate_requested_form,
)
from .bvbrc_annotation_bundle_adapter import validate_saved_annotation_facts, annotation_projection_status
from .bvbrc_assembly_contracts import (
    VALUE_VERSION as ASSEMBLY_VALUE_VERSION, selected_field_schema as assembly_field_schema,
    validate_selected_field as validate_assembly_field, validate_parameters as validate_assembly_parameters,
    validate_requested_form as validate_assembly_form,
)
from .bvbrc_assembly_bundle_adapter import validate_saved_assembly_facts, assembly_projection_status
from . import bvbrc_variation_bundle_adapter as variation
from . import bvbrc_influenza_ha_bundle_adapter as influenza_ha
from . import bvbrc_subspecies_bundle_adapter as subspecies
from . import bvbrc_subspecies_contracts as subspecies_contracts
from . import bvbrc_intervention_bundle_adapter as intervention
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_appservice_publication import RESULT_VERSION
from .bvbrc_appservice_saved_results import read_latest_adapter_result
from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest
from .form_reference_validation import _binding_key, form_validation_value


FACT_SOURCE = "bvbrc_application_outcomes"
FACT_SOURCES = (FACT_SOURCE,)
IDENTIFIER_NAMESPACE = "bvbrc_application_field"
IDENTIFIER_NAMESPACES = (IDENTIFIER_NAMESPACE,)
_ADAPTERS = ("bvbrc_annotation", "bvbrc_assembly", "bvbrc_variation", "bvbrc_influenza_ha", "bvbrc_subspecies", "bvbrc_tnseq", "bvbrc_rnaseq")
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
    value = selected_field_schema()
    definitions = value.pop("$defs")
    assembly = assembly_field_schema()
    _require(canonical(assembly.pop("$defs")) == canonical(definitions), "literal_definitions_conflict")
    ha = influenza_ha.selected_field_schema()
    strains = subspecies_contracts.selected_field_schema()
    perturbation = intervention.selected_field_schema()
    for field in (ha, strains, perturbation):
        _require(canonical(field.pop("$defs")) == canonical(definitions), "literal_definitions_conflict")
    variants = variation.selected_field_schema()
    for name, node in variants.pop("$defs").items():
        _require(name not in definitions or canonical(definitions[name]) == canonical(node), "literal_definitions_conflict")
        definitions[name] = node
    schema = {"type": "array", "items": _object({
        "source_ref": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        "field": {"type": "string", "format": "identifier", "x-reference-namespace": IDENTIFIER_NAMESPACE},
        "value": {"oneOf": [value, assembly, variants, ha, strains, perturbation]}}), "$defs": definitions, "x-source": FACT_SOURCE}
    return {FACT_SOURCE: {"type": "array", "meaning": "Literal original selected BV-BRC application observations and shared calculated components.",
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
        _require(type(candidate) is dict and candidate.get("version") in (VALUE_VERSION, ASSEMBLY_VALUE_VERSION,
            variation.VALUE_VERSION, influenza_ha.VALUE_VERSION, subspecies_contracts.VALUE_VERSION, intervention.VALUE_VERSION),
            "returned_facts_invalid")
        value = ({VALUE_VERSION: validate_selected_field, ASSEMBLY_VALUE_VERSION: validate_assembly_field,
            variation.VALUE_VERSION: variation.validate_selected_field,
            influenza_ha.VALUE_VERSION: influenza_ha.validate_selected_field,
            subspecies_contracts.VALUE_VERSION: subspecies_contracts.validate_selected_field,
            intervention.VALUE_VERSION: intervention.validate_selected_field}[candidate["version"]])(candidate)
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
    if value.get("version") == variation.VALUE_VERSION:
        if set(value) != {"version", "selection", "state", "value", "context", "issues"}:
            return None
        result = plain(value)
        context = result.get("context")
        if isinstance(context, dict):
            for name in ("original_task", "content", "vcf_sheet_sha256"):
                context.pop(name, None)
        # Exact VCF metadata shapes only. Biological tokens, INFO keys and
        # strings resembling reference handles remain untouched literal data.
        def visible(node):
            if isinstance(node, dict):
                if set(node) == {"input_id", "retained_file", "original_file", "source_ref", "capture"}:
                    return {"capture": visible(node["capture"])}
                if set(node) == {"input_id", "artifact_ref", "sha256", "byte_start_0based",
                        "byte_end_0based_exclusive", "line_start_1based", "line_end_1based_inclusive"}:
                    return {key: child for key, child in node.items() if key not in {"input_id", "artifact_ref", "sha256"}}
                return {key: visible(child) for key, child in node.items()}
            if isinstance(node, list):
                return [visible(child) for child in node]
            return node
        result["value"] = visible(result["value"])
        return result
    if (value.get("version") not in (VALUE_VERSION, ASSEMBLY_VALUE_VERSION,
            influenza_ha.VALUE_VERSION, subspecies_contracts.VALUE_VERSION, intervention.VALUE_VERSION) or set(value) != {
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
    if (result["version"] == ASSEMBLY_VALUE_VERSION and isinstance(context, dict)
            and context.get("representation") == "assembly_fasta"):
        for row in result["records"]:
            selected = row.get("value")
            if not isinstance(selected, dict):
                continue
            if result["selection"]["kind"] == "native_document":
                selected.pop("artifact", None)
                native_rows = selected.get("rows", [])
            elif result["selection"]["kind"] == "records":
                native_rows = [selected]
            else:
                native_rows = []
            for native_row in native_rows:
                if isinstance(native_row, dict) and isinstance(native_row.get("source_location"), dict):
                    native_row["source_location"].pop("artifact", None)
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
    pin = inputs.get("adapter_implementation_sha256")
    _require(type(pin) is str and re.fullmatch(r"[a-f0-9]{64}", pin) is not None, "original_adapter_pin_required")
    assignment = body.get("assignment")
    _require(type(assignment) is dict and _same(assignment.get("selector"), selector), "original_selector_conflict")
    parameter_reader, form_reader, saved_reader, status_reader = {
        "bvbrc_annotation": (validate_parameters, validate_requested_form,
            validate_saved_annotation_facts, annotation_projection_status),
        "bvbrc_assembly": (validate_assembly_parameters, validate_assembly_form,
            validate_saved_assembly_facts, assembly_projection_status),
        variation.ADAPTER_ID: (variation.validate_parameters, variation.validate_requested_form,
            variation.validate_saved_variation_facts, variation.variation_projection_status),
        influenza_ha.ADAPTER_ID: (influenza_ha.validate_parameters, influenza_ha.validate_requested_form,
            influenza_ha.validate_saved_influenza_ha_facts, influenza_ha.influenza_ha_projection_status),
        subspecies.ADAPTER_ID: (subspecies_contracts.validate_parameters, subspecies_contracts.validate_requested_form,
            subspecies.validate_saved_subspecies_facts, subspecies.subspecies_projection_status),
        "bvbrc_tnseq": (intervention.validate_parameters, intervention.validate_requested_form,
            intervention.validate_saved_intervention_facts, intervention.intervention_projection_status),
        "bvbrc_rnaseq": (intervention.validate_parameters, intervention.validate_requested_form,
            intervention.validate_saved_intervention_facts, intervention.intervention_projection_status),
    }[saved["adapter_id"]]
    parameters = parameter_reader(selected["parameters"])
    if saved["adapter_id"] in intervention.APPLICATION_ADAPTERS.values():
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


class BVBRCApplicationReturns(EpisodeReturnRecords):
    """Typed own/frozen/received values on existing AppService custody records."""
    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix=_PREFIX)
        self.api = execution

    def _authenticate(self, context):
        self.authenticate(context, allow_unsaved=True)
        self.api.appservice.custody.authenticate(context, allow_unsaved=True)
        self._require(context.role == context.path[-1][0], "publication_owner_conflict")

    def _owner(self, context, body):
        self._require(body.get("run_id") == self.run_id and body.get("episode_id") == context.episode_id
            and self._equal(body.get("scope"), context.scope) and self._equal(body.get("assignment"), context.assignment)
            and self._equal(body["publication_inputs"].get("selector"), context.assignment.get("selector")), "publication_owner_conflict")

    def _possessed_sources(self, context, rows):
        for reference in dict.fromkeys(row["source_ref"] for row in rows):
            self._require(self.store.get(reference).get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)

    def facts(self, context, schema):
        if not requested_sources(schema):
            return {}
        self._authenticate(context)
        latest = read_latest_adapter_result(self.api.appservice.publications, context, adapter_ids=_ADAPTERS)
        if latest is None:
            return {FACT_SOURCE: []}
        body, sheet, components = latest
        self._owner(context, body)
        values = project_application_facts(body, sheet=sheet, components=components)
        self._possessed_sources(context, values[FACT_SOURCE])
        return values

    def _attempt(self, context, index):
        self._authenticate(context)
        child, form, schema = self.api.appservice.custody._attempt(context, index)
        validate_form(form, schema, lambda *_: True)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original_index = int(child.path[-1][1].removeprefix("child_"))
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        original = plain(child.request)["report_contract"]
        if selected.get("kind") in {"episode_child", "child", "job_child"}:
            self._require(self._equal(selected.get("scope"), child.scope)
                and selected.get("purpose") == original["decision"], "original_commission_conflict")
        if self._equal(schema, original["measurements"]["schema"]):
            frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen["form"] is not None
                and self._equal(json.loads(frozen["form"]), form), "frozen_form_conflict")
        return child, form, schema

    def _values(self, form, schema):
        validate_form(form, schema, lambda *_: True)
        selected = None
        for name, node in schema["properties"].items():
            if node.get("x-source") == FACT_SOURCE:
                rows = validate_application_rows(form[name])
                self._require(selected is None or self._equal(selected, rows), "returned_facts_conflict")
                selected = rows
        return {FACT_SOURCE: [] if selected is None else selected}

    def _frozen(self, context, values):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            frozen = json.loads(row["facts"])
            self._require(all(key in frozen and self._equal(frozen[key], rows) for key, rows in values.items()), "frozen_facts_conflict")

    def _original_publication(self, context, reference):
        publications = self.api.appservice.publications
        body = publications.read(reference, context.scope, episode_id=context.episode_id)
        self._owner(context, body)
        saved = body["publication"]["adapter_result"]
        values = [None if saved[name + "_content"] is None else publications.read_content_source(
            saved[name + "_content"]["source_ref"], context.scope) for name in ("sheet", "components")]
        return project_application_facts(body, sheet=values[0], components=values[1])

    def _validate_historical(self, context, form, schema):
        self._authenticate(context)
        values = self._values(form, schema)
        self._frozen(context, values)
        if context.role == "results":
            expected = []
            for reference in dict.fromkeys(row["source_ref"] for row in values[FACT_SOURCE]):
                expected.extend(self._original_publication(context, reference)[FACT_SOURCE])
            self._require(self._equal(values[FACT_SOURCE], expected), "returned_facts_conflict")
        elif context.role in {"annotation", "scientific_process"}:
            received = self.received_facts(context, schema)
            self._require(all(any(self._equal(row, original) for original in received[FACT_SOURCE])
                for row in values[FACT_SOURCE]), "returned_facts_conflict")
        else:
            raise ValueError(_PREFIX + "unsupported_return_owner")
        self._possessed_sources(context, values[FACT_SOURCE])

    def received_context(self, context):
        rows, seen = [], set()
        for child, form, schema in self.received_attempts(context, allow_unsaved=True):
            if not requested_sources(schema):
                continue
            self._validate_historical(child, form, schema)
            for row in self._values(form, schema)[FACT_SOURCE]:
                key = canonical(row)
                if key not in seen:
                    rows.append(deepcopy(row)); seen.add(key)
        return [{"fact_source": FACT_SOURCE, "facts": rows}] if rows else []

    def received_facts(self, context, schema):
        if not requested_sources(schema):
            return {}
        groups = self.received_context(context)
        return {FACT_SOURCE: groups[0]["facts"] if groups else []}

    def validate_received_report(self, context, form, schema):
        if not requested_sources(schema):
            return
        self._authenticate(context)
        values = self._values(plain(form), plain(schema))
        expected = self.facts(context, schema) if context.role == "results" else self.received_facts(context, schema)
        self._require(context.role in {"results", "scientific_process", "annotation"}
            and self._equal(values, expected), "returned_facts_conflict")
        self._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        child, saved, original_schema = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved) and self._equal(schema, original_schema), "admitted_form_conflict")
        self._validate_historical(child, saved, original_schema)
        return list(dict.fromkeys(row["source_ref"] for row in self._values(saved, original_schema)[FACT_SOURCE]))

    def _resolve(self, context, rows, reference, namespace):
        if namespace in {None, "source", "execution_result"} and any(row["source_ref"] == reference for row in rows):
            self._possessed_sources(context, [row for row in rows if row["source_ref"] == reference])
            return True
        if namespace == IDENTIFIER_NAMESPACE:
            return any(row["field"] == reference for row in rows)
        return None

    def resolve_own(self, context, reference, namespace):
        if namespace not in {None, "source", "execution_result", IDENTIFIER_NAMESPACE}:
            return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        facts = form_validation_value((self, "own", _binding_key(context), canonical(schema)), lambda: self.facts(context, schema))
        return self._resolve(context, facts.get(FACT_SOURCE, []), reference, namespace)

    def resolve_received(self, context, reference, namespace):
        if namespace not in {None, "source", "execution_result", IDENTIFIER_NAMESPACE}:
            return None
        groups = form_validation_value((self, "received", _binding_key(context)), lambda: self.received_context(context))
        return self._resolve(context, [row for group in groups for row in group["facts"]], reference, namespace)


__all__ = ["FACT_SOURCE", "FACT_SOURCES", "IDENTIFIER_NAMESPACE", "IDENTIFIER_NAMESPACES", "encode_field",
    "application_fact_sources", "requested_sources", "validate_application_rows", "select_application_execution_values",
    "project_application_facts", "BVBRCApplicationReturns"]
