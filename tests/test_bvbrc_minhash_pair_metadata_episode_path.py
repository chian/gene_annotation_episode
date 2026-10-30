"""V2 MinHash metadata through selected Workflow, saved results and typed returns.

Only scripted choices and the existing urllib response fixture are synthetic.
Actual source registration, material.parse, custody, API ownership, publication,
common calculations, controller observations and receiving boundaries run normally.
These fixtures establish no live service or remote sketch-parameter equivalence.
"""
from copy import deepcopy
from dataclasses import replace
import asyncio
import hashlib
import json

import pytest

from gene_annotation_episode.bvbrc_minhash_views import project_minhash_facts
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

from bvbrc_minhash_episode_fixture import SOURCE_FORM, SyntheticHTTP, fact_form, native_request, request
from bvbrc_minhash_metadata_episode_fixture import (
    FACT_FAMILIES, METADATA_FIELDS, MetadataRun, PartialMetadataResultReached,
    SYNTHETIC_ROWS, SelectedInputFeedbackReached, metadata_result_form, pair,
)
from test_bvbrc_minhash_episode_path import durable_runtime, materialized, temporary_record_change


def closed_path(run):
    root = run.archive
    science = root['units'][0]['child']
    metadata = science['units'][0]['child']
    launch = science['units'][1]['child']
    api = launch['units'][0]['child']
    results = [unit['child'] for unit in science['units'][2:2 + len(run.stages)]]
    return root, science, metadata, launch, api, results


