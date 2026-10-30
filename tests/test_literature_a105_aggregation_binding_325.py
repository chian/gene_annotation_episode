"""Selected aggregation in a literature parent, returned to its caller."""
import asyncio
from copy import deepcopy
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_a105_worksheet import VERSION, a105_worksheet_template
from gene_annotation_episode.literature_a105_worksheet_render import render_a105_worksheet
from gene_annotation_episode.literature_assay_grading_storage import NAMESPACE as GRADE_NAMESPACE
from gene_annotation_episode.literature_a105_aggregation_storage import NAMESPACE, COMPONENTS
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_assay_experiment_instances_323 import two_experiments
from test_runtime import FixtureController


def test_two_experiments_aggregate_through_parent_loop_and_typed_return(tmp_path):
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        original, first, second = two_experiments(store)
        mapping = dict(reliability='effect_precision', validity='recovery_deviation',
            relevance='assertion_prediction_error', attribution='attributed_fraction', overall='source_log_evidence_ratio')
        template = a105_worksheet_template([
            {'field': 'experiments', 'source': GRADE_NAMESPACE, 'components': list(mapping.values())},
            {'field': 'combined', 'source': NAMESPACE, 'components': list(COMPONENTS)}])
        context = {'version': VERSION, 'assertion_refs': [first['assertion_ref']],
            'quantity_links': [], 'assertion_links': []}
        assignment = {**plain(original.assignment), **template['assignment_rosters'],
            'question_context_refs': [first['assertion_ref'], first['experiment_ref'], second['experiment_ref']]}
        decisions = [{'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
            'goal': 'Assess both experiments and combine their retained A105 scores.',
            'scope': store.validate_scope(), 'purpose': 'Return experiment assessments and the five aggregates.',
            'schema_json': json.dumps(template['submitted_form']),
            'initial_report_json': json.dumps({'assessment_context': context})}, 'report_update': {}},
            *[{'selection': {'kind': 'tool', 'tool': 'literature.assay_grading.populate', 'arguments': args},
                'report_update': {'assessment_context': context}} for args in (first, second)]]
        calls, controllers = [], []
        class Provider:
            async def complete(self, episode_id, role, instructions, decision_context, output_schema):
                index = len(calls); calls.append(decision_context)
                if index < len(decisions):
                    return deepcopy(decisions[index])
                assert index == 3
                outcomes = [json.loads(row[0]) for row in store.db.execute(
                    'SELECT outcome FROM literature_assay_grading_operations ORDER BY rowid')]
                arguments = {'assertion_ref': first['assertion_ref'], 'comparison_ref': None,
                    'experiments': [{'experiment_ref': args['experiment_ref'],
                        'metrics': {metric: {'sheet_ref': outcome['result']['sheet_ref'], 'component': component}
                            for metric, component in mapping.items()}}
                        for args, outcome in zip((first, second), outcomes)]}
                return {'selection': {'kind': 'tool', 'tool': 'literature.a105.aggregate', 'arguments': arguments},
                    'report_update': {'assessment_context': context}}
            async def release(self, episode_id):
                pass
        def controller(path, initial):
            value = FixtureController(str(path), initial, 1 if len(path) == 1 else 3)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=Provider(),
            run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(original.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                assay_grading_population=True, reference_parent_sources=[first['source_ref']]),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert len(calls) == 4 and [c.scores for c in controllers] == [[0], [0, 0, 0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        receipt = store.db.execute('SELECT * FROM literature_a105_aggregation_received').fetchone()
        assert receipt is not None
        rows = json.loads(receipt['cells']); by_name = {row['component']: row for row in rows}
        expected = dict(reliability=25 + 1 / .09, validity=-.2, relevance=-.2,
            attribution=.75, overall=7.5 - .3 / .09)
        assert {name: row['value'] for name, row in by_name.items()} == pytest.approx(expected)
        assert all(row['status'] == 'complete' and len(row['selected_components']) == 2 for row in rows)
        assert [by_name[name]['reducer'] for name in COMPONENTS] == ['sum', 'sum', 'max', 'max', 'sum']
        grade_rows = json.loads(store.db.execute('SELECT cells FROM literature_assay_grading_received').fetchone()[0])
        assert len(grade_rows) == 10
        descriptor = json.loads((tmp_path / 'run' / 'run.json').read_text())['episode_bindings'][0]
        run_id = receipt['run_id']; services = WorkflowServices(SimpleNamespace(store=store, run_id=run_id))
        binding, = compose_episode_bindings(services, store=store,
            journal=SimpleNamespace(store=store, run_id=run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        repository = binding._a105_aggregation_repository()
        parent = BindingContext(run_id, receipt['episode_id'], 'annotation', (('annotation', receipt['episode_id']),),
            store.validate_scope(), {}, {}, repository.cell_record_refs(rows))
        assert repository.fact_cells(parent, [rows[0]['sheet_ref']], components=list(COMPONENTS)) == rows
        rendered = []
        render_a105_worksheet(rendered, {'assessment_context': context, 'combined': rows, 'experiments': grade_rows},
            section=lambda out, title, body: out.extend((title, body)),
            table=lambda headers, values: '\n'.join(' | '.join(map(str, row)) for row in [headers, *values]),
            public_records={ref: store.get(ref) for ref in (first['experiment_ref'], second['experiment_ref'])})
        text = '\n'.join(rendered)
        assert 'A105 combined experiment scores' in text
        assert 'Experiment A' in text and 'Experiment B' in text
        assert rows[0]['sheet_ref'] not in text
