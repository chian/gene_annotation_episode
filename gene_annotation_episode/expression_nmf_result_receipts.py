"""Original selected NMF action, launch, worker and publication authority.

These durable controls retain outcomes before credit. Historical validation
uses frozen controls and artifact metadata; it neither loads matrices nor polls
or reruns a native producer.
"""
from copy import deepcopy
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path
import re

from method_loop.identities import EpisodeRef
from .communication import plain
from .domain import identity
from .episode_bindings import BindingContext
from .execution_contracts import canonical, digest, validate_target
from .expression_nmf_result_contracts import (require, validate_file, validate_issue, validate_projection,
    validate_expression_nmf_result_selector, validate_expression_nmf_native_capture)
from .expression_nmf_return_views import (FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    requested_expression_nmf_sources, validate_expression_nmf_fact_values)
from .expression_nmf_result_worker import OUTPUTS, validate_expression_nmf_worker_plan, validate_expression_nmf_worker_result
from .native_expression_nmf_contracts import (POLICY, expression_nmf_driver_argv, expression_nmf_environment,
    validate_expression_nmf_requested_job, validate_expression_nmf_run_plan)
from .native_expression_nmf_preparation import validate_worker_execution
from .native_expression_nmf_storage import read_json
from .practical_execution_records import validate_receipt
from .practical_receipt_information import PracticalReceiptInformation
from .genomic_overlap_result_receipts import (GenomicOverlapResultReceipts as _Shared,
    closed, same, unique, immutable, read_control, directory, regular)

VERSION = 'native_expression_nmf_acquired_result_v1'
_READING = ContextVar('expression_nmf_reading', default=())
_CLOSED_PATHS = ContextVar('expression_nmf_closed_read_paths', default=())

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
    if capture is not None and capture['result'] is not None and execution is not None and execution['failure'] is None and execution['returncode'] == 0:
        for spec, row in zip(OUTPUTS, capture['outputs']):
            if row['outcome'] == 'verified':
                result[spec[0]] = deepcopy(row['observed'])
    return result

def closure_value(receipt):
    return {'version': 'expression_nmf_writer_closure_v1', 'intent_sha256': digest(receipt['intent']),
        'native': receipt['native'], 'observation': receipt['observation']}

