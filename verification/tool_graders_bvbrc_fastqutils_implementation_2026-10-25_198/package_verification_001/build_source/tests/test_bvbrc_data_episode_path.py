"""Actual BV-BRC v2 Workflow/communication checks with labeled engineering choices.

Only the transport response and root choices/continuation are fixtures. Resource
endpoints use the production estimator, and every qualified result comes from
real selected actions, artifacts and host custody checks. No network, configured
model, scientific annotation, or rendered-prompt verification is claimed.
"""
import asyncio
import hashlib
import json

import pytest

from gene_annotation_episode.bvbrc_data_calculators import calculate_page_counts, calculate_facet_fractions
from gene_annotation_episode.bvbrc_data_schema import json_digest
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

from bvbrc_episode_fixture import (
    EpisodeRun, PartialDecisionReached, Transport, envelope, request,
    result_form, retained_bytes, rows_selector, selector,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('BV-BRC episode engineering verification attempted network access')
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)


def received(run, name):
    return next(value for value in run.parent_after_result['received_bvbrc_values']
                if value['fact_source'] == 'execution_bvbrc_' + name)


def assert_custody_and_endpoint(run, transport, body):
    archived = run.archive
    launch = archived['units'][0]['child']
    api = launch['units'][0]['child']
    results = archived['units'][1]['child']
    root = archived['episode_id']
    for closed in (launch, api, results):
        assert closed['units_consumed'] == 1
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert closed['units'][0]['controller_step']['marginal_credit'] > 0
        assert len(run.rows('runtime_observations', closed['episode_id'])) == 1
        assert len(run.rows('runtime_actions', closed['episode_id'])) == 1
        assert len(run.rows('runtime_model_calls', closed['episode_id'])) == 1
    assert archived['units_consumed'] == 3
    assert len(run.rows('runtime_observations', root)) == 3
    assert len(transport.prepared) == 1  # Result acquisition reuses the original GET.
    returned = run.received_forms[0]
    assert returned['completed'] is True
    reference, = returned['references']
    owned = run.api.read_bvbrc_result(reference, context=run.context(results['episode_id']))
    admitted = run.api.read_bvbrc_result(reference, context=run.context(root))
    assert owned['host_qualification']['possession_basis'] == 'own_completed_action'
    assert admitted['host_qualification']['possession_basis'] == 'admitted_return'
    binding, grading = owned['binding'], owned['grading']
    source = run.store.get(reference)
    assert source['artifact_ref'] == binding['native_artifact_ref']
    assert source['auxiliary_artifact_refs'] == [binding['grading_artifact_ref']]
    assert run.store.get_artifact(source['artifact_ref']) == body
    assert binding['native_sha256'] == hashlib.sha256(body).hexdigest()
    retained = json.loads(run.store.get_artifact(binding['grading_artifact_ref']))
    assert retained['grading'] == grading
    assert retained['native_artifact_ref'] == binding['native_artifact_ref']
    assert grading['prepared'] == transport.prepared[0]
    assert grading['selector'] == run.selection
    assert binding['acquisition_assignment_sha256'] == digest(run.context(results['episode_id']).assignment)
    assert binding['selector_sha256'] == digest(run.selection)
    assert grading['parse_result']['sheet']['custody']['prepared_sha256'] == json_digest(grading['prepared'])
    action_key = f'{run.workflow.run_id}:{results["episode_id"]}:0'
    directory = run.api._episode_directory(results['episode_id']) / 'actions' / digest(action_key)
    intent = json.loads((directory / 'intent.json').read_text())
    acquisition = json.loads((directory / 'acquisition.json').read_text())
    inputs = json.loads((directory / 'publication_inputs.json').read_text())
    assert intent['prepared']['prepared_query'] == grading['prepared']
    assert acquisition['record_refs'] == [reference]
    assert acquisition['snapshot_sha256'] == binding['native_sha256']
    assert acquisition['publication_inputs_sha256'] == json_digest(inputs)
    assert inputs['input_results'] == [] and inputs['metadata_bindings'] == []
    assert inputs['prepared'] == grading['prepared']
    saved = run.workflow.journal.row('runtime_model_calls', root, 2)
    assert json.loads(saved['request'])['context']['received_bvbrc_values'] == run.parent_after_result['received_bvbrc_values']
    admissions = run.rows('runtime_bvbrc_admissions')
    assert len(admissions) == 1
    admission = admissions[0]
    assert admission['receiver_episode_id'] == root
    assert json.loads(admission['original_schema']) == run.form
    assert json.loads(admission['form']) == returned
    attempts = run.rows('runtime_report_attempts')
    attempt = next(row for row in attempts if row['child_episode_id'] == results['episode_id'])
    assert attempt['failure'] is None
    assert admission['operation_key'] == f'{run.workflow.run_id}:{root}:{attempt["decision_index"]}:typed_form'
    assert calculate_page_counts(grading['parse_result']['sheet']) == grading['page_components']
    assert run.store.count('annotation') == run.store.count('observation') == 0
    assert all(unit['controller_step']['marginal_credit'] == 0 for unit in archived['units'])
    return results, reference, owned


