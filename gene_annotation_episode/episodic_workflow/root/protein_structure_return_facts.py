"""Original exact typed fact validation, frozen delivery and parent admission."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import FACT_SOURCES, _VALIDATORS
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import _error, _boundary, _validate, requested_sources, _references
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinFactGroups
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import protein_structure_fact_sources
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
import json


class ProteinStructureReturnFacts:
    def _values(self, form, schema):
        """Validate the actual enclosing parent form and exact registered facts."""
        form, schema = plain(form), plain(schema)
        definitions = protein_structure_fact_sources()
        values = {}
        if type(form) is not dict or type(schema) is not dict:
            raise _error("invalid_schema", field="descriptor")
        for name, node in schema.get("properties", {}).items():
            if type(node) is not dict:
                raise _error("invalid_schema", field="descriptor")
            source = node.get("x-source")
            if source not in FACT_SOURCES:
                if isinstance(source, str) and source.startswith("execution_protein_structure_"):
                    raise _error("invalid_schema", field="descriptor")
                continue
            expected = {**definitions[source]["report_schema"], "x-source": source}
            if not self._equal(node, expected):
                raise _error("invalid_schema", field="descriptor")
            rows = form.get(name)
            if type(rows) is not list:
                raise _error("invalid_schema", field="descriptor")
            rows = [_validate(_VALIDATORS[source], row) for row in rows]
            self._require(source not in values or self._equal(values[source], rows))
            values[source] = rows
        try:
            validate_form(form, schema, lambda *_: True)
        except ReportBoundaryError as error:
            raise _error("invalid_schema", field="descriptor") from error
        return {source: values[source] for source in FACT_SOURCES if source in values}

    def _frozen(self, context, values):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            facts = json.loads(row["facts"])
            self._require(all(source in facts and self._equal(facts[source], value)
                              for source, value in values.items()))

    def _own(self, context, *, verify_artifacts=False):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role == "results")
        groups = self.results.own_fact_groups(context, verify_artifacts=verify_artifacts)
        self._require(type(groups) is dict and set(groups) == set(FACT_SOURCES))
        return {source: [_validate(_VALIDATORS[source], row) for row in groups[source]] for source in FACT_SOURCES}

    def _historical(self, context, form, schema, *, verify_artifacts=False, active=()):
        self.authenticate(context)
        marker = (context.episode_id, digest(schema), digest(form))
        self._require(marker not in active)
        values = self._values(form, schema)
        self._frozen(context, values)
        if context.role == "results":
            own = self._own(context, verify_artifacts=verify_artifacts)
            self._require(all(self._equal(rows, own[source]) for source, rows in values.items()))
        else:
            received = self._received(context, verify_artifacts=verify_artifacts, active=(*active, marker))
            self._require(all(all(any(self._equal(row, original) for original in received[source])
                                  for row in rows) for source, rows in values.items()))
        return values

    def _deliveries(self, context, *, verify_artifacts=False, active=()):
        known, seen = self._known(context), {}
        # Inherited reports were already known before this episode's own later
        # deliveries. Preserve that order across different source keys too.
        for current, allowed, before, enabled in reversed(list(self._levels(context))):
            for attempt in self._attempts_at(current, allowed, before, enabled):
                schema = json.loads(attempt["contract"])["measurements"]["schema"]
                if not requested_sources(schema):
                    continue
                child, form, schema = self._attempt(current, attempt["decision_index"])
                values = self._historical(child, form, schema, verify_artifacts=verify_artifacts, active=active)
                for source, rows in values.items():
                    for row in rows:
                        # Exact typed delivery and frozen semantic operands are
                        # independent conditions. Old recursive receipts alone
                        # never create a row or descriptor.
                        if not set(_references({source: [row]})) <= known:
                            continue
                        key = canonical(row)
                        if key not in seen.setdefault(source, set()):
                            seen[source].add(key)
                            yield source, deepcopy(row)

    def _received(self, context, *, verify_artifacts=False, active=()):
        groups = {source: [] for source in FACT_SOURCES}
        for source, row in self._deliveries(context, verify_artifacts=verify_artifacts, active=active):
            groups[source].append(row)
        return groups

    @_boundary
    def received_context(self, context) -> list[dict]:
        return [{"fact_source": source, "facts": rows} for source, rows in self._received(context).items() if rows]

    @_boundary
    def received_facts(self, context, schema) -> ProteinFactGroups:
        sources = requested_sources(schema)
        if not sources:
            return {}
        values = self._received(context)
        return {source: deepcopy(values[source]) for source in sources}

    @_boundary
    def validate_received_report(self, context, form, schema) -> None:
        if not requested_sources(schema):
            return
        self.authenticate(context, allow_unsaved=True)
        values = self._values(form, schema)
        actual = self._own(context, verify_artifacts=True) if context.role == "results" else self._received(context)
        self._require(all(self._equal(rows, actual[source]) for source, rows in values.items()))
        self._frozen(context, values)

    @_boundary
    def record_admission(self, context, form, schema, operation_key) -> list[str]:
        if not requested_sources(schema):
            return []
        child, saved, original = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(saved, form) and self._equal(original, schema))
        return _references(self._historical(child, saved, original))

