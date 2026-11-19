"""Library scenarios of the perturbation storage family, each run inside one tool unit of the library probe
episode: every function receives the unit's context and works only through ``ctx.store``, the custody-scoped store,
with real records, real repositories and real work tables. A failed assertion fails the unit and so the run."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import (
    ReportBoundaryError, validate_closed_schema, validate_form)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_storage import (
    LiteraturePerturbationRepository, perturbation_cells_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_summary_storage import (
    LiteraturePerturbationSummaryProjection, perturbation_summary_cells_schema)
from .library_data import REQUIRED, SUPPORT, basis, data_for, data_with_basis
from .perturbation_case_fixtures import returned_form, setup_case
from .perturbation_summary_fixtures import fixture as summary_fixture, source


def identify(store, context, args, name='experiment-one'):
    record = store.put('reference', {'reference_type': 'assay', 'source_ref': args['source_ref'],
        'accession': name, 'label': name, 'sequence_ref': None, 'molecule': None,
        'length': None, 'term_refs': [], 'context_refs': []}, origin='caller')
    args = deepcopy(args)
    args['experiment_assessment'] = {'experiment_ref': record['id'],
        'experiment_type': 'intervention_response', 'assessment_key': 'intervention-contribution',
        'scientific_question': 'Does the intervention alter the measured outcome?',
        'conclusion': 'The endpoint changes under the selected intervention.',
        'limitations': ['Joint uncertainty of the source index remains unreported.'],
        'revises_sheet_ref': None, 'revision_reason': None}
    context = replace(context, received_record_refs=(*context.received_record_refs, record['id']))
    return context, args


def multiple_experiments(ctx, summary):
    """Revisions, a second experiment, the parent's typed receipt of numbers, and the saved sheets read again."""
    store, context, args = (summary_fixture if summary else setup_case)(ctx)
    repo = LiteraturePerturbationRepository(store, context.run_id)
    context, args = identify(store, context, args)
    original = repo.populate(context, args, 'original')
    assert original['status'] == 'completed', original
    first = original['result']['sheet_ref']
    context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *original['record_refs']))))
    revision = deepcopy(args)
    revision['experiment_assessment'].update(revises_sheet_ref=first,
        revision_reason='Restrict the conclusion to the experimentally measured endpoint.',
        conclusion='The measured endpoint changes; a direct catalytic function is not established.')
    revised = repo.populate(context, revision, 'revision')
    assert revised['status'] == 'completed', revised
    second = revised['result']['sheet_ref']
    assert first != second
    assert original['result']['cells'] == revised['result']['cells']
    context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *revised['record_refs']))))
    other_context, other_args = identify(store, context, args, 'experiment-two')
    other = repo.populate(other_context, other_args, 'second-experiment')
    heads = repo.current_assessments()
    assert len(heads) == 2
    assert {row['sheet_ref'] for row in heads} == {second, other['result']['sheet_ref']}
    assert len({row['experiment_ref'] for row in heads}) == 2
    assert [row['sheet_ref'] for row in repo.assessment_history(second)] == [first, second]
    produced = (repo.summary_projection() if summary else repo).produced_sheet_refs(context)
    assert sorted(produced) == sorted([first, second, other['result']['sheet_ref']])

    schema = obj({'measurements': (perturbation_summary_cells_schema if summary else perturbation_cells_schema)()})
    projection = repo.summary_projection() if summary else repo
    requested = context.assignment['requested_perturbation_summary_components' if summary else 'requested_perturbation_components']
    form = returned_form(projection, context, [second], schema, requested)
    rows = form['measurements']
    assert rows and any(row['value'] is not None for row in rows)
    assert all(row['experiment_ref'] == args['experiment_assessment']['experiment_ref'] for row in rows)
    parent = replace(context, episode_id='parent', role='annotation', assignment={}, path=(('annotation', 'root'),))
    projection.receive_cells(parent, rows, 'assessment-delivery')
    assert projection.received_cells(parent) == rows

    saved = [repo.read(ref) for ref in (first, second, other['result']['sheet_ref'])]
    assert repo.current_assessments() == heads
    assert len(repo.assessment_history(second)) == 2
    assert projection.received_cells(parent) == rows
    assert [repo.read(ref) for ref in (first, second, other['result']['sheet_ref'])] == saved
    assert not store.list('observation') and not store.list('assessment')
    return {'sheets': 3, 'received_rows': len(rows)}


