"""Actual shared Workflow, retained native fixtures, and requested Homology facts.

The decision provider, root/input-preparation continuation and NativeClient are
controlled fixtures. Source
preparation, commissions, custody, manifest/Workspace associations, selected
downloads, scientific publication, typed returns, and continuation are real.
No live service, BLAST executable, configured model, or annotation runs here.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG, PREFIX, OBJECT_UUID, SHOCK_UUID, metadata
from test_bvbrc_appservice_inputs import NativeClient
from test_bvbrc_homology_bundle_adapter import c4_fixture
from test_bvbrc_homology_inputs import raw_document
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client


def _binding(store, source_ref):
    source = store.get(source_ref)
    raw = store.get_artifact(source['artifact_ref'])
    return {'source_ref': source_ref, 'artifact_field': 'artifact_ref',
        'artifact_ref': source['artifact_ref'], 'sha256': hashlib.sha256(raw).hexdigest(),
        'byte_count': len(raw)}


def _supplied_fixture(store, target):
    # Keep every hit/HSP in the deliberately selected one-query native fixture.
    document = raw_document()
    document['BlastOutput2'] = document['BlastOutput2'][:1]
    fixture, contents, supplied, parameters = c4_fixture(document, extras=False)
    raw = contents[fixture['artifacts'][0]['raw_artifact_ref']]
    query = document['BlastOutput2'][0]['report']['results']['search']
    sequence = 'ACDEFGHIKL'
    sequence_sha = hashlib.sha256(sequence.encode()).hexdigest()
    member_id = 'supplied-query-0'
    db_selection = {'db_type': 'faa', 'db_source': 'precomputed_database',
        'db_precomputed_database': 'SYNTHETIC_DATABASE_PATH'}
    original_input = {'fixture': 'Explicit synthetic input and native-query mapping; no algorithm ran',
        'fasta': '>' + query['query_title'] + '\n' + sequence + '\n',
        'members': [{'member_id': member_id, 'supplied_id': query['query_title'],
            'sequence': sequence, 'length': len(sequence), 'molecule': 'protein',
            'sequence_sha256': sequence_sha, 'native_query': {
                'report_index': 0, 'query_id': query['query_id'],
                'query_title': query['query_title'], 'query_len': query['query_len']},
            'sequence_transform': 'identity'}],
        'database': {'requested_selection': db_selection,
            'effective_native_database': 'SYNTHETIC_DATABASE_PATH'}}
    input_material = store.register_material(data=canonical(original_input).encode(),
        name='SYNTHETIC-supplied-input.json', format='text', use='evidence')
    input_source = _binding(store, input_material['source_ref'])
    input_evidence = {'content': input_source, 'pointer': '/members/0'}
    request = {'version': 'bvbrc_appservice_request_v1',
        'effect_contract': 'selected_api_effects_v1', 'required_application_id': 'Homology',
        'parameters': {'output_path': '/synthetic/work/output', 'output_file': 'selected',
            'input_type': 'aa', 'input_source': 'fasta_data',
            'input_fasta_data': original_input['fasta'], 'blast_program': 'blastp',
            'blast_max_hits': 3, **db_selection}, 'start_parameters': {}, 'definition_inputs': [],
        'input_bindings': [{'binding_id': 'query-input', 'parameter_pointer': '/input_fasta_data',
            'kind': 'inline_parameter', 'content': None, 'workspace_path': None,
            'inline_value': original_input['fasta'], 'link_evidence': None,
            'members': [{'member_id': member_id, 'member_pointer': '/members/0',
                'length': len(sequence), 'molecule': 'protein', 'sequence_sha256': sequence_sha,
                'evidence': input_evidence}]}], 'workspace_targets': []}
    scientific_inputs = supplied[0]['value']
    mapping = scientific_inputs['queries'][0]
    mapping['input_member_id'] = member_id
    mapping['binding'].update(input_source_ref=input_source['source_ref'], member_ref=member_id,
        subject_ref=target, sequence_transform={'kind': 'identity',
            'source_ref': input_source['source_ref'], 'pointer': '/members/0', 'coordinate_map_ref': None},
        id_mapping_evidence=[{'source_ref': input_source['source_ref'],
            'pointer': '/members/0/native_query', 'relation': 'exact_submitted_member_to_native_query'}])
    scientific_inputs['database_binding']['requested_selection'] = db_selection
    # No function or taxon assignment is inferred from the raw hit titles.
    scientific_inputs['metadata'] = None
    scientific_material = store.register_material(data=canonical(scientific_inputs).encode(),
        name='SYNTHETIC-explicit-scientific-inputs.json', format='text', use='evidence')
    scientific_evidence = {'content': _binding(store, scientific_material['source_ref']), 'pointer': ''}
    parameters['scientific_inputs'] = scientific_evidence
    raw_format = {'format': adapter.FORMATS['blast_json15_raw'], 'version': None,
        'mode': 'database_identification', 'producer_source_ref': None, 'transformation_evidence': []}
    manifest_format = {'format': 'bvbrc_job_result_json', 'version': None,
        'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}
    requested = adapter.requested_form_schema({
        'hits': {'metric': 'reported_hit_count', 'report_index': 0},
        'query_coverage': {'metric': 'query_paired_coverage', 'report_index': 0, 'hit_index': 0},
        'reference_coverage': {'metric': 'reference_paired_coverage', 'report_index': 0, 'hit_index': 0},
        'missing': {'metric': 'missing_requirements'}})
    selector = {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_projection',
        'requirements': [{'requirement_id': key, 'role': role, 'required': required,
            'declared_format': declared, 'producer_rule_evidence': None, 'exact_object': None}
            for key, role, required, declared in [
                ('manifest', 'job_result_manifest', False, manifest_format),
                ('native', 'blast_json15_raw', True, raw_format)]],
        'adapter': {'adapter_id': 'bvbrc_homology', 'adapter_version': '1', 'parameters': parameters},
        'requested_schema': requested, 'supplied_metadata': [scientific_evidence], 'supplied_capabilities': []}
    return SimpleNamespace(request=request, selector=selector, raw=raw, document=document,
        scientific_inputs=scientific_inputs, original_input=original_input,
        input_material=input_material, scientific_material=scientific_material,
        input_source=input_source, scientific_evidence=scientific_evidence,
        raw_format=raw_format, manifest_format=manifest_format)


@pytest.fixture(scope='module')
def homology_run(tmp_path_factory):
    from gene_annotation_episode.bvbrc_homology_returns import homology_fact_sources

    directory = tmp_path_factory.mktemp('homology-shared-workflow')
    with pytest.MonkeyPatch.context() as patch, Store(directory / 'state') as store:
        target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
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
            raise AssertionError('Homology workflow fixture attempted live network transport')

        patch.setattr(BVBRCAppServiceService, '__init__', configured)
        patch.setattr('socket.create_connection', forbidden)
        patch.setattr('socket.socket.connect', forbidden)
        patch.setattr('socket.socket.connect_ex', forbidden)
        patch.setattr('urllib.request.OpenerDirector.open', forbidden)

        def controllers(path, initial):
            def root_estimate(history, parameters, contexts):
                count = 3 if path[-1][0] == 'annotation' else 2
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                    parameters, {'fixture': 'root_and_input_preparation_continuation_only'})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=root_estimate if path[-1][0] in {'annotation', 'improvement'} else None)

        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
            'service': 'bvbrc_appservice', 'request': supplied.request,
            'endpoint': 'usable_handoff', 'constraints': {}}
        launch = launch_assignment({'selected-api': assignment})
        handoff_form = form('execution_handoff_refs')
        result_form = form('execution_result_refs')
        sources = homology_fact_sources()
        result_form['properties'].update(measurements=sources['bvbrc_homology_measurements']['report_schema'],
            requirements=sources['bvbrc_homology_requirements']['report_schema'])
        result_form['required'].extend(['measurements', 'requirements'])
        config = deepcopy(CONFIG)
        config['scientific_adapters'] = [{'adapter_id': 'bvbrc_homology', 'adapter_version': '1',
            'implementation_sha256': adapter.implementation_sha256()}]
        factory = ExecutionServiceFactory({'selected-api': config}, {}, 2, 3, .5)

        class Choices:
            def __init__(self):
                self.counts = {}
                self.partial_ref = None
                self.partial_snapshot = None
                self.result_objects = {}

            def last(self, episode_id):
                row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                    'AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1',
                    (workflow.run_id, episode_id)).fetchone()
                return json.loads(row['result'])['result']

            async def complete(self, episode_id, role, instructions, current, schema):
                assert current.get('feedback') is None, current.get('feedback')
                self.counts[episode_id] = count = self.counts.get(episode_id, 0) + 1
                execution = current.get('execution_assignment', {})
                version = execution.get('version')
                if version == 'execution_launch_assignment_v1':
                    assert count == 1
                    return child('launch_api', assignment, scope, handoff_form)
                if version == 'api_service_assignment_v1':
                    if count == 1:
                        return selected(PREFIX + 'prepare', {'definition': {
                            'kind': 'packaged', 'required_application_id': 'Homology'}})
                    assert count == 2
                    return selected(PREFIX + 'submit', {'preparation_receipt_ref':
                        self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
                if version == 'execution_results_assignment_v1':
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
                if episode_id != episode.source.episode_id:
                    assert count <= 2
                    material = supplied.input_material if count == 1 else supplied.scientific_material
                    return selected('material.parse', {'material_ref': material['id'], 'format': 'text'})
                if count == 1:
                    return {'selection': {'kind': 'child',
                        'goal': 'Inspect the supplied synthetic query input and mapping metadata for the requested service job',
                        'scope': scope, 'purpose': 'Return retained source references after inspecting the supplied material',
                        'schema_json': json.dumps({'type': 'object', 'properties': {'refs': {
                            'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
                            'x-source': 'committed_record_refs'}}, 'required': ['refs'], 'additionalProperties': False}),
                        'initial_report_json': '{}'}, 'report_update': {}}
                if count == 2:
                    received = current['child_reports'][-1]
                    assert supplied.input_source['source_ref'] in received['refs']
                    assert supplied.scientific_evidence['content']['source_ref'] in received['refs']
                    return child('launch', launch, scope, handoff_form)
                assert count == 3
                received = current['child_reports'][-1]
                assert received['completed']
                assert received['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
                handoff, = received['references']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': handoff, 'selector': supplied.selector}, scope, result_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, ToolRegistry(store, clients=Client()), choices, directory / 'run',
            'homology-selected-workflow', controller_factory=controllers, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=('improvement', 'launch', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        api = workflow.episode_bindings.for_role('results').api_execution
        episode = workflow.build('annotation', 'root', 'Acquire the requested synthetic Homology measurements', scope)

        async def run():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record

        record = asyncio.run(run())
        archive = json.loads(''.join(iter_json(record.as_record())))
        results_record = archive['units'][2]['child']
        returned = json.loads(workflow.journal.row('runtime_forms', results_record['episode_id'])['form'])
        final_refs = {row['source_ref'] for row in returned['measurements']}
        assert len(final_refs) == 1
        final_ref, = final_refs
        yield SimpleNamespace(store=store, workflow=workflow, api=api, native=native,
            choices=choices, record=record, archive=archive, results_record=results_record,
            returned=returned, final_ref=final_ref, scope=scope, supplied=supplied,
            body=api.read_result(final_ref, scope), directory=directory,
            manifest_bytes=manifest_bytes, result_form=result_form, config=config)


def test_selected_homology_reaches_parent_with_complete_sheet_and_exact_zero(homology_run):
    run = homology_run
    preparation = run.archive['units'][0]['child']
    launch = run.archive['units'][1]['child']
    api_record = launch['units'][0]['child']
    results = run.results_record
    assert run.record.units_consumed == 3
    assert preparation['units_consumed'] == 2
    assert launch['units_consumed'] == 1
    assert api_record['units_consumed'] == 2
    assert results['units_consumed'] == 7
    for closed in (launch, api_record, results):
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert closed['units'][-1]['controller_step']['marginal_credit'] > 0
        assert run.choices.counts[closed['episode_id']] == closed['units_consumed']
    assert run.returned['completed'] is True
    assert {row['field']: row['value'] for row in run.returned['measurements']} == {
        'hits': 3, 'query_coverage': .6, 'reference_coverage': .75}
    assert run.returned['requirements'] == [{'source_ref': run.final_ref, 'field': 'missing', 'requirements': []}]
    assert all(row['source_ref'] == run.final_ref for row in run.returned['measurements'])
    admitted = run.store.db.execute('SELECT form,failure FROM runtime_report_attempts WHERE run_id=? '
        'AND child_episode_id=?', (run.workflow.run_id, results['episode_id'])).fetchone()
    assert admitted['failure'] is None and json.loads(admitted['form']) == run.returned
    assert not any(key in run.returned for key in ('sheet', 'components', 'bvbrc_homology_function_weights'))
    publication = run.body['publication']
    assert publication['requested_form_status'] == 'satisfied'
    assert publication['adapter_result']['facts'] == {'hits': 3, 'query_coverage': .6, 'reference_coverage': .75, 'missing': []}
    assert run.body['publication_inputs']['selector'] == run.supplied.selector
    assert run.body['publication_inputs']['adapter_implementation_sha256'] == run.config['scientific_adapters'][0]['implementation_sha256']
    assert run.body['bundle']['original_task']['submitted_parameters'] == run.supplied.request['parameters']
    artifacts = {row['role']: row for row in run.body['bundle']['artifacts']}
    raw = artifacts['blast_json15_raw']
    assert run.store.get_artifact(raw['raw_artifact_ref']) == run.supplied.raw
    assert run.store.get_artifact(artifacts['job_result_manifest']['raw_artifact_ref']) == run.manifest_bytes
    assert raw['task_association']['kind'] == 'task_result_manifest'
    assert raw['task_association']['evidence_ref'] == artifacts['job_result_manifest']['source_ref']
    assert raw['task_association']['pointer'] == '/output_files/0'
    assert raw['workspace_object']['uuid'] == SHOCK_UUID
    assert raw['workspace_object']['type'] == 'json' and raw['workspace_object']['metadata_receipt_ref']
    assert raw['task_association']['byte_version_status'] != 'producer_bytes_bound'
    saved_sheet = publication['adapter_result']['sheet_content']
    saved_components = publication['adapter_result']['components_content']
    sheet = json.loads(run.store.get_artifact(saved_sheet['artifact_ref']))
    components = json.loads(run.store.get_artifact(saved_components['artifact_ref']))
    assert saved_sheet['source_ref'] != saved_components['source_ref']
    assert sheet['binding']['c4_bundle'] == run.body['bundle']
    assert sheet['binding']['supplied_values'] == [{'evidence': run.supplied.scientific_evidence,
        'value': run.supplied.scientific_inputs}]
    query, = sheet['queries']
    assert query['query_binding_status'] == 'validated'
    assert [len(hit['hsps']) for hit in query['normalized_result']['hits']] == [3, 1, 1]
    measured = query['blast_sheet']['hits'][0]['measurements']
    assert measured['observed_paired_query_positions'] == measured['observed_paired_reference_positions'] == 6
    assert measured['overlap_pair_representations'] == 6
    assert measured['query_paired_coverage'] == .6 and measured['reference_paired_coverage'] == .75
    assert components['queries'][0]['conditional_function_weights']['unadjusted_probabilities'] is None
    assert [call[0] for call in run.native.calls] == ['rpc', 'task_info', 'rpc', 'rpc', 'download', 'rpc', 'rpc', 'download']
    assert run.store.count('annotation') == 0
    rows = run.store.db.execute('SELECT purpose FROM runtime_model_calls WHERE run_id=?', (run.workflow.run_id,)).fetchall()
    assert len(rows) == 15 and {row['purpose'] for row in rows} == {'decision'}
    assert run.store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?',
        (run.workflow.run_id,)).fetchone()[0] == 15
    selections = run.store.db.execute('SELECT a.action,m.response FROM runtime_actions a '
        'JOIN runtime_model_calls m ON m.run_id=a.run_id AND m.episode_id=a.episode_id '
        'AND m.call_index=a.decision_index WHERE a.run_id=?', (run.workflow.run_id,)).fetchall()
    assert len(selections) == 15
    assert all(json.loads(row['action']) == json.loads(row['response'])['selection'] for row in selections)


def test_early_partial_publication_survives_completion_without_claiming_zero_hits(homology_run):
    run = homology_run
    early = run.api.read_result(run.choices.partial_ref, run.scope)
    assert early == run.choices.partial_snapshot
    assert early['status'] == 'partial' and early['publication']['completion_proof'] is None
    scientific = early['publication']['adapter_result']
    assert scientific['status'] == 'partial'
    assert scientific['facts']['hits'] is None
    assert scientific['facts']['query_coverage'] is None
    assert scientific['facts']['reference_coverage'] is None
    assert scientific['facts']['missing']
    assert early['publication']['requested_form_status'] == 'partial'
    assert [row['role'] for row in early['bundle']['artifacts']] == ['job_result_manifest']
    assert run.store.get_artifact(early['bundle']['artifacts'][0]['raw_artifact_ref']) == run.manifest_bytes
    assert run.choices.partial_ref != run.final_ref
    assert run.final_ref in run.returned['references']
    assert all(row['source_ref'] != run.choices.partial_ref for row in run.returned['measurements'])


def test_saved_calculation_and_original_read_replay_need_no_native_call(homology_run, monkeypatch):
    run = homology_run
    publication = run.body['publication']
    saved = publication['adapter_result']
    sheet_bytes = run.store.get_artifact(saved['sheet_content']['artifact_ref'])
    component_bytes = run.store.get_artifact(saved['components_content']['artifact_ref'])
    sheet = json.loads(sheet_bytes)
    original = deepcopy(run.body)
    calls = deepcopy(run.native.calls)
    counts = {table: run.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
        for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations')}

    def forbidden(*args, **kwargs):
        raise AssertionError('saved result read/replay attempted acquisition, parsing or recalculation')

    monkeypatch.setattr(run.native, 'rpc', forbidden)
    monkeypatch.setattr(run.native, 'task_info', forbidden)
    monkeypatch.setattr(run.native, 'download', forbidden)
    monkeypatch.setattr('subprocess.run', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr(adapter, 'consume_bundle', forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_homology_grader.build_homology_sheet', forbidden)
    rescored = calculate_homology_scores(sheet, database_model={'temperature_bits': 1})
    original_components = json.loads(component_bytes)
    prior_kernel = original_components['queries'][0]['conditional_function_weights']
    new_kernel = rescored['queries'][0]['conditional_function_weights']
    assert prior_kernel['parameters']['temperature_bits'] == 2
    assert new_kernel['parameters']['temperature_bits'] == 1
    assert prior_kernel['unannotated_reference_kernel_mass'] == 1.75
    assert new_kernel['unannotated_reference_kernel_mass'] == 1.3125
    assert new_kernel['unadjusted_probabilities'] is None
    assert rescored['alignment_supplements'] == original_components['alignment_supplements']
    assert sheet == json.loads(sheet_bytes)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_homology_grader.calculate_homology_scores', forbidden)
    monkeypatch.setattr(adapter, 'calculate_homology_scores', forbidden)
    assert run.api.read_result(run.final_ref, run.scope) == original
    context = run.api.appservice.custody.context(run.results_record['episode_id'])
    operation_key = publication['origin']['operation_key']
    action_index = int(operation_key.rsplit(':', 1)[1])
    action = run.workflow.journal.row('runtime_actions', context.episode_id, action_index)
    runtime_snapshot = dict(action)
    selection = json.loads(action['action'])
    outcome_path = run.api.appservice.publications._directory(context, operation_key) / 'outcome.json'
    service_outcome = json.loads(outcome_path.read_text())
    # The shared runtime adds its own pending-work snapshot after the service
    # returns. Replay must preserve both original records at their own boundary.
    runtime_outcome = json.loads(action['result'])
    assert runtime_outcome == {**service_outcome,
        'pending_work_after_action': runtime_outcome['pending_work_after_action']}
    assert asyncio.run(run.api.execute(context, selection['tool'], selection['arguments'], operation_key)) == service_outcome
    assert dict(run.workflow.journal.row('runtime_actions', context.episode_id, action_index)) == runtime_snapshot
    assert run.native.calls == calls
    assert run.store.get_artifact(saved['sheet_content']['artifact_ref']) == sheet_bytes
    assert run.store.get_artifact(saved['components_content']['artifact_ref']) == component_bytes
    assert json.loads(run.workflow.journal.row('runtime_forms', context.episode_id)['form']) == run.returned
    assert {table: run.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
        for table in counts} == counts
