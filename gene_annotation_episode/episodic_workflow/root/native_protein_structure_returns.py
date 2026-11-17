"""Original protein results and actual, frozen typed-delivery authority."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import _error, _boundary
from gene_annotation_episode.episodic_workflow.root.protein_structure_return_ancestry import ProteinStructureReturnAncestry
from gene_annotation_episode.episodic_workflow.root.protein_structure_return_facts import ProteinStructureReturnFacts
from gene_annotation_episode.episodic_workflow.root.protein_structure_return_operands import ProteinStructureReturnOperands
from gene_annotation_episode.episodic_workflow.root.protein_structure_return_visibility import ProteinStructureReturnVisibility
from gene_annotation_episode.episodic_workflow.root.communication import plain
import json


class NativeProteinStructureReturns(ProteinStructureReturnAncestry, ProteinStructureReturnFacts, ProteinStructureReturnOperands, ProteinStructureReturnVisibility, EpisodeReturnRecords):
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix="protein_return_")
        self.owner = owner
        self.results = owner.native_protein_structure_results

    def _require(self, condition, code=None):
        if not condition:
            raise _error()

    @_boundary
    def authenticate(self, context, *, allow_unsaved=False):
        super().authenticate(context, allow_unsaved=allow_unsaved)
        self._require(context.role == context.path[-1][0])
        saved = self.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        manifest = self._manifest(context)
        parent_id = manifest["parent_episode_id"]
        if saved is None:
            self._require(allow_unsaved and parent_id is not None)
            work = self.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "UNION ALL SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=? LIMIT 1",
                (self.run_id, context.episode_id, self.run_id, context.episode_id)).fetchone()
            self._require(work is None)
        # Check ancestry iteratively, including each original commission. Calling
        # self.context here would recursively authenticate the same ancestors.
        current, seen = context, {context.episode_id}
        while parent_id is not None:
            self._require(parent_id not in seen)
            seen.add(parent_id)
            parent = self._saved_context(parent_id)
            self._commission(current, parent, unsaved=saved is None and current is context)
            current = parent
            parent_id = self._manifest(current)["parent_episode_id"]
        self._require(len(current.path) == 1)
        return context

    def _saved_context(self, episode_id):
        from .receiving_context import BindingContext
        row = self.db.execute("SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.run_id, episode_id)).fetchone()
        self._require(row is not None)
        path, request = json.loads(row["path"]), json.loads(row["request"])
        message = request["message"]
        context = BindingContext(self.run_id, episode_id, path[-1][0], tuple(map(tuple, path)),
            message["scope"], message.get("episode_assignment", {}), request)
        super().authenticate(context)
        return context

    def _attempt(self, context, index):
        self.authenticate(context)
        row = self.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, index)).fetchone()
        self._require(row is not None and row["form"] is not None and row["failure"] is None)
        child = self.context(row["child_episode_id"])
        self._require(child.path[:-1] == context.path)
        self._commission(child, context)
        contract, form = json.loads(row["contract"]), json.loads(row["form"])
        schema = contract["measurements"]["schema"]
        action = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, index)).fetchone()
        decision = self.db.execute("SELECT purpose,request,response FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND call_index=?", (self.run_id, context.episode_id, index)).fetchone()
        selected = json.loads(action["action"]) if action is not None else \
            json.loads(decision["response"]).get("selection", {}) if decision is not None and decision["response"] is not None else {}
        original_contract = plain(child.request)["report_contract"]
        compact_redelivery = selected.get("kind") == "redeliver_report" \
            and not self._equal(json.loads(selected["schema_json"]), schema)
        if not compact_redelivery:
            # Preserve the shared recorded-return proof. Its older raw-schema
            # comparison cannot represent compact redelivery; only that path
            # is reproduced below using its frozen contract-information record.
            super()._attempt(context, index)
        if selected.get("kind") == "redeliver_report":
            self._require(selected.get("delivery_ref") == row["delivery_ref"]
                and selected.get("purpose") == contract["decision"])
            if compact_redelivery:
                self._redelivery_schema(child, selected, schema, decision)
            earlier = self.db.execute("SELECT child_episode_id,contract FROM runtime_report_attempts WHERE run_id=? "
                "AND parent_episode_id=? AND delivery_ref=? AND decision_index<? ORDER BY decision_index LIMIT 1",
                (self.run_id, context.episode_id, row["delivery_ref"], index)).fetchone()
            self._require(earlier is not None and earlier["child_episode_id"] == child.episode_id
                and self._equal(json.loads(earlier["contract"]), original_contract))
        else:
            self._require(child.path[-1][1] == "child_" + str(index)
                and selected.get("kind") in {"episode_child", "job_child"}
                and self._equal(contract, original_contract))
        frozen = self.db.execute("SELECT form,facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, child.episode_id)).fetchone()
        self._require(frozen is not None)
        facts = json.loads(frozen["facts"])
        for name, node in schema.get("properties", {}).items():
            source = node.get("x-source")
            if source is not None:
                self._require(source in facts and name in form and self._equal(form[name], facts[source]))
            elif selected.get("kind") == "redeliver_report":
                # Runtime redelivery can select only already frozen original
                # interpretations under their unchanged field contracts.
                self._require(name in facts.get("interpretations", {}) and name in form
                    and self._equal(node, original_contract["measurements"]["schema"].get("properties", {}).get(name))
                    and self._equal(form[name], facts["interpretations"][name]))
        if self._equal(schema, original_contract["measurements"]["schema"]):
            self._require(frozen is not None and frozen["form"] is not None
                          and self._equal(json.loads(frozen["form"]), form))
        return child, form, schema

