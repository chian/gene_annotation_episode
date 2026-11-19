"""Actual local A108 grading/sheets with explicitly synthetic source records."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import identity
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.literature_source import LiteratureContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_grading import COMPONENTS, CRITERIA_BY_TYPE
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import LiteratureA108GradingRepository, REQUESTED
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_aggregation_storage import LiteratureA108AggregationRepository

def selected_locations(value):
    """The model-facing form: source locations only; the host reads the quotation."""
    if isinstance(value, dict):
        return {key: selected_locations(item) for key, item in value.items() if key != 'quote'}
    if isinstance(value, list):
        return [selected_locations(item) for item in value]
    return value

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
    from method_loop.identities import EpisodeRef
    run_id = 'a108-private-publication'
    episode_id = EpisodeRef(run_id, path).episode_id
    assignment = {REQUESTED: list(COMPONENTS) if requested else []}
    context = LiteratureContext(run_id, episode_id, 'literature', path, {'subject_refs': [target]}, assignment, (target, proposal, source, sample, observed, term))
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
        assert store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone() is None

def test_required_interpretation_rejects_missing_typed_finding_before_saving(tmp_path):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.sample_context_evidence import literature_required_grading
    with Store(tmp_path / 'state') as store:
        context, arguments = context_fixture(store)
        grading = LiteratureA108GradingRepository(store, context.run_id)
        result = literature_required_grading.execute(context, {'kind': 'reason', 'commit': {'assessments': [{'alias': 'missing'}]}, 'evidence_processing': {'kind': 'graded', 'gradings': [{'arguments': json.dumps(selected_locations(arguments))}]}}, 'original-action', grading, authorize_source_access=lambda *args: None)
        assert result['status'] == 'invalid'
        assert result['feedback']['code'] == 'evidence_assessment_source_finding_required'
        assert result['record_refs'] == []
        installed = store.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (grading.operations_table,)).fetchone()
        assert installed is None or store.db.execute('SELECT COUNT(*) FROM ' + grading.operations_table).fetchone()[0] == 0

