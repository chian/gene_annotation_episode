"""Joined selection/construction/execution/receipt tests; no live model or API.

The supplied target and retained count response are inputs, not evidence of a
new biological relationship. A101 and P01 are used unchanged. Count acquisition
does not assert homology, annotation support, or scientific completion.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.bvbrc_data_calculators import calculate_page_counts
from gene_annotation_episode.bvbrc_data_schema import json_digest
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

from bvbrc_selected_process_fixture import (
    PUBLICATION, SELECTED_TOOLS, RetainedHTTP, SelectedProcessRun, count_form,
)


def materialized(context, fact_source):
    return next(item for item in context['received_bvbrc_values']
                if item['fact_source'] == fact_source)


def episode_rows(run):
    """Row order is not part of a SQL query without ORDER BY."""
    rows = run.rows('runtime_episodes')
    keyed = {(row['run_id'], row['episode_id']): row for row in rows}
    assert len(keyed) == len(rows)
    return keyed


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def assert_joined_path(run, http):
    root = run.archive
    scientific = root['units'][0]['child']
    launch = scientific['units'][0]['child']
    api = launch['units'][0]['child']
    results = scientific['units'][1]['child']
    assert len(http.calls) == 1
    assert root['units_consumed'] == 2 and scientific['units_consumed'] == 3
    for closed, count in ((root, 2), (scientific, 3), (launch, 1), (api, 1), (results, 1)):
        assert len(run.rows('runtime_actions', closed['episode_id'])) == count
        assert len(run.rows('runtime_observations', closed['episode_id'])) == count
        assert len(run.rows('runtime_model_calls', closed['episode_id'])) == count
    for closed, gain in ((launch, 3), (api, 3), (results, 2)):
        assert closed['units_consumed'] == 1
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert closed['units'][0]['controller_step']['marginal_credit'] == gain
    for closed in (root, scientific):
        assert all(unit['controller_step']['marginal_credit'] == 0 for unit in closed['units'])
    assert run.store.count('annotation') == run.store.count('observation') == 0
    assert run.workflow.catalog(run.scope, source=run.episode.source) == []

    context = run.scientific_after_result
    count, = materialized(context, 'execution_bvbrc_counts')['facts']
    page, = materialized(context, 'execution_bvbrc_pages')['facts']
    assert count['reported_value'] == 2 and type(count['reported_value']) is int
    assert count['exactness'] == 'exact' and count['availability'] == 'available'
    assert page['returned_row_count'] == 0 and page['reported_total'] == 2
    assert page['mode'] == 'count' and page['unavailable_reason'] is None
    assert count['source_ref'] == page['source_ref']
    assert count['population_ref'] == page['population_ref']
    assert set(run.received_form) == {'completed', 'references', 'yield', 'counts', 'pages'}
    assert run.received_form['counts'] == [count]
    assert run.received_form['pages'] == [page]
    assert run.received_form['completed'] is True

    sci_context = run.context(scientific['episode_id'])
    frozen = plain(sci_context.request['message']['episode_assignment']['selection'])
    original_tools = run.workflow.scientific_process_binding.tool_library.resolve_tool_info(
        SELECTED_TOOLS, available_catalog=run.workflow.services.tool_information_catalog(run.scope))
    assert frozen['version'] == 'scientific_process_selection_v3'
    assert frozen['evidence_axis'] == run.library.reference('A101')
    assert frozen['thought_pattern'] == run.library.reference('P01')
    assert frozen['child_tool_info'] == original_tools
    assert all(set(tool) == {'name', 'description', 'resources', 'instructions'} for tool in original_tools)
    assert context['scientific_process']['child_tool_info'] == original_tools
    assert context['scientific_process']['selection']['child_tool_info'] == SELECTED_TOOLS
    for option in ('A101', 'P01'):
        assert (run.directory / 'scientific-process-library/entries' / (option + '.json')).read_bytes() == (
            PUBLICATION / 'entries' / (option + '.json')).read_bytes()
    saved = run.workflow.journal.row('runtime_model_calls', scientific['episode_id'], 2)
    assert json.loads(saved['request'])['context'] == context
    filled = plain(sci_context.request['message']['scientific_process'])
    assert filled['version'] == 'filled_scientific_process_v1'
    assert filled['selection'] == frozen
    assert filled['mechanics_binding'] == run.descriptor
    direct = run.workflow.scientific_process_binding.catalog(sci_context)
    assert not set(tool['name'] for tool in original_tools) & {row['name'] for row in direct}
    resolution = run.workflow.scientific_process_binding.tool_library.resolve_invocations(
        original_tools, available_catalog=run.workflow.services.tool_information_catalog(run.scope))
    by_name = {row['name']: row for row in resolution}
    assert by_name['api.bvbrc.data.query']['invocation_route'] == {
        'kind': 'commission', 'routes': [{'entry_role': 'launch',
            'resource_id': 'bvbrc', 'resource_role': 'launch_api'}]}
    assert by_name['api.bvbrc.data.result']['invocation_route'] == {
        'kind': 'commission', 'routes': [{'entry_role': 'results',
            'resource_id': 'bvbrc', 'resource_role': 'results'}]}
    assert plain(run.context(api['episode_id']).assignment) == run.api_assignment

    reference, = run.received_form['references']
    owned = run.api.read_bvbrc_result(reference, context=run.context(results['episode_id']))
    admitted = run.api.read_bvbrc_result(reference, context=sci_context)
    assert owned['host_qualification']['possession_basis'] == 'own_completed_action'
    assert admitted['host_qualification']['possession_basis'] == 'admitted_return'
    binding, grading = owned['binding'], owned['grading']
    source = run.store.get(reference)
    assert source['artifact_ref'] == binding['native_artifact_ref']
    assert source['auxiliary_artifact_refs'] == [binding['grading_artifact_ref']]
    assert run.store.get_artifact(binding['native_artifact_ref']) == http.body
    assert binding['native_sha256'] == hashlib.sha256(http.body).hexdigest() == http.metadata['sha256']
    retained = json.loads(run.store.get_artifact(binding['grading_artifact_ref']))
    assert retained['grading'] == grading
    assert grading['parse_result']['sheet']['rows'] == []
    assert grading['parse_result']['sheet']['count']['reported_value'] == 2
    assert grading['selector'] == run.selection
    assert grading['prepared']['original_request'] == run.query
    assert grading['prepared']['native_request']['url'] == http.calls[0]['url']
    assert binding['selector_sha256'] == digest(run.selection)
    assert binding['acquisition_assignment_sha256'] == digest(run.context(results['episode_id']).assignment)
    assert grading['parse_result']['sheet']['custody']['prepared_sha256'] == json_digest(grading['prepared'])
    assert calculate_page_counts(grading['parse_result']['sheet']) == grading['page_components']
    admission = next(row for row in run.rows('runtime_bvbrc_admissions')
        if row['receiver_episode_id'] == scientific['episode_id'])
    attempt = next(row for row in run.rows('runtime_report_attempts')
        if row['child_episode_id'] == results['episode_id'])
    assert attempt['failure'] is None
    assert json.loads(admission['original_schema']) == run.result_form
    assert json.loads(admission['form']) == run.received_form
    assert admission['operation_key'] == f'{run.run_id}:{scientific["episode_id"]}:{attempt["decision_index"]}:typed_form'
    summary = {'verification': 'scripted engineering choices; retained HTTP response; no live model or API',
        'evidence_axis': 'A101', 'thought_pattern': 'P01', 'tool_names': [row['name'] for row in original_tools],
        'tool_info_fields': sorted(original_tools[0]), 'reported_count': count['reported_value'],
        'returned_document_rows': page['returned_row_count'], 'http_requests': len(http.calls),
        'native_sha256': binding['native_sha256'], 'native_byte_count': len(http.body),
        'own_actions_and_observations': {'annotation': 2, 'scientific_process': 3,
            'launch': 1, 'launch_api': 1, 'results': 1},
        'final_resource_gain': {'launch': 3, 'launch_api': 3, 'results': 2},
        'future_resource_expectation': 0, 'scientific_credit': 0,
        'source_ref': reference, 'full_grading_artifact_ref': binding['grading_artifact_ref']}
    for name, value in {'verification_summary': summary,
            'scientific_saved_provider_request': json.loads(saved['request']),
            'scientific_original_request': plain(sci_context.request),
            'results_typed_return': run.received_form, 'published_grading': grading,
            'http_response_replay': {'historical_metadata': http.metadata,
                'current_requests': http.calls, 'live_request_performed': False}}.items():
        (run.directory / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(summary, sort_keys=True))
    return scientific, results, reference, grading


def test_selected_process_receives_actual_count_and_frozen_four_field_tools(tmp_path, monkeypatch):
    http = RetainedHTTP(monkeypatch)
    with Store(tmp_path / 'state') as store:
        run = SelectedProcessRun(store, tmp_path / 'run')
        run.run()
        assert_joined_path(run, http)
        assert run.root_after_result['received_bvbrc_values'] == []
        assert set(run.root_after_result['child_reports'][-1]) == {'references'}
        root_context = run.context(run.archive['episode_id'])
        assert plain(root_context.request)['report_contract'] is None
        assert run.workflow.episode_bindings.received_report_facts(root_context) == {}
        assert not any(name.startswith('execution_bvbrc_')
            for name in run.workflow.facts(run.episode.source))


def test_selected_process_reopen_preserves_frozen_context_admission_and_history(tmp_path, monkeypatch):
    http = RetainedHTTP(monkeypatch)
    with Store(tmp_path / 'state') as store:
        run = SelectedProcessRun(store, tmp_path / 'run')
        run.run()
        scientific, results, reference, grading = assert_joined_path(run, http)
        scope, archived, frozen = deepcopy(run.scope), deepcopy(run.archive), run.frozen_hashes()
        tables = ('runtime_actions', 'runtime_observations', 'runtime_model_calls',
            'runtime_forms', 'runtime_report_attempts', 'runtime_bvbrc_admissions')
        before = {table: run.rows(table) for table in tables}
        original_episodes = episode_rows(run)
        (tmp_path / 'reopen_episodes_before.json').write_text(json.dumps(
            list(original_episodes.values()), indent=2) + '\n')
        original_context = deepcopy(run.scientific_after_result)
    with Store(tmp_path / 'state') as reopened:
        replay = SelectedProcessRun(reopened, tmp_path / 'run', scope=scope)
        async def no_decision(*args, **kwargs):
            raise AssertionError('Reopen attempted a new provider decision')
        replay.complete = no_decision
        assert replay.run() == archived
        assert replay.frozen_hashes() == frozen
        (tmp_path / 'reopen_episodes_after.json').write_text(json.dumps(
            list(episode_rows(replay).values()), indent=2) + '\n')
        assert episode_rows(replay) == original_episodes
        assert {table: replay.rows(table) for table in tables} == before
        assert len(http.calls) == 1
        assert replay.api.read_bvbrc_result(reference, context=replay.context(results['episode_id']))['grading'] == grading
        assert replay.api.received_bvbrc_context(replay.context(scientific['episode_id'])) == original_context['received_bvbrc_values']
        saved = replay.workflow.journal.row('runtime_model_calls', scientific['episode_id'], 2)
        assert json.loads(saved['request'])['context'] == original_context


def test_selected_process_forwards_only_parent_requested_count(tmp_path, monkeypatch):
    """Keep the onward boundary independent from the already received values."""
    http = RetainedHTTP(monkeypatch)
    with Store(tmp_path / 'state') as store:
        run = SelectedProcessRun(store, tmp_path / 'run', parent_form=count_form())
        run.run()
        scientific, _, reference, _ = assert_joined_path(run, http)
        returned = run.root_after_result['child_reports'][-1]
        assert set(returned) == {'counts'}
        assert returned['counts'] == run.received_form['counts']
        values = run.root_after_result['received_bvbrc_values']
        assert len(values) == 1 and values[0]['fact_source'] == 'execution_bvbrc_counts'
        assert values[0]['facts'][0]['reported_value'] == 2
        assert values[0]['facts'][0]['source_ref'] == reference
        assert values[0]['cells'] == []
        assert run.api.read_bvbrc_result(reference, context=run.context(run.archive['episode_id']))[
            'host_qualification']['possession_basis'] == 'admitted_return'
        assert {row['receiver_episode_id'] for row in run.rows('runtime_bvbrc_admissions')} == {
            scientific['episode_id'], run.archive['episode_id']}
        assert 'instructions' not in returned and 'yield' not in returned
        root_request = json.loads(run.workflow.journal.row('runtime_model_calls',
            run.archive['episode_id'], 1)['request'])
        assert root_request['context'] == run.root_after_result
        root_strings = tuple(strings(root_request['context']))
        for info in run.scientific_after_result['scientific_process']['child_tool_info']:
            assert not any(info['instructions'] in value for value in root_strings)
        (run.directory / 'root_saved_provider_request.json').write_text(json.dumps(root_request, indent=2) + '\n')
        (run.directory / 'root_typed_return.json').write_text(json.dumps(returned, indent=2) + '\n')
        forged = deepcopy(returned)
        forged['counts'][0]['reported_value'] = 999
        before = {table: run.rows(table) for table in
            ('runtime_actions', 'runtime_observations', 'runtime_bvbrc_admissions')}
        with pytest.raises(ReportBoundaryError) as rejected:
            run.workflow.validate_report(forged, run.scope, grain='scientific_process',
                schema=count_form(), context=run.context(scientific['episode_id']))
        assert rejected.value.diagnostic['code'] == 'bvbrc_recorded_facts_mismatch'
        assert before == {table: run.rows(table) for table in before}
        (run.directory / 'forged_count_rejection.json').write_text(json.dumps(
            rejected.value.diagnostic, indent=2) + '\n')
