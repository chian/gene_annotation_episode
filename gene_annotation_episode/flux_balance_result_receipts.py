"""Original selected FBA action, launch, worker and publication authority.

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
from .episode_bindings import BindingContext
from .execution_contracts import canonical, digest, validate_target
from .flux_balance_contracts import validate_flux_balance_record
from .flux_balance_result_contracts import validate_fba_projection
from .flux_balance_result_selection import validate_flux_balance_result_selector
from .flux_balance_native_capture_contracts import validate_flux_balance_native_capture
from .flux_balance_return_views import (fba_fact_sources, requested_fba_sources,
    validate_fba_fact_values)
from .flux_balance_worker_contracts import OUTPUTS, validate_flux_balance_worker_plan, validate_flux_balance_worker_result
from .native_flux_balance_contracts import (POLICY, flux_balance_driver_argv,
    validate_flux_balance_requested_job, validate_flux_balance_run_plan, path_value)
from .native_flux_balance_preparation import validate_flux_balance_worker_execution
from .native_flux_balance_storage import read_json
from .practical_execution_records import validate_receipt
from .practical_receipt_information import PracticalReceiptInformation
from .genomic_overlap_result_receipts import (GenomicOverlapResultReceipts as _Shared,
    same, unique, immutable, read_control)
from .progress_records import validate_resource_observation

VERSION = 'native_flux_balance_acquired_result_v1'
PUBLIC_VERSION = 'flux_balance_public_result_v1'
_READING = ContextVar('flux_balance_reading', default=())
FACT_SOURCES = tuple(fba_fact_sources())
PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE = FACT_SOURCES

def require(condition, code='fba_result_authority_conflict'):
    if not condition:
        raise ValueError(code)

def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), 'fba_result_invalid_record')

def issue(code, stage, field):
    return validate_flux_balance_record('Issue', dict(code=code, stage=stage, field=field,
        detail_file=None, source_row_index=None, reaction_position=None,
        metabolite_position=None, variable_position=None, constraint_position=None))

def public_issue(value):
    value = validate_flux_balance_record('Issue', value)
    return validate_fba_fact_values(FAILURE_SOURCE,
        [{k: v for k, v in value.items() if k != 'detail_file'}])[0]

def empty_facts():
    return {source: [] for source in FACT_SOURCES}

def empty_files():
    return {row[0]: None for row in OUTPUTS}

def outcome(receipt):
    refs = [row['artifact_ref'] for row in receipt['facts'][SAVED_SOURCE]]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
        'result': deepcopy(receipt), 'feedback': None}


def public_result_view(receipt):
    observation = receipt['observation']
    native = None if observation is None else observation['native']
    return {'version': PUBLIC_VERSION, 'operation': receipt['intent']['tool_name'],
        'mode': receipt['intent']['assignment']['selector']['mode'],
        'observation': None if observation is None else {
            **{key: observation[key] for key in ('state', 'returncode', 'failure_code', 'result_available')},
            'terminal': native['terminal'], 'quiescent': native['quiescent']},
        'facts': deepcopy(receipt['facts']), 'delivery_complete': receipt['delivery_complete'],
        'host_failures': [public_issue(row) for row in receipt['host_failures']]}

def qualified_files(capture, execution):
    result = empty_files()
    # Independent byte-verified outputs survive a failed worker execution.
    if capture is not None and capture['result'] is not None and execution is not None:
        for spec, row in zip(OUTPUTS, capture['outputs']):
            if row['outcome'] == 'verified':
                result[spec[0]] = deepcopy(row['observed'])
    return result

def closure_value(receipt):
    return {'version': 'flux_balance_writer_closure_v1', 'intent_sha256': digest(receipt['intent']),
        'native': receipt['native'], 'observation': receipt['observation']}

class FluxBalanceResultReceipts:
    def __init__(self, owner):
        self.owner, self.store, self._active = owner, owner.store, {}

    @property
    def returns(self):
        return self.owner.native_flux_balance_returns

    def outcome(self, receipt):
        result = outcome(receipt)
        original = self.returns.context(receipt['intent']['target']['origin_episode_id'])
        from .flux_balance_request_binding import is_compact_assignment, materialized_assignment
        if is_compact_assignment(plain(original.assignment)):
            require(same(materialized_assignment(self.store, original), receipt['intent']['target']['assignment']),
                'fba_result_original_context_conflict')
            result['result'] = public_result_view(receipt)
        return result

    def _original_practical_assignment(self, context):
        from .flux_balance_request_binding import is_compact_assignment, materialized_assignment
        return (materialized_assignment(self.store, context)
            if is_compact_assignment(plain(context.assignment)) else plain(context.assignment))

    def _practical_outcome(self, context, receipt):
        from .flux_balance_request_binding import (
            is_compact_assignment, practical_outcome_view, read_request_binding,
        )
        if not is_compact_assignment(plain(context.assignment)):
            return receipt
        control = read_request_binding(self.store, context.run_id, context.episode_id)
        require(same(control['context'], context.as_record()) and len(control['requests']) == 1,
            'fba_result_original_context_conflict')
        return practical_outcome_view(receipt, assignment=control['requests'][0]['assignment'],
            control_version=control['version'])

    # Reuse selected-action locking, immutable controls and retained-file
    # metadata checks. None of these shared ports interprets tool measurements.
    locked_action = _Shared.locked_action
    require_action = _Shared.require_action
    _selected = _Shared._selected
    _artifact_value = _Shared._artifact_value
    capture_control = _Shared.capture_control
    observation = _Shared.observation

    def file_metadata(self, file, *, value=None, newline=False):
        file = validate_flux_balance_record('File', file)
        metadata = self.store.get(file['artifact_ref'])
        closed(metadata, ('id', 'record_type', 'sha256', 'size', 'media_type'))
        require(metadata['record_type'] == 'artifact' and metadata['id'] == file['artifact_ref']
            == 'artifact_' + file['sha256'] and metadata['sha256'] == file['sha256']
            and type(metadata['size']) is int and metadata['size'] == file['size_bytes'], 'fba_result_file_identity_conflict')
        if value is not None:
            raw = canonical(value).encode('utf-8') + (b'\n' if newline else b'')
            require(hashlib.sha256(raw).hexdigest() == file['sha256'] and len(raw) == file['size_bytes'],
                'fba_result_file_value_conflict')
        return file

    def validate_observation(self, value, intent):
        from .native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value['native']
        require(native.get('execution_id') == intent['target']['execution_id']
            and native.get('version') == native_version and type(native.get('terminal')) is bool
            and type(native.get('quiescent')) is bool
            and same(native.get('metadata', {}).get('policy'), POLICY), 'fba_result_observation_conflict')
        proof = read_control(self.action_directory(intent['episode_id'], intent['operation_key']) / 'handoff.json')
        require(proof is not None, 'fba_result_observation_handoff_required')
        start = proof['start_receipt']
        require(native.get('attempt_operation_key') == start['operation_key']
            and native.get('attempt_id') == digest(start['operation_key'])
            and same(native.get('native_flux_balance_input_binding_file'), proof['input_binding']['file']),
            'fba_result_observation_original_identity_conflict')
        if native['terminal'] and native['quiescent']:
            require(native.get('state') == 'returned' and type(native['metadata'].get('service_exit')) is dict
                and value['state'] in {'completed', 'failed'}, 'fba_result_observation_closure_conflict')
        return value

    def action_directory(self, episode_id, operation_key):
        return self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id]) / 'native-flux-balance-actions' / digest(operation_key)

    def _context(self, context, *, allow_unsaved=False):
        self.returns.authenticate(context, allow_unsaved=allow_unsaved)
        require(isinstance(context, BindingContext) and context.role == 'results', 'fba_results_context_required')
        assignment = plain(context.assignment)
        closed(assignment, ('version', 'handoff_ref', 'selector'))
        require(assignment['version'] == 'execution_results_assignment_v1', 'fba_results_assignment_required')
        validate_flux_balance_result_selector(assignment['selector'])
        self.store.validate_scope(plain(context.scope))
        require(len(context.path) > 1, 'fba_parent_commission_required')
        parent = self.returns.context(EpisodeRef(context.run_id, context.path[:-1]).episode_id)
        require(parent.role in ('annotation', 'scientific_process'), 'fba_scientific_parent_required')
        self.returns._commission(parent, context, construction=allow_unsaved)
        if assignment['selector']['mode'] == 'native_result':
            self.returns.declarations.possession(parent, assignment['handoff_ref'],
                before=int(context.path[-1][1][6:]))
        return assignment

    def _target(self, context, assignment, target):
        target = validate_target(plain(target))
        require(target['run_id'] == self.owner.run_id == context.run_id and target['resource_kind'] == 'local'
            and target['handle'] == assignment['handoff_ref'], 'fba_target_mismatch')
        request = validate_flux_balance_requested_job(target['assignment']['requested_job'])
        require(target['request_sha256'] == digest(request) and target['assignment']['resource_id'] == target['resource_id'], 'fba_target_mismatch')
        self.store.validate_scope(target['scope'], parent_scope=plain(context.scope))
        resource = self.owner.resources.get(target['resource_id'])
        require(type(resource) is dict and resource['kind'] == 'local' and same(resource['policy'], POLICY), 'fba_resource_mismatch')
        reader = self.owner.job_progress_provider.targets
        require(same(reader.resources.get(target['resource_id']), resource) and target['resource_id'] in reader.operations, 'fba_resource_mismatch')
        reader.operations[target['resource_id']].validate_assignment(target['assignment'])
        if assignment['selector']['mode'] == 'native_result':
            validate_flux_balance_result_selector(assignment['selector'], job=request)
        return target

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ('execution.results.status', 'execution.results.collect') and type(arguments) is dict and arguments == {}, 'fba_selected_result_action_required')
        value = dict(version='flux_balance_result_intent_v1', run_id=context.run_id, episode_id=context.episode_id,
            path=plain(context.path), scope=plain(context.scope), assignment=assignment,
            original_request_sha256=digest(plain(context.request)), operation_key=operation_key,
            tool_name=tool_name, arguments={}, target=self._target(context, assignment, target))
        self._selected(value)
        return value

    def _handoff_metadata(self, target, scope):
        """Authenticate actual saved practical ancestry, never live science."""
        reader = self.owner.job_progress_provider.targets
        require(same(reader.read_target(target['handle'], scope), target), 'fba_result_target_history_conflict')
        practical = PracticalReceiptInformation(self.store, self.owner.run_id)
        body = practical.read(target['handle'], scope)
        source = self.store.get(target['handle'])
        snapshot = practical._artifact_json(source['request_ref'])
        target_owner = self.returns.context(body['episode_id'])
        self.returns.authenticate(target_owner)
        require(same(self._original_practical_assignment(target_owner), snapshot['assignment'])
            and same(plain(target_owner.scope), body['scope']), 'fba_result_target_context_conflict')
        target_row = practical._selected(body['receipt'])
        require(target_row['result'] is not None, 'fba_result_target_action_incomplete')
        target_result = json.loads(target_row['result'])
        require(target_result.get('status') in ('completed', 'partial')
            and same(target_result.get('result'), self._practical_outcome(target_owner, body['receipt']))
            and target['handle'] in target_result.get('record_refs', []), 'fba_result_target_action_conflict')
        detail = body['receipt']['outcome'].get('native_outcome') or {}
        key = detail.get('attempt_operation_key')
        require(type(key) is str, 'fba_result_start_missing')
        starts = practical._sources(practical._accession(target['origin_episode_id'], key))
        require(len(starts) == 1, 'fba_result_start_missing')
        start_source = starts[0]
        start_body = practical.read(start_source['id'], scope)
        start_snapshot = practical._artifact_json(start_source['request_ref'])
        start = validate_receipt(start_body['receipt'])
        selected = practical._selected(start)
        require(selected['result'] is not None and start['tool_name'] == 'practical.job.start'
            and start['operation_key'] == key and start['episode_id'] == target['origin_episode_id']
            and start['assignment_sha256'] == digest(target['assignment'])
            and same(start_snapshot['assignment'], target['assignment']), 'fba_result_start_conflict')
        original = self.returns.context(target['origin_episode_id'])
        self.returns.authenticate(original)
        require(same(self._original_practical_assignment(original), target['assignment'])
            and same(plain(original.scope), start_body['scope']), 'fba_result_original_context_conflict')
        original_input = self.owner.flux_balance_inputs.received(original)
        expected_file = original_input['file']
        for candidate in (body['receipt'], start):
            job = candidate['outcome'].get('facts', {}).get('requested_job') or {}
            native = candidate['outcome'].get('native_outcome') or {}
            require(job.get('execution_id') == target['execution_id']
                and job.get('requested_job_sha256') == target['request_sha256']
                and job.get('argv') == target['assignment']['requested_job']['argv']
                and same(job.get('environment'), target['assignment']['requested_job']['environment'])
                and native.get('attempt_operation_key') == key and native.get('attempt_id') == digest(key)
                and same(native.get('native_flux_balance_input_binding_file'), expected_file),
                'fba_result_original_start_identity_conflict')
        require(same(json.loads(selected['result']).get('result'), self._practical_outcome(original, start)),
            'fba_result_start_outcome_conflict')
        return {'source_record': source, 'body': body, 'assignment_snapshot': snapshot,
            'start_source_record': start_source, 'start_body': start_body,
            'start_assignment_snapshot': start_snapshot, 'start_receipt': start,
            'input_binding': original_input}

    def validate_handoff(self, proof, intent):
        closed(proof, ('source_record', 'body', 'assignment_snapshot', 'start_source_record',
            'start_body', 'start_assignment_snapshot', 'start_receipt', 'input_binding'))
        expected = self._handoff_metadata(intent['target'], intent['scope'])
        require(same(proof, expected), 'fba_result_handoff_conflict')

    def read_handoff(self, action):
        self.require_action(action)
        path = action.directory / 'handoff.json'
        saved = read_control(path)
        if saved is None:
            saved = self._handoff_metadata(action.intent['target'], action.intent['scope'])
            immutable(path, saved)
        self.validate_handoff(saved, action.intent)
        return deepcopy(saved)

    def selected_priors(self, proof):
        """Only original received prior File identities, never a new acquisition."""
        rows = []
        for row in proof['input_binding']['receipt']['binding']['prior_sources']:
            file = self.file_metadata(row['file'])
            #697 observes the selected bytes and preserves missing/mismatch.
            path = self.store.path / 'artifacts' / file['sha256'][:2] / file['sha256']
            rows.append({'file': deepcopy(file), 'path': str(path)})
        return rows

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
        require(bool(matches), "flux_balance_saved_handoff_conflict")
        target = matches[0]["intent"]["target"]
        require(all(same(row["intent"]["target"], target) for row in matches), "flux_balance_saved_target_conflict")
        return matches

    def native_snapshot(self, action, observation):
        self.require_action(action)
        path = action.directory / 'native-snapshot.json'
        value = read_control(path)
        if value is None:
            from .native_flux_balance_local import local_flux_balance_plan
            from .native_flux_balance_contracts import STARTED_FILENAME
            from .native_file_capture import capture_native_file, retained_native_file
            target = action.intent['target']
            plan = local_flux_balance_plan(target['assignment'], target['execution_id'])
            root = Path(target['execution_id']).parent
            handle = read_json(target['execution_id'])
            invoke = read_json(root / 'invoke.json')
            request_file = capture_native_file(self.store, directory=str(root),
                relative_path=Path(handle['paths']['request']).name, format='native_local_job_request')
            from .native_flux_balance_storage import read_bytes
            request_raw = read_bytes(retained_native_file(self.store, request_file)).decode('utf-8')
            try:
                marker = read_json(Path(plan['attempt_directory']) / STARTED_FILENAME)
            except FileNotFoundError:
                marker = None
            native_receipt = observation['native'].get('native_receipt')
            never_started = marker is None and type(native_receipt) is dict and native_receipt.get('execution_failure') is not None
            value = dict(original_plan=plan, handle=handle, request=json.loads(request_raw), request_raw=request_raw,
                invoke=invoke, input_binding_file=invoke['native_flux_balance_input_binding_file'],
                started_marker=marker, driver_started=True if marker is not None else False if never_started else None,
                plan_file=self.capture_control(action, 'native-plan.json', plan, plan['version']),
                handle_file=self.capture_control(action, 'native-handle.json', handle, 'durable_systemd_native_job_v2'),
                invoke_file=self.capture_control(action, 'native-invoke.json', invoke, 'flux_balance_invoke_v1'),
                request_file=request_file, started_marker_file=None if marker is None else
                    self.capture_control(action, 'driver-started.json', marker, 'flux_balance_started_control_v1'))
            self.validate_native(value, action.intent, observation)
            immutable(path, value)
        self.validate_native(value, action.intent, observation)
        return deepcopy(value)

    def validate_native(self, value, intent, observation):
        from .native_flux_balance_local import _request, _invoke
        from .native_lifecycle import VERSION as native_version
        closed(value, ('original_plan', 'handle', 'request', 'request_raw', 'invoke', 'invoke_file',
            'input_binding_file', 'started_marker', 'driver_started', 'plan_file', 'handle_file',
            'request_file', 'started_marker_file'))
        plan = validate_flux_balance_run_plan(value['original_plan'])
        target, ident = intent['target'], plan['identity']
        require(same(plan['requested_job'], target['assignment']['requested_job']) and same(plan['policy'], POLICY)
            and ident['run_id'] == intent['run_id'] and ident['episode_id'] == target['origin_episode_id']
            and ident['execution_id'] == target['execution_id'] and ident['resource_id'] == target['resource_id']
            and ident['assignment_sha256'] == digest(target['assignment']) and ident['requested_job_sha256'] == target['request_sha256'],
            'fba_original_native_identity_mismatch')
        selection = target['assignment'].get('native_flux_balance_execution')
        require((selection is None and plan['version'] == 'flux_balance_run_plan_v1')
            or (selection is not None and plan['version'] == 'flux_balance_run_plan_v2'
                and same(plan['environment_binding']['selection'], selection)), 'fba_native_environment_selection_conflict')
        handoff = read_control(self.action_directory(intent['episode_id'], intent['operation_key']) / 'handoff.json')
        require(handoff is not None and ident['operation_key'] == handoff['start_receipt']['operation_key']
            and same(value['input_binding_file'], handoff['input_binding']['file']), 'fba_native_start_mismatch')
        self.file_metadata(value['input_binding_file'], value=handoff['input_binding']['receipt'])
        require(same(value['invoke'], _invoke(plan, value['input_binding_file'])), 'fba_native_invoke_conflict')
        self.file_metadata(value['invoke_file'], value=value['invoke'])
        handle, request, root = value['handle'], value['request'], Path(target['execution_id']).parent
        require(type(handle) is dict and handle.get('version') == native_version
            and handle.get('stage') in ('prepared', 'submitting', 'released')
            and handle.get('command') == flux_balance_driver_argv(plan) and handle.get('cwd') == str(root)
            and same(handle.get('metadata', {}).get('policy'), POLICY)
            and all(handle.get(role) == str(root / (role + '.log')) for role in ('stdout', 'stderr')),
            'fba_native_handle_mismatch')
        paths = handle.get('paths')
        require(type(paths) is dict and {'request', 'ready', 'release', 'status', 'result', 'launcher'} <= paths.keys()
            and not paths.keys() - {'request', 'ready', 'release', 'status', 'result', 'launcher', 'statistics', 'native_events'}
            and all(type(p) is str for p in paths.values()) and len(set(paths.values())) == len(paths),
            'fba_native_request_mismatch')
        for path in paths.values():
            path_value(path, absolute=True)
            require(Path(path).parent == root, 'fba_native_request_mismatch')
        require(same(request, _request(plan, paths)), 'fba_native_request_mismatch')
        require(type(value['request_raw']) is str, 'fba_native_request_mismatch')
        raw = value['request_raw'].encode('utf-8')
        self.file_metadata(value['request_file'])
        require(same(json.loads(raw), request) and hashlib.sha256(raw).hexdigest() == value['request_file']['sha256']
            == handle.get('request_sha256') and len(raw) == value['request_file']['size_bytes'], 'fba_native_request_mismatch')
        self.file_metadata(value['plan_file'], value=plan)
        self.file_metadata(value['handle_file'], value=handle)
        for name, expected_format in (('plan_file', plan['version']), ('handle_file', native_version),
                ('invoke_file', 'flux_balance_invoke_v1'), ('request_file', 'native_local_job_request')):
            require(value[name]['format'] == expected_format, 'fba_native_control_format_conflict')
        marker = value['started_marker']
        if marker is None:
            native = observation['native'].get('native_receipt')
            expected = False if type(native) is dict and native.get('execution_failure') is not None else None
            require(value['driver_started'] is expected and value['started_marker_file'] is None, 'fba_native_marker_mismatch')
        else:
            closed(marker, ('plan_sha256', 'started_at') + (('environment_observation_sha256',)
                if plan['version'] == 'flux_balance_run_plan_v2' else ()))
            require(marker['plan_sha256'] == digest(plan) and type(marker['started_at']) is str and marker['started_at']
                and value['driver_started'] is True, 'fba_native_marker_mismatch')
            if plan['version'] == 'flux_balance_run_plan_v2':
                require(type(marker['environment_observation_sha256']) is str
                    and re.fullmatch(r'[0-9a-f]{64}', marker['environment_observation_sha256']) is not None,
                    'fba_native_marker_mismatch')
            self.file_metadata(value['started_marker_file'], value=marker)
            require(value['started_marker_file']['format'] == 'flux_balance_started_control_v1',
                'fba_native_control_format_conflict')

    def validate_worker(self, receipt):
        plan, capture, execution = (receipt[k] for k in ('worker_plan', 'worker_capture', 'worker_execution'))
        if plan is None:
            require(capture is None and execution is None, 'fba_worker_receipt_mismatch')
            return
        plan = validate_flux_balance_worker_plan(plan)
        intent, selector = receipt['intent'], receipt['intent']['assignment']['selector']
        require(plan['directory'] == str(self.action_directory(intent['episode_id'], intent['operation_key']) / 'worker')
            and same(plan['selector'], selector), 'fba_worker_selection_mismatch')
        if plan['mode'] == 'native_result':
            require(same(plan['original_plan'], receipt['native']['original_plan']) and same(plan['capture'], receipt['capture']),
                'fba_worker_native_binding_mismatch')
            retained = [row['retained'] for row in plan['capture']['files']]
            retained.extend(plan['capture']['controls'].values())
            retained.extend(plan['capture']['prior_sources'])
        else:
            require(same(plan['sheet']['file'], selector['saved_sheet_file']), 'fba_worker_saved_binding_mismatch')
            retained = [plan['sheet']]
        for row in retained:
            if row is not None:
                file = self.file_metadata(row['file'])
                require(row['path'] == str(self.store.path / 'artifacts' / file['sha256'][:2] / file['sha256']), 'fba_worker_input_path_mismatch')
        require(type(capture) is dict and execution is not None, 'fba_worker_receipt_mismatch')
        closed(capture, ('version', 'plan_file', 'execution_receipt_file', 'worker_result_file', 'result', 'outputs', 'failures'))
        require(capture['version'] == 'flux_balance_worker_capture_v1', 'fba_worker_receipt_mismatch')
        self.file_metadata(capture['plan_file'], value=plan, newline=True)
        self.file_metadata(capture['execution_receipt_file'], value=execution, newline=True)
        validate_flux_balance_worker_execution(execution, plan=plan, plan_file=capture['plan_file'])
        for key in ('handle_file', 'request_file', 'stdout_file', 'stderr_file'):
            self.file_metadata(execution[key])
        result = capture['result']
        if result is None:
            require(capture['outputs'] == [], 'fba_worker_outputs_mismatch')
            if capture['worker_result_file'] is not None:
                self.file_metadata(capture['worker_result_file'])
        else:
            validate_flux_balance_worker_result(result)
            self.file_metadata(capture['worker_result_file'], value=result, newline=True)
            require(result['plan_sha256'] == digest(plan) and same(result['selector'], selector)
                and len(capture['outputs']) == len(OUTPUTS), 'fba_worker_result_mismatch')
            for declared, row in zip(result['outputs'], capture['outputs']):
                closed(row, ('declared', 'observed', 'outcome', 'failure'))
                require(same(row['declared'], declared['declaration']), 'fba_worker_outputs_mismatch')
                actual, d = row['observed'], row['declared']
                if actual is not None:
                    self.file_metadata(actual)
                equal = actual is not None and all(actual[k] == d[k] for k in ('sha256', 'size_bytes', 'format'))
                require((row['outcome'] == 'verified' and d['state'] == 'present' and equal and row['failure'] is None)
                    or (row['outcome'] == 'declared_absent' and d['state'] == 'absent' and actual is None and row['failure'] is None)
                    or (row['outcome'] == 'unavailable' and d['state'] == 'present' and actual is None and row['failure'] == 'capture_file_unavailable')
                    or (row['outcome'] == 'digest_mismatch' and d['state'] == 'present' and actual is not None and not equal
                        and row['failure'] == 'capture_file_digest_mismatch'), 'fba_worker_capture_mismatch')
        for row in capture['failures']:
            row = validate_flux_balance_record("Issue", row)
            require(row['stage'] == 'capture' and type(row['field']) is str
                and row['field'].startswith('/worker/') and row['code'] in {
                    'binding_unavailable', 'artifact_missing', 'artifact_identity_conflict', 'schema_invalid'}
                and row['detail_file'] is None and all(row[key] is None for key in (
                    'source_row_index', 'reaction_position', 'metabolite_position',
                    'variable_position', 'constraint_position')), 'fba_worker_capture_issue_conflict')

    def acquisition_population(self, receipt):
        worker = receipt['worker_capture']
        if (receipt['intent']['assignment']['selector']['mode'] == 'native_result'
                and receipt['intent']['tool_name'] == 'execution.results.collect'
                and receipt['qualified_files']['sheet'] is not None and worker is not None
                and worker['result'] is not None and worker['result']['native_association'] == 'verified'
                and worker['result']['new_attempt_evidence_roles']):
            return digest(receipt['native']['original_plan']['identity'])
        return None

    def publication(self, receipt, *, originals=None):
        context = self.returns.context(receipt['intent']['episode_id'])
        schema = plain(context.request)['report_contract']['measurements']['schema']
        requested = requested_fba_sources(schema)
        facts, issues = empty_facts(), list(receipt['host_failures'])
        for key in ('capture', 'worker_capture'):
            if receipt[key] is not None:
                issues.extend(receipt[key]['failures'])
        worker = receipt['worker_capture']
        if worker is not None and worker['result'] is not None:
            issues.extend(worker['result']['failures'])
        public = [public_issue(row) for row in issues]
        if receipt['projection'] is not None:
            public.extend(row['issue'] for row in receipt['projection']['qualification_issues'])
        collecting = receipt['intent']['tool_name'] == 'execution.results.collect'
        if collecting:
            if PROJECTION_SOURCE in requested and receipt['projection'] is not None:
                facts[PROJECTION_SOURCE] = [deepcopy(receipt['projection'])]
            if SAVED_SOURCE in requested and receipt['qualified_files']['sheet'] is not None:
                facts[SAVED_SOURCE] = [deepcopy(receipt['qualified_files']['sheet'])]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = unique(public)
        execution = receipt['worker_execution']
        complete = bool(collecting and requested and worker is not None and worker['result'] is not None
            and execution is not None and execution['terminal'] is True and execution['quiescent'] is True
            and (PROJECTION_SOURCE not in requested or facts[PROJECTION_SOURCE])
            and (SAVED_SOURCE not in requested or facts[SAVED_SOURCE]))
        if receipt['intent']['assignment']['selector']['mode'] == 'native_result':
            observation = receipt['observation']
            complete = bool(complete and observation is not None and observation['native']['terminal']
                and observation['native']['quiescent'] and receipt['capture'] is not None)
        return facts, complete

    def validate(self, receipt, intent):
        closed(receipt, ('version', 'intent', 'handoff_proof', 'original_origins', 'observation', 'native',
            'source_action_file', 'writer_closure_file', 'capture', 'worker_plan', 'worker_capture', 'worker_execution',
            'qualified_files', 'projection', 'host_failures', 'facts', 'acquired_population', 'delivery_complete'))
        require(receipt['version'] == VERSION and same(receipt['intent'], intent), 'fba_result_receipt_mismatch')
        self.validate_handoff(receipt['handoff_proof'], intent)
        saved = intent['assignment']['selector']['mode'] == 'saved_sheet_recalculation'
        originals = None
        if saved:
            originals = self.origins(self.returns.context(intent['episode_id']), intent['assignment'])
            require(receipt['original_origins'] == [{'episode_id': r['intent']['episode_id'], 'operation_key': r['intent']['operation_key']}
                for r in originals] and all(same(r['intent']['target'], intent['target']) for r in originals), 'fba_saved_origin_mismatch')
            require(all(receipt[k] is None for k in ('observation', 'native', 'source_action_file', 'writer_closure_file', 'capture')),
                'fba_saved_native_work_disallowed')
        else:
            require(receipt['original_origins'] == [], 'fba_native_origin_mismatch')
            self.validate_observation(receipt['observation'], intent)
            if receipt['native'] is not None:
                self.validate_native(receipt['native'], intent, receipt['observation'])
            if receipt['capture'] is not None:
                require(intent['tool_name'] == 'execution.results.collect' and receipt['native'] is not None
                    and receipt['observation']['native']['terminal'] and receipt['observation']['native']['quiescent'], 'fba_writer_not_closed')
                capture = validate_flux_balance_native_capture(receipt['capture'], original_plan=receipt['native']['original_plan'])
                self.file_metadata(receipt['source_action_file'], value=receipt['handoff_proof']['start_receipt'])
                self.file_metadata(receipt['writer_closure_file'], value=closure_value(receipt))
                require(capture['source_action_receipt_ref'] == receipt['source_action_file']['artifact_ref']
                    and capture['writer_closure_receipt_ref'] == receipt['writer_closure_file']['artifact_ref']
                    and same(capture['input_binding_file'], receipt['handoff_proof']['input_binding']['file'])
                    and capture['driver_started'] is receipt['native']['driver_started'], 'fba_capture_receipt_mismatch')
            else:
                require(receipt['source_action_file'] is None and receipt['writer_closure_file'] is None, 'fba_capture_receipt_mismatch')
        self.validate_worker(receipt)
        files = qualified_files(receipt['worker_capture'], receipt['worker_execution'])
        require(same(receipt['qualified_files'], files), 'fba_qualified_outputs_mismatch')
        if files['projection'] is None:
            require(receipt['projection'] is None, 'fba_projection_mismatch')
        else:
            projection = validate_fba_projection(receipt['projection'])
            self.file_metadata(files['projection'], value=projection, newline=True)
            require(same(projection['selector'], intent['assignment']['selector']['projection']), 'fba_projection_selection_mismatch')
        for row in receipt['host_failures']:
            validate_flux_balance_record("Issue", row)
        closed(receipt['facts'], FACT_SOURCES)
        for source, rows in receipt['facts'].items():
            validate_fba_fact_values(source, rows)
        facts, complete = self.publication(receipt, originals=originals)
        require(same(receipt['facts'], facts) and type(receipt['delivery_complete']) is bool
            and receipt['delivery_complete'] == complete and receipt['acquired_population'] == self.acquisition_population(receipt),
            'fba_publication_mismatch')
        if intent['tool_name'] == 'execution.results.status':
            require(receipt['worker_plan'] is None and receipt['capture'] is None and not any(receipt['facts'].values()), 'fba_status_publication_mismatch')
        return receipt

    def match_outcome(self, row, receipt):
        require(row['result'] is not None, 'fba_completed_result_required')
        actual = json.loads(row['result'])
        if 'pending_work_after_action' in actual:
            from .waiting import validate_pending
            validate_pending(actual.pop('pending_work_after_action'))
        require(same(actual, self.outcome(receipt)), 'fba_completed_result_mismatch')

    def controls(self, intent):
        root = self.action_directory(intent['episode_id'], intent['operation_key'])
        receipt = read_control(root / 'receipt.json')
        if receipt is None:
            return None
        require(same(read_control(root / 'intent.json'), intent) and same(read_control(root / 'handoff.json'), receipt['handoff_proof']),
            'fba_result_control_mismatch')
        for name, key in (('observation.json', 'observation'), ('native-snapshot.json', 'native'), ('capture.json', 'capture'),
                ('worker-plan.json', 'worker_plan'), ('worker-capture.json', 'worker_capture'), ('worker-execution.json', 'worker_execution')):
            require(same(read_control(root / name), receipt[key]), 'fba_result_control_mismatch')
        return self.validate(receipt, intent)

    def read_staged(self, action):
        self.require_action(action)
        receipt, row = self.controls(action.intent), self._selected(action.intent)
        require(receipt is not None or row['result'] is None, 'fba_result_receipt_required')
        if receipt is not None and row['result'] is not None:
            self.match_outcome(row, receipt)
        return deepcopy(receipt)

    def publish(self, action, receipt):
        self.require_action(action)
        receipt = self.validate(receipt, action.intent)
        immutable(action.directory / 'receipt.json', receipt)
        require(same(self.controls(action.intent), receipt), 'fba_result_control_mismatch')
        return deepcopy(receipt)

    def read_completed(self, *, episode_id, operation_key, scope):
        key = (episode_id, operation_key)
        require(key not in _READING.get(), 'fba_result_cyclic_authority')
        token = _READING.set((*_READING.get(), key))
        try:
            with self.store.read_snapshot():
                context = self.returns.context(episode_id)
                self._context(context)
                self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
                root = self.action_directory(episode_id, operation_key)
                intent = read_control(root / 'intent.json')
                require(type(intent) is dict and same(intent, self.intent(context, intent['target'], 'execution.results.collect', {}, operation_key)),
                    'fba_result_intent_mismatch')
                require(same(read_control(root.parent.parent / 'assignment.json'), dict(run_id=context.run_id,
                    episode_id=episode_id, assignment=plain(context.assignment), scope=plain(context.scope))), 'fba_assignment_control_mismatch')
                row = self._selected(intent)
                require(row['result'] is not None, 'fba_completed_result_required')
                receipt = self.controls(intent)
                require(receipt is not None, 'fba_result_receipt_required')
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
            if action.get('kind') == 'tool' and action.get('tool') == 'execution.results.collect' and row['result'] is not None and json.loads(row['result']).get('status') == 'completed':
                result.append(self.read_completed(episode_id=context.episode_id,
                    operation_key=f'{self.owner.run_id}:{context.episode_id}:{row["decision_index"]}', scope=plain(context.scope)))
        return result

    def owns_reference(self, reference):
        if type(reference) is not str or not reference.startswith('artifact_'):
            return False
        for row in self.store.db.execute("SELECT episode_id,decision_index,result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL "
                "AND json_extract(result,'$.result.version') IN (?,?)", (self.owner.run_id, VERSION, PUBLIC_VERSION)):
            receipt = json.loads(row['result'])['result']
            if receipt['version'] == PUBLIC_VERSION:
                receipt = read_control(self.action_directory(row['episode_id'],
                    f'{self.owner.run_id}:{row["episode_id"]}:{row["decision_index"]}') / 'receipt.json')
                require(receipt is not None, 'fba_result_receipt_required')
                self.match_outcome(row, receipt)
            captures = [] if receipt['worker_capture'] is None else receipt['worker_capture']['outputs']
            files = [r['observed'] for r in captures if r['observed'] is not None]
            if receipt['capture'] is not None:
                # The original input already has its own caller-owned operand
                # authority. Capturing identical bytes cannot revoke it.
                files.extend(r['retained']['file'] for r in receipt['capture']['files']
                    if r['retained'] is not None and r['role'] not in ('original_model', 'selected_request'))
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
            require(current.episode_id not in visited, 'fba_result_cyclic_authority')
            visited.add(current.episode_id)
            manifest = receipts.manifest(current.episode_id)
            require(same(plain(current.request)['message'].get('knowledge_inheritance'), manifest), 'fba_receipt_inheritance_mismatch')
            parent_id = manifest['parent_episode_id']
            if parent_id is None:
                require(len(current.path) == 1, 'fba_receipt_inheritance_mismatch')
                break
            require('received_report_prefix' in manifest, 'fba_receipt_inheritance_mismatch')
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

