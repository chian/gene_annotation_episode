"""Original requested FBA returns, without source or artifact acquisition.

The result host authenticates completed own actions. This reader follows only
their actual immediate-child typed returns and frozen operand inheritance.
Historical delivery is independent of the availability of scientific bytes.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from method_loop.episode import EpisodeGoal
from method_loop.identities import EpisodeRef

from .communication import plain, validate_form
from .episode_bindings import BindingContext
from .episode_receipts import (
    EpisodeReceipts, RECEIVED_REPORT_PREFIX_VERSION, _validate_report_prefix,
)
from .episode_return_records import EpisodeReturnRecords
from .bvbrc_appservice_custody import AppServiceCustody
from .execution_contracts import canonical, digest
from .flux_balance_return_views import (
    fba_fact_sources, requested_fba_sources, select_fba_return_facts, validate_fba_fact_values,
)


FACT_SOURCES = tuple(fba_fact_sources())
PROJECTION_SOURCE = "flux_balance_measurements"
SAVED_SOURCE = "flux_balance_saved_sheets"
MODEL_SOURCE = "flux_balance_model_views"
EDITED_SOURCE = "flux_balance_edited_models"
ORDINARY_PREFIX = "flux_balance_ordinary_action_prefix"
ORDINARY_PREFIX_VERSION = "ordinary_flux_balance_action_prefix_v1"
_LEGACY_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, "flux_balance_failures")
_FILE_SOURCES = (SAVED_SOURCE, EDITED_SOURCE)


_RECEIVING_ROLES = {"annotation", "scientific_process"}
_CLOSURE_PREFIX = "flux_balance_received_report_prefix"
_CONTRIBUTION_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, MODEL_SOURCE, EDITED_SOURCE)


class FluxBalanceReturns(EpisodeReturnRecords):
    def __init__(self, owner, *, ordinary_backend=None):
        super().__init__(owner.store, owner.run_id, failure_prefix="flux_balance_return_")
        self.results = owner.native_flux_balance_results
        self.declarations = AppServiceCustody(owner.store, owner.run_id)
        self.ordinary_backend = ordinary_backend

    def authenticate(self, context, *, allow_unsaved=False):
        self._require(isinstance(context, BindingContext), "binding_context_required")
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.path and context.role == context.path[-1][0], "context_role_conflict")
        request = plain(context.request)
        self._require(set(request) == {"goal", "message", "report_contract"}
            and type(request["message"]) is dict, "original_request_required")
        if len(context.path) > 1:
            self._require(type(request["report_contract"]) is dict
                and type(request["report_contract"].get("measurements", {}).get("schema")) is dict,
                "original_return_schema_required")
            parent = self.context(EpisodeRef(self.run_id, context.path[:-1]).episode_id)
            self._commission(parent, context, construction=allow_unsaved)
        manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)
        self._require(self._equal(request["message"].get("knowledge_inheritance"), manifest)
            and manifest["parent_episode_id"] == (None if len(context.path) == 1 else parent.episode_id),
            "commission_inheritance_conflict")
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
        self._require(selected.get("kind") in {"child", "episode_child", "job_child"}, "original_commission_conflict")
        self._require(self._equal(selected.get("scope"), child.scope), "commission_scope_conflict")
        if selected["kind"] in {"episode_child", "job_child"}:
            self._require(selected.get("role") == child.role, "commission_role_conflict")
        # Shared original-frame validators distinguish compact declarations from
        # expanded saved contracts. Never compare their raw schema JSON.
        schema = self._child_contract(child, selected, sent)
        request, assignment = plain(child.request), plain(child.assignment)
        initial = self._json(selected.get("initial_report_json"))
        self._require(type(initial) is dict, "commission_initial_report_conflict")
        goal = EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
            objective=selected.get("goal"), result_contract=schema)
        self._require(self._equal(request["goal"], goal.as_record())
            and self._equal(request["message"].get("initial_report"), initial), "commission_goal_conflict")
        original_assignment = selected.get("assignment", {})
        if child.role == "scientific_process" and "selection" in assignment:
            from .scientific_process_records import (
                scientific_digest, scientific_invocation_ref, selector_selection, validate_filled_process,
            )
            selected_assignment = {**assignment, "selection": selector_selection(assignment["selection"])}
            self._require(self._equal(original_assignment, assignment)
                or self._equal(original_assignment, selected_assignment), "commission_assignment_conflict")
            filled = validate_filled_process(request["message"].get("scientific_process"))
            invocation = {"objective": request["goal"]["objective"], "scope": plain(child.scope),
                "purpose": request["report_contract"]["decision"], "report_schema": schema,
                "initial_report": initial}
            self._require(self._equal(filled["selection"], assignment["selection"])
                and filled["assignment_sha256"] == scientific_digest(assignment)
                and filled["invocation_sha256"] == scientific_digest(invocation)
                and request["message"].get("scientific_invocation_ref") == scientific_invocation_ref(self.run_id, child.path),
                "commission_assignment_conflict")
        else:
            self._require(self._equal(original_assignment, assignment), "commission_assignment_conflict")

    def _attempt(self, context, index):
        # This shared reader authenticates redelivery against its own frozen
        # frame and validates original and compact return declarations.
        child, form, schema = AppServiceCustody._attempt(self, context, index)
        self._commission(context, child)
        return child, form, schema

    def _values(self, form, schema):
        schema, form = plain(schema), plain(form)
        requested_fba_sources(schema)
        validate_form(form, schema, lambda *_: True)
        values = {}
        for name, node in schema["properties"].items():
            source = node.get("x-source")
            if source not in FACT_SOURCES:
                continue
            rows = validate_fba_fact_values(source, form[name])
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
        self._require(context.role == "results" and self.results is not None and self.results.applies(context),
            "original_results_owner_required")
        groups = self.results.own_fact_groups(context, verify_artifacts=verify_artifacts)
        self._require(type(groups) is dict and all(source in groups for source in _LEGACY_SOURCES),
            "original_facts_required")
        return {source: validate_fba_fact_values(source, groups.get(source, [])) for source in sources}

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
        if self._ordinary_prefix(context) is not None:
            values, metadata = self._historical_ordinary(context, form, schema, sources)
            origins = {}
            for source in _CONTRIBUTION_SOURCES:
                for row, meta in zip(values.get(source, []), metadata.get(source, [])):
                    owners = origins.setdefault(canonical(row), [])
                    owners.extend(owner for owner in meta["origins"] if owner not in owners)
            return values, origins
        self.authenticate(context)
        values = {source: rows for source, rows in self._values(form, schema).items() if source in sources}
        self._require(self._frozen(context, values), "closed_child_facts_required")
        if context.role == "results":
            expected = self._own_facts(context, values, verify_artifacts=False)
            origins = {canonical(row): [context.episode_id] for source in _CONTRIBUTION_SOURCES
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
            wanted = tuple(source for source in requested_fba_sources(schema) if source in sources)
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
        sources = requested_fba_sources(schema)
        if not sources:
            return {}
        if self._uses_ordinary(context):
            return self.facts(context, schema)
        self.authenticate(context, allow_unsaved=True)
        if context.role == "results":
            groups = self._own_facts(context, sources, verify_artifacts=False)
        else:
            groups, _, _ = self._received(context, sources)
        return select_fba_return_facts(groups, schema=schema)

    def facts_for_closure(self, context, schema):
        """Freeze requested values and their original forwarding witnesses.

        The private prefix belongs in existing runtime_forms.facts. It is not
        a fact source, a model-facing field, a receipt grant or an observation.
        """
        schema = plain(schema)
        sources = requested_fba_sources(schema)
        if not sources:
            return {}
        if self._uses_ordinary(context):
            # The new private key is supplied only by ordinary_closure_facts,
            # through the registry's actual-completion callback.
            return self.facts(context, schema)
        with self.store.read_snapshot():
            self.authenticate(context, allow_unsaved=True)
            if context.role == "results":
                return select_fba_return_facts(
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
                selected = select_fba_return_facts(groups, schema=schema)
                self._require(self._ordered_subset(selected, expected), "returned_facts_conflict")
            return {**select_fba_return_facts(groups, schema=schema),
                _CLOSURE_PREFIX: deepcopy(_validate_report_prefix(prefix))}

    def validate_received_report(self, context, form, schema):
        if self._uses_ordinary(context):
            self.authenticate(context, allow_unsaved=True)
            if self._ordinary_prefix(context) is not None:
                # A stripped initial form must still authenticate the original
                # full closed contract and its exact recorded action prefix.
                groups = self._closed_ordinary(context)[0]
            else:
                sources = requested_fba_sources(plain(schema))
                if not sources:
                    return
                groups = self._combined(context, sources, verify_artifacts=True)[0]
            values = self._values(form, schema)
            self._require(self._equal(values, {source: groups[source] for source in values}),
                "returned_facts_conflict")
            return
        if not requested_fba_sources(plain(schema)):
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
        if not requested_fba_sources(plain(schema)):
            return []
        self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
        child, saved, declared = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved) and self._equal(schema, declared), "admitted_form_conflict")
        values, _ = self._historical(child, saved, declared, requested_fba_sources(plain(declared)))
        return list(dict.fromkeys(row["artifact_ref"] for source in _FILE_SOURCES
            for row in values.get(source, [])))

    def resolve_received(self, context, reference, namespace):
        if namespace not in {None, "artifact"} or context.role not in _RECEIVING_ROLES:
            return False
        groups = (self._combined(context, _FILE_SOURCES,
            prefix=self._ordinary_prefix(context), verify_artifacts=False)[0]
            if self._uses_ordinary(context) else self._received(context, _FILE_SOURCES)[0])
        return any(row["artifact_ref"] == reference for source in _FILE_SOURCES for row in groups[source])

    def _form_facts(self, context):
        row = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        return None if row is None else json.loads(row["facts"])

    def _ordinary_prefix(self, context):
        facts = self._form_facts(context)
        if facts is None or ORDINARY_PREFIX not in facts:
            return None
        value = facts[ORDINARY_PREFIX]
        self._require(type(value) is dict
            and set(value) == {"version", "witnesses", "received_prefix", "identities"}
            and value["version"] == ORDINARY_PREFIX_VERSION
            and type(value["witnesses"]) is list and type(value["identities"]) is dict,
            "ordinary_prefix_conflict")
        _validate_report_prefix(value["received_prefix"])
        return deepcopy(value)

    def _uses_ordinary(self, context):
        if context.role not in _RECEIVING_ROLES:
            return False
        facts = self._form_facts(context)
        return (facts is not None and ORDINARY_PREFIX in facts
            or facts is None and self.ordinary_backend is not None)

    def _ordinary_records(self, context, sources, *, witnesses=None, verify_artifacts=False):
        backend = self.ordinary_backend
        if backend is None:
            self._require(not witnesses, "ordinary_backend_unavailable")
            return []
        if witnesses is None:
            rows = backend.own_fact_records(context, sources=sources,
                verify_artifacts=verify_artifacts)
        else:
            # The backend's aggregate port is called per witness so that each
            # source-free public row remains bound to its actual producer.
            rows = [{"witness": witness, "facts": backend.authenticate_frozen_fact_records(
                context, witnesses=[witness], sources=sources)} for witness in witnesses]
        self._require(type(rows) is list, "ordinary_facts_conflict")
        seen, result = set(), []
        for row in rows:
            self._require(type(row) is dict and set(row) == {"witness", "facts"}
                and type(row["witness"]) is dict and type(row["facts"]) is dict,
                "ordinary_facts_conflict")
            witness = plain(row["witness"])
            self._require(type(witness.get("source_ref")) is str
                and bool(witness["source_ref"]) and canonical(witness) not in seen,
                "ordinary_witness_conflict")
            seen.add(canonical(witness))
            self._require(all(source in row["facts"] for source in sources), "ordinary_facts_conflict")
            result.append({"witness": witness, "facts": {source:
                validate_fba_fact_values(source, row["facts"][source]) for source in sources}})
        return result

    @staticmethod
    def _ordinary_identity(source, source_ref, row):
        # Entire selectors include snapshot, explicit ordinals/duplicates,
        # filters and local window. File and failure identities stay literal.
        selected = row.get("selector", row)
        return canonical({"source": source, "source_ref": source_ref, "selection": selected})

    def _combined(self, context, sources, *, prefix=None, verify_artifacts=False):
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in _RECEIVING_ROLES, "unsupported_return_owner")
        groups, metadata = {source: [] for source in sources}, {source: [] for source in sources}
        seen = {source: {} for source in sources}

        def append(source, row, meta):
            self._require(type(meta) is dict and set(meta) == {"identity", "origins"}
                and type(meta["identity"]) is str and type(meta["origins"]) is list
                and all(type(origin) is str for origin in meta["origins"]), "ordinary_identity_conflict")
            index = seen[source].get(meta["identity"])
            if index is None:
                seen[source][meta["identity"]] = len(groups[source])
                groups[source].append(deepcopy(row))
                metadata[source].append(deepcopy(meta))
            else:
                self._require(self._equal(groups[source][index], row), "ordinary_identity_conflict")
                owners = metadata[source][index]["origins"]
                owners.extend(owner for owner in meta["origins"] if owner not in owners)

        allowed = None if prefix is None else prefix["received_prefix"]["attempts"]
        attempts, witnesses = self._attempts(context), []
        if allowed is not None:
            actual = {row["decision_index"]: self._witness(row) for row in attempts}
            self._require(all(self._equal(saved, actual.get(saved["decision_index"]))
                for saved in allowed), "return_prefix_conflict")
        for attempt in attempts:
            if allowed is not None and not any(self._equal(self._witness(attempt), saved) for saved in allowed):
                continue
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            wanted = tuple(source for source in requested_fba_sources(schema) if source in sources)
            if not wanted:
                continue
            child, form, schema = self._attempt(context, attempt["decision_index"])
            if self._ordinary_prefix(child) is not None:
                values, identities = self._historical_ordinary(child, form, schema, wanted)
            else:
                values, origins = self._historical(child, form, schema, wanted)
                identities = {source: [{"identity": canonical({"legacy_source": source, "value": row}),
                    "origins": origins.get(canonical(row), [])} for row in rows]
                    for source, rows in values.items()}
            witnesses.append(self._witness(attempt))
            for source, rows in values.items():
                for row, meta in zip(rows, identities[source]):
                    append(source, row, meta)
        own = self._ordinary_records(context, sources,
            witnesses=None if prefix is None else prefix["witnesses"], verify_artifacts=verify_artifacts)
        for record in own:
            for source, rows in record["facts"].items():
                for row in rows:
                    append(source, row, {"identity": self._ordinary_identity(
                        source, record["witness"]["source_ref"], row), "origins": [context.episode_id]})
        closed = {"version": ORDINARY_PREFIX_VERSION,
            "witnesses": [deepcopy(row["witness"]) for row in own],
            "received_prefix": {"version": RECEIVED_REPORT_PREFIX_VERSION, "attempts": witnesses},
            "identities": metadata}
        return groups, closed

    def _closed_ordinary(self, context):
        self.authenticate(context)
        prefix = self._ordinary_prefix(context)
        self._require(prefix is not None, "ordinary_prefix_required")
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {})
        sources = requested_fba_sources(schema)
        self._require(set(prefix["identities"]) == set(sources), "ordinary_prefix_conflict")
        groups, expected = self._combined(context, sources, prefix=prefix, verify_artifacts=False)
        self._require(self._equal(prefix, expected), "ordinary_prefix_conflict")
        frozen = self._form_facts(context)
        self._require(all(source in frozen and self._equal(frozen[source], rows)
            for source, rows in groups.items()), "frozen_facts_conflict")
        return groups, expected

    def _historical_ordinary(self, context, form, schema, sources):
        groups, prefix = self._closed_ordinary(context)
        values = {source: rows for source, rows in self._values(form, schema).items() if source in sources}
        metadata = {}
        for source, rows in values.items():
            cursor, metadata[source] = 0, []
            for row in rows:
                while cursor < len(groups[source]) and not self._equal(row, groups[source][cursor]):
                    cursor += 1
                self._require(cursor < len(groups[source]), "returned_facts_conflict")
                metadata[source].append(deepcopy(prefix["identities"][source][cursor]))
                cursor += 1
        return values, metadata

    def facts(self, context, schema):
        """Public requested groups from actual own actions and typed child returns."""
        schema = plain(schema)
        sources = requested_fba_sources(schema)
        if not sources:
            return {}
        if not self._uses_ordinary(context):
            return self.received_facts(context, schema)
        groups = (self._closed_ordinary(context)[0] if self._ordinary_prefix(context) is not None
            else self._combined(context, sources, verify_artifacts=True)[0])
        return select_fba_return_facts(groups, schema=schema)

    def ordinary_closure_facts(self, context, schema):
        """Private action/view associations; called only at actual closure."""
        sources = requested_fba_sources(plain(schema))
        if not sources or not self._uses_ordinary(context):
            return {}
        with self.store.read_snapshot():
            prefix = (self._closed_ordinary(context)[1] if self._ordinary_prefix(context) is not None
                else self._combined(context, sources, verify_artifacts=True)[1])
            return {ORDINARY_PREFIX: deepcopy(prefix)}

    def authenticate_received_saved_sheet(self, context, file: dict) -> tuple[str, ...]:
        file = validate_fba_fact_values(SAVED_SOURCE, [plain(file)])[0]
        self.authenticate(context, allow_unsaved=True)
        self._require(context.role in {*_RECEIVING_ROLES, "results"}, "unsupported_return_owner")
        if context.role == "results":
            selector = plain(context.assignment).get("selector", {})
            self._require(self.results.applies(context)
                and selector.get("version") == "flux_balance_result_selector_v1"
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


__all__ = ["FluxBalanceReturns", "ORDINARY_PREFIX", "ORDINARY_PREFIX_VERSION"]
