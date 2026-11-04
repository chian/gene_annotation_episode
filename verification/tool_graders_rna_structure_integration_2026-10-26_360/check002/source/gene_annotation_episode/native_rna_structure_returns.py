"""Authenticate exact RNA facts at existing immediate-child form boundaries.

Source custody never expands into numerical rows or artifact permissions.
Receipt authentication reads recorded work; no scientific operation runs here.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain, validate_form
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical
from .form_reference_validation import _binding_key, form_validation_value
from .rna_structure_result_views import (FAMILY_SOURCES, IDENTIFIER_NAMESPACES,
    REFERENCE_SOURCE, SAVED_SOURCE, rna_structure_fact_sources, validate_rna_structure_row,
    validate_saved_rna_input)

FACT_SOURCES = (*FAMILY_SOURCES.values(), REFERENCE_SOURCE, SAVED_SOURCE)
GENERIC_REFERENCE_SOURCE = "execution_result_refs"


def requested_sources(schema):
    return tuple(dict.fromkeys(node["x-source"] for node in plain(schema).get("properties", {}).values()
        if node.get("x-source") in FACT_SOURCES))


def _generic(schema):
    return any(node.get("x-source") == GENERIC_REFERENCE_SOURCE for node in plain(schema).get("properties", {}).values())


class NativeRNAStructureReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="rna_return_")
        self.owner, self.results = owner, owner.native_rna_structure_results

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], "context_role_conflict")
        return context

    def _handles(self, context, schema):
        return bool(requested_sources(schema) or _generic(schema) and context.role == "results" and self.results.applies(context))

    def _values(self, form, schema, *, generic=False):
        validate_form(form, schema, lambda *_: True)
        descriptors, values = rna_structure_fact_sources(), {}
        for name, node in plain(schema).get("properties", {}).items():
            source = node.get("x-source")
            if source not in FACT_SOURCES and not (generic and source == GENERIC_REFERENCE_SOURCE):
                continue
            rows = plain(form[name])
            expected = descriptors[REFERENCE_SOURCE if source == GENERIC_REFERENCE_SOURCE else source]["report_schema"]
            validate_form({"rows": rows}, {"type": "object", "additionalProperties": False,
                "properties": {"rows": expected}, "required": ["rows"]}, lambda *_: True)
            if source in FAMILY_SOURCES.values():
                for row in rows:
                    validate_rna_structure_row(row)
            elif source == SAVED_SOURCE:
                for row in rows:
                    validate_saved_rna_input(row)
            self._require(source not in values or self._equal(values[source], rows), "conflicting_fields")
            values[source] = rows
        return values

    def _frozen(self, context, values):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            facts = json.loads(row["facts"])
            self._require(all(source in facts and self._equal(facts[source], value)
                for source, value in values.items()), "frozen_facts_conflict")

    def _own_facts(self, context, sources, *, verify_artifacts=True):
        self.authenticate(context)
        self._require(self.results.applies(context), "original_results_owner_required")
        # Original immutable receipts establish descriptor authority even if
        # retained bytes later disappear. Recalculation reports that absence.
        numeric = verify_artifacts and any(source in FAMILY_SOURCES.values() and source != FAMILY_SOURCES["failure"] for source in sources)
        actual = self.results.facts(context, verify_artifacts=numeric)
        return {source: actual[GENERIC_REFERENCE_SOURCE if source == REFERENCE_SOURCE else source] for source in sources}

    def _attempt(self, context, index):
        child, form, schema = super()._attempt(context, index)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original = plain(child.request)["report_contract"]
        original_index = int(child.path[-1][1].removeprefix("child_"))
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        self._require(selected.get("kind") in {"episode_child", "child", "job_child"}
            or selected.get("kind") == "tool" and selected.get("tool") == "process.revise", "original_commission_conflict")
        if selected.get("kind") in {"episode_child", "child", "job_child"}:
            self._require(self._equal(selected.get("scope"), child.scope)
                and self._equal(json.loads(selected["schema_json"]), original["measurements"]["schema"])
                and selected.get("purpose") == original["decision"], "original_commission_conflict")
        frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, child.episode_id)).fetchone()
        if self._equal(schema, original["measurements"]["schema"]):
            self._require(frozen is not None and frozen["form"] is not None and self._equal(json.loads(frozen["form"]), form),
                "frozen_form_conflict")
        return child, form, schema

    def _validate_historical(self, context, form, schema, *, verify_artifacts=True):
        self.authenticate(context)
        values = self._values(form, schema, generic=context.role == "results")
        self._frozen(context, values)
        if context.role == "results":
            self._require(self._equal(values, self._own_facts(context, values, verify_artifacts=verify_artifacts)), "returned_facts_conflict")
        elif context.role in {"annotation", "scientific_process"}:
            grouped = self._received(context, verify_artifacts=verify_artifacts)["groups"]
            received = {source: grouped.get(source, []) for source in requested_sources(schema)}
            self._require(all(all(any(self._equal(value, saved) for saved in received[source]) for value in rows)
                for source, rows in values.items()), "returned_facts_conflict")
        else:
            self._require(False, "unsupported_return_owner")
        return values

    @staticmethod
    def _references(values):
        references = []
        for source, rows in values.items():
            if source in {REFERENCE_SOURCE, GENERIC_REFERENCE_SOURCE}:
                references.extend(rows)
            elif source == SAVED_SOURCE:
                references.extend(row[key] for row in rows for key in
                    ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref"))
            else:
                references.extend(row[key] for row in rows for key in ("source_ref", "subject_ref")
                    if row.get(key) is not None)
        return list(dict.fromkeys(references))

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        return self.db.execute("SELECT decision_index,child_episode_id,contract FROM runtime_report_attempts "
            "WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (self.run_id, context.episode_id)).fetchall()

    def _received(self, context, *, verify_artifacts=True):
        self.authenticate(context, allow_unsaved=True)
        grouped, seen, references = {}, {}, []
        for attempt in self._attempts(context):
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            child = self.context(attempt["child_episode_id"])
            if not self._handles(child, schema):
                continue
            child, form, schema = self._attempt(context, attempt["decision_index"])
            values = self._validate_historical(child, form, schema, verify_artifacts=verify_artifacts)
            references.extend(self._references(values))
            for source, rows in values.items():
                if source not in FACT_SOURCES:
                    continue
                group, identities = grouped.setdefault(source, []), seen.setdefault(source, set())
                for row in rows:
                    key = canonical(row)
                    if key not in identities:
                        group.append(deepcopy(row))
                        identities.add(key)
        return {"groups": grouped, "references": list(dict.fromkeys(references))}

    def _received_values(self, context):
        return form_validation_value((self, "received", _binding_key(context)), lambda: self._received(context))

    def received_context(self, context):
        return [{"fact_source": source, "facts": deepcopy(rows)} for source, rows in self._received_values(context)["groups"].items()]

    def received_facts(self, context, schema):
        requested = requested_sources(schema)
        if not requested:
            return {}
        received = self._received_values(context)
        # Reference-only requests grant only references that were themselves
        # requested. A numeric row's source is a reference resolver operand,
        # not an invented source-only fact group.
        return {source: deepcopy(received["groups"].get(source, [])) for source in requested}

    def validate_received_report(self, context, form, schema):
        if not self._handles(context, schema):
            return
        self.authenticate(context, allow_unsaved=True)
        values = self._values(form, schema, generic=context.role == "results")
        expected = self._own_facts(context, values) if context.role == "results" else self.received_facts(context, schema)
        self._require(self._equal(values, expected), "returned_facts_conflict")
        self._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema) and not _generic(schema):
            return []
        index = self._admission_index(context, operation_key)
        child, saved, declared = self._attempt(context, index)
        if not self._handles(child, declared):
            return []
        self._require(self._equal(form, saved) and self._equal(schema, declared), "admitted_form_conflict")
        return self._references(self._validate_historical(child, saved, declared))

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, None, "source", "artifact", "execution_result", "subject", "execution_handoff"):
            return None
        received = self._received_values(context)
        key = dict(zip(IDENTIFIER_NAMESPACES, ("row_key", "calculation_key", "result_receipt_key"))).get(namespace)
        if key is not None:
            return any(isinstance(row, dict) and row.get(key) == reference for rows in received["groups"].values() for row in rows)
        if reference in received["references"]:
            return namespace not in {"source", "artifact"} or self.store.get(reference)["record_type"] == namespace
        return None

    def resolve_saved_rna_input(self, context, descriptor):
        self.authenticate(context, allow_unsaved=True)
        if context.role == "results":
            from .native_rna_structure_result_publication import authenticate_rna_results_commission
            authenticate_rna_results_commission(self.store, context, allow_unsaved=True)
        descriptor = validate_saved_rna_input(descriptor)
        body = self.results.read_receipt_key(descriptor["result_receipt_key"], context.scope)
        self._require(body["assignment"]["selector"]["acquisition"] == "complete_bound_bundle"
            and self._equal(self.results.saved_descriptor(body, verify_bytes=False), descriptor), "saved_descriptor_conflict")
        if context.role == "results":
            self._require(plain(context.assignment)["handoff_ref"] == descriptor["handoff_ref"]
                and plain(context.assignment)["selector"].get("saved_input") == descriptor, "saved_assignment_conflict")
        # A parent selecting its next child may consume an earlier own received
        # form. A commissioned child sees only each ancestor's frozen prefix.
        found = False
        current, before = context, None
        receipts = EpisodeReceipts(self.store, self.run_id)
        known = set(receipts.known(context.episode_id, baseline=context.role == "results"))
        operand_refs = {descriptor[key] for key in ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")}
        while True:
            for attempt in self._attempts(current):
                if before is not None and attempt["decision_index"] >= before:
                    continue
                schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
                if SAVED_SOURCE not in requested_sources(schema):
                    continue
                child, form, schema = self._attempt(current, attempt["decision_index"])
                values = self._validate_historical(child, form, schema, verify_artifacts=False)
                if any(self._equal(descriptor, value) for value in values.get(SAVED_SOURCE, [])):
                    found = True
                    break
            if found:
                break
            manifest = receipts.manifest(current.episode_id)
            if manifest["parent_episode_id"] is None:
                break
            self._require(current.path[-1][1].startswith("child_"), "saved_prefix_conflict")
            before = int(current.path[-1][1][len("child_"):])
            parent = self.context(manifest["parent_episode_id"])
            self._require(current.path[:-1] == parent.path, "saved_prefix_conflict")
            current = parent
        self._require(found and operand_refs <= known, "saved_input_not_received")
        return body


__all__ = ["NativeRNAStructureReturns", "FACT_SOURCES", "REFERENCE_SOURCE", "SAVED_SOURCE", "requested_sources"]
