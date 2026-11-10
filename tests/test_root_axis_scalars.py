"""Actual opposition, measured zero and unknown scientific inputs stay distinct."""
from copy import deepcopy
import math

import pytest

from gene_annotation_episode.evidence_root import (
    SIGNED_COMBINATION_VERSION, offset_volume, signed_offset_volume,
)
from gene_annotation_episode.root_axis_scalars import (
    AXES, combine_scalars, correspondence_scalar,
    prerequisite_scalar, require_attribution,
)
from gene_annotation_episode.literature_a105_aggregation import annotation_scalar as a105_scalar
from gene_annotation_episode.literature_a106_subscore import annotation_scalar as a106_scalar
from gene_annotation_episode.literature_a108_aggregation import annotation_scalar as context_scalar
from gene_annotation_episode.a107_qualification import partner_requirement_scalar
from gene_annotation_episode.a110_qualification import chemical_constraint_scalar


def context_cell(support=(), conflict=(), unresolved=()):
    from gene_annotation_episode.literature_a108_grading import count_sets
    sets = dict(support=list(support), conflict=list(conflict), unresolved=list(unresolved))
    return dict(component='overall', status='complete', observation_sets=sets, **count_sets(sets))


def test_no_homology_information_is_unknown_and_never_opposes_a_function():
    missing = correspondence_scalar('A101', 0, measured=False)
    empty_analysis = correspondence_scalar('A101', 0, measured=True)
    assert missing['value'] is None and missing['direction'] == 'unknown'
    assert empty_analysis['value'] == 0 and empty_analysis['direction'] == 'measured_neutral'
    assert combine_scalars([missing])['credit'] == 0
    assert combine_scalars([missing])['axis_components']['A101'] is None
    assert combine_scalars([missing])['support'] == combine_scalars([missing])['opposition'] == 0
    assert combine_scalars([empty_analysis])['axis_components']['A101'] == 0
    with pytest.raises(ValueError, match='invalid_native_number'):
        correspondence_scalar('A101', -.5, measured=True)


def test_existing_positive_root_arithmetic_is_unchanged_and_missing_axes_are_neutral():
    actual = combine_scalars([correspondence_scalar('A101', .8, measured=True),
        correspondence_scalar('A102', .6, measured=True)])
    assert actual['credit'] == offset_volume({'A101': .8, 'A102': .6})['credit']
    assert actual['axis_components'] == dict.fromkeys(AXES, None) | {'A101': .8, 'A102': .6}
    assert len(actual['unknown_axes']) == 7
    assert actual['support'] == actual['credit'] and actual['opposition'] == 0
    assert actual['minimum'] == -31 and actual['maximum'] == 511
    assert actual['aggregation_version'] == SIGNED_COMBINATION_VERSION


def test_real_negative_experiment_reduces_support_while_missing_experiment_does_not():
    sequence = correspondence_scalar('A101', .8, measured=True)
    cell = dict(component='experimental_subscore', value=-2, status='complete', unit='natural_log_ratio')
    negative = a106_scalar(cell)
    unknown = a106_scalar(dict(cell, value=None, status='unavailable'))
    assert negative['value'] == math.tanh(-1) and negative['direction'] == 'opposition'
    assert combine_scalars([sequence, unknown])['credit'] == .8
    combined = combine_scalars([sequence, negative])
    assert combined['credit'] == pytest.approx(.8 + math.tanh(-1))
    assert combined['support'] == .8
    assert combined['opposition'] == pytest.approx(-math.tanh(-1))
    assert combined['credit'] < .8
    assert sum(combined['attribution'].values()) == pytest.approx(combined['credit'])


@pytest.mark.parametrize('vector,support,opposition,score', [
    ({'A105': .5, 'A106': .5}, 1.25, 0, 1.25),
    ({'A105': -.5, 'A106': -.5}, 0, 1.25, -1.25),
    ({'A105': .5, 'A106': -.5}, .5, .5, 0),
    ({'A101': .9, 'A105': -1, 'A108': None}, .9, 1, -.1),
    ({'A105': 0., 'A106': None}, 0, 0, 0),
    ({'A105': None, 'A106': None}, 0, 0, 0),
    ({'A105': -1, 'A106': -1}, 0, 3, -3),
])
def test_support_and_opposition_are_combined_separately(vector, support, opposition, score):
    result = signed_offset_volume(vector)
    assert result['support'] == pytest.approx(support)
    assert result['opposition'] == pytest.approx(opposition)
    assert result['credit'] == pytest.approx(score)
    assert result['minimum'] <= result['credit'] <= result['maximum']
    assert sum(result['attribution'].values()) == pytest.approx(score)
    assert result['additive'] + result['interaction'] == pytest.approx(score)


