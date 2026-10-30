"""Selected site tools through real Workflow ownership and typed return paths.

Biopython operations execute locally. BLAST service bytes are explicitly
synthetic native-protocol responses through the real launch/results adapters.
Native minimap2 runs on tiny synthetic reads with retained read quality.
Provider choices, zero credit and continuation horizons are test fixtures only.
No model, external BLAST service, database search or HPC operation runs here.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import zipfile

import pytest

from gene_annotation_episode.alignment_site_returns import alignment_site_fact_sources
from gene_annotation_episode.blast_result_views import BLAST_HSP_FACT_SCHEMA
from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry
from test_api_blast_service import Client
from test_api_service_integration import assignment
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_native_read_mapping import fixture as mapping_fixture
from test_published_axis_workflow import PUBLICATION
from test_sequence_views_integration import LocalOnly
from test_tool_grading_child_returns import RETURN_FORM, zero_fixture_credit


REFERENCE = 'reference_site_rows'
BLAST = 'blast_hsp_column_rows'
RETAINED_BLAST = Path(__file__).resolve().parents[1] / 'verification/w04_blast_graders_2026-10-24_001/live_api'


def _subset(node, names):
    node['properties'] = {key: node['properties'][key] for key in names}
    node['required'] = list(names)


def _site_form(source, *, alignment_ref=None, window=None, process_schema=None):
    fields = alignment_site_fact_sources()[source]['report_schema']
    group = fields['items']
    props = group['properties']
    policy = 'all_own_completed_results' if alignment_ref is None else 'matching_alignment_window'
    props['selection_policy'] = {'type': 'string', 'const': policy}
    if alignment_ref is not None:
        props['alignment_ref']['const'] = alignment_ref
        for key, value in window.items():
            props['selection']['properties'][key]['const'] = value
    if source == REFERENCE:
        row_fields = ('request_ordinal', 'reference_position', 'reference_unit',
            'query_position', 'query_unit', 'relationship', 'query_interval',
            'query_original_intervals', 'reference_original_intervals')
        components = ('requested_position_count', 'unique_requested_position_count',
            'duplicate_requested_position_count', 'paired_positions', 'identical_positions',
            'outside_alignment_positions', 'selected_paired_identity',
            'selected_query_paired_coverage')
    else:
        row_fields = ('column', 'relationship', 'query_symbol', 'reference_symbol',
            'query_interval', 'reference_interval', 'query_unit', 'reference_unit')
        components = ('window_alignment_columns', 'paired_columns', 'identical_pairs',
            'substituted_pairs', 'paired_identity', 'query_paired_coverage')
    _subset(props['rows']['items'], row_fields)
    _subset(props['components'], components)
    _subset(group, ('selection_policy', 'alignment_ref', 'selection', 'data_status',
        'rows', 'components', 'issue_codes', 'operation_status'))
    properties = {'selected_sites': fields}
    if process_schema is not None:
        properties['processes'] = deepcopy(process_schema)
    return obj(properties)


def _controller(counts):
    def factory(path, initial):
        count = counts.get(path[-1][0])
        if count is None:
            # Resource and results episodes use their actual practical endpoint.
            return YieldController(str(path), initial, 0)
        def estimate(history, parameters, contexts):
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                parameters, {'fixture': 'explicit_communication_test_horizon'})
        return YieldController(str(path), initial, 0, estimate_with_context=estimate)
    return factory


def _descriptor(directory, tools):
    descriptor = prepare_scientific_binding(run_directory=directory,
        source_directory=PUBLICATION, tool_catalog=tools.catalog(),
        child_roles=('scientific_process',))
    return descriptor, ScientificProcessLibrary(directory / 'scientific-process-library')


def _commission(library, scope, tools, supplied, schema):
    return child('scientific_process', {
        'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
            'child_tool_info': [{'name': name, 'resources': 'local'} for name in tools]},
        'evidence_refs': supplied, 'constraints': {'no_external_acquisition': True},
        'context': {}}, scope, schema)


def _run(parent, workflow):
    async def run():
        record = await parent.run_async(workflow.context)
        await parent.build_result(record)
        return record
    return asyncio.run(run())


def _context(workflow, episode_id):
    row = workflow.journal.row('runtime_episodes', episode_id)
    path, request = json.loads(row['path']), json.loads(row['request'])
    message = request['message']
    return BindingContext(workflow.run_id, episode_id, path[-1][0], tuple(map(tuple, path)),
        message['scope'], message['episode_assignment'], request)


def _snapshot(store):
    return {name: [tuple(row) for row in store.db.execute('SELECT * FROM ' + name + ' ORDER BY rowid')]
        for name in ('runtime_actions', 'runtime_observations', 'runtime_record_receipts',
                     'tool_operations', 'records')}


def _example(name, value):
    directory = os.environ.get('EPISODE_ALIGNMENT_EXAMPLES_DIR')
    if directory:
        path = Path(directory)
        path.mkdir(exist_ok=True, parents=True)
        (path / (name + '.json')).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _assert_no_private_sheet(form):
    text = json.dumps(form)
    for key in ('native_input', 'original_mapping_inputs', 'native_parameters', 'grading_artifact_ref',
                'inherited_native_measurements', 'operation_ref', 'decision_index'):
        assert key not in text


def _assert_action_counts(store, episode_id, expected):
    for table in ('runtime_actions', 'runtime_observations'):
        assert store.db.execute('SELECT count(*) FROM ' + table + ' WHERE episode_id=?',
            (episode_id,)).fetchone()[0] == expected


def _redeliver_frozen(workflow, parent, child_id, schema, returned, index):
    attempt = workflow.store.db.execute('SELECT * FROM runtime_report_attempts '
        'WHERE parent_episode_id=? AND child_episode_id=? ORDER BY decision_index LIMIT 1',
        (parent.source.episode_id, child_id)).fetchone()
    assert attempt is not None
    before = _snapshot(workflow.store)
    receipt = workflow.redeliver(parent.source, {'delivery_ref': attempt['delivery_ref'],
        'schema_json': json.dumps(schema), 'purpose': 'Receive the original selected site measurements'}, index)
    assert receipt.failure is None
    assert receipt.report.as_record() == returned
    assert _snapshot(workflow.store) == before


@pytest.mark.parametrize('molecule,mode,shape', [
    ('dna', 'global', 'ordinary'), ('rna', 'global', 'ordinary'),
    ('protein', 'local', 'mixed'), ('dna', 'local', 'no_alignment'),
    ('dna', 'global', 'grader_failure')])
def test_scientific_child_owns_alignment_and_selected_sites_through_parent_return(
        tmp_path, monkeypatch, molecule, mode, shape):
    with Store(tmp_path / 'state') as store:
        if shape == 'no_alignment':
            path = tmp_path / 'pair.fa'
            path.write_text('>query\nAAAA\n>reference\nTTTT\n')
            query, reference = store.create_problem(path, molecule='dna')['subject_refs']
            supplied = [query, reference]
        else:
            sequence = {'dna': 'ACGTTGCA', 'rna': 'ACGUUGCA', 'protein': 'MACDEFGH'}[molecule]
            query, = store.create_problem(raw_sequence=sequence, molecule=molecule)['subject_refs']
            reference, supplied = query, [query]
        scope = store.validate_scope({'subject_refs': supplied})
        tools = ToolRegistry(store, clients=LocalOnly())
        directory = tmp_path / 'run'
        descriptor, library = _descriptor(directory, tools)
        schema = _site_form(REFERENCE)
        if shape == 'grader_failure':
            import gene_annotation_episode.alignment_site_inputs as inputs
            def fail(*args, **kwargs):
                raise ValueError('site_native_geometry_conflict')
            monkeypatch.setattr(inputs, 'extract_biopython_reference_sites', fail)

        class Choices:
            calls = []
            child_id = None
            own_calls = 0
            async def complete(self, episode_id, role, instructions, current, output_schema):
                assert not current.get('feedback'), current.get('feedback')
                self.calls.append((episode_id, deepcopy(current)))
                if 'scientific_process' not in current:
                    return _commission(library, scope, ['sequence.align', 'sequence.sites'], supplied, schema)
                self.child_id = episode_id
                self.own_calls += 1
                if self.own_calls == 1:
                    return selected('sequence.align', {'query_ref': query, 'reference_ref': reference,
                        'molecule': molecule, 'mode': mode})
                assert self.own_calls == 2
                aligned = json.loads(store.db.execute('SELECT result FROM tool_operations WHERE name=?',
                    ('sequence.align',)).fetchone()[0])
                assert aligned['status'] == 'completed', aligned
                args = {'alignment_ref': aligned['result']['observation_ref']}
                args.update(window={'start': 0, 'end': 4} if shape == 'no_alignment' else None)
                if shape != 'no_alignment':
                    args.pop('window')
                    args['positions'] = [2, 0, 2]
                return selected('sequence.sites', args)
            async def release(self, episode_id):
                pass

        decisions = Choices()
        workflow = Workflow(store, tools, decisions, directory, 'alignment-site-native-' + shape,
            _controller({'annotation': 1, 'scientific_process': 2}), zero_fixture_credit,
            episode_binding_descriptors=[descriptor], episode_record_receipts=True,
            initial_known_record_refs=[])
        if shape == 'mixed':
            schema = _site_form(REFERENCE, process_schema=workflow.scientific_process_binding.fact_sources(
                'scientific_process')['scientific_process_results']['report_schema'])
        parent = workflow.build('annotation', 'root', 'Compare supplied sequence correspondence', scope)
        assert workflow.catalog(scope, source=parent.source) == []
        assert not workflow.permits_common_action(parent.source, 'tool')
        assert list(workflow.receipts.known(parent.source.episode_id, record_type='observation')) == []
        record = _run(parent, workflow)
        assert record.units_consumed == 1 and len(decisions.calls) == 3
        child_id = decisions.child_id
        saved = workflow.journal.row('runtime_forms', child_id)
        returned, frozen = json.loads(saved['form']), json.loads(saved['facts'])
        group, = returned['selected_sites']
        assert returned['selected_sites'] == frozen[REFERENCE]
        _assert_no_private_sheet(returned['selected_sites'])
        assert set(group) == set(schema['properties']['selected_sites']['items']['properties'])
        operation = store.db.execute('SELECT * FROM tool_operations WHERE name=?', ('sequence.sites',)).fetchone()
        result = json.loads(operation['result'])
        assert group['alignment_ref'] == json.loads(operation['arguments'])['alignment_ref']
        if shape == 'grader_failure':
            assert result['status'] == group['operation_status'] == 'partial'
            assert group['data_status'] == 'unavailable'
            assert group['rows'] is group['components'] is None
            assert 'site_grading_unavailable' in group['issue_codes']
            assert 'site_native_geometry_conflict' in group['issue_codes']
        elif shape == 'no_alignment':
            assert group['data_status'] == 'no_alignment'
            assert group['components']['paired_positions'] == 0
            assert group['components']['outside_alignment_positions'] == 4
            assert group['components']['selected_paired_identity'] == {
                'value': None, 'numerator': 0, 'denominator': 0, 'unit': 'fraction'}
            assert group['components']['selected_query_paired_coverage'] == {
                'value': 0., 'numerator': 0, 'denominator': 4, 'unit': 'fraction'}
            assert all(row['relationship'] == 'outside_alignment' for row in group['rows'])
        else:
            assert group['data_status'] == 'complete'
            assert [row['reference_position'] for row in group['rows']] == [2, 0, 2]
            assert [row['request_ordinal'] for row in group['rows']] == [0, 1, 2]
            assert group['components']['requested_position_count'] == 3
            assert group['components']['unique_requested_position_count'] == 2
            assert group['components']['duplicate_requested_position_count'] == 1
            assert group['components']['paired_positions'] == group['components']['identical_positions'] == 2
            assert group['components']['selected_paired_identity'] == {
                'value': 1., 'numerator': 2, 'denominator': 2, 'unit': 'fraction'}
            assert group['components']['selected_query_paired_coverage'] == {
                'value': .25, 'numerator': 2, 'denominator': 8, 'unit': 'fraction'}
            assert {row['query_unit'] for row in group['rows']} == {'aa' if molecule == 'protein' else 'nt'}
        if shape == 'mixed':
            process, = returned['processes']
            assert process['completed_actions'] == 2
        received = set(workflow.receipts.known(parent.source.episode_id))
        assert group['alignment_ref'] in received
        assert result['result']['observation_ref'] not in received  # The comparison was not requested.
        _assert_action_counts(store, parent.source.episode_id, 1)
        _assert_action_counts(store, child_id, 2)
        assert store.count('annotation') == 0
        before = _snapshot(store)
        assert tools.execute('sequence.sites', json.loads(operation['arguments']), scope=scope,
            operation_key=operation['operation_key']) == result
        action_index = store.db.execute('SELECT decision_index FROM runtime_actions WHERE episode_id=?',
            (parent.source.episode_id,)).fetchone()[0]
        workflow.receive_form(parent.source, returned, schema, action_index, redelivery=True)
        assert _snapshot(store) == before
        context = _context(workflow, child_id)
        def forbidden(*args, **kwargs):
            raise AssertionError('Closed validation must not read live actions or recalculate scores')
        monkeypatch.setattr(WorkflowServices, 'alignment_site_own_action_results', forbidden)
        import gene_annotation_episode.alignment_site_calculators as calculators
        monkeypatch.setattr(calculators, 'calculate_reference_site_components', forbidden)
        workflow.scientific_process_binding.validate_report(context, returned, schema)
        _redeliver_frozen(workflow, parent, child_id, schema, returned, 1)
        if group['rows']:
            altered = deepcopy(returned)
            altered['selected_sites'][0]['rows'][0]['reference_position'] += 1
            with pytest.raises(ReportBoundaryError):
                workflow.scientific_process_binding.validate_report(context, altered, schema)
        _example('reference-' + molecule + '-' + shape, {'returned': returned,
            'tool_result': result, 'counts': {'parent_actions': 1, 'child_actions': 2},
            'source_kind': 'actual_local_biopython'})


@pytest.mark.parametrize('shape,offset', [('ordinary', 2), ('empty', 8), ('missing', 0), ('retained_native', 0)])
def test_blast_hsp_is_acquired_received_then_selected_and_returned(tmp_path, monkeypatch, shape, offset):
    captured = shape == 'retained_native'
    limit = 100 if captured else 4
    native_body = None
    if captured:
        with zipfile.ZipFile(RETAINED_BLAST / 'result.body') as archive:
            native_body = json.loads(archive.read('DTKE1D4G016_1.json'))

    class Responses(Client):
        fetched = None
        def blast(self, action, **arguments):
            response = super().blast(action, **arguments)
            if action == 'fetch' and captured:
                # Reuse the seven complete real HSPs. Only this fixture's query
                # label changes to match its actual Store identity. Submission
                # is an offline protocol fixture, not the old or a new RID job.
                body = deepcopy(native_body)
                body['BlastOutput2']['report']['results']['search']['query_title'] = self.subject
                response = replace(response, content=json.dumps(body).encode(), transport={
                    'status': 200, 'representation': 'retained_native_hsps_with_fixture_query_label',
                    'original_artifact': str(RETAINED_BLAST / 'result.body'),
                    'changed_native_fields': ['/BlastOutput2/report/results/search/query_title']})
            elif action == 'fetch' and shape != 'missing':
                body = json.loads(response.content)
                hsp = body['BlastOutput2'][0]['report']['results']['search']['hits'][0]['hsps'][0]
                hsp.update(qseq='MACDEFGH', hseq='MACAEFGH', midline='||| ||||', identity=7)
                response = replace(response, content=json.dumps(body).encode())
            if action == 'fetch':
                self.fetched = response.content
            return response

    client = Responses()
    resources = {'blast': {'kind': 'api', 'service': 'ncbi_blast'}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, .5)
    with Store(tmp_path / 'state') as store:
        sequence = ''.join((RETAINED_BLAST / 'query.faa').read_text().splitlines()[1:]) if captured else 'MACDEFGH'
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        scope = store.validate_scope({'subject_refs': [target]})
        tools = ToolRegistry(store, clients=client)
        directory = tmp_path / 'run'
        descriptor, library = _descriptor(directory, tools)
        request = assignment('blast', 'ncbi_blast', {'subject_ref': target, 'program': 'blastp', 'database': 'swissprot'})
        launch = launch_assignment({'blast': request})
        handoff_form = form('execution_handoff_refs')
        result_form = obj({'complete': {'type': 'boolean', 'x-source': 'execution_completed'},
            'matches': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}})

        class Choices:
            parent_calls = 0
            calls = []
            hsp = None
            child_id = None
            requested_schema = None
            async def complete(self, episode_id, role, instructions, current, output_schema):
                assert not current.get('feedback'), current.get('feedback')
                self.calls.append((episode_id, deepcopy(current)))
                execution = current.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    return child('launch_api', request, scope, handoff_form)
                if execution.get('version') == 'api_service_assignment_v1':
                    return selected('api.blast.submit')
                if execution.get('version') == 'execution_results_assignment_v1':
                    return selected('api.blast.fetch')
                if 'scientific_process' in current:
                    self.child_id = episode_id
                    assert self.hsp in set(workflow.receipts.known(episode_id))
                    return selected('result.blast.hsp', {'observation_ref': self.hsp,
                        'column_offset': offset, 'column_limit': limit})
                self.parent_calls += 1
                if self.parent_calls == 1:
                    assert store.count('observation') == 0
                    return child('launch', launch, scope, handoff_form)
                if self.parent_calls == 2:
                    handoff, = current['child_reports'][-1]['references']
                    return child('results', {'version': 'execution_results_assignment_v1',
                        'handoff_ref': handoff, 'selector': {}}, scope, result_form)
                assert self.parent_calls == 3
                matches = current['child_reports'][-1]['matches']
                if captured:
                    assert len(matches) == 7
                    match, = [row for row in matches if row['bitscore'] == 38.1206]
                else:
                    match, = matches
                self.hsp = match['hsp_ref']
                assert self.hsp in set(workflow.receipts.known(episode_id))
                self.requested_schema = _site_form(BLAST, alignment_ref=self.hsp,
                    window={'column_offset': offset, 'column_limit': limit})
                return _commission(library, scope, ['result.blast.hsp'], [target, self.hsp], self.requested_schema)
            async def release(self, episode_id):
                pass

        decisions = Choices()
        def services(store, **kwargs):
            execution = factory(store, **kwargs)
            return EpisodeApplicationServices((descriptor, *execution.episode_binding_descriptors),
                execution.role_credit_bindings, execution.job_progress_provider,
                resource_tool_catalogs=execution.resource_tool_catalogs)
        workflow = Workflow(store, tools, decisions, directory, 'alignment-site-api-' + shape,
            _controller({'annotation': 3, 'scientific_process': 1}), zero_fixture_credit,
            episode_service_factory=services,
            episode_service_binding={'execution': factory.as_record(), 'scientific': descriptor},
            episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'results', 'scientific_process'),
            episode_record_receipts=True, initial_known_record_refs=[])
        parent = workflow.build('annotation', 'root', 'Inspect selected BLAST correspondence', scope)
        assert workflow.catalog(scope, source=parent.source) == []
        assert not list(workflow.receipts.known(parent.source.episode_id, record_type='observation'))
        record = _run(parent, workflow)
        assert record.units_consumed == 3 and decisions.parent_calls == 3
        assert [name for name, _ in client.calls] == ['submit', 'fetch']
        child_id = decisions.child_id
        saved = workflow.journal.row('runtime_forms', child_id)
        returned, frozen = json.loads(saved['form']), json.loads(saved['facts'])
        assert returned['selected_sites'] == frozen[BLAST]
        group, = returned['selected_sites']
        assert group['alignment_ref'] == decisions.hsp
        assert group['selection_policy'] == 'matching_alignment_window'
        assert group['selection']['column_offset'] == offset
        assert group['operation_status'] == 'completed'
        _assert_no_private_sheet(returned)
        if shape == 'ordinary':
            assert [row['column'] for row in group['rows']] == [2, 3, 4, 5]
            assert [row['query_interval'] for row in group['rows']] == [[2, 3], [3, 4], [4, 5], [5, 6]]
            assert group['components']['paired_columns'] == 4
            assert group['components']['identical_pairs'] == 3
            assert group['components']['substituted_pairs'] == 1
            assert group['components']['paired_identity'] == {
                'value': .75, 'numerator': 3, 'denominator': 4, 'unit': 'fraction'}
            assert group['components']['query_paired_coverage'] == {
                'value': .5, 'numerator': 4, 'denominator': 8, 'unit': 'fraction'}
        elif captured:
            assert len(group['rows']) == group['components']['window_alignment_columns'] == 86
            assert group['selection']['column_end'] == group['selection']['total_columns'] == 86
            assert group['components']['paired_columns'] == 71
            assert group['components']['identical_pairs'] == 31
            assert group['components']['substituted_pairs'] == 40
            assert group['components']['paired_identity'] == {
                'value': 31 / 71, 'numerator': 31, 'denominator': 71, 'unit': 'fraction'}
            assert group['components']['query_paired_coverage'] == {
                'value': 71 / 253, 'numerator': 71, 'denominator': 253, 'unit': 'fraction'}
        elif shape == 'empty':
            assert group['rows'] == []
            assert group['components']['paired_columns'] == 0
            assert group['selection']['column_end'] == group['selection']['total_columns'] == 8
            assert group['components']['paired_identity']['value'] is None
        else:
            assert group['rows'] is None and group['selection']['column_end'] is None
            assert group['components']['paired_columns'] is None
            assert group['components']['paired_identity']['value'] is None
        observation = store.get(decisions.hsp)
        native_source = store.get(observation['source_ref'])
        assert store.get_artifact(native_source['artifact_ref']) == client.fetched
        assert store.count('observation') == (7 if captured else 1) and store.count('annotation') == 0
        operation = store.db.execute('SELECT * FROM tool_operations WHERE name=?', ('result.blast.hsp',)).fetchone()
        result = json.loads(operation['result'])
        assert result['record_refs'] == []
        grading = json.loads(store.get_artifact(result['result']['site_grading_artifact_ref']))
        assert grading['grading']['sheet']['source']['alignment_ref'] == decisions.hsp
        if captured:
            original_hsp = native_body['BlastOutput2']['report']['results']['search']['hits'][1]['hsps'][0]
            assert grading['grading']['sheet']['native_input'] == original_hsp
            assert grading['grading']['sheet']['source']['native_locator'] == {
                'report_ordinal': 0, 'hit_ordinal': 1, 'hsp_ordinal': 0}
            unchanged = json.loads(client.fetched)
            unchanged['BlastOutput2']['report']['results']['search']['query_title'] = 'gene_001'
            assert unchanged == native_body
        _assert_action_counts(store, child_id, 1)
        _assert_action_counts(store, parent.source.episode_id, 3)
        before = _snapshot(store)
        assert tools.execute('result.blast.hsp', json.loads(operation['arguments']), scope=scope,
            operation_key=operation['operation_key'], permitted_record_refs=[decisions.hsp]) == result
        workflow.receive_form(parent.source, returned, decisions.requested_schema, 2, redelivery=True)
        assert _snapshot(store) == before
        def forbidden(*args, **kwargs):
            raise AssertionError('Closed BLAST return must use frozen facts')
        monkeypatch.setattr(WorkflowServices, 'alignment_site_own_action_results', forbidden)
        import gene_annotation_episode.blast_hsp_site_calculators as calculators
        monkeypatch.setattr(calculators, 'calculate_blast_hsp_column_components', forbidden)
        workflow.scientific_process_binding.validate_report(_context(workflow, child_id), returned,
            decisions.requested_schema)
        _redeliver_frozen(workflow, parent, child_id, decisions.requested_schema, returned, 3)
        assert [name for name, _ in client.calls] == ['submit', 'fetch']
        _example('blast-' + shape, {'returned': returned, 'retained_grading': grading,
            'provider_calls': [name for name, _ in client.calls],
            'counts': {'parent_actions': 3, 'child_site_actions': 1, 'scientific_observations': 7 if captured else 1},
            'source_kind': 'retained_native_hsps_with_fixture_query_label' if captured else
                'synthetic_native_api_protocol_through_launch_results'})


def test_native_minimap_child_returns_selected_quality_coordinates_and_insertion_ancestry(tmp_path, monkeypatch):
    store, tools, target, selection, map_args = mapping_fixture(tmp_path)
    with store:
        scope = selection['scope']
        directory = tmp_path / 'run'
        descriptor, library = _descriptor(directory, tools)
        query_refs = [row[0] for row in store.db.execute(
            'SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref',
            (map_args['query_selection_ref'],))]
        supplied = [target['id'], map_args['query_selection_ref'], *query_refs, *map_args['reference_refs']]
        schema = _site_form(REFERENCE)
        properties = schema['properties']['selected_sites']['items']['properties']
        catalog = alignment_site_fact_sources()[REFERENCE]['report_schema']['items']['properties']
        for name in ('query_strand', 'query_symbol', 'query_original_symbol',
                     'query_quality_character', 'query_quality_score', 'quality_encoding'):
            properties['rows']['items']['properties'][name] = catalog['rows']['items']['properties'][name]
            properties['rows']['items']['required'].append(name)
        for name in ('query_gap_positions', 'selected_insertion_events', 'inserted_query_positions',
                     'selected_alignment_identity'):
            properties['components']['properties'][name] = catalog['components']['properties'][name]
            properties['components']['required'].append(name)
        properties['insertions'] = catalog['insertions']
        _subset(properties['insertions']['items'], ('event_ordinal', 'reference_boundary',
            'query_interval', 'query_strand', 'query_sequence', 'query_quality_characters',
            'query_original_intervals', 'query_unit', 'reference_unit'))
        schema['properties']['selected_sites']['items']['required'].append('insertions')

        class Choices:
            child_id = None
            own_calls = 0
            async def complete(self, episode_id, role, instructions, current, output_schema):
                assert not current.get('feedback'), current.get('feedback')
                if 'scientific_process' not in current:
                    return _commission(library, scope, ['reads.map', 'sequence.sites'], supplied, schema)
                self.child_id = episode_id
                self.own_calls += 1
                if self.own_calls == 1:
                    return selected('reads.map', map_args)
                assert self.own_calls in (2, 3)
                mapped = json.loads(store.db.execute('SELECT result FROM tool_operations WHERE name=?',
                    ('reads.map',)).fetchone()[0])
                assert mapped['status'] == 'completed', mapped
                strand = '+' if self.own_calls == 2 else '-'
                placement, = [row for row in mapped['result']['records'] if row['strand'] == strand]
                return selected('sequence.sites', {'alignment_ref': placement['observation_ref'],
                    'positions': [2099, 2100, 3600] if strand == '+' else [500, 5499]})
            async def release(self, episode_id):
                pass

        decisions = Choices()
        workflow = Workflow(store, tools, decisions, directory, 'alignment-site-minimap-native',
            _controller({'annotation': 1, 'scientific_process': 3}), zero_fixture_credit,
            episode_binding_descriptors=[descriptor], episode_record_receipts=True,
            initial_known_record_refs=[])
        parent = workflow.build('annotation', 'root', 'Measure selected read correspondence and original coordinates', scope)
        assert workflow.catalog(scope, source=parent.source) == []
        record = _run(parent, workflow)
        assert record.units_consumed == 1 and decisions.own_calls == 3
        saved = workflow.journal.row('runtime_forms', decisions.child_id)
        returned, frozen = json.loads(saved['form']), json.loads(saved['facts'])
        assert returned['selected_sites'] == frozen[REFERENCE]
        plus, minus = returned['selected_sites']
        _assert_no_private_sheet(returned)
        assert [row['query_position'] for row in plus['rows']] == [1999, 2003, None]
        assert [row['relationship'] for row in plus['rows']] == ['identical', 'identical', 'query_gap']
        assert [row['query_quality_character'] for row in plus['rows']] == ['I', 'I', None]
        assert plus['components']['paired_positions'] == 2
        assert plus['components']['query_gap_positions'] == 1
        assert plus['components']['selected_insertion_events'] == 1
        assert plus['components']['inserted_query_positions'] == 3
        assert plus['components']['selected_alignment_identity'] == {
            'value': 1 / 3, 'numerator': 2, 'denominator': 6, 'unit': 'fraction'}
        insertion, = plus['insertions']
        assert insertion['reference_boundary'] == 2100 and insertion['query_interval'] == [2000, 2003]
        assert insertion['query_sequence'] == ['G', 'G', 'G']
        assert insertion['query_quality_characters'] == ['I', 'I', 'I']
        assert [row['query_position'] for row in minus['rows']] == [4999, 0]
        assert {row['query_strand'] for row in minus['rows']} == {'-'}
        assert {row['query_quality_character'] for row in minus['rows']} == {'?'}
        assert minus['insertions'] == []
        assert minus['components']['selected_paired_identity']['value'] == 1
        from Bio.Seq import Seq
        for row in minus['rows']:
            assert row['query_symbol'] == str(Seq(row['query_original_symbol']).complement())
        operations = list(store.db.execute('SELECT * FROM tool_operations WHERE name=? ORDER BY rowid',
            ('sequence.sites',)))
        retained = []
        for group, operation in zip((plus, minus), operations, strict=True):
            outcome = json.loads(operation['result'])
            assert outcome['status'] == group['operation_status'] == 'completed'
            assert group['data_status'] == 'partial'  # Encoding is explicitly unspecified, not phred33.
            assert 'site_quality_encoding_unspecified' in group['issue_codes']
            assert all(row['query_quality_score'] is None and row['quality_encoding'] == 'unspecified'
                for row in group['rows'])
            alignment = store.get(group['alignment_ref'])
            native_source = store.get(alignment['source_ref'])
            grading, = source_tool_gradings(store, outcome['result']['source_ref'])
            retained.append(grading)
            sheet = grading['sheet']
            assert sheet['mode'] == 'minimap2_placement'
            assert sheet['native_parameters']['preset'] == map_args['preset']
            assert sheet['source']['native_artifact_ref'] == native_source['stdout_ref']
            assert sheet['source']['native_locator'] == {key: alignment['native_minimap2'][key]
                for key in ('line_number', 'row_start', 'row_end')}
            query, = alignment['subject_refs']
            reference, = alignment['source_subject_refs']
            for row in group['rows']:
                if row['query_interval'] is not None:
                    assert row['query_original_intervals'] == [{'subject_ref': query,
                        'start': row['query_interval'][0], 'end': row['query_interval'][1],
                        'unit': 'nt', 'strand': '+'}]
                assert row['reference_original_intervals'] == [{'subject_ref': reference,
                    'start': row['reference_position'], 'end': row['reference_position'] + 1,
                    'unit': 'nt', 'strand': '+'}]
            if group['insertions']:
                assert insertion['query_original_intervals'] == [{'subject_ref': query,
                    'start': 2000, 'end': 2003, 'unit': 'nt', 'strand': '+'}]
            assert group['alignment_ref'] in set(workflow.receipts.known(parent.source.episode_id))
            assert outcome['result']['observation_ref'] not in set(workflow.receipts.known(parent.source.episode_id))
        _assert_action_counts(store, parent.source.episode_id, 1)
        _assert_action_counts(store, decisions.child_id, 3)
        assert store.count('annotation') == 0
        before = _snapshot(store)
        for operation in store.db.execute('SELECT * FROM tool_operations WHERE name IN (?, ?) ORDER BY rowid',
                ('reads.map', 'sequence.sites')):
            assert tools.execute(operation['name'], json.loads(operation['arguments']), scope=scope,
                operation_key=operation['operation_key']) == json.loads(operation['result'])
        assert _snapshot(store) == before
        def forbidden(*args, **kwargs):
            raise AssertionError('Closed minimap2 site return must use frozen facts')
        monkeypatch.setattr(WorkflowServices, 'alignment_site_own_action_results', forbidden)
        import gene_annotation_episode.alignment_site_calculators as calculators
        monkeypatch.setattr(calculators, 'calculate_reference_site_components', forbidden)
        workflow.scientific_process_binding.validate_report(_context(workflow, decisions.child_id), returned, schema)
        _redeliver_frozen(workflow, parent, decisions.child_id, schema, returned, 1)
        _example('minimap2-quality-ancestry', {'returned': returned, 'retained_grading': retained,
            'counts': {'parent_actions': 1, 'child_actions': 3}, 'source_kind': 'actual_local_minimap2'})


@pytest.mark.parametrize('request_sites', [False, True])
def test_no_site_request_does_not_read_sites_and_requested_unexecuted_source_is_empty(
        tmp_path, monkeypatch, request_sites):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']
        tools = ToolRegistry(store, clients=LocalOnly())
        directory = tmp_path / 'run'
        descriptor, library = _descriptor(directory, tools)
        scope = store.validate_scope({'subject_refs': [target]})
        schema = _site_form(REFERENCE) if request_sites else deepcopy(RETURN_FORM)
        calls = []
        original = WorkflowServices.alignment_site_own_action_results
        def observe(self, context, **kwargs):
            assert request_sites, 'A non-site form must not read any site records'
            calls.append(deepcopy(kwargs))
            return original(self, context, **kwargs)
        monkeypatch.setattr(WorkflowServices, 'alignment_site_own_action_results', observe)
        class Choices:
            child_id = None
            async def complete(self, episode_id, role, instructions, current, output_schema):
                if 'scientific_process' not in current:
                    return _commission(library, scope, ['sequence.inspect'], [target], schema)
                self.child_id = episode_id
                return selected('sequence.inspect', {'subject_ref': target})
            async def release(self, episode_id):
                pass
        decisions = Choices()
        workflow = Workflow(store, tools, decisions, directory, 'alignment-unrequested',
            _controller({'annotation': 1, 'scientific_process': 1}), zero_fixture_credit,
            episode_binding_descriptors=[descriptor], episode_record_receipts=True,
            initial_known_record_refs=[])
        parent = workflow.build('annotation', 'root', 'Inspect supplied composition', scope)
        _run(parent, workflow)
        saved = workflow.journal.row('runtime_forms', decisions.child_id)
        returned, facts = json.loads(saved['form']), json.loads(saved['facts'])
        if request_sites:
            assert returned == {'selected_sites': []} and facts[REFERENCE] == []
            assert calls and all(row['source'] == REFERENCE for row in calls)
        else:
            assert returned['records'] and REFERENCE not in facts and BLAST not in facts
            assert calls == []
        _assert_action_counts(store, decisions.child_id, 1)
        _assert_action_counts(store, parent.source.episode_id, 1)
        assert store.count('annotation') == 0
