"""Requested Homology values from authenticated, frozen publications/returns.

The publication host owns native bytes, original inputs, saved sheets and
calculations. This module copies only its saved requested facts. Immediate
parents receive only rows admitted through the original child form; access to
an opaque source never exposes another projection. Reads create no acquisition,
calculation, journal, episode action, observation or credit.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .bvbrc_appservice_contracts import _finite_json, _Validator, contract_schema, validate_contract
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical


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


class BVBRCHomologyReturns(EpisodeReturnRecords):
    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix=_PREFIX)
        self.api = execution

    def _latest(self, context):
        self.authenticate(context, allow_unsaved=True)
        if context.role != "results":
            return None
        publications = self.api.appservice.publications
        for reference in reversed(publications.own_results(context)):
            body = publications.read(reference, context.scope, episode_id=context.episode_id)
            saved = body.get("publication", {}).get("adapter_result")
            if saved is None or saved.get("adapter_id") != "bvbrc_homology":
                continue
            self._require(body.get("run_id") == self.run_id and body.get("episode_id") == context.episode_id
                and self._equal(body.get("scope"), context.scope)
                and self._equal(body.get("assignment"), context.assignment)
                and self._equal(body["publication_inputs"].get("selector"), context.assignment.get("selector")),
                "publication_owner_conflict")
            _saved_facts(body)
            return body
        return None

    def facts(self, context, schema):
        sources = requested_sources(schema)
        body = self._latest(context) if sources else None
        facts = ({name: [] for name in sources} if body is None else
                 project_homology_facts(body, requested_sources=sources))
        for row in facts.get(FACT_SOURCES[2], []):
            for requirement in row["requirements"]:
                for reference in requirement["source_refs"]:
                    self._require(self.store.get(reference).get("record_type") == "source",
                        "requirement_source_required")
                    self.api.appservice.custody.possession(context, reference)
        return facts

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        return self.db.execute("SELECT decision_index,contract FROM runtime_report_attempts "
            "WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL "
            "ORDER BY decision_index", (self.run_id, context.episode_id)).fetchall()

    def _attempt(self, context, index):
        # Custody uses the common EpisodeReturnRecords checks, plus the original
        # execution-role commission/scope/inputs. No lifecycle-state gate is
        # added: admission may precede the runtime row's closed-state update.
        child, form, schema = self.api.appservice.custody._attempt(context, index)
        validate_form(form, schema, lambda *_: True)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original_index = int(child.path[-1][1].removeprefix("child_"))
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        original = plain(child.request)["report_contract"]
        if selected.get("kind") in {"episode_child", "child", "job_child"}:
            self._require(self._equal(selected.get("scope"), child.scope)
                and self._equal(json.loads(selected["schema_json"]), original["measurements"]["schema"])
                and selected.get("purpose") == original["decision"], "original_commission_conflict")
        if self._equal(schema, original["measurements"]["schema"]):
            frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen["form"] is not None
                and self._equal(json.loads(frozen["form"]), form), "frozen_form_conflict")
        return child, form, schema

    def _validate_values(self, context, form, schema):
        validate_form(form, schema, lambda *_: True)
        if context.role == "results":
            expected = self.facts(context, schema)
        elif context.role in {"annotation", "scientific_process"}:
            expected = self.received_facts(context, schema)
        else:
            raise ValueError(_PREFIX + "unsupported_return_owner")
        for name, node in schema.get("properties", {}).items():
            source = node.get("x-source")
            if source in FACT_SOURCES:
                self._require(name in form and self._equal(form[name], expected[source]), "returned_facts_conflict")
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if frozen is not None:
            saved = json.loads(frozen["facts"])
            self._require(all(source in saved and self._equal(saved[source], expected[source])
                for source in requested_sources(schema)), "frozen_facts_conflict")

    def received_context(self, context):
        grouped, seen = {}, {}
        for attempt in self._attempts(context):
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not requested_sources(schema):
                continue
            child, form, original = self._attempt(context, attempt["decision_index"])
            self._validate_values(child, form, original)
            for name, node in original["properties"].items():
                source = node.get("x-source")
                if source not in FACT_SOURCES:
                    continue
                rows, identities = grouped.setdefault(source, []), seen.setdefault(source, set())
                for row in form[name]:
                    key = canonical(row)
                    if key not in identities:
                        rows.append(deepcopy(row))
                        identities.add(key)
        return [{"fact_source": source, "facts": rows} for source, rows in grouped.items()]

    def received_facts(self, context, schema):
        sources = requested_sources(schema)
        facts = {name: [] for name in sources}
        for value in self.received_context(context) if sources else ():
            if value["fact_source"] in facts:
                facts[value["fact_source"]] = value["facts"]
        return facts

    def validate_received_report(self, context, form, schema):
        if requested_sources(schema):
            self._validate_values(context, plain(form), plain(schema))

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        child, saved_form, saved_schema = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved_form) and self._equal(schema, saved_schema), "admitted_form_conflict")
        self._validate_values(child, saved_form, saved_schema)
        # Source references embedded in requested requirements are also actual
        # received dependencies. Semantic labels do not become Store receipts.
        return list(dict.fromkeys(reference for name, node in saved_schema["properties"].items()
            if node.get("x-source") in FACT_SOURCES for reference, namespace in _references(saved_form[name], node)
            if namespace in {"execution_result", "source"}))

    @staticmethod
    def _has_reference(facts, reference, namespace):
        schemas = homology_fact_sources()
        return any(value == reference and kind == namespace for source, rows in facts.items()
            for value, kind in _references(rows, schemas[source]["report_schema"]))

    def resolve_own(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        facts = self.facts(context, schema)
        target_namespace = "source" if namespace is None else namespace
        found = self._has_reference(facts, reference, target_namespace)
        if namespace is None:
            found = found or self._has_reference(facts, reference, "execution_result")
        if found and namespace in {None, "source"}:
            source = self.store.get(reference)
            self._require(source.get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)
        return found if namespace in IDENTIFIER_NAMESPACES or found else None

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        facts = {value["fact_source"]: value["facts"] for value in self.received_context(context)}
        found = self._has_reference(facts, reference, "source" if namespace is None else namespace)
        if namespace is None:
            found = found or self._has_reference(facts, reference, "execution_result")
        if found and namespace in {None, "source"}:
            self._require(self.store.get(reference).get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)
        if namespace in IDENTIFIER_NAMESPACES or found:
            return found
        try:
            if self.store.get(reference).get("provider") == DATA_PROVIDER:
                # An unreceived bundle never qualifies merely because it exists.
                # Opaque references use the existing AppService custody resolver.
                return self.api.appservice.resolve(context, reference, namespace)
        except (ValueError, KeyError):
            return False
        return None


__all__ = ["BVBRCHomologyReturns", "FACT_SOURCES", "IDENTIFIER_NAMESPACES",
           "homology_fact_sources", "requested_sources", "project_homology_facts"]
