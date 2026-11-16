"""Selected chromatin action controls and completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Completed-action checks use frozen controls and Store metadata, never scientific bytes.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
from typing import Literal, TypedDict

from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import validate_target
from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_contracts import Failure, NativeFileIdentity, RequestedProjection, _finite_json, validate_chromatin_record
from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_return_views import FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE, validate_chromatin_fact_values
from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_result_worker import validate_chromatin_result_worker_plan, validate_chromatin_result_worker_result, _validate_capture
from gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_capture import validate_chromatin_native_capture
from gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_contracts import POLICY, TABLE_ROLES, TABLE_NAMES, chromatin_driver_argv, validate_chromatin_requested_job, validate_chromatin_run_plan, _dependency_roots
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_receipt
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation


from gene_annotation_episode.episodic_workflow.root.library.chromatin_result_receipt_values import ChromatinInteractionResultIntent, ChromatinInteractionHandoffProof, ChromatinInteractionNativeSnapshot, ChromatinInteractionOrigin, ChromatinInteractionQualifiedFiles, ChromatinInteractionFactGroups, ChromatinInteractionSheetEvidence, ChromatinInteractionResultReceipt, ChromatinInteractionResultAction, _finite_json_copy, require, closed, same, decode, directory, regular, read_control, immutable, empty_facts, empty_files, unique, outcome, qualified_files, closure_value, VERSION, _READING, _READ_CACHE, _OUTPUTS


class ChromatinResultCompletedReceipts:
    def validate(self, receipt, intent):
        receipt = _finite_json_copy(receipt)
        closed(receipt, ChromatinInteractionResultReceipt.__annotations__)
        require(receipt["version"] == VERSION and same(receipt["intent"], intent))
        self.validate_handoff(receipt["handoff_proof"], intent)
        saved = intent["assignment"]["selector"]["mode"] == "saved_sheet_recalculation"
        originals = None
        require(type(receipt["original_origins"]) is list)
        if saved:
            originals = self.origins(self.returns.context(intent["episode_id"]), intent["assignment"])
            origins = [{"episode_id": row["intent"]["episode_id"], "operation_key": row["intent"]["operation_key"]}
                       for row in originals]
            require(same(receipt["original_origins"], origins)
                and all(same(row["intent"]["target"], intent["target"]) for row in originals))
            require(all(receipt[key] is None for key in ("observation", "native", "source_action_file", "writer_closure_file", "capture")))
        else:
            require(receipt["original_origins"] == [])
            self.validate_observation(receipt["observation"], intent)
            if receipt["native"] is not None:
                self.validate_native(receipt["native"], intent, receipt["observation"])
            if receipt["capture"] is not None:
                require(intent["tool_name"] == "execution.results.collect" and receipt["native"] is not None
                    and receipt["observation"]["native"]["terminal"] and receipt["observation"]["native"]["quiescent"])
                capture = validate_chromatin_native_capture(receipt["capture"], original_plan=receipt["native"]["original_plan"])
                if receipt['native'].get('version') == 'terminal_native_snapshot_v1':
                    from gene_annotation_episode.episodic_workflow.root.terminal_native_file_capture import validate_execution_file
                    plan, proof = receipt['native']['original_plan'], receipt['native']['command_proof']
                    spec = plan['outputs'][-1]
                    validate_execution_file(capture['bundle']['file'] if capture['bundle'] is not None else None,
                        original_plan=plan, relative_path=spec['relative_path'], format=spec['format'], command_proof=proof)
                    for row in capture['files']:
                        spec = row['specification']
                        files = [row['capture']['observed']] if row['capture'] is not None else []
                        if row['retained'] is not None:
                            files.append(row['retained']['file'])
                        for file in files:
                            validate_execution_file(file, original_plan=plan,
                                relative_path=spec['relative_path'], format=spec['format'], command_proof=proof)
                self.file_metadata(receipt["source_action_file"], value=receipt["handoff_proof"]["start_receipt"])
                self.file_metadata(receipt["writer_closure_file"], value=closure_value(receipt))
                require(capture["source_action_receipt_ref"] == receipt["source_action_file"]["artifact_ref"]
                    and capture["writer_closure_receipt_ref"] == receipt["writer_closure_file"]["artifact_ref"]
                    and (capture["driver_state"] == "not_started") == (receipt["native"]["driver_started"] is False))
            else:
                require(receipt["source_action_file"] is None and receipt["writer_closure_file"] is None)
        self.validate_worker(receipt)
        expected_files = qualified_files(receipt["worker_capture"], receipt["worker_execution"])
        require(same(receipt["qualified_files"], expected_files))
        self.validate_sheet_evidence(receipt, receipt["sheet_evidence"])
        projection = receipt["projection"]
        if expected_files["projection"] is None:
            require(projection is None)
        else:
            require(expected_files["sheet"] is not None and expected_files["components"] is not None)
            validate_chromatin_record("RequestedProjection", projection)
            self.file_metadata(expected_files["projection"], value=projection)
            selector = intent["assignment"]["selector"]
            require(projection["source_sheet_sha256"] == expected_files["sheet"]["sha256"]
                and same(projection["parameters"], selector["parameters"])
                and projection["kind"] == selector["projection"]["kind"]
                and projection["requested_fields"] == selector["projection"]["fields"]
                and projection["population_keys"] == selector["population_keys"])
            selection = selector["projection"].get("selection", {})
            if selection.get("by") == "page":
                require(type(projection["page"]) is dict and projection["page"]["offset"] == selection["page"]["offset"]
                    and projection["page"]["returned_count"] <= selection["page"]["limit"])
            else:
                require(projection["page"] is None)
        require(type(receipt["host_failures"]) is list)
        for row in receipt["host_failures"]:
            validate_chromatin_record("Failure", row)
        closed(receipt["facts"], ChromatinInteractionFactGroups.__annotations__)
        for source, rows in receipt["facts"].items():
            validate_chromatin_fact_values(source, rows)
        facts, complete = self.publication(receipt, originals=originals)
        require(same(receipt["facts"], facts) and type(receipt["delivery_complete"]) is bool
            and receipt["delivery_complete"] == complete)
        require(receipt["acquired_population"] == self.acquisition_population(receipt))
        if intent["tool_name"] == "execution.results.status":
            require(receipt["worker_plan"] is None and receipt["worker_capture"] is None
                and receipt["capture"] is None and all(not rows for rows in receipt["facts"].values()))
        return receipt

    @staticmethod
    def match_outcome(row, receipt):
        require(row["result"] is not None)
        actual = json.loads(row["result"])
        if "pending_work_after_action" in actual:
            from gene_annotation_episode.episodic_workflow.root.wait_events import validate_pending
            validate_pending(actual.pop("pending_work_after_action"))
        require(same(actual, outcome(receipt)))

    def controls(self, intent):
        root = self.action_directory(intent["episode_id"], intent["operation_key"])
        receipt = read_control(root / "receipt.json")
        if receipt is None:
            return None
        require(same(read_control(root / "intent.json"), intent)
            and same(read_control(root / "handoff.json"), receipt["handoff_proof"]))
        for name, key in (("observation.json", "observation"), ("native-snapshot.json", "native"),
                ("capture.json", "capture"), ("worker-plan.json", "worker_plan"),
                ("worker-capture.json", "worker_capture"), ("worker-execution.json", "worker_execution"),
                ("sheet-evidence.json", "sheet_evidence")):
            require(same(read_control(root / name), receipt[key]))
        if receipt["capture"] is not None:
            require(same(read_control(root / "source-action.json"), receipt["handoff_proof"]["start_receipt"])
                and same(read_control(root / "writer-closure.json"), closure_value(receipt)))
        return self.validate(receipt, intent)

    def read_staged(self, action):
        self.require_action(action)
        receipt = self.controls(action.intent)
        row = self._selected(action.intent)
        require(receipt is not None or row["result"] is None)
        if receipt is not None and row["result"] is not None:
            self.match_outcome(row, receipt)
        return deepcopy(receipt)

    def publish(self, action, receipt):
        self.require_action(action)
        receipt = self.validate(receipt, action.intent)
        immutable(action.directory / "receipt.json", receipt)
        require(same(self.controls(action.intent), receipt))
        return deepcopy(receipt)

    def read_completed(self, *, episode_id, operation_key, scope):
        marker = (episode_id, operation_key)
        active = _READING.get()
        require(marker not in active, "chromatin_interaction_result_cyclic_authority")
        cache = _READ_CACHE.get()
        cache_token = None
        if cache is None:
            cache = {}
            cache_token = _READ_CACHE.set(cache)
        cache_key = (str(self.store.path), self.owner.run_id, episode_id, operation_key, canonical(scope))
        if cache_key in cache:
            return deepcopy(cache[cache_key])
        token = _READING.set((*active, marker))
        try:
            with self.store.read_snapshot():
                context = self.returns.context(episode_id)
                self._context(context)
                self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
                root = self.action_directory(episode_id, operation_key)
                intent = read_control(root / "intent.json")
                closed(intent, ChromatinInteractionResultIntent.__annotations__)
                require(same(intent, self.intent(context, intent["target"], "execution.results.collect", {}, operation_key)))
                manifest = {"run_id": context.run_id, "episode_id": context.episode_id,
                    "scope": plain(context.scope), "assignment": plain(context.assignment)}
                require(same(read_control(root.parent.parent / "assignment.json"), manifest))
                row = self._selected(intent)
                require(row["result"] is not None)
                receipt = self.controls(intent)
                require(receipt is not None)
                self.match_outcome(row, receipt)
                # Only one synchronous completed-action read shares verified origins;
                # the next public call checks current controls and runtime again.
                cache[cache_key] = deepcopy(receipt)
                return deepcopy(receipt)
        finally:
            _READING.reset(token)
            if cache_token is not None:
                _READ_CACHE.reset(cache_token)

    def completed_receipts(self, context):
        self._context(context, allow_unsaved=True)
        result = []
        rows = self.store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? ORDER BY decision_index", (self.owner.run_id, context.episode_id))
        for row in rows:
            action = json.loads(row["action"])
            if (action.get("kind") == "tool" and action.get("tool") == "execution.results.collect"
                    and row["result"] is not None and json.loads(row["result"]).get("status") == "completed"):
                result.append(self.read_completed(episode_id=context.episode_id,
                    operation_key=f'{self.owner.run_id}:{context.episode_id}:{row["decision_index"]}', scope=plain(context.scope)))
        return result

    def owns_reference(self, reference):
        """Classify private derived artifacts, without granting their use."""
        if type(reference) is not str or not reference.startswith("artifact_"):
            return False
        rows = self.store.db.execute("SELECT episode_id,result FROM runtime_actions WHERE run_id=? "
            "AND result IS NOT NULL AND json_extract(result,'$.result.version')=?", (self.owner.run_id, VERSION))
        for row in rows:
            candidate = json.loads(row["result"])["result"]
            capture = candidate.get("worker_capture") or {}
            identities = [item["capture"]["observed"] for item in capture.get("outputs", [])
                if item.get("capture", {}).get("observed") is not None]
            identities.extend(capture.get(key) for key in ("plan_file", "execution_receipt_file", "worker_result_file"))
            private = {file["artifact_ref"] for file in identities if file is not None}
            native = candidate.get("capture")
            if native is not None:
                if native.get("bundle") is not None:
                    private.add(native["bundle"]["file"]["artifact_ref"])
                for item in native.get("files", []):
                    # Original supplied operands keep their prior authority.
                    # Newly produced tables/seals/logs remain private custody.
                    if item["specification"]["role"] not in {"original_contact", "original_elements", "original_metadata"}:
                        retained = item.get("retained")
                        if retained is not None:
                            private.add(retained["file"]["artifact_ref"])
                for issue in native.get("failures", []):
                    if issue.get("artifact_ref") is not None:
                        private.add(issue["artifact_ref"])
                    private.update(issue.get("partial_artifact_refs", []))
            # Failure references are custody/provenance, never operand grants.
            for issue in capture.get("failures", []):
                if issue.get("artifact_ref") is not None:
                    private.add(issue["artifact_ref"])
                private.update(issue.get("partial_artifact_refs", []))
            if reference in private:
                original = self.returns.context(row["episode_id"])
                self.read_completed(episode_id=row["episode_id"], operation_key=candidate["intent"]["operation_key"],
                    scope=plain(original.scope))
                return True
        return False

    def baseline_populations(self, context, references):
        """Subtract actual frozen inherited populations, without operand grants."""
        from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
        self._context(context, allow_unsaved=True)
        receipts = object.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.store.db, self.owner.run_id
        baseline = set(receipts.known(context.episode_id, baseline=True)) & set(references)
        result, visited = set(), set()

        def population(receipt):
            if receipt["acquired_population"] is not None:
                result.add(receipt["acquired_population"])
            for origin in receipt["original_origins"]:
                row = self.read_completed(**origin, scope=plain(context.scope))
                population(row)

        current = context
        while True:
            require(current.episode_id not in visited, "chromatin_interaction_result_cyclic_authority")
            visited.add(current.episode_id)
            self.returns.authenticate(current, allow_unsaved=current is context)
            manifest = receipts.manifest(current.episode_id)
            require(same(plain(current.request)["message"].get("knowledge_inheritance"), manifest))
            parent_id = manifest["parent_episode_id"]
            if parent_id is None:
                require(len(current.path) == 1)
                break
            require("received_report_prefix" in manifest)
            parent = self.returns.context(parent_id)
            self.returns._commission(parent, current, construction=current is context)
            if parent.role in {"annotation", "scientific_process"}:
                groups, origins, _ = self.returns._received(parent, (SAVED_SOURCE,),
                    allowed=manifest["received_report_prefix"]["attempts"])
                for bundle in groups[SAVED_SOURCE]:
                    if not {f["artifact_ref"] for f in (bundle["sheet"], *bundle["tables"])} <= baseline:
                        continue
                    for origin in origins[canonical(bundle)]:
                        closed(origin, ("episode_id", "operation_key"))
                        receipt = self.read_completed(**origin, scope=plain(context.scope))
                        require(any(same(bundle, saved) for saved in receipt["facts"][SAVED_SOURCE]))
                        population(receipt)
            current = parent
        return result


