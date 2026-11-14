from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_access import APIRecordAccess
from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.api_job_execution.hmmer_service import HMMERJobService as HMMERAPIExecution

class APIJobService(APIRecordAccess):

    def __init__(self, store, *, run_id, directory, configuration, tool_registry, handoff_unit, acquired_record_unit, received_input_reader=None):
        from gene_annotation_episode.episodic_workflow.root.a104.api_services import build_service
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_execution_run_required')
        for unit in (handoff_unit, acquired_record_unit):
            if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        self.store, self.run_id = (store, run_id)
        if received_input_reader is not None and (not callable(received_input_reader)):
            raise ValueError('api_received_input_reader_must_be_callable')
        self.received_input_reader = received_input_reader
        self.directory = Path(directory) / 'api-service-execution' / digest(run_id)
        self.configuration = json.loads(canonical(configuration))
        self.tools, self.clients = (tool_registry, tool_registry.clients)
        self.handoff_unit, self.acquired_record_unit = (handoff_unit, acquired_record_unit)
        from gene_annotation_episode.episodic_workflow.root.a104.api_selected_effects import SelectedAPIEffects
        self.selected_effects = SelectedAPIEffects(directory, run_id=run_id)
        if not self.configuration or tool_registry.store is not store:
            raise ValueError('actual_api_services_and_tool_registry_required')
        self.services = {}
        legacy = {}
        for resource_id, config in self.configuration.items():
            if config.get('kind') == 'hmmer_api':
                legacy[resource_id] = config
            elif config.get('kind') == 'api':
                self.services[resource_id] = build_service(config.get('service'), config, tool_registry)
            else:
                raise ValueError('unsupported_api_resource_configuration')
        self.legacy = None if not legacy else HMMERAPIExecution(store, run_id=run_id, directory=directory, configuration=legacy, tool_registry=tool_registry, handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import BVBRCDataHost
        self.bvbrc_data = BVBRCDataHost(self)
        from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.api_job_execution.appservice_submission import AppServiceSubmission as BVBRCAppServiceHost
        self.appservice = BVBRCAppServiceHost(self)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import BVBRCHomologyReturns
        self.homology_returns = BVBRCHomologyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import BVBRCPhylogenyReturns
        self.phylogeny_returns = BVBRCPhylogenyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import BVBRCProteomeReturns
        self.proteome_returns = BVBRCProteomeReturns(self)

    def _legacy_context(self, context):
        return plain(context.assignment).get('version') == 'api_execution_assignment_v1'

    def _context(self, context, *, verify_artifacts=True, _completed_appservice_download=False):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role != 'launch_api':
            raise ValueError('api_execution_role_required')
        assignment = self.validate_assignment(context.assignment, scope=context.scope)
        return (assignment, self.services[assignment['resource_id']], None)

    def initialize(self, context):
        if self._legacy_context(context):
            return self._legacy_binding().initialize(context)
        selected = None
        if any((bound.service == 'uniprot' for bound in self.services.values())):
            original = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
            selected = self.uniprot_returns._selection(context, original)
        _, service, _ = self._context(context)
        if selected is not None and selected['pages']:
            self.uniprot_returns._require(service.service == 'uniprot', 'original_context_conflict')
        if self.appservice.owns_context(context):
            self.appservice.validate_assignment(context)
        self._manifest(context)
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

    def catalog(self, context):
        if self._legacy_context(context):
            return self._legacy_binding().catalog(context)
        assignment, service, target = self._context(context)
        return service.launch_catalog(assignment['request'])

    async def execute(self, context, name, arguments, operation_key):
        if self._legacy_context(context):
            return await self._legacy_binding().execute(context, name, arguments, operation_key)
        try:
            arguments = plain(arguments)
            if name == 'api.bvbrc_appservice.download' and type(arguments) is dict and ('max_bytes' not in arguments):
                cached = self.appservice.legacy_cached_download(context, name, arguments, operation_key)
                if cached is not None:
                    return cached
            self.initialize(context)
            assignment, service, target = self._context(context)
            entry = next((row for row in self.catalog(context) if row['name'] == name), None)
            if entry is None:
                raise ValueError('api_operation_not_available')
            validate_schema(arguments, entry['input_schema'])
            self._selected(context, name, arguments, operation_key)
        except (ValueError, ContractError, KeyError, TypeError) as error:
            return _outcome(operation_key, status='invalid', code=str(error), **api_error_feedback(error))
        directory = self._manifest(context) / 'actions' / digest(operation_key)
        directory.mkdir(exist_ok=True)
        with (directory / '.lock').open('a') as lock:
            await asyncio.to_thread(fcntl.flock, lock, fcntl.LOCK_EX)
            try:
                return await self._execute_locked(context, assignment, service, target, name, arguments, operation_key, directory)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    async def _execute_locked(self, context, assignment, service, target, name, arguments, key, directory):
        if service.service == 'bvbrc_appservice':
            return await self.appservice.execute_locked(context, assignment, service, target, name, arguments, key, directory)
        intent_path, snapshot_path = (directory / 'intent.json', directory / 'snapshot.json')
        event_path, outcome_path = (directory / 'event.json', directory / 'outcome.json')
        original = {'run_id': self.run_id, 'episode_id': context.episode_id, 'name': name, 'arguments': arguments, 'assignment_sha256': digest(context.assignment), 'operation_key': key}
        if intent_path.exists():
            intent = _read(intent_path)
            if any((intent.get(field) != value for field, value in original.items())):
                return _outcome(key, status='invalid', code='api_operation_key_reused_for_different_work')
            if outcome_path.exists():
                outcome = _read(outcome_path)
                return outcome
            fresh = False
        else:
            try:
                if self._completion(context) is not None:
                    raise ValueError('api_assignment_already_completed')
                from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import is_bvbrc_request
                previous = self._events(context.episode_id)
                handle = None
                prepared = service.prepare(name, assignment['request'], arguments, scope=plain(context.scope), previous_events=previous, handle=handle, selector=None)
                canonical(prepared)
                if not isinstance(prepared, dict) or prepared.get('operation') != name:
                    raise ValueError('api_service_prepared_operation_conflict')
                if prepared.get('mutates_remote'):
                    for old in self._action_paths(context.episode_id):
                        if _read(old)['prepared'].get('mutates_remote'):
                            prior_path = old.parent / 'outcome.json'
                            prior = _read(prior_path) if prior_path.exists() else {}
                            not_sent = (prior.get('feedback') or {}).get('submission_outcome') == 'not_sent'
                            if not not_sent:
                                raise ValueError('api_original_submission_already_exists')
                intent = {**original, 'prepared': prepared, 'started_at': _now()}
                _immutable(intent_path, intent)
                fresh = True
            except (ValueError, ContractError, AcquisitionError, KeyError, TypeError) as error:
                return _outcome(key, status='invalid', code=getattr(error, 'code', str(error)), retry_after=getattr(error, 'retry_after', None), **api_error_feedback(error))
        prepared = intent['prepared']
        snapshot = None
        try:
            if snapshot_path.exists():
                snapshot = self._load_snapshot(_read(snapshot_path))
            elif prepared.get('cache_original'):
                raise ValueError('api_cached_result_requires_original_handoff')
            elif fresh:
                try:
                    snapshot = await asyncio.to_thread(service.invoke, prepared)
                except BaseException as error:
                    if getattr(error, 'snapshot', None) is not None:
                        _immutable(snapshot_path, self._snapshot(error.snapshot))
                    raise
                if snapshot is not None:
                    _immutable(snapshot_path, self._snapshot(snapshot))
            elif not event_path.exists():
                raise AcquisitionError('api_operation_response_unknown', phase='recovery', submission_outcome='unknown' if prepared.get('mutates_remote') else None)
            event = self._event(_read(event_path) if event_path.exists() else service.decode(prepared, snapshot))
            _immutable(event_path, event)
            outcome = _outcome(key, result={'service': service.service, 'event': event})
            if snapshot is not None and (event['state'] == 'failed' or event['failure_code']):
                outcome['result']['error_response'] = api_error_response(snapshot)
            if event['handoff_ready']:
                if snapshot is None:
                    raise ValueError('api_handoff_requires_actual_response')
                receipt = {**original, 'version': 'api_service_receipt_v1', 'tool_name': name, 'state': event['state'], 'native_kind': event['kind'], 'snapshot_sha256': snapshot.sha256, 'finished_at': _now()}
                if (directory / 'handoff_receipt.json').exists():
                    saved = _read(directory / 'handoff_receipt.json')
                    if any((saved.get(field) != value for field, value in receipt.items() if field != 'finished_at')):
                        raise ValueError('api_handoff_recovery_conflict')
                    receipt = saved
                _immutable(directory / 'handoff_receipt.json', receipt)
                reference = self._publish_handoff(context, event, _read(snapshot_path), receipt)
                outcome['record_refs'] = outcome['changed_record_refs'] = [reference]
                outcome['result'].update(handoff_ref=reference, receipt=receipt)
            _immutable(outcome_path, outcome)
            return outcome
        except BaseException as error:
            interruption = isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit))
            feedback = {**api_error_feedback(error, snapshot=snapshot), 'phase': getattr(error, 'phase', None), 'retry_after': getattr(error, 'retry_after', None), 'submission_outcome': getattr(error, 'submission_outcome', None)}
            if snapshot_path.exists():
                feedback['response_retained'] = True
            outcome = _outcome(key, status='failed', code=getattr(error, 'code', str(error) if isinstance(error, (ValueError, ContractError)) else 'api_service_operation_failed'), **feedback)
            if not interruption:
                _immutable(outcome_path, outcome)
            if interruption:
                raise
            return outcome

    def _publish_handoff(self, context, event, snapshot, receipt):
        body = {'version': HANDOFF_VERSION, 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment': plain(context.assignment), 'assignment_sha256': digest(context.assignment), 'scope': plain(context.scope), 'event': event, 'snapshot': snapshot, 'receipt': receipt}
        return self._handoff_source(body)

    def _handoff_source(self, body):
        artifact = self.store.artifact(canonical(body), 'application/json')
        payload = {'provider': PROVIDER, 'accession': 'api_handoff_' + digest([self.run_id, body['episode_id'], body['receipt']['operation_key']]), 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': artifact, 'version': HANDOFF_VERSION, 'retrieved_at': body['receipt']['finished_at']}
        return self.store.put('source', payload, origin='tool')['id']

    def _index_result(self, context, directory, outcome):
        for reference in outcome.get('record_refs', []):
            index = self.directory / 'result-index' / digest(reference)
            index.mkdir(parents=True, exist_ok=True)
            _immutable(index / (directory.name + '.json'), {'episode_id': context.episode_id, 'operation_key': _read(directory / 'intent.json')['operation_key']})

    def facts(self, context, completion_snapshot):
        if self._legacy_context(context):
            return {**self._legacy_binding().facts(context, completion_snapshot), 'execution_blast_hsps': []}
        self.initialize(context)
        if self.appservice.owns_context(context):
            return self.appservice.facts(context)
        handoffs, results = ([], [])
        for _, outcome in self._own_outcomes(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            for reference in outcome['record_refs']:
                if self.store.get(reference).get('provider') == PROVIDER:
                    self.read_target(reference, context.scope)
                    handoffs.append(reference)
        from gene_annotation_episode.episodic_workflow.root.a104.blast_result_views import blast_hsp_facts
        fields = (context.request.get('report_contract') or {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested_hsps = any((field.get('x-source') == 'execution_blast_hsps' for field in fields.values()))
        hsp_facts = []
        bvbrc_facts = self.bvbrc_data.facts(context, (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}))
        result_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        uniprot_facts = self.uniprot_returns.facts(context, result_schema) if any((service.service == 'uniprot' for service in self.services.values())) else {}
        return {'execution_handoff_refs': sorted(set(handoffs)), 'execution_result_refs': sorted(set(results)), **bvbrc_facts, **uniprot_facts, 'execution_blast_hsps': hsp_facts, 'execution_completed': self._completion(context) is not None}

    def credit_view(self, context, receiver_selection):
        if self._legacy_context(context):
            return self._legacy_binding().credit_view(context, receiver_selection)
        facts = self.facts(context, {})
        selection = plain(receiver_selection)
        known, initial = (set(selection['known_record_refs']), set(selection['initial_known_record_refs']))
        if not initial <= known:
            raise ValueError('api_initial_references_must_be_known')
        old_handoffs, old_results = (set(), set())
        for reference in initial:
            try:
                target = self.read_target(reference, context.scope)
                old_handoffs.add((target['resource_id'], target['execution_id']))
            except (ValueError, ContractError, KeyError, OSError):
                pass
            try:
                old_results.add(self.result_identity(reference, context.scope))
            except (ValueError, ContractError, KeyError, OSError):
                pass
        handoffs = set()
        for reference in set(facts['execution_handoff_refs']) & known:
            target = self.read_target(reference, context.scope)
            handoffs.add((target['resource_id'], target['execution_id']))
        results = {self.result_identity(ref, context.scope) for ref in set(facts['execution_result_refs']) & known}
        new_handoffs, new_results = (len(handoffs - old_handoffs), len(results - old_results))
        value = self.handoff_unit * new_handoffs + self.acquired_record_unit * new_results
        if not math.isfinite(value):
            raise ValueError('finite_operational_credit_required')
        return {'credit': value, 'operational_credit': value, 'new_handoff_count': new_handoffs, 'new_acquired_record_count': new_results, 'operational_credit_binding': {'version': VERSION, 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'scientific_credit': False, 'monitoring_credit': False}}

    def _completion(self, context):
        if self.appservice.owns_context(context):
            return self.appservice.completion(context)
        for directory, outcome in reversed(list(self._own_outcomes(context))):
            if outcome['status'] != 'completed':
                continue
            receipt = (outcome.get('result') or {}).get('receipt')
            if receipt is None:
                continue
            self.read_target(outcome['result']['handoff_ref'], context.scope)
            keys = ['usable_handoff']
            return {'version': 'practical_completion_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'usable_handoff', 'operation_key': receipt['operation_key'], 'receipt_sha256': digest(receipt), 'validation_keys': keys}
        return None

    def completion_for_action(self, context, operation_key):
        if self._legacy_context(context):
            return self._legacy_binding().completion_for_action(context, operation_key)
        proof = self._completion(context)
        return proof if proof is not None and proof['operation_key'] == operation_key else None

    def verify_completion(self, context, proof):
        if self._legacy_context(context):
            return self._legacy_binding().verify_completion(context, proof)
        try:
            proof = validate_completion_proof(plain(proof))
            return proof == self._completion(context)
        except (ValueError, ContractError, KeyError, TypeError, OSError):
            return False

    def decision_context(self, context, current_view=None):
        if self._legacy_context(context):
            return self._legacy_binding().decision_context(context, current_view)
        self.initialize(context)
        assignment, service, target = self._context(context)
        latest = {}
        for row in self._events(context.episode_id):
            latest[row['name']] = {'state': row['event']['state'], 'kind': row['event']['kind'], 'facts': row['event']['facts'], 'failure_code': row['event']['failure_code']}
        return {'api_service': service.service, 'api_request': assignment['request'], 'api_received_progress': latest, 'api_execution_completed': self._completion(context) is not None}
