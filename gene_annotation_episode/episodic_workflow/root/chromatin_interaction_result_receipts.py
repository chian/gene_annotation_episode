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


from gene_annotation_episode.episodic_workflow.root.library.chromatin_result_native_receipts import ChromatinResultNativeReceipts
from gene_annotation_episode.episodic_workflow.root.library.chromatin_result_worker_receipts import ChromatinResultWorkerReceipts
from gene_annotation_episode.episodic_workflow.root.library.chromatin_result_scientific_receipts import ChromatinResultScientificReceipts
from gene_annotation_episode.episodic_workflow.root.library.chromatin_result_completed_receipts import ChromatinResultCompletedReceipts


class ChromatinInteractionResultReceipts(ChromatinResultNativeReceipts, ChromatinResultWorkerReceipts, ChromatinResultScientificReceipts, ChromatinResultCompletedReceipts):
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self._active = {}

    @property
    def returns(self):
        return self.owner.native_chromatin_interaction_returns

    def action_directory(self, episode_id, operation_key):
        return self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id]) / "native-chromatin-interaction-actions" / digest(operation_key)

    def _context(self, context, *, allow_unsaved=False):
        self.returns.authenticate(context, allow_unsaved=allow_unsaved)
        require(isinstance(context, BindingContext) and context.role == "results")
        assignment = plain(context.assignment)
        closed(assignment, ("version", "handoff_ref", "selector"))
        require(assignment["version"] == "execution_results_assignment_v1")
        validate_chromatin_record("ResultSelector", assignment["selector"])
        self.store.validate_scope(plain(context.scope))
        if not allow_unsaved or self.store.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (context.run_id, context.episode_id)).fetchone():
            require(len(context.path) > 1)
            parent_id = EpisodeRef(context.run_id, context.path[:-1]).episode_id
            self.returns._commission(self.returns.context(parent_id), context)
        return assignment

    def _selected(self, intent):
        row = self.owner._selected_result_action(intent["episode_id"], intent["operation_key"],
            intent["tool_name"], intent["arguments"])
        require(same(json.loads(row["action"]), {"kind": "tool", "tool": intent["tool_name"], "arguments": {}}))
        return row

    def _target(self, context, assignment, target):
        target = validate_target(_finite_json_copy(target))
        require(target["run_id"] == self.owner.run_id == context.run_id and target["resource_kind"] == "local"
            and target["handle"] == assignment["handoff_ref"])
        requested = validate_chromatin_requested_job(target["assignment"]["requested_job"])
        require(target["request_sha256"] == digest(requested)
            and target["assignment"]["resource_id"] == target["resource_id"])
        self.store.validate_scope(target["scope"], parent_scope=plain(context.scope))
        resource = self.owner.resources.get(target["resource_id"])
        require(type(resource) is dict and resource["kind"] == "local" and same(resource["policy"], POLICY))
        reader = self.owner.job_progress_provider.targets
        require(same(reader.resources.get(target["resource_id"]), resource)
            and target["resource_id"] in reader.operations)
        reader.operations[target["resource_id"]].validate_assignment(target["assignment"])
        selector = assignment["selector"]
        from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_execution_information import validate_chromatin_result_selector
        request = requested["native_chromatin_interactions"]["request"]
        validate_chromatin_result_selector(selector, request=request)
        return target

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ("execution.results.status", "execution.results.collect")
            and type(arguments) is dict and arguments == {})
        value = {"version": "chromatin_interaction_result_intent_v1", "run_id": context.run_id,
            "episode_id": context.episode_id, "path": plain(context.path), "scope": plain(context.scope),
            "assignment": assignment, "original_request_sha256": digest(plain(context.request)),
            "operation_key": operation_key, "tool_name": tool_name, "arguments": {},
            "target": self._target(context, assignment, target)}
        self._selected(value)
        return value

    @asynccontextmanager
    async def locked_action(self, context, *, target, tool_name, arguments, operation_key):
        intent = self.intent(context, target, tool_name, arguments, operation_key)
        require(not self.store.db.in_transaction)
        root = self.action_directory(context.episode_id, operation_key)
        immutable(root.parent.parent / "assignment.json", {"run_id": context.run_id,
            "episode_id": context.episode_id, "assignment": plain(context.assignment), "scope": plain(context.scope)})
        with directory(root, create=True) as fd, regular(fd, ".action.lock", flags=os.O_RDWR | os.O_CREAT) as lock:
            task = asyncio.create_task(asyncio.to_thread(fcntl.flock, lock, fcntl.LOCK_EX))
            acquired = False
            try:
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    while not task.done():
                        try:
                            await asyncio.shield(task)
                        except asyncio.CancelledError:
                            pass
                    task.result()
                    acquired = True
                    raise
                acquired = True
                require(same(intent, self.intent(context, target, tool_name, arguments, operation_key)))
                immutable(root / "intent.json", intent)
                action = ChromatinInteractionResultAction(deepcopy(intent), root)
                self._active[id(action)] = action
                try:
                    yield action
                finally:
                    self._active.pop(id(action), None)
            finally:
                if acquired:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def require_action(self, action):
        require(self._active.get(id(action)) is action and action.directory == self.action_directory(
            action.intent["episode_id"], action.intent["operation_key"]))
        require(same(read_control(action.directory / "intent.json"), action.intent))
        self._selected(action.intent)

__all__ = ["ChromatinInteractionResultReceipts", "ChromatinInteractionResultAction", "ChromatinInteractionResultReceipt", "VERSION"]
