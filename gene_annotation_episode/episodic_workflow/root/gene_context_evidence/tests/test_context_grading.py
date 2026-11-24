"""The A103 grading of the head, run through the real runner on a real Store (``a103_world``).

The run is linked with the public API and stepped with ``EpisodeRun.next_decision`` and ``EpisodeRun.run_unit``: the
Episode is entered as ``run()`` enters it (its yield controller built from ``credit`` of the initial summary), each
unit is a real tool unit (journaled attempt, custody receipts of what it wrote, ``credit``, a controller step). The
A103 context operations run the library's native worker on the engineered genomes; ``context.grade`` writes the
attachment sheets; the finding is the controlled features code reads from them. No model is asked here."""
import asyncio
import json

from episode_runtime import ModelRequest, ToolCall
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.investigation_finding import (
    EVIDENCE_TYPE_VALUES)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.attachments import (
    ATTACHMENTS, received_attachments)

from .. import task
from ..episode import GeneContextEvidence
from ..messages import final_to_parent, internal_summary
from .a103_world import TARGET, linked, world  # noqa: F401

EPISODE = GeneContextEvidence


def step(run, call):
    return asyncio.run(run.run_unit(call))


def through_the_lookups(run):
    """The two lookups the head's ``decide`` makes first, run as the units it names."""
    for expected in ('process_library', 'tool_catalog'):
        decision = asyncio.run(run.next_decision())
        assert isinstance(decision, ToolCall) and decision.name == expected
        assert step(run, decision)['outcome'] is not None


def operation(run, scope, name, operands):
    entry = next(row for row in internal_summary.internal_summary(run.view)['catalog'] if row['name'] == name)
    outcome = step(run, ToolCall('operation', {'name': name, 'operands': operands, 'scope': scope,
                                               'input_schema': entry['input_schema']}))['outcome']
    assert outcome['status'] == 'completed', outcome
    return outcome['result']


def test_the_first_model_decision_offers_the_grader_with_its_instructions(tmp_path):
    held = world(tmp_path)
    run = linked(held, 'a103-first')
    through_the_lookups(run)
    view = run.view
    assert isinstance(view.controller_state, BoundedQualityYieldController) or view.controller_state is not None
    assert view.controller_state.stop is False and view.controller_state.current_credit == 0.0
    summary = internal_summary.internal_summary(view)
    assert EPISODE.credit(summary, view.records) == 0.0
    assert summary['ungraded_measurement_refs'] == [] and summary['finding']['attachments'] == []
    assert summary['finding']['attribution_state'] == 'no_received_context_association'
    assert {row['name'] for row in summary['catalog']} >= {'context.bind_locus', 'context.compare_neighborhoods'}
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    assert task.GRADING_SECTION in request.instructions
    assert "use the grading sheet's existing criteria and status" in request.instructions.lower()
    assert 'context.grade' in request.output_schema['properties']['operation']['enum']
    assert 'report' not in request.output_schema['properties']['operation']['enum']
    assert 'Current A103 grading sheets' in request.context['task']
    held['store'].close()


def measured_world(held, run):
    """Bind both genomes, measure both neighborhoods and compare them (the library's own engineered panel)."""
    scope, target = held['assignment']['scope'], held['target']
    bindings = [operation(run, scope, 'context.bind_locus', {
        'target_ref': target, 'file_source_ref': genome, 'accession': accession, 'format': 'genbank',
        'sequence_source_ref': None, 'genetic_code': None, 'selector': {'locus_tag': 'anchor'}})['binding_ref']
        for genome, accession in ((held['genome_a'], 'A.1'), (held['genome_b'], 'B.1'))]
    neighborhoods = [operation(run, scope, 'reference.neighborhood', {'binding_ref': binding, 'left_bp': 100,
                                                                      'right_bp': 200}) for binding in bindings]
    return operation(run, scope, 'context.compare_neighborhoods', {
        'target_ref': target, 'partner_reference_ref': neighborhoods[0]['cds'][1]['protein_reference_ref'],
        'definition_source_refs': [held['definition']],
        'rows': [{'neighborhood_ref': row['neighborhood_ref'], 'left_feature_index': 0, 'right_feature_index': 1,
                  'sampling_group': group, 'right_detection_ref': None}
                 for row, group in zip(neighborhoods, ('groupA', 'groupB'))],
        'definition': {'maximum_gap_bp': 20, 'maximum_intervening_genes': 0, 'orientation': 'same',
                       'order': 'left_before_right'}})


