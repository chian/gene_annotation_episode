"""Saved numeric/meaning/owner/output forgery and source-free validation checks."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_ratio_source_calculations import populate_relative_signal_v2
from gene_annotation_episode.literature_ratio_source_inputs import validate_relative_signal_source_extraction
from gene_annotation_episode.literature_ratio_source_validation import validate_relative_signal_saved
from test_literature_ratio_source_inputs import extract, request, visual, image, prose, VIEW, VIEW2, TEXT


def saved(rows=None):
    selection = request([visual()] if rows is None else rows)
    extraction, _ = extract(selection)
    sheet = populate_relative_signal_v2(extraction)
    ref = 'source_' + '1' * 24
    outcome = {'status': 'completed', 'operation_ref': 'operation_' + '2' * 24,
        'record_refs': [ref], 'changed_record_refs': [ref], 'feedback': None,
        'result': {'sheet_ref': ref, 'cells': deepcopy(sheet['cells']),
            **{k: sheet[k] for k in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict')}}}
    return selection, extraction, sheet, outcome


def test_saved_whole_api_source_free_and_detached(monkeypatch):
    from gene_annotation_episode import literature_ratio_source_inputs as inputs
    from gene_annotation_episode import literature_ratio_source_calculations as calculations
    from PIL import Image
    selected, extraction, sheet, outcome = saved([prose(), visual()])
    before = deepcopy((selected, extraction, sheet, outcome))
    def forbidden(*a, **kw):
        raise AssertionError('saved validation called forbidden source/reader/calculator/decoder')
    for module, name in ((inputs, 'read_relative_signal_source_inputs'), (inputs, '_view_bytes'),
                         (inputs, '_jats_expression'), (inputs, '_jats_matches'),
                         (calculations, 'populate_relative_signal_v2'), (calculations, '_component_facts'), (Image, 'open')):
        monkeypatch.setattr(module, name, forbidden)
    validate_relative_signal_saved(selected, extraction, sheet, outcome)
    assert (selected, extraction, sheet, outcome) == before


@pytest.mark.parametrize('path,value', [
    (('representations', 0, 'readings', 0, 'ratio'), .9),
    (('representations', 0, 'readings', 0, 'ratio_exact', 'numerator'), '9'),
    (('representations', 0, 'readings', 0, 'numerator', 'value'), .9),
    (('representations', 0, 'readings', 0, 'numerator', 'exact', 'denominator'), '7'),
    (('representations', 0, 'readings', 0, 'numerator', 'literal'), '0.9'),
    (('representations', 0, 'readings', 0, 'reported_domains', 0, 'lower'), .9),
    (('representations', 0, 'readings', 0, 'source_reading_key'), 'f' * 64),
    (('representations', 0, 'readings', 0, 'numerator', 'locator', 'frame'), 9),
    (('representations', 0, 'readings', 0, 'numerator', 'locator', 'original_source_ref'), 'source_' + 'f' * 24),
    (('representations', 0, 'origin'), 'reported'),
    (('representations', 0, 'reading_state'), 'conflicting'),
    (('representations', 0, 'parse_status'), 'unavailable'),
    (('representations', 0, 'physical_measurement', 'value'), 'fake_owner'),
    (('representations', 0, 'comparison_relation', 'value'), 'unknown'),
    (('representations', 0, 'comparison_relation', 'witnesses', 0, 'authentication'), 'unavailable'),
    (('views', 0, 'own_action_receipt', 'view_ref'), VIEW2),
    (('views', 0, 'metadata', 'width'), 1),
    (('views', 0, 'state'), 'unavailable'),
    (('views', 0, 'original_sha256'), 'bad'),
    (('evidence_origin',), 'reported_source'),
    (('comparison', 'endpoint', 'status'), 'known'),
])
def test_saved_extraction_forgery_rejected(path, value):
    selection, extraction, sheet, outcome = saved()
    target = extraction
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    with pytest.raises(ExperimentalContractError):
        validate_relative_signal_saved(selection, extraction, sheet, outcome)


@pytest.mark.parametrize('component,field,value', [
    ('reported_ratio', 'value', .9), ('reported_ratio', 'value_candidates', [.9]),
    ('reported_ratio', 'reported_domains', []), ('reported_ratio', 'status', 'unavailable'),
    ('reported_ratio', 'unavailable_reason', 'reported_limit_not_point'), ('reported_ratio', 'origin', 'reported'),
    ('reported_ratio', 'conditional_on', []), ('reported_ratio', 'formula', 'forged'),
    ('difference_from_reference', 'value', .4), ('log_reported_ratio', 'value', 0.),
    ('calibrated_amount_ratio', 'value', .6), ('amount_adjusted_effect', 'unit', 'fraction'),
    ('source_profile_log_ratio', 'unavailable_reason', 'numerical_model_range'),
])
def test_saved_sheet_forgery_even_matching_outcome_rejected(component, field, value):
    selection, extraction, sheet, outcome = saved()
    sheet['cells'][component][field] = value
    outcome['result']['cells'] = deepcopy(sheet['cells'])
    with pytest.raises(ExperimentalContractError):
        validate_relative_signal_saved(selection, extraction, sheet, outcome)


def test_saved_roster_and_completeness_reason_domain_relations():
    for part in ('selection', 'representations', 'views'):
        selection, extraction, sheet, outcome = saved()
        if part == 'selection':
            extraction['selection']['source_ref'] = 'source_' + 'f' * 24
        else:
            extraction[part] = []
        with pytest.raises(ExperimentalContractError):
            validate_relative_signal_saved(selection, extraction, sheet, outcome)
    for field in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict'):
        selection, extraction, sheet, outcome = saved()
        sheet[field] = not sheet[field]
        outcome['result'][field] = sheet[field]
        with pytest.raises(ExperimentalContractError):
            validate_relative_signal_saved(selection, extraction, sheet, outcome)
    for literal in ('ND', '<0', '-1', '<.1', '0'):
        selection, extraction, sheet, outcome = saved([visual(literal)])
        validate_relative_signal_saved(selection, extraction, sheet, outcome)
        reading = extraction['representations'][0]['readings'][0]
        reading['diagnostics'] = []
        if literal in ('<.1', '0'):
            sheet['cells']['reported_ratio']['reported_domains'][0]['lower_closed'] = False
            outcome['result']['cells'] = deepcopy(sheet['cells'])
        with pytest.raises(ExperimentalContractError):
            validate_relative_signal_saved(selection, extraction, sheet, outcome)


def test_saved_native_outcome_closed_dictionary_membership_not_projected_array():
    for mutate in (lambda o: o.update(status='failed'), lambda o: o.update(feedback={}),
                   lambda o: o.update(operation_ref=''), lambda o: o.update(extra=1),
                   lambda o: o['record_refs'].append(o['record_refs'][0]),
                   lambda o: o.update(changed_record_refs=['source_' + 'f' * 24]),
                   lambda o: o['result'].update(sheet_ref='source_' + 'f' * 24),
                   lambda o: o['result'].update(cells=[]), lambda o: o['result'].update(selected_roster_resolved=False),
                   lambda o: o['result']['cells'].pop('source_signed_index')):
        selection, extraction, sheet, outcome = saved()
        mutate(outcome)
        with pytest.raises(ExperimentalContractError):
            validate_relative_signal_saved(selection, extraction, sheet, outcome)
    selection, extraction, sheet, outcome = saved()
    with pytest.raises(ExperimentalContractError):
        validate_relative_signal_saved(selection, extraction, sheet, [{'component': 'reported_ratio'}])


def test_runtime_all_three_schema_definitions_equal_normative008():
    from gene_annotation_episode import literature_ratio_source_inputs as inputs
    base = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_reader_070/normative'
    for family in ('REQUEST', 'EXTRACTION', 'SHEET'):
        assert getattr(inputs, '_' + family + '_SCHEMA') == json.loads((base / (family + '_SCHEMA_008.json')).read_text())


def test_generic_html_text_span_saved_forgery_and_actual_jats_unchanged(monkeypatch):
    from gene_annotation_episode import literature_ratio_source_inputs as inputs
    from gene_annotation_episode.literature_ratio_source_inputs import read_relative_signal_source_inputs
    from test_literature_ratio_source_inputs import callbacks
    selected = request([prose(), visual()])
    content = '<p>\u03bc source label</p>'.encode('utf-8')
    start = len('<p>'.encode('utf-8'))
    quote = '\u03bc source'
    witness = {'kind': 'text', 'source_ref': TEXT, 'representation': 'text',
        'start': start, 'end': start + len(quote.encode('utf-8')), 'quote': quote}
    selected['comparison']['subject'] = {'status': 'known', 'value': 'fixture subject', 'witnesses': [witness]}
    source, view, _ = callbacks(text=content)
    extraction = read_relative_signal_source_inputs(selected, read_source=source, read_view=view, evidence_origin='synthetic_fixture')
    locator = extraction['comparison']['subject']['witnesses'][0]['locator']
    assert locator['kind'] == 'text_span' and locator['start'] == 3 and locator['end'] == 12
    assert set(locator) == {'kind', 'source_ref', 'artifact_ref', 'representation', 'start', 'end', 'quote'}
    actual_jats = extraction['representations'][0]['readings'][0]['numerator']['locator']
    assert actual_jats['kind'] == 'jats' and actual_jats['section_id'] == 's1'
    assert actual_jats['paragraph_index'] == 0 and actual_jats['paragraph_text'].startswith('SyntheticProtein')
    sheet = populate_relative_signal_v2(extraction)
    _, _, _, outcome = saved()
    outcome['result'].update(cells=deepcopy(sheet['cells']))
    for field in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict'):
        outcome['result'][field] = sheet[field]
    def forbidden(*a, **kw):
        raise AssertionError('saved read reacquired text')
    monkeypatch.setattr(inputs, 'read_relative_signal_source_inputs', forbidden)
    validate_relative_signal_saved(selected, extraction, sheet, outcome)
    for field, value in (('artifact_ref', 'artifact_' + 'f' * 24), ('representation', 'original'),
                         ('start', 4), ('end', 13), ('quote', 'forged')):
        bad = deepcopy(extraction)
        bad['comparison']['subject']['witnesses'][0]['locator'][field] = value
        with pytest.raises(ExperimentalContractError):
            validate_relative_signal_saved(selected, bad, sheet, outcome)
    invented = deepcopy(extraction)
    invented['comparison']['subject']['witnesses'][0]['locator'] = {
        'kind': 'jats', 'source_ref': TEXT, 'artifact_ref': locator['artifact_ref'],
        'section_id': 'exact_utf8_witness', 'paragraph_index': 0, 'paragraph_text': quote,
        'expression': quote, 'expression_start': 0, 'expression_end': len(quote)}
    with pytest.raises(ExperimentalContractError):
        validate_relative_signal_saved(selected, invented, sheet, outcome)


def test_canonical_multi_source_multi_view_saved_without_callbacks_or_decoders(monkeypatch):
    from gene_annotation_episode import literature_ratio_source_inputs as inputs
    from gene_annotation_episode import literature_ratio_source_calculations as calculations
    from PIL import Image
    from test_literature_ratio_source_inputs import multi_dependency_fixture
    selected, read_source, read_view, calls, data = multi_dependency_fixture()
    extraction = inputs.read_relative_signal_source_inputs(selected, read_source=read_source,
        read_view=read_view, evidence_origin='synthetic_fixture')
    sheet = calculations.populate_relative_signal_v2(extraction)
    assert sheet['cells']['reported_ratio']['value'] == .6
    assert sheet['independent_preparation_count'] is None
    _, _, _, outcome = saved()
    outcome['result'].update(cells=deepcopy(sheet['cells']))
    for field in ('selected_roster_resolved', 'point_candidate_set_complete', 'known_source_conflict'):
        outcome['result'][field] = sheet[field]
    canonical = json.loads(json.dumps({'selection': selected, 'extraction': extraction,
        'sheet': sheet, 'outcome': outcome}, sort_keys=True))
    before = deepcopy(canonical)
    previous_calls = list(calls)
    def forbidden(*a, **kw):
        raise AssertionError('canonical saved read reacquired source or recalculated')
    for module, name in ((inputs, 'read_relative_signal_source_inputs'), (inputs, '_available_call'),
            (inputs, '_view_bytes'), (inputs, '_jats_expression'), (inputs, '_jats_matches'),
            (calculations, 'populate_relative_signal_v2'), (calculations, '_component_facts'), (Image, 'open')):
        monkeypatch.setattr(module, name, forbidden)
    validate_relative_signal_saved(canonical['selection'], canonical['extraction'], canonical['sheet'], canonical['outcome'])
    assert canonical == before and calls == previous_calls
    assert [(row['source_ref'], row['representation']) for row in canonical['extraction']['sources']] == sorted(data)
    # Forging the canonical dependency roster is still rejected, not normalized.
    forged = deepcopy(canonical['extraction'])
    forged['sources'].reverse()
    with pytest.raises(ExperimentalContractError, match='sources.roster'):
        validate_relative_signal_saved(canonical['selection'], forged, canonical['sheet'], canonical['outcome'])
