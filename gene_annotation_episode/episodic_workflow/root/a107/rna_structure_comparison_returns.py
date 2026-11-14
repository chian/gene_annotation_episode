"""Exact comparison facts through the existing immediate-child return records.

Symbolic calculation/receipt identifiers locate validated facts; they are not
Store references and grant no source or artifact traversal.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical
from .rna_structure_comparison_views import (
    IDENTIFIER_NAMESPACES, PROJECTION_SOURCE, rna_comparison_fact_sources,
)


def requested_sources(schema):
    return tuple(dict.fromkeys(node["x-source"] for node in plain(schema).get("properties", {}).values()
        if node.get("x-source") == PROJECTION_SOURCE))


class RNAStructureComparisonReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="rna_comparison_return_")
        self.owner, self.results = owner, owner.rna_structure_comparison_results

    @property
    def original(self):
        return self.owner.native_rna_structure_returns

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], "context_role_conflict")
        return context

    def _values(self, form, schema):
        validate_form(form, schema, lambda *_: True)
        values = {}
        expected = rna_comparison_fact_sources()[PROJECTION_SOURCE]["report_schema"]
        for name, node in plain(schema).get("properties", {}).items():
            if node.get("x-source") != PROJECTION_SOURCE:
                continue
            rows = plain(form[name])
            validate_form({"rows": rows}, {"type": "object", "additionalProperties": False,
                "properties": {"rows": expected}, "required": ["rows"]}, lambda *_: True)
            self._require(PROJECTION_SOURCE not in values or self._equal(values[PROJECTION_SOURCE], rows), "conflicting_fields")
            values[PROJECTION_SOURCE] = rows
        return values

    def _own_facts(self, context, sources):
        self.authenticate(context, allow_unsaved=True)
        self._require(self.results.applies(context), "original_results_owner_required")
        actual = self.results.facts(context)
        return {source: actual[source] for source in sources}

    def _validate_historical(self, context, form, schema):
        self.authenticate(context)
        values = self._values(form, schema)
        self.original._frozen(context, values)
        if context.role == "results":
            expected = self._own_facts(context, values)
            self._require(self._equal(values, expected), "returned_facts_conflict")
        elif context.role in {"annotation", "scientific_process"}:
            received = self._received(context)
            self._require(all(all(any(self._equal(row, saved) for saved in received.get(source, []))
                for row in rows) for source, rows in values.items()), "returned_facts_conflict")
        else:
            self._require(False, "unsupported_return_owner")
        return values

    def _received(self, context):
        self.authenticate(context, allow_unsaved=True)
        values, seen = {}, set()
        for attempt in self.original._attempts(context):
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not requested_sources(schema):
                continue
            child, form, schema = self.original._attempt(context, attempt["decision_index"])
            checked = self._validate_historical(child, form, schema)
            for row in checked.get(PROJECTION_SOURCE, []):
                identity = canonical(row)
                if identity not in seen:
                    values.setdefault(PROJECTION_SOURCE, []).append(deepcopy(row))
                    seen.add(identity)
        return values

    def received_context(self, context):
        return [{"fact_source": source, "facts": rows} for source, rows in self._received(context).items()]

    def received_facts(self, context, schema):
        requested = requested_sources(schema)
        if not requested:
            return {}
        # Recheck the original records every time. Grammar compilation cannot
        # retain an authority verdict after a changed receipt or frozen form.
        received = self._received(context)
        return {source: deepcopy(received.get(source, [])) for source in requested}

    def validate_received_report(self, context, form, schema):
        if not requested_sources(schema):
            return
        self.authenticate(context, allow_unsaved=True)
        values = self._values(form, schema)
        expected = self._own_facts(context, values) if context.role == "results" else self.received_facts(context, schema)
        self._require(self._equal(values, expected), "returned_facts_conflict")
        self.original._frozen(context, values)

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        index = self._admission_index(context, operation_key)
        child, saved, declared = self.original._attempt(context, index)
        self._require(requested_sources(declared) and self._equal(form, saved)
            and self._equal(schema, declared), "admitted_form_conflict")
        self._validate_historical(child, saved, declared)
        return []

    def resolve_received(self, context, reference, namespace):
        if namespace not in IDENTIFIER_NAMESPACES:
            if any(isinstance(reference, str) and reference.startswith(prefix + ":") for prefix in IDENTIFIER_NAMESPACES):
                return False
            return None
        field = "result_receipt_key" if namespace == IDENTIFIER_NAMESPACES[0] else "calculation_key"
        return any(row[field] == reference for row in self._received(context).get(PROJECTION_SOURCE, []))


__all__ = ["RNAStructureComparisonReturns", "requested_sources", "IDENTIFIER_NAMESPACES", "PROJECTION_SOURCE"]
