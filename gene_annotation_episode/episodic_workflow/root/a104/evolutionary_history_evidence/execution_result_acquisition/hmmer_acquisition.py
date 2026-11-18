from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_access import HMMERRecordAccess

class HMMERResultAcquisition(HMMERRecordAccess):

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
        if context.role != 'results':
            raise ValueError('api_execution_role_required')
        raw = plain(context.assignment)
        if set(raw) != {'version', 'handoff_ref', 'selector'} or raw['version'] != 'execution_results_assignment_v1' or (not isinstance(raw['selector'], dict)):
            raise ValueError('invalid_api_results_assignment')
        selector = raw['selector']
        if set(selector) - {'page', 'page_size'} or 'page' not in selector or any((type(value) is not int or value <= 0 for value in selector.values())):
            raise ValueError('invalid_api_results_selector')
        assignment = self.read_target(raw['handoff_ref'], context.scope)['assignment']
        if 'page_size' in assignment['constraints'] and selector.get('page_size', assignment['page_size']) != assignment['constraints']['page_size']:
            raise ValueError('api_result_page_size_constraint_conflict')
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
        return hmmer_operation_catalog('results')

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
            target = self.read_target(context.assignment['handoff_ref'], context.scope)
            body = self._read_handoff(context.assignment['handoff_ref'], context.scope)
            job = dict(self.store.db.execute('SELECT * FROM provider_jobs WHERE id=?', (body['job_ref'],)).fetchone())
            request = body['request']
            selector = plain(context.assignment['selector'])
            page, page_size = (selector['page'], selector.get('page_size', request['page_size']))
            snapshot = await self._http(operation_key, self.clients.hmmer_result, target['execution_id'], page=page, page_size=page_size, with_domains=True, fresh=fresh)
            try:
                native = json.loads(snapshot.content)
                canonical(native)
                if not isinstance(native, dict) or not isinstance(native.get('status'), str):
                    raise ValueError('result_object_required')
            except (ValueError, TypeError, UnicodeError) as error:
                raise AcquisitionError('provider_result_response_invalid', snapshot=snapshot, phase='result_response') from error
            if native['status'] != 'SUCCESS':
                raise AcquisitionError('remote_search_failed' if native['status'] in {'FAILURE', 'FAILED', 'REVOKED'} else 'remote_result_not_ready', snapshot=snapshot, phase='result_response')
            validate_remote_identity(native, request, target['execution_id'], result=True)
            details = json.loads(self._load_snapshot(canonical(body['receipt']['status_snapshot'])).content)
            snapshot = replace(snapshot, request={**request, 'job_id': target['execution_id'], 'page': page, 'page_size': page_size}, transport={**snapshot.transport, 'job_details': details, 'job_ref': body['job_ref']})
            result = self.tools.publish_hmmer_result(snapshot, plain(context.scope), operation_key + ':publication')
            result['operation_ref'] = identity('api_operation', {'key': operation_key})
            result['result']['handoff_ref'] = target['handle']
            if result['status'] == 'completed':
                result['result']['acquisition_receipt'] = {'version': 'api_result_acquisition_receipt_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'operation_key': operation_key, 'tool_name': name, 'arguments': arguments, 'handoff_ref': target['handle'], 'selector': selector, 'selector_sha256': digest(selector), 'source_ref': result['result']['source_ref'], 'snapshot_sha256': snapshot.sha256, 'record_refs': list(result['record_refs']), 'validation_keys': ['requested_result_page']}
        except BaseException as error:
            interruption = error if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)) else None
            result = self._failure(operation_key, error, job=job, record_job_failure=False)
            self._save_action(operation_key, result)
            if interruption is not None:
                raise interruption
            return result
        return self._save_action(operation_key, result)

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
                else:
                    results.append(reference)
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
        return {'api_execution_assignment': plain(context.assignment), 'api_execution_target': self.read_target(context.assignment['handoff_ref'], context.scope), 'api_execution_completion': self._completion(context)}

    def validate_report(self, context, form, schema):
        validate_form(form, schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        facts = self.facts(context, {})
        for name, node in schema.get('properties', {}).items():
            if node.get('x-source') in facts and form[name] != facts[node['x-source']]:
                raise ValueError('api_report_disagrees_with_recorded_facts')

    def _completion(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_completion_run_identity_conflict')
        return self._results_completion(context)

    def _results_completion(self, context):
        assignment = plain(context.assignment)
        if assignment.get('version') != 'execution_results_assignment_v1':
            return None
        target = self.read_target(assignment['handoff_ref'], context.scope)
        for row in self.store.db.execute("SELECT * FROM api_execution_actions WHERE run_id=? AND episode_id=? AND name='api.hmmer.result' AND result IS NOT NULL ORDER BY rowid DESC", (self.run_id, context.episode_id)):
            outcome = json.loads(row['result'])
            if outcome['status'] != 'completed':
                continue
            receipt = (outcome.get('result') or {}).get('acquisition_receipt')
            if receipt is None:
                continue
            if receipt['version'] != 'api_result_acquisition_receipt_v1' or receipt['run_id'] != self.run_id or receipt['episode_id'] != context.episode_id or (receipt['tool_name'] != 'api.hmmer.result') or (receipt['arguments'] != {}) or (receipt['validation_keys'] != ['requested_result_page']) or (receipt['assignment_sha256'] != digest(assignment)) or (receipt['selector'] != assignment['selector']) or (receipt['selector_sha256'] != digest(assignment['selector'])) or (receipt['handoff_ref'] != target['handle']) or (receipt['operation_key'] != row['operation_key']) or (receipt['record_refs'] != outcome['record_refs']) or (receipt['source_ref'] != outcome['result']['source_ref']):
                raise ValueError('api_result_completion_identity_conflict')
            selected = self._selected(context, row['name'], json.loads(row['arguments']), row['operation_key'])
            if selected['result'] is not None:
                actual = json.loads(selected['result'])
                if actual.get('status') != 'completed' or actual.get('record_refs') != outcome['record_refs'] or canonical(actual.get('result')) != canonical(outcome.get('result')):
                    raise ValueError('api_result_completion_runtime_outcome_conflict')
            original = self._load_snapshot(row['snapshot'])
            if original.sha256 != receipt['snapshot_sha256']:
                raise ValueError('api_result_completion_source_conflict')
            source = self.store.get(receipt['source_ref'])
            request = self._artifact_json(source['request_ref'])['request']
            selector = assignment['selector']
            if self.store.get_artifact(source['artifact_ref']) != original.content or request['job_id'] != target['execution_id'] or request['page'] != selector['page'] or (request['page_size'] != selector.get('page_size', target['assignment']['page_size'])):
                raise ValueError('api_result_completion_requested_page_conflict')
            return {'version': 'practical_completion_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(assignment), 'endpoint': 'usable_handoff', 'operation_key': row['operation_key'], 'receipt_sha256': digest(receipt), 'validation_keys': ['requested_result_page']}
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