def test_interaction_and_attribution_do_not_mix_supporting_and_opposing_axes():
    vector = {'A101': .5, 'A102': .5, 'A105': -.5, 'A106': -.5, 'A108': None}
    result = signed_offset_volume(vector)
    interactions = {tuple(row['axes']): row['value'] for row in result['terms'] if len(row['axes']) > 1}
    assert interactions == {('A101', 'A102'): .25, ('A105', 'A106'): -.25}
    assert result['attribution'] == {
        'A101': .625, 'A102': .625, 'A105': -.625, 'A106': -.625, 'A108': 0}
    assert result['support'] == result['opposition'] == 1.25
    assert result['credit'] == 0
    assert result['unknown_axes'] == ['A108']


def test_generic_signed_combiner_handles_full_opposition_and_sign_reversal():
    all_opposing = signed_offset_volume(dict.fromkeys(AXES, -1))
    assert all_opposing['credit'] == all_opposing['minimum'] == -511
    vector = {'first': .7, 'second': -.4, 'third': -.8, 'missing': None}
    forward = signed_offset_volume(vector)
    reverse = signed_offset_volume({key: -value if value is not None else None for key, value in vector.items()})
    assert reverse['credit'] == pytest.approx(-forward['credit'])
    assert reverse['support'] == forward['opposition']
    assert reverse['opposition'] == forward['support']


def test_a105_uses_actual_existing_sum_including_opposing_experiments_without_mutation():
    from gene_annotation_episode.literature_a105_aggregation import aggregate_a105
    from test_literature_a105_aggregation_325 import pure_inputs
    args, rows = pure_inputs((2, -4))
    original = deepcopy((args, rows))
    cell = aggregate_a105(args, rows)['cells']['overall']
    scalar = a105_scalar(cell)
    assert scalar['value'] == pytest.approx(math.tanh(-1))
    assert scalar['native_inputs']['value'] == -2
    assert (args, rows) == original
    assert cell['annotation_credit'] is None


def test_partial_log_evidence_does_not_promote_an_available_subtotal_to_the_final_value():
    cell = dict(component='experimental_subscore', value=None, available_value=12,
        status='partial', unit='natural_log_ratio')
    assert a106_scalar(cell)['value'] is None
    with pytest.raises(ValueError, match='natural_log_ratio_required'):
        a105_scalar(dict(cell, component='overall', status='complete', value=2, unit='per_min'))
    from gene_annotation_episode.literature_a105_aggregation import aggregate_a105
    from test_literature_a105_aggregation_325 import pure_inputs
    arguments, sources = pure_inputs(())
    empty = aggregate_a105(arguments, sources)['cells']['overall']
    assert empty['unit'] == 'unknown'
    assert a105_scalar(empty)['value'] is None


def test_context_unions_keep_overlap_and_conflict_separate_from_unresolved_observations():
    cell = context_cell(['same', 'support'], ['same', 'conflict', 'other_conflict'], ['unknown'])
    scalar = context_scalar(cell)
    assert scalar['value'] == pytest.approx(-1 / 5)
    duplicate = deepcopy(cell)
    duplicate['observation_sets']['support'].append('same')
    assert context_scalar(duplicate)['value'] == scalar['value']
    assert context_scalar(context_cell(unresolved=['unknown']))['value'] is None
    assert context_scalar(context_cell(['same'], ['same']))['value'] == 0
    with pytest.raises(ValueError, match='context_count_set_mismatch'):
        context_scalar(dict(cell, evidence_amount=9))


def test_actual_context_graders_and_main_sheet_deduplicate_shared_observations_before_mapping():
    from gene_annotation_episode.domain import identity
    from gene_annotation_episode.literature_a108_grading import (
        INPUT_VERSION, CRITERIA_BY_TYPE, grade_context_evidence,
    )
    from gene_annotation_episode.literature_a108_aggregation import aggregate_a108
    assertion, context = identity('hypothesis', 'synthetic-root-context'), identity('context', 'synthetic-organism')
    source, subject = identity('source', 'synthetic-physiology'), identity('reference', 'synthetic-organism')
    rows = []
    for kind in ('physiology_resource_response', 'substrate_availability'):
        observations = []
        for index, relation in enumerate(('support', 'support', 'conflict')):
            observations.append(dict(original_observation_key=str(index),
                original_observation_ref=identity('reference', index), context_claim_ref=assertion,
                source_subject_ref=subject, source_context_ref=context, source_refs=[source],
                measurement_keys=[str(index)], origin='organism_physiology_report', target_relationship='direct',
                relation=relation, criteria={key: {'status': 'supported', 'support_refs': [source]}
                    for key in CRITERIA_BY_TYPE[kind]}, qualifications=['explicit_synthetic_test']))
        grade = grade_context_evidence(dict(version=INPUT_VERSION, assertion_ref=assertion,
            target_context_ref=context, target_identity={'status': 'supported', 'support_refs': [source]},
            grader_type=kind, observations=observations))
        rows.append(dict(sheet_ref=identity('source', kind), assertion_ref=assertion,
            target_context_ref=context, grader_type=kind, **grade['cells']['evidence_amount']))
    main = aggregate_a108(dict(assertion_ref=assertion, target_context_ref=context,
        contributions=[{'sheet_ref': row['sheet_ref'], 'component': 'evidence_amount'} for row in rows]), rows)
    cell = main['cells']['overall']
    assert cell['evidence_amount'] == 3 and cell['net_support'] == 1
    assert context_scalar(cell)['value'] == .25
    assert main['annotation_credit'] is None


