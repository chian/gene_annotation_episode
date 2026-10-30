"""Original selected fluorescence action, launch, worker and publication authority.

These durable controls retain outcomes before credit. Historical validation
uses frozen controls and artifact metadata; it neither loads event arrays nor polls
or reruns a native producer.
"""
from copy import deepcopy
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets

from method_loop.identities import EpisodeRef
from .communication import plain
from .domain import identity
from .episode_bindings import BindingContext
from .execution_contracts import canonical as return_canonical, validate_target
from .fluorescence_execution_common import (canonical, digest, closed, same, unique,
    require as control_require, validate_failure)
from .fluorescence_event_contracts import canonical as numerical_canonical
from .fluorescence_result_contracts import (OUTPUTS, validate_file, validate_fluorescence_projection,
    validate_fluorescence_selector, validate_fluorescence_context,
    validate_fluorescence_worker_plan, validate_fluorescence_worker_result)
from .fluorescence_return_views import (FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE,
    requested_fluorescence_sources, validate_fluorescence_fact_values)
from .native_fluorescence_contracts import (POLICY, fluorescence_driver_argv,
    validate_fluorescence_requested_job, validate_fluorescence_run_plan,
    validate_fluorescence_native_capture)
from .native_fluorescence_preparation import validate_fluorescence_worker_execution
from .native_fluorescence_storage import read_json
from .practical_execution_records import validate_receipt
from .practical_receipt_information import PracticalReceiptInformation
from .genomic_overlap_result_receipts import GenomicOverlapResultReceipts as _Shared, directory, regular

VERSION = 'native_fluorescence_acquired_result_v1'
_READING = ContextVar('fluorescence_reading', default=())


def require(condition, code='fluorescence_result_authority_conflict'):
    control_require(condition, code)


def failure(code, stage, *, input_index=None, role=None):
    return validate_failure(dict(code=code, stage=stage, input_index=input_index, role=role))


@dataclass(frozen=True)
class FluorescenceResultAction:
    intent: dict
    directory: Path


def read_control(path):
    """Read only exact immutable control JSON; numerical bytes use their own codec."""
    try:
        with directory(path.parent) as fd, regular(fd, path.name) as handle, os.fdopen(os.dup(handle), 'rb') as stream:
            raw = stream.read()
    except FileNotFoundError:
        return None
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'fluorescence_result_duplicate_key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    require(raw == canonical(value) + b'\n', 'fluorescence_result_noncanonical_control')
    return value


