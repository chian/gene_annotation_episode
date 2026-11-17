"""Original commissioning, frozen receipt prefixes and recorded compact redelivery."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.episode_contract_information import expand_fact_form, validate_saved_fact_form
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import _ASSIGNED_ROLES
from gene_annotation_episode.episodic_workflow.root.scientific_process_records import scientific_digest, scientific_invocation_ref, selector_selection, validate_filled_process
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import digest
import json
import re


class ProteinStructureReturnAncestry:
    def _manifest(self, context):
        manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)
        self._require(self._equal(plain(context.request)["message"].get("knowledge_inheritance"), manifest))
        return manifest

    def _commission(self, child, parent, *, unsaved=False):
        self._require(tuple(map(tuple, child.path[:-1])) == tuple(map(tuple, parent.path)))
        self.store.validate_scope(plain(child.scope), parent_scope=plain(parent.scope))
        slot = child.path[-1][1]
        self._require(isinstance(slot, str) and re.fullmatch(r"child_(0|[1-9][0-9]*)", slot))
        index = int(slot[6:])
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, parent.episode_id, index)).fetchone()
        if row is None and unsaved:
            return index  # Construction only; authenticate checked no work/form.
        self._require(row is not None)
        action, request = json.loads(row["action"]), plain(child.request)
        contract = request.get("report_contract")
        self._require(isinstance(contract, dict) and action.get("kind") in {"episode_child", "job_child"})
        self._require(self._equal(action.get("scope"), child.scope)
            and action.get("purpose") == contract["decision"]
            and action.get("goal") == request["goal"]["objective"]
            and self._equal(json.loads(action["initial_report_json"]), request["message"]["initial_report"]))
        declaration = request["message"].get("report_contract_declaration")
        if declaration is None:
            self._require(self._equal(json.loads(action["schema_json"]), contract["measurements"]["schema"]))
        else:
            validate_saved_fact_form(child_role=child.role, submitted_schema_json=action["schema_json"],
                expanded_schema=contract["measurements"]["schema"], declaration=declaration)
        if action["kind"] in {"episode_child", "job_child"}:
            self._require(action.get("role") == child.role)
            assignment = plain(child.assignment)
            if child.role == "scientific_process" and "selection" in assignment:
                # Only the existing instruction selectors are materialized.
                # Every other selected assignment field stays exact.
                selected = {**assignment, "selection": selector_selection(assignment["selection"])}
                self._require(self._equal(action.get("assignment", {}), assignment)
                    or self._equal(action.get("assignment", {}), selected))
                filled = validate_filled_process(request["message"]["scientific_process"])
                invocation = {"objective": request["goal"]["objective"], "scope": plain(child.scope),
                    "purpose": contract["decision"], "report_schema": contract["measurements"]["schema"],
                    "initial_report": request["message"]["initial_report"]}
                self._require(self._equal(filled["selection"], assignment["selection"])
                    and filled["assignment_sha256"] == scientific_digest(assignment)
                    and filled["invocation_sha256"] == scientific_digest(invocation)
                    and request["message"].get("scientific_invocation_ref") == scientific_invocation_ref(self.run_id, child.path))
            else:
                self._require(self._equal(action.get("assignment", {}), assignment))
        return index

    def _levels(self, context):
        """Yield each exact received prefix."""
        self.authenticate(context, allow_unsaved=True)
        current, allowed, before = context, None, None
        while True:
            yield current, allowed, before, current is not context or context.role not in _ASSIGNED_ROLES
            manifest = self._manifest(current)
            if manifest["parent_episode_id"] is None:
                return
            self._require("received_report_prefix" in manifest)
            allowed = manifest["received_report_prefix"]["attempts"]
            before = int(current.path[-1][1][6:])
            current = self._saved_context(manifest["parent_episode_id"])

    def _known(self, context):
        receipts = EpisodeReceipts(self.store, self.run_id)
        return set(receipts.known(context.episode_id, baseline=context.role in _ASSIGNED_ROLES))

    def _attempts_at(self, context, allowed, before, enabled):
        if not enabled:
            return
        rows = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index",
            (self.run_id, context.episode_id))
        for row in rows:
            if before is not None and row["decision_index"] >= before:
                continue
            if allowed is not None:
                witness = {key: row[key] for key in ("decision_index", "delivery_ref", "child_episode_id")}
                witness.update(contract_sha256=digest(json.loads(row["contract"])),
                               form_sha256=digest(json.loads(row["form"])))
                if not any(self._equal(witness, old) for old in allowed):
                    continue
            yield row

    def _redelivery_schema(self, child, selected, schema, decision):
        """Reproduce this recorded decision's expansion, never today's catalog."""
        from .composition_information import CONTRACT_INFORMATION_PROFILE
        self._require(decision is not None and decision["purpose"] == "decision")
        saved = json.loads(decision["request"])
        info, context = saved["contract_information"], saved["context"]
        keys = {"version", "permitted_child_roles", "fact_sources_by_role", "fact_sources_sha256",
                "catalog_sha256", "action_schema_sha256", "exchange_schema", "instructions"}
        self._require(type(info) is dict and set(info) == keys
            and info["version"] == context.get("contract_information_profile") == CONTRACT_INFORMATION_PROFILE
            and info["fact_sources_sha256"] == digest(info["fact_sources_by_role"])
            and info["catalog_sha256"] == digest(context.get("tools", []))
            and info["action_schema_sha256"] == digest(saved["schema"])
            and type(info["instructions"]) is str
            and type(info["permitted_child_roles"]) is list
            and type(info["fact_sources_by_role"]) is dict
            and set(info["permitted_child_roles"]) == set(info["fact_sources_by_role"]))
        expanded = expand_fact_form(selected["schema_json"], child_role=child.role,
            facts_by_role=info["fact_sources_by_role"], permitted_child_roles=info["permitted_child_roles"])
        validate_saved_fact_form(child_role=child.role, submitted_schema_json=selected["schema_json"],
            expanded_schema=schema, declaration=expanded["declaration"])

