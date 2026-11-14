"""Actual local A108 grading/sheets with explicitly synthetic source records."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a108.domain import identity
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a108.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a108.state import Store
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading import COMPONENTS, CRITERIA_BY_TYPE
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_storage import LiteratureA108GradingRepository, REQUESTED
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import LiteratureA108AggregationRepository

def context_fixture(store, requested=True):
    target, = store.create_problem(raw_sequence='MARG', molecule='protein')['subject_refs']
    term = store.put('term', {'namespace': 'synthetic_function', 'accession': 'thermal', 'label': 'thermal', 'term_type': 'family', 'source_ref': store.targets()[0]['source_ref'], 'anchor': None}, origin='external')['id']
    proposal = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'functional_family', 'value': {'type': 'term_ref', 'ref': term}, 'context_refs': []}, origin='reasoning')['id']
    text = 'Synthetic sample grows at 20 C; this is an engineering fixture, not biological evidence.'
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_context_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic sample', 'source_ref': source, 'attributes': [], 'related_refs': [target]}, origin='caller')['id']
    observed = store.put('reference', {'reference_type': 'literature_result', 'source_ref': source, 'accession': 'synthetic-observation', 'label': 'Synthetic thermal observation', 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [sample], 'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0, 'end': len(text), 'quote': text}}, origin='caller')['id']
    witness = {'source_ref': source, 'representation': 'original', 'start': 0, 'end': len(text), 'quote': text}
    arguments = {'assertion_ref': proposal, 'source_ref': source, 'target_context_ref': sample, 'target_identity': {'status': 'supported', 'support_refs': [sample]}, 'target_identity_evidence': [], 'grader_type': 'environment_temperature', 'observations': [{'original_observation_ref': observed, 'context_claim_ref': proposal, 'source_subject_ref': target, 'source_context_ref': sample, 'origin': 'recorded_sample_condition', 'target_relationship': 'direct', 'relation': 'support', 'criteria': {name: {'status': 'supported', 'support_refs': [observed]} for name in CRITERIA_BY_TYPE['environment_temperature']}, 'qualifications': ['Synthetic applicability is stipulated.'], 'evidence': [{'kind': 'literature_passage', 'witness': witness}], 'origin_link_evidence': []}]}
    path = (('annotation', 'root'), ('literature', 'owner'))
    from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
    run_id = 'a108-private-publication'
    episode_id = EpisodeRef(run_id, path).episode_id
    assignment = {REQUESTED: list(COMPONENTS) if requested else []}
    journal = Journal(store, run_id)
    journal.save('runtime_episodes', {'episode_id': episode_id, 'path': json.dumps(path), 'request': json.dumps({'message': {'scope': {'subject_refs': [target]}, 'episode_assignment': assignment}}), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    context = BindingContext(run_id, episode_id, 'literature', path, {'subject_refs': [target]}, assignment, {}, (target, proposal, source, sample, observed, term))
    return (context, arguments)

@pytest.mark.parametrize('requested', [True, False])
def test_saved_context_grading_updates_main_sheet_even_without_requested_cells(tmp_path, requested):
    with Store(tmp_path / 'state') as store:
        context, arguments = context_fixture(store, requested)
        grading = LiteratureA108GradingRepository(store, context.run_id)
        first = grading.populate(context, arguments, 'original-assessment')
        assert first['status'] in ('completed', 'partial')
        saved = grading.read(first['result']['sheet_ref'])
        assert saved['selection']['observations'][0]['original_observation_ref'] == arguments['observations'][0]['original_observation_ref']
        main = LiteratureA108AggregationRepository(store, context.run_id)
        before, = main.current_annotation_cells(context)
        assert before['support_count'] == 1 and before['conflict_count'] == 0
        changed = deepcopy(arguments)
        changed['observations'][0]['relation'] = 'conflict'
        second = grading.populate(context, changed, 'corrected-assessment')
        current, = main.current_annotation_cells(context)
        assert current['sheet_ref'] in second['record_refs']
        assert current['support_count'] == 0 and current['conflict_count'] == 1
        assert main.read(before['sheet_ref'])['sheet']['cells']['overall']['support_count'] == 1
        assert current['observation_sets']['conflict'] == before['observation_sets']['support']
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0

def test_required_interpretation_rejects_missing_typed_finding_before_saving(tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a108.library import literature_required_grading
    with Store(tmp_path / 'state') as store:
        context, arguments = context_fixture(store)
        grading = LiteratureA108GradingRepository(store, context.run_id)
        result = literature_required_grading.execute(context, {'kind': 'reason', 'commit': {'assessments': [{'alias': 'missing'}]}, 'evidence_processing': {'kind': 'graded', 'gradings': [{'arguments': json.dumps(arguments)}]}}, 'original-action', grading, authorize_source_access=lambda *args: None)
        assert result['status'] == 'invalid'
        assert result['feedback']['code'] == 'evidence_assessment_source_finding_required'
        assert result['record_refs'] == []
        installed = store.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (grading.operations_table,)).fetchone()
        assert installed is None or store.db.execute('SELECT COUNT(*) FROM ' + grading.operations_table).fetchone()[0] == 0

def test_same_action_saves_typed_finding_and_context_sheet_before_progress_without_requested_cells(tmp_path):
    import asyncio
    from gene_annotation_episode.episodic_workflow.root.a108 import runtime
    from gene_annotation_episode.episodic_workflow.root.a108.domain import REASONING_SCHEMA
    from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.episode import LiteratureEpisode
    with Store(tmp_path / 'state') as store:
        context, arguments = context_fixture(store, requested=False)
        original = arguments['observations'][0]['original_observation_ref']
        source = arguments['source_ref']
        target = context.scope['subject_refs'][0]
        proposal = store.get(arguments['assertion_ref'])
        original_record = store.get(original)
        finding = {'source_claim': {'subject_refs': [target], 'predicate': proposal['predicate'], 'value': proposal['value'], 'context_refs': [arguments['target_context_ref']]}, 'qualification': {'kind': 'conditions_limit_transfer', 'context_refs': [arguments['target_context_ref']], 'assumption_refs': []}, 'status': 'retained', 'withdrawal_reason': 'not_withdrawn', 'same_source_claim_as_ref': None, 'replaces_refs': []}
        commit = {name: [] for name in REASONING_SCHEMA['required']}
        commit['observations'] = [{'alias': 'context_observation', 'subject_refs': [target], 'source_subject_refs': [original], 'kind': 'context_measurement', 'source_ref': source, 'measurements': [], 'dependencies': [original], 'anchor': original_record['anchor']}]
        commit['assessments'] = [{'alias': 'context_finding', 'hypothesis_ref': proposal['id'], 'observation_ref': '@context_observation', 'relation': 'does_not_discriminate', 'applicability': 'contextual', 'extent_basis': 'inferred_extent', 'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0, 'investigation_finding': finding}]
        selection = {'kind': 'reason', 'commit': commit, 'evidence_processing': {'kind': 'graded', 'gradings': [{'arguments': json.dumps(arguments)}]}}
        binding = LiteratureEpisode(SimpleNamespace(workflow=SimpleNamespace(store=store, run_id=context.run_id)))
        binding._tool_arguments = lambda context, name, arguments: arguments
        task = object.__new__(binding.decision_source_type)
        task.episode_id = context.episode_id
        task.path = context.path
        task.scope = dict(context.scope)
        task.last_outcome = task.last_outcome_index = task.feedback = None
        task.checkpoint = lambda: None
        observed = []

        def progress(source):
            result = source.last_outcome
            assert result['status'] in ('completed', 'partial'), result
            assessment = store.get(result['aliases']['context_finding'])
            assert assessment['investigation_finding'] == finding
            assert assessment['relation'] == 'does_not_discriminate'
            grading = result['evidence_processing']['gradings'][0]
            sheet = binding._a108_grading_repository().read(grading['result']['sheet_ref'])
            assert sheet['selection']['observations'][0]['original_observation_ref'] == original
            assert grading['result']['sheet_ref'] in result['record_refs']
            observed.append(assessment['id'])
            return {'credit': 0.0}

        async def unchanged(source, index, result):
            return result
        task.workflow = SimpleNamespace(run_id=context.run_id, journal=Journal(store, context.run_id), store=store, execution_binding=None, wait_inputs_version=None, completed_action_inputs_version=None, specialist=lambda source: binding, binding_context=lambda source: context, receive_native_outcome=lambda *args: None, receive_outcome=lambda *args: None, automatic_score_updates=unchanged, source_credit_view=progress, controller_value=lambda source, index, credit: {'credit': credit, 'index': index})
        assert asyncio.run(task.execute(selection, 4)) == {'credit': 0.0, 'index': 4}
        assert len(observed) == 1
        assert asyncio.run(task.execute(selection, 4)) == {'credit': 0.0, 'index': 4}
        assert len(observed) == 1
