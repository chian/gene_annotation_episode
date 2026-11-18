from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_access import HMMERRecordAccess

class HMMERJobService(HMMERRecordAccess):

    def __init__(self, store, *, run_id, directory, configuration, tool_registry, handoff_unit, acquired_record_unit):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_execution_run_required')
        for value in (handoff_unit, acquired_record_unit):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        self.store, self.run_id, self.directory = (store, run_id, Path(directory))
        self.configuration = json.loads(canonical(configuration))
        if not isinstance(self.configuration, dict) or not self.configuration or any((not isinstance(key, str) or not key or (not isinstance(value, dict)) or (value.get('kind') != 'hmmer_api') or set(value) - {'kind', 'service'} or (value.get('service', 'ebi_hmmer') != 'ebi_hmmer') for key, value in self.configuration.items())):
            raise ValueError('explicit_api_resources_required')
        if tool_registry.store is not store or not callable(getattr(tool_registry, 'publish_hmmer_result', None)):
            raise ValueError('actual_tool_registry_required_for_api_execution')
        self.tools, self.clients = (tool_registry, tool_registry.clients)
        self.handoff_unit, self.acquired_record_unit = (handoff_unit, acquired_record_unit)
        store.db.executescript('\n            CREATE TABLE IF NOT EXISTS api_execution_episodes (\n                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, assignment TEXT NOT NULL,\n                scope TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));\n            CREATE TABLE IF NOT EXISTS api_execution_preparations (\n                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, request TEXT NOT NULL,\n                fasta_ref TEXT NOT NULL, PRIMARY KEY(run_id,episode_id));\n            CREATE TABLE IF NOT EXISTS api_execution_actions (\n                operation_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, episode_id TEXT NOT NULL,\n                name TEXT NOT NULL, arguments TEXT NOT NULL, intent TEXT NOT NULL,\n                snapshot TEXT, result TEXT);\n            CREATE TABLE IF NOT EXISTS api_execution_observations (\n                operation_key TEXT PRIMARY KEY, target TEXT NOT NULL, observation TEXT);\n        ')

    def _assignment(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
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
        assignment, scope = (canonical(context.assignment), canonical(context.scope))
        with self.store.transaction():
            row = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
            if row is not None:
                if row['assignment'] != assignment or row['scope'] != scope:
                    raise ValueError('api_original_assignment_conflict')
            else:
                self.store.db.execute('INSERT INTO api_execution_episodes VALUES(?,?,?,?)', (self.run_id, context.episode_id, assignment, scope))
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

    def catalog(self, context):
        self._assignment(context)
        return hmmer_operation_catalog('launch_api')

    def _prepare(self, context):
        assignment = self._assignment(context)
        row = self.store.db.execute('SELECT request,fasta_ref FROM api_execution_preparations WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if row:
            return (json.loads(row['request']), row['fasta_ref'])
        subject = self.tools._check_sequence_operand(assignment['subject_ref'], plain(context.scope))
        sequence = self.tools._sequence(subject['id'], molecule_model='protein')
        from gene_annotation_episode.episodic_workflow.root.a104.domain import parse_sequences
        fasta = f">{subject['id']}\n{sequence}"
        parsed = parse_sequences(fasta, format='fasta', molecule='protein')
        if len(parsed) != 1:
            raise ValueError('single_query_required')
        from gene_annotation_episode.episodic_workflow.root.a104.episode_input_versions import pin_commission_inputs
        input_identities = pin_commission_inputs(self.store, [subject['id']], resource_input_versions=[{'reference': subject['id'], 'version': None, 'content_sha256': None}])
        request = {'input_identities': input_identities, 'subject_ref': subject['id'], 'algorithm': assignment['algorithm'], 'database': assignment['database'], 'parameters': assignment['parameters'], 'page_size': assignment['page_size'], 'resource_id': assignment['resource_id'], 'assignment_sha256': digest(assignment), 'identity_version': HMMER_IDENTITY_VERSION, 'query_sha256': hashlib.sha256(fasta.encode('utf-8')).hexdigest(), 'query_sha256_representation': 'submitted_fasta_utf8_bytes', 'sequence_sha256': hashlib.sha256(parsed[0].sequence.encode('ascii')).hexdigest(), 'sequence_sha256_representation': 'single_fasta_sequence_uppercase_whitespace_removed_ascii', 'query_length': len(parsed[0].sequence), 'molecule_model': 'protein', 'molecule_assignment': 'not_performed'}
        with self.store.transaction():
            fasta_ref = self.store.artifact(fasta, 'text/x-fasta')
            self.store.db.execute('INSERT INTO api_execution_preparations VALUES(?,?,?,?)', (self.run_id, context.episode_id, canonical(request), fasta_ref))
        return (request, fasta_ref)

    def _update_job(self, job_ref, **values):
        with self.store.transaction():
            self.store.db.execute('UPDATE provider_jobs SET ' + ','.join((key + '=?' for key in values)) + ' WHERE id=?', [*values.values(), job_ref])
            if values.get('error_code', 'not_supplied') is None:
                self.store.db.execute('DELETE FROM provider_job_failures WHERE job_ref=?', (job_ref,))

    def _save_action(self, key, result):
        with self.store.transaction():
            self.store.db.execute('UPDATE api_execution_actions SET result=? WHERE operation_key=?', (canonical(result), key))
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
                self.store.db.execute('UPDATE api_execution_actions SET snapshot=? WHERE operation_key=?', (self._snapshot(error.snapshot), key))
            raise
        with self.store.transaction():
            self.store.db.execute('UPDATE api_execution_actions SET snapshot=? WHERE operation_key=?', (self._snapshot(snapshot), key))
        return snapshot

    def _failure(self, key, error, *, job=None, record_job_failure=True):
        from gene_annotation_episode.episodic_workflow.root.a104.api_error_feedback import api_error_feedback
        snapshot = getattr(error, 'snapshot', None)
        saved = self._snapshot(snapshot) if snapshot is not None else None
        cause_error = error.__cause__ or error
        diagnostic = self.store.artifact(saved or canonical({'representation': 'local_exception', 'exception_type': type(cause_error).__name__, 'message': str(cause_error), 'details': getattr(error, 'diagnostic', None)}), 'application/json')
        code = error.code if isinstance(error, AcquisitionError) else str(error) if isinstance(error, (ValueError, ContractError)) else 'api_execution_failed'
        phase = getattr(error, 'phase', None)
        client_phase = phase
        if job is not None:
            phase = 'submission' if job['remote_id'] is None else 'result' if not record_job_failure else 'status'
        submission_outcome = getattr(error, 'submission_outcome', None) or ('remote_handle_returned' if job is not None and job['remote_id'] is not None else 'unknown')
        cause = {'code': code, 'exception_type': type(cause_error).__name__, 'phase': phase, 'client_phase': client_phase, 'submission_outcome': submission_outcome, 'retry_after': getattr(error, 'retry_after', None), 'diagnostic_ref': diagnostic, 'response_ref': diagnostic if saved is not None else None, 'http_status': snapshot.transport.get('status') if snapshot is not None else None}
        feedback = {**api_error_feedback(error), 'category': 'provider', 'code': code, 'phase': phase, 'retry_after': getattr(error, 'retry_after', None), 'diagnostic_ref': diagnostic, 'cause': cause}
        if job is not None:
            feedback.update(job_ref=job['id'], submission_state=job['state'], remote_handle_known=job['remote_id'] is not None, collectable=False, status_addressable=job['remote_id'] is not None, submission_outcome=submission_outcome)
            if record_job_failure:
                with self.store.transaction():
                    self.store.db.execute('INSERT OR REPLACE INTO provider_job_failures VALUES(?,?)', (job['id'], canonical(cause)))
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
            row = self.store.db.execute('SELECT * FROM api_execution_actions WHERE operation_key=?', (operation_key,)).fetchone()
            if row is not None:
                if row['run_id'] != self.run_id or row['episode_id'] != context.episode_id or row['name'] != name or (row['arguments'] != canonical(arguments)):
                    raise ValueError('api_operation_key_reused_for_different_work')
                if row['result'] is not None:
                    return json.loads(row['result'])
            elif self._completion(context) is not None:
                raise ValueError('api_assignment_already_completed')
        except (ValueError, ContractError, TypeError, KeyError) as error:
            return _envelope(operation_key, status='invalid', feedback={'category': 'arguments_or_reference', 'code': str(error)})
        fresh = row is None
        if fresh:
            with self.store.transaction():
                self.store.db.execute('INSERT INTO api_execution_actions VALUES(?,?,?,?,?,?,?,?)', (operation_key, self.run_id, context.episode_id, name, canonical(arguments), canonical({'started_at': _now(), 'assignment_sha256': digest(context.assignment), 'scope': plain(context.scope)}), None, None))
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
                    raise AcquisitionError('provider_database_response_invalid', snapshot=snapshot, phase='database_response') from error
                result = _envelope(operation_key, result={'snapshot': json.loads(self._snapshot(snapshot)), 'raw_artifact_ref': raw_ref, 'provider_result': native})
            elif name == 'api.hmmer.submit':
                request, fasta_ref = self._prepare(context)
                old = self.store.db.execute('SELECT * FROM provider_jobs WHERE operation_key=?', (operation_key,)).fetchone()
                if old is None:
                    existing = self.store.db.execute("SELECT operation_key FROM api_execution_actions WHERE run_id=? AND episode_id=? AND name='api.hmmer.submit' AND operation_key<>?", (self.run_id, context.episode_id, operation_key)).fetchone()
                    if existing is not None:
                        job = self._job(context.episode_id)
                        raise AcquisitionError('api_original_submission_already_exists', job_ref=job['id'])
                    job_ref = identity('provider_job', {'operation_key': operation_key, 'request': request})
                    with self.store.transaction():
                        self.store.db.execute('INSERT INTO provider_jobs VALUES(?,?,?,?,?,?,?,?,?)', (job_ref, operation_key, canonical(request), 'submitting', None, None, None, None, None))
                job = dict(self.store.db.execute('SELECT * FROM provider_jobs WHERE operation_key=?', (operation_key,)).fetchone())
                if job['remote_id'] is not None:
                    result = _envelope(operation_key, result={'job_ref': job['id'], 'execution_id': job['remote_id'], 'state': 'submitted' if job['state'] == 'accepted' else job['state'], 'request': request})
                else:
                    snapshot = await self._http(operation_key, self.clients.hmmer_submit, self.store.get_artifact(fasta_ref).decode('utf-8'), fresh=fresh, algorithm=request['algorithm'], database=request['database'], parameters=request['parameters'])
                    self._update_job(job['id'], submission=self._snapshot(snapshot))
                    try:
                        remote_id = str(uuid.UUID(json.loads(snapshot.content)['id']))
                    except (ValueError, TypeError, KeyError, AttributeError) as error:
                        raise AcquisitionError('provider_submission_response_invalid', snapshot=snapshot, phase='submission_response') from error
                    self._update_job(job['id'], remote_id=remote_id, state='accepted', error_code=None)
                    result = _envelope(operation_key, result={'job_ref': job['id'], 'execution_id': remote_id, 'state': 'submitted', 'request': request})
            elif name in {'api.hmmer.status', 'api.hmmer.check_handoff'}:
                job = self._job(context.episode_id)
                if job['remote_id'] is None:
                    raise AcquisitionError('remote_submission_uncertain', job_ref=job['id'], phase='recovery')
                request = json.loads(job['request'])
                snapshot = await self._http(operation_key, self.clients.hmmer_status, job['remote_id'], fresh=fresh)
                native, status, state = _native_status(snapshot, request, job['remote_id'])
                self._update_job(job['id'], latest_status=self._snapshot(snapshot), state=status, error_code=None)
                result = _envelope(operation_key, result={'job_ref': job['id'], 'execution_id': job['remote_id'], 'state': state, 'native': native, 'status_snapshot': json.loads(self._snapshot(snapshot))})
                if name == 'api.hmmer.check_handoff':
                    if state not in {'submitted', 'running', 'completed'}:
                        raise AcquisitionError('remote_search_failed' if state == 'failed' else 'unknown_remote_search_status', snapshot=snapshot, phase='status_response')
                    receipt = {'version': 'api_execution_receipt_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'operation_key': operation_key, 'tool_name': name, 'arguments': arguments, 'job_ref': job['id'], 'execution_id': job['remote_id'], 'status_snapshot': json.loads(self._snapshot(snapshot)), 'state': state, 'validation_keys': ['usable_handoff'], 'finished_at': _now()}
                    handoff = self._publish_handoff(context, request, receipt)
                    result['record_refs'] = result['changed_record_refs'] = [handoff]
                    result['result'].update(handoff_ref=handoff, receipt=receipt)
        except BaseException as error:
            interruption = error if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)) else None
            if name == 'api.hmmer.submit' and job is not None and (job['remote_id'] is None):
                outcome = getattr(error, 'submission_outcome', None)
                self._update_job(job['id'], state='not_submitted' if outcome == 'not_sent' else 'submission_uncertain', error_code=getattr(error, 'code', 'remote_submission_uncertain'))
                job = dict(self.store.db.execute('SELECT * FROM provider_jobs WHERE id=?', (job['id'],)).fetchone())
                if not isinstance(error, (AcquisitionError, ValueError, ContractError)):
                    original_error = error
                    error = AcquisitionError('remote_submission_uncertain', phase='submission', submission_outcome='unknown')
                    error.__cause__ = original_error
            result = self._failure(operation_key, error, job=job, record_job_failure=name != 'api.hmmer.result' and (name != 'api.hmmer.submit' or job is None or job['operation_key'] == operation_key))
            self._save_action(operation_key, result)
            if interruption is not None:
                raise interruption
            return result
        return self._save_action(operation_key, result)

    def _publish_handoff(self, context, request, receipt):
        body = {'version': HANDOFF_VERSION, 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'assignment': plain(context.assignment), 'scope': plain(context.scope), 'request': request, 'receipt': receipt, 'job_ref': receipt['job_ref'], 'execution_id': receipt['execution_id']}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(body), 'application/json')
            request_ref = self.store.artifact(canonical({'assignment': plain(context.assignment), 'scope': plain(context.scope), 'request': request}), 'application/json')
            return self.store.put('source', {'provider': PROVIDER, 'accession': 'api_handoff_' + digest([self.run_id, context.episode_id, receipt['operation_key']]), 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref, 'version': HANDOFF_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')['id']

    def facts(self, context, completion_snapshot):
        self.initialize(context)
        handoffs, results = ([], [])
        for outcome in self._own_results(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            for reference in outcome['record_refs']:
                record = self.store.get(reference)
                if record.get('provider') == PROVIDER:
                    self.read_target(reference, context.scope)
                    handoffs.append(reference)
        return {'execution_handoff_refs': list(dict.fromkeys(handoffs)), 'execution_result_refs': list(dict.fromkeys(results)), 'execution_completed': self._completion(context) is not None}

    def credit_view(self, context, receiver_selection):
        facts = self.facts(context, {})
        selection = plain(receiver_selection)
        if not {'known_record_refs', 'initial_known_record_refs'} <= set(selection):
            raise ValueError('api_credit_requires_received_record_selection')
        known, initial = (set(selection['known_record_refs']), set(selection['initial_known_record_refs']))
        if not initial <= known:
            raise ValueError('api_credit_initial_references_must_be_known')

        def handoff_identity(reference):
            target = self.read_target(reference, context.scope)
            return (target['resource_id'], target['execution_id'])
        inherited, inherited_records = (set(), set())
        for reference in initial:
            try:
                inherited.add(handoff_identity(reference))
            except (ValueError, ContractError, KeyError):
                pass
            try:
                inherited_records.add(self.result_identity(reference, context.scope))
            except (ValueError, ContractError, KeyError):
                pass
        acquired_records = {self.result_identity(reference, context.scope) for reference in set(facts['execution_result_refs']) & known}
        acquired = len(acquired_records - inherited_records)
        handoffs = {handoff_identity(reference) for reference in set(facts['execution_handoff_refs']) & known}
        count = len(handoffs - inherited)
        credit = self.handoff_unit * count + self.acquired_record_unit * acquired
        if not math.isfinite(credit):
            raise ValueError('finite_operational_credit_required')
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': count, 'new_acquired_record_count': acquired, 'operational_credit_binding': {'version': VERSION, 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'qualification': 'received_qualified_original_api_handoffs_and_own_canonical_result_records', 'scientific_credit': False, 'monitoring_credit': False}}

    def decision_context(self, context, current_view=None):
        self.initialize(context)
        prepared = self.store.db.execute('SELECT request FROM api_execution_preparations WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        try:
            job = self.tools.remote_searches.describe(self._job(context.episode_id)['id'])
        except ValueError:
            job = None
        return {'api_execution_assignment': plain(context.assignment), 'api_execution_prepared_request': json.loads(prepared['request']) if prepared else None, 'api_execution_job': job, 'api_execution_completion': self._completion(context)}

    def validate_report(self, context, form, schema):
        validate_form(form, schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        facts = self.facts(context, {})
        for name, node in schema.get('properties', {}).items():
            if node.get('x-source') in facts and form[name] != facts[node['x-source']]:
                raise ValueError('api_report_disagrees_with_recorded_facts')

    def _completion(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_completion_run_identity_conflict')
        for outcome in reversed(self._own_results(context)):
            receipt = (outcome.get('result') or {}).get('receipt')
            if outcome['status'] == 'completed' and receipt is not None:
                reference = outcome['result']['handoff_ref']
                self.read_target(reference, context.scope)
                return {'version': 'practical_completion_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'usable_handoff', 'operation_key': receipt['operation_key'], 'receipt_sha256': digest(receipt), 'validation_keys': ['usable_handoff']}
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
