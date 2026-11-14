"""Detached rendering checks for received BV-BRC values."""
from copy import deepcopy

import pytest

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.providers import _SessionConnection, load_config
from test_scientific_process_prompt_delivery import INSTRUCTION_TEXT, snapshot


SECTION = 'Received BV-BRC Data API values'


def _presenter(directory):
    return _SessionConnection(load_config(), directory, directory.parent)


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
