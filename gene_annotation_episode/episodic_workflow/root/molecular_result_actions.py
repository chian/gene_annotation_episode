"""Original selected-action locking and control custody used by molecular results."""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Literal, TypedDict
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.native_control_records import require, closed, same, directory, regular, read_control, immutable

class GenomicOverlapResultIntent(TypedDict):
    version: Literal["genomic_overlap_result_intent_v1"]
    run_id: str
    episode_id: str
    path: list[list[str]]
    scope: dict
    assignment: dict
    original_request_sha256: str
    operation_key: str
    tool_name: Literal["execution.results.status", "execution.results.collect"]
    arguments: dict
    target: dict

@dataclass(frozen=True)
class GenomicOverlapResultAction:
    intent: GenomicOverlapResultIntent
    directory: Path

def unique(rows):
    result, seen = [], set()
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_contracts import validate_genomic_overlap_record
from gene_annotation_episode.episodic_workflow.root.library.native_genomic_overlap_job_schema import validate_recorded_genomic_overlap_policy
from .progress_records import validate_resource_observation

class MolecularResultActions:

    def _selected(self, intent):
        row = self.owner._selected_result_action(intent["episode_id"], intent["operation_key"],
            intent["tool_name"], intent["arguments"])
        require(same(json.loads(row["action"]), {"kind": "tool", "tool": intent["tool_name"], "arguments": {}}))
        return row

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
                action = GenomicOverlapResultAction(deepcopy(intent), root)
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

    def file_metadata(self, file, *, value=None, newline=False):
        file = validate_genomic_overlap_record("NativeFileIdentity", file)
        metadata = self.store.get(file["artifact_ref"])
        closed(metadata, ("id", "record_type", "sha256", "size", "media_type"))
        require(metadata["record_type"] == "artifact" and metadata["id"] == file["artifact_ref"]
            == "artifact_" + file["sha256"] and metadata["sha256"] == file["sha256"]
            and type(metadata["size"]) is int and metadata["size"] == file["size_bytes"])
        if value is not None:
            raw = canonical(value).encode("utf-8") + (b"\n" if newline else b"")
            require(hashlib.sha256(raw).hexdigest() == file["sha256"] and len(raw) == file["size_bytes"])
        return file

    def _artifact_value(self, reference, value):
        metadata = self.store.get(reference)
        self.file_metadata({"artifact_ref": reference, "sha256": metadata["sha256"],
            "size_bytes": metadata["size"], "format": "application/json"}, value=value)

    def capture_control(self, action, name, value, format_name):
        from gene_annotation_episode.native_file_capture import capture_native_file
        self.require_action(action)
        immutable(action.directory / name, value)
        file = capture_native_file(self.store, directory=str(action.directory),
            relative_path=name, format=format_name, media_type="application/json")
        self.file_metadata(file, value=value)
        return file

    def validate_observation(self, value, intent):
        from .terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
        if is_terminal_target(intent['target']):
            return validate_terminal_observation(value, intent, self.store, self.owner.run_id)
        from gene_annotation_episode.native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value["native"]
        require(native.get("execution_id") == intent["target"]["execution_id"]
            and native.get("version") == native_version and type(native.get("terminal")) is bool
            and type(native.get("quiescent")) is bool and same(native.get("metadata", {}).get("policy"), validate_recorded_genomic_overlap_policy(native.get("metadata", {}).get("policy"))))
        require(not native["terminal"] or native["quiescent"] and native["state"] == "returned")
        if native["terminal"]:
            require(type(native["metadata"].get("service_exit")) is dict
                and value["state"] in {"completed", "failed"})
        return value

    def observation(self, action):
        self.require_action(action)
        path = action.directory / "observation.json"
        value = read_control(path)
        if value is None:
            value = self.owner.job_progress_provider.targets.observe_target(action.intent["target"],
                operation_key=action.intent["operation_key"])
            value = self.validate_observation(value, action.intent)
            immutable(path, value)
        return deepcopy(self.validate_observation(value, action.intent))
