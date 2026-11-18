import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.a104.library import bvbrc_proteome_bundle_adapter as adapter
from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import FACT_SOURCES
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a104.runtime import TypedReportContract
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.appservice_transport_fixture import CONFIG, PREFIX, metadata
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.commissioned_records_fixture import SavedRecords, api_assignment, selector as support_selector
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.appservice_host_fixture import ProductionDriver
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.appservice_input_fixture import NativeClient, receipt_row
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.proteome_bundle_fixture import SOURCE, fixture as provider_fixture, declaration
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.proteome_projection_fixture import selected_fields, MEAN
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.proteome_native_fixture import REFERENCE_HEADER, COMPARISON_HEADER
OUTPUT_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

def raw_native(fmt):
    raw = (SOURCE / 'input_000.bin').read_bytes()
    if fmt == 'genome_comparison_json_v1':
        return raw
    document = json.loads(raw)
    headers = REFERENCE_HEADER.split('\t') + COMPARISON_HEADER.split('\t')[:10]
    names = ['same label'] + [''] * 11 + ['same label'] + [''] * 9
    rows = [names, headers]
    for i, row in enumerate(document['feature_matches']):
        row['ref_genome_gene'] = i
        rows.append([str(row.get(key, '')) for key in headers])
    return ('\n'.join(('\t'.join(row) for row in rows)) + '\n').encode()

class ControlledClient(NativeClient):

    def __init__(self):
        super().__init__()
        self.native_complete, self.native_status = (True, 200)

    def download(self, url, *, max_bytes, byte_range=None):
        result = super().download(url, max_bytes=max_bytes, byte_range=byte_range)
        if url.endswith('/native'):
            result = replace(result, transport={**result.transport, 'body_complete': self.native_complete, 'status': self.native_status})
        return result