def duplicate_and_stale_revision(ctx):
    """A second report of one experiment, and a stale correction, are refused; one current assessment remains."""
    store, context, args = setup_case(ctx)
    context, args = identify(store, context, args)
    repo = LiteraturePerturbationRepository(store, context.run_id)
    first = repo.populate(context, args, 'one')
    context = replace(context, received_record_refs=(*context.received_record_refs, *first['record_refs']))
    with pytest.raises(ContractError, match='revision_required'):
        repo.populate(context, args, 'duplicate-report')
    revision = deepcopy(args)
    revision['experiment_assessment'].update(revises_sheet_ref=first['result']['sheet_ref'], revision_reason='Correction')
    repo.populate(context, revision, 'two')
    with pytest.raises(ContractError, match='revision_required'):
        repo.populate(context, revision, 'stale-correction')
    assert len(repo.current_assessments()) == 1
    assert len(repo.produced_sheet_refs(context)) == 2
    return {'current': 1}


def revise_other_experiment(ctx):
    """An unreceived experiment identity and a predecessor of another experiment are refused."""
    store, context, args = setup_case(ctx)
    received, args = identify(store, context, args)
    repo = LiteraturePerturbationRepository(store, context.run_id)
    with pytest.raises(ContractError, match='experiment_not_received'):
        repo.populate(context, args, 'unreceived')
    first = repo.populate(received, args, 'one')
    received = replace(received, received_record_refs=(*received.received_record_refs, *first['record_refs']))
    other, other_args = identify(store, received, args, 'another-experiment')
    other_args['experiment_assessment'].update(revises_sheet_ref=first['result']['sheet_ref'], revision_reason='Wrong experiment')
    with pytest.raises(ContractError, match='predecessor_mismatch'):
        repo.populate(other, other_args, 'wrong')
    assert len(repo.current_assessments()) == 1
    return {'current': 1}


def covariance_fixture(ctx, kind='mean_covariance', basis_name='source_reported', *, names=None,
                       with_support=True, data=None):
    store, context, args = summary_fixture(ctx)
    data = data_for(kind, basis_name) if data is None else deepcopy(data)
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
        'requested_perturbation_summary_components': ['perturbation_mean_variance'] if names is None else names},
        received_record_refs=(*context.received_record_refs, *additions))
    return store, context, args


def selected(ctx, kind='mean_covariance', basis_name='source_reported', **kwargs):
    store, context, args = covariance_fixture(ctx, kind, basis_name, **kwargs)
    outcome = LiteraturePerturbationRepository(store, context.run_id).populate(context, args, 'covariance-selected')
    assert outcome['status'] == 'completed', outcome.get('feedback')
    context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    schema = obj({'measurements': perturbation_summary_cells_schema()})
    projection = LiteraturePerturbationSummaryProjection(store, context.run_id)
    form = returned_form(projection, context, [outcome['result']['sheet_ref']], schema,
                         context.assignment['requested_perturbation_summary_components'])
    return store, context, projection, outcome, schema, form


def covariance_receipt(ctx, kind, basis_name):
    """The same numbers keep distinct covariance meanings through the parent's receipt."""
    store, context, projection, outcome, schema, form = selected(ctx, kind, basis_name)
    row, = form['measurements']; qualifier, = row['covariance_interpretations']
    assert row['value'] == 2
    assert (qualifier['first'], qualifier['second']) == ('W', 'K')
    assert qualifier['kind'] == kind and qualifier['interpretation_basis'] == basis_name
    assert qualifier['use'] == 'used_selected_covariance'
    assert 'value' not in qualifier
    parent = replace(context, role='annotation', episode_id='covariance-parent', assignment={},
        path=(('annotation', 'root'),))
    projection.receive_cells(parent, form['measurements'], 'covariance-admission')
    assert projection.received_cells(parent) == form['measurements']
    return {'kind': kind}


