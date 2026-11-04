"""Real AppService custody/provider/returns with controlled transport and choices.

The retained producer output uses synthetic records. Its association with task
123 is constructed for this test. No live service or configured model is used.
"""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_comparative_systems_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_comparative_systems_fact_contracts import requested_selection
from gene_annotation_episode.bvbrc_comparative_systems_returns import FACT_SOURCES, parent_form_schema
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from test_api_bvbrc_appservice import CONFIG, metadata
from test_bvbrc_appservice_custody import SavedRecords, api_assignment, selector as support_selector
from test_bvbrc_appservice_inputs import receipt_row
from bvbrc_proteome_host_fixture import ProteomeDriver, ControlledClient, OUTPUT_UUID

FIXTURES = Path(__file__).parent / 'fixtures' / 'bvbrc_comparative_systems_integration'
FORMAT = 'comparative_systems_families_json_v1'


def parameters():
    return json.loads((FIXTURES / 'parameters.json').read_text())


def declaration(fmt=FORMAT):
    return {'format': fmt, 'version': None, 'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}


def field(name, selector, cardinality=1, availability='typed_state'):
    return {'field_id': name, 'selector': selector, 'expected_cardinality': cardinality, 'availability_requirement': availability}


def requested_form(all_families=True):
    entity = parameters()['calculation_parameters']['requests'][0]['entity']
    rows = [field('occurrences', {'kind': 'measurement', 'view_id': 'plfam', 'entity': entity,
              'native_field': 'reported_feature_occurrences'}),
            field('occupancy', {'kind': 'ratio', 'component_id': 'family_occupancy'})]
    if all_families:
        rows += [field('population', {'kind': 'population', 'population_id': 'families_native_genomes'}),
            field('member', {'kind': 'membership', 'entity': entity, 'population_id': 'families_native_genomes',
                'genome_id': '1.1', 'member_id': 'PLF_TEST'}),
            field('requirements', {'kind': 'requirement', 'required_input_role': 'native_document'}, cardinality=0),
            field('qualification', {'kind': 'qualification', 'code': 'producer_version_unverified'}, cardinality=4),
            field('status', {'kind': 'request_status'})]
    return adapter.requested_form_schema({'version': 'bvbrc_comparative_systems_requested_selection_v1', 'fields': rows})


def result_selector(form=None):
    value = support_selector()
    value.update(endpoint='requested_projection', supplied_contents=[], supplied_metadata=[],
        adapter={'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION, 'parameters': parameters()},
        requested_schema=requested_form() if form is None else form,
        requirements=[{'requirement_id': 'native', 'role': 'family_summary', 'required': True,
            'declared_format': declaration(), 'producer_rule_evidence': None, 'exact_object': None}])
    return value


def query():
    return {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1',
        'required_application_id': 'ComparativeSystems', 'parameters': {
            'genome_ids': ['1.1', '2.1', '3.1', '1.1'], 'genome_groups': [],
            'output_path': '/controlled/comparative', 'output_file': 'selected'},
        'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}


class ComparativeDriver(ProteomeDriver):
    """Reuse only generic saved-record/transport/admission test helpers."""
    def __init__(self, store, directory, *, resources=None):
        self.saved, self.store = SavedRecords(store), store
        self.config = deepcopy(CONFIG)
        self.config['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID,
            'adapter_version': adapter.ADAPTER_VERSION, 'implementation_sha256': adapter.implementation_sha256()}]
        self.family = ExecutionEpisodes(None, store=store, directory=directory, run_id=self.saved.run_id,
            resources={'selected-api': self.config, **(resources or {})}, initial_information={},
            tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.api, self.client = self.family.api_execution, ControlledClient()
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.records, self.custody = self.api.appservice.records, self.api.appservice.custody
        self.last_outcome = None

    def start(self, *, form=None, selected=None, prepare_parent=None):
        self.fmt = FORMAT
        self.selected = result_selector(form) if selected is None else deepcopy(selected)
        self.schema = parent_form_schema(requested_selection(self.selected['requested_schema']))
        self.outer_root = self.saved.root
        self.grandparent = self.saved.child(self.outer_root, 'scientific_process', {}, 0, schema=self.schema)
        self.parent = self.saved.child(self.grandparent, 'scientific_process', {}, 0, schema=self.schema)
        self.saved.root = self.parent
        self.query = query()
        if prepare_parent is not None:
            prepare_parent(self)
        launching = {'version': 'execution_launch_assignment_v1',
            'requests': {'selected-api': api_assignment(self.query)}, 'immutable_input_versions': [],
            'constraints': {'allowed_kinds': ['api']}}
        self.launch = self.saved.child(self.parent, 'launch', launching, 10)
        self.saved.receipts.receive(self.launch.episode_id, self.custody.initial_references(self.launch), kind='initial')
        self.context = self.saved.child(self.launch, 'launch_api', api_assignment(self.query), 0)
        self.api._manifest(self.context)
        preparation = self.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'ComparativeSystems'}})
        self.client.value = {'id': '123', 'application_id': 'ComparativeSystems', 'state_code': 'Q'}
        self.handoff = self.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []})
        references = [self.handoff['source_ref']]
        self.freeze_refs(self.launch, self.context, references)
        self.freeze_refs(self.parent, self.launch, references)
        self.support = self.saved.child(self.parent, 'results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': self.handoff['source_ref'], 'selector': support_selector()}, 20)
        self.api.initialize(self.support)
        self.client.value = {'123': {'id': '123', 'application_id': 'ComparativeSystems', 'state_code': 'C'}}
        self.status = self.call('status', {'handoff_ref': self.handoff['source_ref']}, context=self.support)
        self.info = self.call('task_info', {'handoff_ref': self.handoff['source_ref'], 'file': 'job_result_id'}, context=self.support)
        self.freeze_refs(self.parent, self.support, [self.info['source_ref']])
        self.selected['supplied_metadata'].append({'content': self.content(self.info['source_ref']), 'pointer': '/value'})
        self.context = self.saved.child(self.parent, 'results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': self.handoff['source_ref'], 'selector': self.selected}, 22, schema=self.schema)
        self.frozen_assignment = deepcopy(plain(self.context.assignment))
        self.api.initialize(self.context)
        return self.context

    def acquire_manifest(self, *, native_task='123'):
        obj = {'kind': 'task_info_object', 'receipt_ref': self.info['source_ref']}
        self.client.value = [[metadata('/controlled/comparative/manifest', type='job_result', size=None)['native_row']]]
        observed = self.call('workspace_metadata', {'objects': [obj], 'options': {}}, context=self.context)
        obj = receipt_row(observed)
        self.client.value = ['https://controlled.invalid/manifest']
        cap = self.call('download_capability', {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None}, context=self.context)
        self.client.body = canonical({'id': native_task, 'app': {'id': 'ComparativeSystems'},
            'parameters': deepcopy(self.query['parameters']), 'success': 1,
            'output_files': [['/controlled/comparative/native', OUTPUT_UUID]]}).encode()
        self.manifest = self.call('download', {'object': obj, 'capability': {'kind': 'acquired',
            'receipt_ref': cap['source_ref'], 'input_index': 0}, 'byte_range': None,
            'requirement_ids': [], 'role': 'task_manifest', 'declared_format': declaration('json')}, context=self.context)
        return self.manifest

    def native_arguments(self):
        obj = {'kind': 'manifest_member', 'manifest_receipt_ref': self.manifest['source_ref'], 'output_index': 0}
        self.client.value = ['https://controlled.invalid/native']
        cap = self.call('download_capability', {'objects': [obj], 'generation': 0, 'predecessor_receipt_ref': None}, context=self.context)
        self.native_args = {'object': obj, 'capability': {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0},
            'byte_range': None, 'requirement_ids': ['native'], 'role': 'family_summary', 'declared_format': declaration()}
        return self.native_args

    def acquire_native(self, *, raw=None):
        args = self.native_arguments()
        self.client.body = (FIXTURES / 'families.json').read_bytes() if raw is None else raw
        self.native = self.call('download', args, context=self.context)
        return self.publication()