class ExpressionNMFResultReceipts:
    def __init__(self, owner):
        self.owner, self.store, self._active = owner, owner.store, {}

    @property
    def returns(self):
        return self.owner.native_expression_nmf_returns

    # Reuse selected-action locking, immutable controls and retained-file
    # metadata checks. None of these shared ports interprets tool measurements.
    locked_action = _Shared.locked_action
    require_action = _Shared.require_action
    _selected = _Shared._selected
    file_metadata = _Shared.file_metadata
    _artifact_value = _Shared._artifact_value
    capture_control = _Shared.capture_control
    observation = _Shared.observation
    validate_observation = _Shared.validate_observation

    def action_directory(self, episode_id, operation_key):
        return self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id]) / 'native-expression-nmf-actions' / digest(operation_key)

    def _context(self, context, *, allow_unsaved=False):
        self.returns.authenticate(context, allow_unsaved=allow_unsaved)
        require(isinstance(context, BindingContext) and context.role == 'results', 'nmf_results_context_required')
        assignment = plain(context.assignment)
        closed(assignment, ('version', 'handoff_ref', 'selector'))
        require(assignment['version'] == 'execution_results_assignment_v1', 'nmf_results_assignment_required')
        validate_expression_nmf_result_selector(assignment['selector'])
        self.store.validate_scope(plain(context.scope))
        require(len(context.path) > 1, 'nmf_parent_commission_required')
        self.returns._commission(self.returns.context(EpisodeRef(context.run_id, context.path[:-1]).episode_id),
            context, construction=allow_unsaved)
        return assignment

    def _target(self, context, assignment, target):
        target = validate_target(plain(target))
        require(target['run_id'] == self.owner.run_id == context.run_id and target['resource_kind'] == 'local'
            and target['handle'] == assignment['handoff_ref'], 'nmf_target_mismatch')
        request = validate_expression_nmf_requested_job(target['assignment']['requested_job'])
        require(target['request_sha256'] == digest(request) and target['assignment']['resource_id'] == target['resource_id'], 'nmf_target_mismatch')
        self.store.validate_scope(target['scope'], parent_scope=plain(context.scope))
        resource = self.owner.resources.get(target['resource_id'])
        require(type(resource) is dict and resource['kind'] == 'local' and same(resource['policy'], POLICY), 'nmf_resource_mismatch')
        reader = self.owner.job_progress_provider.targets
        require(same(reader.resources.get(target['resource_id']), resource) and target['resource_id'] in reader.operations, 'nmf_resource_mismatch')
        reader.operations[target['resource_id']].validate_assignment(target['assignment'])
        validate_expression_nmf_result_selector(assignment['selector'], job=request['native_expression_nmf'])
        return target

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ('execution.results.status', 'execution.results.collect') and type(arguments) is dict and arguments == {}, 'nmf_selected_result_action_required')
        value = dict(version='expression_nmf_result_intent_v1', run_id=context.run_id, episode_id=context.episode_id,
            path=plain(context.path), scope=plain(context.scope), assignment=assignment,
            original_request_sha256=digest(plain(context.request)), operation_key=operation_key,
            tool_name=tool_name, arguments={}, target=self._target(context, assignment, target))
        self._selected(value)
        return value

    def validate_handoff(self, proof, intent):
        from .terminal_scientific_evidence import is_terminal_target, validate_terminal_handoff
        if is_terminal_target(intent['target']):
            validate_terminal_handoff(proof, intent, self.store, self.owner.run_id)
            return
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
        requested = validate_expression_nmf_requested_job(assignment["requested_job"])
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
        from .terminal_scientific_evidence import is_terminal_target, read_terminal_handoff
        if is_terminal_target(action.intent['target']):
            proof = read_terminal_handoff(self.store, self.owner.run_id,
                action.intent['target'], action.intent['scope'])
            immutable(action.directory / 'handoff.json', proof)
            return deepcopy(proof)
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
        require(bool(matches), "expression_nmf_saved_handoff_conflict")
        target = matches[0]["intent"]["target"]
        require(all(same(row["intent"]["target"], target) for row in matches), "expression_nmf_saved_target_conflict")
        return matches

    def native_snapshot(self, action, observation):
        self.require_action(action)
        from .terminal_scientific_evidence import is_terminal_target, terminal_native_snapshot
        if is_terminal_target(action.intent['target']):
            value = terminal_native_snapshot(self, action, observation)
            immutable(action.directory / 'native-snapshot.json', value)
            return value
        path = action.directory / 'native-snapshot.json'
        value = read_control(path)
        if value is None:
            from .native_expression_nmf_local import local_expression_nmf_plan
            from .native_expression_nmf_contracts import STARTED_FILENAME
            from .native_expression_nmf_storage import confined_file, regular
            from .native_file_capture import capture_native_file, retained_native_file
            target = action.intent['target']
            plan = local_expression_nmf_plan(target['assignment'], target['execution_id'])
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
                plan_file=self.capture_control(action, 'native-plan.json', plan, 'expression_nmf_run_plan_v1'),
                handle_file=self.capture_control(action, 'native-handle.json', handle, 'durable_systemd_native_job_v2'),
                request_file=request_file, started_marker_file=None if marker is None else
                    self.capture_control(action, 'driver-started.json', marker, 'expression_nmf_driver_started_v1'))
            self.validate_native(value, action.intent, observation)
            immutable(path, value)
        self.validate_native(value, action.intent, observation)
        return deepcopy(value)

    def validate_native(self, value, intent, observation):
        from .terminal_scientific_evidence import is_terminal_target, validate_terminal_native
        if is_terminal_target(intent['target']):
            validate_terminal_native(value, intent, observation, self.store, self.owner.run_id)
            return
        from .native_expression_nmf_local import _request
        from .native_lifecycle import VERSION as native_version
        closed(value, ('original_plan', 'handle', 'request', 'request_raw', 'started_marker',
            'driver_started', 'plan_file', 'handle_file', 'request_file', 'started_marker_file'))
        plan = validate_expression_nmf_run_plan(value['original_plan'])
        target, ident = intent['target'], plan['identity']
        require(same(plan['requested_job'], target['assignment']['requested_job']) and same(plan['policy'], POLICY)
            and ident['run_id'] == intent['run_id'] and ident['episode_id'] == target['origin_episode_id']
            and ident['execution_id'] == target['execution_id'] and ident['resource_id'] == target['resource_id']
            and ident['assignment_sha256'] == digest(target['assignment']) and ident['requested_job_sha256'] == target['request_sha256'],
            'nmf_original_native_identity_mismatch')
        handoff = read_control(self.action_directory(intent['episode_id'], intent['operation_key']) / 'handoff.json')
        require(handoff is not None and ident['operation_key'] == handoff['start_receipt']['operation_key'], 'nmf_native_start_mismatch')
        handle, request, root = value['handle'], value['request'], Path(target['execution_id']).parent
        require(handle.get('version') == native_version and handle.get('stage') in ('prepared', 'submitting', 'released')
            and handle.get('command') == expression_nmf_driver_argv(plan) and handle.get('cwd') == str(root)
            and same(handle.get('metadata', {}).get('policy'), POLICY), 'nmf_native_handle_mismatch')
        paths = handle.get('paths')
        require(type(paths) is dict and {'request', 'ready', 'release', 'status', 'result', 'launcher'} <= paths.keys()
            and not paths.keys() - {'request', 'ready', 'release', 'status', 'result', 'launcher', 'statistics', 'native_events'}
            and len(set(paths.values())) == len(paths) and all(Path(p).parent == root and str(Path(p)) == p for p in paths.values()),
            'nmf_native_request_mismatch')
        require(same(request, _request(plan, paths)), 'nmf_native_request_mismatch')
        raw = value['request_raw'].encode('utf-8')
        require(same(json.loads(raw), request) and hashlib.sha256(raw).hexdigest() == value['request_file']['sha256']
            == handle.get('request_sha256') and len(raw) == value['request_file']['size_bytes'], 'nmf_native_request_mismatch')
        self.file_metadata(value['request_file'])
        self.file_metadata(value['plan_file'], value=plan)
        self.file_metadata(value['handle_file'], value=handle)
        marker = value['started_marker']
        if marker is None:
            native = observation['native'].get('native_receipt')
            expected = False if type(native) is dict and native.get('execution_failure') is not None else None
            require(value['driver_started'] is expected and value['started_marker_file'] is None, 'nmf_native_marker_mismatch')
        else:
            closed(marker, ('plan', 'started_at'))
            require(same(marker['plan'], plan) and type(marker['started_at']) is str and marker['started_at']
                and value['driver_started'] is True, 'nmf_native_marker_mismatch')
            self.file_metadata(value['started_marker_file'], value=marker)

    def validate_worker(self, receipt):
        plan, capture, execution = (receipt[k] for k in ('worker_plan', 'worker_capture', 'worker_execution'))
        if plan is None:
            require(capture is None and execution is None, 'nmf_worker_receipt_mismatch')
            return
        plan = validate_expression_nmf_worker_plan(plan)
        intent, selector = receipt['intent'], receipt['intent']['assignment']['selector']
        identity = (id(self), intent['episode_id'], intent['operation_key'], digest(receipt))
        recorded = [roots for key, roots in _CLOSED_PATHS.get() if key == identity]
        require(len(recorded) <= 1, 'nmf_closed_worker_context_mismatch')
        worker_directory = (recorded[0]['worker_directory'] if recorded else
            str(self.action_directory(intent['episode_id'], intent['operation_key']) / 'worker'))
        store_root = Path(recorded[0]['store_root']) if recorded else self.store.path
        require(plan['directory'] == worker_directory
            and same(plan['selector'], selector), 'nmf_worker_selection_mismatch')
        if plan['mode'] == 'native_result':
            require(same(plan['original_plan'], receipt['native']['original_plan']) and same(plan['capture'], receipt['capture']),
                'nmf_worker_native_binding_mismatch')
            retained = [row['retained'] for row in plan['capture']['files']]
        else:
            require(same(plan['sheet']['file'], selector['saved_sheet_file']), 'nmf_worker_saved_binding_mismatch')
            retained = [plan['sheet']]
        for row in retained:
            if row is not None:
                file = self.file_metadata(row['file'])
                require(row['path'] == str(store_root / 'artifacts' / file['sha256'][:2] / file['sha256']), 'nmf_worker_input_path_mismatch')
        require(type(capture) is dict and execution is not None, 'nmf_worker_receipt_mismatch')
        closed(capture, ('version', 'plan_file', 'execution_receipt_file', 'worker_result_file', 'result', 'outputs', 'failures'))
        require(capture['version'] == 'expression_nmf_worker_capture_v1', 'nmf_worker_receipt_mismatch')
        self.file_metadata(capture['plan_file'], value=plan, newline=True)
        self.file_metadata(capture['execution_receipt_file'], value=execution, newline=True)
        validate_worker_execution(execution, plan=plan, plan_file=capture['plan_file'])
        for key in ('handle_file', 'request_file', 'stdout_file', 'stderr_file'):
            self.file_metadata(execution[key])
        result = capture['result']
        if result is None:
            require(capture['outputs'] == [], 'nmf_worker_outputs_mismatch')
            if capture['worker_result_file'] is not None:
                self.file_metadata(capture['worker_result_file'])
        else:
            validate_expression_nmf_worker_result(result)
            self.file_metadata(capture['worker_result_file'], value=result, newline=True)
            require(result['plan_sha256'] == digest(plan) and same(result['selector'], selector)
                and len(capture['outputs']) == len(OUTPUTS), 'nmf_worker_result_mismatch')
            if result['native_binding']:
                expected_input = intent['target']['assignment']['requested_job']['native_expression_nmf']['input']
                require(result['input_identity'] == {k: expected_input[k] for k in ('sha256', 'size_bytes')}, 'nmf_worker_input_identity_mismatch')
            for declared, row in zip(result['outputs'], capture['outputs']):
                closed(row, ('declared', 'observed', 'outcome', 'failure'))
                require(same(row['declared'], declared['declaration']), 'nmf_worker_outputs_mismatch')
                actual, d = row['observed'], row['declared']
                if actual is not None:
                    self.file_metadata(actual)
                equal = actual is not None and all(actual[k] == d[k] for k in ('sha256', 'size_bytes', 'format'))
                require((row['outcome'] == 'verified' and d['state'] == 'present' and equal and row['failure'] is None)
                    or (row['outcome'] == 'declared_absent' and d['state'] == 'absent' and actual is None and row['failure'] is None)
                    or (row['outcome'] == 'unavailable' and d['state'] == 'present' and actual is None and row['failure'] == 'capture_file_unavailable')
                    or (row['outcome'] == 'digest_mismatch' and d['state'] == 'present' and actual is not None and not equal
                        and row['failure'] == 'capture_file_digest_mismatch'), 'nmf_worker_capture_mismatch')
        for row in capture['failures']:
            validate_issue(row)

    def original_acquisition_complete(self, receipt):
        if receipt['intent']['assignment']['selector']['mode'] == 'saved_sheet_recalculation':
            context = self.returns.context(receipt['intent']['episode_id'])
            return any(self.original_acquisition_complete(row) for row in self.origins(context, receipt['intent']['assignment']))
        observed, capture = receipt['observation'], receipt['worker_capture']
        return bool(observed is not None and observed['state'] == 'completed' and observed['returncode'] == 0
            and observed['native']['terminal'] and observed['native']['quiescent'] and capture is not None
            and capture['result'] is not None and capture['result']['original_fit_acquired']
            and capture['result']['native_outcome'] in ('complete', 'qualified') and not capture['failures']
            and all(receipt['qualified_files'][role] is not None for role in ('sheet', 'calculations')))

    def acquisition_population(self, receipt):
        worker = receipt['worker_capture']
        if (receipt['intent']['assignment']['selector']['mode'] == 'native_result'
                and receipt['intent']['tool_name'] == 'execution.results.collect'
                and receipt['qualified_files']['sheet'] is not None and worker is not None
                and worker['result'] is not None and worker['result']['original_fit_acquired']):
            return digest(receipt['native']['original_plan']['identity'])
        return None

    def publication(self, receipt, *, originals=None):
        context = self.returns.context(receipt['intent']['episode_id'])
        schema = plain(context.request)['report_contract']['measurements']['schema']
        requested = requested_expression_nmf_sources(schema)
        facts = empty_facts()
        issues = list(receipt['host_failures'])
        for key in ('capture', 'worker_capture'):
            value = receipt[key]
            if value is not None:
                issues.extend(value['failures'])
        worker = receipt['worker_capture']
        if worker is not None and worker['result'] is not None:
            issues.extend(worker['result']['failures'])
        if receipt['projection'] is not None:
            issues.extend(receipt['projection']['failures'])
        collecting = receipt['intent']['tool_name'] == 'execution.results.collect'
        if collecting:
            if PROJECTION_SOURCE in requested and receipt['projection'] is not None:
                facts[PROJECTION_SOURCE] = [deepcopy(receipt['projection'])]
            if SAVED_SOURCE in requested and receipt['qualified_files']['sheet'] is not None:
                facts[SAVED_SOURCE] = [deepcopy(receipt['qualified_files']['sheet'])]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = unique(issues)
        complete = bool(collecting and requested and receipt['projection'] is not None and not receipt['host_failures']
            and worker is not None and worker['result'] is not None and worker['result']['analysis_complete']
            and not worker['failures'] and all(receipt['qualified_files'][key] is not None for key in ('sheet', 'calculations', 'projection')))
        if receipt['intent']['assignment']['selector']['mode'] == 'native_result':
            complete = complete and self.original_acquisition_complete(receipt)
        else:
            originals = self.origins(context, receipt['intent']['assignment']) if originals is None else originals
            complete = complete and any(self.original_acquisition_complete(row) for row in originals)
        return facts, bool(complete)

    def validate(self, receipt, intent):
        closed(receipt, ('version', 'intent', 'handoff_proof', 'original_origins', 'observation', 'native',
            'source_action_file', 'writer_closure_file', 'capture', 'worker_plan', 'worker_capture', 'worker_execution',
            'qualified_files', 'projection', 'host_failures', 'facts', 'acquired_population', 'delivery_complete'))
        require(receipt['version'] == VERSION and same(receipt['intent'], intent), 'nmf_result_receipt_mismatch')
        self.validate_handoff(receipt['handoff_proof'], intent)
        saved = intent['assignment']['selector']['mode'] == 'saved_sheet_recalculation'
        originals = None
        if saved:
            originals = self.origins(self.returns.context(intent['episode_id']), intent['assignment'])
            require(receipt['original_origins'] == [{'episode_id': r['intent']['episode_id'], 'operation_key': r['intent']['operation_key']}
                for r in originals] and all(same(r['intent']['target'], intent['target']) for r in originals), 'nmf_saved_origin_mismatch')
            require(all(receipt[k] is None for k in ('observation', 'native', 'source_action_file', 'writer_closure_file', 'capture')),
                'nmf_saved_native_work_disallowed')
        else:
            require(receipt['original_origins'] == [], 'nmf_native_origin_mismatch')
            self.validate_observation(receipt['observation'], intent)
            if receipt['native'] is not None:
                self.validate_native(receipt['native'], intent, receipt['observation'])
            if receipt['capture'] is not None:
                require(intent['tool_name'] == 'execution.results.collect' and receipt['native'] is not None
                    and receipt['observation']['native']['terminal'] and receipt['observation']['native']['quiescent'], 'nmf_writer_not_closed')
                capture = validate_expression_nmf_native_capture(receipt['capture'], original_plan=receipt['native']['original_plan'])
                if receipt['native'].get('version') == 'terminal_native_snapshot_v1':
                    from .terminal_scientific_evidence import terminal_file_identity
                    snapshots = {row['path']: row for row in receipt['native']['command_proof']['output_snapshots']}
                    for row in capture['files']:
                        path = str(Path(receipt['native']['original_plan']['attempt_directory']) / row['relative_path'])
                        snapshot = snapshots.get(path)
                        expected = (terminal_file_identity(snapshot, row['format'])
                            if snapshot is not None and snapshot['available'] else None)
                        actual = row['retained']['file'] if row['retained'] is not None else None
                        require(actual == expected, 'nmf_terminal_capture_file_mismatch')
                self.file_metadata(receipt['source_action_file'], value=receipt['handoff_proof']['start_receipt'])
                self.file_metadata(receipt['writer_closure_file'], value=closure_value(receipt))
                require(capture['source_action_receipt_ref'] == receipt['source_action_file']['artifact_ref']
                    and capture['writer_closure_receipt_ref'] == receipt['writer_closure_file']['artifact_ref']
                    and capture['driver_started'] is receipt['native']['driver_started'], 'nmf_capture_receipt_mismatch')
            else:
                require(receipt['source_action_file'] is None and receipt['writer_closure_file'] is None, 'nmf_capture_receipt_mismatch')
        self.validate_worker(receipt)
        files = qualified_files(receipt['worker_capture'], receipt['worker_execution'])
        require(same(receipt['qualified_files'], files), 'nmf_qualified_outputs_mismatch')
        if files['projection'] is None:
            require(receipt['projection'] is None, 'nmf_projection_mismatch')
        else:
            require(files['sheet'] is not None and files['calculations'] is not None, 'nmf_projection_operands_missing')
            projection = validate_projection(receipt['projection'])
            self.file_metadata(files['projection'], value=projection, newline=True)
            require(same(projection['selector'], intent['assignment']['selector']['projection']), 'nmf_projection_selection_mismatch')
        for row in receipt['host_failures']:
            validate_issue(row)
        closed(receipt['facts'], FACT_SOURCES)
        for source, rows in receipt['facts'].items():
            validate_expression_nmf_fact_values(source, rows)
        facts, complete = self.publication(receipt, originals=originals)
        require(same(receipt['facts'], facts) and type(receipt['delivery_complete']) is bool
            and receipt['delivery_complete'] == complete and receipt['acquired_population'] == self.acquisition_population(receipt),
            'nmf_publication_mismatch')
        if intent['tool_name'] == 'execution.results.status':
            require(receipt['worker_plan'] is None and receipt['capture'] is None and not any(receipt['facts'].values()), 'nmf_status_publication_mismatch')
        return receipt

    @staticmethod
    def match_outcome(row, receipt):
        require(row['result'] is not None, 'nmf_completed_result_required')
        actual = json.loads(row['result'])
        if 'pending_work_after_action' in actual:
            from .waiting import validate_pending
            validate_pending(actual.pop('pending_work_after_action'))
        require(same(actual, outcome(receipt)), 'nmf_completed_result_mismatch')

    def _read_controls(self, intent):
        root = self.action_directory(intent['episode_id'], intent['operation_key'])
        receipt = read_control(root / 'receipt.json')
        if receipt is None:
            return None
        require(same(read_control(root / 'intent.json'), intent) and same(read_control(root / 'handoff.json'), receipt['handoff_proof']),
            'nmf_result_control_mismatch')
        for name, key in (('observation.json', 'observation'), ('native-snapshot.json', 'native'), ('capture.json', 'capture'),
                ('worker-plan.json', 'worker_plan'), ('worker-capture.json', 'worker_capture'), ('worker-execution.json', 'worker_execution')):
            require(same(read_control(root / name), receipt[key]), 'nmf_result_control_mismatch')
        return receipt

    def controls(self, intent):
        receipt = self._read_controls(intent)
        return None if receipt is None else self.validate(receipt, intent)

    def _closed_read_roots(self, context, receipt):
        """Authenticate literal producer roots for one actually closed receipt.

        Physical controls and metadata are still read from the current owner.
        These original lexical roots neither select a filesystem reader nor
        authorize preparation, a live worker or another action.
        """
        row = self.store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.owner.run_id, context.episode_id)).fetchone()
        if (row is None or row['state'] != 'yielded'
                or row['completion'] is None or row['archive'] is None):
            return None
        require(same(json.loads(row['request']), plain(context.request))
            and same(json.loads(row['path']), plain(context.path)), 'nmf_closed_context_mismatch')
        completion, descriptor = json.loads(row['completion']), json.loads(row['archive'])
        closed(completion, ('ended_by', 'actions'))
        require(type(completion['actions']) is int and completion['actions'] >= 0,
            'nmf_closed_context_mismatch')
        closed(descriptor, ('file', 'sha256', 'index_sha256'))
        require(type(descriptor['file']) is str and Path(descriptor['file']).name == descriptor['file']
            and descriptor['file'].endswith('.json') and all(type(descriptor[key]) is str
                and re.fullmatch(r'[0-9a-f]{64}', descriptor[key]) is not None
                for key in ('sha256', 'index_sha256')), 'nmf_closed_archive_mismatch')
        from method_loop.archive import ArchivedRecord
        archive = ArchivedRecord(self.owner.directory / 'archive' / descriptor['file'],
            descriptor['sha256'], descriptor['index_sha256']).load()
        require(archive['run_id'] == self.owner.run_id and archive['episode_id'] == context.episode_id
            and same(archive['path'], plain(context.path))
            and same(archive['request'], plain(context.request))
            and archive['ended_by'] == completion['ended_by']
            and type(archive['units_consumed']) is int
            and archive['units_consumed'] == completion['actions'] == len(archive['units']),
            'nmf_closed_archive_mismatch')
        schema = plain(context.request)['report_contract']['measurements']['schema']
        wanted = requested_expression_nmf_sources(schema)
        frozen = self.store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.owner.run_id, context.episode_id)).fetchone()
        require(frozen is not None and frozen['form'] is not None, 'nmf_closed_facts_mismatch')
        final_values = self.returns._values(json.loads(frozen['form']), schema)
        require(self.returns._frozen(context, final_values)
            and all(any(same(value, final) for final in final_values[source])
                for source in wanted for value in receipt['facts'][source]),
            'nmf_closed_facts_mismatch')
        if receipt['worker_plan'] is None:
            return None
        plan = validate_expression_nmf_worker_plan(receipt['worker_plan'])
        capture, execution = receipt['worker_capture'], receipt['worker_execution']
        require(type(capture) is dict and execution is not None, 'nmf_worker_receipt_mismatch')
        self.file_metadata(capture['plan_file'], value=plan, newline=True)
        self.file_metadata(capture['execution_receipt_file'], value=execution, newline=True)
        validate_worker_execution(execution, plan=plan, plan_file=capture['plan_file'])
        intent = receipt['intent']
        suffix = Path('execution-results') / digest([intent['run_id'], intent['episode_id']]) / \
            'native-expression-nmf-actions' / digest(intent['operation_key']) / 'worker'
        directory = Path(plan['directory'])
        require(directory.is_absolute() and str(directory) == plan['directory']
            and '..' not in directory.parts
            and directory.parts[-len(suffix.parts):] == suffix.parts,
            'nmf_closed_worker_directory_mismatch')
        selected = (intent['target']['assignment']['requested_job']['native_expression_nmf']['input']
            if plan['mode'] == 'native_result' else plan['sheet']['file'])
        selected_path = (selected['path'] if plan['mode'] == 'native_result' else plan['sheet']['path'])
        if plan['mode'] == 'native_result':
            from .native_file_capture import _metadata
            metadata = _metadata(self.store, selected['artifact_ref'])
            require(metadata['sha256'] == selected['sha256'] and metadata['size'] == selected['size_bytes'],
                'nmf_closed_worker_input_path_mismatch')
            selected_file = selected
        else:
            selected_file = self.file_metadata(selected)
        path = Path(selected_path)
        require(path.is_absolute() and str(path) == selected_path and '..' not in path.parts
            and path.parts[-3:] == ('artifacts', selected_file['sha256'][:2], selected_file['sha256']),
            'nmf_closed_worker_input_path_mismatch')
        return dict(worker_directory=plan['directory'], store_root=str(path.parents[2]))

    def read_staged(self, action):
        self.require_action(action)
        receipt, row = self.controls(action.intent), self._selected(action.intent)
        require(receipt is not None or row['result'] is None, 'nmf_result_receipt_required')
        if receipt is not None and row['result'] is not None:
            self.match_outcome(row, receipt)
        return deepcopy(receipt)

    def publish(self, action, receipt):
        self.require_action(action)
        receipt = self.validate(receipt, action.intent)
        immutable(action.directory / 'receipt.json', receipt)
        require(same(self.controls(action.intent), receipt), 'nmf_result_control_mismatch')
        return deepcopy(receipt)

    def read_completed(self, *, episode_id, operation_key, scope):
        key = (episode_id, operation_key)
        require(key not in _READING.get(), 'nmf_result_cyclic_authority')
        token = _READING.set((*_READING.get(), key))
        try:
            with self.store.read_snapshot():
                context = self.returns.context(episode_id)
                self._context(context)
                self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
                root = self.action_directory(episode_id, operation_key)
                intent = read_control(root / 'intent.json')
                require(type(intent) is dict and same(intent, self.intent(context, intent['target'], 'execution.results.collect', {}, operation_key)),
                    'nmf_result_intent_mismatch')
                require(same(read_control(root.parent.parent / 'assignment.json'), dict(run_id=context.run_id,
                    episode_id=episode_id, assignment=plain(context.assignment), scope=plain(context.scope))), 'nmf_assignment_control_mismatch')
                row = self._selected(intent)
                require(row['result'] is not None, 'nmf_completed_result_required')
                receipt = self._read_controls(intent)
                require(receipt is not None, 'nmf_result_receipt_required')
                self.match_outcome(row, receipt)
                roots = self._closed_read_roots(context, receipt)
                paths_token = None
                if roots is not None:
                    identity = (id(self), episode_id, operation_key, digest(receipt))
                    paths_token = _CLOSED_PATHS.set((*_CLOSED_PATHS.get(), (identity, roots)))
                try:
                    return deepcopy(self.validate(receipt, intent))
                finally:
                    if paths_token is not None:
                        _CLOSED_PATHS.reset(paths_token)
        finally:
            _READING.reset(token)

    def completed_receipts(self, context):
        self._context(context, allow_unsaved=True)
        result = []
        for row in self.store.db.execute('SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? ORDER BY decision_index', (self.owner.run_id, context.episode_id)):
            action = json.loads(row['action'])
            if action.get('kind') == 'tool' and action.get('tool') == 'execution.results.collect' and row['result'] is not None and json.loads(row['result']).get('status') == 'completed':
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
                    if r['retained'] is not None and r['role'] != 'original_input')
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
            require(current.episode_id not in visited, 'nmf_result_cyclic_authority')
            visited.add(current.episode_id)
            manifest = receipts.manifest(current.episode_id)
            require(same(plain(current.request)['message'].get('knowledge_inheritance'), manifest), 'nmf_receipt_inheritance_mismatch')
            parent_id = manifest['parent_episode_id']
            if parent_id is None:
                require(len(current.path) == 1, 'nmf_receipt_inheritance_mismatch')
                break
            require('received_report_prefix' in manifest, 'nmf_receipt_inheritance_mismatch')
            parent = self.returns.context(parent_id)
            self.returns._commission(parent, current, construction=current is context)
            if parent.role in ('annotation', 'scientific_process'):
                # Receipt inheritance freezes actual returned information, not
                # only artifact references. A projection already communicates
                # the original fit even if no sheet was requested or granted.
                sources = (PROJECTION_SOURCE, SAVED_SOURCE)
                groups, origins, _ = self.returns._received(parent, sources,
                    allowed=manifest['received_report_prefix']['attempts'])
                for source in sources:
                    for fact in groups[source]:
                        for episode_id in origins[canonical(fact)]:
                            original_context = self.returns.context(episode_id)
                            for row in self.completed_receipts(original_context):
                                if not any(same(fact, recorded) for recorded in row['facts'][source]):
                                    continue
                                originals = [row] if row['acquired_population'] is not None else (self.origins(
                                    original_context, row['intent']['assignment']) if row['intent']['assignment']['selector']['mode']
                                    == 'saved_sheet_recalculation' else [])
                                populations.update(r['acquired_population'] for r in originals
                                    if r['acquired_population'] is not None)
            current = parent
        return populations

