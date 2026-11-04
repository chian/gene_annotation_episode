"""Closed plans, exact request identity and request-local native target errors."""
from copy import deepcopy

import pytest

from gene_annotation_episode import bvbrc_genome_alignment_calculation_contracts as contracts
from gene_annotation_episode import bvbrc_genome_alignment_calculators as calculators
from gene_annotation_episode.bvbrc_genome_alignment_sheet import build_genome_alignment_sheet, validate_genome_alignment_sheet
from test_bvbrc_genome_alignment_sheet import fixture_data, all_requests, plan, slot, resolution


@pytest.mark.parametrize('mutation', ['extra', 'v1', 'duplicate_id', 'missing_id', 'unknown_slot', 'wrong_kind',
    'implicit_selection', 'boolean_index', 'duplicate_pair', 'self_pair', 'bad_case', 'bad_basis',
    'false_source_denominator', 'missing_secondary', 'wrong_secondary', 'document_in_template', 'nonfinite', 'duplicate_cells'])
def test_plan_contract_errors_precede_all_dispatch(monkeypatch, mutation):
    data = fixture_data(); requests = all_requests(); value = plan(requests)
    if mutation == 'extra': value['requests'][0]['extra'] = True
    elif mutation == 'v1': value['schema_version'] = 'bvbrc_genome_alignment_components_v1'
    elif mutation == 'duplicate_id': value['requests'][1]['request_id'] = value['requests'][0]['request_id']
    elif mutation == 'missing_id': value['requests'][0]['request_id'] = ''
    elif mutation == 'unknown_slot': value['requests'][0]['document_slot_id'] = 'unknown'
    elif mutation == 'wrong_kind': value['requests'][0]['document_slot_id'] = 'xmfa'
    elif mutation == 'implicit_selection': value['requests'][0]['selection']['segments'] = 'all'
    elif mutation == 'boolean_index': value['requests'][5]['cells'][0]['column_0based'] = False
    elif mutation == 'duplicate_pair': value['requests'][3]['selected_pairs'] = [[1, 2], [2, 1]]
    elif mutation == 'self_pair': value['requests'][3]['selected_pairs'] = [[1, 1]]
    elif mutation == 'bad_case': value['requests'][3]['case_policy'] = 'automatic'
    elif mutation == 'bad_basis': value['requests'][4]['basis'] = 'whole_genome'
    elif mutation == 'false_source_denominator': value['requests'][1]['use_inputs'] = False
    elif mutation == 'missing_secondary': value['requests'][2]['xmfa_document_slot_id'] = None
    elif mutation == 'wrong_secondary': value['requests'][2]['xmfa_document_slot_id'] = 'v4'
    elif mutation == 'document_in_template': value['requests'][0]['selection']['document_id'] = 'extra'
    elif mutation == 'nonfinite': value['requests'][0]['selection']['segments'][0]['interval_index'] = float('nan')
    else: value['requests'][5]['cells'] *= 2
    def forbidden(*args, **kwargs):
        raise AssertionError('malformed complete plan reached native dispatch')
    monkeypatch.setattr(calculators, '_dispatch', forbidden)
    with pytest.raises(ValueError):
        calculators.calculate_genome_alignment_components(data, calculation_plan=value)


def target_requests():
    results = []
    originals = {r['kind']: r for r in all_requests()}
    for kind, errors in contracts.TARGET_ERRORS.items():
        for error in sorted(errors):
            request = deepcopy(originals[kind]); request['request_id'] = error
            if error.endswith('selection_member_unknown'):
                if kind.startswith('xmfa_'): request['selection']['member_numbers'].append(99)
                else:
                    member = deepcopy(request['selection']['members'][0]); member['index'] = 99
                    request['selection']['members'].append(member)
            elif error.endswith('selection_record_unknown'):
                if kind == 'mauve_v4_segments': request['selection']['segments'][0]['interval_index'] = 99
                else: request['selection']['row_indices'].append(99)
            elif error.endswith('selection_column_outside_record'):
                request['selection']['segments'][0]['column_ranges_0based_half_open'] = [[0, 100000]]
            elif error.endswith('selection_population_incomplete'):
                field = 'segments' if kind == 'mauve_v4_segments' else 'row_indices'
                request['selection'][field] = request['selection'][field][1:]
            elif error == 'xmfa_selection_block_outside_document': request['selection']['block_columns'][0]['block_index'] = 99
            elif error == 'xmfa_selection_column_outside_block': request['selection']['block_columns'][0]['columns_0based'] = [100000]
            elif error == 'xmfa_cell_block_outside_document': request['cells'][0]['block_index'] = 99
            elif error == 'xmfa_cell_record_outside_block': request['cells'][0]['record_index'] = 99
            elif error == 'xmfa_cell_column_outside_record': request['cells'][0]['column_0based'] = 100000
            elif error == 'xmfa_query_member_unknown': request['queries'][0]['member_number'] = 99
            elif error == 'xmfa_query_outside_source': request['queries'][0]['position_0based'] = 50
            else: raise AssertionError(error)
            results.append((kind + ':' + error, error, request))
    return results


