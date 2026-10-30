"""Literal BV-BRC receiver display; retained HTTP and choices are controlled.

The main case uses the actual selected scientific/resource/typed-return path
and production presentation. The small formatting cases supply detached JSON;
they make no receipt, acquisition or scientific-association claim.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.bvbrc_data_views import bvbrc_data_fact_sources
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.providers import _SessionConnection, load_config
from gene_annotation_episode.state import Store
from bvbrc_episode_fixture import FEATURE_IDS, request
from bvbrc_selected_process_fixture import RetainedHTTP, SelectedProcessRun
from test_scientific_process_prompt_delivery import INSTRUCTION_TEXT, snapshot


QUESTION = 'For these two supplied feature IDs, how many matching feature records carry each annotation label?'
SECTION = 'Received BV-BRC Data API values'
SOURCES = ('execution_bvbrc_pages', 'execution_bvbrc_counts', 'execution_bvbrc_facets')


def _presenter(directory):
    return _SessionConnection(load_config(), directory, directory.parent)


def _forbidden(*args, **kwargs):
    raise AssertionError('Closed retained response replay attempted another operation')


class RenderedSelectedProcessRun(SelectedProcessRun):
    def __init__(self, *args, presenter, **kwargs):
        super().__init__(*args, **kwargs)
        self.presenter, self.presentations, self.previous = presenter, [], {}

    async def complete(self, episode_id, role, instructions, current, schema):
        if 'scientific_process' in current:
            original = canonical(current)
            frame = state_frame(current, self.previous.get(episode_id))
            saved_frame = canonical(frame)
            text, rendered_instructions = self.presenter._presentation(
                episode_id, role, instructions, frame)
            assert canonical(current) == original
            assert canonical(frame) == saved_frame
            self.presentations.append(dict(context=deepcopy(current), frame=deepcopy(frame),
                text=text, instructions=rendered_instructions, role=role))
            self.previous[episode_id] = deepcopy(current)
        return await super().complete(episode_id, role, instructions, current, schema)


def _rows(run):
    return {table: sorted((canonical(row) for row in run.rows(table))) for table in (
        'runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls',
        'runtime_forms', 'runtime_report_attempts', 'runtime_bvbrc_admissions', 'runtime_record_receipts')}


def _files(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob('*') if path.is_file()}


def test_selected_scientific_facet_return_renders_admitted_cells_at_actual_presentation(tmp_path, monkeypatch):
    http = RetainedHTTP(monkeypatch, response_name='feature_facet_solr_zero')
    assert hashlib.sha256(http.body).hexdigest() == 'dc1103ce8b6e1f45ac28a6b9a3d1ba0895f79d63b1c2c6aa31dce2e4d1175571'
    query = request(mode='facet', facet=dict(field='annotation', offset=0, limit=2,
        min_count=1, sort='index', include_missing=True))
    descriptors = bvbrc_data_fact_sources()
    parent_form = obj({source.removeprefix('execution_bvbrc_'):
        descriptors[source]['report_schema'] for source in SOURCES})
    options = dict(selected_query=query, result_sources=SOURCES, question=QUESTION,
        parent_form=parent_form)
    presenter = _presenter(tmp_path / 'presentation')
    with Store(tmp_path / 'state') as store:
        run = RenderedSelectedProcessRun(store, tmp_path / 'run', presenter=presenter, **options)
        run.run()
        assert len(http.calls) == 1
        assert run.query == query and run.api_assignment['request'] == query
        assert run.launch_assignment['requests']['bvbrc'] == run.api_assignment
        scientific = run.archive['units'][0]['child']
        results = scientific['units'][1]['child']
        context = run.scientific_after_result
        shown = run.presentations[-1]
        assert canonical(shown['context']) == canonical(context)
        assert [SECTION in item['text'] for item in run.presentations] == [False, False, True]
        assert all(QUESTION in item['text'] for item in run.presentations)
        assert all(item['text'].startswith('TASK\n\n') for item in run.presentations)
        assert context['goal']['objective'] == QUESTION
        assert context['scientific_process']['assignment']['context']['question'] == QUESTION
        assert context['scientific_process']['assignment']['context']['selected_native_count_query'] == query
        assert context['scientific_process']['assignment']['constraints']['preserve_original_query'] is True
        for identifier in FEATURE_IDS:
            assert identifier in shown['text'] and identifier in json.loads(http.body)['responseHeader']['params']['q']
        groups = context['received_bvbrc_values']
        by_source = {group['fact_source']: group for group in groups}
        counts, = by_source['execution_bvbrc_counts']['facts']
        page, = by_source['execution_bvbrc_pages']['facts']
        facets = by_source['execution_bvbrc_facets']
        assert counts['reported_value'] == 2 and counts['availability'] == 'available'
        assert counts['exactness'] == 'exact'
        assert page['returned_row_count'] == 0 and page['reported_total'] == 2
        assert page['mode'] == 'facet' and page['response_complete'] is True
        assert page['population_coverage'] == 'unknown'
        assert [row['count'] for row in facets['facts']] == [1, 1, 0]
        assert [row['denominator'] for row in facets['facts']] == [2, 2, 2]
        assert [row['fraction'] for row in facets['facts']] == [.5, .5, 0]
        assert [row['is_missing_bucket'] for row in facets['facts']] == [False, False, True]
        assert all(row['bucket_window_status'] == 'more_unknown' for row in facets['facts'])
        assert all(row['population_ref'] == counts['population_ref'] == page['population_ref']
            and row['source_ref'] == counts['source_ref'] == page['source_ref'] for row in facets['facts'])
        cells = {cell['cell_ref']: cell for cell in facets['cells']}
        terms = [cells[row['term_ref']] for row in facets['facts']]
        assert [cell['atoms'][0]['string_value'] for cell in terms if cell['atoms']] == ['PATRIC', 'RefSeq']
        assert terms[-1]['presence'] == 'null' and terms[-1]['native_shape'] == 'null'
        assert terms[-1]['atoms'] == [] and terms[-1]['status'] == 'missing'
        for row, cell in zip(facets['facts'], terms):
            assert cell['source_ref'] == row['source_ref'] and cell['source_level'] == 'facet'
            assert cell['field'] == row['field'] == 'annotation'
            assert (row['requested_offset'], row['requested_limit'], row['requested_min_count']) == (0, 2, 1)
        reference, = run.received_form['references']
        owned = run.api.read_bvbrc_result(reference, context=run.context(results['episode_id']))
        grading = owned['grading']
        assert grading['prepared']['original_request'] == query
        assert grading['prepared']['native_request']['url'] == http.metadata['url'] == http.calls[0]['url']
        assert store.get_artifact(owned['binding']['native_artifact_ref']) == http.body
        assert page['population_coverage'] == grading['parse_result']['sheet']['page']['population_coverage']
        for current in (run.context(results['episode_id']), run.context(scientific['episode_id']),
                run.context(run.archive['episode_id'])):
            resolve = run.workflow.resolver(run.scope, context=current)
            for namespace, semantic in (('bvbrc_data_population', counts['population_ref']),
                    ('bvbrc_data_bucket', facets['facts'][0]['bucket_ref']),
                    ('bvbrc_data_cell', facets['facts'][0]['term_ref'])):
                assert resolve(semantic, namespace) is True
                assert resolve(semantic + '/forged', namespace) is False
            assert resolve(counts['source_ref'], 'bvbrc_data_population') is False
        for source in SOURCES:
            field = source.removeprefix('execution_bvbrc_')
            assert canonical(run.received_form[field]) == canonical(by_source[source]['facts'])
            assert canonical(run.root_after_result['child_reports'][-1][field]) == canonical(by_source[source]['facts'])
        facet_index = next(index for index, group in enumerate(groups) if group['fact_source'] == 'execution_bvbrc_facets')
        page_index = next(index for index, group in enumerate(groups) if group['fact_source'] == 'execution_bvbrc_pages')
        assert f'| [{page_index}].facts[0].population_coverage | unknown |' in shown['text']
        for index in range(len(facets['facts'])):
            assert f'| [{facet_index}].facts[{index}].bucket_window_status | more_unknown |' in shown['text']
        assert f'| [{facet_index}].cells[0].atoms[0].string_value | PATRIC |' in shown['text']
        assert f'| [{facet_index}].cells[1].atoms[0].string_value | RefSeq |' in shown['text']
        assert f'| [{facet_index}].cells[2].presence | null |' in shown['text']
        assert f'| [{facet_index}].facts[2].count | 0 |' in shown['text']
        assert f'| [{facet_index}].facts[2].fraction | 0.0 |' in shown['text']
        assert f'| [{facet_index}].facts[2].denominator | 2 |' in shown['text']
        for index, group in enumerate(groups):
            assert f'| [{index}].form_field | {group["form_field"]} |' in shown['text']
            assert f'| [{index}].fact_source | {group["fact_source"]} |' in shown['text']
            assert group['admission_key'] not in shown['text']
        assert 'admission_key' not in shown['text'] and 'bvbrc_received_values_v1' not in shown['text']
        saved = run.workflow.journal.row('runtime_model_calls', scientific['episode_id'], 2)
        assert canonical(json.loads(saved['request'])['context']) == canonical(context)
        state = presenter.scientific_prompt_states[(scientific['episode_id'], shown['role'])]
        assert canonical(state) == canonical(context)
        before, files = _rows(run), _files(run.directory)
        archived = deepcopy(run.archive)
        replay = SelectedProcessRun(store, run.directory, scope=run.scope, **options)
        monkeypatch.setattr(replay, 'complete', _forbidden)
        assert replay.run() == archived
        assert _rows(replay) == before and _files(run.directory) == files and len(http.calls) == 1
        (tmp_path / 'BV_BRC_PRESENTATION.json').write_text(json.dumps(dict(
            qualification='engineering choices and retained HTTP replay; no live API or model',
            question=QUESTION, selected_query=query, native_body_sha256=hashlib.sha256(http.body).hexdigest(),
            retained_http_replays=len(http.calls), typed_result=run.received_form,
            scientific_received_values=groups, onward_typed_return=run.root_after_result['child_reports'][-1],
            rendered_scientific_text=shown['text']), indent=2) + '\n')


def _render_detached(tmp_path, groups):
    state = snapshot()
    if groups is not None:
        state['received_bvbrc_values'] = deepcopy(groups)
    before = canonical(state)
    presenter = _presenter(tmp_path / 'presentation')
    frame = state_frame(state)
    original = canonical(frame)
    text, _ = presenter._presentation('detached-format-control', 'REASONING', INSTRUCTION_TEXT, frame)
    assert canonical(state) == before and canonical(frame) == original
    return text


@pytest.mark.parametrize('qualification', ['unknown', 'partial_page'])
def test_received_bvbrc_qualification_values_are_literal(tmp_path, qualification):
    unknown = qualification == 'unknown'
    facts = [dict(source_ref='source_detached', collection='genome_feature', input_source_refs=[],
        metadata_source_refs=[], status='partial' if unknown else 'complete', mode='page',
        requested_offset=2, requested_limit=1, returned_row_count=0, valid_row_count=0,
        invalid_row_count=0, reported_total=None if unknown else 3, count_exactness='unknown' if unknown else 'exact',
        response_complete=not unknown, population_coverage='unknown' if unknown else 'subset',
        next_offset=None if unknown else 3, population_ref='source_detached#population',
        unavailable_reason='transport_incomplete' if unknown else None)]
    groups = [dict(version='bvbrc_received_values_v1', admission_key='DO_NOT_RENDER_ADMISSION',
        form_field='pages', fact_source='execution_bvbrc_pages', facts=facts, cells=[], unavailable=[])]
    text = _render_detached(tmp_path, groups)
    assert '| [0].facts[0].returned_row_count | 0 |' in text
    assert f'| [0].facts[0].population_coverage | {facts[0]["population_coverage"]} |' in text
    assert f'| [0].facts[0].reported_total | {"null" if unknown else "3"} |' in text
    assert f'| [0].facts[0].response_complete | {"false" if unknown else "true"} |' in text
    assert f'| [0].facts[0].next_offset | {"null" if unknown else "3"} |' in text
    assert '| [0].cells | empty array |' in text
    assert 'DO_NOT_RENDER_ADMISSION' not in text and 'bvbrc_received_values_v1' not in text


@pytest.mark.parametrize('groups', [None, []])
def test_unreceived_bvbrc_values_are_omitted(tmp_path, groups):
    assert SECTION not in _render_detached(tmp_path, groups)


def test_received_bvbrc_atom_escaping_is_literal(tmp_path):
    cell = dict(source_ref='source_detached', row_ref=None, cell_ref='source_detached#facet/0',
        collection='genome_feature', native_id=None, field='annotation', source_level='facet',
        presence='present', native_shape='scalar', atoms=[dict(kind='string',
            string_value='PATRIC|RefSeq\nliteral', number_value=None, boolean_value=None, number_lexeme=None)],
        status='valid', issue_codes=[])
    text = _render_detached(tmp_path, [dict(version='bvbrc_received_values_v1',
        admission_key='DO_NOT_RENDER_ADMISSION', form_field='facets', fact_source='execution_bvbrc_facets',
        facts=[], cells=[cell], unavailable=[dict(collection='genome_feature', native_id=None,
            field='annotation', source_level='facet', reason='native_field_absent')])])
    assert '| [0].cells[0].atoms[0].string_value | PATRIC\\|RefSeq<br>literal |' in text
    assert '| [0].cells[0].atoms[0].number_value | null |' in text
    assert '| [0].cells[0].atoms[0].boolean_value | null |' in text
    assert '| [0].unavailable[0].reason | native_field_absent |' in text
    assert 'DO_NOT_RENDER_ADMISSION' not in text and 'bvbrc_received_values_v1' not in text