def test_count_two_with_no_docs_reaches_real_parent_and_replays_without_get(tmp_path, monkeypatch):
    body = retained_bytes('feature_count_solr')
    transport = Transport(monkeypatch, [body])
    with Store(tmp_path / 'state') as store:
        run = EpisodeRun(store, tmp_path / 'run', request(), selector(),
            result_form('execution_bvbrc_pages', 'execution_bvbrc_counts'))
        run.run()
        results, reference, owned = assert_custody_and_endpoint(run, transport, body)
        counts = received(run, 'counts')['facts']
        assert len(counts) == 1
        assert counts[0]['reported_value'] == 2
        assert counts[0]['exactness'] == 'exact'
        assert counts[0]['availability'] == 'available'
        assert received(run, 'pages')['facts'][0]['returned_row_count'] == 0
        assert owned['grading']['parse_result']['sheet']['rows'] == []
        context = run.context(results['episode_id'])
        before = {name: run.rows(name) for name in ('runtime_actions', 'runtime_observations', 'runtime_bvbrc_admissions')}
        original = json.loads(run.rows('runtime_actions', results['episode_id'])[0]['result'])
        original.pop('pending_work_after_action', None)
        replay = asyncio.run(run.api.execute(context, 'api.bvbrc.data.result', {},
            f'{run.workflow.run_id}:{context.episode_id}:0'))
        assert replay == original
        assert len(transport.prepared) == 1
        assert before == {name: run.rows(name) for name in before}
        known = {'version': 'episode_record_selection_v1', 'known_record_refs': [reference],
            'initial_known_record_refs': [reference]}
        credit = run.api.credit_view(context, known)
        assert credit['credit'] == credit['new_acquired_record_count'] == 0
        assert credit['operational_credit_binding']['scientific_credit'] is False


