"""Selected overlap action controls and historical completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Historical checks use frozen controls and Store metadata, never scientific bytes.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.retained_native_read_profiles import retained_policy_matches
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import json
import os
from pathlib import PurePosixPath
import stat
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.genomic_overlap_contracts import _finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_genomic_overlap_contracts import POLICY
from gene_annotation_episode.episodic_workflow.root.a101.progress_records import validate_resource_observation

def require(condition, code='genomic_overlap_result_authority_conflict'):
    if not condition:
        raise ValueError(code)

def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), 'genomic_overlap_result_invalid_record')

def same(left, right):
    return canonical(left) == canonical(right)

def decode(raw, *, newline=False, canonical_bytes=True):

    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'genomic_overlap_result_duplicate_key')
            result[key] = value
        return result
    value = _finite_json_copy(json.loads(raw.decode('utf-8'), object_pairs_hook=pairs))
    require(not canonical_bytes or raw == canonical(value).encode('utf-8') + (b'\n' if newline else b''), 'genomic_overlap_result_noncanonical_control')
    return value

@contextmanager
def directory(path, *, create=False):
    value = str(path)
    pure = PurePosixPath(value)
    require(pure.is_absolute() and str(pure) == value and (value != '/') and ('..' not in pure.parts) and (not any((c in value for c in '\x00\r\n\\'))), 'genomic_overlap_result_invalid_path')
    with ExitStack() as stack:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in pure.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 448, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        require(os.fstat(fd).st_uid == os.geteuid(), 'genomic_overlap_result_invalid_path')
        yield fd

@contextmanager
def regular(fd, name, *, flags=os.O_RDONLY):
    require(type(name) is str and name not in ('', '.', '..') and ('/' not in name))
    handle = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 384, dir_fd=fd)
    try:
        require(stat.S_ISREG(os.fstat(handle).st_mode), 'genomic_overlap_result_invalid_path')
        yield handle
    finally:
        os.close(handle)

def read_control(path):
    try:
        with directory(path.parent) as fd, regular(fd, path.name) as handle, os.fdopen(os.dup(handle), 'rb') as stream:
            raw = stream.read()
    except FileNotFoundError:
        return None
    return decode(raw, newline=path.name == 'assignment.json' and raw.endswith(b'\n'))

def unique(rows):
    result, seen = ([], set())
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import fcntl
import hashlib
from pathlib import Path
import secrets
from typing import Literal, TypedDict
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.genomic_overlap_contracts import validate_genomic_overlap_record

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

def immutable(path, value):
    value = _finite_json_copy(value)
    with directory(path.parent, create=True) as fd:
        previous = read_control(path)
        if previous is not None:
            require(same(previous, value), "genomic_overlap_result_control_conflict")
            return
        temporary = "." + path.name + "." + secrets.token_hex(16) + ".writing"
        try:
            with regular(fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as handle:
                with os.fdopen(os.dup(handle), "wb") as stream:
                    stream.write(canonical(value).encode("utf-8") + (b"\n" if path.name == "assignment.json" else b""))
                    stream.flush()
                os.fchmod(handle, 0o444)
                os.fsync(handle)
            try:
                os.link(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except FileExistsError:
                require(same(read_control(path), value), "genomic_overlap_result_control_conflict")
            os.fsync(fd)
        finally:
            os.unlink(temporary, dir_fd=fd)


class GenomicOverlapResultReceipts:

    def _selected(self, intent):
        row = self.owner._selected_result_action(intent['episode_id'], intent['operation_key'], intent['tool_name'], intent['arguments'])
        require(same(json.loads(row['action']), {'kind': 'tool', 'tool': intent['tool_name'], 'arguments': {}}))
        return row

    def validate_observation(self, value, intent):
        from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
        if is_terminal_target(intent['target']):
            return validate_terminal_observation(value, intent, self.store, self.owner.run_id)
        from gene_annotation_episode.episodic_workflow.root.a101.native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value['native']
        require(native.get('execution_id') == intent['target']['execution_id'] and native.get('version') == native_version and (type(native.get('terminal')) is bool) and (type(native.get('quiescent')) is bool) and retained_policy_matches(native.get('metadata', {}).get('policy')))
        require(not native['terminal'] or (native['quiescent'] and native['state'] == 'returned'))
        if native['terminal']:
            require(type(native['metadata'].get('service_exit')) is dict and value['state'] in {'completed', 'failed'})
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
        from gene_annotation_episode.episodic_workflow.root.a101.native_file_capture import capture_native_file
        self.require_action(action)
        immutable(action.directory / name, value)
        file = capture_native_file(self.store, directory=str(action.directory),
            relative_path=name, format=format_name, media_type="application/json")
        self.file_metadata(file, value=value)
        return file

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
