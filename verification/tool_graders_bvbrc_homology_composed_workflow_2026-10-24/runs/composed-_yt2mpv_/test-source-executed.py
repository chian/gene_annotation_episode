"""Composed scientific library -> existing API/results -> requested Homology return.

Scripted choices and NativeClient responses are explicitly synthetic fixtures.
The shared Workflow, mother construction, input parsing/custody, selected API
operations, native readers/calculators, publications, admissions and practical
completion estimator are production code. No service, model or BLAST runs here.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from gene_annotation_episode.bvbrc_homology_returns import homology_fact_sources
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from bvbrc_minhash_episode_fixture import PUBLICATION
from test_api_bvbrc_appservice import CONFIG, PREFIX, OBJECT_UUID, SHOCK_UUID, metadata
from test_bvbrc_appservice_inputs import NativeClient
from test_bvbrc_homology_workflow import _supplied_fixture
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import form
from test_practical_runtime import selected
from test_public_search import Client


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'verification/tool_graders_bvbrc_homology_composed_workflow_2026-10-24'
TOOL_NAME = 'bvbrc.homology.database_identification'
MEASUREMENTS = {'hits': 3, 'query_coverage': .6, 'reference_coverage': .75}


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def _child(role, assignment, scope, schema):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Acquire the requested hit count and residue coverage for the supplied protein through the selected Homology service',
        'scope': scope, 'purpose': 'Return only the declared recorded facts: the complete reported hit count and coverage from unique paired positions divided by full operand lengths; preserve missing values',
        'assignment': deepcopy(assignment), 'schema_json': json.dumps(schema),
        'initial_report_json': '{}'}, 'report_update': {}}


@pytest.fixture(scope='module')
def composed_homology_run():
    # Keep every run, including a failing run, outside pytest's temporary-file
    # retention. No previous evidence or run is removed by this harness.
    (EVIDENCE / 'runs').mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='composed-', dir=EVIDENCE / 'runs'))
    _write(directory / 'PROVENANCE.json', {'status': 'started',
        'scope': 'synthetic native responses through the actual composed Workflow',
        'scientific_mode': 'database_identification', 'live_api': False,
        'configured_model': False, 'native_blast': False, 'hpc': False,
        'fixture_overrides': ['scripted choices', 'root/scientific continuation', 'NativeClient transport'],
        'production_overrides': []})
    with pytest.MonkeyPatch.context() as patch, Store(directory / 'state') as store:
        sequence = 'ACDEFGHIKL'
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        supplied = _supplied_fixture(store, target)
        manifest_path = '/synthetic/work/output/selected.job_result'
        raw_path = '/synthetic/work/output/selected.raw.json'
        manifest_bytes = canonical({'id': '123', 'app': {'id': 'Homology'}, 'success': 1,
            'parameters': supplied.request['parameters'], 'output_files': [[raw_path, SHOCK_UUID]]}).encode()

        class Responses(NativeClient):
            def rpc(self, command):
                method = command['method']
                if method == 'AppService.start_app2':
                    assert command['params'][0] == 'Homology'
                    assert command['params'][1] == supplied.request['parameters']
                    self.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q'}
                elif method == 'Workspace.get':
                    reference, = command['params'][0]['objects']
                    assert command['params'][0]['metadata_only'] == 1
                    if reference == OBJECT_UUID:
                        row = metadata(manifest_path, type='job_result', size=len(manifest_bytes))
                    else:
                        assert reference == raw_path
                        row = metadata(raw_path, uuid=SHOCK_UUID, type='json', size=len(supplied.raw))
                    row['native_row'][8] = {'task_data': {'task_id': '123', 'app_id': 'Homology'}}
                    self.value = [[row['native_row'], None]]
                elif method == 'Workspace.get_download_url':
                    reference, = command['params'][0]['objects']
                    assert reference in (manifest_path, raw_path)
                    self.value = ['https://fixture.invalid/' + ('manifest' if reference == manifest_path else 'raw')]
                else:
                    raise AssertionError(command)
                return super().rpc(command)

            def download(self, url, *, byte_range=None):
                assert byte_range is None
                assert url in ('https://fixture.invalid/manifest', 'https://fixture.invalid/raw')
                self.body = manifest_bytes if url.endswith('/manifest') else supplied.raw
                return super().download(url, byte_range=byte_range)

        native = Responses()
        constructor = BVBRCAppServiceService.__init__

        def configured(self, *args, **kwargs):
            constructor(self, *args, **kwargs)
            self.client = native

        def forbidden(*args, **kwargs):
            raise AssertionError('Composed Homology fixture attempted live transport or a subprocess')

        patch.setattr(BVBRCAppServiceService, '__init__', configured)
        patch.setattr('socket.create_connection', forbidden)
        patch.setattr('socket.socket.connect', forbidden)
        patch.setattr('urllib.request.OpenerDirector.open', forbidden)
        patch.setattr('subprocess.run', forbidden)
        patch.setattr('subprocess.Popen', forbidden)

        def controllers(path, initial):
            def fixture_estimate(history, parameters, contexts):
                count = {'annotation': 1, 'scientific_process': 4}[path[-1][0]]
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                    parameters, {'fixture': 'root_and_scientific_continuation_only'})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=fixture_estimate
                if path[-1][0] in {'annotation', 'scientific_process'} else None)

        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
            'service': 'bvbrc_appservice', 'request': supplied.request,
            'endpoint': 'usable_handoff', 'constraints': {}}
        launch_assignment_value = launch_assignment({'selected-api': assignment})
        handoff_form = form('execution_handoff_refs')
        result_form = form('execution_result_refs')
        sources = homology_fact_sources()
        measurements = sources['bvbrc_homology_measurements']['report_schema']
        result_form['properties'].update(measurements=measurements,
            requirements=sources['bvbrc_homology_requirements']['report_schema'])
        result_form['required'].extend(['measurements', 'requirements'])
        parent_form = {'type': 'object', 'additionalProperties': False,
            'properties': {'measurements': deepcopy(measurements)}, 'required': ['measurements']}
        config = deepcopy(CONFIG)
        config['scientific_adapters'] = [{'adapter_id': 'bvbrc_homology', 'adapter_version': '1',
            'implementation_sha256': adapter.implementation_sha256()}]
        factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)
        tools = ToolRegistry(store, clients=Client())
        run_id, run_directory = 'homology-composed-selected-workflow', directory / 'run'
        application = factory(store, run_id=run_id, directory=run_directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory,
            source_directory=PUBLICATION, tool_catalog=tools.catalog(),
            child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / 'scientific-process-library')
        selected_tools = [{'name': TOOL_NAME, 'resources': 'api'},
            {'name': 'material.parse', 'resources': 'local'}]

        class Choices:
            def __init__(self):
                self.counts, self.scientific_calls, self.result_objects = {}, [], {}
                self.partial_ref = self.partial_snapshot = self.handoff = None

            def last(self, episode_id):
                row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                    'AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1',
                    (run_id, episode_id)).fetchone()
                return json.loads(row['result'])['result']

            async def complete(self, episode_id, role, instructions, current, schema):
                assert current.get('feedback') is None, current.get('feedback')
                self.counts[episode_id] = count = self.counts.get(episode_id, 0) + 1
                execution = current.get('execution_assignment', {})
                version = execution.get('version')
                if version == 'execution_launch_assignment_v1':
                    assert count == 1 and execution == launch_assignment_value
                    return _child('launch_api', assignment, scope, handoff_form)
                if version == 'api_service_assignment_v1':
                    assert execution == assignment
                    if count == 1:
                        return selected(PREFIX + 'prepare', {'definition': {
                            'kind': 'packaged', 'required_application_id': 'Homology'}})
                    assert count == 2
                    return selected(PREFIX + 'submit', {'preparation_receipt_ref':
                        self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
                if version == 'execution_results_assignment_v1':
                    assert execution['selector'] == supplied.selector
                    if count == 1:
                        return selected(PREFIX + 'task_info', {'handoff_ref': execution['handoff_ref'], 'file': 'job_result_id'})
                    previous = self.last(episode_id)
                    if count == 2:
                        return selected(PREFIX + 'workspace_metadata', {'objects': [{'kind': 'task_info_object',
                            'receipt_ref': previous['support_receipt_ref']}], 'options': {}})
                    if count in (3, 6):
                        obj = {'kind': 'receipt_row', 'receipt_ref': previous['support_receipt_ref'], 'row_pointer': '/result/0/0'}
                        self.result_objects[count] = obj
                        return selected(PREFIX + 'download_capability', {'objects': [obj],
                            'generation': 0, 'predecessor_receipt_ref': None})
                    if count in (4, 7):
                        manifest = count == 4
                        return selected(PREFIX + 'download', {'object': self.result_objects[count - 1],
                            'capability': {'kind': 'acquired', 'receipt_ref': previous['support_receipt_ref'], 'input_index': 0},
                            'byte_range': None, 'requirement_ids': ['manifest' if manifest else 'native'],
                            'role': 'job_result_manifest' if manifest else 'blast_json15_raw',
                            'declared_format': supplied.manifest_format if manifest else supplied.raw_format})
                    assert count == 5
                    self.partial_ref = previous['source_ref']
                    self.partial_snapshot = api.read_result(self.partial_ref, scope)
                    assert self.partial_snapshot['publication']['completion_proof'] is None
                    return selected(PREFIX + 'workspace_metadata', {'objects': [{'kind': 'manifest_member',
                        'manifest_receipt_ref': previous['support_receipt_ref'], 'output_index': 0}], 'options': {}})
                if 'scientific_process' in current:
                    self.scientific_calls.append((deepcopy(current), instructions))
                    assert current['scientific_process']['selection']['child_tool_info'] == selected_tools
                    if count <= 2:
                        material = supplied.input_material if count == 1 else supplied.scientific_material
                        return selected('material.parse', {'material_ref': material['id'], 'format': 'text'})
                    if count == 3:
                        return _child('launch', launch_assignment_value, scope, handoff_form)
                    assert count == 4
                    received = current['child_reports'][-1]
                    assert received['completed']
                    assert received['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
                    self.handoff, = received['references']
                    return _child('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': self.handoff, 'selector': supplied.selector}, scope, result_form)
                assert count == 1 and episode_id == episode.source.episode_id
                available = workflow.scientific_process_binding.tool_library.parent_tool_info(
                    workflow.services.tool_information_catalog(scope))
                assert all(any((row['name'], row['resources']) == (tool['name'], tool['resources'])
                    for row in available) for tool in selected_tools)
                scientific_assignment = {'selection': {'version': 'scientific_process_selection_v3',
                    'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
                    'child_tool_info': deepcopy(selected_tools)}, 'evidence_refs': [target],
                    'constraints': {'preserve_original_query': True},
                    'context': {'supplied_sequence': sequence, 'molecule': 'protein', 'complete': True,
                        'label_is_public_identity': False,
                        'supplied_material_refs': [supplied.input_material['id'], supplied.scientific_material['id']]}}
                return _child('scientific_process', scientific_assignment, scope, parent_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, tools, choices, run_directory, run_id,
            controller_factory=controllers, project_credit=lambda *_: 0,
            episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            annotation_child_roles=('scientific_process',), episode_record_receipts=True,
            initial_known_record_refs=[])
        api = workflow.episode_bindings.for_role('results').api_execution
        episode = workflow.build('annotation', 'root',
            'Measure the returned Homology hit population and aligned residue coverage for the supplied protein', scope)

        async def execute():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record

        record = asyncio.run(execute())
        archive = json.loads(''.join(iter_json(record.as_record())))
        scientific = archive['units'][0]['child']
        launch = scientific['units'][2]['child']
        api_record = launch['units'][0]['child']
        results = scientific['units'][3]['child']
        returned = json.loads(workflow.journal.row('runtime_forms', results['episode_id'])['form'])
        forwarded = json.loads(workflow.journal.row('runtime_forms', scientific['episode_id'])['form'])
        final_ref, = {row['source_ref'] for row in returned['measurements']}
        body = api.read_result(final_ref, scope)
        saved = body['publication']['adapter_result']
        sheet_bytes = store.get_artifact(saved['sheet_content']['artifact_ref'])
        components_bytes = store.get_artifact(saved['components_content']['artifact_ref'])
        for name, value in (('archive', archive), ('results-return', returned), ('scientific-return', forwarded),
                ('publication', body), ('native-calls', native.calls)):
            _write(directory / (name + '.json'), value)
        (directory / 'native-raw.json').write_bytes(supplied.raw)
        (directory / 'native-manifest.json').write_bytes(manifest_bytes)
        (directory / 'sheet.json').write_bytes(sheet_bytes)
        (directory / 'components.json').write_bytes(components_bytes)
        for index, (current, instructions) in enumerate(choices.scientific_calls):
            (directory / f'scientific-presentation-{index}.txt').write_text(
                render_scientific_process_prompt(current, instructions))
        _write(directory / 'PROVENANCE.json', {'status': 'workflow_closed',
            'scope': 'synthetic native responses through the actual composed Workflow',
            'scientific_mode': 'database_identification', 'live_api': False,
            'configured_model': False, 'native_blast': False, 'hpc': False,
            'fixture_overrides': ['scripted choices', 'root/scientific continuation', 'NativeClient transport'],
            'production_overrides': [], 'returned_measurements': MEASUREMENTS,
            'own_actions': {'annotation': 1, 'scientific_process': 4, 'launch': 1, 'launch_api': 2, 'results': 7},
            'native_raw_sha256': hashlib.sha256(supplied.raw).hexdigest(),
            'native_raw_byte_count': len(supplied.raw)})
        yield SimpleNamespace(store=store, workflow=workflow, api=api, native=native, choices=choices,
            record=record, archive=archive, scientific=scientific, launch=launch, api_record=api_record,
            results=results, returned=returned, forwarded=forwarded, final_ref=final_ref, body=body,
            scope=scope, supplied=supplied, directory=directory, run_directory=run_directory,
            sheet=json.loads(sheet_bytes), components=json.loads(components_bytes), episode=episode,
            selected_tools=selected_tools, library=library, parent_form=parent_form, manifest_bytes=manifest_bytes)


def test_library_constructs_scientific_child_with_frozen_tools_and_correct_owners(composed_homology_run):
    run = composed_homology_run
    context = run.api.appservice.custody.context(run.scientific['episode_id'])
    binding = run.workflow.scientific_process_binding
    binding.validate_context(context)
    information = binding.tool_library.resolve_tool_info(run.selected_tools,
        run.workflow.services.tool_information_catalog(run.scope))
    assert plain(context.assignment)['selection']['child_tool_info'] == information
    assert plain(context.assignment)['selection']['evidence_axis'] == run.library.reference('A101')
    assert plain(context.assignment)['selection']['thought_pattern'] == run.library.reference('P01')
    assert set(context.request['message']['scientific_process']) == {
        'version', 'selection', 'assignment_sha256', 'invocation_sha256', 'mechanics_binding'}
    direct = {row['name'] for row in binding.catalog(context)}
    assert 'material.parse' in direct and TOOL_NAME not in direct
    assert not any(name.startswith('api.bvbrc_appservice.') for name in direct)
    assert run.workflow.catalog(run.scope, source=run.episode.source) == []
    resolved = binding.tool_library.resolve_invocations(run.selected_tools,
        run.workflow.services.tool_information_catalog(run.scope))
    homology = next(row for row in resolved if row['name'] == TOOL_NAME)
    assert homology['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]}
    for index, (current, _) in enumerate(run.choices.scientific_calls):
        assert current['scientific_process']['child_tool_info'] == information
        prompt = (run.directory / f'scientific-presentation-{index}.txt').read_text()
        task, steering = prompt.split('\n\nSTEERING', 1)
        assert task.startswith('TASK\n')
        assert homology['instructions'] in task and homology['instructions'] not in steering
        assert current['scientific_process']['evidence_axis']['investigation_instructions'] in task
    for option in ('A101', 'P01'):
        assert (run.run_directory / 'scientific-process-library/entries' / (option + '.json')).read_bytes() == (
            PUBLICATION / 'entries' / (option + '.json')).read_bytes()
    api_context = run.api.appservice.custody.context(run.api_record['episode_id'])
    owner = run.api.appservice.custody.original_job_owner(api_context)
    assert owner['launch_episode_id'] == run.launch['episode_id']
    assert owner['parent_commission_operation_key'] == f'{run.workflow.run_id}:{context.episode_id}:2'
    assert run.api.appservice.custody.possession(context, run.supplied.input_source['source_ref']) == 'own_completed_action'
    assert run.api.appservice.custody.possession(context,
        run.supplied.scientific_evidence['content']['source_ref']) == 'own_completed_action'


def test_requested_actual_numbers_cross_results_scientific_parent_and_root(composed_homology_run):
    run = composed_homology_run
    assert {row['field']: row['value'] for row in run.returned['measurements']} == MEASUREMENTS
    assert run.returned['completed'] is True
    assert run.forwarded == {'measurements': run.returned['measurements']}
    assert run.returned['requirements'] == [{'source_ref': run.final_ref, 'field': 'missing', 'requirements': []}]
    assert set(run.forwarded) == {'measurements'}
    assert all(set(row) == {'source_ref', 'field', 'value'} and row['source_ref'] == run.final_ref
        for row in run.forwarded['measurements'])
    for child, parent, expected in ((run.results, run.scientific, run.returned),
            (run.scientific, run.archive, run.forwarded)):
        admission = run.store.db.execute('SELECT parent_episode_id,form,failure FROM runtime_report_attempts '
            'WHERE run_id=? AND child_episode_id=?', (run.workflow.run_id, child['episode_id'])).fetchone()
        assert admission['parent_episode_id'] == parent['episode_id']
        assert admission['failure'] is None and json.loads(admission['form']) == expected
        context = run.api.appservice.custody.context(parent['episode_id'])
        values = {row['fact_source']: row['facts'] for row in run.api.homology_returns.received_context(context)}
        assert values['bvbrc_homology_measurements'] == expected['measurements']
        assert 'bvbrc_homology_function_weights' not in values
        if parent is run.archive:
            assert set(values) == {'bvbrc_homology_measurements'}
        assert run.api.appservice.custody.possession(context, run.final_ref) == 'admitted_return'
    assert run.body['publication']['adapter_result']['facts'] == {**MEASUREMENTS, 'missing': []}
    assert run.body['publication_inputs']['selector'] == run.supplied.selector
    artifacts = {row['role']: row for row in run.body['bundle']['artifacts']}
    raw = artifacts['blast_json15_raw']
    assert run.store.get_artifact(raw['raw_artifact_ref']) == run.supplied.raw
    assert run.store.get_artifact(artifacts['job_result_manifest']['raw_artifact_ref']) == run.manifest_bytes
    assert raw['task_association']['kind'] == 'task_result_manifest'
    assert raw['task_association']['evidence_ref'] == artifacts['job_result_manifest']['source_ref']
    assert raw['task_association']['pointer'] == '/output_files/0'
    assert raw['workspace_object']['uuid'] == SHOCK_UUID and raw['workspace_object']['metadata_receipt_ref']
    assert raw['task_association']['byte_version_status'] != 'producer_bytes_bound'
    assert run.sheet['binding']['c4_bundle'] == run.body['bundle']
    query, = run.sheet['queries']
    assert query['query_binding_status'] == 'validated'
    assert [len(hit['hsps']) for hit in query['normalized_result']['hits']] == [3, 1, 1]
    measured = query['blast_sheet']['hits'][0]['measurements']
    assert measured['observed_paired_query_positions'] == measured['observed_paired_reference_positions'] == 6
    assert measured['overlap_pair_representations'] == 6
    assert measured['query_paired_coverage'] == 6 / 10
    assert measured['reference_paired_coverage'] == 6 / 8
    assert run.components['queries'][0]['conditional_function_weights']['unadjusted_probabilities'] is None


def test_only_selected_own_actions_have_observations_and_practical_closure_is_exact(composed_homology_run):
    run = composed_homology_run
    expected = [(run.archive, ['episode_child:scientific_process']),
        (run.scientific, ['material.parse', 'material.parse', 'episode_child:launch', 'episode_child:results']),
        (run.launch, ['episode_child:launch_api']),
        (run.api_record, [PREFIX + 'prepare', PREFIX + 'submit']),
        (run.results, [PREFIX + name for name in ('task_info', 'workspace_metadata',
            'download_capability', 'download', 'workspace_metadata', 'download_capability', 'download')])]
    for closed, names in expected:
        assert closed['units_consumed'] == len(names) == run.choices.counts[closed['episode_id']]
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert run.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                (run.workflow.run_id, closed['episode_id'])).fetchone()[0] == len(names)
        actions = [json.loads(row[0]) for row in run.store.db.execute(
            'SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (run.workflow.run_id, closed['episode_id']))]
        assert [action['tool'] if action['kind'] == 'tool' else action['kind'] + ':' + action['role']
            for action in actions] == names
    for closed in (run.launch, run.api_record, run.results):
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert closed['units'][-1]['controller_step']['marginal_credit'] > 0
    for closed in (run.archive, run.scientific):
        assert [unit['controller_step']['marginal_credit'] for unit in closed['units']] == [0] * closed['units_consumed']
    assert run.store.count('annotation') == run.store.count('observation') == 0
    assert run.store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?',
        (run.workflow.run_id,)).fetchone()[0] == 15
    decisions = run.store.db.execute('SELECT a.action,m.response,m.purpose FROM runtime_actions a '
        'JOIN runtime_model_calls m ON m.run_id=a.run_id AND m.episode_id=a.episode_id '
        'AND m.call_index=a.decision_index WHERE a.run_id=?', (run.workflow.run_id,)).fetchall()
    assert len(decisions) == 15
    assert all(row['purpose'] == 'decision' and json.loads(row['action']) == json.loads(row['response'])['selection']
        for row in decisions)
    assert [call[0] for call in run.native.calls] == ['rpc', 'task_info', 'rpc', 'rpc', 'download', 'rpc', 'rpc', 'download']


def test_partial_native_bundle_is_retained_and_saved_calculation_needs_no_execution(composed_homology_run):
    run = composed_homology_run
    early = run.api.read_result(run.choices.partial_ref, run.scope)
    assert early == run.choices.partial_snapshot
    assert early['status'] == 'partial' and early['publication']['completion_proof'] is None
    assert early['publication']['adapter_result']['facts'] == {
        'hits': None, 'query_coverage': None, 'reference_coverage': None,
        'missing': early['publication']['adapter_result']['missing_requirements']}
    assert early['publication']['adapter_result']['missing_requirements']
    assert run.choices.partial_ref != run.final_ref
    assert all(row['source_ref'] != run.choices.partial_ref for row in run.forwarded['measurements'])
    calls, sheet = deepcopy(run.native.calls), deepcopy(run.sheet)
    counts = {table: run.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=?',
        (run.workflow.run_id,)).fetchone()[0] for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls')}
    rescored = calculate_homology_scores(sheet, database_model={'temperature_bits': 1})
    prior_kernel = run.components['queries'][0]['conditional_function_weights']
    new_kernel = rescored['queries'][0]['conditional_function_weights']
    assert prior_kernel['parameters']['temperature_bits'] == 2
    assert new_kernel['parameters']['temperature_bits'] == 1
    assert prior_kernel['unannotated_reference_kernel_mass'] == 1.75
    assert new_kernel['unannotated_reference_kernel_mass'] == 1.3125
    assert new_kernel['unadjusted_probabilities'] is None
    assert sheet == run.sheet and run.native.calls == calls
    assert rescored['alignment_supplements'] == run.components['alignment_supplements']
    assert {table: run.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=?',
        (run.workflow.run_id,)).fetchone()[0] for table in counts} == counts
    _write(run.directory / 'saved-sheet-temperature-1.json', rescored)