class ProteomeDriver(ProductionDriver):

    def __init__(self, store, directory, *, owners):
        self.saved, self.store = (SavedRecords(store), store)
        self.config = deepcopy(CONFIG)
        self.config['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION}]
        self.family = owners[0](None, store=store, directory=directory, run_id=self.saved.run_id, resources={'selected-api': self.config}, initial_information={}, tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3, log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.launch_family = owners[1](None, store=store, directory=directory, run_id=self.saved.run_id, resources={'selected-api': self.config}, initial_information={}, tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3, log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.parent_family = owners[2](None, store=store, directory=directory, run_id=self.saved.run_id, resources={'selected-api': self.config}, initial_information={}, tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3, log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.api, self.client = (self.family.api_execution, ControlledClient())
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.launch_api = self.launch_family.api_execution
        self.parent_api = self.parent_family.api_execution
        self.launch_api.services['selected-api'].client = self.client
        self.parent_api.services['selected-api'].client = self.client
        self.records, self.custody = (self.api.appservice.records, self.api.appservice.custody)
        self.last_outcome = None

    def form_schema(self, sources=FACT_SOURCES):
        descriptors = self.family._appservice_sources()
        properties = {f'fact{i}': deepcopy(descriptors[source]['report_schema']) for i, source in enumerate(sources)}
        return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

    def content(self, reference, field='artifact_ref'):
        source = self.store.get(reference)
        raw = self.store.get_artifact(source[field])
        return dict(source_ref=reference, artifact_field=field, artifact_ref=source[field], sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))

    def freeze_refs(self, parent, child, references):
        schema = plain(child.request)['report_contract']['measurements']['schema']
        form = {'refs': references}
        validate_form(form, schema, lambda ref, namespace=None: self.custody.possession(child, ref) is not None)
        self.freeze_form(parent, child, form, {'committed_record_refs': references})
        self.saved.receipts.receive(parent.episode_id, references, kind='child_form', source_index=int(child.path[-1][1][6:]))

    def freeze_form(self, parent, child, form, facts):
        index = int(child.path[-1][1][6:])
        self.saved.journal.save('runtime_forms', {'episode_id': child.episode_id, 'facts': canonical(facts), 'form': canonical(form)})
        self.saved.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id, 'decision_index': index, 'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24], 'child_episode_id': child.episode_id, 'contract': canonical(plain(child.request)['report_contract']), 'form': canonical(form), 'failure': None})

    def start(self, fmt='genome_comparison_json_v1', *, fields=None, supplementary=True):
        self.fmt, self.schema = (fmt, self.form_schema())
        self.outer_root = self.saved.root
        self.grandparent = self.saved.child(self.outer_root, 'evolutionary_history_evidence', {}, 0, schema=self.schema)
        self.parent = self.saved.child(self.grandparent, 'evolutionary_history_evidence', {}, 0, schema=self.schema)
        self.saved.root = self.parent
        self.query = {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1', 'required_application_id': 'GenomeComparison', 'parameters': {'genome_ids': [], 'user_genomes': ['/unused.faa', '/ref.faa', '/subject.faa'], 'user_feature_groups': [], 'reference_genome_index': 2, 'output_path': '/controlled/proteome', 'output_file': 'selected'}, 'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}
        launch_assignment = {'version': 'execution_launch_assignment_v1', 'requests': {'selected-api': api_assignment(self.query)}, 'immutable_input_versions': [], 'constraints': {'allowed_kinds': ['api']}}
        self.launch = self.saved.child(self.parent, 'launch', launch_assignment, 10)
        self.saved.receipts.receive(self.launch.episode_id, self.custody.initial_references(self.launch), kind='initial')
        self.context = self.saved.child(self.launch, 'launch_api', api_assignment(self.query), 0)
        self.api._manifest(self.context)
        preparation = self.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'GenomeComparison'}})
        self.client.value = {'id': '123', 'application_id': 'GenomeComparison', 'state_code': 'Q'}
        self.handoff = self.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []})
        source = self.handoff['value']['original_task']['submission_source_ref']
        self.submission_content = self.content(source, 'request_ref')
        references = [self.handoff['source_ref'], source]
        self.freeze_refs(self.launch, self.context, references)
        self.freeze_refs(self.parent, self.launch, references)
        self.support = self.saved.child(self.parent, 'results', {'version': 'execution_results_assignment_v1', 'handoff_ref': self.handoff['source_ref'], 'selector': support_selector()}, 20)
        self.api.initialize(self.support)
        self.client.value = {'123': {'id': '123', 'application_id': 'GenomeComparison', 'state_code': 'C'}}
        self.status = self.call('status', {'handoff_ref': self.handoff['source_ref']}, context=self.support)
        self.info = self.call('task_info', {'handoff_ref': self.handoff['source_ref'], 'file': 'job_result_id'}, context=self.support)
        self.freeze_refs(self.parent, self.support, [self.info['source_ref']])
        case = provider_fixture(supplementary=False)
        parameters = deepcopy(case['parameters'])
        document = parameters['native_documents'][0]
        document.pop('source_ref')
        document.pop('raw_artifact_ref')
        document.update(requirement_id='native', declared_format=declaration(fmt))
        parameters['analysis_id'] = 'controlled-proteome-host'
        self.selected = support_selector()
        self.selected['supplied_metadata'] = [dict(content=self.content(self.info['source_ref']), pointer='/value')]
        self.selected.update(endpoint='requested_projection', supplied_contents=[], adapter={'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION, 'parameters': parameters}, requested_schema=adapter.requested_form_schema(selected_fields() if fields is None else fields))
        self.selected['requirements'] = [dict(requirement_id='native', role='proteome_native_projection', required=True, declared_format=declaration(fmt), producer_rule_evidence=None, exact_object=None)]
        if supplementary:
            templates = json.loads((SOURCE / 'SUPPLIED_VALUES.json').read_text())
            supplied = dict(version='bvbrc_proteome_supplied_data_v1', original_input_index={'mode': 'construct', 'parameter_source': {'kind': 'submitted', 'source_field': {'source_ref': source, 'sha256': self.submission_content['sha256'], 'pointer': '/prepared/native_operands/call/rpc_request/params/1', 'row_ordinal': None, 'field_name': None}}, 'additional_parameter_sources': []}, inventories=[], feature_snapshots=[], genome_snapshots=[], sequence_snapshots=[], execution_links=[], native_links=[], metadata_links=[], representation_links=[])
            self.selected['supplied_contents'].append(self.submission_content)
            for number, (group, key) in enumerate((('inventories', 'ref'), ('inventories', 'subject'), ('feature_snapshots', 'feature'), ('genome_snapshots', 'genome'), ('sequence_snapshots', 'sequence')), 2):
                raw = (SOURCE / f'input_{number:03d}.bin').read_bytes()
                content = self.saved.source(raw, accession='controlled-supplied-' + key)
                self.saved.own(self.parent, content['source_ref'], index=number + 9)
                self.selected['supplied_contents'].append(content)
                original = templates[group][number - 2 if group == 'inventories' else 0]
                row = dict(mode='raw', declared_format=original['format'], source=dict(kind='supplied_snapshot', content=content, completeness_evidence=None))
                if group == 'inventories':
                    row['inventory_key'] = original['inventory_key']
                else:
                    row.update(snapshot_key=original['snapshot_key'], population=original['population'])
                    if group == 'feature_snapshots':
                        row['coordinate_convention'] = original['coordinate_convention']
                supplied[group].append(row)
            content = self.saved.source(canonical(supplied).encode(), accession='controlled-supplied-selection')
            self.saved.own(self.parent, content['source_ref'], index=21)
            evidence = dict(content=content, pointer='')
            parameters['supplied_data_evidence'] = evidence
            self.selected['supplied_metadata'].append(evidence)
            self.supplied = supplied
        self.context = self.saved.child(self.parent, 'results', {'version': 'execution_results_assignment_v1', 'handoff_ref': self.handoff['source_ref'], 'selector': self.selected}, 22, schema=self.schema)
        self.frozen_assignment = deepcopy(plain(self.context.assignment))
        self.api.initialize(self.context)
        return self.context

    def acquire_manifest(self, *, native_task='123'):
        obj = {'kind': 'task_info_object', 'receipt_ref': self.info['source_ref']}
        self.client.value = [[metadata('/controlled/proteome/manifest', type='job_result', size=None)['native_row']]]
        observed = self.call('workspace_metadata', {'objects': [obj], 'options': {}}, context=self.context)
        obj = receipt_row(observed)
        self.client.value = ['https://controlled.invalid/manifest']
        cap = self.call('download_capability', {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None}, context=self.context)
        manifest = {'id': native_task, 'app': {'id': 'GenomeComparison'}, 'parameters': deepcopy(self.query['parameters']), 'success': 1, 'output_files': [['/controlled/proteome/native', OUTPUT_UUID]]}
        self.client.body = canonical(manifest).encode()
        self.manifest = self.call('download', {'object': obj, 'capability': {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0}, 'max_bytes': 1024 * 1024, 'byte_range': None, 'requirement_ids': [], 'role': 'task_manifest', 'declared_format': declaration('json')}, context=self.context)
        return self.manifest

    def native_arguments(self):
        obj = {'kind': 'manifest_member', 'manifest_receipt_ref': self.manifest['source_ref'], 'output_index': 0}
        self.client.value = ['https://controlled.invalid/native']
        cap = self.call('download_capability', {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None}, context=self.context)
        self.native_args = {'object': obj, 'capability': {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0}, 'max_bytes': 1024 * 1024, 'byte_range': None, 'requirement_ids': ['native'], 'role': 'proteome_native_projection', 'declared_format': declaration(self.fmt)}
        return self.native_args

    def acquire_native(self, *, raw=None):
        args = self.native_arguments()
        self.client.body = raw_native(self.fmt) if raw is None else raw
        self.native = self.call('download', args, context=self.context)
        return self.publication()

    def publication(self):
        self.body = self.api.read_result(self.last_outcome['result']['source_ref'], self.context.scope)
        saved = self.body['publication']['adapter_result']
        self.sheet = self.api.appservice.publications.read_content_source(saved['sheet_content']['source_ref'], self.context.scope)
        self.components = None if saved['components_content'] is None else self.api.appservice.publications.read_content_source(saved['components_content']['source_ref'], self.context.scope)
        return self.body

    def admit_numeric(self, *, to_grandparent=False):
        child, parent = (self.parent, self.grandparent) if to_grandparent else (self.context, self.parent)
        facts = self.family.received_report_facts(child) if to_grandparent else self.family.facts(child, {})
        form = {name: facts[node['x-source']] for name, node in self.schema['properties'].items()}
        contract = TypedReportContract('Return original requested measurements', self.schema, lambda ref, namespace=None: self.family.resolve(child, ref, namespace), lambda value: self.family.validate_received_report(child, value, self.schema))
        admitted = contract.admit(form, audit_identifiers=())
        assert admitted is not None
        self.freeze_form(parent, child, form, facts)
        index = int(child.path[-1][1][6:])
        key = f'{parent.run_id}:{parent.episode_id}:{index}:typed_form'
        refs = self.family.received_form_references(parent, form, self.schema, key)
        self.saved.receipts.receive(parent.episode_id, refs, kind='child_form', source_index=index)
        self.family.validate_received_report(parent, form, self.schema)
        return (form, key, refs)

    def invoke(self, context, suffix, args, key):
        outcome = asyncio.run((self.launch_api if context.role == 'launch_api' else self.api).execute(context, PREFIX + suffix, args, key))
        self.last_outcome = outcome
        if outcome['status'] in {'completed', 'partial'}:
            index = int(key.rsplit(':', 1)[1])
            row = self.saved.journal.row('runtime_actions', context.episode_id, index)
            self.saved.journal.save('runtime_actions', {**row, 'result': canonical(outcome), 'credit': 0})
            self.saved.receipts.receive(context.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
        return outcome
