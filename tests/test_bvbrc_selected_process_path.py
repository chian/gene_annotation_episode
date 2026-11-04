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


def test_selected_process_combined_page_fields_sort_and_onward(tmp_path, monkeypatch):
    """New engineered page through actual selected owners; no live API/model.

    The two literal feature IDs define a two-record fixture population. Only its
    second page is supplied; its zero length is an engineered reported value,
    not a new measurement of either biological feature or a missing-value fill.
    """
    from email.message import Message
    from urllib.parse import parse_qsl, quote, urlencode, urlsplit

    from gene_annotation_episode.bvbrc_data_views import bvbrc_data_fact_sources
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.providers import _SessionConnection, load_config
    from bvbrc_episode_fixture import FEATURE_IDS, RESOURCES, request, rows_selector

    question = ('For the two supplied feature IDs in genome 511145.12 with an annotation '
                'and a reported amino-acid length from 0 through 1000, what annotation '
                'label and reported length are returned at offset 1, limit 1, sorted '
                'by annotation and feature ID?')
    query = request(mode='page', fields=['annotation', 'aa_length'], offset=1, limit=1,
        filters=[{'field': 'feature_id', 'operator': 'in', 'value': list(FEATURE_IDS)},
            {'field': 'genome_id', 'operator': 'eq', 'value': '511145.12'},
            {'field': 'aa_length', 'operator': 'range', 'lower': 0, 'upper': 1000,
             'lower_inclusive': True, 'upper_inclusive': True},
            {'field': 'annotation', 'operator': 'exists', 'present': True}],
        sort=[{'field': 'annotation', 'direction': 'asc'}])
    selection = rows_selector(rows=(0,), numbers=('aa_length',),
        metadata=('annotation', 'feature_id'))
    expected_q = ('(feature_id:("' + FEATURE_IDS[0] + '" OR "' + FEATURE_IDS[1] + '")) '
        'AND (genome_id:"511145.12") AND (aa_length:[0 TO 1000]) AND (annotation:[* TO *])')
    parameters = [('q', expected_q), ('rows', '1'), ('start', '1'),
        ('fl', 'annotation,aa_length,feature_id'), ('sort', 'annotation asc,feature_id asc')]
    address = RESOURCES['bvbrc']['base_url'] + '/genome_feature/?' + urlencode(
        parameters, quote_via=quote, safe='')
    document = {'feature_id': FEATURE_IDS[1], 'annotation': 'RefSeq', 'aa_length': 0}
    payload = {'responseHeader': {'status': 0, 'params': dict(parameters)},
        'response': {'docs': [document], 'numFound': 2, 'numFoundExact': True, 'start': 1}}
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
    calls = []

    class Response:
        status = 200

        def __init__(self):
            self.headers = Message()
            self.headers['Content-Type'] = 'application/solr+json'
            self.headers['Content-Length'] = str(len(body))

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def geturl(self):
            return address

        def read(self):
            return body

    def open_response(opener, native_request, *, timeout):
        assert not calls, 'Combined-page fixture attempted another HTTP operation'
        assert native_request.get_method() == 'GET' and native_request.data is None
        assert native_request.full_url == address
        assert parse_qsl(urlsplit(native_request.full_url).query) == parameters
        assert timeout == RESOURCES['bvbrc']['timeout']
        headers = {key.lower(): value for key, value in native_request.header_items()}
        assert headers == {'user-agent': 'gene-annotation-episode/0.2',
            'accept': 'application/solr+json',
            'content-type': 'application/solrquery+x-www-form-urlencoded'}
        calls.append(dict(url=native_request.full_url, method='GET', headers=headers,
            timeout=timeout, body=None))
        return Response()

    def forbidden(*args, **kwargs):
        raise AssertionError('Combined-page verification attempted live I/O or a replay decision')

    monkeypatch.setattr('urllib.request.OpenerDirector.open', open_response)
    monkeypatch.setattr('socket.create_connection', forbidden)
    presenter = _SessionConnection(load_config(), tmp_path / 'presentation', tmp_path)

    class PresentedRun(SelectedProcessRun):
        async def complete(self, episode_id, role, instructions, current, schema):
            key = episode_id, role
            frame = state_frame(current, previous.get(key))
            original = canonical(current), canonical(frame), canonical(schema)
            text, shown_instructions = presenter._presentation(episode_id, role, instructions, frame)
            assert isinstance(text, str) and text and isinstance(shown_instructions, str)
            assert original == (canonical(current), canonical(frame), canonical(schema))
            previous[key] = deepcopy(current)
            presentations.append(dict(episode_id=episode_id, role=role, context=deepcopy(current)))
            return await super().complete(episode_id, role, instructions, current, schema)

    previous, presentations = {}, []
    sources = ('execution_bvbrc_pages', 'execution_bvbrc_numeric_rows')
    parent_form = {'type': 'object', 'additionalProperties': False, 'required': ['numeric_rows'],
        'properties': {'numeric_rows': deepcopy(
            bvbrc_data_fact_sources()['execution_bvbrc_numeric_rows']['report_schema'])}}
    options = dict(selected_query=query, selected_selector=selection, question=question,
        result_sources=sources, parent_form=parent_form)

    def table_rows(store):
        names = [row[0] for row in store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: sorted((tuple((type(value).__name__, value) for value in row)
            for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')),
            key=repr) for name in names}

    def files(directory):
        return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob('*') if path.is_file()}

    with Store(tmp_path / 'state') as store:
        run = PresentedRun(store, tmp_path / 'run', **options)
        run.run()
        assert len(FEATURE_IDS) == len(set(FEATURE_IDS)) == 2 and len(calls) == 1
        root = run.archive
        scientific = root['units'][0]['child']
        launch = scientific['units'][0]['child']
        api = launch['units'][0]['child']
        results = scientific['units'][1]['child']
        contexts = {closed['episode_id']: run.context(closed['episode_id'])
            for closed in (root, scientific, launch, api, results)}
        sci_context = contexts[scientific['episode_id']]
        root_context = contexts[root['episode_id']]
        assert plain(contexts[api['episode_id']].assignment) == run.api_assignment
        assert run.launch_assignment['requests']['bvbrc'] == run.api_assignment
        assert run.api_assignment['request'] == query and run.selection == selection
        assert plain(contexts[results['episode_id']].assignment)['selector'] == selection
        selected_tools = plain(sci_context.assignment)['selection']['child_tool_info']
        assert [{'name': row['name'], 'resources': row['resources']} for row in selected_tools] == SELECTED_TOOLS
        assert all(set(row) == {'name', 'description', 'resources', 'instructions'} for row in selected_tools)
        assert selected_tools == run.scientific_after_result['scientific_process']['child_tool_info']
        assert plain(sci_context.assignment)['selection']['evidence_axis'] == run.library.reference('A101')
        assert plain(sci_context.assignment)['selection']['thought_pattern'] == run.library.reference('P01')
        for option in ('A101', 'P01'):
            assert (run.directory / 'scientific-process-library/entries' / (option + '.json')).read_bytes() == (
                PUBLICATION / 'entries' / (option + '.json')).read_bytes()
        assert run.scientific_after_result['goal']['objective'] == question
        assert run.scientific_after_result['scientific_process']['assignment']['context'][
            'selected_native_count_query'] == query
        assert len([item for item in presentations if 'scientific_process' in item['context']]) == 3
        assert presenter.process is None
        for closed in (scientific, api):
            item = next(item for item in reversed(presentations) if item['episode_id'] == closed['episode_id'])
            assert canonical(presenter.scientific_prompt_states[(item['episode_id'], item['role'])]) == canonical(item['context'])

        reference, = run.received_form['references']
        owned = run.api.read_bvbrc_result(reference, context=contexts[results['episode_id']])
        assert owned['host_qualification']['possession_basis'] == 'own_completed_action'
        for context in (sci_context, root_context):
            assert run.api.read_bvbrc_result(reference, context=context)[
                'host_qualification']['possession_basis'] == 'admitted_return'
        binding, grading = owned['binding'], owned['grading']
        source = store.get(reference)
        assert source['artifact_ref'] == binding['native_artifact_ref']
        assert source['auxiliary_artifact_refs'] == [binding['grading_artifact_ref']]
        assert store.get_artifact(binding['native_artifact_ref']) == body
        assert binding['native_sha256'] == hashlib.sha256(body).hexdigest()
        assert binding['selector_sha256'] == digest(selection)
        assert binding['acquisition_assignment_sha256'] == digest(contexts[results['episode_id']].assignment)
        assert json.loads(store.get_artifact(binding['grading_artifact_ref']))['grading'] == grading
        prepared = grading['prepared']
        assert prepared['original_request'] == query and prepared['page_selector'] is None
        assert prepared['effective_request'] == dict(version='bvbrc_data_effective_query_v2',
            collection='genome_feature', mode='page', filters=query['filters'],
            fields=['annotation', 'aa_length', 'feature_id'],
            sort=[*query['sort'], {'field': 'feature_id', 'direction': 'asc'}],
            offset=1, limit=1, facet=None)
        assert prepared['field_selection'] == dict(requested_fields=['annotation', 'aa_length'],
            defaulted_fields=[], custody_added_fields=['feature_id'])
        assert prepared['sort_selection'] == dict(requested_sort=query['sort'], defaulted_sort=[],
            tie_breaker_added={'field': 'feature_id', 'direction': 'asc'})
        assert prepared['native_request']['url'] == calls[0]['url'] == address
        assert [(item['name'], item['value']) for item in prepared['native_request']['query_parameters']] == parameters
        population = prepared['query_population']
        assert population['collection'] == query['collection'] and population['filters'] == query['filters']
        assert not {'mode', 'fields', 'sort', 'offset', 'limit'}.intersection(population)
        assert population['population_key'] == json_digest({key: value for key, value in population.items()
            if key != 'population_key'})
        assert grading['selector'] == selection
        sheet = grading['parse_result']['sheet']
        assert sheet['custody']['prepared_sha256'] == json_digest(prepared)
        assert sheet['selected_fields'] == prepared['effective_request']['fields']
        assert sheet['population']['population_key'] == population['population_key']
        assert sheet['count']['reported_value'] == 2 and sheet['count']['exactness'] == 'exact'
        assert len(sheet['rows']) == 1 and sheet['rows'][0]['native_id'] == FEATURE_IDS[1]
        number, = sheet['rows'][0]['numerical_cells']
        assert number['value'] == 0 and type(number['value']) is int
        assert number['status'] == 'reported' and number['reason'] is None

        groups = {group['fact_source']: group for group in run.scientific_after_result['received_bvbrc_values']}
        assert set(groups) == set(sources)
        page, = groups['execution_bvbrc_pages']['facts']
        numeric = groups['execution_bvbrc_numeric_rows']
        row, = numeric['facts']
        assert page['source_ref'] == row['source_ref'] == reference
        assert (page['requested_offset'], page['requested_limit'], page['returned_row_count'],
            page['reported_total']) == (1, 1, 1, 2)
        assert page['population_coverage'] == 'subset' and page['next_offset'] is None
        assert page['response_complete'] is True and page['count_exactness'] == 'exact'
        assert row['requested_row_index'] == 0 and row['native_id'] == FEATURE_IDS[1]
        measurement, = row['measurements']
        assert measurement['field'] == 'aa_length' and measurement['value'] == 0
        assert measurement['unit_code'] == 'amino_acid' and measurement['unit_basis'] == 'field_definition'
        assert row['unavailable'] == row['metadata_unavailable'] == []
        cells = {cell['cell_ref']: cell for cell in numeric['cells']}
        cell = cells[measurement['cell_ref']]
        assert cell['presence'] == 'present' and cell['status'] == 'valid'
        assert cell['atoms'][0]['number_value'] == 0 and cell['atoms'][0]['number_lexeme'] == '0'
        assert {item['field']: cells[item['value_ref']]['atoms'][0]['string_value']
            for item in row['metadata_cells']} == {'annotation': 'RefSeq', 'feature_id': FEATURE_IDS[1]}
        assert run.received_form['completed'] is True
        assert canonical(run.received_form['pages']) == canonical([page])
        assert canonical(run.received_form['numeric_rows']) == canonical([row])
        onward = run.root_after_result['child_reports'][-1]
        assert set(onward) == {'numeric_rows'} and canonical(onward['numeric_rows']) == canonical([row])
        received, = run.root_after_result['received_bvbrc_values']
        assert received['fact_source'] == 'execution_bvbrc_numeric_rows'
        assert canonical(received['facts']) == canonical([row]) and canonical(received['cells']) == canonical(numeric['cells'])
        assert row['input_source_refs'] == row['metadata_source_refs'] == []
        scientific_resolver = run.workflow.resolver(run.scope, context=sci_context)
        root_resolver = run.workflow.resolver(run.scope, context=root_context)
        assert scientific_resolver(page['population_ref'], 'bvbrc_data_population') is True
        assert root_resolver(page['population_ref'], 'bvbrc_data_population') is False
        for namespace, ref in (('bvbrc_data_row', row['row_ref']),
                ('bvbrc_data_cell', measurement['cell_ref'])):
            assert root_resolver(ref, namespace) is True
            assert root_resolver(ref + '/forged', namespace) is False
        assert {item['receiver_episode_id'] for item in run.rows('runtime_bvbrc_admissions')} == {
            scientific['episode_id'], root['episode_id']}
        before = table_rows(store)
        forged = deepcopy(onward)
        forged['numeric_rows'][0]['measurements'][0]['value'] = 999
        with pytest.raises(ReportBoundaryError) as rejected:
            run.workflow.validate_report(forged, run.scope, grain='scientific_process',
                schema=parent_form, context=sci_context)
        assert rejected.value.diagnostic['code'] == 'bvbrc_recorded_facts_mismatch'
        assert table_rows(store) == before
        counts = {'annotation': 2, 'scientific_process': 3, 'launch': 1, 'launch_api': 1, 'results': 1}
        for closed in (root, scientific, launch, api, results):
            count = counts[contexts[closed['episode_id']].role]
            for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls'):
                assert len(run.rows(table, closed['episode_id'])) == count
        assert run.store.count('annotation') == run.store.count('observation') == 0

        archived, before = deepcopy(run.archive), table_rows(store)
        run_files, artifacts = files(run.directory), files(store.path / 'artifacts')
        changes = store.db.total_changes
        replay = SelectedProcessRun(store, run.directory, scope=run.scope, **options)
        monkeypatch.setattr(replay, 'complete', forbidden)
        assert replay.run() == archived
        # Existing same-value episode reclosure UPSERTs may increment SQLite's
        # total_changes; all actual row values, archives and artifacts stay fixed.
        assert table_rows(store) == before
        assert files(run.directory) == run_files and files(store.path / 'artifacts') == artifacts
        assert len(calls) == 1 and presenter.process is None
        (tmp_path / 'BV_BRC_COMBINED_PAGE.json').write_text(json.dumps(dict(
            qualification='engineering choices and new controlled Solr page; no live API or model',
            question=question, selected_query=query, selected_selector=selection,
            http_requests=calls, native_body_sha256=hashlib.sha256(body).hexdigest(),
            prepared=prepared, typed_result=run.received_form, scientific_received_values=list(groups.values()),
            onward_typed_return=onward, actual_actions_and_observations=counts,
            closed_replay_rows_and_files_unchanged=True,
            replay_total_changes_delta=store.db.total_changes - changes), indent=2) + '\n')


