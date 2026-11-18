from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_access import APIRecordAccess
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.hmmer_acquisition import HMMERResultAcquisition as HMMERAPIExecution

class APIResultAcquisition(APIRecordAccess):

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
        from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.appservice_acquisition import AppServiceAcquisition as BVBRCAppServiceHost
        self.appservice = BVBRCAppServiceHost(self)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import BVBRCHomologyReturns
        self.homology_returns = BVBRCHomologyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import BVBRCPhylogenyReturns
        self.phylogeny_returns = BVBRCPhylogenyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import BVBRCProteomeReturns
        self.proteome_returns = BVBRCProteomeReturns(self)

    def _legacy_context(self, context):
        return self.store.get(context.assignment['handoff_ref']).get('provider') == LEGACY_PROVIDER

    def _context(self, context, *, verify_artifacts=True):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role != 'results':
            raise ValueError('api_execution_role_required')
        raw = plain(context.assignment)
        if set(raw) != {'version', 'handoff_ref', 'selector'} or raw['version'] != 'execution_results_assignment_v1':
            raise ValueError('invalid_api_results_assignment')
        target = self.read_target(raw['handoff_ref'], context.scope, verify_artifacts=verify_artifacts)
        self.validate_result_selector(target, raw['selector'])
        return (target['assignment'], self.services[target['resource_id']], target)

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
        return service.result_catalog(assignment['request'], plain(context.assignment)['selector'])

    async def execute(self, context, name, arguments, operation_key):
        if self._legacy_context(context):
            return await self._legacy_binding().execute(context, name, arguments, operation_key)
        try:
            arguments = plain(arguments)
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
                self._index_result(context, directory, outcome)
                return outcome
            fresh = False
        else:
            try:
                if self._completion(context) is not None:
                    raise ValueError('api_assignment_already_completed')
                from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import is_bvbrc_request
                if service.service == 'bvbrc_data' and is_bvbrc_request(assignment['request']):
                    self.bvbrc_data.validate_inputs(context, plain(context.assignment)['selector'], request=assignment['request'])
                previous = self._events(context.episode_id)
                handle = self._native_handle(target)
                prepared = service.prepare(name, assignment['request'], arguments, scope=plain(context.scope), previous_events=previous, handle=handle, selector=plain(context.assignment)['selector'])
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
                metadata = self._read_handoff(target['handle'], context.scope)['snapshot']
                snapshot = self._load_snapshot(metadata)
                _immutable(snapshot_path, metadata)
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
            acquired = event['kind'] == 'response' and event['result_available']
            if acquired:
                if snapshot is None:
                    raise ValueError('api_result_response_required')
                publication = {}
                from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import is_bvbrc_request
                if service.service == 'bvbrc_data' and is_bvbrc_request(assignment['request']):
                    inputs_path = directory / 'publication_inputs.json'
                    inputs = self.bvbrc_data.publication_inputs(context, prepared['prepared_query'])
                    _immutable(inputs_path, inputs)
                    publication['publication_inputs'] = _read(inputs_path)
                published_path = directory / 'publication.json'
                if publication and published_path.exists():
                    outcome = _read(published_path)
                else:
                    outcome = service.publish(assignment['request'], plain(context.assignment)['selector'], snapshot, plain(context.scope), key + ':publication', submission_snapshot=self._submission_snapshot(target), handle=self._native_handle(target), **publication)
                    if publication:
                        _immutable(published_path, json.loads(canonical(outcome)))
                outcome = json.loads(canonical(outcome))
                outcome['operation_ref'] = identity('api_operation', {'key': key})
                result = outcome.setdefault('result', {})
                if result is None:
                    result = outcome['result'] = {}
                receipt = {**original, 'version': 'api_service_acquisition_v1', 'handoff_ref': target['handle'], 'selector': plain(context.assignment)['selector'], 'snapshot_sha256': snapshot.sha256, 'record_refs': list(outcome.get('record_refs', [])), 'source_ref': result.get('source_ref'), 'finished_at': _now()}
                if publication:
                    from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_schema import json_digest
                    receipt['publication_inputs_sha256'] = json_digest(publication['publication_inputs'])
                if (directory / 'acquisition.json').exists():
                    saved = _read(directory / 'acquisition.json')
                    if any((saved.get(field) != value for field, value in receipt.items() if field != 'finished_at')):
                        raise ValueError('api_acquisition_recovery_conflict')
                    receipt = saved
                result['acquisition_receipt'] = receipt
                result['handoff_ref'] = target['handle']
                _immutable(directory / 'acquisition.json', receipt)
            else:
                outcome = _outcome(key, result={'service': service.service, 'event': event})
                if snapshot is not None and (event['state'] == 'failed' or event['failure_code']):
                    outcome['result']['error_response'] = api_error_response(snapshot)
            if acquired:
                self._index_result(context, directory, outcome)
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
                else:
                    self.read_result(reference, context.scope)
                    results.append(reference)
        from gene_annotation_episode.episodic_workflow.root.a104.blast_result_views import blast_hsp_facts
        fields = (context.request.get('report_contract') or {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested_hsps = any((field.get('x-source') == 'execution_blast_hsps' for field in fields.values()))
        hsp_facts = blast_hsp_facts(self.store, results) if requested_hsps else []
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
            receipt = (outcome.get('result') or {}).get('acquisition_receipt')
            if receipt is None or not outcome['record_refs']:
                continue
            acquired = self.read_result(outcome['record_refs'][0], context.scope)
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import is_bvbrc_request
            if is_bvbrc_request(acquired.get('service_request')):
                from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_publication import requested_projection_failures
                qualified = self.read_bvbrc_result(acquired['source_ref'], context=context)
                failures = requested_projection_failures(qualified['grading'], input_results=qualified['input_results'])
                if failures:
                    continue
            keys = ['requested_service_result']
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
