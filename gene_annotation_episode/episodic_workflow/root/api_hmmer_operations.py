"""Original selected HMMER operations and exact response/intent persistence."""
from __future__ import annotations
import asyncio
from dataclasses import asdict, replace
import hashlib
import json
import uuid
from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.domain import ContractError, identity, validate_schema
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.library.provider_jobs import HMMER_IDENTITY_VERSION, validate_remote_identity
from gene_annotation_episode.episodic_workflow.root.api_hmmer_protocol import _now, _envelope, _native_status


class HMMERAPIOperations:
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
        from gene_annotation_episode.domain import parse_sequences
        fasta = f'>{subject["id"]}\n{sequence}'
        parsed = parse_sequences(fasta, format='fasta', molecule='protein')
        if len(parsed) != 1:
            raise ValueError('single_query_required')
        from gene_annotation_episode.episodic_workflow.root.episode_input_versions import pin_commission_inputs
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
        from gene_annotation_episode.api_error_feedback import api_error_feedback
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

