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

from .library.bvbrc_appservice_contracts import _finite_json, _Validator, contract_schema, validate_contract
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_homology_return_values import FACT_SOURCES, IDENTIFIER_NAMESPACES, _PREFIX, _saved_facts, homology_fact_sources, project_homology_facts, requested_sources


















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
        # commission/scope/inputs and full or compact forms authenticated from
        # the original decision's frozen fact catalog. No lifecycle-state gate
        # is added: admission may precede the runtime row's closed-state update.
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


__all__ = ['BVBRCHomologyReturns']