def test_nine_axis_composition_uses_each_native_mapping_and_keeps_opposition():
    from gene_annotation_episode.literature_a105_aggregation import aggregate_a105
    from gene_annotation_episode.literature_partner_calculations import populate_partner_components
    from test_literature_a105_aggregation_325 import pure_inputs
    from test_literature_partner_calculations import _inputs
    from test_literature_reaction_calculations import calculate, ratio, budget
    args, rows = pure_inputs((1, 2))
    partner = populate_partner_components(_inputs())['cells']
    chemical = calculate(ratio(), budget())['cells']
    scalars = [correspondence_scalar(axis, value, measured=True)
        for axis, value in zip(AXES[:4], (.2, .3, .4, .5))]
    scalars.extend((a105_scalar(aggregate_a105(args, rows)['cells']['overall']),
        a106_scalar(dict(component='experimental_subscore', value=-2,
            unit='natural_log_ratio', status='complete')),
        partner_requirement_scalar([dict(component=name, **cell) for name, cell in partner.items()]),
        context_scalar(context_cell(['physiology'], ['contradiction', 'other'])),
        chemical_constraint_scalar([dict(component=name, **cell) for name, cell in chemical.items()],
            required=('reaction_comparison', 'resource_comparison'))))
    view = combine_scalars(scalars)
    assert set(view['axis_components']) == set(AXES)
    assert not view['unknown_axes']
    assert view['axis_components']['A106'] < 0 and view['axis_components']['A108'] < 0
    support = math.prod(1 + row['value'] for row in scalars if row['value'] > 0) - 1
    opposition = math.prod(1 - row['value'] for row in scalars if row['value'] < 0) - 1
    assert view['support'] == pytest.approx(support)
    assert view['opposition'] == pytest.approx(opposition)
    assert view['credit'] == pytest.approx(support - opposition)


@pytest.mark.parametrize('w,o,a,sign', [(100, 20, 90, 1), (100, 200, 150, -1), (100, 100, 100, 0)])
def test_partner_mapping_uses_real_calculated_omission_and_restoration_contrasts(w, o, a, sign):
    from gene_annotation_episode.literature_partner_calculations import populate_partner_components
    from test_literature_partner_calculations import _inputs
    native = populate_partner_components(_inputs(w, o, a))
    cells = [dict(component=name, **cell) for name, cell in native['cells'].items()]
    original = deepcopy(cells)
    scalar = partner_requirement_scalar(cells)
    assert scalar['value'] is not None
    assert (scalar['value'] > 0) - (scalar['value'] < 0) == sign
    assert cells == original
    unresolved = require_attribution(scalar, missing=['target_correspondence_unestablished'])
    assert unresolved['value'] is None
    assert unresolved['native_inputs'] == scalar['native_inputs']


def test_unknown_necessary_test_cannot_make_positive_support_but_actual_counterexample_is_retained():
    positive = prerequisite_scalar('A110', {'reaction_comparison': .6},
        required=('reaction_comparison', 'resource_comparison'))
    negative = prerequisite_scalar('A110', {'reaction_comparison': -.6},
        required=('reaction_comparison', 'resource_comparison'))
    assert positive['value'] is None
    assert negative['value'] == -.6 and negative['status'] == 'partial'
    assert negative['missing_inputs'] == ['resource_comparison']
    assert require_attribution(negative, missing=['molecule_identity_unknown'])['value'] is None


def test_chemical_mapper_preserves_signed_native_comparisons_without_scaling_physical_units():
    cells = [dict(component='reaction_comparison', value=-.25, unit='dimensionless', status='populated'),
        dict(component='resource_comparison', value=.4, unit='dimensionless', status='populated')]
    assert chemical_constraint_scalar(cells, required=tuple(row['component'] for row in cells))['value'] == -.25
    with pytest.raises(ValueError, match='existing_chemical_comparison_required'):
        chemical_constraint_scalar([], required=('resource_capacity',))


def test_root_rejects_duplicate_axis_packets_and_nonfinite_inputs():
    row = correspondence_scalar('A101', .5, measured=True)
    with pytest.raises(ValueError, match='unique_versioned_axes_required'):
        combine_scalars([row, row])
    for value in (True, float('nan'), float('inf'), -1.01, 1.01):
        with pytest.raises(ValueError, match='outside_unit_interval'):
            signed_offset_volume({'A105': value})
