"""Bounded HMMER operations inside the shared execution episode.

This adapter contains no polling, retry, model or episode loop. API targets use
``digest(original API assignment)`` as request_sha256; the HTTP request, submitted
FASTA bytes and parsed sequence each retain their own distinct frozen identities.
Native monitoring has independent observation custody and never changes launch
receipts, completion proofs or its closed controller history.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import uuid

from .acquisition import AcquisitionError, SourceSnapshot
from .communication import plain, validate_form
from .domain import ContractError, identity, validate_schema
from .execution_contracts import canonical, digest, validate_api_assignment, validate_target
from .practical_execution_records import validate_completion_proof
from .provider_jobs import HMMER_IDENTITY_VERSION, validate_remote_identity

PROVIDER = 'episode.api_hmmer_handoff'
VERSION = 'api_hmmer_execution_v1'
HANDOFF_VERSION = 'api_hmmer_handoff_v1'
RESULT_DESCRIPTION = ('Acquire exactly the assigned HMMER result page from the original API handoff; '
    'retain native scores, domain alignments and separately defined numerical correspondence measurements.')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def hmmer_operation_catalog(role):
    """Declared contracts without an invented query, target or service call."""
    if role not in {'launch_api', 'results'}:
        raise ValueError('api_execution_role_required')
    descriptions = ({'api.hmmer.result': RESULT_DESCRIPTION}
        if role == 'results' else {
            'api.hmmer.databases': 'Read one current served database inventory; no job is selected or submitted.',
            'api.hmmer.prepare': 'Freeze the assigned query sequence, submitted FASTA and exact request identities.',
            'api.hmmer.submit': 'Commit intent and submit the original assigned search once; uncertain submissions never repeat.',
            'api.hmmer.status': 'Read the original submitted search with one status request.',
            'api.hmmer.check_handoff': 'Read one status response and validate a usable original monitoring/results handoff.'})
    return [{'name': name, 'description': description, 'input_schema': _object({})}
            for name, description in descriptions.items()]


def _envelope(key, *, status='completed', result=None, refs=(), feedback=None):
    return {'status': status, 'operation_ref': identity('api_operation', {'key': key}),
            'record_refs': list(refs), 'changed_record_refs': list(refs),
            'result': result, 'feedback': feedback}


def _native_status(snapshot, request, remote_id):
    try:
        native = json.loads(snapshot.content)
        canonical(native)  # Native projections must remain finite recorded JSON.
        task = native.get('task') if isinstance(native, dict) else None
        if (not isinstance(native, dict) or task is not None and
                (not isinstance(task, dict) or not isinstance(task.get('status', 'UNKNOWN'), str))):
            raise ValueError('status_object_required')
    except (ValueError, TypeError, UnicodeError) as error:
        raise AcquisitionError('provider_status_response_invalid', snapshot=snapshot,
                               phase='status_response') from error
    try:
        validate_remote_identity(native, request, remote_id)
    except AcquisitionError as error:
        error.snapshot = snapshot
        raise
    status = (task or {}).get('status', 'UNKNOWN')
    states = {'PENDING': 'submitted', 'RECEIVED': 'submitted', 'STARTED': 'running',
              'RETRY': 'running', 'SUCCESS': 'completed', 'FAILURE': 'failed', 'REVOKED': 'failed'}
    return native, status, states.get(status, 'unknown')


class HMMERAPIExecution:
    def __init__(self, store, *, run_id, directory, configuration, tool_registry,
                 handoff_unit, acquired_record_unit):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_execution_run_required')
        for value in (handoff_unit, acquired_record_unit):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        self.store, self.run_id, self.directory = store, run_id, Path(directory)
        self.configuration = json.loads(canonical(configuration))
        if (not isinstance(self.configuration, dict) or not self.configuration or
                any(not isinstance(key, str) or not key or not isinstance(value, dict)
                    or value.get('kind') != 'hmmer_api' or set(value) - {'kind', 'service'}
                    or value.get('service', 'ebi_hmmer') != 'ebi_hmmer'
                    for key, value in self.configuration.items())):
            raise ValueError('explicit_api_resources_required')
        if tool_registry.store is not store or not callable(getattr(tool_registry, 'publish_hmmer_result', None)):
            raise ValueError('actual_tool_registry_required_for_api_execution')
        self.tools, self.clients = tool_registry, tool_registry.clients
        self.handoff_unit, self.acquired_record_unit = handoff_unit, acquired_record_unit
        store.db.executescript('''
            CREATE TABLE IF NOT EXISTS api_execution_episodes (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, assignment TEXT NOT NULL,
                scope TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));
            CREATE TABLE IF NOT EXISTS api_execution_preparations (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, request TEXT NOT NULL,
                fasta_ref TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));
            CREATE TABLE IF NOT EXISTS api_execution_actions (
                operation_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                name TEXT NOT NULL, arguments TEXT NOT NULL, intent TEXT NOT NULL,
                snapshot TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS api_execution_observations (
                operation_key TEXT PRIMARY KEY, target TEXT NOT NULL, observation TEXT);
        ''')

    def _constraints(self, assignment):
        constraints = assignment['constraints']
        for key, value in constraints.items():
            if key == 'allowed_resource_ids':
                if not isinstance(value, list) or assignment['resource_id'] not in value:
                    raise ValueError('api_resource_constraint_conflict')
            elif key == 'allowed_kinds':
                if not isinstance(value, list) or 'api' not in value:
                    raise ValueError('api_kind_constraint_conflict')
            elif key == 'kind':
                if value not in {'api', 'hmmer_api'}:
                    raise ValueError('api_kind_constraint_conflict')
            elif key in {'service', 'resource_id', 'subject_ref', 'algorithm', 'database', 'parameters', 'page_size'}:
                if value != assignment[key]:
                    raise ValueError('api_request_constraint_conflict')
            else:
                raise ValueError('unsupported_api_execution_constraint:'+key)

    def _assignment(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role == 'results':
            raw = plain(context.assignment)
            if (set(raw) != {'version', 'handoff_ref', 'selector'}
                    or raw['version'] != 'execution_results_assignment_v1'
                    or not isinstance(raw['selector'], dict)):
                raise ValueError('invalid_api_results_assignment')
            selector = raw['selector']
            if (set(selector) - {'page', 'page_size'} or 'page' not in selector
                    or any(type(value) is not int or value <= 0 for value in selector.values())):
                raise ValueError('invalid_api_results_selector')
            assignment = self.read_target(raw['handoff_ref'], context.scope)['assignment']
            if ('page_size' in assignment['constraints'] and
                    selector.get('page_size', assignment['page_size']) != assignment['constraints']['page_size']):
                raise ValueError('api_result_page_size_constraint_conflict')
            return assignment
        if context.role != 'launch_api':
            raise ValueError('api_execution_role_required')
        assignment = validate_api_assignment(plain(context.assignment))
        self._constraints(assignment)
        if assignment['resource_id'] not in self.configuration:
            raise ValueError('api_resource_not_bound')
        self.tools._check_sequence_operand(assignment['subject_ref'], plain(context.scope))
        return assignment

    def initialize(self, context):
        self._assignment(context)
        assignment, scope = canonical(context.assignment), canonical(context.scope)
        with self.store.transaction():
            row = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes '
                'WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
            if row is not None:
                if row['assignment'] != assignment or row['scope'] != scope:
                    raise ValueError('api_original_assignment_conflict')
            else:
                self.store.db.execute('INSERT INTO api_execution_episodes VALUES(?,?,?,?)',
                    (self.run_id, context.episode_id, assignment, scope))
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

    def catalog(self, context):
        self._assignment(context)
        return hmmer_operation_catalog(context.role)

    def _snapshot(self, snapshot):
        fields = asdict(snapshot)
        fields.pop('content')
        fields['content_ref'] = self.store.artifact(snapshot.content, snapshot.media_type)
        return canonical(fields)

    def _load_snapshot(self, saved):
        fields = json.loads(saved)
        fields['content'] = self.store.get_artifact(fields.pop('content_ref'))
        return SourceSnapshot(**fields)

    def _selected(self, context, name, arguments, key):
        prefix = f'{self.run_id}:{context.episode_id}:'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('api_selected_action_identity_required')
        try:
            row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? AND decision_index=?', (self.run_id, context.episode_id, int(suffix))).fetchone()
        except Exception as error:
            raise ValueError('api_selected_action_missing') from error
        if row is None:
            raise ValueError('api_selected_action_missing')
        action = json.loads(row['action'])
        if (action.get('kind') != 'tool' or action.get('tool') != name
                or canonical(action.get('arguments')) != canonical(arguments)):
            raise ValueError('api_selected_action_conflict')
        return row

    def _prepare(self, context):
        assignment = self._assignment(context)
        row = self.store.db.execute('SELECT request,fasta_ref FROM api_execution_preparations '
            'WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if row:
            return json.loads(row['request']), row['fasta_ref']
        subject = self.tools._check_sequence_operand(assignment['subject_ref'], plain(context.scope))
        sequence = self.tools._sequence(subject['id'], molecule_model='protein')
        from .domain import parse_sequences
        fasta = f'>{subject["id"]}\n{sequence}'
        parsed = parse_sequences(fasta, format='fasta', molecule='protein')
        if len(parsed) != 1:
            raise ValueError('single_query_required')
        from .episode_input_versions import pin_commission_inputs
        input_identities = pin_commission_inputs(self.store, [subject['id']], resource_input_versions=[
            {'reference': subject['id'], 'version': None, 'content_sha256': None}])
        request = {'input_identities': input_identities, 'subject_ref': subject['id'], 'algorithm': assignment['algorithm'],
            'database': assignment['database'], 'parameters': assignment['parameters'],
            'page_size': assignment['page_size'], 'resource_id': assignment['resource_id'],
            'assignment_sha256': digest(assignment), 'identity_version': HMMER_IDENTITY_VERSION,
            'query_sha256': hashlib.sha256(fasta.encode('utf-8')).hexdigest(),
            'query_sha256_representation': 'submitted_fasta_utf8_bytes',
            'sequence_sha256': hashlib.sha256(parsed[0].sequence.encode('ascii')).hexdigest(),
            'sequence_sha256_representation': 'single_fasta_sequence_uppercase_whitespace_removed_ascii',
            'query_length': len(parsed[0].sequence), 'molecule_model': 'protein',
            'molecule_assignment': 'not_performed'}
        with self.store.transaction():
            fasta_ref = self.store.artifact(fasta, 'text/x-fasta')
            self.store.db.execute('INSERT INTO api_execution_preparations VALUES(?,?,?,?)',
                (self.run_id, context.episode_id, canonical(request), fasta_ref))
        return request, fasta_ref

    def _job(self, episode_id):
        rows = self.store.db.execute('SELECT * FROM provider_jobs WHERE operation_key IN '
            '(SELECT operation_key FROM api_execution_actions WHERE run_id=? AND episode_id=? '
            "AND name='api.hmmer.submit')", (self.run_id, episode_id)).fetchall()
        if len(rows) != 1:
            raise ValueError('api_original_submission_missing' if not rows else 'api_submission_identity_conflict')
        return dict(rows[0])

    def _update_job(self, job_ref, **values):
        with self.store.transaction():
            self.store.db.execute('UPDATE provider_jobs SET '+','.join(key+'=?' for key in values)+' WHERE id=?',
                                 [*values.values(), job_ref])
            if values.get('error_code', 'not_supplied') is None:
                self.store.db.execute('DELETE FROM provider_job_failures WHERE job_ref=?', (job_ref,))

    def _save_action(self, key, result):
        with self.store.transaction():
            self.store.db.execute('UPDATE api_execution_actions SET result=? WHERE operation_key=?',
                                  (canonical(result), key))
        return result

    async def _http(self, key, function, *args, fresh, **kwargs):
        row = self.store.db.execute('SELECT snapshot FROM api_execution_actions WHERE operation_key=?', (key,)).fetchone()
        if row['snapshot'] is not None:
            return self._load_snapshot(row['snapshot'])
        if not fresh:
            raise AcquisitionError('api_operation_response_unknown', phase='recovery')
        try:
            snapshot = await asyncio.to_thread(function, *args, **kwargs)
        except BaseException as error:
            if getattr(error, 'snapshot', None) is not None:
                self.store.db.execute('UPDATE api_execution_actions SET snapshot=? WHERE operation_key=?',
                                      (self._snapshot(error.snapshot), key))
            raise
        # Exact response bytes commit before parsing UUIDs, native status or rows.
        with self.store.transaction():
            self.store.db.execute('UPDATE api_execution_actions SET snapshot=? WHERE operation_key=?',
                                  (self._snapshot(snapshot), key))
        return snapshot

    def _failure(self, key, error, *, job=None, record_job_failure=True):
        from .api_error_feedback import api_error_feedback
        snapshot = getattr(error, 'snapshot', None)
        saved = self._snapshot(snapshot) if snapshot is not None else None
        cause_error = error.__cause__ or error
        diagnostic = self.store.artifact(saved or canonical({'representation': 'local_exception',
            'exception_type': type(cause_error).__name__, 'message': str(cause_error),
            'details': getattr(error, 'diagnostic', None)}), 'application/json')
        code = (error.code if isinstance(error, AcquisitionError) else str(error)
                if isinstance(error, (ValueError, ContractError)) else 'api_execution_failed')
        phase = getattr(error, 'phase', None)
        client_phase = phase
        if job is not None:
            phase = 'submission' if job['remote_id'] is None else 'result' if not record_job_failure else 'status'
        submission_outcome = (getattr(error, 'submission_outcome', None) or
            ('remote_handle_returned' if job is not None and job['remote_id'] is not None else 'unknown'))
        cause = {'code': code, 'exception_type': type(cause_error).__name__, 'phase': phase,
            'client_phase': client_phase, 'submission_outcome': submission_outcome,
            'retry_after': getattr(error, 'retry_after', None), 'diagnostic_ref': diagnostic,
            'response_ref': diagnostic if saved is not None else None,
            'http_status': snapshot.transport.get('status') if snapshot is not None else None}
        feedback = {**api_error_feedback(error), 'category': 'provider', 'code': code, 'phase': phase,
            'retry_after': getattr(error, 'retry_after', None), 'diagnostic_ref': diagnostic, 'cause': cause}
        if job is not None:
            feedback.update(job_ref=job['id'], submission_state=job['state'],
                remote_handle_known=job['remote_id'] is not None, collectable=False,
                status_addressable=job['remote_id'] is not None, submission_outcome=submission_outcome)
            if record_job_failure:
                with self.store.transaction():
                    self.store.db.execute('INSERT OR REPLACE INTO provider_job_failures VALUES(?,?)',
                                          (job['id'], canonical(cause)))
                    self.store.db.execute('UPDATE provider_jobs SET error_code=? WHERE id=?', (code, job['id']))
                    if job['remote_id'] is None and saved is not None:
                        self.store.db.execute('UPDATE provider_jobs SET submission=? WHERE id=?', (saved, job['id']))
        return _envelope(key, status='failed', feedback=feedback)

    async def execute(self, context, name, arguments, operation_key):
        arguments = plain(arguments)
        try:
            self.initialize(context)
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if name not in catalog:
                raise ValueError('api_operation_not_available')
            validate_schema(arguments, catalog[name]['input_schema'])
            self._selected(context, name, arguments, operation_key)
            row = self.store.db.execute('SELECT * FROM api_execution_actions WHERE operation_key=?',
                                      (operation_key,)).fetchone()
            if row is not None:
                if (row['run_id'] != self.run_id or row['episode_id'] != context.episode_id
                        or row['name'] != name or row['arguments'] != canonical(arguments)):
                    raise ValueError('api_operation_key_reused_for_different_work')
                if row['result'] is not None:
                    return json.loads(row['result'])
            elif self._completion(context) is not None:
                raise ValueError('api_assignment_already_completed')
        except (ValueError, ContractError, TypeError, KeyError) as error:
            return _envelope(operation_key, status='invalid', feedback={
                'category': 'arguments_or_reference', 'code': str(error)})
        fresh = row is None
        if fresh:
            with self.store.transaction():
                self.store.db.execute('INSERT INTO api_execution_actions VALUES(?,?,?,?,?,?,?,?)',
                    (operation_key, self.run_id, context.episode_id, name, canonical(arguments),
                     canonical({'started_at': _now(), 'assignment_sha256': digest(context.assignment),
                                'scope': plain(context.scope)}), None, None))
        job = None
        try:
            if name == 'api.hmmer.prepare':
                request, fasta_ref = self._prepare(context)
                result = _envelope(operation_key, result={'request': request, 'fasta_ref': fasta_ref})
            elif name == 'api.hmmer.databases':
                snapshot = await self._http(operation_key, self.clients.hmmer_databases, fresh=fresh)
                raw_ref = self.store.artifact(snapshot.content, snapshot.media_type)
                try:
                    native = json.loads(snapshot.content)
                    canonical(native)
                except (ValueError, TypeError, UnicodeError) as error:
                    raise AcquisitionError('provider_database_response_invalid', snapshot=snapshot,
                                           phase='database_response') from error
                result = _envelope(operation_key, result={'snapshot': json.loads(self._snapshot(snapshot)),
                    'raw_artifact_ref': raw_ref, 'provider_result': native})
            elif name == 'api.hmmer.submit':
                request, fasta_ref = self._prepare(context)
                old = self.store.db.execute('SELECT * FROM provider_jobs WHERE operation_key=?', (operation_key,)).fetchone()
                if old is None:
                    # A different selected submit may observe existing ambiguity,
                    # but may never commission a replacement physical search.
                    existing = self.store.db.execute('SELECT operation_key FROM api_execution_actions WHERE run_id=? '
                        "AND episode_id=? AND name='api.hmmer.submit' AND operation_key<>?",
                        (self.run_id, context.episode_id, operation_key)).fetchone()
                    if existing is not None:
                        job = self._job(context.episode_id)
                        raise AcquisitionError('api_original_submission_already_exists', job_ref=job['id'])
                    job_ref = identity('provider_job', {'operation_key': operation_key, 'request': request})
                    with self.store.transaction():
                        self.store.db.execute('INSERT INTO provider_jobs VALUES(?,?,?,?,?,?,?,?,?)',
                            (job_ref, operation_key, canonical(request), 'submitting', None, None, None, None, None))
                job = dict(self.store.db.execute('SELECT * FROM provider_jobs WHERE operation_key=?', (operation_key,)).fetchone())
                if job['remote_id'] is not None:
                    result = _envelope(operation_key, result={'job_ref': job['id'], 'execution_id': job['remote_id'],
                        'state': 'submitted' if job['state'] == 'accepted' else job['state'], 'request': request})
                else:
                    snapshot = await self._http(operation_key, self.clients.hmmer_submit,
                        self.store.get_artifact(fasta_ref).decode('utf-8'), fresh=fresh,
                        algorithm=request['algorithm'], database=request['database'], parameters=request['parameters'])
                    self._update_job(job['id'], submission=self._snapshot(snapshot))
                    try:
                        remote_id = str(uuid.UUID(json.loads(snapshot.content)['id']))
                    except (ValueError, TypeError, KeyError, AttributeError) as error:
                        raise AcquisitionError('provider_submission_response_invalid', snapshot=snapshot,
                                               phase='submission_response') from error
                    self._update_job(job['id'], remote_id=remote_id, state='accepted', error_code=None)
                    result = _envelope(operation_key, result={'job_ref': job['id'], 'execution_id': remote_id,
                        'state': 'submitted', 'request': request})
            elif name in {'api.hmmer.status', 'api.hmmer.check_handoff'}:
                job = self._job(context.episode_id)
                if job['remote_id'] is None:
                    raise AcquisitionError('remote_submission_uncertain', job_ref=job['id'], phase='recovery')
                request = json.loads(job['request'])
                snapshot = await self._http(operation_key, self.clients.hmmer_status, job['remote_id'], fresh=fresh)
                native, status, state = _native_status(snapshot, request, job['remote_id'])
                self._update_job(job['id'], latest_status=self._snapshot(snapshot), state=status, error_code=None)
                result = _envelope(operation_key, result={'job_ref': job['id'], 'execution_id': job['remote_id'],
                    'state': state, 'native': native, 'status_snapshot': json.loads(self._snapshot(snapshot))})
                if name == 'api.hmmer.check_handoff':
                    if state not in {'submitted', 'running', 'completed'}:
                        raise AcquisitionError('remote_search_failed' if state == 'failed' else
                            'unknown_remote_search_status', snapshot=snapshot, phase='status_response')
                    receipt = {'version': 'api_execution_receipt_v1', 'run_id': self.run_id,
                        'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                        'operation_key': operation_key, 'tool_name': name, 'arguments': arguments,
                        'job_ref': job['id'], 'execution_id': job['remote_id'],
                        'status_snapshot': json.loads(self._snapshot(snapshot)), 'state': state,
                        'validation_keys': ['usable_handoff'], 'finished_at': _now()}
                    handoff = self._publish_handoff(context, request, receipt)
                    result['record_refs'] = result['changed_record_refs'] = [handoff]
                    result['result'].update(handoff_ref=handoff, receipt=receipt)
            else:
                target = self.read_target(context.assignment['handoff_ref'], context.scope)
                body = self._read_handoff(context.assignment['handoff_ref'], context.scope)
                job = dict(self.store.db.execute('SELECT * FROM provider_jobs WHERE id=?', (body['job_ref'],)).fetchone())
                request = body['request']
                selector = plain(context.assignment['selector'])
                page, page_size = selector['page'], selector.get('page_size', request['page_size'])
                snapshot = await self._http(operation_key, self.clients.hmmer_result, target['execution_id'],
                    page=page, page_size=page_size, with_domains=True, fresh=fresh)
                try:
                    native = json.loads(snapshot.content)
                    canonical(native)
                    if not isinstance(native, dict) or not isinstance(native.get('status'), str):
                        raise ValueError('result_object_required')
                except (ValueError, TypeError, UnicodeError) as error:
                    raise AcquisitionError('provider_result_response_invalid', snapshot=snapshot, phase='result_response') from error
                if native['status'] != 'SUCCESS':
                    raise AcquisitionError('remote_search_failed' if native['status'] in {'FAILURE', 'FAILED', 'REVOKED'}
                        else 'remote_result_not_ready', snapshot=snapshot, phase='result_response')
                validate_remote_identity(native, request, target['execution_id'], result=True)
                details = json.loads(self._load_snapshot(canonical(body['receipt']['status_snapshot'])).content)
                snapshot = replace(snapshot, request={**request, 'job_id': target['execution_id'],
                    'page': page, 'page_size': page_size}, transport={**snapshot.transport,
                    'job_details': details, 'job_ref': body['job_ref']})
                result = self.tools.publish_hmmer_result(snapshot, plain(context.scope), operation_key+':publication')
                result['operation_ref'] = identity('api_operation', {'key': operation_key})
                result['result']['handoff_ref'] = target['handle']
                if result['status'] == 'completed':
                    result['result']['acquisition_receipt'] = {
                        'version': 'api_result_acquisition_receipt_v1', 'run_id': self.run_id,
                        'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                        'operation_key': operation_key, 'tool_name': name, 'arguments': arguments,
                        'handoff_ref': target['handle'], 'selector': selector,
                        'selector_sha256': digest(selector), 'source_ref': result['result']['source_ref'],
                        'snapshot_sha256': snapshot.sha256,
                        'record_refs': list(result['record_refs']), 'validation_keys': ['requested_result_page']}
                # Result custody belongs to this receiving episode. The original
                # launch state and its submitted/status history remain unchanged.
        except BaseException as error:
            interruption = error if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)) else None
            if name == 'api.hmmer.submit' and job is not None and job['remote_id'] is None:
                outcome = getattr(error, 'submission_outcome', None)
                self._update_job(job['id'], state='not_submitted' if outcome == 'not_sent' else 'submission_uncertain',
                                 error_code=getattr(error, 'code', 'remote_submission_uncertain'))
                job = dict(self.store.db.execute('SELECT * FROM provider_jobs WHERE id=?', (job['id'],)).fetchone())
                if not isinstance(error, (AcquisitionError, ValueError, ContractError)):
                    original_error = error
                    error = AcquisitionError('remote_submission_uncertain', phase='submission', submission_outcome='unknown')
                    error.__cause__ = original_error
            result = self._failure(operation_key, error, job=job, record_job_failure=name != 'api.hmmer.result' and
                (name != 'api.hmmer.submit' or job is None or job['operation_key'] == operation_key))
            self._save_action(operation_key, result)
            if interruption is not None:
                raise interruption
            return result
        return self._save_action(operation_key, result)

    def _publish_handoff(self, context, request, receipt):
        body = {'version': HANDOFF_VERSION, 'run_id': self.run_id, 'episode_id': context.episode_id,
            'assignment_sha256': digest(context.assignment), 'assignment': plain(context.assignment),
            'scope': plain(context.scope), 'request': request, 'receipt': receipt,
            'job_ref': receipt['job_ref'], 'execution_id': receipt['execution_id']}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(body), 'application/json')
            request_ref = self.store.artifact(canonical({'assignment': plain(context.assignment),
                'scope': plain(context.scope), 'request': request}), 'application/json')
            return self.store.put('source', {'provider': PROVIDER,
                'accession': 'api_handoff_'+digest([self.run_id, context.episode_id, receipt['operation_key']]),
                'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
                'version': HANDOFF_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')['id']

    def _artifact_json(self, reference):
        raw, record = self.store.get_artifact(reference), self.store.get(reference)
        value = json.loads(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if (raw != canonical(value).encode('utf-8') or record.get('sha256') != sha
                or reference != 'artifact_'+sha or record.get('size') != len(raw)):
            raise ValueError('api_handoff_artifact_identity_conflict')
        return value

    def _read_handoff(self, reference, scope):
        source = self.store.get(reference)
        if source.get('provider') != PROVIDER or source.get('record_type') != 'source' or source.get('origin') != 'tool':
            raise ValueError('not_an_api_execution_handoff')
        body = self._artifact_json(source['artifact_ref'])
        assignment = validate_api_assignment(body['assignment'])
        self._constraints(assignment)
        if (body['version'] != HANDOFF_VERSION or body['run_id'] != self.run_id
                or body['assignment_sha256'] != digest(assignment)
                or assignment['resource_id'] not in self.configuration):
            raise ValueError('api_handoff_assignment_identity_conflict')
        self.store.validate_scope(plain(scope))
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        manifest = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes '
            'WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if (manifest is None or manifest['assignment'] != canonical(assignment)
                or manifest['scope'] != canonical(body['scope'])):
            raise ValueError('api_handoff_original_assignment_conflict')
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_episodes'").fetchone():
            episode = self.store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (self.run_id, body['episode_id'])).fetchone()
            if episode is None:
                raise ValueError('api_handoff_original_episode_missing')
            message = json.loads(episode['request']).get('message', {})
            original = message.get('episode_assignment', message.get('assignment'))
            path = json.loads(episode['path'])
            if (canonical(original) != canonical(assignment) or canonical(message.get('scope')) != canonical(body['scope'])
                    or not path or path[-1][0] != 'launch_api'):
                raise ValueError('api_handoff_original_episode_conflict')
        receipt = body['receipt']
        if (receipt['version'] != 'api_execution_receipt_v1' or receipt['run_id'] != self.run_id
                or receipt['episode_id'] != body['episode_id'] or receipt['assignment_sha256'] != digest(assignment)
                or receipt['tool_name'] != 'api.hmmer.check_handoff' or receipt['arguments'] != {}
                or receipt['validation_keys'] != ['usable_handoff']
                or receipt['state'] not in {'submitted', 'running', 'completed'}
                or receipt['job_ref'] != body['job_ref'] or receipt['execution_id'] != body['execution_id']):
            raise ValueError('api_handoff_receipt_identity_conflict')
        original = self.store.db.execute('SELECT * FROM api_execution_actions WHERE operation_key=?',
                                        (receipt['operation_key'],)).fetchone()
        if (original is None or original['run_id'] != self.run_id or original['episode_id'] != body['episode_id']
                or original['name'] != receipt['tool_name'] or original['arguments'] != canonical(receipt['arguments'])
                or original['snapshot'] != canonical(receipt['status_snapshot'])):
            raise ValueError('api_handoff_selected_receipt_conflict')
        from .episode_bindings import BindingContext
        context = BindingContext(self.run_id, body['episode_id'], 'launch_api', (('launch_api', 'original'),),
            body['scope'], assignment, {})
        selected = self._selected(context, receipt['tool_name'], receipt['arguments'], receipt['operation_key'])
        if original['result'] is not None:
            result = json.loads(original['result'])
            if (result['status'] != 'completed' or reference not in result['record_refs']
                    or canonical(result['result'].get('receipt')) != canonical(receipt)):
                raise ValueError('api_handoff_saved_outcome_conflict')
        if selected['result'] is not None:
            result = json.loads(selected['result'])
            if (result.get('status') != 'completed' or reference not in result.get('record_refs', [])
                    or canonical(result.get('result', {}).get('receipt')) != canonical(receipt)):
                raise ValueError('api_handoff_runtime_outcome_conflict')
        job = self._job(body['episode_id'])
        prepared = self.store.db.execute('SELECT request,fasta_ref FROM api_execution_preparations WHERE run_id=? '
            'AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if (job['id'] != body['job_ref'] or job['remote_id'] != body['execution_id']
                or job['request'] != canonical(body['request']) or prepared is None
                or prepared['request'] != canonical(body['request'])):
            raise ValueError('api_handoff_physical_identity_conflict')
        request = body['request']
        from .episode_input_versions import pin_commission_inputs
        identities = pin_commission_inputs(self.store, [assignment['subject_ref']], resource_input_versions=[
            {'reference': assignment['subject_ref'], 'version': None, 'content_sha256': None}])
        if identities != request['input_identities']:
            raise ValueError('api_handoff_original_input_identity_conflict')
        fasta = self.store.get_artifact(prepared['fasta_ref'])
        from .domain import parse_sequences
        parsed = parse_sequences(fasta.decode('utf-8'), format='fasta', molecule='protein')
        if (len(parsed) != 1 or hashlib.sha256(fasta).hexdigest() != request['query_sha256']
                or hashlib.sha256(parsed[0].sequence.encode('ascii')).hexdigest() != request['sequence_sha256']
                or len(parsed[0].sequence) != request['query_length']
                or any(request[key] != assignment[key] for key in
                       ('subject_ref', 'algorithm', 'database', 'parameters', 'page_size', 'resource_id'))
                or request['assignment_sha256'] != digest(assignment)):
            raise ValueError('api_handoff_query_identity_conflict')
        snapshot = self._load_snapshot(canonical(receipt['status_snapshot']))
        _native, _status, state = _native_status(snapshot, request, body['execution_id'])
        if state != receipt['state']:
            raise ValueError('api_handoff_validation_conflict')
        expected = {'provider': PROVIDER, 'accession': 'api_handoff_'+digest([
            self.run_id, body['episode_id'], receipt['operation_key']]), 'uri': None,
            'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'],
            'request_ref': source['request_ref'], 'version': HANDOFF_VERSION, 'retrieved_at': receipt['finished_at']}
        payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
        if (canonical(payload) != canonical(expected) or reference != identity('source', {'origin': 'tool', 'record': expected})
                or self._artifact_json(source['request_ref']) != {'assignment': assignment, 'scope': body['scope'], 'request': request}):
            raise ValueError('api_handoff_source_identity_conflict')
        return body

    def scope(self, handoff_ref):
        source = self.store.get(handoff_ref)
        body = self._artifact_json(source['artifact_ref'])
        self._read_handoff(handoff_ref, body['scope'])
        return body['scope']

    def read_target(self, handoff_ref, scope):
        body = self._read_handoff(handoff_ref, scope)
        return validate_target({'version': 'execution_target_v1', 'handle': handoff_ref,
            'run_id': self.run_id, 'resource_id': body['assignment']['resource_id'], 'resource_kind': 'api',
            'execution_id': body['execution_id'], 'request_sha256': digest(body['assignment']),
            'origin_episode_id': body['episode_id'], 'assignment': body['assignment'], 'scope': body['scope']})

    def observe_target(self, target, *, operation_key):
        target = validate_target(plain(target))
        qualified = self.read_target(target['handle'], target['scope'])
        if target != qualified:
            raise ValueError('api_observation_target_identity_conflict')
        row = self.store.db.execute('SELECT * FROM api_execution_observations WHERE operation_key=?',
                                  (operation_key,)).fetchone()
        if row is not None:
            if row['target'] != canonical(target):
                raise ValueError('api_observation_operation_key_conflict')
            if row['observation'] is not None:
                return json.loads(row['observation'])
            observation = self._unknown_observation(target, 'api_observation_response_unknown')
            with self.store.transaction():
                self.store.db.execute('UPDATE api_execution_observations SET observation=? WHERE operation_key=?',
                    (canonical(observation), operation_key))
            return observation
        with self.store.transaction():
            self.store.db.execute('INSERT INTO api_execution_observations VALUES(?,?,NULL)',
                                  (operation_key, canonical(target)))
        body = self._read_handoff(target['handle'], target['scope'])
        try:
            snapshot = self.clients.hmmer_status(target['execution_id'])
            saved = self._snapshot(snapshot)
            native, native_state, state = _native_status(snapshot, body['request'], target['execution_id'])
            provenance = self.store.artifact(saved, 'application/json')
            observation = {'observed_at': snapshot.retrieved_at, 'state': state, 'returncode': None,
                'failure_code': 'remote_search_failed' if state == 'failed' else None,
                'result_available': state == 'completed', 'measurements': [], 'outputs': [], 'logs': [],
                'provenance_refs': [target['handle'], provenance],
                'native': {'service': 'ebi_hmmer', 'execution_id': target['execution_id'],
                    'native_state': native_state, 'status': native, 'snapshot': json.loads(saved)}}
        except Exception as error:
            from .api_error_feedback import api_error_feedback
            observation = self._unknown_observation(target, getattr(error, 'code', 'api_status_observation_failed'))
            observation['native']['error'] = api_error_feedback(error)
            if getattr(error, 'snapshot', None) is not None:
                saved = self._snapshot(error.snapshot)
                observation['provenance_refs'].append(self.store.artifact(saved, 'application/json'))
                observation['native']['snapshot'] = json.loads(saved)
        with self.store.transaction():
            self.store.db.execute('UPDATE api_execution_observations SET observation=? WHERE operation_key=?',
                                  (canonical(observation), operation_key))
        return observation

    def _unknown_observation(self, target, code):
        return {'observed_at': _now(), 'state': 'unknown', 'returncode': None, 'failure_code': code,
            'result_available': False, 'measurements': [], 'outputs': [], 'logs': [],
            'provenance_refs': [target['handle']], 'native': {'service': 'ebi_hmmer',
                'execution_id': target['execution_id'], 'failure_code': code}}

    def _own_results(self, context):
        return [json.loads(row['result']) for row in self.store.db.execute('SELECT result FROM api_execution_actions '
            'WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY rowid',
            (self.run_id, context.episode_id))]

    def facts(self, context, completion_snapshot):
        self.initialize(context)
        handoffs, results = [], []
        for outcome in self._own_results(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            for reference in outcome['record_refs']:
                record = self.store.get(reference)
                if record.get('provider') == PROVIDER:
                    self.read_target(reference, context.scope)
                    handoffs.append(reference)
                elif context.role == 'results':
                    results.append(reference)
        return {'execution_handoff_refs': list(dict.fromkeys(handoffs)),
            'execution_result_refs': list(dict.fromkeys(results)),
            'execution_completed': self._completion(context) is not None}

    def credit_view(self, context, receiver_selection):
        facts = self.facts(context, {})
        selection = plain(receiver_selection)
        if not {'known_record_refs', 'initial_known_record_refs'} <= set(selection):
            raise ValueError('api_credit_requires_received_record_selection')
        known, initial = set(selection['known_record_refs']), set(selection['initial_known_record_refs'])
        if not initial <= known:
            raise ValueError('api_credit_initial_references_must_be_known')
        def handoff_identity(reference):
            target = self.read_target(reference, context.scope)
            return target['resource_id'], target['execution_id']
        inherited, inherited_records = set(), set()
        for reference in initial:
            try:
                inherited.add(handoff_identity(reference))
            except (ValueError, ContractError, KeyError):
                pass
            try:
                inherited_records.add(self.result_identity(reference, context.scope))
            except (ValueError, ContractError, KeyError):
                pass
        acquired_records = {self.result_identity(reference, context.scope) for reference in
            set(facts['execution_result_refs']) & known}
        acquired = len(acquired_records-inherited_records)
        handoffs = {handoff_identity(reference) for reference in set(facts['execution_handoff_refs']) & known}
        count = len(handoffs-inherited)
        credit = self.handoff_unit*count + self.acquired_record_unit*acquired
        if not math.isfinite(credit):
            raise ValueError('finite_operational_credit_required')
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': count,
            'new_acquired_record_count': acquired, 'operational_credit_binding': {
                'version': VERSION, 'handoff_unit': self.handoff_unit,
                'acquired_record_unit': self.acquired_record_unit,
                'qualification': 'received_qualified_original_api_handoffs_and_own_canonical_result_records',
                'scientific_credit': False, 'monitoring_credit': False}}

    def result_identity(self, reference, scope):
        """Exact typed acquired content, independent of repeated custody timestamps.

        The source keeps every original byte and retrieval. Credit normalizes
        references only within that same original page publication, so another
        receipt of identical content cannot manufacture a new acquisition.
        """
        body = self.read_result(reference, scope)
        source = self.store.get(body['source_ref'])
        page = body['assignment']['selector']
        target = body['target']
        page_identity = digest({'resource_id': target['resource_id'], 'execution_id': target['execution_id'],
            'page': page['page'], 'page_size': page.get('page_size', target['assignment']['page_size']),
            'raw_sha256': hashlib.sha256(self.store.get_artifact(source['artifact_ref'])).hexdigest()})
        publication = set(body['record_refs'])
        cache = {body['source_ref']: {'record_type': 'source', 'page_content_identity': page_identity}}
        visiting = set()
        def record_value(ref):
            if ref in cache:
                return cache[ref]
            if ref in visiting:
                raise ValueError('cyclic_api_acquired_record_identity')
            visiting.add(ref)
            record = self.store.get(ref)
            value = {key: normalize(value) for key, value in record.items() if key not in {'id', 'origin'}}
            visiting.remove(ref)
            cache[ref] = value
            return value
        def normalize(value):
            if isinstance(value, str) and value in publication:
                return record_value(value)
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            return value
        return digest({'page_content_identity': page_identity, 'record': record_value(reference)})

    def read_result(self, reference, scope):
        """Qualify actual acquired records for their receiving parent, without I/O."""
        self.store.get(reference)
        rows = self.store.db.execute("SELECT action.* FROM api_execution_actions action, "
            "json_each(action.result,'$.record_refs') returned WHERE action.run_id=? "
            "AND action.name='api.hmmer.result' AND returned.value=? ORDER BY action.rowid",
            (self.run_id, reference)).fetchall()
        for row in rows:
            outcome = json.loads(row['result'])
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            manifest = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes '
                'WHERE run_id=? AND episode_id=?', (self.run_id, row['episode_id'])).fetchone()
            assignment, original_scope = json.loads(manifest['assignment']), json.loads(manifest['scope'])
            self.store.validate_scope(original_scope, parent_scope=plain(scope))
            if assignment.get('version') != 'execution_results_assignment_v1':
                raise ValueError('api_result_original_assignment_conflict')
            target = self.read_target(assignment['handoff_ref'], original_scope)
            selector = assignment['selector']
            from .episode_bindings import BindingContext
            original_context = BindingContext(self.run_id, row['episode_id'], 'results', (('results', 'original'),),
                original_scope, assignment, {})
            selected = self._selected(original_context, row['name'], json.loads(row['arguments']), row['operation_key'])
            if selected['result'] is not None:
                actual = json.loads(selected['result'])
                if (actual.get('status') != outcome['status'] or actual.get('record_refs') != outcome['record_refs']
                        or canonical(actual.get('result')) != canonical(outcome.get('result'))):
                    raise ValueError('api_result_runtime_outcome_conflict')
            episode = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (self.run_id, row['episode_id'])).fetchone()
            message = json.loads(episode['request']).get('message', {}) if episode is not None else {}
            if (canonical(message.get('episode_assignment', message.get('assignment'))) != canonical(assignment)
                    or canonical(message.get('scope')) != canonical(original_scope)):
                raise ValueError('api_result_original_episode_conflict')
            publication = self.store.db.execute('SELECT * FROM tool_operations WHERE operation_key=?',
                (row['operation_key']+':publication',)).fetchone()
            if publication is None or publication['name'] != 'internal.hmmer.result_publication':
                raise ValueError('api_result_original_publication_missing')
            published = json.loads(publication['result'])
            if (published['record_refs'] != outcome['record_refs'] or published['status'] != outcome['status']
                    or publication['scope'] != canonical(original_scope)):
                raise ValueError('api_result_original_publication_conflict')
            source_ref = published['result']['source_ref']
            source = self.store.get(source_ref)
            request = self._artifact_json(source['request_ref'])['request']
            snapshot = self._load_snapshot(row['snapshot'])
            body = self._read_handoff(target['handle'], original_scope)
            if (self.store.get_artifact(source['artifact_ref']) != snapshot.content
                    or request != {**body['request'], 'job_id': target['execution_id'], 'page': selector['page'],
                        'page_size': selector.get('page_size', target['assignment']['page_size'])}):
                raise ValueError('api_result_original_request_conflict')
            validate_remote_identity(json.loads(snapshot.content), body['request'], target['execution_id'], result=True)
            return {'version': 'api_acquired_result_information_v1', 'reference': reference,
                'run_id': self.run_id, 'episode_id': row['episode_id'], 'scope': original_scope,
                'assignment': assignment, 'target': target, 'source_ref': source_ref,
                'record_refs': list(outcome['record_refs']), 'status': outcome['status']}
        raise ValueError('not_an_api_acquired_result')

    def decision_context(self, context, current_view=None):
        self.initialize(context)
        if context.role == 'results':
            return {'api_execution_assignment': plain(context.assignment),
                'api_execution_target': self.read_target(context.assignment['handoff_ref'], context.scope),
                'api_execution_completion': self._completion(context)}
        prepared = self.store.db.execute('SELECT request FROM api_execution_preparations WHERE run_id=? '
            'AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        try:
            job = self.tools.remote_searches.describe(self._job(context.episode_id)['id'])
        except ValueError:
            job = None
        return {'api_execution_assignment': plain(context.assignment),
            'api_execution_prepared_request': json.loads(prepared['request']) if prepared else None,
            'api_execution_job': job, 'api_execution_completion': self._completion(context)}

    def resolve(self, context, reference, namespace):
        if context.run_id != self.run_id:
            return False
        if namespace not in {None, 'source', 'execution_handoff', 'execution_result'}:
            return False
        try:
            if namespace != 'execution_result':
                self.read_target(reference, context.scope)
                return True
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            pass
        if namespace in {None, 'source', 'execution_result'}:
            try:
                self.read_result(reference, context.scope)
                return namespace != 'source' or self.store.get(reference).get('record_type') == 'source'
            except (ValueError, ContractError, KeyError, OSError, TypeError):
                return False
        return False

    def validate_report(self, context, form, schema):
        validate_form(form, schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        facts = self.facts(context, {})
        for name, node in schema.get('properties', {}).items():
            if node.get('x-source') in facts and form[name] != facts[node['x-source']]:
                raise ValueError('api_report_disagrees_with_recorded_facts')

    def _completion(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_completion_run_identity_conflict')
        if context.role == 'results':
            return self._results_completion(context)
        if context.role != 'launch_api':
            return None
        for outcome in reversed(self._own_results(context)):
            receipt = (outcome.get('result') or {}).get('receipt')
            if outcome['status'] == 'completed' and receipt is not None:
                reference = outcome['result']['handoff_ref']
                self.read_target(reference, context.scope)
                return {'version': 'practical_completion_v1', 'run_id': self.run_id,
                    'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                    'endpoint': 'usable_handoff', 'operation_key': receipt['operation_key'],
                    'receipt_sha256': digest(receipt), 'validation_keys': ['usable_handoff']}
        return None

    def _results_completion(self, context):
        assignment = plain(context.assignment)
        if assignment.get('version') != 'execution_results_assignment_v1':
            return None
        target = self.read_target(assignment['handoff_ref'], context.scope)
        for row in self.store.db.execute("SELECT * FROM api_execution_actions WHERE run_id=? AND episode_id=? "
                "AND name='api.hmmer.result' AND result IS NOT NULL ORDER BY rowid DESC",
                (self.run_id, context.episode_id)):
            outcome = json.loads(row['result'])
            if outcome['status'] != 'completed':
                continue
            receipt = (outcome.get('result') or {}).get('acquisition_receipt')
            if receipt is None:
                continue
            if (receipt['version'] != 'api_result_acquisition_receipt_v1'
                    or receipt['run_id'] != self.run_id or receipt['episode_id'] != context.episode_id
                    or receipt['tool_name'] != 'api.hmmer.result' or receipt['arguments'] != {}
                    or receipt['validation_keys'] != ['requested_result_page']
                    or receipt['assignment_sha256'] != digest(assignment)
                    or receipt['selector'] != assignment['selector']
                    or receipt['selector_sha256'] != digest(assignment['selector'])
                    or receipt['handoff_ref'] != target['handle']
                    or receipt['operation_key'] != row['operation_key']
                    or receipt['record_refs'] != outcome['record_refs']
                    or receipt['source_ref'] != outcome['result']['source_ref']):
                raise ValueError('api_result_completion_identity_conflict')
            selected = self._selected(context, row['name'], json.loads(row['arguments']), row['operation_key'])
            if selected['result'] is not None:
                actual = json.loads(selected['result'])
                if (actual.get('status') != 'completed' or actual.get('record_refs') != outcome['record_refs']
                        or canonical(actual.get('result')) != canonical(outcome.get('result'))):
                    raise ValueError('api_result_completion_runtime_outcome_conflict')
            original = self._load_snapshot(row['snapshot'])
            if original.sha256 != receipt['snapshot_sha256']:
                raise ValueError('api_result_completion_source_conflict')
            source = self.store.get(receipt['source_ref'])
            request = self._artifact_json(source['request_ref'])['request']
            selector = assignment['selector']
            if (self.store.get_artifact(source['artifact_ref']) != original.content
                    or request['job_id'] != target['execution_id']
                    or request['page'] != selector['page']
                    or request['page_size'] != selector.get('page_size', target['assignment']['page_size'])):
                raise ValueError('api_result_completion_requested_page_conflict')
            return {'version': 'practical_completion_v1', 'run_id': self.run_id,
                'episode_id': context.episode_id, 'assignment_sha256': digest(assignment),
                'endpoint': 'usable_handoff', 'operation_key': row['operation_key'],
                'receipt_sha256': digest(receipt), 'validation_keys': ['requested_result_page']}
        return None

    def completion_for_action(self, context, key):
        proof = self._completion(context)
        return proof if proof is not None and proof['operation_key'] == key else None

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
            actual = self._completion(context)
            return actual is not None and proof == actual
        except (ValueError, ContractError, TypeError, KeyError, OSError):
            return False


__all__ = ['HMMERAPIExecution', 'PROVIDER', 'VERSION']