def test_selected_process_received_feature_sequence_join_and_onward(tmp_path, monkeypatch):
    """Real selected owners join retained native rows in controlled Solr replies.

    Historical array bytes remain canonical test inputs. Only their literal rows
    are reserialized here; these replies are not new live-v2 measurements. The
    sequence Source must reach the scientific parent through a prior real child
    return before it can be selected by the feature Results child.
    """
    from collections import Counter
    from email.message import Message
    from pathlib import Path
    from urllib.parse import quote, urlencode

    import gene_annotation_episode.bvbrc_data_publication as publication
    from gene_annotation_episode.bvbrc_data_views import bvbrc_data_fact_sources
    from gene_annotation_episode.domain import canonical
    from bvbrc_episode_fixture import FEATURE_IDS, RESOURCES, child, handoff_form, request, result_form, selector

    fixture = Path(__file__).with_name('fixtures') / 'bvbrc_feature_sequence_join'
    pins = {'feature_page.body': '6066eb055239b72179d1c9b34671fe4799db2d7e39e459ca327ad3e43f1e45a6',
        'feature_page.meta.json': '465d8e9f84849e335b33b6e6ec24223ca0e420bde816dac38ee37886d2991410',
        'feature_sequences.body': 'bfd55b6778a56808abe5f2f37c3254161fbb9c71cc96028b45329d2afbca741c',
        'feature_sequences.meta.json': 'caa735770f0dbc2ad6bd222baedc3142b45279c88d94672b0ef544ed80f8abca'}
    originals = {name: (fixture / name).read_bytes() for name in pins}
    assert {name: hashlib.sha256(raw).hexdigest() for name, raw in originals.items()} == pins
    for name in ('feature_page', 'feature_sequences'):
        metadata = json.loads(originals[name + '.meta.json'])
        assert metadata['sha256'] == pins[name + '.body']
        assert metadata['byte_count'] == len(originals[name + '.body'])
    features = json.loads(originals['feature_page.body'])
    sequences = json.loads(originals['feature_sequences.body'])
    aa_md5, na_md5 = '7594e119ffe8456710f27d137885e84c', '584ae482fd635ee1fb6243df48fb8508'
    assert [row['feature_id'] for row in features] == FEATURE_IDS
    assert [(row['md5'], row['sequence_type']) for row in sequences] == [(na_md5, 'NA'), (aa_md5, 'AA')]
    assert sequences[0]['sequence'].islower()
    feature_fields = ['feature_id', 'genome_id', 'sequence_id', 'patric_id', 'gene',
        'aa_sequence_md5', 'na_sequence_md5', 'aa_length', 'na_length', 'start', 'end', 'strand', 'annotation']
    sequence_query = request('feature_sequence', mode='page', fields=['md5', 'sequence_type', 'sequence'],
        filters=[{'field': 'md5', 'operator': 'in', 'value': [aa_md5, na_md5]}],
        sort=[{'field': 'md5', 'direction': 'asc'}], offset=0, limit=2)
    feature_query = request(mode='page', fields=feature_fields,
        sort=[{'field': 'feature_id', 'direction': 'asc'}], offset=0, limit=2)
    wire = [
        ('feature_sequence', sequence_query, sequences,
         'md5:("' + aa_md5 + '" OR "' + na_md5 + '")', 'md5 asc'),
        ('genome_feature', feature_query, features,
         'feature_id:("' + FEATURE_IDS[0] + '" OR "' + FEATURE_IDS[1] + '")', 'feature_id asc')]
    responses = []
    for collection, query, rows, q, sort in wire:
        parameters = [('q', q), ('rows', '2'), ('start', '0'),
            ('fl', ','.join(query['fields'])), ('sort', sort)]
        url = RESOURCES['bvbrc']['base_url'] + '/' + collection + '/?' + urlencode(
            parameters, quote_via=quote, safe='')
        body = json.dumps({'responseHeader': {'status': 0, 'params': dict(parameters)},
            'response': {'docs': rows, 'start': 0, 'numFound': 2, 'numFoundExact': True}},
            ensure_ascii=False, allow_nan=False).encode()
        responses.append(dict(url=url, body=body, parameters=parameters))
    http_calls = []

    class Response:
        status = 200

        def __init__(self, selected):
            self.selected, self.headers = selected, Message()
            self.headers['Content-Type'] = 'application/solr+json'
            self.headers['Content-Length'] = str(len(selected['body']))

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def geturl(self):
            return self.selected['url']

        def read(self):
            return self.selected['body']

    def open_response(opener, native_request, *, timeout):
        assert len(http_calls) < 2, 'Join fixture attempted another GET or automatic page'
        selected_response = responses[len(http_calls)]
        assert native_request.full_url == selected_response['url']
        assert native_request.get_method() == 'GET' and native_request.data is None
        assert timeout == RESOURCES['bvbrc']['timeout']
        headers = {key.lower(): value for key, value in native_request.header_items()}
        assert headers['accept'] == 'application/solr+json'
        assert headers['content-type'] == 'application/solrquery+x-www-form-urlencoded'
        http_calls.append(dict(url=native_request.full_url, method='GET', timeout=timeout, headers=headers))
        return Response(selected_response)

    def forbidden(*args, **kwargs):
        raise AssertionError('Retained join verification attempted live I/O or new replay work')

    monkeypatch.setattr('urllib.request.OpenerDirector.open', open_response)
    monkeypatch.setattr('socket.create_connection', forbidden)
    calculation_calls = Counter()
    for name in ('extract_feature_sequence_join', 'calculate_feature_sequence_counts'):
        original = getattr(publication, name)

        def tracked(*args, _name=name, _original=original, **kwargs):
            calculation_calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(publication, name, tracked)
    fact_source = 'execution_bvbrc_feature_sequence_rows'
    parent_form = {'type': 'object', 'additionalProperties': False, 'required': ['feature_sequence_rows'],
        'properties': {'feature_sequence_rows': deepcopy(bvbrc_data_fact_sources()[fact_source]['report_schema'])}}
    question = ('For the two supplied feature IDs, which retained AA and NA sequence occurrences '
                'match their literal sequence-MD5 keys, and do their reported feature lengths '
                'agree with the exact sequence-character lengths?')
    handoff_schema = handoff_form()

    class JoinedRun(SelectedProcessRun):
        def commission(self):
            action = super().commission()
            context = action['selection']['assignment']['context']
            context.pop('selected_native_count_query')
            context['selected_native_input_queries'] = deepcopy([sequence_query, feature_query])
            return action

        async def complete(self, episode_id, role, instructions, current, schema):
            if 'scientific_process' not in current:
                return await super().complete(episode_id, role, instructions, current, schema)
            self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
            count = self.calls[episode_id]
            self.contexts.append((episode_id, deepcopy(current)))
            assert current.get('feedback') is None, current.get('feedback')
            if count == 1:
                assert current['received_bvbrc_values'] == []
                return child('launch', self.launch_assignment, self.scope, handoff_schema)
            if count == 2:
                self.sequence_handoff, = current['child_reports'][-1]['references']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.sequence_handoff, 'selector': self.selection},
                    self.scope, self.result_form)
            if count == 3:
                self.sequence_form = deepcopy(current['child_reports'][-1])
                self.sequence_source, = self.sequence_form['references']
                self.sequence_received_context = deepcopy(current)
                admitted = self.api.read_bvbrc_result(self.sequence_source, context=self.context(episode_id))
                assert admitted['host_qualification']['possession_basis'] == 'admitted_return'
                self.api_assignment = {**deepcopy(self.api_assignment), 'request': deepcopy(feature_query)}
                self.launch_assignment = {**deepcopy(self.launch_assignment),
                    'requests': {'bvbrc': deepcopy(self.api_assignment)}}
                return child('launch', self.launch_assignment, self.scope, handoff_schema)
            if count == 4:
                self.handoff, = current['child_reports'][-1]['references']
                self.selection = selector({'family': 'feature_sequence',
                    'feature_ids': list(reversed(FEATURE_IDS)), 'sequence_kind': 'both',
                    'feature_metadata_fields': ['annotation', 'gene', 'start', 'end', 'strand'],
                    'include_sequence_values': True}, inputs=[
                        {'collection': 'feature_sequence', 'source_ref': self.sequence_source}])
                self.result_form = result_form(fact_source)
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': self.selection}, self.scope, self.result_form)
            assert count == 5
            self.scientific_after_result = deepcopy(current)
            self.received_form = deepcopy(current['child_reports'][-1])
            return self.wait()

    options = dict(selected_query=sequence_query, result_sources=('execution_bvbrc_pages',),
        parent_form=parent_form, question=question, scientific_action_count=5)

    def table_rows(store):
        names = [row[0] for row in store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: sorted((tuple((type(value).__name__, value) for value in row)
            for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')),
            key=repr) for name in names}

    def files(directory):
        return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob('*') if path.is_file()}

    with Store(tmp_path / 'state') as store:
        run = JoinedRun(store, tmp_path / 'run', **options)
        run.run()
        root, scientific = run.archive, run.archive['units'][0]['child']
        root_context, sci_context = run.context(root['episode_id']), run.context(scientific['episode_id'])
        closed = [root, scientific]
        for unit in scientific['units']:
            child_archive = unit.get('child')
            if child_archive is not None:
                closed.append(child_archive)
                if run.context(child_archive['episode_id']).role == 'launch':
                    closed.append(child_archive['units'][0]['child'])
        contexts = {item['episode_id']: run.context(item['episode_id']) for item in closed}
        assert len(contexts) == len(run.rows('runtime_episodes')) == 8
        episode_counts = Counter(context.role for context in contexts.values())
        actual_counts = {table: dict(Counter({role: sum(len(run.rows(table, episode_id))
            for episode_id, context in contexts.items() if context.role == role)
            for role in episode_counts})) for table in
            ('runtime_actions', 'runtime_observations', 'runtime_model_calls')}
        assert dict(episode_counts) == {'annotation': 1, 'scientific_process': 1,
            'launch': 2, 'launch_api': 2, 'results': 2}
        assert all(counts == {'annotation': 2, 'scientific_process': 5, 'launch': 2,
            'launch_api': 2, 'results': 2} for counts in actual_counts.values())
        assert all(len(run.rows(table)) == 13 for table in actual_counts)
        selected_tools = plain(sci_context.assignment)['selection']['child_tool_info']
        assert [{'name': row['name'], 'resources': row['resources']} for row in selected_tools] == SELECTED_TOOLS
        assert all(set(row) == {'name', 'description', 'resources', 'instructions'} for row in selected_tools)
        assert selected_tools == run.scientific_after_result['scientific_process']['child_tool_info']
        assert plain(sci_context.assignment)['selection']['evidence_axis'] == run.library.reference('A101')
        assert plain(sci_context.assignment)['selection']['thought_pattern'] == run.library.reference('P01')
        results_contexts = [context for context in contexts.values() if context.role == 'results']
        sequence_context, = [context for context in results_contexts if plain(context.assignment)[
            'handoff_ref'] == run.sequence_handoff]
        join_context, = [context for context in results_contexts if plain(context.assignment)[
            'handoff_ref'] == run.handoff]
        sequence = run.api.read_bvbrc_result(run.sequence_source, context=sequence_context)
        joined_source, = run.received_form['references']
        joined = run.api.read_bvbrc_result(joined_source, context=join_context)
        assert joined_source != run.sequence_source
        assert joined['host_qualification']['possession_basis'] == 'own_completed_action'
        assert run.api.read_bvbrc_result(run.sequence_source, context=join_context)[
            'host_qualification']['possession_basis'] == 'parent_assignment'
        assert joined['input_results'] == [{'binding': sequence['binding'],
            'sheet': sequence['grading']['parse_result']['sheet']}]
        assert joined['grading']['input_bindings'] == [sequence['binding']]
        assert joined['grading']['selector'] == run.selection
        assert joined['grading']['selector']['inputs'] == [
            {'collection': 'feature_sequence', 'source_ref': run.sequence_source}]
        prior, = run.sequence_received_context['received_bvbrc_values']
        assert prior['fact_source'] == 'execution_bvbrc_pages'
        assert prior['facts'][0]['source_ref'] == run.sequence_source
        admissions = run.rows('runtime_bvbrc_admissions')
        scientific_admissions = [row for row in admissions if row['receiver_episode_id'] == sci_context.episode_id]
        assert {row['operation_key'] for row in scientific_admissions} == {
            f'{run.run_id}:{sci_context.episode_id}:1:typed_form',
            f'{run.run_id}:{sci_context.episode_id}:3:typed_form'}
        assert len(admissions) == 3
        original_sequence_return, = [row for row in scientific_admissions
            if json.loads(row['form']) == run.sequence_form]
        assert json.loads(original_sequence_return['bindings']) == [sequence['binding']]
        assert json.loads(original_sequence_return['original_schema']) == plain(sequence_context.request)[
            'report_contract']['measurements']['schema']
        for qualified, expected, rows, query in ((sequence, responses[0], sequences, sequence_query),
                (joined, responses[1], features, feature_query)):
            source = store.get(qualified['binding']['source_ref'])
            raw = store.get_artifact(source['artifact_ref'])
            assert raw == expected['body'] and json.loads(raw)['response']['docs'] == rows
            assert qualified['binding']['native_sha256'] == hashlib.sha256(raw).hexdigest()
            assert qualified['grading']['prepared']['original_request'] == query
            assert qualified['grading']['prepared']['native_request']['url'] == expected['url']
            assert source['auxiliary_artifact_refs'] == [qualified['binding']['grading_artifact_ref']]
            assert json.loads(store.get_artifact(source['auxiliary_artifact_refs'][0]))['grading'] == qualified['grading']
        assert len(http_calls) == 2
        sheet, grading = joined['grading']['feature_sequence_sheet'], joined['grading']
        expected_pairs = [(FEATURE_IDS[1], 'AA', 1, 1, 253, aa_md5),
            (FEATURE_IDS[1], 'NA', 1, 0, 762, na_md5),
            (FEATURE_IDS[0], 'AA', 0, 1, 253, aa_md5), (FEATURE_IDS[0], 'NA', 0, 0, 762, na_md5)]
        assert sheet['selection'] == {'feature_ids': list(reversed(FEATURE_IDS)), 'sequence_kind': 'both'}
        assert len(sheet['edges']) == 4 and sheet['requirements'] == sheet['issues'] == []
        assert grading['feature_sequence_components'] == dict(version='bvbrc_feature_sequence_components_v1',
            selected_feature_count=2, retained_feature_row_count=2, native_sequence_record_count=2,
            distinct_joined_aa_sequence_count=1, distinct_joined_na_sequence_count=1, relation_count=4,
            missing_key_count=0, missing_record_count=0, conflicting_relation_count=0, length_agreement_count=4)
        assert calculation_calls == {'extract_feature_sequence_join': 1, 'calculate_feature_sequence_counts': 1}
        group, = [value for value in run.scientific_after_result['received_bvbrc_values']
            if value['fact_source'] == fact_source]
        facts, cells = group['facts'], {cell['cell_ref']: cell for cell in group['cells']}
        assert len(facts) == 4
        feature_native = grading['parse_result']['sheet']
        sequence_native = sequence['grading']['parse_result']['sheet']
        for edge, row, (identifier, kind, feature_index, sequence_index, length, md5) in zip(
                sheet['edges'], facts, expected_pairs):
            feature_row, sequence_row = feature_native['rows'][feature_index], sequence_native['rows'][sequence_index]
            assert feature_row['native_id'] == identifier and sequence_row['native_id'] == md5
            assert (edge['feature_id'], edge['sequence_kind'], edge['sequence_length'], edge['feature_length'],
                edge['native_md5']) == (identifier, kind, length, length, md5)
            assert edge['raw_md5_match'] is edge['length_match'] is True and edge['join_status'] == 'joined'
            assert row['source_ref'] == joined_source and row['input_source_refs'] == [run.sequence_source]
            assert row['metadata_source_refs'] == [] and row['collection'] == 'genome_feature'
            assert (row['feature_id'], row['sequence_kind'], row['native_md5'], row['sequence_length'],
                row['feature_length'], row['join_status']) == (identifier, kind, md5, length, length, 'joined')
            assert row['raw_md5_match'] is row['length_match'] is True
            assert row['status'] == 'complete' and row['unavailable_reason'] is None
            assert row['metadata_unavailable'] == []
            assert row['feature_row_refs'] == [joined_source + '#' + feature_row['row_key']]
            assert row['sequence_row_refs'] == [run.sequence_source + '#' + sequence_row['row_key']]
            sequence_cell, = [cell for cell in sequence_row['cells'] if cell['field'] == 'sequence']
            assert row['sequence_value_refs'] == [run.sequence_source + '#' + sequence_cell['cell_key']]
            actual_sequence = cells[row['sequence_value_refs'][0]]
            assert actual_sequence['source_level'] == 'sequence' and actual_sequence['source_ref'] == run.sequence_source
            assert actual_sequence['atoms'][0]['string_value'] == sequences[sequence_index]['sequence']
            if kind == 'NA':
                assert actual_sequence['atoms'][0]['string_value'].islower()
            native_type, = [cell for cell in sequence_row['cells'] if cell['field'] == 'sequence_type']
            assert native_type['atoms'][0]['string_value'] == kind
            native_length, = [cell for cell in feature_row['numerical_cells'] if cell['field'] == kind.lower() + '_length']
            assert native_length['value'] == length and native_length['origin'] == 'native_reported'
            assert native_length['unit_code'] == {'AA': 'amino_acid', 'NA': 'nucleotide'}[kind]
            assert native_length['unit_basis'] == 'field_definition'
            metadata = {item['field']: cells[item['value_ref']] for item in row['metadata_cells']}
            assert metadata['gene']['atoms'][0]['string_value'] == 'ybhP'
            assert metadata['annotation']['atoms'][0]['string_value'] == features[feature_index]['annotation']
            assert metadata['start']['atoms'][0]['number_value'] == 822959
            assert metadata['end']['atoms'][0]['number_value'] == 823720
            assert metadata['strand']['atoms'][0]['string_value'] == '-'
        assert canonical(run.received_form['feature_sequence_rows']) == canonical(facts)
        onward = run.root_after_result['child_reports'][-1]
        assert set(onward) == {'feature_sequence_rows'} and canonical(onward['feature_sequence_rows']) == canonical(facts)
        received, = run.root_after_result['received_bvbrc_values']
        assert received['fact_source'] == fact_source and canonical(received['facts']) == canonical(facts)
        assert canonical(received['cells']) == canonical(group['cells'])
        resolve = run.workflow.resolver(run.scope, context=root_context)
        for row in facts:
            assert resolve(row['feature_id'], 'bvbrc_data_identifier') is True
            assert resolve(row['native_md5'], 'bvbrc_data_identifier') is True
            for namespace, refs in (('execution_result', [row['source_ref'], *row['input_source_refs']]),
                    ('bvbrc_data_row', [*row['feature_row_refs'], *row['sequence_row_refs']]),
                    ('bvbrc_data_cell', row['sequence_value_refs'])):
                for reference in refs:
                    assert resolve(reference, namespace) is True
                    assert resolve(reference + '/forged', namespace) is False
        page, = run.sequence_form['pages']
        assert resolve(page['population_ref'], 'bvbrc_data_population') is False
        before = table_rows(store)
        for field in ('sequence_length', 'feature_row_refs'):
            forged = deepcopy(onward)
            forged['feature_sequence_rows'][0][field] = (254 if field == 'sequence_length'
                else deepcopy(facts[2]['feature_row_refs']))
            with pytest.raises(ReportBoundaryError) as rejected:
                run.workflow.validate_report(forged, run.scope, grain='scientific_process',
                    schema=parent_form, context=sci_context)
            assert rejected.value.diagnostic['code'] == 'bvbrc_recorded_facts_mismatch'
            assert table_rows(store) == before
        assert store.count('annotation') == store.count('observation') == 0
        for name in ('extract_feature_sequence_join', 'calculate_feature_sequence_counts',
                'calculate_page_counts', 'calculate_facet_fractions', 'parse_data_snapshot', 'publish_bvbrc_data'):
            monkeypatch.setattr(publication, name, forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_data_feature_sequences.extract_feature_sequence_join', forbidden)
        for name in ('calculate_feature_sequence_counts', 'calculate_page_counts', 'calculate_facet_fractions'):
            monkeypatch.setattr('gene_annotation_episode.bvbrc_data_calculators.' + name, forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_data_readers.parse_data_snapshot', forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_data_query.encode_native_query', forbidden)
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc.encode_native_query', forbidden)
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc.BVBRCDataClient.query_prepared', forbidden)
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc.BVBRCDataClient._query_once', forbidden)
        before, archived = table_rows(store), deepcopy(run.archive)
        run_files, artifacts, changes = files(run.directory), files(store.path / 'artifacts'), store.db.total_changes
        replay = JoinedRun(store, run.directory, scope=run.scope, **options)
        monkeypatch.setattr(replay, 'complete', forbidden)
        assert replay.run() == archived
        # Same-value existing episode reclosure writes are permitted, with every
        # table value, archive and retained artifact checked before construction.
        assert table_rows(store) == before and files(run.directory) == run_files
        assert files(store.path / 'artifacts') == artifacts and len(http_calls) == 2
        assert {name: (fixture / name).read_bytes() for name in pins} == originals
        (tmp_path / 'BV_BRC_FEATURE_SEQUENCE_JOIN.json').write_text(json.dumps(dict(
            qualification='scripted Workflow choices and controlled Solr replies over retained native rows; no live API/model',
            question=question, fixture_sha256=pins, original_sequence_source=run.sequence_source,
            original_feature_handoff=run.handoff, joined_source=joined_source, selected_selector=run.selection,
            feature_sequence_components=grading['feature_sequence_components'], typed_result=run.received_form,
            onward_typed_return=onward, received_values=received, http_requests=http_calls,
            actual_episode_counts=dict(episode_counts), actual_record_counts=actual_counts,
            actual_join_calls=dict(calculation_calls), closed_replay_rows_and_files_unchanged=True,
            replay_total_changes_delta=store.db.total_changes - changes), indent=2) + '\n')


def test_selected_process_received_molecular_join_with_caller_metadata_and_onward(tmp_path, monkeypatch):
    """Three selected native pages plus a separately received caller document.

    Native historical rows are copied literally into controlled Solr replies,
    not presented as live-v2 measurements. The caller document asserts only
    null/empty unknowns. No matching feature page is supplied or fetched.
    """
    from collections import Counter
    from email.message import Message
    from pathlib import Path
    from urllib.parse import quote, urlencode

    import gene_annotation_episode.bvbrc_data_publication as publication
    from gene_annotation_episode.bvbrc_data_views import bvbrc_data_fact_sources
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.materials import source_for_artifact
    from bvbrc_episode_fixture import RESOURCES, child, handoff_form, request, result_form, selector

    fixture = Path(__file__).with_name('fixtures') / 'bvbrc_molecular_join'
    pins = {'expression_page.body': 'f1c04ce4da4a246503395776eb00ebd7313cd32657e4fc2ca44cd7392044837b',
        'expression_page.meta.json': 'ce156981b9327c5e226b425707a1ff1060a18ec0dca81997577aedff5ceef09f',
        'bioset_page.body': 'b39070f2258f1b68b2d6d69c3de904d09efc32fbe47309a559079c83872ea628',
        'bioset_page.meta.json': '53f698c7f92dba30cd940cfa83c31759f3029e33fa283fa370f35d3b597ff127',
        'experiment_page.body': '33ccc4af468696e0d5e3ef7f2068d3e6f77c88e0436c6b2bf86249d4cea2fd41',
        'experiment_page.meta.json': '6d32c6a5c3dcfb24bd18c31f73ea7f2e47a7307844d4f432a9688826f18339a7'}
    originals = {name: (fixture / name).read_bytes() for name in pins}
    assert {name: hashlib.sha256(raw).hexdigest() for name, raw in originals.items()} == pins
    for name in ('expression_page', 'bioset_page', 'experiment_page'):
        metadata = json.loads(originals[name + '.meta.json'])
        assert metadata['sha256'] == pins[name + '.body']
        assert metadata['byte_count'] == len(originals[name + '.body'])
    native_rows = {collection: json.loads(originals[name + '.body']) for collection, name in (
        ('bioset', 'bioset_page'), ('experiment', 'experiment_page'), ('bioset_result', 'expression_page'))}
    result_ids = ['00000125-8a72-4eea-aad0-d58d4fdb772c', '00000317-5d60-4e06-9c35-c42e53fd5ae3']
    bioset_ids, experiment_ids = ['53111326', '57692532'], ['65769', '30087']
    assert [row['id'] for row in native_rows['bioset_result']] == result_ids
    assert [row['exp_id'] for row in native_rows['experiment']] == list(reversed(experiment_ids))
    measurements = ['counts', 'fpkm', 'tpm', 'log2_fc', 'p_value', 'z_score', 'other_value']
    supplied_fields = ['sample_ids', 'biological_replicate_ids', 'technical_replicate_ids',
        'measurement_units', 'normalization_method', 'pvalue_correction_method', 'contrast']
    document = {'records': [dict(result_id=result_id, bioset_id=bioset_id,
        sample_ids=None, biological_replicate_ids=None, technical_replicate_ids=None,
        measurement_units=[], normalization_method=None, pvalue_correction_method=None, contrast=None)
        for result_id, bioset_id in zip(result_ids, bioset_ids)]}
    fields = {
        'bioset': ['bioset_id', 'exp_id', 'entity_count', 'bioset_type', 'result_type', 'genome_id',
            'treatment_name', 'treatment_type', 'treatment_duration', 'analysis_group_1', 'analysis_group_2', 'analysis_method'],
        'experiment': ['exp_id', 'exp_name', 'exp_type', 'measurement_technique', 'genome_id',
            'samples', 'biosets', 'treatment_name', 'treatment_type', 'treatment_duration'],
        'bioset_result': ['id', 'feature_id', 'exp_id', 'bioset_id', 'entity_id', 'genome_id', 'result_type',
            'treatment_name', 'treatment_type', 'treatment_duration', *measurements]}
    queries, responses = [], []
    for collection, identity, values in (
            ('bioset', 'bioset_id', bioset_ids), ('experiment', 'exp_id', experiment_ids),
            ('bioset_result', 'id', result_ids)):
        query = request(collection, mode='page', fields=fields[collection],
            filters=[{'field': identity, 'operator': 'in', 'value': values}],
            sort=[{'field': identity, 'direction': 'asc'}], offset=0, limit=2)
        queries.append(query)
        q = identity + ':("' + '" OR "'.join(value.replace('-', r'\-') for value in values) + '")'
        parameters = [('q', q), ('rows', '2'), ('start', '0'),
            ('fl', ','.join(fields[collection])), ('sort', identity + ' asc')]
        url = RESOURCES['bvbrc']['base_url'] + '/' + collection + '/?' + urlencode(
            parameters, quote_via=quote, safe='')
        body = json.dumps({'responseHeader': {'status': 0, 'params': dict(parameters)},
            'response': {'docs': native_rows[collection], 'start': 0, 'numFound': 2, 'numFoundExact': True}},
            ensure_ascii=False, allow_nan=False).encode()
        responses.append(dict(url=url, body=body))
    http_calls = []

    class Response:
        status = 200

        def __init__(self, selected):
            self.selected, self.headers = selected, Message()
            self.headers['Content-Type'] = 'application/solr+json'
            self.headers['Content-Length'] = str(len(selected['body']))

        def __enter__(self): return self
        def __exit__(self, *_): return False
        def geturl(self): return self.selected['url']
        def read(self): return self.selected['body']

    def open_response(opener, native_request, *, timeout):
        assert len(http_calls) < 3, 'Molecular join attempted an unselected query or automatic page'
        expected = responses[len(http_calls)]
        assert native_request.full_url == expected['url']
        assert native_request.get_method() == 'GET' and native_request.data is None
        assert timeout == RESOURCES['bvbrc']['timeout']
        headers = {key.lower(): value for key, value in native_request.header_items()}
        assert headers['accept'] == 'application/solr+json'
        assert headers['content-type'] == 'application/solrquery+x-www-form-urlencoded'
        http_calls.append(dict(url=native_request.full_url, method='GET', timeout=timeout, headers=headers))
        return Response(expected)

    def forbidden(*args, **kwargs):
        raise AssertionError('Molecular join attempted live I/O or new closed-replay work')

    monkeypatch.setattr('urllib.request.OpenerDirector.open', open_response)
    monkeypatch.setattr('socket.create_connection', forbidden)
    extraction_calls, extract = [], publication.extract_molecular_experiment_rows

    def observed_extract(*args, **kwargs):
        extraction_calls.append(deepcopy(kwargs))
        return extract(*args, **kwargs)

    monkeypatch.setattr(publication, 'extract_molecular_experiment_rows', observed_extract)
    fact_source = 'execution_bvbrc_expression_rows'
    parent_form = {'type': 'object', 'additionalProperties': False, 'required': ['expression_rows'],
        'properties': {'expression_rows': deepcopy(bvbrc_data_fact_sources()[fact_source]['report_schema'])}}
    question = ('For the two selected expression-result records, what native log2 fold changes and z scores '
        'are reported, which bioset and experiment records are explicitly linked, and which feature, '
        'units, replication, normalization, correction and contrast information remains unavailable?')
    handoff_schema = handoff_form()

    class MolecularRun(SelectedProcessRun):
        def commission(self):
            action = super().commission()
            context = action['selection']['assignment']['context']
            context.pop('selected_native_count_query')
            context['selected_native_input_queries'] = deepcopy(queries)
            return action

        async def complete(self, episode_id, role, instructions, current, schema):
            if 'scientific_process' not in current:
                return await super().complete(episode_id, role, instructions, current, schema)
            self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
            count = self.calls[episode_id]
            self.contexts.append((episode_id, deepcopy(current)))
            assert current.get('feedback') is None, current.get('feedback')
            if count in (1, 3, 5):
                stage = (count - 1) // 2
                if count > 1:
                    prior = deepcopy(current['child_reports'][-1])
                    reference, = prior['references']
                    admitted = self.api.read_bvbrc_result(reference, context=self.context(episode_id))
                    assert admitted['host_qualification']['possession_basis'] == 'admitted_return'
                    self.input_sources.append(reference)
                    self.input_forms.append(prior)
                else:
                    self.input_sources, self.input_forms, self.handoffs = [], [], []
                    assert current['received_bvbrc_values'] == []
                self.api_assignment = {**deepcopy(self.api_assignment), 'request': deepcopy(queries[stage])}
                self.launch_assignment = {**deepcopy(self.launch_assignment),
                    'requests': {'bvbrc': deepcopy(self.api_assignment)}}
                return child('launch', self.launch_assignment, self.scope, handoff_schema)
            if count in (2, 4, 6):
                handoff, = current['child_reports'][-1]['references']
                self.handoffs.append(handoff)
                if count < 6:
                    self.selection, self.result_form = selector(), result_form('execution_bvbrc_pages')
                else:
                    metadata_fields = ([{'source_level': 'result', 'field': field} for field in
                        ('result_type', 'treatment_name', 'treatment_type', 'treatment_duration')]
                        + [{'source_level': 'bioset', 'field': field} for field in
                            ('entity_count', 'exp_id', 'treatment_duration', 'analysis_group_1', 'analysis_group_2', 'analysis_method')]
                        + [{'source_level': 'experiment', 'field': field} for field in
                            ('exp_name', 'measurement_technique', 'biosets', 'samples', 'treatment_duration')]
                        + [{'source_level': 'supplied', 'field': field} for field in supplied_fields])
                    self.selection = selector({'family': 'molecular_experiment', 'result_ids': result_ids,
                        'measurement_fields': measurements, 'metadata_fields': metadata_fields}, inputs=[
                            {'collection': name, 'source_ref': reference} for name, reference in
                            zip(('bioset', 'experiment'), self.input_sources)], supplied=[
                                {**record, 'provenance': {'source_ref': caller_source,
                                    'record_path': '/records/' + str(index)}}
                                for index, record in enumerate(document['records'])])
                    self.result_form = result_form(fact_source)
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': handoff, 'selector': self.selection}, self.scope, self.result_form)
            assert count == 7
            self.scientific_after_result = deepcopy(current)
            self.received_form = deepcopy(current['child_reports'][-1])
            return self.wait()

    def table_rows(store):
        names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: sorted((tuple((type(value).__name__, value) for value in row)
            for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')),
            key=repr) for name in names}

    def files(directory):
        return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob('*') if path.is_file()}

    with Store(tmp_path / 'state') as store:
        sequence = ''.join(line.strip() for line in (Path(__file__).parents[1] / 'cases/gene_001/target.faa').read_text().splitlines()
            if not line.startswith('>'))
        scope = {'subject_refs': store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']}
        caller_bytes = canonical(document).encode('utf-8')
        caller_artifact = store.artifact(caller_bytes, 'application/json')
        caller_source = source_for_artifact(store, caller_artifact)['id']
        foreign_document = {**document, 'unselected': True}
        foreign_source = source_for_artifact(store, store.artifact(canonical(foreign_document).encode('utf-8'),
            'application/json'))['id']
        options = dict(scope=scope, selected_query=queries[0], result_sources=('execution_bvbrc_pages',),
            parent_form=parent_form, question=question, scientific_action_count=7,
            initial_known_record_refs=[caller_source])
        run = MolecularRun(store, tmp_path / 'run', **options)
        run.run()
        contexts = {row['episode_id']: run.context(row['episode_id']) for row in run.rows('runtime_episodes')}
        root, scientific = run.archive, run.archive['units'][0]['child']
        root_context, sci_context = contexts[root['episode_id']], contexts[scientific['episode_id']]
        counts = Counter(context.role for context in contexts.values())
        records = {table: {role: sum(len(run.rows(table, ref)) for ref, context in contexts.items() if context.role == role)
            for role in counts} for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls')}
        assert dict(counts) == {'annotation': 1, 'scientific_process': 1, 'launch': 3, 'launch_api': 3, 'results': 3}
        assert len(contexts) == 11
        assert all(value == {'annotation': 2, 'scientific_process': 7, 'launch': 3, 'launch_api': 3, 'results': 3}
            for value in records.values())
        assert all(len(run.rows(table)) == 18 for table in records)
        selected_tools = plain(sci_context.assignment)['selection']['child_tool_info']
        assert all(set(value) == {'name', 'description', 'resources', 'instructions'} for value in selected_tools)
        assert [{'name': value['name'], 'resources': value['resources']} for value in selected_tools] == SELECTED_TOOLS
        assert plain(sci_context.assignment)['selection']['evidence_axis'] == run.library.reference('A101')
        assert plain(sci_context.assignment)['selection']['thought_pattern'] == run.library.reference('P01')
        assert caller_source in plain(sci_context.assignment)['evidence_refs']
        initial = {row['record_ref'] for row in store.db.execute('SELECT record_ref FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? AND receipt_kind=?', (run.run_id, root_context.episode_id, 'initial'))}
        assert {caller_source, caller_artifact} <= initial and foreign_source not in initial
        assert run.api.received_input_reader.__self__ is run.workflow.services
        join_context, = [context for context in contexts.values() if context.role == 'results'
            and plain(context.assignment)['handoff_ref'] == run.handoffs[-1]]
        metadata, path = run.api.received_input_reader(join_context, caller_source, 'source', file_format='json')
        assert metadata['failure'] is None and metadata['input']['byte_verification'] == 'verified'
        assert metadata['input']['file']['artifact_ref'] == caller_artifact and path.read_bytes() == caller_bytes
        assert metadata['input']['inheritance_manifest']['parent_episode_id'] == sci_context.episode_id
        inherited = set(run.workflow.receipts.known(join_context.episode_id, baseline=True))
        assert {caller_source, caller_artifact} <= inherited
        result_initial = {row['record_ref'] for row in store.db.execute('SELECT record_ref FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? AND receipt_kind=?', (run.run_id, join_context.episode_id, 'initial'))}
        assert caller_source not in result_initial and caller_artifact not in result_initial
        assert {run.handoffs[-1], *run.input_sources} <= result_initial
        denied, denied_path = run.api.received_input_reader(join_context, foreign_source, 'source', file_format='json')
        assert denied['input'] is None and denied_path is None and denied['failure']['code'] == 'reference_not_received'
        joined_source, = run.received_form['references']
        joined = run.api.read_bvbrc_result(joined_source, context=join_context)
        input_results = [run.api.read_bvbrc_result(reference, context=join_context) for reference in run.input_sources]
        assert joined['input_results'] == [{'binding': value['binding'], 'sheet': value['grading']['parse_result']['sheet']}
            for value in input_results]
        for qualified, expected, query in zip([*input_results, joined], responses, queries):
            source = store.get(qualified['binding']['source_ref'])
            assert store.get_artifact(source['artifact_ref']) == expected['body']
            assert json.loads(expected['body'])['response']['docs'] == native_rows[query['collection']]
            assert qualified['grading']['prepared']['original_request'] == query
            assert qualified['grading']['prepared']['native_request']['url'] == expected['url']
        assert store.get(caller_source)['provider'] == 'caller' and store.get_artifact(caller_artifact) == caller_bytes
        assert len(http_calls) == 3 and len(extraction_calls) == 1
        executor = run.workflow.episode_bindings.for_role('results')
        fresh = store.db.execute('SELECT coalesce(max(decision_index),-1)+1 FROM runtime_actions '
            'WHERE run_id=? AND episode_id=?', (run.run_id, sci_context.episode_id)).fetchone()[0]
        before_preflight, preflight_changes = table_rows(store), store.db.total_changes
        for offset, (defect, code) in enumerate((
                ('unreceived_metadata', 'bvbrc_host_metadata_reference_not_received'),
                ('caller_as_native_input', 'not_an_api_acquired_result'))):
            index = fresh + offset
            assert store.db.execute('SELECT count(*) FROM runtime_actions WHERE run_id=? AND episode_id=? '
                'AND decision_index=?', (run.run_id, sci_context.episode_id, index)).fetchone()[0] == 0
            assert store.db.execute('SELECT count(*) FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? '
                'AND decision_index=?', (run.run_id, sci_context.episode_id, index)).fetchone()[0] == 0
            selection = plain(join_context.assignment)
            if defect == 'unreceived_metadata':
                selection['selector']['supplied_metadata'][0]['provenance']['source_ref'] = foreign_source
            else:
                selection['selector']['inputs'][0]['source_ref'] = caller_source
            with pytest.raises(ValueError) as rejected:
                executor.prepare_assignment(sci_context, 'results', selection, run.scope,
                    f'{run.run_id}:{sci_context.episode_id}:{index}')
            assert str(rejected.value) == code
            assert table_rows(store) == before_preflight and store.db.total_changes == preflight_changes
        grading, sheet = joined['grading'], joined['grading']['molecular_sheet']
        assert grading['selector'] == run.selection and sheet['supplied_metadata'] == run.selection['supplied_metadata']
        assert [item['record_path'] for item in grading['metadata_bindings']] == ['/records/0', '/records/1']
        assert all(item['source_ref'] == caller_source and item['native_artifact_ref'] == caller_artifact
            and item['native_sha256'] == hashlib.sha256(caller_bytes).hexdigest() for item in grading['metadata_bindings'])
        assert [item['metadata_sha256'] for item in grading['metadata_bindings']] == [
            json_digest(record) for record in document['records']]
        group = materialized(run.scientific_after_result, fact_source)
        facts, cells = group['facts'], {cell['cell_ref']: cell for cell in group['cells']}
        assert len(facts) == len(sheet['rows']) == 2
        assert sheet['missing_result_ids'] == []
        assert sheet['requirements'] == [dict(collection='genome_feature', field='feature_id',
            values=[row['feature_id'] for row in native_rows['bioset_result']], sequence_kind=None, reason='missing_input_page')]
        for index, (row, molecular) in enumerate(zip(facts, sheet['rows'])):
            assert row['result_id'] == result_ids[index] and row['bioset_id'] == bioset_ids[index]
            assert row['exp_id'] == experiment_ids[index]
            assert row['source_ref'] == joined_source and row['input_source_refs'] == run.input_sources
            assert row['metadata_source_refs'] == [caller_source]
            assert row['status'] == row['relationship_status'] == 'partial' and row['feature_row_refs'] == []
            assert molecular['feature']['status'] == 'missing_input' and molecular['feature']['reason'] == 'missing_input_page'
            for kind, source_ref, values, identity in (
                    ('bioset', run.input_sources[0], native_rows['bioset'], 'bioset_id'),
                    ('experiment', run.input_sources[1], native_rows['experiment'], 'exp_id')):
                selected, = [value for value in values if value[identity] == row[identity]]
                parent_sheet = input_results[0 if kind == 'bioset' else 1]['grading']['parse_result']['sheet']
                parent_row, = [value for value in parent_sheet['rows'] if value['native_id'] == selected[identity]]
                assert molecular[kind]['status'] == 'matched'
                assert row[kind + '_row_refs'] == [source_ref + '#' + parent_row['row_key']]
            actual = {value['field']: value for value in row['measurements']}
            assert set(actual) == {'log2_fc', 'z_score'}
            assert actual['log2_fc']['value'] == [-0.132, -0.129][index]
            assert actual['z_score']['value'] == [-0.544, -0.556][index]
            for value in actual.values():
                assert value['origin'] == 'native_reported' and value['unit_code'] is None
                assert value['unit_basis'] == value['denominator_basis'] == 'unknown'
                assert value['unit_value_refs'] == value['uncertainty_cell_refs'] == [] and value['denominator_value'] is None
                assert cells[value['cell_ref']]['atoms'][0]['number_value'] == value['value']
            assert row['unavailable'] == [{'field': field, 'reason': 'native_field_absent'}
                for field in measurements if field not in actual]
            selected_metadata = {(item['source_level'], item['field']): cells[item['value_ref']]
                for item in row['metadata_cells']}
            assert selected_metadata['bioset', 'entity_count']['atoms'][0]['string_value'] == ['3879', '3930'][index]
            assert selected_metadata['experiment', 'biosets']['atoms'][0]['number_value'] == [15, 16][index]
            assert selected_metadata['experiment', 'measurement_technique']['atoms'][0]['string_value'] == 'Microarray'
            assert selected_metadata['bioset', 'treatment_duration']['atoms'][0]['string_value'] == ['5 mins', ''][index]
            assert {'source_level': 'experiment', 'field': 'samples', 'reason': 'native_field_absent'} in row['metadata_unavailable']
            for field in supplied_fields:
                cell = selected_metadata['supplied', field]
                assert cell['source_ref'] == caller_source and cell['collection'] is None and cell['row_ref'] is None
                assert cell['cell_ref'].endswith('/records/' + str(index) + '/' + field)
                assert cell['atoms'] == []
                expected = ('present', 'array', 'valid', 'unknown_units') if field == 'measurement_units' else ('null', 'null', 'missing', 'native_null')
                assert (cell['presence'], cell['native_shape'], cell['status']) == expected[:3]
                assert {'source_level': 'supplied', 'field': field, 'reason': expected[3]} in row['metadata_unavailable']
        onward = run.root_after_result['child_reports'][-1]
        assert canonical(run.received_form['expression_rows']) == canonical(facts)
        assert onward == {'expression_rows': facts}
        received = materialized(run.root_after_result, fact_source)
        assert canonical(received['facts']) == canonical(facts) and canonical(received['cells']) == canonical(group['cells'])
        resolve = run.workflow.resolver(run.scope, context=root_context)
        assert resolve(caller_source, 'source') is True and resolve(caller_source, 'execution_result') is False
        for row in facts:
            assert resolve(row['source_ref'], 'execution_result') is True
            for namespace, refs in (('bvbrc_data_row', [row['row_ref'], *row['bioset_row_refs'], *row['experiment_row_refs']]),
                    ('bvbrc_data_cell', [value['cell_ref'] for value in row['measurements']]
                        + [value['value_ref'] for value in row['metadata_cells']])):
                for reference in refs:
                    assert resolve(reference, namespace) is True and resolve(reference + '/forged', namespace) is False
        before = table_rows(store)
        for field in ('value', 'metadata_source'):
            forged = deepcopy(onward)
            if field == 'value': forged['expression_rows'][0]['measurements'][0]['value'] = 0
            else: forged['expression_rows'][0]['metadata_source_refs'] = [foreign_source]
            with pytest.raises(ReportBoundaryError) as rejected:
                run.workflow.validate_report(forged, run.scope, grain='scientific_process', schema=parent_form, context=sci_context)
            assert rejected.value.diagnostic['code'] == 'bvbrc_recorded_facts_mismatch'
            assert table_rows(store) == before
        assert store.count('annotation') == store.count('observation') == 0
        for name in ('extract_molecular_experiment_rows', 'calculate_page_counts', 'calculate_facet_fractions',
                'calculate_feature_sequence_counts', 'parse_data_snapshot', 'publish_bvbrc_data'):
            monkeypatch.setattr(publication, name, forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_data_molecular.extract_molecular_experiment_rows', forbidden)
        for name in ('calculate_page_counts', 'calculate_facet_fractions', 'calculate_feature_sequence_counts'):
            monkeypatch.setattr('gene_annotation_episode.bvbrc_data_calculators.' + name, forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_data_readers.parse_data_snapshot', forbidden)
        monkeypatch.setattr('gene_annotation_episode.bvbrc_data_query.encode_native_query', forbidden)
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc.encode_native_query', forbidden)
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc.BVBRCDataClient.query_prepared', forbidden)
        monkeypatch.setattr('gene_annotation_episode.api_bvbrc.BVBRCDataClient._query_once', forbidden)
        before, archived = table_rows(store), deepcopy(run.archive)
        run_files, artifacts, changes = files(run.directory), files(store.path / 'artifacts'), store.db.total_changes
        replay = MolecularRun(store, run.directory, **options)
        monkeypatch.setattr(replay, 'complete', forbidden)
        assert replay.run() == archived
        assert table_rows(store) == before and files(run.directory) == run_files
        assert files(store.path / 'artifacts') == artifacts and len(http_calls) == 3 and len(extraction_calls) == 1
        assert {name: (fixture / name).read_bytes() for name in pins} == originals
        (tmp_path / 'BV_BRC_MOLECULAR_JOIN.json').write_text(json.dumps(dict(
            qualification='scripted Workflow and controlled Solr replies over retained native rows; separate caller unknown metadata; no live API/model',
            question=question, fixture_sha256=pins, caller_source=caller_source, caller_artifact=caller_artifact,
            caller_document=document, native_input_sources=run.input_sources, original_handoffs=run.handoffs,
            joined_source=joined_source, selected_selector=run.selection, metadata_bindings=grading['metadata_bindings'],
            molecular_sheet=sheet, typed_result=run.received_form, onward_typed_return=onward,
            received_values=received, http_requests=http_calls, actual_episode_counts=dict(counts),
            actual_record_counts=records, actual_molecular_extraction_calls=len(extraction_calls),
            closed_replay_rows_and_files_unchanged=True, replay_total_changes_delta=store.db.total_changes-changes), indent=2) + '\n')
