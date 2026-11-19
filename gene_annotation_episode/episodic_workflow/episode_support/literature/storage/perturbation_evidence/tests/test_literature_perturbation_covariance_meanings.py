"""Constructed covariance meaning custody, without new statistical arithmetic."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_storage import LiteraturePerturbationRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_summary_storage import LiteraturePerturbationSummaryProjection, perturbation_summary_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.perturbation_evidence.tests.test_literature_perturbation_summary import source_data, extract, calculate, covariance
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.tests.perturbation_summary_fixtures import fixture, source
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.tests.perturbation_case_fixtures import returned_form

FIELDS = ('summary_kind', 'summary_scale', 'spread_kind', 'spread_scale',
          'count_n', 'count_unit', 'count_independence')
SUPPORT = b'Constructed covariance design; covariance 0.000000000000000000, unrelated arm value 987654321.'
NAMES = ['perturbation_mean_variance']


def data_for(kind='mean_covariance', basis='source_reported', *, qualify=True, all_pairs=False):
    data = source_data(); data['exposure_unit'] = 'unreported'
    for role in ('W', 'K', 'R'):
        entry = data['measurements'][role]
        entry['count'].update(n=5, unit_kind='culture')
        entry['uncertainty'].update(kind='sem', value=1)
        entry['interpretation_basis'] = dict.fromkeys(FIELDS, 'source_supported_inference')
    if kind == 'paired_units':
        for role, values in [('W', [8, 13, 13, 13, 13]), ('K', [3, 0, 2, 4, 6])]:
            entry = data['measurements'][role]; entry['value'] = None
            entry['uncertainty'].update(kind='unreported', value=None)
            entry['raw_units'] = [{'unit_id': 'unit' + str(i), 'values': [value]}
                                  for i, value in enumerate(values)]
    pairs = (('W', 'K'), ('W', 'R'), ('K', 'R')) if all_pairs else (('W', 'K'),)
    data['covariances'] = []
    for first, second in pairs:
        item = covariance(first, second, kind, 0 if kind == 'mean_covariance' else None)
        if qualify:
            item['interpretation_basis'] = basis
        data['covariances'].append(item)
    return data


def covariance_fixture(path, kind='mean_covariance', basis='source_reported', *, names=NAMES,
                       with_support=True, data=None):
    store, context, args = fixture(path)
    data = data_for(kind, basis) if data is None else deepcopy(data)
    additions = []
    if with_support:
        support = source(store, SUPPORT, parents=[args['source_ref']])
        additions.append(support['id'])
        witness = {'source_ref': support['id'], 'representation': 'original',
            'start': 0, 'end': len(SUPPORT), 'quote': SUPPORT.decode()}
        for row in data['covariances']:
            row['witnesses'] = [deepcopy(witness)]
    retained = source(store, canonical(data), parents=[args['source_ref']])
    additions.append(retained['id']); args['data_source_ref'] = retained['id']
    context = replace(context, assignment={**context.assignment,
        'source_refs': [*context.assignment['source_refs'], *additions],
        'requested_perturbation_summary_components': names},
        received_record_refs=(*context.received_record_refs, *additions))
    return store, context, args


def selected(path, kind='mean_covariance', basis='source_reported', **kwargs):
    store, context, args = covariance_fixture(path, kind, basis, **kwargs)
    outcome = LiteraturePerturbationRepository(store, context.run_id).populate(context, args, 'covariance-selected')
    assert outcome['status'] == 'completed', outcome.get('feedback')
    context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    schema = obj({'measurements': perturbation_summary_cells_schema()})
    projection = LiteraturePerturbationSummaryProjection(store, context.run_id)
    form = returned_form(projection, context, [outcome['result']['sheet_ref']], schema,
                         context.assignment['requested_perturbation_summary_components'])
    return store, context, projection, outcome, schema, form


@pytest.mark.parametrize('basis', [None, True, 1, 'probably_reported'])
def test_covariance_interpretation_basis_is_closed_and_never_inferred(basis):
    data = data_for(); data['covariances'][0]['interpretation_basis'] = basis
    with pytest.raises(ExperimentalContractError, match='unsupported_summary_meaning'):
        extract(data)


def test_optional_capture_does_not_change_any_numerical_cell_or_old_payload_shape():
    old = calculate(data_for(qualify=False))
    new = calculate(data_for())
    assert old['cells'] == new['cells']
    assert 'covariance_descriptors' not in old
    assert new['covariance_descriptors'][0]['interpretation_basis'] == 'source_reported'
    assert new['covariance_descriptors'][1]['interpretation_basis'] is None
    assert new['covariance_descriptors'][1]['selection'] == 'unreported'


def test_same_numbers_keep_distinct_meanings_through_parent_receipt(tmp_path):
    for kind, basis in [('mean_covariance', 'source_reported'), ('uncorrelated', 'conditional_assumption'),
                        ('paired_units', 'source_supported_inference')]:
        store, context, projection, outcome, schema, form = selected(tmp_path / kind, kind, basis)
        try:
            row, = form['measurements']; qualifier, = row['covariance_interpretations']
            assert row['value'] == 2
            assert (qualifier['first'], qualifier['second']) == ('W', 'K')
            assert qualifier['kind'] == kind and qualifier['interpretation_basis'] == basis
            assert qualifier['use'] == 'used_selected_covariance'
            assert 'value' not in qualifier
            parent = replace(context, role='annotation', episode_id='covariance-parent', assignment={},
                path=(('annotation', 'root'),))
            projection.receive_cells(parent, form['measurements'], 'covariance-admission')
            assert projection.received_cells(parent) == form['measurements']
        finally:
            store.close()


def test_only_component_relevant_pairs_cross_the_exact_original_form(tmp_path):
    data = data_for('uncorrelated', 'conditional_assumption', all_pairs=True)
    names = ['W_summary_value', 'perturbation_mean_variance', 'restoration_mean_variance', 'shared_contrast_covariance']
    store, context, projection, outcome, schema, form = selected(tmp_path, data=data, names=names)
    try:
        rows = form['measurements']
        assert 'covariance_interpretations' not in rows[0]
        assert [(r['first'], r['second']) for r in rows[1]['covariance_interpretations']] == [('W', 'K')]
        assert [(r['first'], r['second']) for r in rows[2]['covariance_interpretations']] == [('K', 'R')]
        assert [(r['first'], r['second']) for r in rows[3]['covariance_interpretations']] == [('W', 'K'), ('W', 'R'), ('K', 'R')]
        for defect in ('omission', 'basis', 'kind', 'support'):
            bad = deepcopy(rows[1:2])
            if defect == 'omission':
                bad[0].pop('covariance_interpretations')
            else:
                qualifier = bad[0]['covariance_interpretations'][0]
                if defect == 'basis': qualifier['interpretation_basis'] = 'source_reported'
                elif defect == 'kind': qualifier['kind'] = 'mean_covariance'
                else: qualifier['support_refs'] = [rows[2]['covariance_interpretations'][0]['support_refs'][0]]
            with pytest.raises(ContractError, match='differs_from_saved'):
                projection.validate_returned_values(bad, permitted_record_refs=context.received_record_refs)
        wrong_pair = deepcopy(rows[1:2]); wrong_pair[0]['covariance_interpretations'][0]['second'] = 'R'
        with pytest.raises(ContractError): validate_schema(wrong_pair, perturbation_summary_cells_schema())
        resolver_denied = set(rows[1]['covariance_interpretations'][0]['support_refs'])
        with pytest.raises(ReportBoundaryError) as denied:
            validate_form(form, schema, lambda ref, namespace: ref not in resolver_denied)
        assert denied.value.diagnostic['code'] == 'unknown_reference'
        parent = replace(context, role='annotation', episode_id='covariance-parent', assignment={}, path=(('annotation', 'root'),))
        projection.receive_cells(parent, rows[1:2], 'one-pair-admission')
        assert projection.received_cells(parent) == rows[1:2]
        assert projection.fact_cells(parent, [rows[1]['sheet_ref']], components=['restoration_mean_variance']) == []
        with pytest.raises(ContractError, match='cell_not_received'):
            projection.validate_fact_values(parent, rows[2:3])
        next_parent = replace(parent, episode_id='covariance-grandparent')
        projection.receive_cells(next_parent, projection.received_cells(parent), 'forward-pair')
        assert projection.received_cells(next_parent) == rows[1:2]
    finally:
        store.close()


@pytest.mark.parametrize('unavailable', ['unknown_covariance', 'incompatible_estimator'])
def test_unknown_or_unavailable_estimator_is_not_presented_as_applied_covariance(tmp_path, unavailable):
    data = data_for('unknown' if unavailable == 'unknown_covariance' else 'uncorrelated',
                    'unresolved' if unavailable == 'unknown_covariance' else 'conditional_assumption')
    if unavailable == 'incompatible_estimator':
        data['measurements']['W']['summary_kind'] = 'median'
    names = ['perturbation_mean_variance', 'perturbation_variance_upper']
    store, context, projection, outcome, schema, form = selected(tmp_path, data=data, names=names, with_support=False)
    try:
        exact, bound = form['measurements']
        assert exact['value'] is None
        assert exact['covariance_interpretations'][0]['use'] == 'component_unavailable'
        if unavailable == 'unknown_covariance':
            assert exact['unavailable_reason'] == 'cross_arm_covariance_unknown'
            assert bound['value'] == 4
            assert bound['covariance_interpretations'][0]['use'] == 'unknown_covariance_enclosure'
        else:
            assert exact['unavailable_reason'] == 'mean_variance_unavailable'
            assert bound['value'] is None and bound['covariance_interpretations'][0]['use'] == 'component_unavailable'
        assert exact['covariance_interpretations'][0]['support_refs'] == []
    finally:
        store.close()