@pytest.fixture
def driver(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('controlled ComparativeSystems verification attempted live network')
    monkeypatch.setattr('socket.create_connection', forbidden)
    with Store(tmp_path / 'state') as store:
        yield ComparativeDriver(store, tmp_path)


def forbid_science(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('saved read repeated parsing/calculation/acquisition/model work')
    for module, names in {
        'bvbrc_comparative_systems_bundle_adapter': ['consume_bundle'],
        'bvbrc_comparative_systems_bundle_resolution': ['consume_bundle', 'parse_comparative_systems_document',
            'build_comparative_systems_sheet', 'extract_comparative_systems_data_inputs', 'calculate_comparative_systems_components'],
        'bvbrc_comparative_systems_native': ['parse_comparative_systems_document'],
        'bvbrc_comparative_systems_sheet': ['build_comparative_systems_sheet'],
        'bvbrc_comparative_systems_data_inputs': ['extract_comparative_systems_data_inputs'],
        'bvbrc_comparative_systems_calculators': ['calculate_comparative_systems_components'],
    }.items():
        target = importlib.import_module('gene_annotation_episode.' + module)
        for name in names:
            monkeypatch.setattr(target, name, forbidden)
    return forbidden


def test_actual_preparation_task_manifest_provider_and_two_parent_boundaries(driver, monkeypatch):
    d = driver
    d.start()
    assert d.handoff['value']['original_task']['submitted_parameters'] == query()['parameters']
    d.acquire_manifest()
    assert d.api._completion(d.context) is None
    body = d.acquire_native()
    facts = body['publication']['adapter_result']['facts']
    assert facts['occurrences']['values'][0]['value'] == 3
    ratio = facts['occupancy']['values'][0]
    assert (ratio['numerator']['value'], ratio['denominator']['value'], ratio['output']['value']) == (2, 3, 2/3)
    assert facts['member']['values'][0]['presence_state'] == 'recorded_positive'
    assert len(facts['qualification']['values']) == 4
    assert facts['requirements']['values'] == []
    assert body['publication']['requested_form_status'] == 'satisfied'
    assert d.api._completion(d.context) is not None
    assert d.sheet['original_request']['genome_ids'] == ['1.1', '2.1', '3.1', '1.1']
    assert d.sheet['original_request']['genome_groups'] == []
    assert d.sheet['original_request']['task_ref'] == d.handoff['source_ref']
    assert d.sheet['source_documents'][0]['producer_evidence_id'] is None
    assert d.components['version'] == 'bvbrc_comparative_systems_published_components_v2'
    assert d.components['calculations']['components'][2]['value']['value'] == pytest.approx(.4082482904638631)
    assert d.components['failure_context'] == {'retained_requirements': [], 'retained_diagnostics': [], 'failure_status': None}
    before = d.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
    forbidden = forbid_science(monkeypatch)
    monkeypatch.setattr(d.client, 'rpc', forbidden)
    monkeypatch.setattr(d.client, 'download', forbidden)
    form, _, refs = d.admit_numeric()
    forwarded, _, forwarded_refs = d.admit_numeric(to_grandparent=True)
    assert forwarded == form and set(refs) == set(forwarded_refs)
    assert set(d.family.received_report_facts(d.grandparent)) == set(FACT_SOURCES)
    assert d.api.read_result(body['source_ref'], d.context.scope) == body
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == before
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


import asyncio
from method_loop.archive import iter_json
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow, _compile_form
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.tools import ToolRegistry
from bvbrc_minhash_episode_fixture import PUBLICATION
from test_api_bvbrc_appservice import PREFIX, OBJECT_UUID
from test_bvbrc_appservice_inputs import NativeClient
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client


def test_actual_selected_tool_shared_workflow_native_publication_and_typed_parent_return(tmp_path, monkeypatch):
    selected_selector = result_selector()
    assignment = api_assignment(query())
    request = assignment['request']
    manifest_path, output_path = '/controlled/comparative/manifest', '/controlled/comparative/native'
    output_uuid = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    manifest = {'id': '123', 'app': {'id': 'ComparativeSystems'}, 'parameters': deepcopy(request['parameters']),
        'success': 1, 'output_files': [[output_path, output_uuid]]}

    class Responses(NativeClient):
        def rpc(self, command):
            method = command['method']
            if method == 'AppService.start_app2':
                assert command['params'] == ['ComparativeSystems', request['parameters'], {}]
                self.value = {'id': '123', 'application_id': 'ComparativeSystems', 'state_code': 'Q'}
            elif method == 'AppService.query_tasks':
                self.value = {'123': {'id': '123', 'application_id': 'ComparativeSystems', 'state_code': 'C'}}
            elif method == 'Workspace.get':
                self.value = [[metadata(manifest_path, type='job_result', size=len(canonical(manifest).encode()))['native_row']]]
            elif method == 'Workspace.get_download_url':
                obj, = command['params'][0]['objects']
                self.value = ['https://controlled.invalid/' + ('manifest' if obj in {manifest_path, OBJECT_UUID} else 'native')]
            else: raise AssertionError(command)
            return super().rpc(command)

        def download(self, url, *, byte_range=None):
            self.body = canonical(manifest).encode() if url.endswith('/manifest') else (FIXTURES / 'families.json').read_bytes()
            return super().download(url, byte_range=byte_range)

    client = Responses()
    constructor = BVBRCAppServiceService.__init__
    def configured(self, *args, **kwargs):
        constructor(self, *args, **kwargs)
        self.client = client
    monkeypatch.setattr(BVBRCAppServiceService, '__init__', configured)
    def forbidden(*args, **kwargs): raise AssertionError('controlled Workflow attempted live network')
    monkeypatch.setattr('socket.create_connection', forbidden)

    # Only synthetic scientific/root continuation is fixture-controlled. The
    # real API, launch and results endpoints use their ordinary completion rule.
    def controllers(path, initial):
        role = path[-1][0]
        def estimate(history, parameters, contexts):
            count = 1 if role == 'annotation' else 2
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                parameters, {'fixture': 'scientific_parent_continuation_only'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if role in {'annotation', 'scientific_process'} else None)

    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        config = deepcopy(CONFIG)
        config['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
            'implementation_sha256': adapter.implementation_sha256()}]
        factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)
        tools = ToolRegistry(store, clients=Client())
        run_id, run_directory = 'comparative-shared-workflow', tmp_path / 'run'
        application = factory(store, run_id=run_id, directory=run_directory, tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
        parent_schema = parent_form_schema(requested_selection(selected_selector['requested_schema']))
        result_schema = form('execution_result_refs')
        result_schema['properties'].update(parent_schema['properties'])
        result_schema['required'].extend(parent_schema['required'])
        handoff_schema = form('execution_handoff_refs')
        launching = launch_assignment({'selected-api': assignment})

        class Choices:
            def __init__(self): self.counts, self.calls = {}, []
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
                    if count == 1: return selected(PREFIX + 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'ComparativeSystems'}})
                    assert count == 2
                    return selected(PREFIX + 'submit', {'preparation_receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
                if execution.get('version') == 'execution_results_assignment_v1':
                    if count == 1: return selected(PREFIX + 'status', {'handoff_ref': execution['handoff_ref']})
                    if count == 2: return selected(PREFIX + 'task_info', {'handoff_ref': execution['handoff_ref'], 'file': 'job_result_id'})
                    if count == 3: return selected(PREFIX + 'workspace_metadata', {'objects': [{'kind': 'task_info_object',
                        'receipt_ref': self.last(episode_id)['support_receipt_ref']}], 'options': {}})
                    if count == 4:
                        self.manifest_object = {'kind': 'receipt_row', 'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'row_pointer': '/result/0/0'}
                        return selected(PREFIX + 'download_capability', {'objects': [self.manifest_object], 'generation': 0, 'predecessor_receipt_ref': None})
                    if count == 5: return selected(PREFIX + 'download', {'object': self.manifest_object,
                        'capability': {'kind': 'acquired', 'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0},
                        'byte_range': None, 'requirement_ids': [], 'role': 'task_manifest', 'declared_format': {
                            'format': 'json', 'version': None, 'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}})
                    if count == 6:
                        self.manifest_ref = self.last(episode_id)['support_receipt_ref']
                        return selected(PREFIX + 'download_capability', {'objects': [{'kind': 'manifest_member',
                            'manifest_receipt_ref': self.manifest_ref, 'output_index': 0}], 'generation': 0, 'predecessor_receipt_ref': None})
                    assert count == 7
                    return selected(PREFIX + 'download', {'object': {'kind': 'manifest_member', 'manifest_receipt_ref': self.manifest_ref, 'output_index': 0},
                        'capability': {'kind': 'acquired', 'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0},
                        'byte_range': None, 'requirement_ids': ['native'], 'role': 'family_summary',
                        'declared_format': declaration()})
                if 'scientific_process' in current:
                    if count == 1: return child('launch', launching, scope, handoff_schema)
                    assert count == 2
                    handoff, = current['child_reports'][-1]['references']
                    return child('results', {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff,
                        'selector': selected_selector}, scope, result_schema)
                assert count == 1
                scientific = {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': library.reference('A101'),
                    'thought_pattern': library.reference('P01'), 'child_tool_info': [{'name': 'bvbrc.comparative_systems', 'resources': 'api'}]},
                    'evidence_refs': [target], 'constraints': {}, 'context': {'supplied_sequence': 'MACDEFGH', 'molecule': 'protein',
                        'complete': True, 'label_is_public_identity': False}}
                return child('scientific_process', scientific, scope, parent_schema)
            async def release(self, episode_id): pass

        choices = Choices()
        workflow = Workflow(store, tools, choices, run_directory, run_id, controller_factory=controllers,
            project_credit=lambda *_: 0, episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
            annotation_child_roles=('scientific_process',), episode_record_receipts=True, initial_known_record_refs=[])
        for grain in ('results', 'scientific_process', 'annotation'):
            assert set(FACT_SOURCES) <= workflow.report_sources(grain).keys()
            assert _compile_form(json.dumps(parent_schema), workflow.report_sources(grain)) == parent_schema
        episode = workflow.build('annotation', 'root', 'Return the requested stored ComparativeSystems measurements and their populations', scope)
        async def execute():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record
        closed = asyncio.run(execute())
        archived = json.loads(''.join(iter_json(closed.as_record())))
        science = archived['units'][0]['child']
        launch_record, results_record = science['units'][0]['child'], science['units'][1]['child']
        api_record = launch_record['units'][0]['child']
        returned = json.loads(workflow.journal.row('runtime_forms', results_record['episode_id'])['form'])
        forwarded = json.loads(workflow.journal.row('runtime_forms', science['episode_id'])['form'])
        assert forwarded == {name: returned[name] for name in parent_schema['properties']}
        assert all(len(rows) == 1 for rows in forwarded.values())
        assert returned['completed']
        selected_values = {row['field']: row['value'] for rows in forwarded.values() for row in rows}
        assert selected_values['occurrences']['values'][0]['value'] == 3
        assert selected_values['occupancy']['values'][0]['output']['value'] == 2 / 3
        assert selected_values['requirements']['values'] == []
        assert len(selected_values['qualification']['values']) == 4
        assert (archived['units_consumed'], science['units_consumed'], launch_record['units_consumed'],
            api_record['units_consumed'], results_record['units_consumed']) == (1, 2, 1, 2, 7)
        for record in (archived, science, launch_record, api_record, results_record):
            for table in ('runtime_actions', 'runtime_observations'):
                assert store.db.execute('SELECT COUNT(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                    (run_id, record['episode_id'])).fetchone()[0] == record['units_consumed']
        for record in (launch_record, api_record, results_record):
            assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        family = workflow.episode_bindings.for_role('results')
        api = family.api_execution
        result_ref = next(iter(forwarded.values()))[0]['source_ref']
        body = api.read_result(result_ref, scope)
        artifact = body['bundle']['artifacts'][0]
        assert store.get_artifact(artifact['raw_artifact_ref']) == (FIXTURES / 'families.json').read_bytes()
        root_context = api.appservice.custody.context(archived['episode_id'])
        root_attempt = store.db.execute(
            'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (run_id, archived['episode_id'], 0)).fetchone()
        assert root_attempt is not None
        assert root_attempt['child_episode_id'] == science['episode_id']
        assert root_attempt['failure'] is None
        assert json.loads(root_attempt['form']) == forwarded
        assert json.loads(root_attempt['contract'])['measurements']['schema'] == parent_schema
        assert family.received_report_facts(root_context) == {}
        assert workflow.catalog(scope, source=episode.source) == []
        assert store.count('annotation') == 0
