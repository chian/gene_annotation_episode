"""Actual synthetic assay grading and typed findings precede original task credit."""
import asyncio
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105 import runtime
from gene_annotation_episode.episodic_workflow.root.a105.domain import REASONING_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a105.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import LiteratureAssayGradingRepository, REQUESTED
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_a105_assay_type_binding_322 import grading_fixture

def fixture_context(store):
    from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    original, arguments, _ = grading_fixture(store)
    for quantity in arguments['quantities'].values():
        quantity['number']['witness'].pop('quote')
        quantity['unit'].pop('quote')
    context = replace(original, episode_id=EpisodeRef(original.run_id, original.path).episode_id, assignment={**dict(original.assignment), REQUESTED: []})
    Journal(store, context.run_id).save('runtime_episodes', {'episode_id': context.episode_id, 'path': json.dumps(context.path), 'request': json.dumps({'message': {'scope': dict(context.scope), 'episode_assignment': dict(context.assignment)}}), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    return (context, arguments)

def test_same_action_keeps_reference_claim_and_sheet_before_credit_without_requested_cells(tmp_path):
    with Store(tmp_path / 'state') as store:
        context, arguments = fixture_context(store)
        experiment = store.get(arguments['experiment_ref'])
        proposal = store.get(arguments['assertion_ref'])
        target = context.scope['subject_refs'][0]
        finding = {'source_claim': {'subject_refs': [experiment['id']], 'predicate': proposal['predicate'], 'value': proposal['value'], 'context_refs': []}, 'qualification': {'kind': 'different_source_subject', 'context_refs': [], 'assumption_refs': []}, 'status': 'retained', 'withdrawal_reason': 'not_withdrawn', 'same_source_claim_as_ref': None, 'replaces_refs': []}
        commit = {name: [] for name in REASONING_SCHEMA['required']}
        commit['observations'] = [{'alias': 'assay_observation', 'subject_refs': [target], 'source_subject_refs': [experiment['id']], 'kind': 'source_content', 'source_ref': arguments['source_ref'], 'measurements': [], 'dependencies': [experiment['id']], 'anchor': {key: value for key, value in experiment['anchor'].items() if key != 'quote'}}]
        commit['assessments'] = [{'alias': 'assay_finding', 'hypothesis_ref': proposal['id'], 'observation_ref': '@assay_observation', 'relation': 'does_not_discriminate', 'applicability': 'contextual', 'extent_basis': 'inferred_extent', 'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0, 'investigation_finding': finding}]
        selected = {'kind': 'reason', 'commit': commit, 'evidence_processing': {'kind': 'graded', 'gradings': [{'arguments': json.dumps(arguments)}]}}
        binding = LiteratureEpisode(SimpleNamespace(workflow=SimpleNamespace(store=store, run_id=context.run_id)), rate_population=True, assay_grading_population=True)
        binding._tool_arguments = lambda context, name, arguments: arguments
        task = object.__new__(binding.decision_source_type)
        task.episode_id, task.path, task.scope = (context.episode_id, context.path, dict(context.scope))
        task.last_outcome = task.last_outcome_index = task.feedback = None
        task.checkpoint = lambda: None
        observed = []

        def progress(source):
            outcome = source.last_outcome
            assert outcome['status'] in ('completed', 'partial'), outcome
            assessment = store.get(outcome['aliases']['assay_finding'])
            assert assessment['investigation_finding'] == finding
            assert assessment['relation'] == 'does_not_discriminate'
            grading = outcome['evidence_processing']['gradings'][0]
            sheet_ref = grading['result']['sheet_ref']
            saved = binding._assay_grading_repository().read(sheet_ref)
            assert saved['selection']['experiment_ref'] == experiment['id']
            assert sheet_ref in outcome['record_refs']
            assert grading['result']['cells'] == []
            observed.append(assessment['id'])
            return {'credit': 0.0}

        async def unchanged(source, index, outcome):
            return outcome
        task.workflow = SimpleNamespace(run_id=context.run_id, journal=Journal(store, context.run_id), store=store, execution_binding=None, pending_work=lambda source: {'version': 'pending_work_v1', 'captured_at': '2026-10-27T00:00:00+00:00', 'items': []}, specialist=lambda source: binding, binding_context=lambda source: context, receive_native_outcome=lambda *args: None, receive_outcome=lambda *args: None, automatic_score_updates=unchanged, source_credit_view=progress, controller_value=lambda source, index, credit: {'credit': credit})
        assert asyncio.run(task.execute(selected, 4)) == {'credit': 0.0}
        assert asyncio.run(task.execute(selected, 4)) == {'credit': 0.0}
        assert len(observed) == 1

def test_required_assessment_rejects_missing_typed_finding_before_publication(tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a105.library import literature_required_grading
    with Store(tmp_path / 'state') as store:
        context, arguments = fixture_context(store)
        repository = LiteratureAssayGradingRepository(store, context.run_id)
        outcome = literature_required_grading.execute(context, {'kind': 'reason', 'commit': {'assessments': [{'alias': 'missing_finding'}]}, 'evidence_processing': {'kind': 'graded', 'gradings': [{'arguments': json.dumps(arguments)}]}}, 'original-assessment', repository, authorize_source_access=lambda *args: None)
        assert outcome['status'] == 'invalid'
        assert outcome['feedback']['code'] == 'evidence_assessment_source_finding_required'
        assert outcome['record_refs'] == []
        installed = store.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (repository.operations_table,)).fetchone()
        assert installed is None or store.db.execute('SELECT COUNT(*) FROM ' + repository.operations_table).fetchone()[0] == 0
