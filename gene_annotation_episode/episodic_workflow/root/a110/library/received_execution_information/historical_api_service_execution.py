"""Selected API operations in the existing episode loop, across real services.

This module records calls and qualifies their handoffs and acquisitions. Service
implementations supply individual native operations; neither layer owns a model
loop, polling schedule, retry decision or scientific interpretation.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_hmmer_api_readers import HMMERAPIExecution, PROVIDER as LEGACY_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, identity
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_api_contracts import API_ASSIGNMENT_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, checked, digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_api_contracts import validate_api_assignment, validate_target
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _immutable, _read
PROVIDER = 'episode.api_service_handoff'
HANDOFF_VERSION = 'api_service_handoff_v1'
EVENT_FIELDS = {'kind', 'state', 'native_handle', 'handoff_ready', 'result_available', 'facts', 'failure_code'}
STATES = {'submitted', 'running', 'completed', 'failed', 'unknown'}

def _now():
    return datetime.now(timezone.utc).isoformat()

class APIServiceExecution:
    """Keep service-native protocols behind the shared execution interfaces."""

    def __init__(self, store, *, run_id, directory, configuration, tool_registry, handoff_unit, acquired_record_unit, received_input_reader=None):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.api_services import build_received_service as build_service
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
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.api_selected_effects import SelectedAPIEffects
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
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_host import BVBRCDataHost
        self.bvbrc_data = BVBRCDataHost(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_minhash_host import BVBRCMinhashHost
        self.minhash = BVBRCMinhashHost(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_host import BVBRCAppServiceHost
        self.appservice = BVBRCAppServiceHost(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_homology_returns import BVBRCHomologyReturns
        self.homology_returns = BVBRCHomologyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_phylogeny_returns import BVBRCPhylogenyReturns
        self.phylogeny_returns = BVBRCPhylogenyReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_alignment_returns import BVBRCAlignmentReturns
        self.alignment_returns = BVBRCAlignmentReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_genome_alignment_returns import BVBRCGenomeAlignmentReturns
        self.genome_alignment_returns = BVBRCGenomeAlignmentReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_returns import BVBRCProteomeReturns
        self.proteome_returns = BVBRCProteomeReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_returns import BVBRCComparativeSystemsReturns
        self.comparative_systems_returns = BVBRCComparativeSystemsReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_fastqutils_returns import BVBRCFastqUtilsReturns
        self.fastqutils_returns = BVBRCFastqUtilsReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_application_returns import BVBRCApplicationReturns
        self.application_returns = BVBRCApplicationReturns(self)

    @property
    def rfam_returns(self):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rfam_batch_returns import RfamBatchReturns
        if '_rfam_returns' not in self.__dict__:
            self._rfam_returns = RfamBatchReturns(self)
        return self._rfam_returns

    @property
    def uniprot_returns(self):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.uniprot_returns import UniProtReturns
        if '_uniprot_returns' not in self.__dict__:
            self._uniprot_returns = UniProtReturns(self)
        return self._uniprot_returns

    @property
    def enrichr_protocol(self):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.api_enrichr_host import EnrichrProtocolHost
        if '_enrichr_protocol' not in self.__dict__:
            self._enrichr_protocol = EnrichrProtocolHost(self)
        return self._enrichr_protocol

    @property
    def enrichr_returns(self):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.enrichr_returns import EnrichrReturns
        if '_enrichr_returns' not in self.__dict__:
            self._enrichr_returns = EnrichrReturns(self)
        return self._enrichr_returns

    @property
    def addgene_returns(self):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.addgene_sequence_returns import AddgeneSequenceReturns
        if '_addgene_returns' not in self.__dict__:
            self._addgene_returns = AddgeneSequenceReturns(self)
        return self._addgene_returns

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
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_api_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
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
            if service.service == 'bvbrc_appservice' and assignment['request'].get('required_application_id') == 'ComparativeSystems':
                from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_tool_info import validate_comparative_request
                validate_comparative_request(assignment['request'])
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

    def is_handoff_source(self, reference):
        try:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
            if self.store.get(reference).get('provider') == APPSERVICE_PROVIDER:
                self.appservice.read_handoff(reference)
                return True
            return self.store.get(reference).get('provider') in {PROVIDER, LEGACY_PROVIDER}
        except (ValueError, KeyError, OSError, TypeError):
            return False

    def _legacy_context(self, context):
        if context.role == 'results':
            return self.store.get(context.assignment['handoff_ref']).get('provider') == LEGACY_PROVIDER
        return plain(context.assignment).get('version') == 'api_execution_assignment_v1'

    def _context(self, context, *, verify_artifacts=True, _enrichr_history=None, _completed_appservice_download=False):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role == 'launch_api':
            if _enrichr_history is not None:
                raise ValueError('enrichr_original_context_conflict')
            assignment = self.validate_assignment(context.assignment, scope=context.scope)
            return (assignment, self.services[assignment['resource_id']], None)
        if context.role != 'results':
            raise ValueError('api_execution_role_required')
        raw = plain(context.assignment)
        if set(raw) != {'version', 'handoff_ref', 'selector'} or raw['version'] != 'execution_results_assignment_v1':
            raise ValueError('invalid_api_results_assignment')
        target = self.read_target(raw['handoff_ref'], context.scope, verify_artifacts=verify_artifacts, _enrichr_history=_enrichr_history, **{'_completed_appservice_download': True} if _completed_appservice_download else {})
        self.validate_result_selector(target, raw['selector'])
        return (target['assignment'], self.services[target['resource_id']], target)

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

    def initialize(self, context):
        if self._legacy_context(context):
            return self._legacy_binding().initialize(context)
        selected = None
        if any((bound.service == 'uniprot' for bound in self.services.values())):
            original = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
            selected = self.uniprot_returns._selection(context, original)
        closed_target = self.closed_enrichr_target(context)
        if closed_target is None:
            _, service, _ = self._context(context)
        else:
            service = self.services[closed_target['resource_id']]
            self.validate_result_selector(closed_target, plain(context.assignment)['selector'])
        if selected is not None and selected['pages']:
            self.uniprot_returns._require(service.service == 'uniprot', 'original_context_conflict')
        if any((bound.service == 'enrichr' for bound in self.services.values())):
            schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
            if self.enrichr_returns.validate_fields(context, schema):
                self.enrichr_returns._require(service.service == 'enrichr', 'original_context_conflict')
        if self.appservice.owns_context(context):
            self.appservice.validate_assignment(context)
        self._manifest(context, create=closed_target is None)
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

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

    def closed_enrichr_target(self, context):
        """Recover an actual closed Results target from its original proof."""
        if context.role != 'results' or not any((service.service == 'enrichr' for service in self.services.values())):
            return None
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.enrichr_returns import OWN_WITNESSES
        from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import _same
        owner = self.enrichr_returns
        closed = owner._closed(context)
        if closed is None or OWN_WITNESSES not in closed['facts']:
            return None
        owner.authenticate(context)
        if not _same(owner.context(context.episode_id).as_record(), context.as_record()):
            raise ValueError('enrichr_original_context_conflict')
        if not owner._successful_closed(context):
            return None
        witnesses = owner._own_witnesses(context)
        if not witnesses:
            return None
        original = witnesses[0]
        body = self.read_result(original['source_ref'], context.scope, episode_id=context.episode_id, operation_key=original['operation_key'], verify_artifacts=False)
        return body['target']

    def _enrichr_history_witness(self, handoff_ref, scope, caller):
        """Recheck saved caller identities; the tuple itself grants nothing."""
        if type(caller) is not tuple or len(caller) != 3 or any((type(value) is not str for value in caller)):
            raise ValueError('enrichr_original_context_conflict')
        episode_id, operation_key, source_ref = caller
        context = self.enrichr_returns.context(episode_id)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        if context.role != 'results' or context.assignment.get('handoff_ref') != handoff_ref:
            raise ValueError('enrichr_original_context_conflict')
        return self.enrichr_returns.historical_result_witness(source_ref, context=context, operation_key=operation_key)

    def _validate_enrichr_result_snapshot(self, target, scope, snapshot):
        """A local window must use the authenticated original query capture."""
        body = self._read_handoff(target['handle'], scope)
        original = self._load_snapshot(body['snapshot'])
        actual_fields, original_fields = (asdict(snapshot), asdict(original))
        actual_content = actual_fields.pop('content')
        original_content = original_fields.pop('content')
        if type(actual_content) is not bytes or actual_content != original_content or canonical(actual_fields) != canonical(original_fields):
            raise ValueError('enrichr_original_result_snapshot_conflict')

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        value = json.loads(raw)
        if raw != canonical(value).encode('utf-8') or reference != 'artifact_' + hashlib.sha256(raw).hexdigest():
            raise ValueError('api_service_artifact_identity_conflict')
        return value

    def _original_context(self, manifest):
        from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
        return BindingContext(self.run_id, manifest['episode_id'], manifest['role'], ((manifest['role'], 'original'),), manifest['scope'], manifest['assignment'], {})

    def _read_handoff(self, reference, scope, *, verify_artifacts=True, _enrichr_history=None):
        source = self.store.get(reference)
        if _enrichr_history is not None and source.get('provider') != PROVIDER:
            raise ValueError('enrichr_original_context_conflict')
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
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
        historical_enrichr = None
        if _enrichr_history is not None:
            if verify_artifacts or assignment.get('service') != 'enrichr':
                raise ValueError('enrichr_original_context_conflict')
            historical_enrichr = self._enrichr_history_witness(reference, scope, _enrichr_history)
            if digest(metadata) != historical_enrichr['snapshot_metadata_sha256'] or metadata.get('content_ref') != historical_enrichr['native_artifact_ref'] or historical_enrichr['snapshot_sha256'] != receipt['snapshot_sha256']:
                raise ValueError('enrichr_source_snapshot_conflict')
        if historical_uniprot:
            if metadata.get('content_ref') != 'artifact_' + receipt['snapshot_sha256']:
                raise ValueError('uniprot_source_snapshot_conflict')
            snapshot_sha256 = receipt['snapshot_sha256']
        elif historical_enrichr is not None:
            snapshot_sha256 = historical_enrichr['snapshot_sha256']
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
        if assignment.get('service') == 'enrichr':
            if historical_enrichr is None:
                self.enrichr_protocol.validate(context, self.services[assignment['resource_id']], intent, directory, self._load_snapshot(metadata))
            else:
                self.enrichr_protocol.validate_closed_metadata(context, self.services[assignment['resource_id']], intent, directory, metadata, protocol_artifacts=historical_enrichr['protocol_artifacts'])
        return body

    def scope(self, handoff_ref):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if self.store.get(handoff_ref).get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_handoff(handoff_ref)['scope']
        if self.store.get(handoff_ref).get('provider') == LEGACY_PROVIDER:
            return self._legacy_binding().scope(handoff_ref)
        body = self._artifact_json(self.store.get(handoff_ref)['artifact_ref'])
        return self._read_handoff(handoff_ref, body['scope'])['scope']

    def read_target(self, handoff_ref, scope, *, verify_artifacts=True, _enrichr_history=None, _completed_appservice_download=False):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if _enrichr_history is not None and self.store.get(handoff_ref).get('provider') != PROVIDER:
            raise ValueError('enrichr_original_context_conflict')
        if self.store.get(handoff_ref).get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_target(handoff_ref, scope, **{'_completed_download': True} if _completed_appservice_download else {})
        if _completed_appservice_download:
            raise ValueError('appservice_cached_download_context_conflict')
        if self.store.get(handoff_ref).get('provider') == LEGACY_PROVIDER:
            return self._legacy_binding().read_target(handoff_ref, scope)
        body = self._read_handoff(handoff_ref, scope, verify_artifacts=verify_artifacts, _enrichr_history=_enrichr_history)
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
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.api_blast import blast_wait_forecast
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
                enrichr_history = None
                if not verify_artifacts and self.store.get(reference).get('provider') == 'enrichr':
                    if type(verify_artifacts) is not bool:
                        raise ValueError('enrichr_original_context_conflict')
                    from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import _same
                    owner = self.enrichr_returns.context(context.episode_id)
                    if owner.role != context.role or not _same(owner.scope, context.scope) or (not _same(owner.assignment, context.assignment)):
                        raise ValueError('enrichr_original_context_conflict')
                    self.enrichr_returns.historical_result_witness(reference, context=owner, operation_key=pointer['operation_key'])
                    enrichr_history = (context.episode_id, pointer['operation_key'], reference)
                assignment, _, target = self._context(context, verify_artifacts=verify_artifacts, _enrichr_history=enrichr_history)
                directory = self._manifest(context, create=False) / 'actions' / digest(pointer['operation_key'])
                intent, outcome = (_read(directory / 'intent.json'), _read(directory / 'outcome.json'))
                receipt = _read(directory / 'acquisition.json')
                if outcome['status'] not in {'completed', 'partial'} or reference not in outcome['record_refs']:
                    continue
                metadata = _read(directory / 'snapshot.json')
                uniprot = assignment.get('service') == 'uniprot'
                enrichr = assignment.get('service') == 'enrichr'
                exact_publication = uniprot or enrichr
                historical_uniprot = uniprot and (not verify_artifacts)
                historical_enrichr = enrichr and enrichr_history is not None
                if enrichr_history is not None and (not enrichr):
                    raise ValueError('enrichr_original_context_conflict')
                if historical_uniprot:
                    from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import _same
                    owner = self.uniprot_returns.context(context.episode_id)
                    if owner.role != context.role or not _same(owner.scope, context.scope) or (not _same(owner.assignment, context.assignment)):
                        raise ValueError('uniprot_original_context_conflict')
                    if not self.uniprot_returns._successful_closed(owner):
                        raise ValueError('uniprot_frozen_prefix_conflict')
                historical = historical_uniprot or historical_enrichr
                snapshot = None if historical else self._load_snapshot(metadata)
                snapshot_sha256 = receipt['snapshot_sha256'] if historical else snapshot.sha256
                if enrichr and (not historical_enrichr):
                    self._validate_enrichr_result_snapshot(target, context.scope, snapshot)
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
                        from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import _same
                        if enrichr and 'pending_work_after_action' in actual:
                            from gene_annotation_episode.episodic_workflow.root.a110.waiting import validate_pending
                            validate_pending(actual['pending_work_after_action'])
                        actual.pop('pending_work_after_action', None)
                        if not _same(actual, outcome):
                            raise ValueError(assignment['service'] + '_original_receipt_conflict')
                source = self.store.get(receipt['source_ref'])
                if exact_publication and (metadata.get('content_ref') != source.get('artifact_ref') or source.get('artifact_ref') != 'artifact_' + receipt['snapshot_sha256']):
                    raise ValueError(assignment['service'] + '_source_snapshot_conflict')
                if not historical and self.store.get_artifact(source['artifact_ref']) != snapshot.content:
                    raise ValueError('api_result_original_response_conflict')
                return {'version': 'api_service_acquired_result_v1', 'reference': reference, 'run_id': self.run_id, 'episode_id': context.episode_id, 'scope': manifest['scope'], 'assignment': plain(context.assignment), 'target': target, 'source_ref': receipt['source_ref'], 'record_refs': list(outcome['record_refs']), 'status': outcome['status'], 'snapshot_sha256': snapshot_sha256, 'service_request': assignment['request'], **({'publication_result': deepcopy(outcome['result'])} if assignment['service'] in {'rfam_batch', 'uniprot', 'sequence_support', 'enrichr'} else {})}
        if self.legacy is not None and episode_id is None and (operation_key is None):
            return self._legacy_binding().read_result(reference, scope)
        raise ValueError('not_an_api_acquired_result')

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
                elif context.role == 'results':
                    self.read_result(reference, context.scope)
                    results.append(reference)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_result_views import blast_hsp_facts
        fields = (context.request.get('report_contract') or {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested_hsps = any((field.get('x-source') == 'execution_blast_hsps' for field in fields.values()))
        hsp_facts = blast_hsp_facts(self.store, results) if context.role == 'results' and requested_hsps else []
        bvbrc_facts = self.bvbrc_data.facts(context, (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}))
        minhash_facts = self.minhash.facts(context, (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}))
        rfam_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        rfam_facts = self.rfam_returns.facts(context, rfam_schema) if any((service.service == 'rfam_batch' for service in self.services.values())) else {}
        uniprot_facts = self.uniprot_returns.facts(context, rfam_schema) if any((service.service == 'uniprot' for service in self.services.values())) else {}
        enrichr_facts = self.enrichr_returns.facts(context, rfam_schema) if any((service.service == 'enrichr' for service in self.services.values())) else {}
        addgene_facts = {}
        if any((service.service == 'sequence_support' for service in self.services.values())):
            closing = completion_snapshot is not None and completion_snapshot.get('completion') is not None
            addgene_facts = self.addgene_returns.facts_for_closure(context, rfam_schema) if closing else self.addgene_returns.facts(context, rfam_schema)
        return {'execution_handoff_refs': sorted(set(handoffs)), 'execution_result_refs': sorted(set(results)), **bvbrc_facts, **minhash_facts, **rfam_facts, **uniprot_facts, **enrichr_facts, **addgene_facts, 'execution_blast_hsps': hsp_facts, 'execution_completed': self._completion(context) is not None}

    def _completion(self, context):
        if self.appservice.owns_context(context):
            return self.appservice.completion(context)
        for directory, outcome in reversed(list(self._own_outcomes(context))):
            if outcome['status'] != 'completed':
                continue
            if context.role == 'launch_api':
                receipt = (outcome.get('result') or {}).get('receipt')
                if receipt is None:
                    continue
                self.read_target(outcome['result']['handoff_ref'], context.scope)
                keys = ['usable_handoff']
            else:
                receipt = (outcome.get('result') or {}).get('acquisition_receipt')
                if receipt is None or not outcome['record_refs']:
                    continue
                acquired = self.read_result(outcome['record_refs'][0], context.scope)
                if acquired['target']['assignment'].get('service') == 'rfam_batch':
                    qualified = self.rfam_returns.read(outcome['record_refs'][0], context.scope, episode_id=context.episode_id)
                    if context.assignment['selector']['projection'] is not None and qualified['projection'] is None:
                        continue
                from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_host import is_bvbrc_request
                if is_bvbrc_request(acquired.get('service_request')):
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_publication import requested_projection_failures
                    qualified = self.read_bvbrc_result(acquired['source_ref'], context=context)
                    failures = requested_projection_failures(qualified['grading'], input_results=qualified['input_results'])
                    if failures:
                        continue
                keys = ['requested_service_result']
            return {'version': 'practical_completion_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'usable_handoff', 'operation_key': receipt['operation_key'], 'receipt_sha256': digest(receipt), 'validation_keys': keys}
        return None

    def resolve(self, context, reference, namespace):
        if context.run_id == self.run_id:
            if any((service.service == 'enrichr' for service in self.services.values())):
                resolved = self.enrichr_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.enrichr_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if any((service.service == 'uniprot' for service in self.services.values())):
                resolved = self.uniprot_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.uniprot_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if any((service.service == 'sequence_support' for service in self.services.values())):
                resolved = self.addgene_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.addgene_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace in {'rfam_record', 'rfam_query', 'rfam_family', 'rfam_model'}:
                return self.rfam_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.rfam_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.homology_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.homology_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                return self.phylogeny_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.phylogeny_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
            if namespace in ALIGNMENT_NAMESPACES:
                return self.alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
            if namespace in GENOME_ALIGNMENT_NAMESPACES:
                return self.genome_alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.genome_alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                return self.proteome_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.proteome_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                return self.comparative_systems_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.comparative_systems_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
            if namespace in FASTQUTILS_NAMESPACES:
                return self.fastqutils_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.fastqutils_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
            if namespace in APPLICATION_NAMESPACES:
                return self.application_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.application_returns.resolve_received(context, reference, namespace)
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