def test_measurements_are_graded_into_sheets_and_the_return_is_their_controlled_features(tmp_path):
    held = world(tmp_path)
    run = linked(held, 'a103-grade')
    through_the_lookups(run)
    comparison = measured_world(held, run)
    view = run.view
    summary = internal_summary.internal_summary(view)
    assert comparison['comparison_ref'] in summary['ungraded_measurement_refs']
    # The next decision is the grading of the held measurements, without a model.
    decision = asyncio.run(run.next_decision())
    assert decision == ToolCall('context_grade', {'scope': held['assignment']['scope']})
    graded = step(run, decision)
    assert graded['outcome']['status'] == 'completed'
    reader = run.view.records
    sheets = received_attachments(reader, reader.refs())
    recurrence = next(row for row in sheets if row['measurement_ref'] == comparison['comparison_ref'])
    assert recurrence['policy'] == 'recurrence_specific_loci_components_and_sampling'
    assert reader.receipt(recurrence['source_ref'])['how'] == 'produced'
    assert reader.table(ATTACHMENTS).select({'source_ref': recurrence['source_ref']})
    summary = internal_summary.internal_summary(run.view)
    assert summary['ungraded_measurement_refs'] == []
    finding = summary['finding']
    features = next(row for row in finding['attachments'] if row['sheet_ref'] == [recurrence['source_ref']])
    assert features['evidence_type'] == 'conserved_neighborhood' and features['scored'] is True
    assert (features['score_lower'], features['score_upper']) == tuple(recurrence['bounds'])
    assert features['missing_count'] == len(recurrence['missing'])
    assert finding['conserved_neighborhood_count'] == 1 and finding['single_locus_organization_count'] == 2
    # Without an assessment linking the context observation to the proposed annotation, nothing is credited.
    assert EPISODE.credit(summary, reader) == 0.0
    observation = next(row['id'] for row in reader.list('observation')
                       if row['source_ref'] == recurrence['source_ref'])
    commit = {'structural_proposals': [], 'terms': [], 'source_subjects': [], 'observations': [], 'hypotheses': [],
              'annotation_updates': [],
              'assessments': [{'alias': 'context_support', 'expected_revision': 0,
                               'hypothesis_ref': held['hypothesis'], 'observation_ref': observation,
                               'relation': 'strengthens', 'applicability': 'direct',
                               'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': []}]}
    reasoned = step(run, ToolCall('reason', {'commit': commit, 'scope': held['assignment']['scope']}))
    assert reasoned['outcome']['status'] == 'completed', reasoned['outcome']
    summary = internal_summary.internal_summary(run.view)
    credit = EPISODE.credit(summary, run.view.records)
    assert credit > 0 and summary['finding']['source_contribution_count'] == 1
    assert summary['finding']['covered_fraction'] > 0
    completion = {'ended_by': 'yield_stop', 'units_consumed': run.view.units_consumed, 'credit': credit}
    result = final_to_parent.final_to_parent(summary, completion, ('committed_record_refs',))
    form = EPISODE.return_form.select(('committed_record_refs',))
    assert form.admit(result, 'return') == result
    refs = set(form.record_refs(result))
    assert recurrence['source_ref'] in refs and comparison['comparison_ref'] in refs and observation in refs
    assert set(result['committed_record_refs']) <= refs
    assert set(result['finding']) >= {name + '_count' for name in EVIDENCE_TYPE_VALUES}
    text = [name for name, spec in form.fields['finding'].form.fields.items() if spec.type == 'text']
    assert all(hasattr(form.fields['finding'].form.fields[name], 'options') for name in text)
    json.dumps(result, allow_nan=False)
    held['store'].close()
