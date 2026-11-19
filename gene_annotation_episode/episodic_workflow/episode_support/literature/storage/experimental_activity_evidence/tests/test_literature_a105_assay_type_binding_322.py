"""A105 delivery of existing numerical reports; synthetic engineering fixtures."""
from dataclasses import replace
import json
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_worksheet import VERSION, a105_worksheet_template, validate_a105_worksheet_links
from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence.literature_worksheet_render import render_a105_worksheet
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_completion_time_storage import LiteratureCompletionTimeRepository, completion_time_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_product_partition_storage import LiteratureProductPartitionRepository, product_partition_cells_schema
from .unit_world import held, in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_a105_partition_time_joined_149 import synthetic_inputs, RAW_NUMBERS

from copy import deepcopy
from functools import partial
import asyncio
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS, CRITERIA_BY_TYPE, ROLES
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import LiteratureAssayGradingRepository, assay_grading_cells_schema, REQUESTED, NAMESPACE
from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress

def grading_fixture(store, ctx, assay_type='endpoint_conversion'):
    quantity_kind = dict(activity_rate='rate_ratio', endpoint_conversion='conversion_fraction', product_distribution='product_fraction', reaction_coupling='productive_fraction')[assay_type]
    unit = 'dimensionless' if assay_type == 'activity_rate' else 'fraction'
    lines = ['Experiment A: synthetic assay for one reference molecule. Scientific applicability and a known normal fixed-prediction model are explicitly stipulated for this synthetic fixture.', f'effect 0.8 {unit}; variance 0.04 {unit}_squared;', 'recovery 0.9 fraction; attributed 0.6 fraction; total 0.8 fraction;', 'condition test 0.8 fraction; condition reference 1 fraction;', f'assertion prediction 1 {unit}; alternative prediction 0 {unit}.', f'Experiment B: effect 0.2 {unit}; variance 0.09 {unit}_squared.']
    text = '\n'.join(lines)
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_assay_grading_322', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    quote = lines[0]
    support = store.put('reference', {'reference_type': 'assay', 'source_ref': source, 'accession': 'synthetic_assay_322', 'label': 'Experiment A', 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [], 'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0, 'end': len(quote), 'quote': quote}}, origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'reaction322', 'label': 'Synthetic reaction', 'term_type': 'reaction', 'source_ref': source, 'anchor': None}, origin='caller')['id']
    assertion = store.put('hypothesis', {'subject_refs': [support], 'predicate': 'catalyzes', 'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []}, origin='reasoning')['id']

    def witness(quote, start=0):
        offset = text.index(quote, start)
        return {'source_ref': source, 'representation': 'original', 'start': offset, 'end': offset + len(quote), 'quote': quote}

    def number(label, token, native_unit):
        fragment = label + ' ' + token + ' ' + native_unit
        start = text.index(fragment)
        return {'kind': 'source_number', 'number': {'witness': witness(fragment), 'number_start': len(label) + 1, 'number_end': len(label) + 1 + len(token)}, 'unit': witness(native_unit, start + len(label) + 1 + len(token) + 1), 'origin': 'synthetic'}
    args = {'source_ref': source, 'source_kind': 'synthetic_fixture', 'assay_type': assay_type, 'assertion_ref': assertion, 'experiment_ref': support, 'quantity_kind': quantity_kind, 'interpretations': {name: {'status': 'supported', 'support_refs': [support]} for name in CRITERIA_BY_TYPE[assay_type]}, 'prediction_model': {'kind': 'fixed_predictions_known_normal', 'variance_interpretation': 'known', 'support_refs': [support]}, 'quantities': {'effect': number('effect', '0.8', unit), 'effect_variance': number('variance', '0.04', unit + '_squared'), 'recovery': number('recovery', '0.9', 'fraction'), 'attributed_signal': number('attributed', '0.6', 'fraction'), 'total_signal': number('total', '0.8', 'fraction'), 'condition_test': number('condition test', '0.8', 'fraction'), 'condition_reference': number('condition reference', '1', 'fraction'), 'assertion_prediction': number('assertion prediction', '1', unit), 'alternative_prediction': number('alternative prediction', '0', unit)}}
    refs = [source, support, assertion]
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature', (('literature', 'child'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'version': 'literature_assignment_v1', 'question_context_refs': [support, assertion], 'source_refs': [source], REQUESTED: list(COMPONENTS)}, {}, refs)
    return (context, args, artifact)

@pytest.mark.parametrize('assay_type', ['activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling'])
@in_unit
def test_four_assay_types_persist_same_numerical_dimensions_and_partial_inputs(store, ctx, assay_type):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    context, args, _ = grading_fixture(store, ctx, assay_type)
    repo = LiteratureAssayGradingRepository(store)
    outcome = repo.populate(context.scope, None, args, 'selected-grading', list(COMPONENTS))
    rows = outcome['result']['cells']
    validate_schema(rows, assay_grading_cells_schema())
    by_name = {r['component']: r for r in rows}
    assert by_name['measured_effect']['value'] == 0.8
    assert by_name['effect_precision']['value'] == 25
    assert by_name['recovery_deviation']['value'] == pytest.approx(-0.1)
    assert by_name['attributed_fraction']['value'] == pytest.approx(0.75)
    assert by_name['condition_response']['value'] == 0.8
    assert by_name['source_log_evidence_ratio']['value'] == pytest.approx(7.5)
    assert by_name['source_log_evidence_ratio']['status'] == 'conditional'
    assert by_name['source_log_evidence_ratio']['input_origins'] == ['synthetic']
    assert not held(store, 'observation') and (not held(store, 'assessment'))
    partial = deepcopy(args)
    partial['quantities']['effect_variance'] = None
    partial['interpretations']['attribution_supported'] = {'status': 'unknown', 'support_refs': []}
    result = repo.populate(context.scope, None, partial, 'selected-partial', list(COMPONENTS))
    partial_rows = {r['component']: r for r in result['result']['cells']}
    assert partial_rows['measured_effect']['value'] == 0.8
    assert partial_rows['source_log_evidence_ratio']['value'] is None
    assert 'attribution_supported_unknown' in partial_rows['source_log_evidence_ratio']['reasons']
    assert partial_rows['attributed_fraction']['value'] is None

@in_unit
def test_measured_only_grade_does_not_expand_other_interpretations(store, ctx):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    context, args, _ = grading_fixture(store, ctx)
    repo = LiteratureAssayGradingRepository(store)
    outcome = repo.populate(context.scope, None, args, 'selected', ['measured_effect'])
    row, = outcome['result']['cells']
    assert row['component'] == 'measured_effect'
    assert row['interpretations'] == {} and row['prediction_model'] is None
    assert row['source_refs'] == [args['source_ref']]


@in_unit
def test_grade_render_uses_context_from_all_delivered_cells_and_no_private_context(store, ctx):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import CRITERION_QUESTIONS
    from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence.literature_assay_grading_render import render_received
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    context, args, _ = grading_fixture(store, ctx)
    repo = LiteratureAssayGradingRepository(store)
    outcome = repo.populate(context.scope, None, args, 'render-grade', list(COMPONENTS))
    ref = outcome['result']['sheet_ref']

    def rendered(components):
        parts = []
        rows = repo.project_cells(ref, components)
        render_received(parts, rows, section=lambda out, title, body: out.extend((title, body)), table=lambda headers, rows: '\n'.join((' | '.join(map(str, row)) for row in [headers, *rows])))
        return '\n'.join(parts)
    combined = rendered(['measured_effect', 'source_log_evidence_ratio'])
    assert CRITERION_QUESTIONS['attribution_supported'] in combined
    assert 'fixed_predictions_known_normal' in combined
    assert '7.5' in combined
    measured = rendered(['measured_effect'])
    assert CRITERION_QUESTIONS['attribution_supported'] not in measured
    assert 'fixed_predictions_known_normal' not in measured
    assert ref not in combined and args['assertion_ref'] not in combined