def assert_selected_path(run, http):
    root, science, metadata, launch, api, results = closed_path(run)
    expected = [(root, 2), (science, 3 + len(run.stages)), (metadata, 1),
        (launch, 1), (api, 1), *((result, 1) for result in results)]
    for closed, count in expected:
        assert closed['units_consumed'] == count
        assert len(run.rows('runtime_actions', closed['episode_id'])) == count
        assert len(run.rows('runtime_observations', closed['episode_id'])) == count
        assert len(run.rows('runtime_model_calls', closed['episode_id'])) == (
            count + int(run.redeliver and closed['episode_id'] == science['episode_id']))
    for closed in (launch, api, *results):
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    assert launch['units'][0]['controller_step']['marginal_credit'] == 3
    assert api['units'][0]['controller_step']['marginal_credit'] == 3
    assert [result['units'][0]['controller_step']['marginal_credit'] for result in results] == (
        [2] + [0] * (len(results) - 1))
    for closed in (root, science, metadata):
        assert all(unit['controller_step']['marginal_credit'] == 0 for unit in closed['units'])
    assert run.store.count('annotation') == run.store.count('observation') == 0
    assert len(http.calls) == 1
    rpc = native_request(run.query)
    sent = json.dumps(rpc, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()
    assert http.calls[0]['request'] == rpc
    assert len(rpc['params']) == 8
    assert http.calls[0]['request_sha256'] == hashlib.sha256(sent).hexdigest()
    assert http.calls[0]['request_bytes'] == len(sent)
    assert plain(run.context(api['episode_id']).assignment) == run.api_assignment
    handoff = run.api._read_handoff(run.handoff, run.scope)
    assert handoff['event']['kind'] == 'response' and handoff['event']['native_handle'] == {}
    assert run.api._load_snapshot(handoff['snapshot']).content == http.body

    # This is a genuine selected input action and immediate-child return. The
    # supplied source exists before it is received, without implying custody.
    action, = run.rows('runtime_actions', metadata['episode_id'])
    assert json.loads(action['action']) == {'kind': 'tool', 'tool': 'material.parse',
        'arguments': {'material_ref': run.material_ref, 'format': 'opaque'}}
    outcome = json.loads(action['result'])
    assert outcome['status'] == 'completed'
    assert outcome['result']['parse_attempt']['code'] == 'retained_without_sequence_projection'
    assert run.metadata_source in outcome['record_refs']
    assert run.metadata_source in run.metadata_report['references']
    producer, form, schema = run.api.minhash._attempt(run.context(science['episode_id']), 0)
    assert producer.episode_id == metadata['episode_id']
    assert form == run.metadata_report and schema == SOURCE_FORM
    assert run.store.get_artifact(run.supplied_artifact_ref) == run.input_bytes
    assert all(run.context(result['episode_id']).path[-1][1] == f'child_{2 + index}'
        for index, result in enumerate(results))

    for closed, selected_tools in ((science, run.selected_tools), (metadata, run.metadata_tools)):
        context = run.context(closed['episode_id'])
        frozen = plain(context.assignment)['selection']
        expected_info = run.workflow.scientific_process_binding.tool_library.resolve_tool_info(
            selected_tools, available_catalog=run.workflow.services.tool_information_catalog(run.scope))
        assert frozen['evidence_axis'] == run.library.reference('A101')
        assert frozen['thought_pattern'] == run.library.reference('P01')
        assert frozen['child_tool_info'] == expected_info
        assert all(set(row) == {'name', 'description', 'resources', 'instructions'} for row in expected_info)
        assert all(row['description'] and row['instructions'] for row in expected_info)
    assert run.workflow.catalog(run.scope, source=run.episode.source) == []
    return root, science, metadata, launch, api, results


def assert_publication(run, http, index=0):
    context = run.context(run.result_ids[index])
    reference = run.result_reference(run.received_forms[index])
    qualified = run.api.minhash.read_own(reference, context=context)
    grade = qualified['grading']
    source = run.store.get(reference)
    assert run.store.get_artifact(source['artifact_ref']) == http.body
    artifact = json.loads(run.store.get_artifact(source['auxiliary_artifact_refs'][0]))
    assert artifact['native_artifact_ref'] == source['artifact_ref']
    assert artifact['grading'] == grade
    assert grade['schema'] == 'bvbrc_minhash_grading_v2'
    assert grade['sheet']['schema'] == 'bvbrc_minhash_sheet_v1'
    assert grade['components']['schema'] == 'bvbrc_minhash_components_v1'
    assert grade['request'] == run.query
    assert grade['rpc_request'] == http.request
    assert grade['selector'] == run.selectors[index] == plain(context.assignment)['selector']
    assert grade['sheet']['native_result'] == http.rows
    assert all(value is None for value in grade['sheet']['search_metadata'].values())
    inputs = grade['publication_inputs']
    assert inputs['pair_metadata'] == grade['selector']['pair_metadata']
    expected_bindings = []
    for metadata_index, row in enumerate(inputs['pair_metadata']):
        assert row['provenance']['query_mode'] == run.query['mode']
        assert row['provenance']['query_operand'] == run.query['query']
        assert row['provenance']['native_parameter_equivalence'] == 'unestablished'
        for evidence in row['provenance']['fields']:
            expected_bindings.append({'pair_metadata_index': metadata_index,
                'source_ref': run.metadata_source, 'artifact_ref': run.supplied_artifact_ref,
                'artifact_sha256': hashlib.sha256(run.input_bytes).hexdigest(),
                'field': evidence['field'], 'record_path': evidence['record_path'],
                'value': row[evidence['field']]})
    assert inputs['metadata_bindings'] == expected_bindings
    (directory, outcome), = run.api._own_outcomes(context)
    assert json.loads((directory / 'publication_inputs.json').read_bytes()) == inputs
    assert json.loads((directory / 'acquisition.json').read_bytes())['publication_inputs_sha256'] == digest(inputs)
    assert json.loads((directory / 'publication.json').read_bytes())['result']['source_ref'] == reference
    assert outcome['status'] == 'completed'
    assert run.api.completion_for_action(context, f'{run.run_id}:{context.episode_id}:0') is not None
    requested = tuple(node['x-source'] for node in run.result_form['properties'].values()
        if node.get('x-source') in FACT_FAMILIES)
    projected = project_minhash_facts([qualified], requested_sources=requested)
    for family, rows in projected.items():
        assert rows == run.received_forms[index][family.removeprefix('bvbrc_minhash_')]
    if 'bvbrc_minhash_calculations' in projected:
        for returned, component in zip(projected['bvbrc_minhash_calculations'], grade['components']['rows']):
            for field in ('row_index', 'genome_id', 'shared_hash_fraction', 'recomputed_distance',
                          'unsaturated_distance', 'recomputed_pvalue'):
                assert returned[field] == component[field]
            assert all(returned[field] == component['calculation_inputs'][field] for field in METADATA_FIELDS)
            assert returned['diagnostic_codes'] == [item['code'] for item in component['diagnostics']]
    return reference, grade


def forbid_recalculation_and_transport(monkeypatch, *, metadata=True):
    def forbidden(*args, **kwargs):
        raise AssertionError('Saved publication/read/replay attempted acquisition, extraction or recalculation')
    for module in ('api_bvbrc_minhash', 'bvbrc_minhash_grader'):
        for name in ('parse_minhash_result', 'calculate_minhash_components'):
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name, forbidden)
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc_minhash.BVBRCMinhashService.invoke', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    if metadata:
        monkeypatch.setattr('gene_annotation_episode.bvbrc_minhash_host.BVBRCMinhashHost.publication_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_minhash_host.BVBRCMinhashHost.validate_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_minhash_host.BVBRCMinhashHost.metadata_bindings', forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_minhash_host.BVBRCMinhashHost._pointer', forbidden)


def retained_artifacts(run, references):
    artifacts = set()
    for reference in references:
        source = run.store.get(reference)
        artifacts.update([source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs']])
        request_metadata = json.loads(run.store.get_artifact(source['request_ref']))
        artifacts.add(request_metadata['rpc_request_artifact_ref'])
    return {reference: run.store.get_artifact(reference) for reference in sorted(artifacts)}


@pytest.mark.parametrize('mode', ['genome', 'fasta'])
def test_selected_pair_inputs_reach_common_sheet_and_onward_typed_return(tmp_path, monkeypatch, mode):
    http = SyntheticHTTP(monkeypatch, request(mode), SYNTHETIC_ROWS)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', mode=mode)
        run.run()
        root, science, _, _, _, _ = assert_selected_path(run, http)
        reference, grade = assert_publication(run, http)
        row, = run.received_form['calculations']
        assert row['shared_hash_fraction'] == 2 / 3
        assert row['recomputed_distance'] == row['unsaturated_distance'] == 0.22314355131420976
        assert row['recomputed_pvalue'] == 0.2592592592592592
        assert row['parse_status'] == 'ok'
        assert run.received_form['matches'][0]['reported_distance'] == 0.223144
        assert run.received_form['matches'][0]['reported_pvalue'] == 0.259259
        assert grade['sheet']['native_result'][0][1:] == ['0.223144', '0.259259', '2/3']
        for family in FACT_FAMILIES:
            expected = run.received_form[family.removeprefix('bvbrc_minhash_')]
            assert materialized(run.scientific_after_result, family) == expected
            assert materialized(run.root_after_result, family) == expected
        assert run.api.minhash.read_received_result(reference,
            context=run.context(science['episode_id']))['grading'] == grade
        assert run.api.minhash.resolve_received(run.context(root['episode_id']), '83333.1', 'bvbrc_minhash_genome')
        assert grade['publication_inputs']['saved_result'] is None
        validate_closed_schema(run.result_form)
        validate_closed_schema(run.parent_form)


@pytest.mark.parametrize('metadata, distance', [
    (pair(query_length=None, reference_length=None, alphabet_size=None), 0.22314355131420976),
    (pair(kmer_length=None, query_length=None, reference_length=None, alphabet_size=None), None),
])
def test_explicit_missing_inputs_preserve_fraction_and_native_parse_status(tmp_path, monkeypatch, metadata, distance):
    http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', stages=[[metadata]])
        run.run()
        assert_selected_path(run, http)
        _, grade = assert_publication(run, http)
        row, = run.received_form['calculations']
        assert row['parse_status'] == grade['parse_status'] == 'ok'
        assert row['shared_hash_fraction'] == 2 / 3
        assert row['recomputed_distance'] == distance
        assert row['recomputed_pvalue'] is None
        assert [binding['field'] for binding in grade['publication_inputs']['metadata_bindings']] == (
            ['kmer_length'] if distance is not None else [])
        assert all(row[field] == metadata[field] for field in METADATA_FIELDS)


def test_both_key_joins_preserve_duplicates_reordering_and_unmatched_diagnostics(tmp_path, monkeypatch):
    rows = [*deepcopy(SYNTHETIC_ROWS), *deepcopy(SYNTHETIC_ROWS), ['999.1', '0.5', '0.1', '2/3']]
    metadata = [pair(1, kmer_length=2), pair(0), pair(0), pair(1, '999.1'),
        pair(9), pair(2, '999.1')]
    http = SyntheticHTTP(monkeypatch, request(), rows)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', stages=[metadata])
        run.run()
        assert_selected_path(run, http)
        reference, grade = assert_publication(run, http)
        calculations = run.received_form['calculations']
        assert [row['row_index'] for row in calculations] == [0, 1, 2]
        assert [row['genome_id'] for row in calculations] == ['83333.1', '83333.1', '999.1']
        assert calculations[0]['shared_hash_fraction'] == 2 / 3
        assert calculations[0]['recomputed_distance'] is calculations[0]['recomputed_pvalue'] is None
        assert 'ambiguous_pair_metadata' in calculations[0]['diagnostic_codes']
        assert calculations[1]['kmer_length'] == 2
        assert calculations[1]['recomputed_distance'] == 0.11157177565710488
        assert calculations[1]['recomputed_pvalue'] == 0.10400000000000001
        assert calculations[2]['kmer_length'] == 1
        assert calculations[2]['recomputed_distance'] == 0.22314355131420976
        assert grade['components']['rows'][0]['calculation_inputs']['pair_metadata_candidates'] == (
            grade['publication_inputs']['pair_metadata'][1:3])
        diagnostics = run.received_form['calculation_diagnostics']
        assert diagnostics == [{'source_ref': reference, **row} for row in grade['components']['diagnostics']]
        assert diagnostics[:2] == [
            {'source_ref': reference, 'code': 'pair_metadata_genome_id_mismatch',
             'path': 'pair_metadata[3].genome_id', 'severity': 'error'},
            {'source_ref': reference, 'code': 'pair_metadata_row_index_mismatch',
             'path': 'pair_metadata[4].row_index', 'severity': 'error'}]
        assert materialized(run.root_after_result, 'bvbrc_minhash_calculation_diagnostics') == diagnostics


@pytest.mark.parametrize('rows, metadata, code', [
    ([], [], 'empty_result_completeness_unknown'),
    ([['83333.1', '0', '1', '0/0']], [pair()], 'zero_union_calculations_unavailable'),
])
def test_empty_and_zero_denominator_complete_with_explicit_unavailable_cells(tmp_path, monkeypatch, rows, metadata, code):
    http = SyntheticHTTP(monkeypatch, request(), rows)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', stages=[metadata])
        run.run()
        assert_selected_path(run, http)
        _, grade = assert_publication(run, http)
        assert grade['parse_status'] == 'ok'
        assert run.received_form['counts'][0]['returned_row_count'] == len(rows)
        assert code in [row['code'] for row in run.received_form['calculation_diagnostics']]
        for row in run.received_form['calculations']:
            assert row['shared_hash_fraction'] is row['recomputed_distance'] is row['recomputed_pvalue'] is None


@pytest.mark.parametrize('family', ['bvbrc_minhash_counts', 'bvbrc_minhash_calculations', 'source_only'])
def test_only_requested_result_families_cross_both_receiving_boundaries(tmp_path, monkeypatch, family):
    form = SOURCE_FORM if family == 'source_only' else metadata_result_form(family)
    parent = SOURCE_FORM if family == 'source_only' else fact_form(family)
    http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
    with Store(tmp_path / 'state') as store:
        saved = {'stages': [[pair()], [pair(kmer_length=2)]],
            'stage_modes': ['native_result', 'saved_sheet']} if family == 'source_only' else {}
        run = MetadataRun(store, tmp_path / 'run', parent_form=parent, result_schema=form, **saved)
        run.run()
        root, science, _, launch, _, _ = assert_selected_path(run, http)
        reference, _ = assert_publication(run, http)
        expected = [] if family == 'source_only' else [family]
        for current in (run.scientific_after_result, run.root_after_result):
            assert [row['fact_source'] for row in current['received_minhash_values']] == expected
        for closed in (science, root):
            context = run.context(closed['episode_id'])
            unrequested = [name for name in FACT_FAMILIES if name not in expected]
            assert run.api.minhash.received_facts(context, fact_form(*unrequested)) == {
                name: [] for name in unrequested}
            assert run.api.minhash.resolve_received(context, '83333.1', 'bvbrc_minhash_genome') == (
                family == 'bvbrc_minhash_calculations')
        assert run.api.minhash.received_context(run.context(launch['episode_id'])) == []
        assert run.api.minhash.read_received_result(reference,
            context=run.context(science['episode_id']))['source_ref'] == reference
        if family == 'source_only':
            _, recalculated = assert_publication(run, http, 1)
            assert recalculated['publication_inputs']['saved_result']['source_ref'] == reference
            assert recalculated['components']['rows'][0]['recomputed_distance'] == 0.11157177565710488


def test_selected_saved_sheet_recalculation_and_closed_replay_preserve_original_work(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
    frozen = {}

    def after_first(run):
        reference = run.result_reference(run.received_form)
        frozen['reference'] = reference
        frozen['grade'] = run.api.minhash.read_own(reference,
            context=run.context(run.result_ids[0]))['grading']
        frozen['artifacts'] = retained_artifacts(run, [reference])
        frozen['closed_actions'] = deepcopy(run.rows('runtime_actions', run.result_ids[0]))
        frozen['closed_observations'] = deepcopy(run.rows('runtime_observations', run.result_ids[0]))

        def no_new_native_parse(*args, **kwargs):
            raise AssertionError('Explicit saved-sheet selection independently reparsed native scientific rows')
        # The existing common calculator may call its pure saved-native-data
        # validator. Only a new service-level scientific parse is forbidden.
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc_minhash.parse_minhash_result', no_new_native_parse)
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc_minhash.BVBRCMinhashService.invoke', no_new_native_parse)

    stages = [[pair()], [pair(kmer_length=2)]]
    modes = ['native_result', 'saved_sheet']
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', stages=stages, stage_modes=modes,
            after_first_result=after_first)
        run.run()
        root, science, _, _, api, results = assert_selected_path(run, http)
        first_ref, first_grade = assert_publication(run, http, 0)
        second_ref, second_grade = assert_publication(run, http, 1)
        assert first_ref != second_ref
        assert first_grade == frozen['grade']
        assert retained_artifacts(run, [first_ref]) == frozen['artifacts']
        assert run.rows('runtime_actions', results[0]['episode_id']) == frozen['closed_actions']
        assert run.rows('runtime_observations', results[0]['episode_id']) == frozen['closed_observations']
        saved = second_grade['publication_inputs']['saved_result']
        assert saved['source_ref'] == first_ref
        assert saved['sheet'] == second_grade['sheet'] == first_grade['sheet']
        assert saved['original_components'] == first_grade['components']
        first, second = [form['calculations'][0] for form in run.received_forms]
        assert (first['recomputed_distance'], first['recomputed_pvalue']) == (
            0.22314355131420976, 0.2592592592592592)
        assert (second['recomputed_distance'], second['recomputed_pvalue']) == (
            0.11157177565710488, 0.10400000000000001)
        for grade in (first_grade, second_grade):
            assert grade['sheet']['native_result'] == SYNTHETIC_ROWS
            assert grade['components']['rows'][0]['reported_distance'] == 0.223144
            assert grade['components']['rows'][0]['reported_pvalue'] == 0.259259
        # The unchanged legacy empty-selector identity remains the acquisition
        # basis even though these two publication sources carry different inputs.
        page = digest({'service': 'bvbrc_minhash', 'request': run.query,
            'selector': {}, 'response_sha256': hashlib.sha256(http.body).hexdigest()})
        expected_identity = digest({'page': page, 'record': {'record_type': 'source', 'page': page}})
        assert run.api.result_identity(first_ref, run.scope) == expected_identity
        assert run.api.result_identity(second_ref, run.scope) == expected_identity
        archive, history = deepcopy(run.archive), durable_runtime(run)
        scope, material_ref, hashes = deepcopy(run.scope), run.material_ref, run.frozen_hashes()
        values = {closed['episode_id']: run.api.minhash.received_context(run.context(closed['episode_id']))
            for closed in (science, root)}
        outcomes = {closed['episode_id']: next(run.api._own_outcomes(run.context(closed['episode_id'])))[1]
            for closed in (api, *results)}
        artifacts = retained_artifacts(run, [first_ref, second_ref])

    forbid_recalculation_and_transport(monkeypatch)
    with Store(tmp_path / 'state') as reopened:
        replay = MetadataRun(reopened, tmp_path / 'run', stages=stages, stage_modes=modes,
            scope=scope, material_ref=material_ref)

        async def no_decision(*args, **kwargs):
            raise AssertionError('Closed replay requested another provider decision')
        replay.complete = no_decision
        assert replay.run() == archive
        assert replay.frozen_hashes() == hashes
        assert retained_artifacts(replay, [first_ref, second_ref]) == artifacts
        for reference, closed, grade in zip((first_ref, second_ref), results, (first_grade, second_grade)):
            assert replay.api.minhash.read_own(reference,
                context=replay.context(closed['episode_id']))['grading'] == grade
        for episode_id, expected in values.items():
            assert replay.api.minhash.received_context(replay.context(episode_id)) == expected
        for closed in (api, *results):
            context = replay.context(closed['episode_id'])
            operation = 'api.bvbrc.minhash.genome' if closed is api else 'api.bvbrc.minhash.result'
            assert asyncio.run(replay.api.execute(context, operation, {},
                f'{replay.run_id}:{context.episode_id}:0')) == outcomes[context.episode_id]
        assert durable_runtime(replay) == history
        assert len(http.calls) == 1


def test_changed_native_metadata_selector_keeps_one_original_acquisition(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', stages=[[pair()], [pair(kmer_length=2)]])
        run.run()
        assert_selected_path(run, http)
        first_ref, first = assert_publication(run, http, 0)
        second_ref, second = assert_publication(run, http, 1)
        assert first_ref != second_ref
        assert first['sheet'] == second['sheet']
        assert first['publication_inputs']['saved_result'] is second['publication_inputs']['saved_result'] is None
        assert first['components']['rows'][0]['recomputed_distance'] == 0.22314355131420976
        assert second['components']['rows'][0]['recomputed_distance'] == 0.11157177565710488
        assert run.api.result_identity(first_ref, run.scope) == run.api.result_identity(second_ref, run.scope)
        assert run.api.minhash.read_own(first_ref,
            context=run.context(run.result_ids[0]))['grading'] == first
        assert len(http.calls) == 1


def test_received_unrelated_source_cannot_replace_saved_minhash_result(tmp_path, monkeypatch):
    def select_unrelated(index, selector):
        if index == 1:
            selector['saved_result_ref'] = selector['pair_metadata'][0]['provenance']['fields'][0]['source_ref']
        return selector
    original = {}

    def retain_first(run):
        original['reference'] = run.result_reference(run.received_form)
        original['artifacts'] = retained_artifacts(run, [original['reference']])
        original['actions'] = deepcopy(run.rows('runtime_actions', run.result_ids[0]))
        original['observations'] = deepcopy(run.rows('runtime_observations', run.result_ids[0]))

    http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', stages=[[pair()], [pair(kmer_length=2)]],
            stage_modes=['native_result', 'saved_sheet'], selector_transform=select_unrelated,
            expect_feedback=True, after_first_result=retain_first)
        with pytest.raises(SelectedInputFeedbackReached):
            run.run()
        assert 'minhash_saved_result_not_received' in json.dumps(run.feedback_context['feedback'])
        assert run.metadata_source in json.dumps(run.feedback_context['feedback'])
        assert len(run.result_ids) == 1
        assert retained_artifacts(run, [original['reference']]) == original['artifacts']
        assert run.rows('runtime_actions', run.result_ids[0]) == original['actions']
        assert run.rows('runtime_observations', run.result_ids[0]) == original['observations']
        assert len(run.rows('runtime_observations', run.scientific_episode_id)) == 3
        assert run.store.get_artifact(run.supplied_artifact_ref) == run.input_bytes
        assert len(http.calls) == 1


def test_selected_redelivery_reuses_closed_facts_without_an_observation(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
    saved = {}

    def freeze_before_redelivery(run):
        episode_id = run.result_ids[0]
        saved['actions'] = deepcopy(run.rows('runtime_actions', episode_id))
        saved['observations'] = deepcopy(run.rows('runtime_observations', episode_id))
        forbid_recalculation_and_transport(monkeypatch)

    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', redeliver=True,
            after_first_result=freeze_before_redelivery)
        run.run()
        _, science, _, _, _, results = assert_selected_path(run, http)
        assert run.redelivered_form == run.received_form
        assert run.rows('runtime_actions', results[0]['episode_id']) == saved['actions']
        assert run.rows('runtime_observations', results[0]['episode_id']) == saved['observations']
        attempts = list(store.db.execute('SELECT decision_index FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND child_episode_id=? ORDER BY decision_index',
            (run.run_id, science['episode_id'], results[0]['episode_id'])))
        assert [row[0] for row in attempts] == [2, 3]
        assert len(materialized(run.scientific_after_result, 'bvbrc_minhash_calculations')) == 1
        assert len(http.calls) == 1


def test_invalid_selected_pointer_preserves_source_and_native_handoff_without_acquisition(tmp_path, monkeypatch):
    def invalid_pointer(index, selector):
        selector['pair_metadata'][0]['provenance']['fields'][0]['record_path'] = '/stages/99/0/kmer_length'
        return selector
    http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', selector_transform=invalid_pointer,
            expect_feedback=True)
        with pytest.raises(SelectedInputFeedbackReached):
            run.run()
        assert 'minhash_metadata_pointer_unavailable' in json.dumps(run.feedback_context['feedback'])
        assert run.metadata_source in json.dumps(run.feedback_context['feedback'])
        assert 'kmer_length' in json.dumps(run.feedback_context['feedback'])
        assert run.result_ids == []
        assert len(run.rows('runtime_observations', run.scientific_episode_id)) == 2
        assert store.get_artifact(run.supplied_artifact_ref) == run.input_bytes
        handoff = run.api._read_handoff(run.handoff, run.scope)
        assert run.api._load_snapshot(handoff['snapshot']).content == http.body
        assert list(store.db.execute("SELECT id FROM records WHERE record_type='source' "
            "AND json_extract(data,'$.provider')='bvbrc_minhash'")) == []
        assert len(http.calls) == 1


def test_partial_native_neighbors_retain_numbers_and_two_dimensional_diagnostics(tmp_path, monkeypatch):
    rows = [SYNTHETIC_ROWS[0], ['83333.1', None, '0.2', '0/0'],
        ['999.1', '0.3', '0.4', 'malformed'], [None, '0.1', '0.2', '2/3']]
    http = SyntheticHTTP(monkeypatch, request(), rows)
    with Store(tmp_path / 'state') as store:
        run = MetadataRun(store, tmp_path / 'run', partial=True,
            stages=[[pair(), pair(1), pair(2, '999.1')]])
        with pytest.raises(PartialMetadataResultReached):
            run.run()
        context = run.context(run.partial_episode_id)
        action, = run.rows('runtime_actions', context.episode_id)
        assert len(run.rows('runtime_observations', context.episode_id)) == 1
        outcome = json.loads(action['result'])
        assert outcome['status'] == 'partial'
        reference = outcome['result']['source_ref']
        grade = run.api.minhash.read_own(reference, context=context)['grading']
        facts = run.api.minhash.facts(context, run.result_form)
        values = facts['bvbrc_minhash_calculations']
        assert [row['row_index'] for row in values] == [0, 1, 2, 3]
        assert values[0]['recomputed_distance'] == 0.22314355131420976
        assert values[0]['recomputed_pvalue'] == 0.2592592592592592
        assert all(row['recomputed_distance'] is row['recomputed_pvalue'] is None for row in values[1:])
        assert values[3]['genome_id'] is None
        diagnostics = facts['bvbrc_minhash_calculation_diagnostics']
        assert diagnostics == [{'source_ref': reference, **row} for row in grade['components']['diagnostics']]
        assert {'source_ref': reference, 'code': 'null_native_field',
            'path': 'native_result[1][1]', 'severity': 'error'} in diagnostics
        assert grade['sheet']['native_result'] == rows
        assert store.get_artifact(store.get(reference)['artifact_ref']) == http.body
        assert run.api.completion_for_action(context, f'{run.run_id}:{context.episode_id}:0') is None
        assert run.partial_context['execution_progress']['execution_completed'] is False
        assert run.api.minhash.received_context(run.context(run.scientific_episode_id)) == []
        assert len(http.calls) == 1


@pytest.fixture(scope='module')
def qualified_metadata_workflow(tmp_path_factory):
    directory = tmp_path_factory.mktemp('minhash-metadata-custody-workflow')
    with pytest.MonkeyPatch.context() as monkeypatch, Store(directory / 'state') as store:
        http = SyntheticHTTP(monkeypatch, request(), SYNTHETIC_ROWS)
        run = MetadataRun(store, directory / 'run')
        run.run()
        assert_selected_path(run, http)
        assert_publication(run, http)
        yield run, http


def test_metadata_input_authority_requires_original_immediate_child_and_receiver(qualified_metadata_workflow):
    run, http = qualified_metadata_workflow
    root, science, producer, launch, _, results = closed_path(run)
    selector = run.selectors[0]
    history = durable_runtime(run)
    for closed in (root, launch):
        with pytest.raises(ValueError, match='minhash_metadata_source_not_received'):
            run.api.minhash.validate_inputs(run.context(closed['episode_id']), selector,
                request=run.query, handoff_ref=run.handoff)
    key = (run.run_id, science['episode_id'], 0)
    with temporary_record_change(run.store,
            'UPDATE runtime_report_attempts SET failure=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (json.dumps({'code': 'synthetic_failed_delivery'}), *key)):
        with pytest.raises(ValueError, match='minhash_metadata_source_not_received'):
            run.api.minhash.validate_inputs(run.context(results[0]['episode_id']), selector,
                request=run.query, handoff_ref=run.handoff)
    with temporary_record_change(run.store,
            'UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0',
            (run.run_id, producer['episode_id'])):
        with pytest.raises(ValueError, match='minhash_metadata_source_not_received'):
            run.api.minhash.validate_inputs(run.context(results[0]['episode_id']), selector,
                request=run.query, handoff_ref=run.handoff)
    assert durable_runtime(run) == history
    assert len(http.calls) == 1


def test_forged_returned_calculation_and_diagnostic_are_rejected_without_history_change(qualified_metadata_workflow):
    run, http = qualified_metadata_workflow
    history = durable_runtime(run)
    for field, replacement in (('recomputed_distance', 0.8), ('kmer_length', 9)):
        forged = deepcopy(run.received_form)
        forged['calculations'][0][field] = replacement
        with pytest.raises(ValueError):
            run.workflow.validate_report(forged, run.scope, grain='results', schema=run.result_form,
                context=run.context(run.result_ids[0]))
    forged = deepcopy(run.received_form)
    forged['calculation_diagnostics'] = [{'source_ref': run.result_reference(forged),
        'code': 'pair_metadata_missing', 'path': 'rows[0].calculation_inputs', 'severity': 'error'}]
    with pytest.raises(ValueError):
        run.workflow.validate_report(forged, run.scope, grain='results', schema=run.result_form,
            context=run.context(run.result_ids[0]))
    assert durable_runtime(run) == history
    assert len(http.calls) == 1


def test_same_selected_action_key_cannot_replay_a_different_selector(qualified_metadata_workflow, monkeypatch):
    run, http = qualified_metadata_workflow
    context = run.context(run.result_ids[0])
    history = durable_runtime(run)
    original, = run.api._own_outcomes(context)
    changed = plain(context.assignment)
    changed['selector']['pair_metadata'][0]['kmer_length'] = 2
    request_record = plain(context.request)
    request_record['message']['episode_assignment'] = changed
    forged = replace(context, assignment=changed, request=request_record)
    forbid_recalculation_and_transport(monkeypatch)
    outcome = asyncio.run(run.api.execute(forged, 'api.bvbrc.minhash.result', {},
        f'{run.run_id}:{context.episode_id}:0'))
    assert outcome['status'] == 'invalid' and outcome['record_refs'] == []
    assert outcome['feedback']['code'] in {
        'practical_immutable_record_conflict', 'api_original_assignment_conflict',
        'api_operation_key_reused_for_different_work'}
    assert next(run.api._own_outcomes(context)) == original
    assert durable_runtime(run) == history
    assert len(http.calls) == 1


def test_unselected_source_and_changed_metadata_bytes_cannot_supply_inputs(qualified_metadata_workflow):
    run, http = qualified_metadata_workflow
    context = run.context(run.scientific_episode_id)
    history = durable_runtime(run)
    # This is an actual caller-supplied material record, deliberately never
    # selected or returned. Merely storing it cannot establish possession.
    unselected = run.store.register_material(data=b'{"kmer_length":1}',
        name='unselected synthetic metadata counterexample', format='opaque', use='evidence')
    selector = deepcopy(run.selectors[0])
    evidence = selector['pair_metadata'][0]['provenance']['fields'][0]
    evidence.update(source_ref=unselected['source_ref'],
        artifact_ref=run.store.get(unselected['source_ref'])['artifact_ref'], record_path='/kmer_length')
    with pytest.raises(ValueError, match='minhash_metadata_source_not_received') as caught:
        run.api.minhash.validate_inputs(context, selector, request=run.query, handoff_ref=run.handoff)
    assert caught.value.detail['source_ref'] == unselected['source_ref']
    assert caught.value.detail['field'] == 'kmer_length'

    sha = run.supplied_artifact_ref.removeprefix('artifact_')
    path = run.store.path / 'artifacts' / sha[:2] / sha
    original = path.read_bytes()
    try:
        path.write_bytes(original + b' ')
        with pytest.raises(ValueError, match='minhash_metadata_artifact_conflict') as caught:
            run.api.minhash.validate_inputs(context, run.selectors[0],
                request=run.query, handoff_ref=run.handoff)
        assert caught.value.detail['source_ref'] == run.metadata_source
        assert caught.value.detail['field'] == 'kmer_length'
    finally:
        path.write_bytes(original)
    assert run.store.get_artifact(run.supplied_artifact_ref) == run.input_bytes
    assert durable_runtime(run) == history
    assert len(http.calls) == 1
