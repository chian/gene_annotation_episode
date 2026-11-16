from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_values import *

class APIRecordAccess:
    """Keep service-native protocols behind the shared execution interfaces."""

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
        from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_record_access import AppServiceRecordAccess as BVBRCAppServiceHost
        self.appservice = BVBRCAppServiceHost(self)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import BVBRCHomologyReturns
        self.homology_returns = BVBRCHomologyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import BVBRCPhylogenyReturns
        self.phylogeny_returns = BVBRCPhylogenyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import BVBRCProteomeReturns
        self.proteome_returns = BVBRCProteomeReturns(self)

    @property
    def uniprot_returns(self):
        from gene_annotation_episode.episodic_workflow.root.a104.uniprot_returns import UniProtReturns
        if '_uniprot_returns' not in self.__dict__:
            self._uniprot_returns = UniProtReturns(self)
        return self._uniprot_returns

    def __getattr__(self, name):
        legacy = self.__dict__.get('legacy')
        if legacy is not None:
            return getattr(legacy, name)
        raise AttributeError(name)

    def _legacy_binding(self):
        if self.legacy is None:
            raise ValueError('legacy_api_resource_not_bound')
        return self.legacy

    def assignment_schema(self, resource_id):
        if resource_id not in self.configuration:
            raise ValueError('api_resource_not_bound')
        if resource_id not in self.services:
            schema = deepcopy(API_ASSIGNMENT_SCHEMA)
        else:
            from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
            schema = deepcopy(API_SERVICE_ASSIGNMENT_SCHEMA)
            schema['properties']['service'] = {'const': self.services[resource_id].service}
            schema['properties']['request'] = deepcopy(self.services[resource_id].request_schema)
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        return schema

    def validate_assignment(self, assignment, *, scope=None):
        assignment = validate_api_assignment(plain(assignment))
        resource_id = assignment['resource_id']
        schema = self.assignment_schema(resource_id)
        checked(assignment, schema, 'api_service_assignment_conflict')
        if resource_id not in self.services:
            self._legacy_binding()._constraints(assignment)
            if scope is not None:
                self.tools._check_sequence_operand(assignment['subject_ref'], plain(scope))
        else:
            service = self.services[resource_id]
            service.validate_request(assignment['request'], plain(scope) if scope is not None else None)
            for key, value in assignment['constraints'].items():
                if key == 'allowed_resource_ids':
                    valid = isinstance(value, list) and resource_id in value
                elif key == 'allowed_kinds':
                    valid = isinstance(value, list) and 'api' in value
                elif key == 'kind':
                    valid = value == 'api'
                elif key in {'resource_id', 'service', 'request', 'endpoint'}:
                    valid = value == assignment[key]
                else:
                    valid = False
                if not valid:
                    raise ValueError('api_service_constraint_conflict:' + key)
        return assignment

    def capabilities(self, resource_id):
        if resource_id in self.services:
            return self.services[resource_id].capabilities()
        return [{'name': name} for name in ('api.hmmer.databases', 'api.hmmer.prepare', 'api.hmmer.submit', 'api.hmmer.status', 'api.hmmer.check_handoff')]

    def operation_contracts(self, resource_id, role):
        """Actual configured service contracts; no query or target is fabricated."""
        if resource_id not in self.configuration:
            raise ValueError('api_resource_not_bound')
        if role not in {'launch_api', 'results'}:
            raise ValueError('api_execution_role_required')
        if resource_id not in self.services:
            from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_values import hmmer_operation_catalog as hmmer_operation_catalog
            return hmmer_operation_catalog(role)
        service = self.services[resource_id]
        if service.service == 'bvbrc_appservice':
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_tool_info import bvbrc_appservice_tool_contracts
            return [{key: deepcopy(row[key]) for key in ('name', 'description', 'input_schema', 'instructions')} for row in bvbrc_appservice_tool_contracts(resource_id=resource_id) if any((route['resource_role'] == role for route in row['invocation_route']['routes']))]
        entries = service.capabilities() if role == 'launch_api' else service.result_capabilities()
        return [{key: deepcopy(row[key]) for key in ('name', 'description', 'input_schema', 'instructions') if key in row} for row in entries]

    def is_handoff_source(self, reference):
        try:
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
            if self.store.get(reference).get('provider') == APPSERVICE_PROVIDER:
                self.appservice.read_handoff(reference)
                return True
            return self.store.get(reference).get('provider') in {PROVIDER, LEGACY_PROVIDER}
        except (ValueError, KeyError, OSError, TypeError):
            return False

    def validate_result_selector(self, target, selector):
        if target['assignment'].get('version') == 'api_execution_assignment_v1':
            schema = {'type': 'object', 'properties': {'page': {'type': 'integer', 'minimum': 1}, 'page_size': {'type': 'integer', 'minimum': 1}}, 'required': ['page'], 'additionalProperties': False}
        else:
            self.validate_assignment(target['assignment'], scope=target['scope'])
            schema = self.services[target['resource_id']].selector_schema
        value = checked(selector, schema, 'invalid_api_service_result_selector')
        if target['assignment'].get('version') != 'api_execution_assignment_v1':
            self.services[target['resource_id']].result_catalog(target['assignment']['request'], value)
        return value

    def _episode_directory(self, episode_id):
        return self.directory / 'episodes' / digest(episode_id)

    def _manifest(self, context, *, create=True):
        directory = self._episode_directory(context.episode_id)
        body = {'run_id': self.run_id, 'episode_id': context.episode_id, 'role': context.role, 'assignment': plain(context.assignment), 'scope': plain(context.scope)}
        path = directory / 'assignment.json'
        if create:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'actions').mkdir(exist_ok=True)
            _immutable(path, body)
        if not path.exists() or _read(path) != body:
            raise ValueError('api_original_assignment_conflict')
        return directory

    def _selected(self, context, name, arguments, key):
        prefix = f'{self.run_id}:{context.episode_id}:'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('api_selected_action_identity_required')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, context.episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('api_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('api_selected_action_conflict')
        return row

    def _snapshot(self, snapshot):
        fields = asdict(snapshot)
        fields.pop('content')
        fields['content_ref'] = self.store.artifact(snapshot.content, snapshot.media_type)
        return json.loads(canonical(fields))

    def _load_snapshot(self, metadata):
        fields = deepcopy(metadata)
        fields['content'] = self.store.get_artifact(fields.pop('content_ref'))
        return SourceSnapshot(**fields)

    def _event(self, value):
        value = json.loads(canonical(value))
        if set(value) != EVENT_FIELDS or value['kind'] not in {'response', 'job', 'preparation', 'metadata'} or value['state'] not in STATES or (type(value['handoff_ready']) is not bool) or (type(value['result_available']) is not bool) or (not isinstance(value['facts'], dict)) or (value['native_handle'] is not None and (not isinstance(value['native_handle'], dict))) or (value['failure_code'] is not None and (not isinstance(value['failure_code'], str))):
            raise ValueError('invalid_api_service_native_event')
        if value['handoff_ready'] and value['state'] not in {'submitted', 'running', 'completed'}:
            raise ValueError('api_service_unusable_handoff_state')
        return value

    def _action_paths(self, episode_id):
        directory = self._episode_directory(episode_id) / 'actions'
        return sorted(directory.glob('*/intent.json'), key=lambda path: int(_read(path)['operation_key'].rsplit(':', 1)[-1])) if directory.exists() else []

    def _events(self, episode_id):
        result = []
        for path in self._action_paths(episode_id):
            event_path = path.parent / 'event.json'
            if event_path.exists():
                intent = _read(path)
                result.append({'name': intent['name'], 'prepared': intent['prepared'], 'event': _read(event_path), 'operation_key': intent['operation_key']})
        return sorted(result, key=lambda row: int(row['operation_key'].rsplit(':', 1)[-1]))

    def _native_handle(self, target):
        return self._read_handoff(target['handle'], target['scope'])['event']['native_handle']

    def _submission_snapshot(self, target):
        if target['assignment'].get('service') == 'bvbrc_appservice':
            body = self.appservice.read_handoff(target['handle'], target['scope'])
            return self._load_snapshot(body['snapshot'])
        for path in self._action_paths(target['origin_episode_id']):
            intent = _read(path)
            snapshot = path.parent / 'snapshot.json'
            if intent['prepared'].get('mutates_remote') and snapshot.exists():
                return self._load_snapshot(_read(snapshot))
        return None

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        value = json.loads(raw)
        if raw != canonical(value).encode('utf-8') or reference != 'artifact_' + hashlib.sha256(raw).hexdigest():
            raise ValueError('api_service_artifact_identity_conflict')
        return value

    def _original_context(self, manifest):
        from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
        return BindingContext(self.run_id, manifest['episode_id'], manifest['role'], ((manifest['role'], 'original'),), manifest['scope'], manifest['assignment'], {})

    def _read_handoff(self, reference, scope, *, verify_artifacts=True):
        source = self.store.get(reference)
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if source.get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_handoff(reference, scope)
        if source.get('provider') != PROVIDER or source.get('record_type') != 'source' or source.get('origin') != 'tool':
            raise ValueError('not_an_api_service_handoff')
        body = self._artifact_json(source['artifact_ref'])
        if set(body) != {'version', 'run_id', 'episode_id', 'assignment', 'assignment_sha256', 'scope', 'event', 'snapshot', 'receipt'} or body.get('version') != HANDOFF_VERSION or body.get('run_id') != self.run_id:
            raise ValueError('api_service_handoff_identity_conflict')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        assignment = self.validate_assignment(body['assignment'], scope=body['scope'])
        if body['assignment_sha256'] != digest(assignment):
            raise ValueError('api_service_handoff_assignment_conflict')
        manifest = _read(self._episode_directory(body['episode_id']) / 'assignment.json')
        if manifest['role'] != 'launch_api' or manifest['assignment'] != assignment or manifest['scope'] != body['scope']:
            raise ValueError('api_service_original_assignment_conflict')
        receipt = body['receipt']
        context = self._original_context(manifest)
        directory = self._manifest(context, create=False) / 'actions' / digest(receipt['operation_key'])
        intent = _read(directory / 'intent.json')
        if _read(directory / 'handoff_receipt.json') != receipt:
            raise ValueError('api_service_original_handoff_receipt_conflict')
        event = self._event(_read(directory / 'event.json'))
        metadata = _read(directory / 'snapshot.json')
        historical_uniprot = not verify_artifacts and assignment.get('service') == 'uniprot'
        if historical_uniprot:
            if metadata.get('content_ref') != 'artifact_' + receipt['snapshot_sha256']:
                raise ValueError('uniprot_source_snapshot_conflict')
            snapshot_sha256 = receipt['snapshot_sha256']
        else:
            snapshot_sha256 = self._load_snapshot(metadata).sha256
        if event != body['event'] or not event['handoff_ready'] or metadata != body['snapshot'] or (receipt['run_id'] != self.run_id) or (receipt['episode_id'] != body['episode_id']) or (receipt['assignment_sha256'] != digest(assignment)) or (receipt['name'] != intent['name']) or (receipt['tool_name'] != intent['name']) or (receipt['arguments'] != intent['arguments']) or (receipt['state'] != event['state']) or (receipt['snapshot_sha256'] != snapshot_sha256):
            raise ValueError('api_service_handoff_receipt_conflict')
        selected = self._selected(context, intent['name'], intent['arguments'], receipt['operation_key'])
        if (directory / 'outcome.json').exists():
            outcome = _read(directory / 'outcome.json')
            if outcome.get('status') != 'completed' or reference not in outcome.get('record_refs', []) or outcome.get('result', {}).get('receipt') != receipt:
                raise ValueError('api_service_handoff_outcome_conflict')
        if selected['result'] is not None and reference not in json.loads(selected['result']).get('record_refs', []):
            raise ValueError('api_service_handoff_runtime_outcome_conflict')
        expected = {'provider': PROVIDER, 'accession': 'api_handoff_' + digest([self.run_id, body['episode_id'], receipt['operation_key']]), 'uri': None, 'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'], 'request_ref': source['artifact_ref'], 'version': HANDOFF_VERSION, 'retrieved_at': receipt['finished_at']}
        if {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != expected or reference != identity('source', {'origin': 'tool', 'record': expected}):
            raise ValueError('api_service_handoff_source_conflict')
        return body

    def scope(self, handoff_ref):
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if self.store.get(handoff_ref).get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_handoff(handoff_ref)['scope']
        if self.store.get(handoff_ref).get('provider') == LEGACY_PROVIDER:
            return self._legacy_binding().scope(handoff_ref)
        body = self._artifact_json(self.store.get(handoff_ref)['artifact_ref'])
        return self._read_handoff(handoff_ref, body['scope'])['scope']

    def read_target(self, handoff_ref, scope, *, verify_artifacts=True):
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if self.store.get(handoff_ref).get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_target(handoff_ref, scope)
        if self.store.get(handoff_ref).get('provider') == LEGACY_PROVIDER:
            return self._legacy_binding().read_target(handoff_ref, scope)
        body = self._read_handoff(handoff_ref, scope, verify_artifacts=verify_artifacts)
        event = body['event']
        handle = event['native_handle'] or {}
        if event['kind'] == 'job':
            execution_id = next((handle[key] for key in ('id', 'rid', 'task_id', 'execution_id', 'job_id') if isinstance(handle.get(key), str) and handle[key]), None)
            if execution_id is None:
                raise ValueError('api_actual_native_job_identity_required')
        else:
            execution_id = 'request:' + body['receipt']['operation_key']
        return validate_target({'version': 'execution_target_v1', 'handle': handoff_ref, 'run_id': self.run_id, 'resource_id': body['assignment']['resource_id'], 'resource_kind': 'api', 'execution_id': execution_id, 'request_sha256': digest(body['assignment']), 'origin_episode_id': body['episode_id'], 'assignment': body['assignment'], 'scope': body['scope']})

    def received_blast_jobs(self, context, progress_provider):
        """Current saved state of only BLAST handoffs received by this episode.

        Reading this view makes no NCBI request. A status check remains a
        separately selected monitor/results action against the same RID.
        """
        from gene_annotation_episode.episodic_workflow.root.a104.api_blast import blast_wait_forecast
        jobs = []
        forecast_as_of = _now()
        received = sorted(set(context.received_record_refs))
        result_targets = set()
        for reference in received:
            if not (self.directory / 'result-index' / digest(reference)).exists():
                continue
            result = self.read_result(reference, context.scope)
            if result['target']['assignment'].get('service') == 'ncbi_blast':
                result_targets.add(result['target']['handle'])
        for reference in received:
            record = self.store.get(reference)
            if record.get('provider') != PROVIDER:
                continue
            body = self._read_handoff(reference, context.scope)
            if body['assignment']['service'] != 'ncbi_blast':
                continue
            target = self.read_target(reference, context.scope)
            handle = body['event']['native_handle']
            latest = progress_provider.latest_saved_observation(reference, context.scope)
            native_latest = progress_provider.latest_saved_observation(reference, context.scope, require_native_state=True)
            latest_failure_code = None if latest is None else latest['execution_status']['native'].get('failure_code')
            if native_latest is None:
                state = 'accepted'
                observed_at = body['snapshot']['retrieved_at']
                result_available = False
            else:
                observation = native_latest['execution_status']['native']
                state = observation['native']['facts']['native_state']
                observed_at = observation['observed_at']
                result_available = native_latest['result_available']
            progress_ref = None if latest is None else latest['progress_ref']
            forecast = blast_wait_forecast(handle, forecast_as_of, state)
            jobs.append({'handoff_ref': reference, 'origin_episode_id': target['origin_episode_id'], 'rid': handle['rid'], 'subject_ref': body['assignment']['request']['subject_ref'], 'program': body['assignment']['request']['program'], 'database': body['assignment']['request']['database'], 'native_state': state, 'observed_at': observed_at, 'forecast_as_of': forecast_as_of, 'latest_progress_failure_code': latest_failure_code, 'wait_forecast': forecast, 'progress_ref': progress_ref, 'result_available': result_available, 'result_received': reference in result_targets})
        return jobs

    def _own_outcomes(self, context):
        for path in self._action_paths(context.episode_id):
            outcome_path = path.parent / 'outcome.json'
            if outcome_path.exists():
                yield (path.parent, _read(outcome_path))

    def read_result(self, reference, scope, *, episode_id=None, operation_key=None, verify_artifacts=True):
        if self.appservice.publications.is_provider(self.store.get(reference).get('provider')):
            return self.appservice.publications.read(reference, scope, episode_id=episode_id)
        index = self.directory / 'result-index' / digest(reference)
        if index.exists():
            for path in sorted(index.glob('*.json')):
                pointer = _read(path)
                if episode_id is not None and pointer['episode_id'] != episode_id:
                    continue
                if operation_key is not None and pointer['operation_key'] != operation_key:
                    continue
                manifest = _read(self._episode_directory(pointer['episode_id']) / 'assignment.json')
                self.store.validate_scope(manifest['scope'], parent_scope=plain(scope))
                if manifest['role'] != 'results':
                    raise ValueError('api_result_original_role_conflict')
                context = self._original_context(manifest)
                assignment, _, target = self._saved_result_context(context, verify_artifacts=verify_artifacts)
                directory = self._manifest(context, create=False) / 'actions' / digest(pointer['operation_key'])
                intent, outcome = (_read(directory / 'intent.json'), _read(directory / 'outcome.json'))
                receipt = _read(directory / 'acquisition.json')
                if outcome['status'] not in {'completed', 'partial'} or reference not in outcome['record_refs']:
                    continue
                metadata = _read(directory / 'snapshot.json')
                uniprot = assignment.get('service') == 'uniprot'
                exact_publication = uniprot
                historical_uniprot = uniprot and (not verify_artifacts)
                if historical_uniprot:
                    from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import _same
                    original_context = self.uniprot_returns.context(context.episode_id)
                    if original_context.role != context.role or not _same(original_context.scope, context.scope) or (not _same(original_context.assignment, context.assignment)):
                        raise ValueError('uniprot_original_context_conflict')
                    if not self.uniprot_returns._successful_closed(original_context):
                        raise ValueError('uniprot_frozen_prefix_conflict')
                historical = historical_uniprot
                snapshot = None if historical else self._load_snapshot(metadata)
                snapshot_sha256 = receipt['snapshot_sha256'] if historical else snapshot.sha256
                if receipt['record_refs'] != outcome['record_refs'] or receipt['handoff_ref'] != target['handle'] or receipt['selector'] != plain(context.assignment)['selector'] or (receipt['assignment_sha256'] != digest(context.assignment)) or (receipt['snapshot_sha256'] != snapshot_sha256) or (receipt['source_ref'] != outcome['result'].get('source_ref')) or (outcome['result'].get('acquisition_receipt') != receipt):
                    raise ValueError('api_result_acquisition_receipt_conflict')
                selected = self._selected(context, intent['name'], intent['arguments'], pointer['operation_key'])
                if exact_publication and (receipt.get('run_id') != self.run_id or receipt.get('episode_id') != context.episode_id or receipt.get('operation_key') != pointer['operation_key'] or (intent.get('operation_key') != pointer['operation_key']) or (intent.get('run_id') != self.run_id) or (intent.get('episode_id') != context.episode_id) or (intent.get('assignment_sha256') != digest(context.assignment)) or (receipt.get('name') != intent['name']) or (receipt.get('arguments') != intent['arguments'])):
                    raise ValueError(assignment['service'] + '_original_receipt_conflict')
                if selected['result'] is not None:
                    actual = json.loads(selected['result'])
                    if actual.get('record_refs') != outcome['record_refs'] or actual.get('result') != outcome['result']:
                        raise ValueError('api_result_runtime_outcome_conflict')
                    if exact_publication:
                        from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import _same
                        actual.pop('pending_work_after_action', None)
                        if not _same(actual, outcome):
                            raise ValueError(assignment['service'] + '_original_receipt_conflict')
                source = self.store.get(receipt['source_ref'])
                if exact_publication and (metadata.get('content_ref') != source.get('artifact_ref') or source.get('artifact_ref') != 'artifact_' + receipt['snapshot_sha256']):
                    raise ValueError(assignment['service'] + '_source_snapshot_conflict')
                if not historical and self.store.get_artifact(source['artifact_ref']) != snapshot.content:
                    raise ValueError('api_result_original_response_conflict')
                return {'version': 'api_service_acquired_result_v1', 'reference': reference, 'run_id': self.run_id, 'episode_id': context.episode_id, 'scope': manifest['scope'], 'assignment': plain(context.assignment), 'target': target, 'source_ref': receipt['source_ref'], 'record_refs': list(outcome['record_refs']), 'status': outcome['status'], 'snapshot_sha256': snapshot_sha256, 'service_request': assignment['request'], **({'publication_result': deepcopy(outcome['result'])} if assignment['service'] in {'uniprot'} else {})}
        if self.legacy is not None and episode_id is None and (operation_key is None):
            return self._legacy_binding().read_result(reference, scope)
        raise ValueError('not_an_api_acquired_result')

    def result_identity(self, reference, scope):
        body = self.read_result(reference, scope)
        if body['version'] == 'bvbrc_appservice_acquired_bundle_v1':
            return self.appservice.publications.result_identity(body)
        if body['version'] != 'api_service_acquired_result_v1':
            return self._legacy_binding().result_identity(reference, scope)
        publication = set(body['record_refs'])
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import is_bvbrc_request
        if is_bvbrc_request(body['service_request']) and body['target']['assignment']['service'] == 'bvbrc_data':
            _, _, _, grading, _ = self.bvbrc_data._stored(reference, scope)
            page = digest({'service': 'bvbrc_data', 'request': grading['prepared']['effective_request'], 'population': grading['prepared']['query_population'], 'response_sha256': body['snapshot_sha256']})
        else:
            page = digest({'service': body['target']['assignment']['service'], 'request': body['service_request'], 'selector': body['assignment']['selector'], 'response_sha256': body['snapshot_sha256']})
        cache = {body['source_ref']: {'record_type': 'source', 'page': page}}
        visiting = set()

        def record(ref):
            if ref in cache:
                return cache[ref]
            if ref in visiting:
                raise ValueError('cyclic_api_result_identity')
            visiting.add(ref)
            value = {key: normalize(value) for key, value in self.store.get(ref).items() if key not in {'id', 'origin', 'retrieved_at'}}
            visiting.remove(ref)
            cache[ref] = value
            return value

        def normalize(value):
            if isinstance(value, str) and value in publication:
                return record(value)
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            return value
        return digest({'page': page, 'record': record(reference)})

    def resolve(self, context, reference, namespace):
        if context.run_id == self.run_id:
            if any((service.service == 'uniprot' for service in self.services.values())):
                resolved = self.uniprot_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.uniprot_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.homology_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.homology_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                return self.phylogeny_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.phylogeny_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                return self.proteome_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.proteome_returns.resolve_received(context, reference, namespace)
            resolved = self.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if context.run_id != self.run_id or namespace not in {None, 'source', 'execution_handoff', 'execution_result'}:
            return False
        try:
            if namespace != 'execution_result':
                self.read_target(reference, context.scope)
                return True
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            pass
        try:
            self.read_result(reference, context.scope)
            return namespace != 'execution_handoff' and (namespace != 'source' or self.store.get(reference)['record_type'] == 'source')
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            return False

    def read_bvbrc_result(self, reference, *, context, admission_operation_key=None):
        return self.bvbrc_data.read(reference, context=context, admission_operation_key=admission_operation_key)

    def record_bvbrc_admission(self, context, form, schema, operation_key):
        return self.bvbrc_data.record_admission(context, form, schema, operation_key)

    def received_bvbrc_context(self, context):
        return self.bvbrc_data.received_context(context)

    def _saved_result_context(self, context, *, verify_artifacts=True):
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