def test_numeric_and_metadata_values_materialize_at_saved_parent_decision(tmp_path, monkeypatch):
    rows = json.loads(retained_bytes('expression_page'))
    # Retained measurements in an explicitly synthetic Solr envelope. A separate
    # synthetic zero count is added solely to verify zero versus response absence.
    rows[0]['counts'] = 0
    body = envelope(rows)
    transport = Transport(monkeypatch, [body])
    fields = ['id', 'feature_id', 'exp_id', 'bioset_id', 'counts', 'tpm', 'log2_fc',
              'z_score', 'treatment_duration', 'treatment_name']
    selection = rows_selector(rows=(0, 1), numbers=('counts', 'tpm', 'log2_fc', 'z_score'),
        metadata=('feature_id', 'exp_id', 'bioset_id', 'treatment_duration', 'treatment_name'))
    with Store(tmp_path / 'state') as store:
        run = EpisodeRun(store, tmp_path / 'run', request('bioset_result', mode='page', fields=fields),
            selection, result_form('execution_bvbrc_numeric_rows'))
        run.run()
        _, _, owned = assert_custody_and_endpoint(run, transport, body)
        value = received(run, 'numeric_rows')
        first, second = value['facts']
        assert first['native_id'] == rows[0]['id']
        assert second['native_id'] == rows[1]['id']
        assert {m['field']: m['value'] for m in first['measurements']} == {
            'counts': 0, 'log2_fc': -.132, 'z_score': -.544}
        assert {m['field']: m['value'] for m in second['measurements']} == {
            'log2_fc': -.129, 'z_score': -.556}
        assert first['unavailable'] == [{'field': 'tpm', 'reason': 'native_field_absent'}]
        assert {'field': 'counts', 'reason': 'native_field_absent'} in second['unavailable']
        text_cells = {(c['native_id'], c['field']): c['atoms'][0]['string_value']
            for c in value['cells'] if c['atoms'] and c['atoms'][0]['kind'] == 'string'}
        assert text_cells[rows[0]['id'], 'treatment_duration'] == '5 mins'
        assert text_cells[rows[0]['id'], 'treatment_name'] == 'S-nitrosoglutathione (GSNO)'
        assert text_cells[rows[1]['id'], 'treatment_name'] == 'glucose'
        assert text_cells[rows[0]['id'], 'feature_id'] == rows[0]['feature_id']
        assert (rows[1]['id'], 'treatment_duration') not in text_cells
        assert len(owned['grading']['parse_result']['sheet']['rows']) == 2


def test_retained_native_facet_values_and_missing_bucket_reach_parent(tmp_path, monkeypatch):
    body = retained_bytes('feature_facet_solr_zero')
    transport = Transport(monkeypatch, [body])
    query = request(mode='facet', facet={'field': 'annotation', 'offset': 0, 'limit': 2,
        'min_count': 1, 'sort': 'index', 'include_missing': True})
    with Store(tmp_path / 'state') as store:
        run = EpisodeRun(store, tmp_path / 'run', query, selector(), result_form('execution_bvbrc_facets'))
        run.run()
        _, _, owned = assert_custody_and_endpoint(run, transport, body)
        values = received(run, 'facets')
        assert [row['count'] for row in values['facts']] == [1, 1, 0]
        assert [row['denominator'] for row in values['facts']] == [2, 2, 2]
        assert [row['fraction'] for row in values['facts']] == [.5, .5, 0]
        assert [row['is_missing_bucket'] for row in values['facts']] == [False, False, True]
        assert [cell['atoms'][0]['string_value'] for cell in values['cells'] if cell['atoms']] == ['PATRIC', 'RefSeq']
        assert values['cells'][-1]['presence'] == 'null'
        assert calculate_facet_fractions(owned['grading']['parse_result']['sheet'],
            denominator_policy='same_response_exact_document_count') == owned['grading']['facet_components']


