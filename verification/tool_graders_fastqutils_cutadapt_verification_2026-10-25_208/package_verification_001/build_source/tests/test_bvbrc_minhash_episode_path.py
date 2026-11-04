"""Complete scripted MinHash selection/receipt/return path; no live API or model.

The numerical rows are explicitly synthetic native-shaped inputs. They establish
engineering behavior, not biological similarity or deployed service availability.
"""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json

import pytest

from gene_annotation_episode.bvbrc_minhash_views import project_minhash_facts
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

from bvbrc_minhash_episode_fixture import (
    MinhashRun, NATIVE_ROWS, PUBLICATION, PartialResultDecisionReached,
    SOURCE_FORM, SyntheticHTTP, count_form, fact_form, request,
)


def materialized(context, source):
    return next(item['facts'] for item in context['received_minhash_values']
                if item['fact_source'] == source)


def durable_runtime(run):
    """Compare all run-owned runtime records independently of SQL row ordering."""
    result = {}
    tables = [row[0] for row in run.store.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'runtime_%'")]
    for table in tables:
        columns = {row[1] for row in run.store.db.execute('PRAGMA table_info(' + table + ')')}
        if 'run_id' in columns:
            result[table] = sorted(json.dumps(row, sort_keys=True) for row in run.rows(table))
    return result


@contextmanager
def temporary_record_change(store, sql, operands):
    """Alter this test's own runtime record, then restore the original bytes."""
    store.db.execute('SAVEPOINT minhash_test_counterexample')
    try:
        store.db.execute(sql, operands)
        yield
    finally:
        store.db.execute('ROLLBACK TO minhash_test_counterexample')
        store.db.execute('RELEASE minhash_test_counterexample')


def assert_joined_path(run, http):
    root = run.archive
    scientific = root['units'][0]['child']
    launch = scientific['units'][0]['child']
    api = launch['units'][0]['child']
    results = scientific['units'][1]['child']
    assert len(http.calls) == 1
    for closed, count in ((root, 2), (scientific, 3), (launch, 1), (api, 1), (results, 1)):
        assert closed['units_consumed'] == count
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert len(run.rows(table, closed['episode_id'])) == count
    for closed, gain in ((launch, 3), (api, 3), (results, 2)):
        assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert closed['units'][0]['controller_step']['marginal_credit'] == gain
    for closed in (root, scientific):
        assert [unit['controller_step']['marginal_credit'] for unit in closed['units']] == (
            [0] * closed['units_consumed'])
    assert run.store.count('annotation') == run.store.count('observation') == 0
    assert run.workflow.catalog(run.scope, source=run.episode.source) == []

    sci_context = run.context(scientific['episode_id'])
    results_context = run.context(results['episode_id'])
    frozen = plain(sci_context.assignment)['selection']
    tool_info = run.workflow.scientific_process_binding.tool_library.resolve_tool_info(
        run.selected_tools, available_catalog=run.workflow.services.tool_information_catalog(run.scope))
    assert frozen['version'] == 'scientific_process_selection_v3'
    assert frozen['evidence_axis'] == run.library.reference('A101')
    assert frozen['thought_pattern'] == run.library.reference('P01')
    assert frozen['child_tool_info'] == tool_info
    assert all(set(tool) == {'name', 'description', 'resources', 'instructions'} for tool in tool_info)
    assert all(tool['description'] and tool['instructions'] for tool in tool_info)
    assert run.scientific_after_result['scientific_process']['child_tool_info'] == tool_info
    assert run.scientific_after_result['scientific_process']['selection']['child_tool_info'] == run.selected_tools
    for option in ('A101', 'P01'):
        assert (run.directory / 'scientific-process-library/entries' / (option + '.json')).read_bytes() == (
            PUBLICATION / 'entries' / (option + '.json')).read_bytes()
    direct = run.workflow.scientific_process_binding.catalog(sci_context)
    assert not {row['name'] for row in tool_info} & {row['name'] for row in direct}
    resolution = run.workflow.scientific_process_binding.tool_library.resolve_invocations(
        tool_info, available_catalog=run.workflow.services.tool_information_catalog(run.scope))
    by_name = {row['name']: row for row in resolution}
    assert by_name['api.bvbrc.minhash.' + run.query['mode']]['invocation_route'] == {
        'kind': 'commission', 'routes': [{'entry_role': 'launch',
            'resource_id': 'minhash', 'resource_role': 'launch_api'}]}
    assert by_name['api.bvbrc.minhash.result']['invocation_route'] == {
        'kind': 'commission', 'routes': [{'entry_role': 'results',
            'resource_id': 'minhash', 'resource_role': 'results'}]}
    assert plain(run.context(api['episode_id']).assignment) == run.api_assignment
    assert plain(results_context.assignment) == {'version': 'execution_results_assignment_v1',
        'handoff_ref': run.handoff, 'selector': {}}

    reference, = run.received_form['references']
    assert set(run.received_form) == {'completed', 'references', 'yield', 'matches', 'counts'}
    assert run.received_form['completed'] is True
    qualified = run.api.minhash.read_own(reference, context=results_context)
    assert set(qualified) == {'source_ref', 'grading'}
    assert qualified['source_ref'] == reference
    grading = qualified['grading']
    source = run.store.get(reference)
    assert source['provider'] == 'bvbrc_minhash'
    assert run.store.get_artifact(source['artifact_ref']) == http.body
    grading_ref, = source['auxiliary_artifact_refs']
    artifact = json.loads(run.store.get_artifact(grading_ref))
    assert artifact['native_artifact_ref'] == source['artifact_ref']
    assert artifact['grading'] == grading
    assert grading['schema'] == 'bvbrc_minhash_grading_v1'
    assert grading['request'] == run.query
    assert grading['rpc_request'] == http.calls[0]['request'] == http.request
    assert grading['selector'] == {} and grading['parse_status'] == 'ok'
    assert grading['sheet']['mode'] == run.query['mode']
    assert grading['sheet']['request'] == http.request
    assert grading['sheet']['native_result'] == http.rows == NATIVE_ROWS
    assert [row['row_index'] for row in grading['sheet']['rows']] == [0, 1]
    assert [row['genome_id'] for row in grading['sheet']['rows']] == ['83333.1', '83333.1']
    assert all(value is None for value in grading['sheet']['search_metadata'].values())
    components = grading['components']['rows']
    assert [row['reported_distance'] for row in components] == [0.02, 0.03]
    assert [row['reported_pvalue'] for row in components] == [0.001, 0.002]
    assert [row['shared_hash_fraction'] for row in components] == [0.041, 0.02]
    for row in components:
        assert row['recomputed_distance'] is row['recomputed_pvalue'] is None
        assert row['calculation_inputs']['pair_metadata'] is None
        for field in ('kmer_length', 'query_length', 'reference_length', 'alphabet_size'):
            assert row['calculation_inputs'][field] is None

    requested = project_minhash_facts([qualified], requested_sources=(
        'bvbrc_minhash_matches', 'bvbrc_minhash_counts'))
    assert requested['bvbrc_minhash_matches'] == run.received_form['matches']
    assert requested['bvbrc_minhash_counts'] == run.received_form['counts']
    matches = materialized(run.scientific_after_result, 'bvbrc_minhash_matches')
    counts = materialized(run.scientific_after_result, 'bvbrc_minhash_counts')
    assert matches == run.received_form['matches']
    assert counts == run.received_form['counts']
    assert [row['row_index'] for row in matches] == [0, 1]
    assert [row['genome_id'] for row in matches] == ['83333.1', '83333.1']
    assert matches[0]['reported_distance'] == 0.02
    assert matches[0]['reported_pvalue'] == 0.001
    assert matches[0]['shared_hashes'] == 41
    assert matches[0]['compared_union_hashes'] == 1000
    assert matches[0]['shared_hash_fraction'] == 0.041
    assert counts == [{'source_ref': reference, 'returned_row_count': 2,
        'parse_status': 'ok', 'population_size': None, 'truncated': None}]
    assert all(set(row) == {'source_ref', 'row_index', 'genome_id', 'reported_distance',
        'reported_pvalue', 'shared_hashes', 'compared_union_hashes',
        'shared_hash_fraction', 'parse_status'} for row in matches)

    handoff = run.api._read_handoff(run.handoff, run.scope)
    assert handoff['event']['kind'] == 'response'
    assert handoff['event']['native_handle'] == {}
    assert handoff['event']['state'] == 'completed'
    assert handoff['event']['facts']['population_size'] is None
    assert handoff['event']['facts']['truncated'] is None
    assert run.api._load_snapshot(handoff['snapshot']).content == http.body
    retained_request = json.loads(run.store.get_artifact(source['request_ref']))
    assert retained_request['sha256'] == hashlib.sha256(http.body).hexdigest()
    assert retained_request['transport']['request']['body_sha256'] == http.calls[0]['request_sha256']
    assert json.loads(run.store.get_artifact(retained_request['rpc_request_artifact_ref'])) == http.request
    assert run.api.minhash.resolve_own(results_context, '83333.1', 'bvbrc_minhash_genome')
    assert run.api.minhash.resolve_received(sci_context, '83333.1', 'bvbrc_minhash_genome')
    for episode_id, snapshot in ((scientific['episode_id'], run.scientific_after_result),
                                (root['episode_id'], run.root_after_result)):
        index = 2 if episode_id == scientific['episode_id'] else 1
        saved = run.workflow.journal.row('runtime_model_calls', episode_id, index)
        assert json.loads(saved['request'])['context'] == snapshot

    summary = {'verification': 'scripted choices and retained synthetic urllib response; no live API or model',
        'mode': run.query['mode'], 'tool_info_fields': sorted(tool_info[0]),
        'tool_names': [row['name'] for row in tool_info], 'native_rows': http.rows,
        'reported_distance': 0.02, 'reported_pvalue': 0.001,
        'shared_hash_fraction': 0.041, 'returned_row_count': 2,
        'population_size': None, 'truncated': None,
        'recomputed_distance': None, 'recomputed_pvalue': None,
        'http_requests': len(http.calls), 'response_sha256': hashlib.sha256(http.body).hexdigest(),
        'own_actions_and_observations': {'annotation': 2, 'scientific_process': 3,
            'launch': 1, 'launch_api': 1, 'results': 1},
        'final_resource_gain': {'launch': 3, 'launch_api': 3, 'results': 2},
        'future_resource_expectation': 0, 'scientific_credit': 0}
    for name, value in {'verification_summary': summary, 'published_grading': grading,
            'results_typed_return': run.received_form,
            'scientific_saved_context': run.scientific_after_result,
            'root_saved_context': run.root_after_result,
            'http_request': http.calls[0]}.items():
        (run.directory / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    (run.directory / 'synthetic_native_response.json').write_bytes(http.body)
    print(json.dumps(summary, sort_keys=True))
    return scientific, launch, api, results, reference, grading


@pytest.mark.parametrize('mode', ['genome', 'fasta'])
def test_selected_minhash_modes_return_matches_to_science_and_only_counts_to_root(tmp_path, monkeypatch, mode):
    http = SyntheticHTTP(monkeypatch, request(mode))
    with Store(tmp_path / 'state') as store:
        run = MinhashRun(store, tmp_path / 'run', mode=mode)
        run.run()
        scientific, _, _, _, reference, _ = assert_joined_path(run, http)
        returned = run.root_after_result['child_reports'][-1]
        assert returned == {'counts': run.received_form['counts']}
        assert run.root_after_result['received_minhash_values'] == [
            {'fact_source': 'bvbrc_minhash_counts', 'facts': run.received_form['counts']}]
        root_context = run.context(run.archive['episode_id'])
        assert run.api.minhash.received_facts(root_context, fact_form('bvbrc_minhash_matches')) == {
            'bvbrc_minhash_matches': []}
        assert not run.api.minhash.resolve_received(root_context, '83333.1', 'bvbrc_minhash_genome')
        assert run.api.minhash.received_context(run.context(scientific['episode_id'])) == (
            run.scientific_after_result['received_minhash_values'])
        with pytest.raises(ValueError):
            run.api.minhash.read_own(reference, context=root_context)
        validate_closed_schema(run.result_form)
        validate_closed_schema(run.parent_form)


def test_minhash_reopen_and_selected_action_replay_do_not_call_http_or_regrade(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request())
    with Store(tmp_path / 'state') as store:
        run = MinhashRun(store, tmp_path / 'run')
        run.run()
        scientific, _, api, results, reference, grading = assert_joined_path(run, http)
        scope, archive, frozen = deepcopy(run.scope), deepcopy(run.archive), run.frozen_hashes()
        history = durable_runtime(run)
        received = deepcopy(run.scientific_after_result['received_minhash_values'])
        action_outcomes = {}
        for closed in (api, results):
            (_, outcome), = run.api._own_outcomes(run.context(closed['episode_id']))
            action_outcomes[closed['episode_id']] = outcome

    def no_grading(*args, **kwargs):
        raise AssertionError('Replay attempted parsing or grading')
    for module in ('api_bvbrc_minhash', 'bvbrc_minhash_grader'):
        for function in ('parse_minhash_result', 'calculate_minhash_components'):
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + function, no_grading)

    with Store(tmp_path / 'state') as reopened:
        replay = MinhashRun(reopened, tmp_path / 'run', scope=scope)
        async def no_decision(*args, **kwargs):
            raise AssertionError('Replay attempted another provider decision')
        replay.complete = no_decision
        assert replay.run() == archive
        assert replay.frozen_hashes() == frozen
        assert replay.api.minhash.read_own(reference, context=replay.context(results['episode_id']))['grading'] == grading
        assert replay.api.minhash.received_context(replay.context(scientific['episode_id'])) == received
        import asyncio
        for closed, name in ((api, 'api.bvbrc.minhash.genome'), (results, 'api.bvbrc.minhash.result')):
            key = f'{replay.run_id}:{closed["episode_id"]}:0'
            assert asyncio.run(replay.api.execute(replay.context(closed['episode_id']), name, {}, key)) == (
                action_outcomes[closed['episode_id']])
        assert len(http.calls) == 1
        assert durable_runtime(replay) == history


def test_source_only_and_unrelated_receivers_cannot_expand_minhash_measurements(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request())
    with Store(tmp_path / 'state') as store:
        run = MinhashRun(store, tmp_path / 'run', parent_form=SOURCE_FORM)
        run.run()
        _, launch, _, _, reference, _ = assert_joined_path(run, http)
        returned = run.root_after_result['child_reports'][-1]
        assert set(returned) == {'references'}
        assert reference in returned['references']
        assert run.root_after_result['received_minhash_values'] == []
        before = durable_runtime(run)
        for context in (run.context(run.archive['episode_id']), run.context(launch['episode_id'])):
            assert run.api.minhash.received_context(context) == []
            assert run.api.minhash.received_facts(context, fact_form(
                'bvbrc_minhash_matches', 'bvbrc_minhash_counts')) == {
                    'bvbrc_minhash_matches': [], 'bvbrc_minhash_counts': []}
            assert not run.api.minhash.resolve_received(context, '83333.1', 'bvbrc_minhash_genome')
            with pytest.raises(ValueError):
                run.api.minhash.read_own(reference, context=context)
        assert durable_runtime(run) == before


def test_minhash_forged_count_match_and_row_association_are_rejected_without_credit(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request())
    with Store(tmp_path / 'state') as store:
        run = MinhashRun(store, tmp_path / 'run')
        run.run()
        scientific, _, _, results, reference, grading = assert_joined_path(run, http)
        before = durable_runtime(run)
        count = deepcopy(run.root_after_result['child_reports'][-1])
        count['counts'][0]['returned_row_count'] = 999
        with pytest.raises(ValueError):
            run.workflow.validate_report(count, run.scope, grain='scientific_process',
                schema=count_form(), context=run.context(scientific['episode_id']))
        matches = deepcopy(run.received_form)
        matches['matches'][0]['shared_hash_fraction'] = 0.41
        with pytest.raises(ValueError):
            run.workflow.validate_report(matches, run.scope, grain='results',
                schema=run.result_form, context=run.context(results['episode_id']))
        forged = deepcopy(grading)
        forged['components']['rows'][0]['row_index'] = 1
        with pytest.raises(ValueError):
            project_minhash_facts([{'source_ref': reference, 'grading': forged}],
                requested_sources=('bvbrc_minhash_matches',))
        assert durable_runtime(run) == before
        assert len(http.calls) == 1


def test_minhash_received_values_require_successful_original_immediate_child_return(tmp_path, monkeypatch):
    http = SyntheticHTTP(monkeypatch, request())
    with Store(tmp_path / 'state') as store:
        run = MinhashRun(store, tmp_path / 'run')
        run.run()
        scientific, _, api, results, _, _ = assert_joined_path(run, http)
        context = run.context(scientific['episode_id'])
        before = durable_runtime(run)
        key = (run.run_id, scientific['episode_id'], 1)
        where = ' WHERE run_id=? AND parent_episode_id=? AND decision_index=?'
        for field, value in (('failure', json.dumps({'code': 'synthetic_failed_delivery'})),
                             ('form', None)):
            with temporary_record_change(store,
                    'UPDATE runtime_report_attempts SET ' + field + '=?' + where, (value, *key)):
                assert run.api.minhash.received_context(context) == []
        with temporary_record_change(store,
                'UPDATE runtime_report_attempts SET child_episode_id=?' + where,
                (api['episode_id'], *key)):
            with pytest.raises(ValueError, match='return_child_contract_conflict'):
                run.api.minhash.received_context(context)
        action = json.loads(run.workflow.journal.row('runtime_actions', scientific['episode_id'], 1)['action'])
        action['role'] = 'launch'
        with temporary_record_change(store,
                'UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (json.dumps(action), *key)):
            with pytest.raises(ValueError, match='commission_role_conflict'):
                run.api.minhash.received_context(context)
        facts = json.loads(run.workflow.journal.row('runtime_forms', results['episode_id'])['facts'])
        facts['bvbrc_minhash_counts'][0]['returned_row_count'] = 999
        with temporary_record_change(store,
                'UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?',
                (json.dumps(facts), run.run_id, results['episode_id'])):
            with pytest.raises(ValueError, match='frozen_return_conflict'):
                run.api.minhash.received_context(context)
        assert durable_runtime(run) == before
        assert run.api.minhash.received_context(context) == run.scientific_after_result['received_minhash_values']
        assert len(http.calls) == 1


def test_partial_minhash_retains_native_cells_and_unknowns_without_claiming_completion(tmp_path, monkeypatch):
    rows = [NATIVE_ROWS[0], ['83333.1', None, '0.002', '0/0'],
            [None, '0.05', '0.1', '1/10']]
    http = SyntheticHTTP(monkeypatch, request(), rows)
    with Store(tmp_path / 'state') as store:
        run = MinhashRun(store, tmp_path / 'run', partial=True)
        with pytest.raises(PartialResultDecisionReached):
            run.run()
        context = run.context(run.partial_episode_id)
        actions = run.rows('runtime_actions', run.partial_episode_id)
        assert len(actions) == len(run.rows('runtime_observations', run.partial_episode_id)) == 1
        outcome = json.loads(actions[0]['result'])
        assert outcome['status'] == 'partial'
        assert outcome['result']['parse_status'] == 'partial'
        assert outcome['result']['projection_errors']
        reference = outcome['result']['source_ref']
        qualified = run.api.minhash.read_own(reference, context=context)
        assert qualified['grading']['sheet']['native_result'] == rows
        assert run.store.get_artifact(run.store.get(reference)['artifact_ref']) == http.body
        facts = run.api.minhash.facts(context, run.result_form)
        matches = facts['bvbrc_minhash_matches']
        assert [row['row_index'] for row in matches] == [0, 1, 2]
        assert matches[0]['shared_hash_fraction'] == 0.041
        assert matches[1]['reported_distance'] is None
        assert matches[1]['reported_pvalue'] == 0.002
        assert matches[1]['shared_hashes'] == matches[1]['compared_union_hashes'] == 0
        assert matches[1]['shared_hash_fraction'] is None
        assert matches[2]['genome_id'] is None
        assert matches[2]['shared_hash_fraction'] is None
        assert facts['bvbrc_minhash_counts'] == [{'source_ref': reference,
            'returned_row_count': 3, 'parse_status': 'partial',
            'population_size': None, 'truncated': None}]
        assert run.api.completion_for_action(context, f'{run.run_id}:{context.episode_id}:0') is None
        assert run.partial_context['execution_progress']['execution_completed'] is False
        assert run.api.minhash.received_context(run.context(run.episode.source.episode_id)) == []
        assert run.store.count('annotation') == run.store.count('observation') == 0
        assert len(http.calls) == 1

