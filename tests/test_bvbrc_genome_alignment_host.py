"""Real GenomeAlignment host integration with controlled native service replies.

The Store, selected-action journal, executor, receipt authentication, custody,
publication, configured E provider and F typed-return consumers are production
objects. Selections and HTTP/RPC responses are scripted. Retained native files
are unchanged; their association with this controlled task is a fixture, not a
claim of live BV-BRC execution or configured-model Workflow verification.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_genome_alignment_returns import FACT_SOURCES
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.state import Store
from test_api_bvbrc_appservice import CONFIG, PREFIX, OBJECT_UUID, metadata
from test_bvbrc_appservice_custody import SavedRecords, refs_schema, selector as support_selector
from test_bvbrc_appservice_host import ProductionDriver
from test_bvbrc_appservice_inputs import NativeClient, receipt_row
from test_bvbrc_genome_alignment_bundle_resolution import measurement, member
from test_bvbrc_genome_alignment_retained_records import inline, log_bytes
from test_bvbrc_genome_alignment_sheet import all_requests, plan, slot
from test_mauve_v4_formats import OFFICIAL


MEASUREMENTS = 'bvbrc_genome_alignment_measurements'
ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'
FILES = {'mauve_v4': OFFICIAL, 'mauve1_xmfa': NATIVE / 'separate.xmfa',
    'mauve_backbone': NATIVE / 'separate.xmfa.backbone', 'mauve_bbcols': NATIVE / 'separate.xmfa.bbcols'}
SLOTS = {'mauve_v4': 'v4', 'mauve1_xmfa': 'xmfa', 'mauve_backbone': 'backbone', 'mauve_bbcols': 'bbcols'}
OUTPUT_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


def declaration(fmt):
    return {'format': fmt, 'version': {'mauve_v4': '4', 'mauve1_xmfa': 'Mauve1'}.get(fmt),
        'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}


def query(fmt='mauve_v4'):
    genomes = ['123.1', '456.2'] if fmt == 'mauve_v4' else ['123.1', '456.2', '789.3']
    return {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
        'required_application_id': 'GenomeAlignment', 'parameters': {
            'genome_ids': genomes, 'recipe': 'mauveAligner' if fmt == 'mauve_v4' else 'progressiveMauve',
            'output_path': '/controlled/genome-alignment', 'output_file': 'selected'},
        'start_parameters': {}, 'definition_inputs': [],
        'input_bindings': [inline('original-genomes', '/genome_ids', genomes)], 'workspace_targets': []}


def selected_fields(fmt):
    return {'native': {
        'mauve_v4': measurement(field='coverage_fraction'),
        'mauve1_xmfa': measurement('pairs', 'xmfa_pair', 'identity_fraction', block_index=0, member_a=1, member_b=2),
        'mauve_backbone': measurement('backbone', 'backbone_coverage', member=member(0, 'mauve_sidecar_member_0based')),
        'mauve_bbcols': measurement('columns', 'bbcols_interval', 'union_columns', native_interval_index_0based=0),
    }[fmt]}


def selection(fmt, *, fields=None):
    chosen = slot(SLOTS[fmt], fmt)
    requests = [r for r in all_requests() if r['document_slot_id'] == chosen['slot_id']]
    slots = [chosen]
    if fmt == 'mauve_bbcols':
        slots.append(slot('xmfa', 'mauve1_xmfa'))
    value = support_selector()
    value.update(endpoint='requested_projection', adapter={'adapter_id': adapter.ADAPTER_ID,
        'adapter_version': adapter.ADAPTER_VERSION, 'parameters': {
            'schema_version': 'bvbrc_genome_alignment_parameters_v1', 'analysis_id': 'controlled-host-native',
            'document_slots': slots, 'calculation_plan': plan(requests)}},
        requested_schema=adapter.requested_form_schema(selected_fields(fmt) if fields is None else fields),
        supplied_contents=[])
    value['requirements'] = [
        {'requirement_id': 'manifest', 'role': 'task_manifest', 'required': False,
         'declared_format': declaration('json'), 'producer_rule_evidence': None, 'exact_object': None},
        {'requirement_id': 'native', 'role': chosen['role'], 'required': True,
         'declared_format': declaration(fmt), 'producer_rule_evidence': None, 'exact_object': None},
    ]
    return value


class ControlledClient(NativeClient):
    """Only the selected native transport response is controlled."""
    def __init__(self):
        super().__init__()
        self.stdout = b''

    def task_info(self, task_id, file):
        snapshot = super().task_info(task_id, file)
        raw = self.stdout if file == 'stdout' else snapshot.content
        return replace(snapshot, content=raw, transport={**snapshot.transport,
            'received_body_bytes': len(raw), 'headers': {'content-length': str(len(raw))}})


class GenomeDriver(ProductionDriver):
    def __init__(self, store, directory):
        self.saved, self.store = SavedRecords(store), store
        self.config = deepcopy(CONFIG)
        self.config['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID,
            'adapter_version': adapter.ADAPTER_VERSION, 'implementation_sha256': adapter.implementation_sha256()}]
        self.family = ExecutionEpisodes(None, store=store, directory=directory, run_id=self.saved.run_id,
            resources={'selected-api': self.config}, initial_information={},
            tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.api = self.family.api_execution
        self.client = ControlledClient()
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.records, self.custody = self.api.appservice.records, self.api.appservice.custody
        self.last_outcome = None

    def form_schema(self, sources=(MEASUREMENTS,)):
        descriptors = self.family._appservice_sources()
        properties = {f'fact{i}': deepcopy(descriptors[source]['report_schema']) for i, source in enumerate(sources)}
        return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

    def content(self, reference):
        source = self.store.get(reference)
        raw = self.store.get_artifact(source['artifact_ref'])
        return {'source_ref': reference, 'artifact_field': 'artifact_ref', 'artifact_ref': source['artifact_ref'],
            'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}

    def freeze_refs(self, parent, child, references):
        schema = plain(child.request)['report_contract']['measurements']['schema']
        form = {'refs': references}
        validate_form(form, schema, lambda ref, namespace=None: self.custody.possession(child, ref) is not None)
        index = int(child.path[-1][1].removeprefix('child_'))
        self.saved.journal.save('runtime_forms', {'episode_id': child.episode_id,
            'facts': canonical({'committed_record_refs': references}), 'form': canonical(form)})
        self.saved.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24],
            'child_episode_id': child.episode_id, 'contract': canonical(plain(child.request)['report_contract']),
            'form': canonical(form), 'failure': None})
        self.saved.receipts.receive(parent.episode_id, references, kind='child_form', source_index=index)

    def start(self, fmt='mauve_v4', *, fields=None, stdout='explicit', candidate=False, identity_content=True):
        self.schema = self.form_schema()
        self.saved.root = self.saved.child(self.saved.root, 'scientific_process', {}, 0, schema=self.schema)
        self.parent = self.saved.root
        self.query = query(fmt)
        self.tree(self.query)
        preparation = self.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'GenomeAlignment'}})
        self.client.value = {'id': '123', 'application_id': 'GenomeAlignment', 'state_code': 'Q'}
        handoff = self.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []})
        self.handoff = handoff
        support = self.results(handoff)
        self.api.initialize(support)
        self.client.value = {'123': {'id': '123', 'application_id': 'GenomeAlignment', 'state_code': 'C'}}
        self.status = self.call('status', {'handoff_ref': handoff['source_ref']}, context=support)
        self.info = self.call('task_info', {'handoff_ref': handoff['source_ref'], 'file': 'job_result_id'}, context=support)
        self.client.stdout = log_bytes(self.query['parameters']['genome_ids'], recipe=self.query['parameters']['recipe'])
        self.log = self.call('task_info', {'handoff_ref': handoff['source_ref'], 'file': 'stdout'}, context=support)
        refs = [self.info['source_ref'], self.info['value']['receipt']['snapshot']['source_ref'], self.log['source_ref']]
        if stdout == 'explicit':
            refs.append(self.log['value']['receipt']['snapshot']['source_ref'])
        self.freeze_refs(self.parent, support, refs)
        selected = selection(fmt, fields=fields)
        selected['supplied_metadata'] = [{'content': self.content(r['source_ref']), 'pointer': '/value'}
            for r in (self.info, self.log)]
        selected['supplied_contents'] = ([deepcopy(self.info['value']['receipt']['snapshot']['content'])]
            if identity_content else [])
        if stdout in ('explicit', 'unreceived_selected'):
            selected['supplied_contents'].append(deepcopy(self.log['value']['receipt']['snapshot']['content']))
        if candidate:
            self.candidate_bytes = self.saved.source(b'>candidate one\nACGT\n>candidate two\nry\n')
            metadata_value = {'kind': 'genome_alignment_staged_file', 'original_task_id': '123',
                'file_id': 'explicit-candidate', 'native_path_token': '/task/work/123.1.fasta',
                'content': self.candidate_bytes, 'genome_occurrence_indices': [0],
                'retrieval': {'query': None, 'requested_record_limit': None, 'reported_total_records': None,
                    'returned_records': 2, 'state': 'unknown', 'evidence': []}}
            self.candidate_metadata = self.saved.source(canonical({'candidate': metadata_value}).encode())
            for i, binding in enumerate((self.candidate_bytes, self.candidate_metadata), 4):
                self.saved.own(self.parent, binding['source_ref'], index=i)
            selected['supplied_metadata'].append({'content': self.candidate_metadata, 'pointer': '/candidate'})
            selected['supplied_contents'].append(self.candidate_bytes)
        self.context = self.saved.child(self.parent, 'results', {
            'version': 'execution_results_assignment_v1', 'handoff_ref': handoff['source_ref'], 'selector': selected},
            6 if candidate else 4, schema=self.schema)
        self.api._manifest(self.context)
        self.selected = selected
        self.fmt = fmt
        return self.context

    def acquire_manifest(self, *, native_task='123'):
        obj = {'kind': 'task_info_object', 'receipt_ref': self.info['source_ref']}
        self.client.value = [[metadata('/controlled/genome-alignment/manifest', type='job_result', size=None)['native_row']]]
        observed = self.call('workspace_metadata', {'objects': [obj], 'options': {}}, context=self.context)
        manifest_object = receipt_row(observed)
        self.client.value = ['https://controlled.invalid/manifest']
        cap = self.call('download_capability', {'objects': [manifest_object], 'generation': 0,
            'predecessor_receipt_ref': None}, context=self.context)
        self.native_manifest = {'id': native_task, 'app': {'id': 'GenomeAlignment'},
            'parameters': deepcopy(self.query['parameters']), 'success': 1,
            'output_files': [['/controlled/genome-alignment/native', OUTPUT_UUID]]}
        self.client.body = canonical(self.native_manifest).encode()
        args = {'object': manifest_object, 'capability': {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0},
            'max_bytes': 1024 * 1024, 'byte_range': None, 'requirement_ids': ['manifest'], 'role': 'task_manifest', 'declared_format': declaration('json')}
        self.manifest = self.call('download', args, context=self.context)
        self.manifest_publication = self.api.read_result(self.last_outcome['result']['source_ref'], self.context.scope)
        return self.manifest

    def native_arguments(self):
        obj = {'kind': 'manifest_member', 'manifest_receipt_ref': self.manifest['source_ref'], 'output_index': 0}
        self.client.value = ['https://controlled.invalid/native']
        cap = self.call('download_capability', {'objects': [obj], 'generation': 0,
            'predecessor_receipt_ref': None}, context=self.context)
        self.native_args = {'object': obj, 'capability': {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0},
            'max_bytes': 1024 * 1024, 'byte_range': None, 'requirement_ids': ['native'], 'role': self.selected['requirements'][1]['role'],
            'declared_format': declaration(self.fmt)}
        return self.native_args

    def acquire_native(self, *, raw=None):
        args = self.native_arguments()
        self.client.body = FILES[self.fmt].read_bytes() if raw is None else raw
        self.native = self.call('download', args, context=self.context)
        return self.publication()

    def publication(self):
        self.body = self.api.read_result(self.last_outcome['result']['source_ref'], self.context.scope)
        saved = self.body['publication']['adapter_result']
        self.sheet = self.api.appservice.publications.read_content_source(saved['sheet_content']['source_ref'], self.context.scope)
        self.components = self.api.appservice.publications.read_content_source(saved['components_content']['source_ref'], self.context.scope)
        return self.body

    def admit_numeric(self):
        facts = self.family.facts(self.context, {})
        form = {name: facts[node['x-source']] for name, node in self.schema['properties'].items()}
        validate_form(form, self.schema, lambda ref, namespace=None: self.api.resolve(self.context, ref, namespace))
        self.family.validate_received_report(self.context, form, self.schema)
        self.saved.journal.save('runtime_forms', {'episode_id': self.context.episode_id,
            'facts': canonical(facts), 'form': canonical(form)})
        index = int(self.context.path[-1][1].removeprefix('child_'))
        self.saved.journal.save('runtime_report_attempts', {'parent_episode_id': self.parent.episode_id,
            'decision_index': index, 'delivery_ref': 'delivery_' + digest([self.parent.episode_id, index])[:24],
            'child_episode_id': self.context.episode_id, 'contract': canonical(plain(self.context.request)['report_contract']),
            'form': canonical(form), 'failure': None})
        key = f'{self.parent.run_id}:{self.parent.episode_id}:{index}:typed_form'
        refs = self.family.received_form_references(self.parent, form, self.schema, key)
        self.saved.receipts.receive(self.parent.episode_id, refs, kind='child_form', source_index=index)
        self.family.validate_received_report(self.parent, form, self.schema)
        return form, key, refs


@pytest.fixture
def driver(tmp_path, monkeypatch):
    def forbidden(*a, **k):
        pytest.fail('controlled GenomeAlignment host test attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    with Store(tmp_path / 'state') as store:
        yield GenomeDriver(store, tmp_path)


@pytest.mark.parametrize('fmt,expected', [('mauve_v4', 690 / 693), ('mauve1_xmfa', 40 / 48),
    ('mauve_backbone', 50), ('mauve_bbcols', 52)])
def test_registered_provider_native_publication_and_original_parent_receipt(driver, fmt, expected):
    d = driver
    d.start(fmt)
    assert d.service.scientific_adapters[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)][0] is adapter
    d.acquire_manifest()
    assert d.api._completion(d.context) is None
    body = d.acquire_native()
    saved = body['publication']['adapter_result']
    assert saved['status'] == 'ok', saved['missing_requirements']
    assert saved['facts']['native']['value']['value'] == expected
    assert body['publication']['requested_form_status'] == 'satisfied'
    assert d.sheet['components'] == d.components
    assert d.sheet['data']['associations']['artifacts'][0]['state'] == 'bound'
    assert d.sheet['data']['inputs']['invocation']['observed_argv'][0] == d.query['parameters']['recipe']
    assert [o['input_binding_id'] for o in d.sheet['data']['inputs']['genome_occurrences']] == ['original-genomes'] * len(d.query['parameters']['genome_ids'])
    assert d.store.get_artifact(d.native['value']['artifact']['raw_artifact_ref']) == FILES[fmt].read_bytes()
    assert d.native['value']['artifact']['task_association']['byte_version_status'] == 'unknown'
    assert saved['missing_requirements']
    proof = d.api._completion(d.context)
    assert proof is not None and d.api.verify_completion(d.context, proof)
    form, key, refs = d.admit_numeric()
    assert refs == [body['source_ref']]
    received = d.family.received_report_facts(d.parent)
    assert set(received) == {MEASUREMENTS}
    assert received[MEASUREMENTS] == form['fact0']
    assert received[MEASUREMENTS][0]['value']['value']['value'] == expected
    assert d.family.resolve_received_reference(d.parent, form['fact0'][0]['field'], 'bvbrc_genome_alignment_field')
    assert d.family.received_form_references(d.parent, form, d.schema, key) == refs
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_explicit_candidate_metadata_preserves_zero_missing_and_unknown_source_identity(driver):
    d = driver
    location = {'interval_index': 0, 'segment_index': 0, 'member': member()}
    fields = {'coverage': measurement(field='coverage_fraction'),
        'zero': measurement('anchors', 'v4_member', 'selected_gap_count', **location),
        'missing': measurement('anchors', 'v4_member', 'selected_canonical_count', **location)}
    d.start(fields=fields, candidate=True)
    d.acquire_manifest()
    body = d.acquire_native()
    saved = body['publication']['adapter_result']
    assert saved['facts']['coverage']['value']['value'] == 690 / 693
    assert (saved['facts']['zero']['value']['value'], saved['facts']['zero']['value']['state']) == (0, 'available')
    assert (saved['facts']['missing']['value']['value'], saved['facts']['missing']['value']['state']) == (None, 'missing')
    assert saved['status'] == 'partial' and d.api._completion(d.context) is None
    inputs = d.sheet['data']['inputs']
    candidate = next(f for f in inputs['files'] if f['content'] == d.candidate_bytes)
    assert [r['header'] for r in candidate['records']] == ['candidate one', 'candidate two']
    assert [len(r['sequence']) for r in candidate['records']] == [4, 2]
    assert candidate['same_run_state'] == candidate['path_state'] == 'unverified'
    assert candidate['genome_occurrence_indices'] == []
    assert candidate['retrieval']['state'] == inputs['genome_census_state'] == 'unknown'
    assert all(m['source_length'] is None for m in inputs['member_bindings'])
    assert inputs['original_maps'] == [] and inputs['xmfa_source_inputs'] is None
    form, _, _ = d.admit_numeric()
    assert {row['field'].rsplit('/', 1)[1]: row['value']['value']['value'] for row in form['fact0']} == {
        'coverage': 690 / 693, 'zero': 0, 'missing': None}


def test_receipt_reference_does_not_supply_unreceived_stdout_bytes(driver):
    d = driver
    d.start(stdout='receipt_only', identity_content=False)
    native = d.log['value']['receipt']['snapshot']['content']
    assert d.store.get_artifact(native['artifact_ref']) == d.client.stdout
    assert d.custody.possession(d.context, d.log['source_ref']) == 'parent_assignment'
    with pytest.raises(ValueError, match='input_not_possessed'):
        d.custody.possession(d.context, native['source_ref'])
    d.acquire_manifest()
    body = d.acquire_native()
    saved = body['publication']['adapter_result']
    assert saved['status'] == 'ok' and saved['facts']['native']['value']['value'] == 690 / 693
    assert d.sheet['data']['inputs']['invocation']['observed_argv'] is None
    missing = [r for r in saved['missing_requirements'] if r['reason_code'] == 'bvbrc_genome_alignment_content_missing']
    assert any(d.log['source_ref'] in r['source_refs'] for r in missing)
    records, raw = d.api.appservice.publications._genome_alignment_retained_records(
        d.context, body['publication_inputs'], body['bundle'], current_acquisition=d.native)
    assert any(r['record']['source_ref'] == d.log['source_ref'] for r in records)
    assert native['artifact_ref'] not in raw
    # Addendum015 permits this exact job_result_id operational identity chain;
    # it still grants neither log content nor general native-source possession.
    identity = d.info['value']['receipt']['snapshot']['content']
    assert raw[identity['artifact_ref']] == (OBJECT_UUID + '\n').encode()
    with pytest.raises(ValueError, match='input_not_possessed'):
        d.custody.possession(d.context, identity['source_ref'])
    assert d.api._completion(d.context) is not None


def test_explicitly_selecting_unreceived_log_is_rejected_by_real_custody(driver):
    d = driver
    d.start(stdout='unreceived_selected')
    calls = len(d.client.calls)
    with pytest.raises(ValueError, match='input_not_possessed'):
        d.api.initialize(d.context)
    assert len(d.client.calls) == calls
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_wrong_task_native_manifest_and_wrong_receipt_are_rejected_before_native_download(driver):
    d = driver
    d.start()
    d.acquire_manifest(native_task='not-the-original-task')
    for obj in (
        {'kind': 'manifest_member', 'manifest_receipt_ref': d.manifest['source_ref'], 'output_index': 0},
        {'kind': 'manifest_member', 'manifest_receipt_ref': d.info['source_ref'], 'output_index': 0},
        {'kind': 'receipt_row', 'receipt_ref': d.manifest['source_ref'], 'row_pointer': '/result/0/0'},
    ):
        args = {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None}
        calls = len(d.client.calls)
        context, key = d.selection('download_capability', args, context=d.context)
        outcome = d.invoke(context, 'download_capability', args, key)
        assert outcome['status'] == 'invalid'
        assert outcome['feedback']['code'] in {'task_manifest_mismatch', 'appservice_acquisition_receipt_required',
            'appservice_receipt_contract_conflict'}
        assert len(d.client.calls) == calls
    assert d.api._completion(d.context) is None


def test_actual_current_acquisition_exception_and_wrong_retained_inputs_reject(driver, monkeypatch):
    d = driver
    d.start()
    calls = []
    actual = d.api.appservice.publications._genome_alignment_retained_records

    def observed(context, inputs, bundle, *, current_acquisition):
        origin = current_acquisition['value']['origin']
        index = int(origin['operation_key'].rsplit(':', 1)[1])
        assert d.saved.journal.row('runtime_actions', context.episode_id, index)['result'] is None
        # The real reader still requires completion by default at this point.
        with pytest.raises((ValueError, FileNotFoundError)):
            d.records.read(current_acquisition['source_ref'])
        result = actual(context, inputs, bundle, current_acquisition=current_acquisition)
        assert sum(r['record']['source_ref'] == current_acquisition['source_ref'] for r in result[0]) == 1
        calls.append((current_acquisition['source_ref'], [r['record']['source_ref'] for r in result[0]]))
        return result

    monkeypatch.setattr(d.api.appservice.publications, '_genome_alignment_retained_records', observed)
    d.acquire_manifest()
    d.acquire_native()
    monkeypatch.setattr(d.api.appservice.publications, '_genome_alignment_retained_records', actual)
    assert len(calls) == 2 and d.native['source_ref'] == calls[-1][0]
    assert d.manifest['source_ref'] in calls[-1][1]
    inputs, bundle, current = d.body['publication_inputs'], d.body['bundle'], d.native
    before = len(d.client.calls)
    for kind, code in (
        ('task', 'original_task_mismatch'),
        ('receipt', 'appservice_genome_alignment_current_acquisition_conflict'),
        ('request', 'appservice_genome_alignment_current_acquisition_conflict'),
        ('selector', 'publication_adapter_conflict'),
    ):
        bad_inputs, bad_bundle, bad_current = deepcopy(inputs), deepcopy(bundle), deepcopy(current)
        if kind == 'task':
            bad_bundle['original_task']['task_id'] = 'different-task'
        elif kind == 'receipt':
            bad_current = deepcopy(d.manifest)
        elif kind == 'request':
            bad_inputs['request']['parameters']['output_file'] = 'different-request'
        else:
            bad_inputs['selector']['adapter']['parameters']['analysis_id'] = 'different-selector'
        with pytest.raises(ValueError, match='^' + code + '$'):
            actual(d.context, bad_inputs, bad_bundle, current_acquisition=bad_current)
    assert len(d.client.calls) == before
    # Clearing a prior action's saved result is deliberate negative corruption;
    # its record is not allowed to borrow the exact-current exception.
    origin = d.manifest['value']['origin']
    index = int(origin['operation_key'].rsplit(':', 1)[1])
    saved = d.saved.journal.row('runtime_actions', d.context.episode_id, index)
    d.saved.journal.save('runtime_actions', {**saved, 'result': None})
    try:
        with pytest.raises(ValueError, match='completed_action_required'):
            actual(d.context, inputs, bundle, current_acquisition=current)
    finally:
        d.saved.journal.save('runtime_actions', saved)
    assert d.api.read_result(d.body['source_ref'], d.context.scope) == d.body


def forbid_saved_science(monkeypatch):
    from test_bvbrc_genome_alignment_returns import forbid_science
    forbid_science(monkeypatch)
    def forbidden(*a, **k):
        raise AssertionError('saved host projection entered numerical verification')
    for name in ('mauve_v4_calculation_contracts', 'mauve_backbone_contracts', 'xmfa_calculation_contracts'):
        module = importlib.import_module('gene_annotation_episode.' + name)
        for attr in ('union_intervals', 'interval_length', 'multiplicity_bases', 'complement_intervals',
                     '_cell', '_coverage_counts', '_union'):
            if hasattr(module, attr):
                monkeypatch.setattr(module, attr, forbidden)
    monkeypatch.setattr('math.log2', forbidden)


def test_saved_host_return_replay_forbids_science_and_adds_no_observations(driver, monkeypatch):
    d = driver
    d.start('mauve1_xmfa')
    d.acquire_manifest()
    original_body = deepcopy(d.acquire_native())
    form, admission_key, refs = d.admit_numeric()
    original_outcome = deepcopy(d.last_outcome)
    operation = d.native['value']['origin']['operation_key']
    original_actions = [dict(r) for r in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')]
    original_observations = [dict(r) for r in d.store.db.execute('SELECT * FROM runtime_observations')]
    calls = deepcopy(d.client.calls)
    forbid_saved_science(monkeypatch)
    assert d.invoke(d.context, 'download', d.native_args, operation) == original_outcome
    # The stronger shared numerical barrier also blocks socket construction;
    # install it after asyncio's replay loop has closed, before all saved reads.
    from test_genome_alignment_saved_structure import scientific_barrier
    scientific_barrier(monkeypatch)
    assert d.api.read_result(original_body['source_ref'], d.context.scope) == original_body
    assert d.api.facts(d.context, {})[MEASUREMENTS] == form['fact0']
    assert d.family.received_report_facts(d.parent)[MEASUREMENTS] == form['fact0']
    assert d.family.received_form_references(d.parent, form, d.schema, admission_key) == refs
    assert d.client.calls == calls
    assert [dict(r) for r in d.store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')] == original_actions
    assert [dict(r) for r in d.store.db.execute('SELECT * FROM runtime_observations')] == original_observations


def test_explicit_saved_recalculation_changes_denominator_without_acquisition(driver, monkeypatch):
    from gene_annotation_episode.bvbrc_genome_alignment_calculators import calculate_genome_alignment_components
    d = driver
    d.start()
    d.acquire_manifest()
    d.acquire_native()
    original_sheet = deepcopy(d.sheet)
    changed = deepcopy(d.components['calculation_plan'])
    changed['requests'][0]['selection']['denominator'] = 'none'
    def forbidden(*a, **k):
        raise AssertionError('saved recalculation reacquired or reparsed data')
    for name in ('mauve_v4_formats', 'mauve_backbone_formats', 'xmfa_formats'):
        module = importlib.import_module('gene_annotation_episode.' + name)
        for attr in ('parse_mauve_v4', 'parse_mauve_backbone', 'parse_mauve_bbcols', 'parse_mauve_xmfa'):
            if hasattr(module, attr):
                monkeypatch.setattr(module, attr, forbidden)
    monkeypatch.setattr(d.client, 'rpc', forbidden)
    monkeypatch.setattr(d.client, 'download', forbidden)
    changed_components = calculate_genome_alignment_components(d.sheet['data'], calculation_plan=changed)
    coverage = changed_components['outcomes'][0]['measurement']['value']['coverage'][0]
    assert coverage['known_union_bases']['value'] == 690
    assert coverage['coverage_fraction']['value'] is None
    assert d.sheet == original_sheet
    assert original_sheet['components']['outcomes'][0]['measurement']['value']['coverage'][0]['coverage_fraction']['value'] == 690 / 693


def test_latest_partial_recovered_selection_preserves_original_admitted_return(driver, monkeypatch):
    """Controlled overlapping executor selections; no concurrent model claim."""
    d = driver
    d.start()
    d.acquire_manifest()
    args = d.native_arguments()
    _, first_key = d.selection('download', args, context=d.context)
    _, later_key = d.selection('download', args, context=d.context)
    actual_download = d.client.download
    d.client.body = b'FormatVersion\t5\nSequenceCount\t0\n'
    def interrupted(url, *, byte_range=None):
        error = KeyboardInterrupt()
        error.snapshot = actual_download(url, byte_range=byte_range)
        raise error
    monkeypatch.setattr(d.client, 'download', interrupted)
    with pytest.raises(KeyboardInterrupt):
        d.invoke(d.context, 'download', args, later_key)
    later_dir = d.api._manifest(d.context) / 'actions' / digest(later_key)
    assert (later_dir / 'call_response.json').exists()
    original_later_response = _read(later_dir / 'call_response.json')
    monkeypatch.setattr(d.client, 'download', actual_download)
    d.client.body = FILES[d.fmt].read_bytes()
    first = d.invoke(d.context, 'download', args, first_key)
    assert first['status'] == 'completed'
    d.native = d.records.read(first['result']['support_receipt_ref'])
    original_body = deepcopy(d.publication())
    original_form, admission_key, refs = d.admit_numeric()
    old_proof = d.api._completion(d.context)
    assert old_proof['operation_key'] == first_key
    calls = len(d.client.calls)
    later = d.invoke(d.context, 'download', args, later_key)
    assert later['status'] == 'partial' and len(d.client.calls) == calls
    latest = d.publication()
    assert latest['source_ref'] != original_body['source_ref']
    assert latest['publication']['adapter_result']['status'] == 'partial'
    assert latest['publication']['completion_proof'] is None
    assert d.api._completion(d.context) is None
    assert not d.api.verify_completion(d.context, old_proof)
    assert d.api.facts(d.context, {})[MEASUREMENTS][0]['value']['state'] == 'missing'
    assert _read(later_dir / 'call_response.json') == original_later_response
    assert d.api.read_result(original_body['source_ref'], d.context.scope) == original_body
    forbid_saved_science(monkeypatch)
    from test_genome_alignment_saved_structure import scientific_barrier
    scientific_barrier(monkeypatch)
    assert d.family.received_report_facts(d.parent)[MEASUREMENTS] == original_form['fact0']
    assert d.family.received_form_references(d.parent, original_form, d.schema, admission_key) == refs
    assert original_form['fact0'][0]['value']['value']['value'] == 690 / 693
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0

