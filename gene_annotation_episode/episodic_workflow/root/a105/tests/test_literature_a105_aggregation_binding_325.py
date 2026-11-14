from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories
'Selected aggregation in a literature parent, returned to its caller.'
import asyncio
from copy import deepcopy
from functools import partial
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import plain
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a105.episode_composition import compose_episode_bindings
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_worksheet import VERSION, a105_worksheet_template
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_worksheet_render import render_a105_worksheet
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import NAMESPACE as GRADE_NAMESPACE
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import NAMESPACE, COMPONENTS
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.runtime import run_workflow
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_assay_experiment_instances_323 import two_experiments
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import FixtureController

def test_two_experiments_aggregate_through_parent_loop_and_typed_return(tmp_path):
    from .source_location_fixture import verified_source_locations
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        original, first, second = two_experiments(store)
        source_claim = store.get(first['assertion_ref'])
        proposed = store.put('hypothesis', {'subject_refs': list(store.validate_scope()['subject_refs']), 'predicate': source_claim['predicate'], 'value': deepcopy(source_claim['value']), 'context_refs': []}, origin='caller')['id']
        mapping = dict(reliability='effect_precision', validity='recovery_deviation', relevance='assertion_prediction_error', attribution='attributed_fraction', overall='source_log_evidence_ratio')
        template = a105_worksheet_template([{'field': 'experiments', 'source': GRADE_NAMESPACE, 'components': list(mapping.values())}, {'field': 'combined', 'source': NAMESPACE, 'components': list(COMPONENTS)}])
        context = {'version': VERSION, 'assertion_refs': [first['assertion_ref']], 'quantity_links': [], 'assertion_links': []}
        assignment = {**plain(original.assignment), **template['assignment_rosters'], 'question_context_refs': [first['assertion_ref'], first['experiment_ref'], second['experiment_ref']]}
        assignment.update(proposed_annotation_ref=proposed, literature_task={'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'a105_experiments', 'credit_unit': 1, 'experiments': [{'experiment_ref': args['experiment_ref'], 'assay_type': args['assay_type']} for args in (first, second)]})
        decisions = [{'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment, 'goal': 'Assess both experiments and combine their retained A105 scores.', 'scope': store.validate_scope(), 'purpose': 'Return experiment assessments and the five aggregates.', 'schema_json': json.dumps(template['submitted_form']), 'initial_report_json': json.dumps({'assessment_context': context})}, 'report_update': {}}, *[{'selection': {'kind': 'tool', 'tool': 'literature.assay_grading.populate', 'arguments': verified_source_locations(store, args)}, 'report_update': {'assessment_context': context}} for args in (first, second)]]
        calls, controllers = ([], [])

        class Provider:

            async def complete(self, episode_id, role, instructions, decision_context, output_schema):
                index = len(calls)
                calls.append(decision_context)
                if index < len(decisions):
                    return deepcopy(decisions[index])
                assert index == 3
                outcomes = [json.loads(row[0]) for row in store.db.execute('SELECT outcome FROM literature_assay_grading_operations ORDER BY rowid')]
                arguments = {'assertion_ref': first['assertion_ref'], 'comparison_ref': None, 'experiments': [{'experiment_ref': args['experiment_ref'], 'metrics': {metric: {'sheet_ref': outcome['result']['sheet_ref'], 'component': component} for metric, component in mapping.items()}} for args, outcome in zip((first, second), outcomes)]}
                return {'selection': {'kind': 'tool', 'tool': 'literature.a105.aggregate', 'arguments': arguments}, 'report_update': {'assessment_context': context}}

            async def release(self, episode_id):
                pass

        def controller(path, initial):
            value = FixtureController(str(path), initial, 1 if len(path) == 1 else 3)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=Provider(), run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer, initial_known_record_refs=[*original.received_record_refs, proposed], episode_binding_factories=literature_binding_factories(rate_population=True, assay_grading_population=True, reference_parent_sources=[first['source_ref']]), binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert len(calls) == 4 and [c.scores for c in controllers] == [[0], [0, 0, 0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        receipt = store.db.execute('SELECT * FROM literature_a105_aggregation_received').fetchone()
        assert receipt is not None
        returned_rows = json.loads(receipt['cells'])
        selected_action = store.db.execute(
            "SELECT episode_id,decision_index FROM runtime_actions WHERE json_extract(action,'$.tool')=?",
            ('literature.a105.aggregate',)).fetchone()
        assert selected_action is not None
        operation_key = f"{receipt['run_id']}:{selected_action['episode_id']}:{selected_action['decision_index']}"
        selected_outcome = json.loads(store.db.execute(
            'SELECT outcome FROM literature_a105_aggregation_operations WHERE run_id=? AND episode_id=? AND operation_key=?',
            (receipt['run_id'], selected_action['episode_id'], operation_key)).fetchone()[0])
        selected_ref = selected_outcome['result']['sheet_ref']
        rows = [row for row in returned_rows if row['sheet_ref'] == selected_ref]
        assert len(rows) == len(COMPONENTS)
        historical_unavailable = [row for row in returned_rows if row['status'] == 'unavailable']
        assert historical_unavailable
        assert all(row['sheet_ref'] != selected_ref and not row['selected_components'] for row in historical_unavailable)
        by_name = {row['component']: row for row in rows}
        expected = dict(reliability=25 + 1 / 0.09, validity=-0.2, relevance=-0.2, attribution=0.75, overall=7.5 - 0.3 / 0.09)
        assert {name: row['value'] for name, row in by_name.items()} == pytest.approx(expected)
        assert all((row['status'] == 'complete' and len(row['selected_components']) == 2 for row in rows))
        assert [by_name[name]['reducer'] for name in COMPONENTS] == ['sum', 'sum', 'max', 'max', 'sum']
        grade_rows = json.loads(store.db.execute('SELECT cells FROM literature_assay_grading_received').fetchone()[0])
        assert len(grade_rows) == 10
        descriptor = json.loads((tmp_path / 'run' / 'run.json').read_text())['episode_bindings'][0]
        run_id = receipt['run_id']
        services = WorkflowServices(SimpleNamespace(store=store, run_id=run_id))
        binding, = compose_episode_bindings(services, store=store, journal=SimpleNamespace(store=store, run_id=run_id), execution_backend=None, descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        repository = binding._a105_aggregation_repository()
        parent = BindingContext(run_id, receipt['episode_id'], 'annotation', (('annotation', receipt['episode_id']),), store.validate_scope(), {}, {}, repository.cell_record_refs(rows))
        assert repository.fact_cells(parent, [rows[0]['sheet_ref']], components=list(COMPONENTS)) == rows
        rendered = []
        render_a105_worksheet(rendered, {'assessment_context': context, 'combined': rows, 'experiments': grade_rows}, section=lambda out, title, body: out.extend((title, body)), table=lambda headers, values: '\n'.join((' | '.join(map(str, row)) for row in [headers, *values])), public_records={ref: store.get(ref) for ref in (first['experiment_ref'], second['experiment_ref'])})
        text = '\n'.join(rendered)
        assert 'A105 combined experiment scores' in text
        assert 'Experiment A' in text and 'Experiment B' in text
        assert rows[0]['sheet_ref'] not in text