def covariance_pairs(ctx):
    """Only the component-relevant pairs cross the exact original form; one admitted pair is forwarded."""
    data = data_for('uncorrelated', 'conditional_assumption', all_pairs=True)
    names = ['W_summary_value', 'perturbation_mean_variance', 'restoration_mean_variance', 'shared_contrast_covariance']
    store, context, projection, outcome, schema, form = selected(ctx, data=data, names=names)
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
    return {'pairs': 3}


def covariance_unavailable(ctx, unavailable):
    """An unknown or unavailable estimator is not presented as an applied covariance."""
    data = data_for('unknown' if unavailable == 'unknown_covariance' else 'uncorrelated',
                    'unresolved' if unavailable == 'unknown_covariance' else 'conditional_assumption')
    if unavailable == 'incompatible_estimator':
        data['measurements']['W']['summary_kind'] = 'median'
    names = ['perturbation_mean_variance', 'perturbation_variance_upper']
    store, context, projection, outcome, schema, form = selected(ctx, data=data, names=names, with_support=False)
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
    return {'unavailable': unavailable}


def basis_receipt(ctx):
    """The exact contributing roles and their qualification survive the typed receipt; defects are refused."""
    store, context, args = summary_fixture(ctx)
    data = source(store, canonical(data_with_basis()), parents=[args['source_ref']])
    args['data_source_ref'] = data['id']
    context = replace(context, assignment={**context.assignment,
        'source_refs': [*context.assignment['source_refs'], data['id']],
        'requested_perturbation_summary_components': REQUIRED},
        received_record_refs=(*context.received_record_refs, data['id']))
    projection = LiteraturePerturbationSummaryProjection(store, context.run_id)
    outcome = LiteraturePerturbationRepository(store, context.run_id).populate(context, args, 'basis-selected')
    assert outcome['status'] == 'completed', outcome.get('feedback')
    context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    sheet = outcome['result']['sheet_ref']
    rows = projection.project_cells([sheet], permitted_record_refs=context.received_record_refs, components=REQUIRED)
    expected = [('W',), ('W', 'K'), ('W', 'K'), ('K', 'R'), ('W', 'K', 'R'),
        ('A_reference', 'A_restored'), ('W', 'K', 'R', 'B_pert', 'B_rest'),
        ('W', 'K', 'R', 'A_reference', 'A_restored', 'B_pert', 'B_rest')]
    for row, roles in zip(rows, expected):
        assert tuple(row['statistical_interpretation_basis']) == roles
        assert all(item == basis(summary_scale='conditional_assumption')
            for item in row['statistical_interpretation_basis'].values())
    form_schema = obj({'measurements': perturbation_summary_cells_schema()})
    validate_closed_schema(form_schema)
    form = returned_form(projection, context, [sheet], form_schema, REQUIRED)
    assert form['measurements'] == rows
    with pytest.raises(ReportBoundaryError) as unavailable:
        validate_form(form, form_schema, lambda reference, namespace: False)
    assert unavailable.value.diagnostic['code'] == 'unknown_reference'
    parent = replace(context, episode_id='basis-parent', role='annotation', assignment={}, path=(('annotation', 'root'),))
    projection.receive_cells(parent, form['measurements'], 'basis-admission')
    assert projection.received_cells(parent) == rows
    for kind in ('omission', 'mutation', 'irrelevant_role'):
        bad = deepcopy(rows)
        if kind == 'omission':
            bad[0].pop('statistical_interpretation_basis')
        elif kind == 'mutation':
            bad[0]['statistical_interpretation_basis']['W']['summary_scale'] = 'source_reported'
        else:
            bad[0]['statistical_interpretation_basis']['K'] = basis()
        with pytest.raises(ContractError, match='differs_from_saved'):
            projection.validate_returned_values(bad, permitted_record_refs=context.received_record_refs)
        with pytest.raises(ContractError):
            projection.receive_cells(parent, bad, 'bad-' + kind)
    bad = deepcopy(rows)
    bad[0]['statistical_interpretation_basis']['K'] = basis()
    with pytest.raises(ContractError):
        validate_schema(bad, perturbation_summary_cells_schema())
    return {'rows': len(rows)}


SCENARIOS = {name: value for name, value in globals().items() if name in (
    'multiple_experiments', 'duplicate_and_stale_revision', 'revise_other_experiment', 'covariance_receipt',
    'covariance_pairs', 'covariance_unavailable', 'basis_receipt')}