def immutable(path, value):
    raw = canonical(value) + b'\n'
    with directory(path.parent, create=True) as fd:
        previous = read_control(path)
        if previous is not None:
            require(same(previous, value), 'fluorescence_result_control_conflict')
            return
        temporary = '.' + path.name + '.' + secrets.token_hex(16) + '.writing'
        try:
            with regular(fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as handle:
                with os.fdopen(os.dup(handle), 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                os.fchmod(handle, 0o444)
                os.fsync(handle)
            try:
                os.link(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except FileExistsError:
                require(same(read_control(path), value), 'fluorescence_result_control_conflict')
            os.fsync(fd)
        finally:
            os.unlink(temporary, dir_fd=fd)

def empty_facts():
    return {source: [] for source in FACT_SOURCES}

def empty_files():
    return {row[0]: None for row in OUTPUTS}

def outcome(receipt):
    refs = [row['artifact_ref'] for row in receipt['facts'][SAVED_SOURCE]]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
        'result': deepcopy(receipt), 'feedback': None}

def qualified_files(capture, execution):
    result = empty_files()
    if (capture is not None and capture['result'] is not None and execution is not None
            and execution['terminal'] and execution['quiescent'] and execution['failure'] is None
            and execution['returncode'] == 0):
        for spec, row in zip(OUTPUTS, capture['outputs']):
            if row['outcome'] == 'verified':
                result[spec[0]] = deepcopy(row['observed'])
    if result['sheet'] is None or result['calculations'] is None:
        result['projection'] = None
    if result['projection'] is None:
        result['context'] = None
    return result

def closure_value(receipt):
    return {'version': 'fluorescence_writer_closure_v1', 'intent_sha256': digest(receipt['intent']),
        'native': receipt['native'], 'observation': receipt['observation']}

class FluorescenceResultReceipts:
    def __init__(self, owner):
        self.owner, self.store, self._active = owner, owner.store, {}

    @property
    def returns(self):
        return self.owner.native_fluorescence_returns

    # Existing selected-action and resource-observation validators interpret
    # no scientific measurements. Control persistence above uses the frozen LF encoding.
    _selected = _Shared._selected
    validate_observation = _Shared.validate_observation

    def action_directory(self, episode_id, operation_key):
        return self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id]) / 'native-fluorescence-actions' / digest(operation_key)

    def _context(self, context, *, allow_unsaved=False):
        self.returns.authenticate(context, allow_unsaved=allow_unsaved)
        require(isinstance(context, BindingContext) and context.role == 'results', 'fluorescence_results_context_required')
        assignment = plain(context.assignment)
        closed(assignment, ('version', 'handoff_ref', 'selector'))
        require(assignment['version'] == 'execution_results_assignment_v1', 'fluorescence_results_assignment_required')
        validate_fluorescence_selector(assignment['selector'])
        schema = plain(context.request)['report_contract']['measurements']['schema']
        requested = requested_fluorescence_sources(schema)
        require(bool(assignment['selector']['context_fields']) == (CONTEXT_SOURCE in requested),
            'fluorescence_context_selection_mismatch')
        self.store.validate_scope(plain(context.scope))
        require(len(context.path) > 1, 'fluorescence_parent_commission_required')
        self.returns._commission(self.returns.context(EpisodeRef(context.run_id, context.path[:-1]).episode_id),
            context, construction=allow_unsaved)
        return assignment

    def _target(self, context, assignment, target, *, current_resource=False):
        target = validate_target(plain(target))
        require(target['run_id'] == self.owner.run_id == context.run_id and target['resource_kind'] == 'local'
            and target['handle'] == assignment['handoff_ref'], 'fluorescence_target_mismatch')
        request = validate_fluorescence_requested_job(target['assignment']['requested_job'])
        require(target['request_sha256'] == digest(request) and target['assignment']['resource_id'] == target['resource_id'], 'fluorescence_target_mismatch')
        self.store.validate_scope(target['scope'], parent_scope=plain(context.scope))
        if current_resource:
            resource = self.owner.resources.get(target['resource_id'])
            require(type(resource) is dict and resource['kind'] == 'local' and same(resource['policy'], POLICY), 'fluorescence_resource_mismatch')
            reader = self.owner.job_progress_provider.targets
            require(same(reader.resources.get(target['resource_id']), resource) and target['resource_id'] in reader.operations, 'fluorescence_resource_mismatch')
            reader.operations[target['resource_id']].validate_assignment(target['assignment'])
        validate_fluorescence_selector(assignment['selector'], job=request['native_fluorescence'])
        return target

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ('execution.results.status', 'execution.results.collect') and type(arguments) is dict and arguments == {}, 'fluorescence_selected_result_action_required')
        value = dict(version='fluorescence_result_intent_v1', run_id=context.run_id, episode_id=context.episode_id,
            path=plain(context.path), scope=plain(context.scope), assignment=assignment,
            original_request_sha256=digest(plain(context.request)), operation_key=operation_key,
            tool_name=tool_name, arguments={}, target=self._target(context, assignment, target))
        self._selected(value)
        return value

    @asynccontextmanager
    async def locked_action(self, context, *, target, tool_name, arguments, operation_key):
        intent = self.intent(context, target, tool_name, arguments, operation_key)
        require(not self.store.db.in_transaction)
        root = self.action_directory(context.episode_id, operation_key)
        immutable(root.parent.parent / 'assignment.json', {'run_id': context.run_id,
            'episode_id': context.episode_id, 'assignment': plain(context.assignment), 'scope': plain(context.scope)})
        with directory(root, create=True) as fd, regular(fd, '.action.lock', flags=os.O_RDWR | os.O_CREAT) as lock:
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
                immutable(root / 'intent.json', intent)
                action = FluorescenceResultAction(deepcopy(intent), root)
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
            action.intent['episode_id'], action.intent['operation_key']))
        require(same(read_control(action.directory / 'intent.json'), action.intent))
        self._selected(action.intent)

    def file_metadata(self, file, *, value=None, newline=False, numerical=False):
        """Authenticate retained identities without reopening historical scientific bytes."""
        file = validate_file(file)
        metadata = self.store.get(file['artifact_ref'])
        closed(metadata, ('id', 'record_type', 'sha256', 'size', 'media_type'))
        require(metadata['record_type'] == 'artifact' and metadata['id'] == file['artifact_ref']
            == 'artifact_' + file['sha256'] and metadata['sha256'] == file['sha256']
            and type(metadata['size']) is int and metadata['size'] == file['size_bytes'],
            'fluorescence_result_file_metadata_mismatch')
        if value is not None:
            raw = (numerical_canonical if numerical else canonical)(value) + (b'\n' if newline else b'')
            require(hashlib.sha256(raw).hexdigest() == file['sha256'] and len(raw) == file['size_bytes'],
                'fluorescence_result_artifact_value_mismatch')
        return deepcopy(file)

    def _artifact_value(self, reference, value):
        metadata = self.store.get(reference)
        self.file_metadata({'artifact_ref': reference, 'sha256': metadata['sha256'],
            'size_bytes': metadata['size'], 'format': 'application/json'}, value=value)

    def capture_control(self, action, name, value, format_name):
        from .native_file_capture import capture_native_file
        self.require_action(action)
        immutable(action.directory / name, value)
        file = capture_native_file(self.store, directory=str(action.directory),
            relative_path=name, format=format_name, media_type='application/json')
        self.file_metadata(file, value=value, newline=True)
        return file

    def observation(self, action):
        self.require_action(action)
        path = action.directory / 'observation.json'
        value = read_control(path)
        if value is None:
            value = self.owner.job_progress_provider.targets.observe_target(action.intent['target'],
                operation_key=action.intent['operation_key'])
            value = self.validate_observation(value, action.intent)
            immutable(path, value)
        return deepcopy(self.validate_observation(value, action.intent))

    def validate_handoff(self, proof, intent):
        closed(proof, ("source_record", "body", "assignment_snapshot", "start_receipt"))
        source, body, snapshot, start = (proof[name] for name in ("source_record", "body", "assignment_snapshot", "start_receipt"))
        practical = PracticalReceiptInformation(self.store, self.owner.run_id)
        qualified, selected = practical._qualify(body, snapshot, intent["scope"])
        require(same(qualified, body) and selected["result"] is not None)
        self._artifact_value(source["artifact_ref"], body)
        self._artifact_value(source["request_ref"], snapshot)
        payload = practical._source_payload(body, source["artifact_ref"], source["request_ref"])
        require(same(source, self.store.get(source["id"])) and source["origin"] == "tool"
            and source["record_type"] == "source" and source["id"] == identity("source", {"origin": "tool", "record": payload})
            and same({k: v for k, v in source.items() if k not in ("id", "record_type", "origin")}, payload)
            and len(practical._sources(source["accession"])) == 1)
        receipt, assignment = body["receipt"], snapshot["assignment"]
        original = self.returns.context(body["episode_id"])
        require(same(plain(original.assignment), assignment) and same(plain(original.scope), body["scope"]))
        require(len(original.path) > 1)
        self.returns._commission(self.returns.context(EpisodeRef(self.owner.run_id, original.path[:-1]).episode_id), original)
        selected_outcome = json.loads(selected["result"])
        require(selected_outcome.get("status") in ("completed", "partial")
            and same(selected_outcome.get("result"), receipt) and source["id"] in selected_outcome.get("record_refs", []))
        require(receipt["tool_name"] in ("practical.job.start", "practical.job.status", "practical.job.collect"))
        requested = validate_fluorescence_requested_job(assignment["requested_job"])
        job = receipt["outcome"].get("facts", {}).get("requested_job", {})
        detail = receipt["outcome"].get("native_outcome") or {}
        key = detail.get("attempt_operation_key")
        require(type(key) is str and detail.get("attempt_id") == digest(key))
        require(job.get("requested_job_sha256") == digest(requested) and job.get("argv") == requested["argv"]
            and same(job.get("environment"), requested["environment"]) and job.get("resource_kind") == "local"
            and type(job.get("handoff")) is dict and job["execution_id"] == job["handoff"].get("execution_id")
            and job["handoff"].get("monitor_operation") == "practical.job.status"
            and job["handoff"].get("results_operation") == "practical.job.collect")
        start = validate_receipt(start)
        start_row = practical._selected(start)
        require(start_row["result"] is not None and start["tool_name"] == "practical.job.start"
            and start["operation_key"] == key and start["run_id"] == self.owner.run_id
            and start["episode_id"] == body["episode_id"] and start["assignment_sha256"] == body["assignment_sha256"])
        start_outcome = json.loads(start_row["result"])
        require(start_outcome.get("status") in ("completed", "partial") and same(start_outcome.get("result"), start))
        start_job = start["outcome"].get("facts", {}).get("requested_job", {})
        start_detail = start["outcome"].get("native_outcome") or {}
        require(start_job.get("execution_id") == job["execution_id"] and start_job.get("requested_job_sha256") == digest(requested)
            and start_detail.get("attempt_id") == detail["attempt_id"] and start_detail.get("attempt_operation_key") == key)
        expected = {"version": "execution_target_v1", "handle": source["id"], "run_id": self.owner.run_id,
            "resource_id": assignment["resource_id"], "resource_kind": "local", "execution_id": job["execution_id"],
            "request_sha256": digest(requested), "origin_episode_id": body["episode_id"],
            "assignment": assignment, "scope": body["scope"]}
        require(same(validate_target(expected), intent["target"]))
        require(job["execution_id"] == str(Path(assignment["workspace"]) / ".episode-operations" /
            digest({"run": self.owner.run_id, "episode": body["episode_id"]}) / digest(key) / "native.json"))

    def read_handoff(self, action):
        self.require_action(action)
        path = action.directory / "handoff.json"
        saved = read_control(path)
        if saved is None:
            target = action.intent["target"]
            practical = PracticalReceiptInformation(self.store, self.owner.run_id)
            body = practical.read(target["handle"], action.intent["scope"])
            source = self.store.get(target["handle"])
            snapshot = practical._artifact_json(source["request_ref"])
            key = body["receipt"]["outcome"]["native_outcome"]["attempt_operation_key"]
            prefix = f'{self.owner.run_id}:{body["episode_id"]}:'
            suffix = key.removeprefix(prefix)
            require(key.startswith(prefix) and re.fullmatch(r"0|[1-9][0-9]*", suffix) is not None)
            row = self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                (self.owner.run_id, body["episode_id"], int(suffix))).fetchone()
            require(row is not None and row["result"] is not None)
            saved = {"source_record": source, "body": body, "assignment_snapshot": snapshot,
                "start_receipt": json.loads(row["result"])["result"]}
            self.validate_handoff(saved, action.intent)
            immutable(path, saved)
        self.validate_handoff(saved, action.intent)
        return deepcopy(saved)

    def origins(self, context, assignment):
        """Use every explicitly received saved origin; no native or data reads."""
        selector = assignment["selector"]
        file = selector["saved_sheet_file"]
        episodes = self.returns.authenticate_received_saved_sheet(context, file)
        matches = []
        for episode_id in episodes:
            original_context = self.returns.context(episode_id)
            self.store.validate_scope(plain(original_context.scope), parent_scope=plain(context.scope))
            for receipt in self.completed_receipts(original_context):
                if (any(same(file, row) for row in receipt["facts"][SAVED_SOURCE])
                        and receipt["intent"]["target"]["handle"] == assignment["handoff_ref"]):
                    matches.append(receipt)
        require(bool(matches), "fluorescence_saved_handoff_conflict")
        target = matches[0]["intent"]["target"]
        require(all(same(row["intent"]["target"], target) for row in matches), "fluorescence_saved_target_conflict")
        return matches

    def native_snapshot(self, action, observation):
        self.require_action(action)
        path = action.directory / 'native-snapshot.json'
        value = read_control(path)
        if value is None:
            from .native_fluorescence_local import local_fluorescence_plan
            from .native_fluorescence_contracts import STARTED_FILENAME
            from .native_fluorescence_storage import confined_file, regular
            from .native_file_capture import capture_native_file, retained_native_file
            target = action.intent['target']
            plan = local_fluorescence_plan(target['assignment'], target['execution_id'])
            handle = read_json(target['execution_id'])
            request_file = capture_native_file(self.store, directory=str(Path(target['execution_id']).parent),
                relative_path=Path(handle['paths']['request']).name, format='native_local_job_request')
            request_raw = retained_native_file(self.store, request_file).read_bytes().decode('utf-8')
            marker_path = confined_file(Path(plan['attempt_directory']), STARTED_FILENAME)
            marker = read_json(marker_path) if marker_path.exists() else None
            native_receipt = observation['native'].get('native_receipt')
            never_started = marker is None and type(native_receipt) is dict and native_receipt.get('execution_failure') is not None
            value = dict(original_plan=plan, handle=handle, request=json.loads(request_raw), request_raw=request_raw,
                started_marker=marker, driver_started=True if marker is not None else False if never_started else None,
                plan_file=self.capture_control(action, 'native-plan.json', plan, 'fluorescence_run_plan_v1'),
                handle_file=self.capture_control(action, 'native-handle.json', handle, 'durable_systemd_native_job_v2'),
                request_file=request_file, started_marker_file=None if marker is None else
                    self.capture_control(action, 'driver-started.json', marker, 'fluorescence_driver_started_v1'))
            self.validate_native(value, action.intent, observation)
            immutable(path, value)
        self.validate_native(value, action.intent, observation)
        return deepcopy(value)

    def validate_native(self, value, intent, observation):
        from .native_fluorescence_local import fluorescence_native_request
        from .native_lifecycle import VERSION as native_version
        closed(value, ('original_plan', 'handle', 'request', 'request_raw', 'started_marker',
            'driver_started', 'plan_file', 'handle_file', 'request_file', 'started_marker_file'))
        plan = validate_fluorescence_run_plan(value['original_plan'])
        target, ident = intent['target'], plan['identity']
        require(same(plan['requested_job'], target['assignment']['requested_job']) and same(plan['policy'], POLICY)
            and ident['run_id'] == intent['run_id'] and ident['episode_id'] == target['origin_episode_id']
            and ident['execution_id'] == target['execution_id'] and ident['resource_id'] == target['resource_id']
            and ident['assignment_sha256'] == digest(target['assignment']) and ident['requested_job_sha256'] == target['request_sha256'],
            'fluorescence_original_native_identity_mismatch')
        handoff = read_control(self.action_directory(intent['episode_id'], intent['operation_key']) / 'handoff.json')
        require(handoff is not None and ident['operation_key'] == handoff['start_receipt']['operation_key'], 'fluorescence_native_start_mismatch')
        handle, request, root = value['handle'], value['request'], Path(target['execution_id']).parent
        require(handle.get('version') == native_version and handle.get('stage') in ('prepared', 'submitting', 'released')
            and handle.get('command') == fluorescence_driver_argv(plan) and handle.get('cwd') == str(root)
            and same(handle.get('metadata', {}).get('policy'), POLICY), 'fluorescence_native_handle_mismatch')
        paths = handle.get('paths')
        require(type(paths) is dict and {'request', 'ready', 'release', 'status', 'result', 'launcher'} <= paths.keys()
            and not paths.keys() - {'request', 'ready', 'release', 'status', 'result', 'launcher', 'statistics', 'native_events'}
            and len(set(paths.values())) == len(paths) and all(Path(p).parent == root and str(Path(p)) == p for p in paths.values()),
            'fluorescence_native_request_mismatch')
        require(same(request, fluorescence_native_request(plan, paths)), 'fluorescence_native_request_mismatch')
        raw = value['request_raw'].encode('utf-8')
        require(same(json.loads(raw), request) and hashlib.sha256(raw).hexdigest() == value['request_file']['sha256']
            == handle.get('request_sha256') and len(raw) == value['request_file']['size_bytes'], 'fluorescence_native_request_mismatch')
        self.file_metadata(value['request_file'])
        self.file_metadata(value['plan_file'], value=plan, newline=True)
        self.file_metadata(value['handle_file'], value=handle, newline=True)
        marker = value['started_marker']
        if marker is None:
            native = observation['native'].get('native_receipt')
            expected = False if type(native) is dict and native.get('execution_failure') is not None else None
            require(value['driver_started'] is expected and value['started_marker_file'] is None, 'fluorescence_native_marker_mismatch')
        else:
            closed(marker, ('plan', 'started_at'))
            require(same(marker['plan'], plan) and type(marker['started_at']) is str and marker['started_at']
                and value['driver_started'] is True, 'fluorescence_native_marker_mismatch')
            self.file_metadata(value['started_marker_file'], value=marker, newline=True)

    def validate_worker(self, receipt):
        plan, capture, execution = (receipt[k] for k in ('worker_plan', 'worker_capture', 'worker_execution'))
        if plan is None:
            require(capture is None and execution is None, 'fluorescence_worker_receipt_mismatch')
            return
        plan = validate_fluorescence_worker_plan(plan)
        intent, selector = receipt['intent'], receipt['intent']['assignment']['selector']
        require(plan['directory'] == str(self.action_directory(intent['episode_id'], intent['operation_key']) / 'worker')
            and same(plan['selector'], selector), 'fluorescence_worker_selection_mismatch')
        if plan['mode'] == 'native_result':
            require(same(plan['original_plan'], receipt['native']['original_plan']) and same(plan['capture'], receipt['capture']),
                'fluorescence_worker_native_binding_mismatch')
            retained = [row['retained'] for row in plan['capture']['files']]
        else:
            require(same(plan['sheet']['file'], selector['saved_sheet_file']), 'fluorescence_worker_saved_binding_mismatch')
            retained = [plan['sheet']]
        for row in retained:
            if row is not None:
                file = self.file_metadata(row['file'])
                require(row['path'] == str(self.store.path / 'artifacts' / file['sha256'][:2] / file['sha256']), 'fluorescence_worker_input_path_mismatch')
        require(type(capture) is dict and execution is not None, 'fluorescence_worker_receipt_mismatch')
        closed(capture, ('version', 'plan_file', 'execution_receipt_file', 'worker_result_file', 'result', 'outputs', 'failures'))
        require(capture['version'] == 'fluorescence_worker_capture_v1' and type(capture['outputs']) is list
            and type(capture['failures']) is list, 'fluorescence_worker_receipt_mismatch')
        self.file_metadata(capture['plan_file'], value=plan, newline=True)
        self.file_metadata(capture['execution_receipt_file'], value=execution, newline=True)
        require(capture['plan_file']['format'] == 'fluorescence_worker_plan_v1'
            and capture['execution_receipt_file']['format'] == 'fluorescence_worker_execution_v1',
            'fluorescence_worker_receipt_mismatch')
        validate_fluorescence_worker_execution(execution, plan=plan, plan_file=capture['plan_file'])
        for key in ('handle_file', 'request_file', 'stdout_file', 'stderr_file'):
            self.file_metadata(execution[key])
        result = capture['result']
        expected_failures = []
        if execution['failure'] is not None or execution['returncode'] != 0:
            expected_failures.append(failure('worker_resource_failure' if execution['failure'] is not None
                and execution['failure']['code'] == 'local_job_resource_limit' else 'worker_nonzero_exit', 'worker'))
        if capture['worker_result_file'] is not None:
            require(capture['worker_result_file']['format'] == 'fluorescence_worker_result_v1',
                'fluorescence_worker_receipt_mismatch')
        if result is None:
            require(capture['outputs'] == [], 'fluorescence_worker_outputs_mismatch')
            if capture['worker_result_file'] is not None:
                self.file_metadata(capture['worker_result_file'])
            expected_failures.append(failure('worker_output_unavailable' if capture['worker_result_file'] is None
                else 'worker_output_malformed', 'worker', role='worker_result'))
        else:
            validate_fluorescence_worker_result(result)
            self.file_metadata(capture['worker_result_file'], value=result, newline=True)
            require(result['plan_sha256'] == digest(plan) and result['mode'] == plan['mode'] and same(result['selector'], selector)
                and len(capture['outputs']) == len(OUTPUTS), 'fluorescence_worker_result_mismatch')
            expected_inputs = ([row['source']['file'] for row in plan['original_plan']['requested_job']['native_fluorescence']['inputs']]
                if plan['mode'] == 'native_result' else [plan['sheet']['file']])
            require(same(result['input_identities'], expected_inputs), 'fluorescence_worker_input_identity_mismatch')
            if result['native_binding']:
                require(plan['mode'] == 'native_result' and receipt['native']['driver_started'] is True
                    and receipt['observation']['native']['terminal'] and receipt['observation']['native']['quiescent'],
                    'fluorescence_worker_native_binding_mismatch')
            for declared, row, spec in zip(result['outputs'], capture['outputs'], OUTPUTS):
                closed(row, ('declared', 'observed', 'outcome', 'failure'))
                require(same(row['declared'], declared['declaration']), 'fluorescence_worker_outputs_mismatch')
                actual, d = row['observed'], row['declared']
                if actual is not None:
                    self.file_metadata(actual)
                equal = actual is not None and all(actual[k] == d[k] for k in ('sha256', 'size_bytes', 'format'))
                require((row['outcome'] == 'verified' and d['state'] == 'present' and equal and row['failure'] is None)
                    or (row['outcome'] == 'declared_absent' and d['state'] == 'absent' and actual is None and row['failure'] is None)
                    or (row['outcome'] == 'unavailable' and d['state'] == 'present' and actual is None and row['failure'] == 'capture_file_unavailable')
                    or (row['outcome'] == 'digest_mismatch' and d['state'] == 'present' and actual is not None and not equal
                        and row['failure'] == 'capture_file_digest_mismatch'), 'fluorescence_worker_capture_mismatch')
                if row['failure'] is not None:
                    expected_failures.append(failure(row['failure'], 'capture', role=spec[0]))
        require(type(capture['failures']) is list and same(capture['failures'], unique(capture['failures'])),
            'fluorescence_worker_capture_mismatch')
        for row in capture['failures']:
            validate_failure(row)
        require(same(capture['failures'], unique(expected_failures)), 'fluorescence_worker_capture_mismatch')

    def original_acquisition_complete(self, receipt):
        if receipt['intent']['assignment']['selector']['mode'] == 'saved_sheet_recalculation':
            return False
        observed, capture, native_capture = receipt['observation'], receipt['worker_capture'], receipt['capture']
        return bool(observed is not None and observed['state'] == 'completed' and observed['returncode'] == 0
            and observed['native']['terminal'] and observed['native']['quiescent'] and capture is not None
            and capture['result'] is not None and capture['result']['original_events_acquired']
            and capture['result']['native_binding'] and capture['result']['native_outcome'] == 'complete'
            and native_capture is not None and not native_capture['failures']
            and all(row['retained'] is not None for row in native_capture['files']) and not capture['failures']
            and all(receipt['qualified_files'][role] is not None for role in ('sheet', 'calculations')))

    def acquisition_population(self, receipt):
        worker = receipt['worker_capture']
        if (receipt['intent']['assignment']['selector']['mode'] == 'native_result'
                and receipt['intent']['tool_name'] == 'execution.results.collect'
                and receipt['qualified_files']['sheet'] is not None and worker is not None
                and worker['result'] is not None and worker['result']['original_events_acquired']):
            return digest(receipt['native']['original_plan']['identity'])
        return None

    def publication(self, receipt, *, originals=None):
        context = self.returns.context(receipt['intent']['episode_id'])
        schema = plain(context.request)['report_contract']['measurements']['schema']
        requested = requested_fluorescence_sources(schema)
        facts = empty_facts()
        issues = list(receipt['host_failures'])
        for key in ('capture', 'worker_capture'):
            value = receipt[key]
            if value is not None:
                issues.extend(value['failures'])
        worker = receipt['worker_capture']
        if worker is not None and worker['result'] is not None:
            issues.extend(worker['result']['failures'])
        collecting = receipt['intent']['tool_name'] == 'execution.results.collect'
        if collecting:
            if PROJECTION_SOURCE in requested and receipt['projection'] is not None:
                facts[PROJECTION_SOURCE] = [deepcopy(receipt['projection'])]
            if CONTEXT_SOURCE in requested and receipt['context'] is not None:
                facts[CONTEXT_SOURCE] = [deepcopy(receipt['context'])]
            if SAVED_SOURCE in requested and receipt['qualified_files']['sheet'] is not None:
                facts[SAVED_SOURCE] = [deepcopy(receipt['qualified_files']['sheet'])]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = unique(issues)
        complete = bool(collecting and receipt['projection'] is not None and not receipt['host_failures']
            and worker is not None and worker['result'] is not None and worker['result']['analysis_complete']
            and not worker['failures'] and all(receipt['qualified_files'][key] is not None for key in ('sheet', 'calculations', 'projection'))
            and (CONTEXT_SOURCE not in requested or receipt['context'] is not None)
            and all(bool(facts[source]) for source in requested if source != FAILURE_SOURCE))
        if receipt['intent']['assignment']['selector']['mode'] == 'native_result':
            complete = complete and self.original_acquisition_complete(receipt)
        else:
            originals = self.origins(context, receipt['intent']['assignment']) if originals is None else originals
            # The selected assignment is recalculation of genuinely received
            # sheet data. Its original acquisition remains partial or complete
            # as recorded; successful new calculation does not re-acquire it.
            complete = complete and bool(originals)
        return facts, bool(complete)

    def validate(self, receipt, intent):
        closed(intent, ('version', 'run_id', 'episode_id', 'path', 'scope', 'assignment',
            'original_request_sha256', 'operation_key', 'tool_name', 'arguments', 'target'))
        context = self.returns.context(intent['episode_id'])
        require(same(intent, self.intent(context, intent['target'], intent['tool_name'],
            intent['arguments'], intent['operation_key'])), 'fluorescence_result_intent_mismatch')
        closed(receipt, ('version', 'intent', 'handoff_proof', 'original_origins', 'observation', 'native',
            'source_action_file', 'writer_closure_file', 'capture', 'worker_plan', 'worker_capture', 'worker_execution',
            'qualified_files', 'projection', 'context', 'host_failures', 'facts', 'acquired_population', 'delivery_complete'))
        require(receipt['version'] == VERSION and same(receipt['intent'], intent), 'fluorescence_result_receipt_mismatch')
        self.validate_handoff(receipt['handoff_proof'], intent)
        saved = intent['assignment']['selector']['mode'] == 'saved_sheet_recalculation'
        originals = None
        if saved:
            originals = self.origins(self.returns.context(intent['episode_id']), intent['assignment'])
            require(receipt['original_origins'] == [{'episode_id': r['intent']['episode_id'], 'operation_key': r['intent']['operation_key']}
                for r in originals] and all(same(r['intent']['target'], intent['target']) for r in originals), 'fluorescence_saved_origin_mismatch')
            require(all(receipt[k] is None for k in ('observation', 'native', 'source_action_file', 'writer_closure_file', 'capture')),
                'fluorescence_saved_native_work_disallowed')
        else:
            require(receipt['original_origins'] == [], 'fluorescence_native_origin_mismatch')
            self.validate_observation(receipt['observation'], intent)
            if receipt['native'] is not None:
                self.validate_native(receipt['native'], intent, receipt['observation'])
            if receipt['capture'] is not None:
                require(intent['tool_name'] == 'execution.results.collect' and receipt['native'] is not None
                    and receipt['observation']['native']['terminal'] and receipt['observation']['native']['quiescent'], 'fluorescence_writer_not_closed')
                capture = validate_fluorescence_native_capture(receipt['capture'], original_plan=receipt['native']['original_plan'])
                self.file_metadata(receipt['source_action_file'], value=receipt['handoff_proof']['start_receipt'], newline=True)
                self.file_metadata(receipt['writer_closure_file'], value=closure_value(receipt), newline=True)
                require(capture['source_action_receipt_ref'] == receipt['source_action_file']['artifact_ref']
                    and capture['writer_closure_receipt_ref'] == receipt['writer_closure_file']['artifact_ref']
                    and capture['driver_started'] is receipt['native']['driver_started'], 'fluorescence_capture_receipt_mismatch')
            else:
                require(receipt['source_action_file'] is None and receipt['writer_closure_file'] is None, 'fluorescence_capture_receipt_mismatch')
        self.validate_worker(receipt)
        files = qualified_files(receipt['worker_capture'], receipt['worker_execution'])
        require(same(receipt['qualified_files'], files), 'fluorescence_qualified_outputs_mismatch')
        if files['projection'] is None:
            require(receipt['projection'] is None, 'fluorescence_projection_mismatch')
        else:
            require(files['sheet'] is not None and files['calculations'] is not None, 'fluorescence_projection_operands_missing')
            projection = validate_fluorescence_projection(receipt['projection'])
            self.file_metadata(files['projection'], value=projection, newline=True, numerical=True)
            require(same(projection['selection'], intent['assignment']['selector']['selection']), 'fluorescence_projection_selection_mismatch')
        if files['context'] is None:
            require(receipt['context'] is None, 'fluorescence_context_mismatch')
        else:
            require(files['projection'] is not None, 'fluorescence_context_projection_missing')
            context = validate_fluorescence_context(receipt['context'])
            self.file_metadata(files['context'], value=context, newline=True, numerical=True)
            require(same(context['selection'], intent['assignment']['selector']['selection'])
                and context['context_fields'] == intent['assignment']['selector']['context_fields'],
                'fluorescence_context_selection_mismatch')
        require(type(receipt['host_failures']) is list, 'fluorescence_failure_mismatch')
        for row in receipt['host_failures']:
            validate_failure(row)
        closed(receipt['facts'], FACT_SOURCES)
        for source, rows in receipt['facts'].items():
            validate_fluorescence_fact_values(source, rows)
        facts, complete = self.publication(receipt, originals=originals)
        require(same(receipt['facts'], facts) and type(receipt['delivery_complete']) is bool
            and receipt['delivery_complete'] == complete and receipt['acquired_population'] == self.acquisition_population(receipt),
            'fluorescence_publication_mismatch')
        if intent['tool_name'] == 'execution.results.status':
            require(all(receipt[key] is None for key in ('native', 'source_action_file', 'writer_closure_file',
                'capture', 'worker_plan', 'worker_capture', 'worker_execution', 'projection', 'context'))
                and not any(receipt['facts'].values()) and not receipt['host_failures'], 'fluorescence_status_publication_mismatch')
        return deepcopy(receipt)

    @staticmethod
    def match_outcome(row, receipt):
        require(row['result'] is not None, 'fluorescence_completed_result_required')
        actual = json.loads(row['result'])
        if 'pending_work_after_action' in actual:
            from .waiting import validate_pending
            validate_pending(actual.pop('pending_work_after_action'))
        require(same(actual, outcome(receipt)), 'fluorescence_completed_result_mismatch')

    def controls(self, intent):
        root = self.action_directory(intent['episode_id'], intent['operation_key'])
        receipt = read_control(root / 'receipt.json')
        if receipt is None:
            return None
        require(same(read_control(root / 'intent.json'), intent) and same(read_control(root / 'handoff.json'), receipt['handoff_proof']),
            'fluorescence_result_control_mismatch')
        for name, key in (('observation.json', 'observation'), ('native-snapshot.json', 'native'), ('capture.json', 'capture'),
                ('worker-plan.json', 'worker_plan'), ('worker-capture.json', 'worker_capture'), ('worker-execution.json', 'worker_execution')):
            require(same(read_control(root / name), receipt[key]), 'fluorescence_result_control_mismatch')
        return self.validate(receipt, intent)

    def read_staged(self, action):
        self.require_action(action)
        receipt, row = self.controls(action.intent), self._selected(action.intent)
        require(receipt is not None or row['result'] is None, 'fluorescence_result_receipt_required')
        if receipt is not None and row['result'] is not None:
            self.match_outcome(row, receipt)
        return deepcopy(receipt)

    def publish(self, action, receipt):
        self.require_action(action)
        receipt = self.validate(receipt, action.intent)
        immutable(action.directory / 'receipt.json', receipt)
        require(same(self.controls(action.intent), receipt), 'fluorescence_result_control_mismatch')
        return deepcopy(receipt)

    def read_completed(self, *, episode_id, operation_key, scope):
        key = (episode_id, operation_key)
        require(key not in _READING.get(), 'fluorescence_result_cyclic_authority')
        token = _READING.set((*_READING.get(), key))
        try:
            with self.store.read_snapshot():
                context = self.returns.context(episode_id)
                self._context(context)
                self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
                root = self.action_directory(episode_id, operation_key)
                intent = read_control(root / 'intent.json')
                require(type(intent) is dict and same(intent, self.intent(context, intent['target'], intent['tool_name'], {}, operation_key)),
                    'fluorescence_result_intent_mismatch')
                require(same(read_control(root.parent.parent / 'assignment.json'), dict(run_id=context.run_id,
                    episode_id=episode_id, assignment=plain(context.assignment), scope=plain(context.scope))), 'fluorescence_assignment_control_mismatch')
                row = self._selected(intent)
                require(row['result'] is not None, 'fluorescence_completed_result_required')
                receipt = self.controls(intent)
                require(receipt is not None, 'fluorescence_result_receipt_required')
                self.match_outcome(row, receipt)
                return deepcopy(receipt)
        finally:
            _READING.reset(token)

    def completed_receipts(self, context):
        self._context(context, allow_unsaved=True)
        result = []
        for row in self.store.db.execute('SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? ORDER BY decision_index', (self.owner.run_id, context.episode_id)):
            action = json.loads(row['action'])
            if (action.get('kind') == 'tool' and action.get('tool') in ('execution.results.collect', 'execution.results.status')
                    and row['result'] is not None and json.loads(row['result']).get('status') == 'completed'):
                result.append(self.read_completed(episode_id=context.episode_id,
                    operation_key=f'{self.owner.run_id}:{context.episode_id}:{row["decision_index"]}', scope=plain(context.scope)))
        return result

    def owns_reference(self, reference):
        if type(reference) is not str or not reference.startswith('artifact_'):
            return False
        for row in self.store.db.execute("SELECT episode_id,result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL "
                "AND json_extract(result,'$.result.version')=?", (self.owner.run_id, VERSION)):
            receipt = json.loads(row['result'])['result']
            captures = [] if receipt['worker_capture'] is None else receipt['worker_capture']['outputs']
            files = [r['observed'] for r in captures if r['observed'] is not None]
            if receipt['capture'] is not None:
                # The original input already has its own caller-owned operand
                # authority. Capturing identical bytes cannot revoke it.
                files.extend(r['retained']['file'] for r in receipt['capture']['files']
                    if r['retained'] is not None and not r['role'].startswith(
                        ('event_input:', 'support_input:', 'report_input:')))
            if any(file['artifact_ref'] == reference for file in files):
                original = self.returns.context(row['episode_id'])
                self.read_completed(episode_id=row['episode_id'], operation_key=receipt['intent']['operation_key'], scope=plain(original.scope))
                return True
        return False

    def baseline_populations(self, context, references):
        from .episode_receipts import EpisodeReceipts
        self._context(context, allow_unsaved=True)
        receipts = EpisodeReceipts(self.store, self.owner.run_id)
        populations, visited, current = set(), set(), context
        while True:
            require(current.episode_id not in visited, 'fluorescence_result_cyclic_authority')
            visited.add(current.episode_id)
            manifest = receipts.manifest(current.episode_id)
            require(same(plain(current.request)['message'].get('knowledge_inheritance'), manifest), 'fluorescence_receipt_inheritance_mismatch')
            parent_id = manifest['parent_episode_id']
            if parent_id is None:
                require(len(current.path) == 1, 'fluorescence_receipt_inheritance_mismatch')
                break
            require('received_report_prefix' in manifest, 'fluorescence_receipt_inheritance_mismatch')
            parent = self.returns.context(parent_id)
            self.returns._commission(parent, current, construction=current is context)
            if parent.role in ('annotation', 'scientific_process'):
                # Receipt inheritance freezes actual returned information, not
                # only artifact references. A projection already communicates
                # the original acquisition even if no sheet was requested or granted.
                sources = (PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE)
                groups, origins, _ = self.returns._received(parent, sources,
                    allowed=manifest['received_report_prefix']['attempts'])
                for source in sources:
                    for fact in groups[source]:
                        for episode_id in origins[return_canonical(fact)]:
                            original_context = self.returns.context(episode_id)
                            for row in self.completed_receipts(original_context):
                                if row['acquired_population'] is not None:
                                    populations.add(row['acquired_population'])
            current = parent
        return populations

    def contribution_origins(self, context, source, fact):
        """Original acquisition owners of a returned value, including recalculations."""
        result = []
        for receipt in self.completed_receipts(context):
            if not any(same(fact, row) for row in receipt['facts'][source]):
                continue
            origins = (receipt['original_origins'] if receipt['intent']['assignment']['selector']['mode']
                == 'saved_sheet_recalculation' else [{'episode_id': context.episode_id}])
            result.extend(row['episode_id'] for row in origins if row['episode_id'] not in result)
        require(bool(result), 'fluorescence_return_contribution_origin_missing')
        return tuple(result)

