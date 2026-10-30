"""Original requested fluorescence returns, without source or artifact acquisition.

The result host authenticates completed own actions. This reader follows only
their actual immediate-child typed returns and frozen operand inheritance.
Historical delivery is independent of the availability of scientific bytes.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .communication import plain, validate_form
from .episode_receipts import (
    EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION, _validate_report_prefix,
)
from .episode_return_records import EpisodeReturnRecords
from .bvbrc_appservice_custody import AppServiceCustody
from .execution_contracts import canonical, digest
from .fluorescence_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, requested_fluorescence_sources,
    select_fluorescence_return_facts, validate_fluorescence_fact_values,
)


_RECEIVING_ROLES = {"annotation", "scientific_process"}
_CLOSURE_PREFIX = "fluorescence_received_report_prefix"
_CONTRIBUTION_SOURCES = (PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE)


class FluorescenceReturns(EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="fluorescence_return_")
        self.results = owner.native_fluorescence_results
        self.declarations = AppServiceCustody(owner.store, owner.run_id)

    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.path and context.role == context.path[-1][0], "context_role_conflict")
        request = plain(context.request)
        self._require(set(request) == {"goal", "message", "report_contract"}
            and type(request["message"]) is dict, "original_request_required")
        if len(context.path) > 1:
            self._require(type(request["report_contract"]) is dict
                and type(request["report_contract"].get("measurements", {}).get("schema")) is dict,
                "original_return_schema_required")
        return context

    def _selection(self, parent, index, *, unsaved=False):
        return self.declarations._selection(parent, index, unsaved=unsaved)

    def _selected_form(self, selected, role, sent):
        return self.declarations._selected_form(selected, role, sent)

    def _child_contract(self, child, selected, sent):
        return self.declarations._child_contract(child, selected, sent)

    _report_contract = staticmethod(AppServiceCustody._report_contract)

    def _json(self, raw):
        return self.declarations._json(raw)

    def _commission(self, parent, child, *, construction=False):
        self._require(child.path[:-1] == parent.path, "commission_parent_conflict")
        try:
            self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        except ValueError as error:
            raise ValueError(self.failure_prefix + "commission_scope_conflict") from error
        slot = child.path[-1][1]
        self._require(re.fullmatch(r"child_(0|[1-9][0-9]*)", slot) is not None, "commission_child_conflict")
        saved = self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.run_id, child.episode_id)).fetchone()
        unsaved = construction and saved is None
        selected, sent = self._selection(parent, int(slot[6:]), unsaved=unsaved)
        if selected.get("kind") == "tool":
            self._require(selected.get("tool") == "process.revise" and child.role == "scientific_process",
                "original_commission_conflict")
            return
        self._require(selected.get("kind") in {"child", "episode_child", "job_child"}, "original_commission_conflict")
        self._require(self._equal(selected.get("scope"), child.scope), "commission_scope_conflict")
        if selected["kind"] in {"episode_child", "job_child"}:
            self._require(selected.get("role") == child.role, "commission_role_conflict")
        if child.role in {"results", "launch", "launch_local", "launch_hpc", "launch_api"}:
            self._require(self._equal(selected.get("assignment"), child.assignment), "commission_assignment_conflict")
        # Shared original-frame validators distinguish compact declarations from
        # expanded saved contracts. Never compare their raw schema JSON.
        self._child_contract(child, selected, sent)

    def _attempt(self, context, index):
        # This shared reader authenticates redelivery against its own frozen
        # frame and validates original and compact return declarations.
        child, form, schema = AppServiceCustody._attempt(self, context, index)
        self._commission(context, child)
        return child, form, schema

    def _values(self, form, schema):
        schema, form = plain(schema), plain(form)
        requested_fluorescence_sources(schema)
        validate_form(form, schema, lambda *_: True)
        values = {}
        for name, node in schema["properties"].items():
            source = node.get("x-source")
            if source not in FACT_SOURCES:
                continue
            rows = validate_fluorescence_fact_values(source, form[name])
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
        self._require(type(groups) is dict and all(source in groups for source in FACT_SOURCES),
            "original_facts_required")
        return {source: validate_fluorescence_fact_values(source, groups[source]) for source in sources}

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
            origins = {canonical(row): list(self.results.receipts.contribution_origins(context, source, row))
                for source in _CONTRIBUTION_SOURCES
                for row in values.get(source, [])}
        elif context.role in _RECEIVING_ROLES:
            prefix = self._closure_prefix(context)
            expected, origins, _ = self._received(context, values, allowed=prefix["attempts"])
        else:
            self._require(False, "unsupported_return_owner")
        self._require(self._ordered_subset(values, expected), "returned_facts_conflict")
        # Preserve the contribution's original owner for credit even when only
        # measurements were returned. Artifact grants still use SAVED_SOURCE.
        return values, {canonical(row): origins[canonical(row)] for source in _CONTRIBUTION_SOURCES
            for row in values.get(source, [])}

    def _received(self, context, sources, *, allowed=None):
        self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
        groups, seen, origins = {source: [] for source in sources}, {source: set() for source in sources}, {}
        attempts, witnesses = self._attempts(context), []
        if allowed is not None:
            # A recorded prefix must still refer to the exact original saved
            # forms. Missing/altered witnesses are errors, not permission to
            # silently reconstruct a different historical publication.
            actual = {row["decision_index"]: self._witness(row) for row in attempts}
            self._require(all(self._equal(saved, actual.get(saved["decision_index"]))
                for saved in allowed), "return_prefix_conflict")
        for attempt in attempts:
            if allowed is not None:
                if not any(self._equal(self._witness(attempt), saved) for saved in allowed):
                    continue
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            wanted = tuple(source for source in requested_fluorescence_sources(schema) if source in sources)
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
                    if source in _CONTRIBUTION_SOURCES:
                        result = origins.setdefault(key, [])
                        result.extend(origin for origin in child_origins[key] if origin not in result)
        return groups, origins, witnesses

    def received_facts(self, context, schema):
        schema = plain(schema)
        sources = requested_fluorescence_sources(schema)
        if not sources:
            return {}
        self.authenticate(context, allow_unsaved=True)
        if context.role == "results":
            groups = self._own_facts(context, sources, verify_artifacts=False)
        else:
            groups, _, _ = self._received(context, sources)
        return select_fluorescence_return_facts(groups, schema=schema)

    def facts_for_closure(self, context, schema):
        """Freeze requested values and their original forwarding witnesses.

        The private prefix belongs in existing runtime_forms.facts. It is not
        a fact source, a model-facing field, a receipt grant or an observation.
        """
        schema = plain(schema)
        sources = requested_fluorescence_sources(schema)
        if not sources:
            return {}
        with self.store.read_snapshot():
            self.authenticate(context, allow_unsaved=True)
            if context.role == "results":
                return select_fluorescence_return_facts(
                    self._own_facts(context, sources, verify_artifacts=False), schema=schema)
            self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
            frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, context.episode_id)).fetchone()
            if frozen is None:
                groups, _, witnesses = self._received(context, sources)
                prefix = {"version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": witnesses}
            else:
                groups = json.loads(frozen["facts"])
                prefix = self._closure_prefix(context)
                expected, _, _ = self._received(context, sources, allowed=prefix["attempts"])
                selected = select_fluorescence_return_facts(groups, schema=schema)
                self._require(self._ordered_subset(selected, expected), "returned_facts_conflict")
            return {**select_fluorescence_return_facts(groups, schema=schema),
                _CLOSURE_PREFIX: deepcopy(_validate_report_prefix(prefix))}

    def validate_received_report(self, context, form, schema):
        if not requested_fluorescence_sources(plain(schema)):
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
        if not requested_fluorescence_sources(plain(schema)):
            return []
        self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
        child, saved, declared = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved) and self._equal(schema, declared), "admitted_form_conflict")
        values, _ = self._historical(child, saved, declared, requested_fluorescence_sources(plain(declared)))
        return list(dict.fromkeys(row["artifact_ref"] for row in values.get(SAVED_SOURCE, [])))

    def resolve_received(self, context, reference, namespace):
        if namespace not in {None, "artifact"} or context.role not in _RECEIVING_ROLES:
            return False
        groups, _, _ = self._received(context, (SAVED_SOURCE,))
        return any(row["artifact_ref"] == reference for row in groups[SAVED_SOURCE])

    def authenticate_received_saved_sheet(self, context, file: dict) -> tuple[str, ...]:
        file = validate_fluorescence_fact_values(SAVED_SOURCE, [plain(file)])[0]
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in {*_RECEIVING_ROLES, "results"}, "unsupported_return_owner")
        if context.role == "results":
            selector = plain(context.assignment).get("selector", {})
            self._require(self.results.applies(context)
                and selector.get("version") == "fluorescence_result_selector_v1"
                and selector.get("mode") == "saved_sheet_recalculation"
                and self._equal(selector.get("saved_sheet_file"), file), "saved_assignment_conflict")
        # Only selected-operand authentication walks frozen inherited receipt
        # prefixes. It never expands the episode's received facts or steering.
        current, allowed, origins, visited = context, None, [], set()
        while True:
            self._require(current.episode_id not in visited, "saved_prefix_conflict")
            visited.add(current.episode_id)
            if current.role in _RECEIVING_ROLES:
                groups, supplied, _ = self._received(current, (SAVED_SOURCE,), allowed=allowed)
                if any(self._equal(file, row) for row in groups[SAVED_SOURCE]):
                    origins.extend(origin for origin in supplied[canonical(file)] if origin not in origins)
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
        receipts = EpisodeReceipts(self.store, self.run_id)
        known = receipts.known(context.episode_id, baseline=context.role == "results")
        self._require(bool(origins) and file["artifact_ref"] in known, "saved_sheet_not_received")
        return tuple(origins)


__all__ = ["FluorescenceReturns"]
