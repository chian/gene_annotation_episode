"""Synthetic typed values, not observations about the fixed gene or new assays.

Threshold examples come from the reviewed censored-efficiency/ratio/IscR cases.
The source below is explicitly synthetic; no retained corpus or run is modified.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.credit import CreditPolicy, project_credit
from gene_annotation_episode.evidence_geometry import _metric
from gene_annotation_episode.domain import ATOM, ContractError, REASONING_SCHEMA, canonical, validate_schema
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, project_finding_progress
from gene_annotation_episode.runtime import _action_generation_schema, _decode_action_response
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


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
        'start': 0, 'end': len(text.encode()), 'quote': text}
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


def test_bound_thresholds_round_trip_without_defaults_through_real_consumers(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        source, anchor = source_fixture(store)
        data = empty_commit()
        for alias, label in [('efficiency_unit', 'M^-1 s^-1'), ('nM', 'nM')]:
            data['terms'].append({'alias': alias, 'label': label, 'term_type': 'unit',
                'source_ref': source['id'], 'anchor': anchor})
        examples = [numeric(10, 'less_than', '@efficiency_unit'), numeric(37000, 'greater_than'),
            numeric(26000, 'greater_than'), numeric(1000, 'greater_than', '@nM'),
            numeric(10, 'less_or_equal'), numeric(26000, 'greater_or_equal'), numeric(10)]
        # Explicit approximation and uncertainty coexist only as reported;
        # this synthetic example tests preservation, not interval arithmetic.
        examples[4].update(qualifier='approximate', uncertainty={
            'representation': 'plus_minus', 'magnitude': 1, 'statistic': 'unspecified'})
        data['contexts'] = [{'alias': 'bounded_context', 'context_type': 'assay_condition',
            'name': 'ConstructX', 'source_ref': source['id'], 'anchor': anchor,
            'attributes': [{'name': 'concentration', 'value': numeric(1000, 'greater_than', '@nM')}],
            'related_refs': [target]}]
        data['hypotheses'] = [{'alias': 'bounded_question', 'subject_refs': [target],
            'predicate': 'binds', 'value': numeric(1000, 'greater_than', '@nM'),
            'context_refs': ['@bounded_context']}]
        for index, value in enumerate(examples):
            data['observations'].append({'alias': 'o'+str(index), 'subject_refs': [target],
                'source_subject_refs': [target], 'kind': 'assay_report', 'source_ref': source['id'],
                'measurements': [{'name': 'activity', 'value': value}],
                'dependencies': ['@bounded_context'], 'anchor': anchor})
        host = store.reasoning_schema()
        transport = _action_generation_schema(host)
        wire = deepcopy(data)
        for row in wire['observations']:
            value = row['measurements'][0]['value']
            for key in ['bound', 'qualifier', 'uncertainty']:
                value.setdefault(key, None)
            row.update(visual_anchor=None, operand_intervals=None)
        # Validate the actual numeric transport branch. The full reasoning
        # schema also has unrelated optional row fields outside this fixture.
        numeric_wire = transport['properties']['observations']['items']['properties']['measurements']['items']['properties']['value']
        assert all(Draft202012Validator(numeric_wire).is_valid(row['measurements'][0]['value'])
            for row in wire['observations'])
        decoded = _decode_action_response(wire, host)
        assert decoded == data
        committed = store.commit_reasoning(decoded, {'subject_refs': [target]}, 'synthetic-bounds')
        assert committed['status'] == 'completed', committed
        refs = [committed['aliases']['o'+str(index)] for index in range(len(examples))]
        expected = deepcopy(examples)
        expected[0]['unit_ref'] = committed['aliases']['efficiency_unit']
        expected[3]['unit_ref'] = committed['aliases']['nM']
        assert [store.get(ref)['measurements'][0]['value'] for ref in refs] == expected
        context = store.get(committed['aliases']['bounded_context'])
        question = store.get(committed['aliases']['bounded_question'])
        assert context['attributes'][0]['value'] == question['value'] == expected[3]
        assert store.commit_reasoning(decoded, {'subject_refs': [target]}, 'synthetic-bounds') == committed
        tools = ToolRegistry(store)
        queried = tools.execute('state.query', {'refs': refs}, operation_key='synthetic-bounds-query')
        assert queried['status'] == 'completed'
        assert [row['measurements'][0]['value'] for row in queried['result']['records']] == expected
        viewed = {row['id']: row for row in store.reasoning_view()['observations']}
        assert [viewed[ref]['measurements'][0]['value'] for ref in refs] == expected
        output = export_annotation(store, tmp_path/'bounds.json', include_artifacts=True)
        exported = {row['id']: row for row in json.loads(Path(output['json']['path']).read_text())['records']}
        assert [exported[ref]['measurements'][0]['value'] for ref in refs] == expected
        old = store.get(refs[-1])
        assert 'bound' not in old['measurements'][0]['value']
        assert project_credit(store).credit == 0
    with Store(tmp_path/'state') as reopened:
        assert reopened.get(refs[-1]) == old
        assert [reopened.get(ref)['measurements'][0]['value'] for ref in refs] == expected


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
def test_bounded_extent_is_unavailable_while_other_support_and_received_progress_survive(tmp_path, metric, extent):
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
        store.put('annotation', record, origin='reasoning', scope=scope)
        scorer = AnnotationSupportScore(CreditPolicy())
        projected = scorer.read_details(store, scope, details_limit=20, details_offset=0)
        assert projected['axis_components']['empirical'] == 1
        assert projected['axis_components']['comparative'] == 0
        unavailable, = projected['inactive_dependencies']
        assert unavailable['reason'] == 'bounded_measurement_cannot_supply_exact_extent'
        assert unavailable['assessment_ref'] == limited['id']
        assert unavailable['observation_ref'] == bad['id']
        assert unavailable['field_path'] == ['measurements', 0, 'value']
        assert unavailable['measurement_name'] == metric and unavailable['measurement_value'] == threshold
        assert scorer(store, scope).credit == projected['credit'] > 0
        progress = project_finding_progress(store, scope, FindingProgressPolicy(1),
            known_assessment_refs=[retained['id'], limited['id']], details_limit=10)
        assert progress['retained_finding_count'] == 2 and progress['credit'] == 2
        assert ToolRegistry(store).execute('state.query', {'refs': [bad['id'], limited['id']]})['status'] == 'completed'
        actions = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        assert scorer.read_details(store, scope, details_limit=20, details_offset=0) == projected
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