@pytest.mark.parametrize('case,error,requested', target_requests(), ids=[r[0] for r in target_requests()])
def test_every_exact_native_target_error_is_local_and_replayable(case, error, requested):
    request = requested
    data = fixture_data(); following = all_requests()[3] | {'request_id': 'following-valid'}
    components = calculators.calculate_genome_alignment_components(data, calculation_plan=plan([request, following]))
    failed, success = components['outcomes']
    assert failed['state'] == 'incompatible' and failed['measurement'] is None
    assert failed['call'] is not None and failed['document_id'] is not None
    assert success['state'] == 'calculated' and success['request_id'] == 'following-valid' and success['request_index'] == 1
    reason = 'selection_target_missing' if error in contracts.MISSING_TARGET_ERRORS else 'selection_target_incompatible'
    cause = contracts._cause(data, request, 0, reason, affected=error)
    assert cause['requirements'][0] in failed['requirements']
    assert cause['diagnostics'][0] in failed['diagnostics']
    assert cause['diagnostics'][0]['path'] == '/calculation_plan/requests/0'
    assert cause['diagnostics'][0]['evidence_refs'] == [next(p['artifact']['source_ref'] for p in data['parsed_artifacts']
        if p['document']['document_id'] == failed['document_id'])]
    saved = build_genome_alignment_sheet(data=data, components=components)
    assert validate_genome_alignment_sheet(saved) == saved


DISPATCH_NAMES = {'mauve_v4_segments': 'calculate_mauve_v4_segments',
    'mauve_backbone': 'calculate_mauve_backbone_components', 'mauve_bbcols': 'calculate_mauve_bbcols_components',
    'xmfa_alignment': 'xmfa_alignment_components', 'xmfa_coverage': 'xmfa_interval_coverage',
    'xmfa_coordinates': 'xmfa_column_coordinates', 'xmfa_inverse_coordinates': 'xmfa_source_positions'}


@pytest.mark.parametrize('kind,name', list(DISPATCH_NAMES.items()))
@pytest.mark.parametrize('failure', ['selection_document_conflict', 'unlisted_native_failure', 'programming_failure'])
def test_unlisted_errors_propagate_from_every_dispatch(monkeypatch, kind, name, failure):
    data = fixture_data(); request = next(r for r in all_requests() if r['kind'] == kind)
    prefix = 'xmfa' if kind.startswith('xmfa_') else 'mauve_v4' if kind == 'mauve_v4_segments' else kind
    error = RuntimeError(failure) if failure == 'programming_failure' else ValueError(prefix + '_' + failure)
    def fail(*args, **kwargs): raise error
    monkeypatch.setattr(calculators, name, fail)
    with pytest.raises(type(error), match=str(error)):
        calculators.calculate_genome_alignment_components(data, calculation_plan=plan([request]))


def test_source_binder_errors_are_never_translated(monkeypatch):
    data = fixture_data(); request = all_requests()[4]
    def fail(*args, **kwargs): raise ValueError('xmfa_source_check_span_conflict')
    monkeypatch.setattr(calculators, 'bind_xmfa_sources', fail)
    with pytest.raises(ValueError, match='xmfa_source_check_span_conflict'):
        calculators.calculate_genome_alignment_components(data, calculation_plan=plan([request]))


@pytest.mark.parametrize('missing_index', [0, 1, 2])
def test_missing_first_middle_last_preserves_original_request_bijection(missing_index):
    data = fixture_data(include_missing=True)
    requests = [all_requests()[3] | {'request_id': 'request-' + str(i)} for i in range(3)]
    requests[missing_index]['document_slot_id'] = 'missing'
    comp = calculators.calculate_genome_alignment_components(data, calculation_plan=plan(requests))
    assert [o['request_id'] for o in comp['outcomes']] == [r['request_id'] for r in requests]
    assert [o['request_index'] for o in comp['outcomes']] == [0, 1, 2]
    for i, outcome in enumerate(comp['outcomes']):
        assert outcome['state'] == ('missing' if i == missing_index else 'calculated')
        if i == missing_index:
            assert outcome['call'] is outcome['measurement'] is outcome['document_id'] is None
            assert outcome['requirements'][0]['reason_code'].endswith('document_missing')
        else:
            assert outcome['measurement']['value']['blocks'][0]['pairs'][0]['identical_canonical']['value'] == 40


def test_empty_plan_and_duplicate_science_distinct_ids_are_explicit():
    data = fixture_data()
    empty = calculators.calculate_genome_alignment_components(data, calculation_plan=plan([]))
    assert empty['outcomes'] == empty['source_bindings'] == []
    requests = [all_requests()[4], all_requests()[4] | {'request_id': 'same-science-other-id'}]
    comp = calculators.calculate_genome_alignment_components(data, calculation_plan=plan(requests))
    assert comp['outcomes'][0]['measurement'] == comp['outcomes'][1]['measurement']
    assert comp['outcomes'][0]['request_id'] != comp['outcomes'][1]['request_id']
    assert len(comp['source_bindings']) == 1


def test_conflicting_slot_readers_for_same_artifact_reject():
    data = fixture_data(); extra = deepcopy(data['document_slots'][0]); extra['slot_id'] = 'different-reader'
    extra['reader']['encoding'] = 'utf-8'
    data['document_slots'].append(extra)
    res = deepcopy(data['slot_resolutions'][0]); res['slot_id'] = extra['slot_id']
    data['slot_resolutions'].append(res)
    from gene_annotation_episode.bvbrc_genome_alignment_sheet import validate_genome_alignment_data
    with pytest.raises(ValueError, match='slot_reader_conflict'):
        validate_genome_alignment_data(data)
