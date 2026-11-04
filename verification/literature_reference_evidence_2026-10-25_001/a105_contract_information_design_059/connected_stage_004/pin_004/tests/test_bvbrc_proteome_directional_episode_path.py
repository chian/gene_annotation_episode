"""Availability/compilation and a real shared Workflow with controlled choices.

Native response bytes are retained public BLASTP fixtures, associated with the
synthetic AppService task only by this test. No live service or model claim.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

from method_loop.archive import iter_json

from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_proteome_returns import proteome_fact_sources
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow, _compile_form
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from bvbrc_minhash_episode_fixture import PUBLICATION
from test_api_bvbrc_appservice import CONFIG, PREFIX, metadata, OBJECT_UUID
from test_bvbrc_appservice_inputs import NativeClient
from test_bvbrc_proteome_directional_returns import DirectionalDriver, DIRECTIONAL_SOURCES, selected_fields
from test_bvbrc_proteome_bundle_v2_resolution import fixture, selector
from test_bvbrc_proteome_directional import native
from test_bvbrc_proteome_tool_info import launch
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client


def test_fourteen_source_definitions_reach_actual_registry_workflow_and_form_compilation(tmp_path):
    with Store(tmp_path / 'state') as store:
        driver = DirectionalDriver(store, tmp_path)
        registry = EpisodeBindingRegistry([driver.family])
        # Exercise the actual Workflow.report_sources implementation; the fields
        # below are its ordinary caller-owned bindings, with no source override.
        workflow = SimpleNamespace(job_episodes=None, native_event_information=None,
            native_timing_information=None, project_annotation_score=None, resource_estimator=None,
            episode_bindings=registry)
        for role in ('results', 'scientific_process', 'annotation'):
            definitions = Workflow.report_sources(workflow, role)
            assert set(DIRECTIONAL_SOURCES) <= definitions.keys()
            for source in DIRECTIONAL_SOURCES:
                schema = {'type': 'object', 'properties': {'selected': definitions[source]['report_schema']},
                    'required': ['selected'], 'additionalProperties': False}
                assert _compile_form(json.dumps(schema), definitions) == schema
        assert registry.received_report_sources('launch') == {}


def test_actual_selected_tool_shared_workflow_native_publication_and_typed_parent_return(tmp_path, monkeypatch):
    fields = selected_fields()
    fields['integer'] = dict(kind='directional_native_integer', scope='query', document_id='d', query_ordinal=1, metric='length')
    case = fixture('2221')
    case['requested_form'] = adapter.requested_form_schema(fields)
    selected_selector = selector(case)
    assignment = launch('genome_ids')
    request = assignment['request']
    manifest_path, output_path = '/controlled/proteome/manifest', '/controlled/proteome/native'
    output_uuid = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    manifest = {'id': '123', 'app': {'id': 'GenomeComparison'}, 'parameters': deepcopy(request['parameters']),
        'success': 1, 'output_files': [[output_path, output_uuid]]}

    class Responses(NativeClient):
        def rpc(self, command):
            method = command['method']
            if method == 'AppService.start_app2':
                assert command['params'] == ['GenomeComparison', request['parameters'], {}]
                self.value = {'id': '123', 'application_id': 'GenomeComparison', 'state_code': 'Q'}
            elif method == 'AppService.query_tasks':
                self.value = {'123': {'id': '123', 'application_id': 'GenomeComparison', 'state_code': 'C'}}
            elif method == 'Workspace.get':
                self.value = [[metadata(manifest_path, type='job_result', size=len(canonical(manifest).encode()))['native_row']]]
            elif method == 'Workspace.get_download_url':
                obj, = command['params'][0]['objects']
                self.value = ['https://controlled.invalid/' + ('manifest' if obj in {manifest_path, OBJECT_UUID} else 'native')]
            else: raise AssertionError(command)
            return super().rpc(command)

        def download(self, url, *, byte_range=None):
            self.body = canonical(manifest).encode() if url.endswith('/manifest') else native('2221')
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
        config['scientific_adapters'] = [{'adapter_id': 'bvbrc_proteome', 'adapter_version': '2',
            'implementation_sha256': adapter.implementation_sha256()}]
        factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)
        tools = ToolRegistry(store, clients=Client())
        run_id, run_directory = 'directional-shared-workflow', tmp_path / 'run'
        application = factory(store, run_id=run_id, directory=run_directory, tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
        parent_schema = {'type': 'object', 'properties': {f'fact{i}': deepcopy(proteome_fact_sources()[name]['report_schema'])
            for i, name in enumerate(DIRECTIONAL_SOURCES)}, 'required': [f'fact{i}' for i in range(14)], 'additionalProperties': False}
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
                    if count == 1: return selected(PREFIX + 'prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'GenomeComparison'}})
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
                        'byte_range': None, 'requirement_ids': ['directional'], 'role': 'proteome_directional_report',
                        'declared_format': case['parameters']['directional_documents'][0]['declared_format']})
                if 'scientific_process' in current:
                    if count == 1: return child('launch', launching, scope, handoff_schema)
                    assert count == 2
                    handoff, = current['child_reports'][-1]['references']
                    return child('results', {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff,
                        'selector': selected_selector}, scope, result_schema)
                assert count == 1
                scientific = {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': library.reference('A101'),
                    'thought_pattern': library.reference('P01'), 'child_tool_info': [{'name': 'bvbrc.proteome_comparison', 'resources': 'api'}]},
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
            assert set(DIRECTIONAL_SOURCES) <= workflow.report_sources(grain).keys()
            assert _compile_form(json.dumps(parent_schema), workflow.report_sources(grain)) == parent_schema
        episode = workflow.build('annotation', 'root', 'Return the requested exact displayed protein correspondence measurements', scope)
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
        assert returned['fact4'][0]['value']['cell']['value'] == dict(sign=0, digits=[2], exponent=-66)
        assert returned['fact1'][0]['value']['pair_population']['unresolved_pairs'] == 61
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
        result_ref = returned['fact4'][0]['source_ref']
        body = api.read_result(result_ref, scope)
        artifact = body['bundle']['artifacts'][0]
        assert store.get_artifact(artifact['raw_artifact_ref']) == native('2221')
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
