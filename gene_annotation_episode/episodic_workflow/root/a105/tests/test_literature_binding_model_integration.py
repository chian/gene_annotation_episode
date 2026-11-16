"""Conditional binding models in ordinary episodes; fixtures are labeled.

The primary example has no invented model. Positive numerical likelihood cases
use explicitly synthetic parameter tables and model sources with scripted
decisions/controllers, never a model-backed experimental claim.
"""
import asyncio
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import form_with_facts, plain
from gene_annotation_episode.episodic_workflow.root.a105.domain import canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_calculations import populate_binding_contrast
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_reader import read_binding_parameter_table
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_models import binding_model_operand_keys
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_model_storage import binding_model_cells_schema
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories
from gene_annotation_episode.episodic_workflow.root.a105.runtime import run_workflow
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_binding_integration import setup_primary
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import FixtureController, ScriptedProvider
COMPONENTS = ['log_parameter_contrast', 'log_contrast_noise_variance', 'source_profile_log_ratio', 'source_signed_index']
FORM = obj({'measurements': binding_model_cells_schema()})

def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisode(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding

def setup_synthetic(path, *, limit=False):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')

    def source(content, parents=()):
        artifact = store.artifact(content, 'application/json')
        return store.put('source', {'provider': 'synthetic_binding_model_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')
    words = 'FixtureProtein competition: same protein and state, different ligand. Synthetic known joint normal log-parameter error, with a stated threshold reporting rule for any censored log estimate.'
    methods = source(words)
    table = {'version': 'binding_parameter_table_v1', 'table_id': 'synthetic_table', 'parameter_kind': 'ic50', 'unit': 'nM', 'uncertainty_basis': 'unknown', 'minimum_experiment_count': None, 'rows': [{'subject': 'FixtureProtein', 'state': 'apo', 'experiment': 'synthetic_contrast', 'ligand': ligand, 'expression': expression, 'locator': {'row_index': index, 'column': 'IC50'}} for index, (ligand, expression) in enumerate([('reference', '10'), ('test', '>20' if limit else '20')])]}
    table_source = source(canonical(table), [methods['id']])
    extracted = read_binding_parameter_table({'source_ref': table_source['id'], 'artifact_ref': table_source['artifact_ref'], 'text': canonical(table), 'representation': 'synthetic_fixture'}, expected_subject='FixtureProtein', expected_state='apo', expected_experiment='synthetic_contrast', reference_ligand='reference', test_ligand='test', parameter_kind='ic50')
    owners = binding_model_operand_keys(populate_binding_contrast(extracted))
    model = {'version': 'known_normal_log_binding_v1', 'parameter_kind': 'ic50', 'measurement_order': ['reference', 'test'], 'measurement_keys': [owners['reference'], owners['test']], 'log_covariance': [[0.04, 0.01], [0.01, 0.09]], 'variance_status': 'known', 'censoring_model': 'threshold_of_log_estimate' if limit else 'none', 'log_basis': 'natural_log_nM', 'origin': 'synthetic'}
    model_source = source(canonical(model), [table_source['id']])
    witness = {'source_ref': methods['id'], 'representation': 'original', 'start': 0, 'end': len(words.encode())}
    args = {'source_ref': table_source['id'], 'representation': 'synthetic_fixture', 'subject': 'FixtureProtein', 'state': 'apo', 'experiment': 'synthetic_contrast', 'reference_ligand': 'reference', 'test_ligand': 'test', 'parameter_kind': 'ic50', 'design': 'equilibrium_competition', 'protein_arrangement': 'single_preparation', 'interpretation_witnesses': [witness]}
    refs = [methods['id'], table_source['id'], model_source['id']]
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': refs, 'requested_binding_model_components': COMPONENTS}
    context = BindingContext('synthetic-model-run', 'synthetic-model-child', 'literature', (('literature', 'fixture'),), store.validate_scope(), assignment, {}, refs)
    return (store, context, args, model_source['id'], witness)

def test_primary_without_error_model_preserves_limit_and_specific_unknown(tmp_path):
    store, context, args = setup_primary(tmp_path)
    try:
        assignment = plain(context.assignment)
        assignment['requested_binding_model_components'] = COMPONENTS
        context = replace(context, assignment=assignment)
        binding = binding_for(store, context)
        first = asyncio.run(binding.execute(context, 'literature.binding.populate', args, 'native'))
        current = replace(context, received_record_refs=(*context.received_record_refs, *first['record_refs']))
        modeled = asyncio.run(binding.execute(current, 'literature.binding.model.populate', {'source_ref': first['result']['sheet_ref'], 'model_source_ref': None, 'model_witnesses': []}, 'model'))
        assert modeled['status'] == 'completed', modeled
        current = replace(current, received_record_refs=(*current.received_record_refs, *modeled['record_refs']))
        facts = binding.facts(current, {'committed_record_refs': [modeled['result']['sheet_ref']]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(current, form, FORM)
        rows = form['measurements']
        assert rows[0]['value'] == pytest.approx(2.7686748229186446)
        assert rows[0]['relation'] == 'gt'
        assert rows[0]['bound_kind'] == 'reported_limit_arithmetic'
        assert rows[0]['source_uncertainty_basis'] == 'fit_to_averaged_curve'
        for row in rows[1:]:
            assert row['value'] is None
            assert row['unavailable_reason'] == 'binding_sampling_model_not_supplied'
        assert all((row['model_source_ref'] is None for row in rows))
        assert all((row['variance_status'] == 'not_supplied' for row in rows))
    finally:
        store.close()


@pytest.mark.parametrize('limit', [False, True])
def test_selected_model_action_returns_conditional_values_once(tmp_path, limit):
    store, context, args, model_ref, witness = setup_synthetic(tmp_path / 'state', limit=limit)
    controllers, received = ([], [])
    try:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(context.assignment), 'goal': 'Evaluate this synthetic source parameter contrast with its supplied model.', 'scope': plain(context.scope), 'purpose': 'Return only the requested conditional numerical components.', 'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        native = {'selection': {'kind': 'tool', 'tool': 'literature.binding.populate', 'arguments': args}, 'report_update': {}}

        def model_action(inputs):
            first = inputs['last_local_outcome']
            assert first['status'] == 'completed'
            return {'selection': {'kind': 'tool', 'tool': 'literature.binding.model.populate', 'arguments': {'source_ref': first['result']['sheet_ref'], 'model_source_ref': model_ref, 'model_witnesses': [witness]}}, 'report_update': {}}

        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert [row['component'] for row in rows] == COMPONENTS
            assert rows[0]['relation'] == ('gt' if limit else 'eq')
            assert rows[1]['value'] == pytest.approx(0.11)
            assert rows[2]['value'] > 0 and 0 < rows[3]['value'] < 1
            if not limit:
                assert rows[2]['value'] == pytest.approx(2.1838773359918244)
                assert rows[3]['value'] == pytest.approx(0.7975846370428177)
            for row in rows:
                assert row['model_origin'] == 'synthetic'
                assert row['variance_status'] == 'known'
                assert row['contrast_meaning'] == 'test_parameter_exceeds_reference'
                assert row['confidence_bound'] is None
                assert row['independent_preparation_count'] is None
            assert 'known_normal_log_parameters' in rows[2]['conditional_on']
            assert ('threshold_censoring_of_log_estimate' in rows[2]['conditional_on']) is limit
            paper = store.get(context.received_record_refs[0])
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'reported_source', 'reference_type': 'assay', 'source_ref': paper['id'], 'label': 'FixtureProtein', 'anchor': {'source_ref': paper['id'], 'artifact_ref': paper['artifact_ref'], 'start': 0, 'end': len('FixtureProtein')}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

        def controller(path, initial):
            value = FixtureController(str(path), initial, 2)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([commission, native, model_action, receive]), run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs), episode_binding_factories=literature_binding_factories(rate_population=True), binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(received) == 1
        assert [value.scores for value in controllers] == [[0, 0], [0, 0]]
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 4
        assert store.db.execute('select count(*) from literature_binding_model_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_binding_model_received').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_binding_operations').fetchone()[0] == 1
    finally:
        store.close()
