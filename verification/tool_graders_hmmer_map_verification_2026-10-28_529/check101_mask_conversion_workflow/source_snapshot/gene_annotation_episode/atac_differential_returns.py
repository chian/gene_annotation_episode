"""Exact received atac facts and compound saved-operand authority.

Completed selected publications belong to the result host. This reader follows
their immediate typed returns and frozen operand inheritance using existing
runtime records only. Historical delivery never opens scientific artifacts.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .communication import plain, validate_closed_schema, validate_form
from .episode_receipts import (
    EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION, _validate_report_prefix,
)
from .episode_return_records import EpisodeReturnRecords
from .episode_contract_information import expand_fact_form, validate_saved_fact_form
from .execution_contracts import canonical, digest
from .atac_differential_return_views import (
    FACT_SOURCES, SAVED_SOURCE, requested_atac_sources,
    select_atac_return_facts, validate_atac_fact_values,
)


_RECEIVING_ROLES = {"annotation", "scientific_process"}
_CLOSURE_PREFIX = "atac_received_report_prefix"


def _bundle_references(bundle):
    yield bundle["sheet"]["artifact_ref"]
    yield from (file["artifact_ref"] for row in bundle["tables"] for file in (row["file"],))


class AtacDifferentialReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="atac_return_")
        self.results = owner.atac_results

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0], "context_role_conflict")
        if allow_unsaved and self.db.execute(
                "SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.run_id, context.episode_id)).fetchone() is None:
            own = self.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "UNION ALL SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=? LIMIT 1",
                (self.run_id, context.episode_id, self.run_id, context.episode_id)).fetchone()
            self._require(own is None, "original_commission_required")
        return context

    def _commission(self, parent, child, *, construction=False):
        self.authenticate(parent)
        self.authenticate(child, allow_unsaved=construction)
        self._require(child.path[:-1] == parent.path, "commission_parent_conflict")
        try:
            self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        except ValueError as error:
            raise ValueError(self.failure_prefix + "commission_scope_conflict") from error
        slot = child.path[-1][1]
        self._require(re.fullmatch(r"child_(0|[1-9][0-9]*)", slot) is not None,
            "commission_child_conflict")
        original = plain(child.request).get("report_contract")
        self._require(type(original) is dict, "original_return_schema_required")
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, parent.episode_id, int(slot[6:]))).fetchone()
        if row is None and construction:
            saved = self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(saved is None, "original_commission_required")
            return
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        if selected.get("kind") == "tool":
            # The existing process-revision owner authenticates its construction
            # provenance. This exception retains only its scientific-child edge.
            self._require(selected.get("tool") == "process.revise"
                and child.role == "scientific_process", "original_commission_conflict")
            return
        self._require(selected.get("kind") in {"child", "episode_child", "job_child"},
            "original_commission_conflict")
        self._require(self._equal(selected.get("scope"), child.scope)
            and selected.get("purpose") == original["decision"], "original_commission_conflict")
        declaration = plain(child.request)["message"].get("report_contract_declaration")
        if declaration is None:
            self._require(self._equal(json.loads(selected["schema_json"]), original["measurements"]["schema"]),
                "original_commission_conflict")
        else:
            validate_saved_fact_form(child_role=child.role, submitted_schema_json=selected["schema_json"],
                expanded_schema=original["measurements"]["schema"], declaration=declaration)
            expanded = self._expanded_form(parent, int(slot[6:]), selected, child.role)
            self._require(self._equal(expanded["expanded_schema"], original["measurements"]["schema"])
                and self._equal(expanded["declaration"], declaration), "original_commission_conflict")
        if selected["kind"] in {"episode_child", "job_child"}:
            self._require(selected.get("role") == child.role, "commission_role_conflict")
        if child.role in {"results", "launch", "launch_local"}:
            self._require(self._equal(selected.get("assignment"), child.assignment),
                "commission_assignment_conflict")

    def _expanded_form(self, parent, index, selected, role):
        """Authenticate compact source references against that decision's frame."""
        row = self.db.execute("SELECT purpose,request FROM runtime_model_calls WHERE run_id=? AND episode_id=? "
            "AND call_index=?", (self.run_id, parent.episode_id, index)).fetchone()
        self._require(row is not None and row["purpose"] == "decision", "original_contract_information_required")
        # This existing validator only checks supplied original records. It
        # performs no discovery, catalog refresh, construction or model call.
        from .runtime import Workflow
        from .episode_journal import WorkflowError
        try:
            record = Workflow.validate_contract_information(None, json.loads(row["request"]))
        except WorkflowError as error:
            raise ValueError(self.failure_prefix + "original_contract_information_conflict") from error
        facts = {role: {source: value for source, value in rows.items() if "report_schema" in value}
            for role, rows in record["fact_sources_by_role"].items()}
        return expand_fact_form(selected["schema_json"], child_role=role, facts_by_role=facts,
            permitted_child_roles=record["permitted_child_roles"])

    def _attempt(self, context, index):
        # The shared reader handles literal forms. Compact redelivery has its
        # own original expansion and must not be compared to literal JSON.
        self.authenticate(context)
        attempt = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, index)).fetchone()
        self._require(attempt is not None and attempt["form"] is not None and attempt["failure"] is None,
            "successful_return_required")
        decision = self.db.execute("SELECT response FROM runtime_model_calls WHERE run_id=? AND episode_id=? "
            "AND call_index=?", (self.run_id, context.episode_id, index)).fetchone()
        action = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, index)).fetchone()
        selected = (json.loads(action["action"]) if action is not None else
            {} if decision is None or decision["response"] is None else json.loads(decision["response"]).get("selection", {}))
        contract = json.loads(attempt["contract"])
        schema = contract.get("measurements", {}).get("schema")
        compact_redelivery = (selected.get("kind") == "redeliver_report"
            and not self._equal(json.loads(selected["schema_json"]), schema))
        if not compact_redelivery:
            child, form, schema = super()._attempt(context, index)
        else:
            child = self.context(attempt["child_episode_id"])
            form = json.loads(attempt["form"])
            self._require(child.path[:-1] == context.path, "return_child_contract_conflict")
            expanded = self._expanded_form(context, index, selected, child.role)
            self._require(self._equal(expanded["expanded_schema"], schema)
                and selected.get("delivery_ref") == attempt["delivery_ref"]
                and selected.get("purpose") == contract.get("decision"), "redelivery_conflict")
            earlier = self.db.execute("SELECT child_episode_id,contract FROM runtime_report_attempts WHERE run_id=? "
                "AND parent_episode_id=? AND delivery_ref=? AND decision_index<? ORDER BY decision_index LIMIT 1",
                (self.run_id, context.episode_id, attempt["delivery_ref"], index)).fetchone()
            self._require(earlier is not None and earlier["child_episode_id"] == child.episode_id
                and self._equal(json.loads(earlier["contract"]), child.request.get("report_contract")), "redelivery_origin_conflict")
            frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None, "closed_child_facts_required")
            facts = json.loads(frozen["facts"])
            for name, node in schema.get("properties", {}).items():
                source = node.get("x-source")
                if source is not None:
                    self._require(source in facts and name in form and self._equal(form[name], facts[source]),
                        "frozen_return_conflict")
        self._commission(context, child)
        original = plain(child.request)["report_contract"]["measurements"]["schema"]
        if self._equal(schema, original):
            frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen["form"] is not None
                and self._equal(json.loads(frozen["form"]), form), "frozen_form_conflict")
        return child, form, schema

    @staticmethod
    def _schema(schema):
        schema = plain(schema)
        sources = requested_atac_sources(schema)
        if sources:
            validate_closed_schema(schema)
        return schema, sources

    def _values(self, form, schema):
        schema, _ = self._schema(schema)
        form = plain(form)
        # Shape validation is separate from the completed-publication and
        # received-form authority checked below; no resolver grant is persisted.
        validate_form(form, schema, lambda *_: True)
        values = {}
        for name, node in schema["properties"].items():
            source = node.get("x-source")
            if source not in FACT_SOURCES:
                continue
            rows = validate_atac_fact_values(source, form[name])
            self._require(source not in values or self._equal(values[source], rows), "conflicting_fields")
            values[source] = rows
        return values

    def _frozen(self, context, values):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is not None:
            facts = json.loads(row["facts"])
            self._require(all(source in facts and self._equal(facts[source], rows)
                for source, rows in values.items()), "frozen_facts_conflict")
        return row is not None

    @classmethod
    def _ordered_subset(cls, values, expected):
        for source, rows in values.items():
            remaining = iter(expected.get(source, []))
            for row in rows:
                if not any(cls._equal(row, original) for original in remaining):
                    return False
        return True

    def _own_facts(self, context, sources, *, verify_artifacts):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role == "results" and self.results.applies(context),
            "original_results_owner_required")
        groups = self.results.own_fact_groups(context, verify_artifacts=verify_artifacts)
        self._require(type(groups) is dict and set(groups) == set(FACT_SOURCES), "original_facts_required")
        return {source: validate_atac_fact_values(source, groups[source]) for source in sources}

    def _own_origins(self, context, bundle):
        rows = self.results.completed_saved_bundle_origins(context, bundle)
        self._require(type(rows) is tuple and bool(rows), "completed_bundle_origins_required")
        prefix = re.escape(f"{self.run_id}:{context.episode_id}:")
        result = []
        for row in rows:
            self._require(type(row) is dict and set(row) == {"episode_id", "operation_key"}
                and type(row["episode_id"]) is str and row["episode_id"] == context.episode_id
                and type(row["operation_key"]) is str
                and re.fullmatch(prefix + r"(0|[1-9][0-9]*)", row["operation_key"]) is not None,
                "completed_bundle_origin_conflict")
            if row not in result:
                result.append(deepcopy(row))
        return result

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        return self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (self.run_id, context.episode_id)).fetchall()

    @staticmethod
    def _witness(attempt):
        result = {key: attempt[key] for key in ("decision_index", "delivery_ref", "child_episode_id")}
        result.update(contract_sha256=digest(json.loads(attempt["contract"])),
            form_sha256=digest(json.loads(attempt["form"])))
        return result

    def _closure_prefix(self, context):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        facts = {} if row is None else json.loads(row["facts"])
        self._require(_CLOSURE_PREFIX in facts, "closure_prefix_required")
        return _validate_report_prefix(facts[_CLOSURE_PREFIX])

    def _historical(self, context, form, schema, sources):
        self.authenticate(context)
        values = {source: rows for source, rows in self._values(form, schema).items() if source in sources}
        self._require(self._frozen(context, values), "closed_child_facts_required")
        if context.role == "results":
            expected = self._own_facts(context, values, verify_artifacts=False)
            origins = {canonical(bundle): self._own_origins(context, bundle)
                for bundle in values.get(SAVED_SOURCE, [])}
        elif context.role in _RECEIVING_ROLES:
            prefix = self._closure_prefix(context)
            expected, origins, _ = self._received(context, values, allowed=prefix["attempts"])
        else:
            self._require(False, "unsupported_return_owner")
        self._require(self._ordered_subset(values, expected), "returned_facts_conflict")
        return values, {canonical(bundle): origins[canonical(bundle)]
            for bundle in values.get(SAVED_SOURCE, [])}

    def _received(self, context, sources, *, allowed=None):
        """Read immediate received forms; retain all exact action origins."""
        self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
        self._require(all(source in FACT_SOURCES for source in sources), "unknown_source")
        groups, seen, origins = {source: [] for source in sources}, {source: set() for source in sources}, {}
        attempts, witnesses = self._attempts(context), []
        if allowed is not None:
            _validate_report_prefix({"version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": allowed})
            actual = {row["decision_index"]: self._witness(row) for row in attempts}
            self._require(all(self._equal(saved, actual.get(saved["decision_index"]))
                for saved in allowed), "return_prefix_conflict")
        allowed_indices = None if allowed is None else {row["decision_index"] for row in allowed}
        for attempt in attempts:
            if allowed_indices is not None and attempt["decision_index"] not in allowed_indices:
                continue
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            wanted = tuple(source for source in requested_atac_sources(schema) if source in sources)
            if not wanted:
                continue
            child, form, schema = self._attempt(context, attempt["decision_index"])
            values, child_origins = self._historical(child, form, schema, wanted)
            witnesses.append(self._witness(attempt))
            for source, rows in values.items():
                for row in rows:
                    key = canonical(row)
                    if key not in seen[source]:
                        groups[source].append(deepcopy(row))
                        seen[source].add(key)
                    if source == SAVED_SOURCE:
                        result = origins.setdefault(key, [])
                        result.extend(deepcopy(origin) for origin in child_origins[key] if origin not in result)
        return groups, origins, _validate_report_prefix({
            "version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": witnesses})

    def facts(self, context, schema):
        schema, sources = self._schema(schema)
        if not sources:
            return {}
        self.authenticate(context, allow_unsaved=True)
        if context.role == "results":
            groups = self._own_facts(context, sources, verify_artifacts=False)
        else:
            groups, _, _ = self._received(context, sources)
        return select_atac_return_facts(groups, schema=schema)

    def facts_for_closure(self, context, schema):
        """Freeze the requested facts and private existing-form witnesses."""
        schema, sources = self._schema(schema)
        if not sources:
            return {}
        with self.store.read_snapshot():
            self.authenticate(context, allow_unsaved=True)
            if context.role == "results":
                return select_atac_return_facts(
                    self._own_facts(context, sources, verify_artifacts=False), schema=schema)
            self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
            frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, context.episode_id)).fetchone()
            if frozen is None:
                groups, _, prefix = self._received(context, sources)
            else:
                groups = json.loads(frozen["facts"])
                prefix = self._closure_prefix(context)
                expected, _, _ = self._received(context, sources, allowed=prefix["attempts"])
                selected = select_atac_return_facts(groups, schema=schema)
                self._require(self._ordered_subset(selected, expected), "returned_facts_conflict")
            return {**select_atac_return_facts(groups, schema=schema),
                _CLOSURE_PREFIX: deepcopy(prefix)}

    def validate_received_report(self, context, form, schema):
        schema, sources = self._schema(schema)
        if not sources:
            return
        self.authenticate(context, allow_unsaved=True)
        values = self._values(form, schema)
        frozen = self._frozen(context, values)
        if context.role == "results":
            expected = self._own_facts(context, values, verify_artifacts=not frozen)
        else:
            allowed = self._closure_prefix(context)["attempts"] if frozen else None
            expected, _, _ = self._received(context, values, allowed=allowed)
        self._require(self._ordered_subset(values, expected) if frozen else self._equal(values, expected),
            "returned_facts_conflict")

    def record_admission(self, context, form, schema, operation_key):
        schema, sources = self._schema(schema)
        if not sources:
            return []
        self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
        child, saved, declared = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved) and self._equal(schema, declared), "admitted_form_conflict")
        values, _ = self._historical(child, saved, declared, sources)
        return list(dict.fromkeys(reference for bundle in values.get(SAVED_SOURCE, [])
            for reference in _bundle_references(bundle)))

    def resolve_received(self, context, reference, namespace):
        if namespace not in {None, "artifact"} or context.role not in _RECEIVING_ROLES:
            return False
        groups, _, _ = self._received(context, (SAVED_SOURCE,))
        return any(reference in _bundle_references(bundle) for bundle in groups[SAVED_SOURCE])

    def authenticate_received_saved_bundle(self, context, bundle):
        bundle = validate_atac_fact_values(SAVED_SOURCE, [plain(bundle)])[0]
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in {*_RECEIVING_ROLES, "results"}, "unsupported_return_owner")
        if context.role == "results":
            selector = plain(context.assignment).get("selector", {})
            self._require(self.results.applies(context)
                and selector.get("version") == "atac_differential_result_selector_v1"
                and selector.get("mode") == "saved_sheet_recalculation"
                and self._equal(selector.get("saved_sheet_bundle"), bundle), "saved_assignment_conflict")
        current, allowed, origins, visited = context, None, [], set()
        while True:
            self._require(current.episode_id not in visited, "saved_prefix_conflict")
            visited.add(current.episode_id)
            if current.role in _RECEIVING_ROLES:
                groups, supplied, _ = self._received(current, (SAVED_SOURCE,), allowed=allowed)
                if any(self._equal(bundle, row) for row in groups[SAVED_SOURCE]):
                    origins.extend(origin for origin in supplied[canonical(bundle)] if origin not in origins)
            manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, current.episode_id)
            self._require(self._equal(plain(current.request)["message"].get("knowledge_inheritance"), manifest),
                "saved_prefix_conflict")
            parent_id = manifest["parent_episode_id"]
            if parent_id is None:
                self._require(len(current.path) == 1, "saved_prefix_conflict")
                break
            self._require("received_report_prefix" in manifest, "saved_prefix_required")
            parent = self.context(parent_id)
            self._commission(parent, current, construction=current is context)
            allowed = manifest["received_report_prefix"]["attempts"]
            current = parent
        # Read the existing ledger without the constructor's schema migration.
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.db, self.run_id
        known = set(receipts.known(context.episode_id, baseline=context.role == "results"))
        self._require(bool(origins) and all(reference in known for reference in _bundle_references(bundle)),
            "saved_bundle_not_received")
        return tuple(deepcopy(origins))


__all__ = ["AtacDifferentialReturns"]
