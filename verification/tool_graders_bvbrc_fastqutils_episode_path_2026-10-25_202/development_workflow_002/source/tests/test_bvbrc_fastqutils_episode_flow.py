"""Real FastqUtils host and shared Workflow with controlled transport/choices.

Native-format records and task/Workspace associations are explicitly synthetic.
Custody, selected calls, publication, parsers, calculators, admission, persistence,
and practical endpoint validation are production objects. No live service runs.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_fastqutils_contracts import make_requested_schema, validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_identity import decode_reference
from gene_annotation_episode.bvbrc_fastqutils_returns import FACT_SOURCES, parent_form_schema, decode_return_value
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.runtime import Workflow, _compile_form
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from bvbrc_proteome_host_fixture import ProteomeDriver, ControlledClient
from bvbrc_minhash_episode_fixture import PUBLICATION
from test_api_bvbrc_appservice import CONFIG, PREFIX, OBJECT_UUID, metadata
from test_bvbrc_appservice_custody import SavedRecords, api_assignment, selector as support_selector
from test_bvbrc_appservice_inputs import NativeClient, receipt_row
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client


FIXTURES = Path(__file__).parent / 'fixtures/bvbrc_fastqutils/integration'
NAMES = ('reads', 'hostile', 'qc')
OUTPUTS = {name: ('/fixture/output/' + name, str(uuid.uuid5(uuid.NAMESPACE_URL,
    'synthetic-fastqutils-host:' + name))) for name in NAMES}


def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text())


def raw(name):
    return (FIXTURES / (name + '.native')).read_bytes()


def configured():
    config = deepcopy(CONFIG)
    config['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID,
        'adapter_version': adapter.ADAPTER_VERSION, 'implementation_sha256': adapter.implementation_sha256()}]
    return config


def declaration(fmt):
    return dict(format=fmt, version=None, mode=None, producer_source_ref=None, transformation_evidence=[])


def query():
    return dict(version='bvbrc_appservice_request_v1', effect_contract='selected_api_effects_v1',
        required_application_id='FastqUtils', parameters=fixture('submitted_parameters'),
        start_parameters={}, definition_inputs=[], input_bindings=[], workspace_targets=[])


def content(store, reference):
    source = store.get(reference)
    value = store.get_artifact(source['artifact_ref'])
    return dict(source_ref=reference, artifact_field='artifact_ref', artifact_ref=source['artifact_ref'],
        sha256=hashlib.sha256(value).hexdigest(), byte_count=len(value))


def supplied_source(store):
    artifact = store.artifact(canonical(fixture('declarations')).encode(), 'application/json')
    source = store.put('source', dict(provider='fastqutils.synthetic.supplied', accession='explicit-declarations',
        uri=None, artifact_ref=artifact, text_ref=artifact, request_ref=None, version=None,
        retrieved_at='2026-10-25T00:00:00+00:00'), origin='tool')
    return content(store, source['id'])


def result_selector(binding, *, fields=None, documents=NAMES):
    parameters = fixture('parameters')
    parameters['documents'] = [row for row in parameters['documents'] if row['document_id'] in documents]
    for index, row in enumerate(parameters['metadata_bindings']):
        row['evidence'] = dict(content=deepcopy(binding), pointer='/declarations/' + str(index))
    selected_form = fixture('requested_form')
    if fields is not None:
        selected_form['fields'] = [row for row in selected_form['fields'] if row['field'] in fields]
    value = support_selector()
    value.update(endpoint='requested_projection', supplied_contents=[],
        supplied_metadata=[deepcopy(row['evidence']) for row in parameters['metadata_bindings']],
        adapter=dict(adapter_id=adapter.ADAPTER_ID, adapter_version=adapter.ADAPTER_VERSION, parameters=parameters),
        requested_schema=make_requested_schema(selected_form),
        requirements=[dict(requirement_id=row['selection']['requirement_id'], role=row['document_id'],
            required=True, declared_format=declaration(row['format']), producer_rule_evidence=None, exact_object=None)
            for row in parameters['documents']])
    return value


def native_values(typed_form):
    values = {}
    for rows in typed_form.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or 'field' not in row:
                continue
            name = decode_reference(row['field'])['pointer'].removeprefix('/facts/')
            kind = row['value']['selection']['target']['kind']
            values[name] = decode_return_value(kind, row['value'])
    return values


def assert_numbers(facts):
    assert [facts[key]['records'][0]['payload']['value'] for key in
        ('read_count', 'gc', 'errors', 'retained')] == [2, 5 / 9, .001, .75]
    assert facts['association']['records'][0]['payload']['state'] == 'unresolved'
    assert facts['population']['records'][0]['payload']['scope'] == 'complete'
    errors = facts['errors']['records'][0]['payload']
    assert errors['meaning'] == 'phred_model_prediction'
    assert errors['encoding_basis']['basis'] == 'explicit_source_bound_declaration'
    assert errors['encoding_basis']['declaration']['basis'] == 'explicit_assumption'
    retained = facts['retained']['records'][0]['payload']
    assert (retained['numerator'], retained['denominator']) == (6, 8)


def save_example(name, values):
    if os.environ.get('FASTQUTILS_EXAMPLE_DIRECTORY'):
        directory = Path(os.environ['FASTQUTILS_EXAMPLE_DIRECTORY']) / name
        directory.mkdir(parents=True, exist_ok=True)
        for key, value in values.items():
            (directory / (key + '.json')).write_text(json.dumps(value, indent=2) + '\n')


class FastqDriver(ProteomeDriver):
    """Reuse generic action recording and typed admission helpers only."""
    def __init__(self, store, directory, *, config=None):
        self.saved, self.store = SavedRecords(store), store
        self.config = configured() if config is None else config
        self.family = ExecutionEpisodes(None, store=store, directory=directory, run_id=self.saved.run_id,
            resources={'selected-api': self.config}, initial_information={},
            tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.api, self.client = self.family.api_execution, ControlledClient()
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.records, self.custody = self.api.appservice.records, self.api.appservice.custody
        self.last_outcome = None

    def start(self, *, fields=None, documents=NAMES):
        self.declarations = supplied_source(self.store)
        self.selected = result_selector(self.declarations, fields=fields, documents=documents)
        self.schema = parent_form_schema(validate_requested_form(self.selected['requested_schema']))
        self.outer_root = self.saved.root
        self.grandparent = self.saved.child(self.outer_root, 'scientific_process', {}, 0, schema=self.schema)
        self.parent = self.saved.child(self.grandparent, 'scientific_process', {}, 0, schema=self.schema)
        self.saved.root = self.parent
        self.saved.own(self.parent, self.declarations['source_ref'], index=1)
        self.query = query()
        launching = launch_assignment({'selected-api': api_assignment(self.query)})
        self.launch = self.saved.child(self.parent, 'launch', launching, 10)
        self.saved.receipts.receive(self.launch.episode_id, self.custody.initial_references(self.launch), kind='initial')
        self.context = self.saved.child(self.launch, 'launch_api', api_assignment(self.query), 0)
        self.api._manifest(self.context)
        prepared = self.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'FastqUtils'}})
        assert self.client.calls == []
        self.client.value = {'id': '123', 'application_id': 'FastqUtils', 'state_code': 'Q'}
        self.handoff = self.call('submit', {'preparation_receipt_ref': prepared['source_ref'], 'input_evidence_refs': []})
        self.freeze_refs(self.launch, self.context, [self.handoff['source_ref']])
        self.freeze_refs(self.parent, self.launch, [self.handoff['source_ref']])
        self.context = self.saved.child(self.parent, 'results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': self.handoff['source_ref'], 'selector': self.selected}, 22, schema=self.schema)
        self.frozen_assignment = deepcopy(plain(self.context.assignment))
        self.api.initialize(self.context)
        return self.context

    def acquire_manifest(self, *, native_task='123', native_parameters=None):
        self.client.value = {'123': {'id': '123', 'application_id': 'FastqUtils', 'state_code': 'C'}}
        self.call('status', {'handoff_ref': self.handoff['source_ref']})
        info = self.call('task_info', {'handoff_ref': self.handoff['source_ref'], 'file': 'job_result_id'})
        obj = {'kind': 'task_info_object', 'receipt_ref': info['source_ref']}
        self.client.value = [[metadata('/fixture/output/manifest', type='job_result', size=None)['native_row']]]
        observed = self.call('workspace_metadata', {'objects': [obj], 'options': {}})
        obj = receipt_row(observed)
        self.client.value = ['https://controlled.invalid/manifest']
        cap = self.call('download_capability', {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None})
        self.client.body = canonical({'id': native_task, 'app': {'id': 'FastqUtils'},
            'parameters': self.query['parameters'] if native_parameters is None else native_parameters,
            'success': 1, 'output_files': [list(OUTPUTS[name]) for name in NAMES]}).encode()
        self.manifest = self.call('download', {'object': obj, 'capability': {'kind': 'acquired',
            'receipt_ref': cap['source_ref'], 'input_index': 0}, 'byte_range': None,
            'requirement_ids': [], 'role': 'task_manifest', 'declared_format': declaration('json')})
        return self.manifest

    def native_arguments(self, name='reads'):
        obj = {'kind': 'manifest_member', 'manifest_receipt_ref': self.manifest['source_ref'], 'output_index': NAMES.index(name)}
        self.client.value = ['https://controlled.invalid/native']
        cap = self.call('download_capability', {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None})
        document = next(row for row in self.selected['adapter']['parameters']['documents'] if row['document_id'] == name)
        self.native_args = {'object': obj, 'capability': {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0},
            'byte_range': None, 'requirement_ids': [document['selection']['requirement_id']],
            'role': name, 'declared_format': declaration(document['format'])}
        return self.native_args

    def acquire_native(self, name='reads', *, data=None, complete=True):
        args = self.native_arguments(name)
        self.client.body, self.client.native_complete = raw(name) if data is None else data, complete
        self.native = self.call('download', args)
        return self.publication()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('controlled FastqUtils verification attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)


@pytest.fixture
def driver(tmp_path):
    with Store(tmp_path / 'state') as store:
        yield FastqDriver(store, tmp_path)


def forbid_science(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved validation repeated acquisition, parsing or scientific calculation')
    names = {
        'bvbrc_fastqutils_bundle_adapter': ('consume_bundle', 'parse_fastqutils_artifact', 'populate_fastqutils_sheet', 'calculate_fastqutils'),
        'bvbrc_fastqutils_native': ('parse_fastqutils_artifact',),
        'bvbrc_fastqutils_sheet': ('populate_fastqutils_sheet',),
        'bvbrc_fastqutils_metadata': ('extract_fastqutils_metadata',),
        'bvbrc_fastqutils_calculators': ('calculate_fastqutils',),
        'bvbrc_fastqutils_fastq_reader': ('parse_fastq',),
        'bvbrc_fastqutils_sam_reader': ('parse_sam',),
        'bvbrc_fastqutils_bam_reader': ('parse_bam',),
        'bvbrc_fastqutils_hostile_reader': ('parse_hostile_json',),
        'bvbrc_fastqutils_fastqc_reader': ('parse_fastqc_data', 'parse_fastqc_html', 'parse_fastqc_zip'),
        'bvbrc_fastqutils_trim_reader': ('parse_trim_galore_report',),
        'bvbrc_fastqutils_pair_report_reader': ('parse_fastq_pair_stderr',),
        'bvbrc_fastqutils_composition': ('calculate_composition',),
        'bvbrc_fastqutils_quality': ('calculate_quality',),
        'bvbrc_fastqutils_mapping': ('calculate_mapping',),
        'bvbrc_fastqutils_retention': ('calculate_retention',),
        'bvbrc_fastqutils_consistency': ('calculate_report_consistency',),
    }
    for module, functions in names.items():
        target = importlib.import_module('gene_annotation_episode.' + module)
        for name in functions:
            monkeypatch.setattr(target, name, forbidden)
    return forbidden


def test_actual_host_all_families_saved_reads_and_two_typed_boundaries(driver, monkeypatch):
    d = driver
    d.start()
    assert d.service.scientific_adapters[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)][0] is adapter
    assert d.handoff['value']['original_task']['submitted_parameters'] == query()['parameters']
    d.acquire_manifest()
    for name in NAMES:
        assert d.api._completion(d.context) is None
        body = d.acquire_native(name)
    assert_numbers(body['publication']['adapter_result']['facts'])
    assert body['publication']['requested_form_status'] == 'satisfied'
    assert d.api._completion(d.context) is not None
    assert plain(d.context.assignment) == d.frozen_assignment
    assert all(row['observed_state'] == 'unknown' for row in d.sheet['stages'])
    assert [row['requested_token'] for row in d.sheet['stages']] == query()['parameters']['recipe']
    for member in body['bundle']['artifacts']:
        assert member['task_association']['task_id'] == '123'
        assert member['workspace_object']['path'] == member['task_association']['output_path']
        assert member['workspace_object']['uuid'] == member['task_association']['output_uuid']
        assert d.store.get_artifact(member['raw_artifact_ref']) == raw(member['role'])
    count = d.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
    forbidden = forbid_science(monkeypatch)
    monkeypatch.setattr(d.client, 'rpc', forbidden)
    monkeypatch.setattr(d.client, 'download', forbidden)
    typed, key, refs = d.admit_numeric()
    forwarded, _, forwarded_refs = d.admit_numeric(to_grandparent=True)
    assert typed == forwarded and refs == forwarded_refs
    assert_numbers(native_values(forwarded))
    assert set(d.family.received_report_facts(d.grandparent)) == set(FACT_SOURCES)
    assert d.family.received_form_references(d.parent, typed, d.schema, key) == refs
    assert d.api.read_result(body['source_ref'], d.context.scope) == body
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == count
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
    binding = body['publication']['adapter_result']['sheet_content']
    path = d.store.path / 'artifacts' / binding['sha256'][:2] / binding['sha256']
    retained_bytes = path.read_bytes()
    try:
        path.write_bytes(retained_bytes + b' ')
        with pytest.raises(ValueError, match='artifact_digest_mismatch'):
            d.api.fastqutils_returns.facts(d.context, d.schema)
    finally:
        path.write_bytes(retained_bytes)
    for mutation in ('value', 'selector', 'source'):
        altered = deepcopy(typed)
        row = altered['facts_0'][0]
        if mutation == 'value':
            row['value']['records'][0]['payload']['value'] = 900
        elif mutation == 'selector':
            row['value']['selection']['expected_cardinality'] = 2
        else:
            row['source_ref'] = d.saved.source(b'unreceived')['source_ref']
        with pytest.raises(ValueError):
            d.family.validate_received_report(d.context, altered, d.schema)
    save_example('host', dict(publication=body, sheet=d.sheet, components=d.components, typed_form=typed,
        forwarded_form=forwarded, submission=d.handoff, assignment=d.frozen_assignment,
        commands=d.client.calls, qualification='controlled transport and manually saved choices; no method_loop in this host case'))


def test_partial_transfer_keeps_prefix_and_cannot_complete_original_available_request(driver):
    d = driver
    d.start(fields=('read_count', 'requirements', 'status'), documents=('reads',))
    d.acquire_manifest()
    body = d.acquire_native(data=b'@first\nACGT\n+\nIIII\n@second\nA', complete=False)
    fact = body['publication']['adapter_result']['facts']['read_count']
    assert fact['records'][0]['payload']['value'] == 1
    assert fact['records'][0]['state'] == 'partial'
    assert fact['state'] == 'missing_value' and fact['satisfied'] is False
    assert body['publication']['result_record_refs'] == [body['source_ref']]
    assert all(row['transfer']['object_complete'] != 'yes' for row in body['bundle']['artifacts'])
    assert body['publication']['requested_form_status'] == 'partial'
    assert d.api._completion(d.context) is None
    typed, _, _ = d.admit_numeric()
    assert native_values(typed)['read_count'] == fact
    save_example('partial', dict(publication=body, sheet=d.sheet, components=d.components, typed_form=typed))


def test_wrong_manifest_task_rejected_before_native_download(driver):
    d = driver
    d.start(fields=('read_count',), documents=('reads',))
    d.acquire_manifest(native_task='wrong-task')
    args = dict(objects=[dict(kind='manifest_member', manifest_receipt_ref=d.manifest['source_ref'], output_index=0)],
        generation=0, predecessor_receipt_ref=None)
    calls = deepcopy(d.client.calls)
    context, key = d.selection('download_capability', args)
    outcome = d.invoke(context, 'download_capability', args, key)
    assert outcome['status'] == 'invalid' and outcome['feedback']['code'] == 'task_manifest_mismatch'
    assert d.client.calls == calls


@pytest.mark.parametrize('mutation', ['selector', 'resource', 'original_parameters', 'commission', 'source', 'binding'])
def test_actual_host_rejects_changed_original_inputs_and_unpossessed_metadata(driver, mutation):
    d = driver
    d.start(fields=('read_count',), documents=('reads',))
    if mutation == 'selector':
        altered = deepcopy(d.frozen_assignment)
        altered['selector']['adapter']['parameters']['analysis_id'] = 'changed'
        with pytest.raises(ValueError):
            d.api.initialize(replace(d.context, assignment=altered))
    elif mutation in {'resource', 'original_parameters'}:
        original = d.custody.context(d.launch.episode_id)
        row = d.saved.journal.row('runtime_actions', original.episode_id, 0)
        selected_value = json.loads(row['action'])
        if mutation == 'resource':
            selected_value['assignment']['resource_id'] = 'unselected'
        else:
            selected_value['assignment']['request']['parameters']['recipe'] = ['FASTQC']
        d.saved.journal.save('runtime_actions', {**row, 'action': canonical(selected_value)})
        with pytest.raises(ValueError):
            d.api.read_target(d.handoff['source_ref'], d.context.scope)
    elif mutation == 'commission':
        row = d.saved.journal.row('runtime_actions', d.parent.episode_id, 22)
        selected_value = json.loads(row['action'])
        selected_value['assignment']['selector']['adapter']['parameters']['analysis_id'] = 'changed'
        d.saved.journal.save('runtime_actions', {**row, 'action': canonical(selected_value)})
        with pytest.raises(ValueError):
            d.api.initialize(d.context)
    elif mutation == 'source':
        d.store.db.execute('DELETE FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=1',
            (d.parent.run_id, d.parent.episode_id))
        with pytest.raises(ValueError):
            d.api.initialize(d.context)
    else:
        altered = {**d.declarations, 'sha256': '0' * 64}
        with pytest.raises(ValueError):
            d.custody.content(d.context, altered)


@pytest.mark.parametrize('pin', ['missing', 'unknown', 'mismatch'])
def test_unconfigured_or_wrong_pin_does_not_advertise_scientific_tool(tmp_path, pin):
    config = configured()
    if pin == 'missing': config['scientific_adapters'] = []
    elif pin == 'unknown': config['scientific_adapters'][0]['adapter_version'] = 'unknown'
    else: config['scientific_adapters'][0]['implementation_sha256'] = '0' * 64
    with Store(tmp_path / 'state') as store:
        if pin == 'mismatch':
            with pytest.raises(ValueError, match='implementation_conflict'):
                FastqDriver(store, tmp_path, config=config)
        else:
            d = FastqDriver(store, tmp_path, config=config)
            assert 'bvbrc.fastqutils' not in {entry['name'] for entry in d.family.resource_tool_contracts()}


def test_later_interrupted_partial_publication_supersedes_current_but_preserves_admitted_history(driver, monkeypatch):
    d = driver
    d.start(fields=('read_count',), documents=('reads',))
    d.acquire_manifest()
    args = d.native_arguments()
    _, first_key = d.selection('download', args)
    _, later_key = d.selection('download', args)
    download = d.client.download
    d.client.body, d.client.native_complete = b'@r\nACGT\n+\nIIII\n@bad\nA', False
    def interrupted(url, *, byte_range=None):
        error = KeyboardInterrupt()
        error.snapshot = download(url, byte_range=byte_range)
        raise error
    monkeypatch.setattr(d.client, 'download', interrupted)
    with pytest.raises(KeyboardInterrupt):
        d.invoke(d.context, 'download', args, later_key)
    directory = d.api._manifest(d.context) / 'actions' / digest(later_key)
    snapshot = _read(directory / 'call_response.json')
    monkeypatch.setattr(d.client, 'download', download)
    d.client.body, d.client.native_complete = raw('reads'), True
    first = d.invoke(d.context, 'download', args, first_key)
    assert first['status'] == 'completed'
    original = deepcopy(d.publication())
    typed, key, refs = d.admit_numeric()
    proof = d.api._completion(d.context)
    calls = deepcopy(d.client.calls)
    later = d.invoke(d.context, 'download', args, later_key)
    assert later['status'] == 'partial' and d.client.calls == calls
    current = d.publication()
    assert current['publication']['completion_proof'] is None
    assert d.api._completion(d.context) is None and not d.api.verify_completion(d.context, proof)
    facts = d.api.fastqutils_returns.facts(d.context, d.schema)
    assert facts[FACT_SOURCES[0]][0]['source_ref'] == current['source_ref'] != original['source_ref']
    assert not facts[FACT_SOURCES[0]][0]['value']['satisfied']
    assert _read(directory / 'call_response.json') == snapshot
    forbidden = forbid_science(monkeypatch)
    monkeypatch.setattr(d.client, 'rpc', forbidden)
    monkeypatch.setattr(d.client, 'download', forbidden)
    assert d.api.read_result(original['source_ref'], d.context.scope) == original
    assert d.family.received_report_facts(d.parent)[FACT_SOURCES[0]] == next(iter(typed.values()))
    assert d.family.received_form_references(d.parent, typed, d.schema, key) == refs
    assert native_values(typed)['read_count']['records'][0]['payload']['value'] == 2
    save_example('history', dict(original_publication=original, latest_publication=current, admitted_original=typed))


def test_actual_selected_tool_shared_workflow_and_original_typed_root_return(tmp_path, monkeypatch):
    request = query()
    assignment = api_assignment(request)
    manifest_path = '/fixture/output/manifest'
    manifest = {'id': '123', 'app': {'id': 'FastqUtils'}, 'parameters': deepcopy(request['parameters']),
        'success': 1, 'output_files': [list(OUTPUTS[name]) for name in NAMES]}

    class Responses(NativeClient):
        def rpc(self, command):
            method = command['method']
            if method == 'AppService.start_app2':
                assert command['params'] == ['FastqUtils', request['parameters'], {}]
                self.value = {'id': '123', 'application_id': 'FastqUtils', 'state_code': 'Q'}
            elif method == 'AppService.query_tasks':
                self.value = {'123': {'id': '123', 'application_id': 'FastqUtils', 'state_code': 'C'}}
            elif method == 'Workspace.get':
                self.value = [[metadata(manifest_path, type='job_result', size=len(canonical(manifest).encode()))['native_row']]]
            elif method == 'Workspace.get_download_url':
                obj, = command['params'][0]['objects']
                name = 'manifest' if obj in {manifest_path, OBJECT_UUID} else next(
                    name for name, identifiers in OUTPUTS.items() if obj in identifiers)
                self.value = ['https://controlled.invalid/' + name]
            else:
                raise AssertionError(command)
            return super().rpc(command)

        def download(self, url, *, byte_range=None):
            name = url.rsplit('/', 1)[-1]
            self.body = canonical(manifest).encode() if name == 'manifest' else raw(name)
            return super().download(url, byte_range=byte_range)

    client = Responses()
    constructor = BVBRCAppServiceService.__init__
    def transport(self, *args, **kwargs):
        constructor(self, *args, **kwargs)
        self.client = client
    monkeypatch.setattr(BVBRCAppServiceService, '__init__', transport)

    # Synthetic parent stopping is controlled. All execution endpoints retain
    # the configured ordinary PracticalYieldEstimator and verified proof.
    def controllers(path, initial):
        role = path[-1][0]
        def estimate(history, parameters, contexts):
            count = 1 if role == 'annotation' else 3
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                parameters, {'fixture': 'scientific_parent_continuation_only'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if role in {'annotation', 'scientific_process'} else None)

    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        supplied_material = store.register_material(data=canonical(fixture('declarations')).encode(),
            name='SYNTHETIC-fastqutils-supplied-declarations.json', format='text', use='evidence')
        supplied = content(store, supplied_material['source_ref'])
        selected_selector = result_selector(supplied)
        factory = ExecutionServiceFactory({'selected-api': configured()}, {}, 2, 3, .5)
        tools = ToolRegistry(store, clients=Client())
        run_id, run_directory = 'fastqutils-shared-workflow', tmp_path / 'run'
        application = factory(store, run_id=run_id, directory=run_directory, tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
        parent_schema = parent_form_schema(validate_requested_form(selected_selector['requested_schema']))
        result_schema = form('execution_result_refs')
        result_schema['properties'].update(parent_schema['properties'])
        result_schema['required'].extend(parent_schema['required'])
        handoff_schema = form('execution_handoff_refs')
        launching = launch_assignment({'selected-api': assignment})

        class Choices:
            def __init__(self):
                self.counts, self.calls = {}, []

            def last(self, episode_id):
                row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL '
                    'ORDER BY decision_index DESC LIMIT 1', (run_id, episode_id)).fetchone()
                return json.loads(row['result'])['result']

            async def complete(self, episode_id, role, instructions, current, schema):
                assert current.get('feedback') is None, current.get('feedback')
                count = self.counts[episode_id] = self.counts.get(episode_id, 0) + 1
                self.calls.append((episode_id, deepcopy(current)))
                execution = current.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    assert count == 1
                    return child('launch_api', assignment, scope, handoff_schema)
                if execution.get('version') == 'api_service_assignment_v1':
                    if count == 1:
                        return selected(PREFIX + 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'FastqUtils'}})
                    assert count == 2
                    return selected(PREFIX + 'submit', {'preparation_receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
                if execution.get('version') == 'execution_results_assignment_v1':
                    if count == 1:
                        return selected(PREFIX + 'status', {'handoff_ref': execution['handoff_ref']})
                    if count == 2:
                        return selected(PREFIX + 'task_info', {'handoff_ref': execution['handoff_ref'], 'file': 'job_result_id'})
                    if count == 3:
                        return selected(PREFIX + 'workspace_metadata', {'objects': [{'kind': 'task_info_object',
                            'receipt_ref': self.last(episode_id)['support_receipt_ref']}], 'options': {}})
                    if count == 4:
                        self.manifest_object = {'kind': 'receipt_row', 'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'row_pointer': '/result/0/0'}
                        return selected(PREFIX + 'download_capability', {'objects': [self.manifest_object], 'generation': 0, 'predecessor_receipt_ref': None})
                    if count == 5:
                        return selected(PREFIX + 'download', {'object': self.manifest_object,
                            'capability': {'kind': 'acquired', 'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0},
                            'byte_range': None, 'requirement_ids': [], 'role': 'task_manifest', 'declared_format': declaration('json')})
                    if count == 6:
                        self.manifest_ref = self.last(episode_id)['support_receipt_ref']
                    name = NAMES[(count - 6) // 2]
                    obj = {'kind': 'manifest_member', 'manifest_receipt_ref': self.manifest_ref, 'output_index': NAMES.index(name)}
                    if count % 2 == 0:
                        return selected(PREFIX + 'download_capability', {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None})
                    document = next(row for row in selected_selector['adapter']['parameters']['documents'] if row['document_id'] == name)
                    return selected(PREFIX + 'download', {'object': obj, 'capability': {'kind': 'acquired',
                        'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0},
                        'byte_range': None, 'requirement_ids': [document['selection']['requirement_id']],
                        'role': name, 'declared_format': declaration(document['format'])})
                if 'scientific_process' in current:
                    if count == 1:
                        return selected('material.parse', {'material_ref': supplied_material['id'], 'format': 'text'})
                    if count == 2:
                        return child('launch', launching, scope, handoff_schema)
                    assert count == 3
                    handoff, = current['child_reports'][-1]['references']
                    return child('results', {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff,
                        'selector': selected_selector}, scope, result_schema)
                assert count == 1
                scientific = {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': library.reference('A101'),
                    'thought_pattern': library.reference('P01'), 'child_tool_info': [
                        {'name': 'bvbrc.fastqutils', 'resources': 'api'}, {'name': 'material.parse', 'resources': 'local'}]},
                    'evidence_refs': [target], 'constraints': {},
                    'context': {'supplied_sequence': 'MACDEFGH', 'molecule': 'protein', 'complete': True,
                        'label_is_public_identity': False, 'supplied_material_refs': [supplied_material['id']]}}
                return child('scientific_process', scientific, scope, parent_schema)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, tools, choices, run_directory, run_id, controller_factory=controllers,
            project_credit=lambda *_: 0, episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
            annotation_child_roles=('scientific_process',), episode_record_receipts=True,
            initial_known_record_refs=[])
        for grain in ('results', 'scientific_process', 'annotation'):
            assert set(FACT_SOURCES) <= workflow.report_sources(grain).keys()
            assert _compile_form(json.dumps(parent_schema), workflow.report_sources(grain)) == parent_schema
        episode = workflow.build('annotation', 'root', 'Return the requested read counts, composition, quality-model values and report retention with their populations', scope)
        async def execute():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record
        closed = asyncio.run(execute())
        archived = json.loads(''.join(iter_json(closed.as_record())))
        science = archived['units'][0]['child']
        launch_record, results_record = science['units'][1]['child'], science['units'][2]['child']
        api_record = launch_record['units'][0]['child']
        returned = json.loads(workflow.journal.row('runtime_forms', results_record['episode_id'])['form'])
        forwarded = json.loads(workflow.journal.row('runtime_forms', science['episode_id'])['form'])
        assert forwarded == {name: returned[name] for name in parent_schema['properties']}
        assert returned['completed']
        assert_numbers(native_values(forwarded))
        records = (archived, science, launch_record, api_record, results_record)
        assert tuple(record['units_consumed'] for record in records) == (1, 3, 1, 2, 11)
        counts = []
        for record in records:
            actions, observations = [store.db.execute('SELECT COUNT(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                (run_id, record['episode_id'])).fetchone()[0] for table in ('runtime_actions', 'runtime_observations')]
            assert actions == observations == record['units_consumed'] == choices.counts[record['episode_id']]
            counts.append(dict(episode_id=record['episode_id'], role=record['path'][-1][0], actions=actions,
                observations=observations, controller=record['controller_state']))
        for record in (launch_record, api_record, results_record):
            assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        family = workflow.episode_bindings.for_role('results')
        api = family.api_execution
        scientific_context = api.appservice.custody.context(science['episode_id'])
        assert api.appservice.custody.possession(scientific_context, supplied['source_ref']) == 'own_completed_action'
        parse_action = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0',
            (run_id, science['episode_id'])).fetchone()
        parsed = json.loads(parse_action['result'])
        assert supplied['source_ref'] in parsed['record_refs']
        attempt = parsed['result']['parse_attempt']
        assert (attempt['status'], attempt['code'], attempt['source_ref']) == (
            'completed', 'retained_without_sequence_projection', supplied['source_ref'])
        assert store.get(supplied['source_ref'])['origin'] == 'caller'
        assert store.get_artifact(supplied['artifact_ref']) == canonical(fixture('declarations')).encode()
        result_ref = next(iter(forwarded.values()))[0]['source_ref']
        body = api.read_result(result_ref, scope)
        root_attempt = store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=0',
            (run_id, archived['episode_id'])).fetchone()
        assert root_attempt['failure'] is None and root_attempt['child_episode_id'] == science['episode_id']
        assert json.loads(root_attempt['form']) == forwarded
        assert json.loads(root_attempt['contract'])['measurements']['schema'] == parent_schema
        assert workflow.catalog(scope, source=episode.source) == []
        assert store.count('annotation') == 0
        saved = body['publication']['adapter_result']
        sheet = api.appservice.publications.read_content_source(saved['sheet_content']['source_ref'], scope)
        components = api.appservice.publications.read_content_source(saved['components_content']['source_ref'], scope)
        save_example('workflow', dict(publication=body, sheet=sheet, components=components, typed_form=returned,
            root_received_form=forwarded, root_admission=dict(root_attempt), counts=counts, archive=archived,
            supplied_material=supplied_material, parse_action=parsed,
            choices=choices.calls, commands=client.calls, qualification='actual shared method_loop; controlled choices and transport; no live service or model'))
