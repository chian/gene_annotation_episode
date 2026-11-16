"""Synthetic typed values, not observations about the fixed gene or new assays.

Threshold examples come from the reviewed censored-efficiency/ratio/IscR cases.
The source below is explicitly synthetic; no retained corpus or run is modified.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.evidence_geometry import _metric, _observation_extents
from gene_annotation_episode.domain import ATOM, ContractError, REASONING_SCHEMA, canonical, validate_schema
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.investigation_progress import FindingProgressPolicy, project_finding_progress
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


BOUNDS = ['less_than', 'less_or_equal', 'greater_than', 'greater_or_equal']


def empty_commit():
    return {key: [] for key in REASONING_SCHEMA['properties']}


def source_fixture(store):
    text = ('SYNTHETIC representation fixture, not a new biological result: '
        'ConstructX efficiency <10 M^-1 s^-1, ratio >37000, ratio >26000, '
        'IC50 >1000 nM. Synthetic threshold-control <=10 and >=26000.')
    artifact = store.artifact(text)
    source = store.put('source', {'provider': 'synthetic_numeric_bounds',
        'accession': 'fixture', 'uri': None, 'artifact_ref': artifact,
        'text_ref': artifact, 'request_ref': None, 'version': 'fixture',
        'retrieved_at': None}, origin='external')
    anchor = {'source_ref': source['id'], 'artifact_ref': artifact,
        'start': 0, 'end': len(text.encode())}
    return source, anchor


def numeric(value, bound=None, unit=None):
    return {'type': 'number', 'value': value, 'unit_ref': unit,
        **({'bound': bound} if bound is not None else {})}


def finding(subject, value):
    return {'source_claim': {'subject_refs': [subject], 'predicate': 'binds',
        'value': deepcopy(value), 'context_refs': []},
        'qualification': {'kind': 'none', 'context_refs': [], 'assumption_refs': []},
        'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
        'same_source_claim_as_ref': None, 'replaces_refs': []}


def assessment(hypothesis, observation, *, extent='observed_extent'):
    return {'hypothesis_ref': hypothesis, 'observation_ref': observation,
        'relation': 'strengthens', 'applicability': 'transfer' if extent == 'inferred_extent' else 'direct',
        'extent_basis': extent, 'condition_refs': [], 'assumption_refs': [],
        'expected_revision': 0}


def annotation(target, hypothesis, assessments):
    return {'subject_ref': target, 'footprint_kind': 'localized',
        'coherent_sets': [{'interpretations': [{'hypothesis_ref': hypothesis,
            'disposition': 'supported', 'assessment_refs': assessments}], 'context_refs': []}],
        'alternative_refs': [], 'resolution': 'selected', 'expected_revision': 0}


@pytest.mark.parametrize('bound', ['<', '<=', '>', '>=', 'equal', 'unknown', '', 1, True, None])
def test_unknown_or_explicit_null_bound_is_rejected_and_other_commit_rows_survive(tmp_path, bound):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        source, anchor = source_fixture(store)
        data = empty_commit()
        for alias, value in [('bad', {**numeric(10), 'bound': bound}), ('good', numeric(10))]:
            data['observations'].append({'alias': alias, 'subject_refs': [target],
                'source_subject_refs': [target], 'kind': 'assay_report', 'source_ref': source['id'],
                'measurements': [{'name': 'activity', 'value': value}], 'dependencies': [], 'anchor': anchor})
        result = store.commit_reasoning(data, {'subject_refs': [target]}, 'synthetic-invalid-bound')
        assert result['status'] == 'partial'
        assert set(result['aliases']) == {'good'}
        assert result['errors'] == [{'section': 'observations', 'row_index': 0,
            'code': 'representation_error', 'field_path': ['measurements', 0, 'value'], 'schema_keyword': 'anyOf'}]
        assert store.get(result['aliases']['good'])['measurements'][0]['value'] == numeric(10)


@pytest.mark.parametrize('metric,extent', [
    ('query_coverage', 'observed_extent'), ('target_coverage', 'observed_extent'),
    ('query_start', 'observed_extent'), ('query_end', 'observed_extent'),
    ('query_coverage', 'inferred_extent'), ('query_start', 'inferred_extent'),
    ('query_coverage', 'context_allocation')])
def test_bounded_extent_is_unavailable_while_findings_and_received_progress_survive(tmp_path, metric, extent):
    with Store(tmp_path/'state') as store:
        Journal(store, 'synthetic-numeric-projection-check')
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        source, anchor = source_fixture(store)
        hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'binds',
            'value': {'type': 'enum', 'value': 'unknown'}, 'context_refs': []}, origin='reasoning')['id']
        good = store.put('observation', {'subject_refs': [target], 'source_subject_refs': [target],
            'kind': 'assay_report', 'source_ref': source['id'], 'anchor': anchor,
            'measurements': [{'name': 'activity', 'value': numeric(10, 'less_than')}], 'dependencies': []}, origin='extracted')
        threshold = numeric(.4 if 'coverage' in metric else 2, 'less_than')
        body = {'subject_refs': [target], 'source_subject_refs': [target],
            'kind': 'comparison', 'source_ref': source['id'], 'anchor': None,
            'measurements': [{'name': metric, 'value': threshold}], 'dependencies': []}
        if metric == 'target_coverage':
            body['operand_intervals'] = [{'role': 'reference', 'subject_ref': target,
                'start': 0, 'end': 5, 'unit': 'aa'}]
        bad = store.put('observation', body, origin='tool')
        with pytest.raises(ContractError, match='bounded_measurement_cannot_supply_exact_extent') as error:
            _metric(bad, metric)
        assert error.value.detail['measurement_value'] == threshold
        first = assessment(hypothesis, good['id'])
        first['investigation_finding'] = finding(target, numeric(10, 'less_than'))
        retained = store.put('assessment', first, origin='reasoning', scope=scope)
        limited = assessment(hypothesis, bad['id'], extent=extent)
        limited['investigation_finding'] = finding(target, threshold)
        if extent == 'inferred_extent':
            limited['target_footprint'] = [{'target_ref': target, 'start': 0, 'end': 10, 'unit': 'aa'}]
        if extent == 'context_allocation':
            limited.update(context_account_scope=scope, context_scope=scope)
        # Real commit boundary: both valid findings survive. Censored geometry
        # is unavailable for annotation arithmetic, not invalid science.
        data = empty_commit()
        data['assessments'] = [{'alias': 'limited', **limited}]
        result = store.commit_reasoning(data, scope, 'retain-bounded-finding')
        assert result['status'] == 'completed', result
        limited = store.get(result['aliases']['limited'])
        record = annotation(target, hypothesis, [retained['id'], limited['id']])
        if extent == 'context_allocation':
            record.update(footprint_kind='whole_input_context', context_account_scope=scope, context_scope=scope)
        saved_annotation = store.put('annotation', record, origin='reasoning', scope=scope)
        # Exercise the actual downstream geometry consumer without reviving
        # the retired category-to-score mapping. The retained source threshold
        # is not an exact interval or fractional coverage operand.
        with pytest.raises(ContractError, match='bounded_measurement_cannot_supply_exact_extent') as projection_error:
            _observation_extents(store, bad)
        assert projection_error.value.detail == {
            'observation_ref': bad['id'], 'measurement_name': metric,
            'field_path': ['measurements', 0, 'value'], 'measurement_value': threshold,
            'required_representation': 'unbounded_extent_operand',
            'meaning': 'bounded_measurement_retained_without_scalar_extent_projection'}
        expected_extent = [({target: [(0, 10)]}, 1., {'extent_mode': 'subject_footprint'})]
        assert _observation_extents(store, good) == expected_extent
        assert store.get(saved_annotation['id']) == saved_annotation
        progress = project_finding_progress(store, scope, FindingProgressPolicy(1),
            known_assessment_refs=[retained['id'], limited['id']], details_limit=10)
        assert progress['retained_finding_count'] == 2 and progress['credit'] == 2
        assert ToolRegistry(store, run_directory=store.path / 'tool-run').execute('state.query', {'refs': [bad['id'], limited['id']]})['status'] == 'completed'
        actions = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        with pytest.raises(ContractError, match='bounded_measurement_cannot_supply_exact_extent') as repeated_error:
            _observation_extents(store, bad)
        assert repeated_error.value.detail == projection_error.value.detail
        assert _observation_extents(store, good) == expected_extent
        assert project_finding_progress(store, scope, FindingProgressPolicy(1),
            known_assessment_refs=[retained['id'], limited['id']], details_limit=10) == progress
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == actions == 0


def test_numeric_bound_is_part_of_existing_typed_value_without_a_new_identity_formula():
    from gene_annotation_episode.scientific_findings import FindingIdentity
    normalizer = FindingIdentity(None)
    ordinary = numeric(10)
    for bound in BOUNDS:
        value = numeric(10, bound)
        validate_schema(value, ATOM)
        assert normalizer.value(value) == value
        assert canonical(value) != canonical(ordinary)