def test_explicit_second_page_is_one_selected_get_and_delivers_only_requested_page(tmp_path, monkeypatch):
    initial = envelope([{'genome_id': 'first-fixture', 'genome_length': 11}], total=2)
    second = envelope([{'genome_id': 'second-fixture', 'genome_length': 22}], total=2, start=1)
    transport = Transport(monkeypatch, [initial, second])
    query = request('genome', mode='page', fields=['genome_id', 'genome_length'], limit=1)
    selection = rows_selector(numbers=('genome_length',), metadata=('genome_id',), page={'offset': 1, 'limit': 1})
    with Store(tmp_path / 'state') as store:
        run = EpisodeRun(store, tmp_path / 'run', query, selection,
            result_form('execution_bvbrc_pages', 'execution_bvbrc_numeric_rows'))
        run.run()
        assert [value['effective_request']['offset'] for value in transport.prepared] == [0, 1]
        assert received(run, 'pages')['facts'][0]['requested_offset'] == 1
        assert received(run, 'pages')['facts'][0]['population_coverage'] == 'subset'
        row, = received(run, 'numeric_rows')['facts']
        assert row['native_id'] == 'second-fixture'
        assert row['measurements'][0]['value'] == 22
        result = run.archive['units'][1]['child']
        assert result['units_consumed'] == 1
        assert result['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        context = run.context(result['episode_id'])
        qualified = run.api.read_bvbrc_result(run.received_forms[0]['references'][0], context=context)
        assert qualified['grading']['prepared'] == transport.prepared[1]
        assert qualified['grading']['prepared']['original_request'] == query
        assert store.get_artifact(qualified['binding']['native_artifact_ref']) == second
        assert len(run.rows('runtime_observations', result['episode_id'])) == 1


def test_repeated_actual_child_delivery_is_deduplicated_without_new_observation(tmp_path, monkeypatch):
    body = retained_bytes('feature_count_solr')
    transport = Transport(monkeypatch, [body])
    with Store(tmp_path / 'state') as store:
        run = EpisodeRun(store, tmp_path / 'run', request(), selector(),
            result_form('execution_bvbrc_pages', 'execution_bvbrc_counts'), redeliver=True)
        run.run()
        assert run.root_calls == 4  # Explicit redelivery is not a new observation.
        root = run.archive['episode_id']
        assert run.archive['units_consumed'] == 3
        assert len(run.rows('runtime_observations', root)) == 3
        assert len(run.rows('runtime_actions', root)) == 3
        assert len(run.rows('runtime_model_calls', root)) == 4
        assert len(run.rows('runtime_bvbrc_admissions')) == 2
        assert run.received_forms[0] == run.received_forms[1]
        assert len(run.parent_after_result['received_bvbrc_values']) == 2
        assert len({value['admission_key'] for value in run.parent_after_result['received_bvbrc_values']}) == 2
        assert len(transport.prepared) == 1
        assert all(unit['controller_step']['marginal_credit'] == 0 for unit in run.archive['units'])


def test_saved_workflow_reconstruction_keeps_admissions_and_closed_observations(tmp_path, monkeypatch):
    body = retained_bytes('feature_count_solr')
    transport = Transport(monkeypatch, [body])
    form = result_form('execution_bvbrc_pages', 'execution_bvbrc_counts')
    with Store(tmp_path / 'state') as store:
        original = EpisodeRun(store, tmp_path / 'run', request(), selector(), form)
        original.run()
        tables = ('runtime_actions', 'runtime_observations', 'runtime_bvbrc_admissions', 'runtime_model_calls')
        saved = {table: original.rows(table) for table in tables}
        root = original.archive['episode_id']
        values = original.api.received_bvbrc_context(original.context(root))

    with Store(tmp_path / 'state') as store:
        restored = EpisodeRun(store, tmp_path / 'run', request(), selector(), form, scope=original.scope)

        async def no_new_decision(*args, **kwargs):
            pytest.fail('Completed workflow reconstruction called a model fixture again')

        monkeypatch.setattr(restored, 'complete', no_new_decision)
        restored.run()
        assert restored.archive == original.archive
        assert {table: restored.rows(table) for table in tables} == saved
        assert restored.api.received_bvbrc_context(restored.context(root)) == values
        assert len(transport.prepared) == 1


def test_reprojection_of_original_response_adds_no_acquired_record_credit(tmp_path, monkeypatch):
    body = envelope([{'genome_id': 'first-fixture', 'genome_length': 11},
                     {'genome_id': 'second-fixture', 'genome_length': 22}])
    transport = Transport(monkeypatch, [body])
    first = rows_selector(rows=(0,), numbers=('genome_length',), metadata=('genome_id',))
    second = rows_selector(rows=(1,), numbers=('genome_length',), metadata=('genome_id',))
    with Store(tmp_path / 'state') as store:
        run = EpisodeRun(store, tmp_path / 'run',
            request('genome', mode='page', fields=['genome_id', 'genome_length']),
            first, result_form('execution_bvbrc_numeric_rows'), following_selection=second)
        run.run()
        first_child = run.archive['units'][1]['child']
        second_child = run.archive['units'][2]['child']
        one, = run.received_forms[0]['references']
        two, = run.received_forms[1]['references']
        assert one != two  # Distinct selected local projections retain distinct custody.
        assert run.api.result_identity(one, run.scope) == run.api.result_identity(two, run.scope)
        assert first_child['units'][0]['controller_step']['marginal_credit'] == 2
        assert second_child['units'][0]['controller_step']['marginal_credit'] == 0
        assert second_child['units_consumed'] == 1
        assert second_child['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert len(transport.prepared) == 1
        materialized = run.parent_after_result['received_bvbrc_values']
        assert [value['facts'][0]['measurements'][0]['value'] for value in materialized] == [11, 22]
        assert len({value['admission_key'] for value in materialized}) == 2
        assert len(run.rows('runtime_observations', second_child['episode_id'])) == 1


@pytest.mark.parametrize('failure', ['native_partial', 'malformed_requested_value'])
def test_partial_result_retains_values_and_does_not_complete_original_endpoint(tmp_path, monkeypatch, failure):
    rows = [{'genome_id': '511145.12', 'genome_length': 4639675, 'gc_content': 50.8},
            {'genome_id': 'synthetic-fixture-genome', 'genome_length': 12, 'gc_content': 0}]
    if failure == 'malformed_requested_value':
        rows[1]['genome_length'] = 'invalid native number'
    body = envelope(rows, partial=failure == 'native_partial')
    transport = Transport(monkeypatch, [body])
    query = request('genome', mode='page', fields=['genome_id', 'genome_length', 'gc_content'])
    selection = rows_selector(rows=(0, 1), numbers=('genome_length', 'gc_content'), metadata=('genome_id',))
    with Store(tmp_path / 'state') as store:
        run = EpisodeRun(store, tmp_path / 'run', query, selection,
            result_form('execution_bvbrc_pages', 'execution_bvbrc_numeric_rows'), partial=True)
        with pytest.raises(PartialDecisionReached):
            run.run()
        result_id = next(row['episode_id'] for row in run.rows('runtime_episodes')
                         if json.loads(row['path'])[-1][0] == 'results')
        context = run.context(result_id)
        actions = run.rows('runtime_actions', result_id)
        assert len(actions) == 1
        outcome = json.loads(actions[0]['result'])
        assert outcome['status'] == 'partial'
        assert outcome['result']['requested_projection_complete'] is False
        assert run.api.completion_for_action(context, f'{run.workflow.run_id}:{result_id}:0') is None
        assert run.result_next_decision['execution_progress']['execution_completed'] is False
        assert len(run.rows('runtime_observations', result_id)) == 1
        assert len(transport.prepared) == 1
        reference, = outcome['record_refs']
        qualified = run.api.read_bvbrc_result(reference, context=context)
        assert store.get_artifact(qualified['binding']['native_artifact_ref']) == body
        assert len(qualified['grading']['parse_result']['sheet']['rows']) == 2
        own = run.result_next_decision['own_bvbrc_values']
        numeric = next(value for value in own if value['fact_source'] == 'execution_bvbrc_numeric_rows')
        assert numeric['facts'][0]['measurements'][0]['value'] == 4639675
        if failure == 'malformed_requested_value':
            assert numeric['facts'][1]['unavailable'] == [
                {'field': 'genome_length', 'reason': 'native_value_invalid'}]
            assert numeric['facts'][1]['measurements'][0]['value'] == 0
        saved = run.workflow.journal.row('runtime_model_calls', result_id, 1)
        assert json.loads(saved['request'])['context']['own_bvbrc_values'] == own
        assert run.result_next_decision['received_bvbrc_values'] == []
        assert run.api.received_bvbrc_context(run.context(result_id)) == []
        assert store.count('annotation') == store.count('observation') == 0
