"""A108 observation union and contextual scalar checks."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import annotation_scalar as context_scalar

def context_cell(support=(), conflict=(), unresolved=()):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_grading import count_sets
    sets = dict(support=list(support), conflict=list(conflict), unresolved=list(unresolved))
    return dict(component='overall', status='complete', observation_sets=sets, **count_sets(sets))

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
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_grading import INPUT_VERSION, CRITERIA_BY_TYPE, grade_context_evidence
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import aggregate_a108
    assertion, context = (identity('hypothesis', 'synthetic-root-context'), identity('context', 'synthetic-organism'))
    source, subject = (identity('source', 'synthetic-physiology'), identity('reference', 'synthetic-organism'))
    rows = []
    for kind in ('physiology_resource_response', 'substrate_availability'):
        observations = []
        for index, relation in enumerate(('support', 'support', 'conflict')):
            observations.append(dict(original_observation_key=str(index), original_observation_ref=identity('reference', index), context_claim_ref=assertion, source_subject_ref=subject, source_context_ref=context, source_refs=[source], measurement_keys=[str(index)], origin='organism_physiology_report', target_relationship='direct', relation=relation, criteria={key: {'status': 'supported', 'support_refs': [source]} for key in CRITERIA_BY_TYPE[kind]}, qualifications=['explicit_synthetic_test']))
        grade = grade_context_evidence(dict(version=INPUT_VERSION, assertion_ref=assertion, target_context_ref=context, target_identity={'status': 'supported', 'support_refs': [source]}, grader_type=kind, observations=observations))
        rows.append(dict(sheet_ref=identity('source', kind), assertion_ref=assertion, target_context_ref=context, grader_type=kind, **grade['cells']['evidence_amount']))
    main = aggregate_a108(dict(assertion_ref=assertion, target_context_ref=context, contributions=[{'sheet_ref': row['sheet_ref'], 'component': 'evidence_amount'} for row in rows]), rows)
    cell = main['cells']['overall']
    assert cell['evidence_amount'] == 3 and cell['net_support'] == 1
    assert context_scalar(cell)['value'] == 0.25
    assert main['annotation_credit'] is None
