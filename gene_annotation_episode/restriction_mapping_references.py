"""Read restriction-name authority from original work and requested receipts.

Names are case-sensitive catalog identifiers, not Store handles. This reader
performs no acquisition, numerical calculation, receipt mutation or forwarding.
"""
from __future__ import annotations

import json
import re

from .boundary_validation import parse_json_object
from .communication import interpretation_schema, plain, validate_form
from .episode_receipts import EpisodeReceipts, _validate_report_prefix
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import digest
from .restriction_mapping_action_records import RestrictionMappingActionRecords
from .restriction_mapping_returns import (
    requested_restriction_projections, validate_frozen_restriction_return,
)


_SOURCE = "restriction_mapping_results"


class RestrictionMappingReferences(EpisodeReturnRecords):
    def __init__(self, store, run_id):
        super().__init__(store, run_id, failure_prefix="restriction_mapping_reference_")

    def authenticate(self, context, *, allow_unsaved=False):
        try:
            super().authenticate(context, allow_unsaved=allow_unsaved)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
            if str(error).startswith(self.failure_prefix):
                raise
            raise ValueError(self.failure_prefix + "context_invalid") from error
        self._require(bool(context.path) and context.role == context.path[-1][0],
            "context_role_conflict")
        return context

    def context(self, episode_id):
        try:
            return super().context(episode_id)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
            if str(error).startswith(self.failure_prefix):
                raise
            raise ValueError(self.failure_prefix + "saved_context_invalid") from error

    def _json(self, value, code):
        try:
            return json.loads(value)
        except (ValueError, TypeError, RecursionError) as error:
            raise ValueError(self.failure_prefix + code) from error

    def _requested(self, schema):
        try:
            return requested_restriction_projections(schema)
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            raise ValueError(self.failure_prefix + "requested_source_invalid") from error

    def _names(self, form, schema, facts):
        requested = self._requested(schema)
        if _SOURCE not in requested:
            return set()
        try:
            validate_frozen_restriction_return(form, schema, facts)
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            raise ValueError(self.failure_prefix + "frozen_source_conflict") from error
        names = set()
        for field, node in schema["properties"].items():
            if node.get("x-source") != _SOURCE:
                continue
            rows = node["items"]["properties"].get("enzyme_rows", {})
            if "name" not in rows.get("items", {}).get("properties", {}):
                continue
            for group in form[field]:
                for enzyme in group.get("enzyme_rows") or []:
                    names.add(enzyme["name"])
        return names

    def _own_frozen_names(self, context):
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema")
        if not isinstance(schema, dict) or _SOURCE not in self._requested(schema):
            return set()
        row = self.db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if row is None:
            return set()
        facts = self._json(row["facts"], "frozen_facts_invalid")
        self._require(type(facts) is dict, "frozen_facts_invalid")
        # An open episode has no frozen result yet. Absence is not an empty
        # source, and a candidate's non-source interpretation grants nothing.
        if _SOURCE not in facts:
            return set()
        if row["form"] is not None:
            form = self._json(row["form"], "frozen_form_invalid")
        else:
            # Host facts can be frozen before the model's first form admission.
            # Build only requested source fields from that saved host record.
            form = {field: facts[_SOURCE] for field, node in schema["properties"].items()
                if node.get("x-source") == _SOURCE}
        return self._names(form, schema, facts)

    def _commission(self, parent, child):
        self._require(child.path[:-1] == parent.path, "commission_parent_conflict")
        try:
            self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        except ValueError as error:
            raise ValueError(self.failure_prefix + "commission_scope_conflict") from error
        slot = child.path[-1][1]
        self._require(type(slot) is str and re.fullmatch(r"child_(0|[1-9][0-9]*)", slot) is not None,
            "commission_child_conflict")
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, parent.episode_id, int(slot[6:]))).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = self._json(row["action"], "original_commission_invalid")
        original = plain(child.request).get("report_contract")
        self._require(type(selected) is dict and isinstance(original, dict), "original_commission_invalid")
        if selected.get("kind") == "tool":
            self._require(selected.get("tool") == "process.revise" and child.role == "scientific_process",
                "original_commission_conflict")
            return selected
        self._require(selected.get("kind") in {"child", "episode_child", "job_child"},
            "original_commission_conflict")
        schema = self._json(selected.get("schema_json"), "original_commission_invalid")
        declaration = plain(child.request).get("message", {}).get("report_contract_declaration")
        if declaration is not None:
            from .episode_contract_information import validate_saved_fact_form
            try:
                schema = validate_saved_fact_form(child_role=child.role,
                    submitted_schema_json=selected["schema_json"],
                    expanded_schema=original.get("measurements", {}).get("schema"),
                    declaration=declaration)
            except (ValueError, TypeError, KeyError, RecursionError) as error:
                raise ValueError(self.failure_prefix + "original_commission_invalid") from error
        self._require(self._equal(selected.get("scope"), child.scope)
            and self._equal(schema, original.get("measurements", {}).get("schema"))
            and selected.get("purpose") == original.get("decision"), "original_commission_conflict")
        if selected["kind"] in {"episode_child", "job_child"}:
            self._require(selected.get("role") == child.role, "commission_role_conflict")
        if child.role == "results":
            self._require(self._equal(selected.get("assignment"), child.assignment),
                "commission_assignment_conflict")
        return selected

    def _initial_names(self, context):
        request = plain(context.request)
        initial = request.get("message", {}).get("initial_report")
        schema = (request.get("report_contract") or {}).get("measurements", {}).get("schema")
        if initial is None or not isinstance(schema, dict):
            return set()
        names = set()
        def collect(value, namespace=None):
            if namespace == "restriction_enzyme":
                names.add(value)
            return True
        try:
            validate_form(initial, interpretation_schema(schema), collect)
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            raise ValueError(self.failure_prefix + "original_initial_report_invalid") from error
        return names

    def _initial_catalog_reference(self, context, reference):
        current, seen = context, set()
        while reference in self._initial_names(current):
            self._require(current.episode_id not in seen, "receipt_lineage_cycle")
            seen.add(current.episode_id)
            manifest = self._manifest(current)
            if manifest is None or manifest["parent_episode_id"] is None:
                return False
            self._require(manifest["parent_episode_id"] not in seen, "receipt_lineage_cycle")
            parent = self.context(manifest["parent_episode_id"])
            selected = self._commission(parent, current)
            if "initial_report_json" not in selected:
                return False
            try:
                initial = parse_json_object(selected["initial_report_json"])
            except (ValueError, TypeError, RecursionError) as error:
                raise ValueError(self.failure_prefix + "original_initial_report_invalid") from error
            self._require(self._equal(initial,
                plain(current.request)["message"]["initial_report"]), "original_initial_report_conflict")
            through = manifest["through_receipt_index"]
            self._require(type(through) is int and through >= 0, "catalog_cutoff_required")
            before = int(current.path[-1][1][6:])  # _commission validated child_N.
            if parent.role == "scientific_process":
                self._manifest(parent)
                try:
                    own = RestrictionMappingActionRecords(self.store, self.run_id).own_enzyme_reference(
                        parent, reference, before_decision_index=before, through_receipt_index=through)
                except (ValueError, TypeError, KeyError, RecursionError) as error:
                    raise ValueError(self.failure_prefix + "initial_catalog_authority_invalid") from error
                if own:
                    return True
            # Only an explicitly supplied original initial name may cross the
            # next boundary; an ancestor's available catalog supplies no grant.
            current = parent
        return False

    def _attempt(self, context, index):
        try:
            child, form, schema = super()._attempt(context, index)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
            if str(error).startswith(self.failure_prefix):
                raise
            raise ValueError(self.failure_prefix + "attempt_invalid") from error
        self._commission(context, child)
        self._require(child.role == "scientific_process", "scientific_source_owner_required")
        row = self.db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, child.episode_id)).fetchone()
        self._require(row is not None, "closed_child_facts_required")
        original = plain(child.request)["report_contract"]["measurements"]["schema"]
        if self._equal(schema, original):
            self._require(row["form"] is not None
                and self._equal(self._json(row["form"], "frozen_form_invalid"), form),
                "frozen_form_conflict")
        facts = self._json(row["facts"], "frozen_facts_invalid")
        return self._names(form, schema, facts)

    def _witness(self, attempt):
        witness = {key: attempt[key] for key in ("decision_index", "delivery_ref", "child_episode_id")}
        try:
            witness.update(contract_sha256=digest(self._json(attempt["contract"], "attempt_contract_invalid")),
                form_sha256=digest(self._json(attempt["form"], "attempt_form_invalid")))
        except (ValueError, TypeError, RecursionError) as error:
            raise ValueError(self.failure_prefix + "attempt_witness_invalid") from error
        return witness

    def _received_names(self, context, allowed):
        rows = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (self.run_id, context.episode_id)).fetchall()
        if allowed is not None:
            by_index = {row["decision_index"]: row for row in rows}
            self._require(all(witness["decision_index"] in by_index
                and self._equal(self._witness(by_index[witness["decision_index"]]), witness)
                for witness in allowed), "received_prefix_conflict")
            indices = {witness["decision_index"] for witness in allowed}
            rows = [row for row in rows if row["decision_index"] in indices]
        names = set()
        for row in rows:
            contract = self._json(row["contract"], "attempt_contract_invalid")
            self._require(type(contract) is dict, "attempt_contract_invalid")
            schema = contract.get("measurements", {}).get("schema")
            if isinstance(schema, dict) and _SOURCE in self._requested(schema):
                names.update(self._attempt(context, row["decision_index"]))
        return names

    def _manifest(self, context):
        declared = plain(context.request).get("message", {}).get("knowledge_inheritance")
        table = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_receipt_inheritance'").fetchone()
        row = None if table is None else self.db.execute("SELECT 1 FROM runtime_receipt_inheritance "
            "WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)).fetchone()
        if row is None:
            self._require(declared is None or type(declared) is dict and declared.get("parent_episode_id") is None,
                "inheritance_manifest_required")
            return None
        try:
            manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            raise ValueError(self.failure_prefix + "inheritance_manifest_invalid") from error
        if manifest["parent_episode_id"] is not None or declared is not None:
            self._require(self._equal(declared, manifest), "inheritance_manifest_conflict")
        return manifest

    def _received_reference(self, context, reference):
        current, allowed, seen, found = context, None, set(), False
        while True:
            self._require(current.episode_id not in seen, "receipt_lineage_cycle")
            seen.add(current.episode_id)
            found = reference in self._received_names(current, allowed) or found
            manifest = self._manifest(current)
            if manifest is None or manifest["parent_episode_id"] is None:
                return found
            self._require("received_report_prefix" in manifest, "received_prefix_required")
            try:
                allowed = _validate_report_prefix(manifest["received_report_prefix"])["attempts"]
            except (ValueError, TypeError, KeyError, RecursionError) as error:
                raise ValueError(self.failure_prefix + "received_prefix_invalid") from error
            self._require(manifest["parent_episode_id"] not in seen, "receipt_lineage_cycle")
            parent = self.context(manifest["parent_episode_id"])
            self._commission(parent, current)
            current = parent

    def frozen_reference(self, context, reference, namespace):
        """Resolve a closed scientific return's requested names without live work."""
        if namespace != "restriction_enzyme":
            return None
        self.authenticate(context)
        if context.role != "scientific_process" or type(reference) is not str or not reference:
            return False
        with self.store.read_snapshot():
            return reference in self._own_frozen_names(context)

    def resolve(self, context, reference, namespace):
        if namespace != "restriction_enzyme":
            return None
        self.authenticate(context)
        if type(reference) is not str or not reference:
            return False
        with self.store.read_snapshot():
            if context.role == "scientific_process":
                if reference in self._own_frozen_names(context):
                    return True
                try:
                    own = RestrictionMappingActionRecords(self.store, self.run_id).own_enzyme_reference(context, reference)
                except (ValueError, TypeError, KeyError, RecursionError) as error:
                    raise ValueError(self.failure_prefix + "own_authority_invalid") from error
                if own:
                    return True
            return (self._initial_catalog_reference(context, reference)
                or self._received_reference(context, reference))
